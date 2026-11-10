"""Local HTTP/WebSocket API for the captioning pipeline.

This is the transport the React teacher dashboard will consume in a later phase.
It stays deliberately small: one health endpoint, device discovery, and a single
streaming WebSocket.

WebSocket protocol (``/ws/captions``)
-------------------------------------
Client sends one JSON config message::

    {"source": "mic", "device": null, "model": "base.en",
     "language": "en", "partials": true}

or for offline files::

    {"source": "file", "path": "C:/lectures/week3.wav", "realtime": true}

Server then emits newline-delimited JSON messages:

* ``{"type": "status", "stage": "loading_model", ...}``
* ``{"type": "ready", "schema": 1, "asr": {...}}``
* ``{"type": "caption", "kind": "partial" | "final", ...}``
* ``{"type": "error", "message": "..."}``
* ``{"type": "done"}``

The client may send ``{"action": "stop"}`` at any time to end the session.
Closing the socket also stops the capture thread.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from ila import __version__
from ila.asr import AsrProvider, create_asr
from ila.audio import build_source, list_input_devices
from ila.config import Settings, load_settings
from ila.events import SCHEMA_VERSION, CaptionEvent
from ila.pipeline import CaptionPipeline

logger = logging.getLogger(__name__)

app = FastAPI(title="Offline Intelligent Lecture Assistant", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AsrRegistry:
    """Loads each (model, device, compute_type) combination at most once."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cache: dict[tuple[str, str, str], AsrProvider] = {}

    def get(self, settings: Settings) -> AsrProvider:
        key = (settings.asr.model, settings.asr.device, settings.asr.compute_type)
        with self._lock:
            provider = self._cache.get(key)
            if provider is None:
                provider = create_asr(settings.asr)
                self._cache[key] = provider
            return provider

    def loaded(self) -> list[dict[str, str]]:
        with self._lock:
            return [provider.info.to_dict() for provider in self._cache.values()]


REGISTRY = AsrRegistry()
SETTINGS = load_settings()


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": __version__,
        "schema": SCHEMA_VERSION,
        "asr_loaded": REGISTRY.loaded(),
    }


@app.get("/api/devices")
def devices() -> dict[str, Any]:
    try:
        return {"devices": list_input_devices()}
    except Exception as exc:  # pragma: no cover - hardware dependent
        return {"devices": [], "error": str(exc)}


@app.websocket("/ws/captions")
async def captions_socket(websocket: WebSocket) -> None:
    await websocket.accept()

    try:
        request = await websocket.receive_json()
    except (WebSocketDisconnect, ValueError):
        return

    if not isinstance(request, dict):
        await websocket.send_json({"type": "error", "message": "Expected a JSON object"})
        await websocket.close()
        return

    settings = _apply_overrides(SETTINGS.model_copy(deep=True), request)
    source_kind = str(request.get("source", "mic")).lower()

    await websocket.send_json(
        {"type": "status", "stage": "loading_model", "model": settings.asr.model}
    )
    try:
        asr = await asyncio.to_thread(REGISTRY.get, settings)
    except Exception as exc:
        logger.exception("failed to load ASR model")
        await websocket.send_json({"type": "error", "message": str(exc)})
        await websocket.close()
        return

    await websocket.send_json(
        {
            "type": "ready",
            "schema": SCHEMA_VERSION,
            "asr": asr.info.to_dict(),
            "source": source_kind,
        }
    )
    await _pump(websocket, settings, asr, source_kind, request)


def _apply_overrides(settings: Settings, request: dict[str, Any]) -> Settings:
    if request.get("model"):
        settings.asr.model = str(request["model"]).strip()
    if "language" in request:
        language = request["language"]
        settings.asr.language = None if not language or language == "auto" else str(language)
    if request.get("device") is not None:
        settings.audio.device = int(request["device"])
    if request.get("partials") is not None:
        settings.partials.enabled = bool(request["partials"])
    if request.get("realtime") is not None:
        settings.audio.realtime = bool(request["realtime"])
    if request.get("model_dir"):
        settings.asr.model_dir = request["model_dir"]
    return settings


async def _pump(
    websocket: WebSocket,
    settings: Settings,
    asr: AsrProvider,
    source_kind: str,
    request: dict[str, Any],
) -> None:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[Any] = asyncio.Queue()
    stop = threading.Event()
    sentinel = object()

    def worker() -> None:
        source = None
        try:
            source = build_source(
                source_kind,
                path=request.get("path"),
                sample_rate=settings.audio.sample_rate,
                block_ms=settings.audio.block_ms,
                device=settings.audio.device,
                realtime=settings.audio.realtime,
            )
            pipeline = CaptionPipeline.from_settings(settings, source, asr)
            for event in pipeline.events(stop=stop.is_set):
                loop.call_soon_threadsafe(queue.put_nowait, event)
                if stop.is_set():
                    break
        except Exception as exc:
            logger.exception("caption session failed")
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "message": str(exc)})
        finally:
            if source is not None:
                try:
                    source.close()
                except Exception:  # pragma: no cover - best effort
                    logger.debug("failed to close audio source", exc_info=True)
            loop.call_soon_threadsafe(queue.put_nowait, sentinel)

    thread = threading.Thread(target=worker, name="ila-captions", daemon=True)
    thread.start()

    async def watch_client() -> None:
        try:
            while True:
                message = await websocket.receive_json()
                if isinstance(message, dict) and message.get("action") == "stop":
                    stop.set()
                    return
        except Exception:
            stop.set()

    watcher = asyncio.create_task(watch_client())
    completed = False
    try:
        while True:
            item = await queue.get()
            if item is sentinel:
                completed = True
                break
            if isinstance(item, CaptionEvent):
                await websocket.send_json(item.to_dict())
            else:
                await websocket.send_json(item)
    except WebSocketDisconnect:
        logger.debug("caption client disconnected")
    finally:
        stop.set()
        watcher.cancel()
        if thread.is_alive():
            await asyncio.to_thread(thread.join, 5.0)

    if completed:
        with contextlib.suppress(Exception):  # client may already be gone
            await websocket.send_json({"type": "done"})
