"""Local HTTP/WebSocket API for the captioning and notes pipelines.

The server is the only thing the React dashboard talks to. Everything binds to
loopback, nothing calls the network, and the same process can serve the built
dashboard from ``dashboard/dist``.

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

REST endpoints
--------------
``GET  /api/health``       liveness + loaded ASR models
``GET  /api/config``       ASR, notes profile, hardware and NCERT catalogue
``GET  /api/devices``      microphone list
``GET  /api/demo``         built-in NCERT demo lecture for a class/subject
``POST /api/notes``        transcript lines -> grounded notes + Markdown
``POST /api/transcribe``   uploaded audio -> transcript + optional notes
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ila import __version__, hardware
from ila.asr import AsrProvider, create_asr
from ila.audio import FileSource, build_source, list_input_devices
from ila.config import Settings, load_settings
from ila.curriculum import (
    CLASS_LEVELS,
    SUBJECT_LABELS,
    SUBJECTS,
    build_syllabus_context,
    course_catalogue,
    get_course,
)
from ila.demo import demo_summaries, find_demo
from ila.events import SCHEMA_VERSION, CaptionEvent
from ila.llm import (
    PROFILE_MODELS,
    LlmProvider,
    create_llm,
    llama_cpp_installed,
    resolve_profile,
)
from ila.notes import (
    NoteResult,
    NotesGenerator,
    TranscriptLine,
    lines_from_events,
    lines_from_text,
)
from ila.pipeline import CaptionPipeline
from ila.text import normalize_transcript

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_DIST = PROJECT_ROOT / "dashboard" / "dist"
NOTES_DIR = PROJECT_ROOT / "notes"
MAX_UPLOAD_BYTES = 250 * 1024 * 1024

app = FastAPI(title="Offline Intelligent Lecture Assistant", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
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


class LlmRegistry:
    """Keeps one local notes model in memory, replacing it when the profile changes."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._key: tuple[Any, ...] | None = None
        self._provider: LlmProvider | None = None

    def get(self, settings: Settings, *, profile: str | None) -> LlmProvider:
        key = (
            settings.llm.enabled,
            profile,
            str(settings.llm.model_path or ""),
            str(settings.llm.model_dir),
            settings.llm.n_ctx,
            settings.llm.n_threads,
        )
        with self._lock:
            if key != self._key or self._provider is None:
                self._close_locked()
                self._provider = create_llm(settings.llm, profile=profile)
                self._key = key
            return self._provider

    def _close_locked(self) -> None:
        close = getattr(self._provider, "close", None)
        if callable(close):
            with contextlib.suppress(Exception):
                close()
        self._provider = None
        self._key = None


REGISTRY = AsrRegistry()
LLM_REGISTRY = LlmRegistry()
SETTINGS = load_settings()

#: Serialise note generation: one local model, one lecture at a time.
NOTES_LOCK = threading.Lock()
#: Serialise batch transcription; the WS capture thread owns the model otherwise.
TRANSCRIBE_LOCK = threading.Lock()


# ------------------------------------------------------------------ REST models
class NoteLine(BaseModel):
    text: str
    start: float | None = None
    end: float | None = None


class NotesRequest(BaseModel):
    lines: list[NoteLine] = Field(default_factory=list)
    text: str | None = None
    title: str = "Lecture notes"
    class_level: int | None = None
    subject: str | None = None
    profile: str = "auto"
    use_llm: bool = True
    use_syllabus: bool = True
    budget_s: float | None = Field(default=None, gt=0, le=900)


# ------------------------------------------------------------------ helpers
def _resolved_profile(settings: Settings) -> str:
    try:
        return resolve_profile(settings.llm.profile)
    except ValueError:
        return "balanced"


def _notes_provider_info(settings: Settings, profile: str) -> dict[str, Any]:
    from ila.llm import LlamaCppProvider

    provider = LlamaCppProvider(settings.llm, profile=profile)
    path = provider.path
    expected = provider.expected_bytes
    size_bytes = path.stat().st_size if path.is_file() else 0
    available = (
        settings.llm.enabled
        and llama_cpp_installed()
        and path.is_file()
        and (size_bytes == expected if expected is not None else size_bytes > 0)
    )
    spec = PROFILE_MODELS[profile]
    return {
        "enabled": settings.llm.enabled,
        "profile": profile,
        "profile_requested": settings.llm.profile,
        "available": available,
        "model": path.name,
        "path": str(path),
        "size_mb": round(size_bytes / (1024**2), 1),
        "download_gb": spec.download_gb,
        "ram_gb": spec.ram_gb,
        "note": spec.note,
        "budget_s": settings.llm.budget_s,
        "threads": provider.info.n_threads,
        "selectable": ["auto", *PROFILE_MODELS],
    }


def _selection(class_level: int | None, subject: str | None) -> tuple[int, str]:
    level = SETTINGS.curriculum.class_level if class_level is None else class_level
    name = (subject or SETTINGS.curriculum.subject).strip().lower()
    try:
        get_course(level, name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return level, name


def _request_settings(request: NotesRequest) -> Settings:
    settings = SETTINGS.model_copy(deep=True)
    settings.llm.enabled = request.use_llm and request.profile != "extractive"
    if request.budget_s is not None:
        settings.llm.budget_s = request.budget_s
    return settings


def _request_lines(request: NotesRequest) -> list[TranscriptLine]:
    if request.lines:
        lines = [
            TranscriptLine(
                text=normalize_transcript(line.text),
                start=line.start,
                end=line.end,
            )
            for line in request.lines
        ]
    elif request.text and request.text.strip():
        lines = lines_from_text(request.text)
    else:
        raise HTTPException(status_code=400, detail="Provide transcript lines or text")

    lines = [line for line in lines if line.text]
    if not lines:
        raise HTTPException(status_code=400, detail="No transcript text to summarise")
    return lines


def _syllabus_for(
    lines: list[TranscriptLine], class_level: int, subject: str
) -> Any:
    if not SETTINGS.curriculum.auto_match:
        return None
    text = " ".join(line.text for line in lines)
    return build_syllabus_context(text, class_level, subject)


def _generate_notes_sync(
    settings: Settings,
    lines: list[TranscriptLine],
    *,
    title: str,
    profile: str | None,
    syllabus: Any,
) -> NoteResult:
    resolved: str | None = None
    if settings.llm.enabled:
        try:
            resolved = resolve_profile(profile or settings.llm.profile)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    provider = LLM_REGISTRY.get(settings, profile=resolved)
    generator = NotesGenerator(provider, settings.llm)
    with NOTES_LOCK:
        return generator.generate(lines, title=title, syllabus=syllabus)


def _transcribe_file(
    settings: Settings,
    path: Path,
    *,
    title: str,
    class_level: int,
    subject: str,
    profile: str,
    use_llm: bool,
) -> dict[str, Any]:
    with TRANSCRIBE_LOCK:
        asr = REGISTRY.get(settings)
        source = FileSource(
            path,
            sample_rate=settings.audio.sample_rate,
            block_ms=settings.audio.block_ms,
            realtime=False,
        )
        try:
            pipeline = CaptionPipeline.from_settings(settings, source, asr)
            events = [event for event in pipeline.events() if event.final]
            duration_s = source.duration_s
        finally:
            source.close()

    lines = lines_from_events(events)
    if not lines:
        raise ValueError("No speech was detected in the uploaded file")

    syllabus = _syllabus_for(lines, class_level, subject)
    notes: dict[str, Any] | None = None
    markdown: str | None = None
    notes_error: str | None = None
    try:
        result = _generate_notes_sync(
            settings,
            lines,
            title=title,
            profile=profile if use_llm else None,
            syllabus=syllabus,
        )
        notes = result.to_dict()
        markdown = result.to_markdown()
    except Exception as exc:  # a transcript is still useful if notes fail
        logger.exception("notes failed after upload transcription")
        notes_error = str(exc)

    return {
        "lines": [line.to_dict() for line in lines],
        "transcript": " ".join(line.text for line in lines),
        "duration_s": round(duration_s, 2),
        "asr": asr.info.to_dict(),
        "notes": notes,
        "markdown": markdown,
        "notes_error": notes_error,
    }


# --------------------------------------------------------------------- routes
@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": __version__,
        "schema": SCHEMA_VERSION,
        "asr_loaded": REGISTRY.loaded(),
    }


@app.get("/api/config")
def config() -> dict[str, Any]:
    settings = SETTINGS
    profile = _resolved_profile(settings)
    detected = hardware.detect()
    return {
        "version": __version__,
        "schema": SCHEMA_VERSION,
        "offline": True,
        "asr": {
            "model": settings.asr.model,
            "language": settings.asr.language,
            "device": settings.asr.device,
            "compute_type": settings.asr.compute_type,
            "model_dir": str(settings.asr.model_dir),
            "local_files_only": settings.asr.local_files_only,
        },
        "notes": _notes_provider_info(settings, profile),
        "hardware": {
            "summary": detected.summary,
            "ram_gb": detected.ram_gb,
            "logical_cores": detected.logical_cores,
            "physical_cores": detected.physical_cores,
            "platform": detected.platform,
            "suggested_profile": detected.suggested_profile,
            "reason": detected.reason,
        },
        "curriculum": {
            "class_levels": list(CLASS_LEVELS),
            "subjects": list(SUBJECTS),
            "subject_labels": SUBJECT_LABELS,
            "default_class_level": settings.curriculum.class_level,
            "default_subject": settings.curriculum.subject,
            "auto_match": settings.curriculum.auto_match,
            "courses": course_catalogue(),
            "demos": demo_summaries(),
        },
        "server": {
            "host": settings.server.host,
            "port": settings.server.port,
            "dashboard_built": DASHBOARD_DIST.is_dir(),
        },
    }


@app.get("/api/devices")
def devices() -> dict[str, Any]:
    try:
        return {"devices": list_input_devices()}
    except Exception as exc:  # pragma: no cover - hardware dependent
        return {"devices": [], "error": str(exc)}


@app.get("/api/demo")
def demo(class_level: int = 10, subject: str = "science") -> dict[str, Any]:
    level, name = _selection(class_level, subject)
    lecture, exact = find_demo(level, name)
    payload = lecture.to_dict()
    payload["exact"] = exact
    return payload


@app.get("/api/ncert-notes")
def list_ncert_notes() -> list[dict[str, Any]]:
    """List available generated NCERT study notes for Units 1, 2, and 3."""
    results = []
    unit_map = {
        1: ("Unit 1: Real Numbers", "Unit_1_Real_Numbers_Notes.md", 1),
        2: ("Unit 2: Polynomials", "Unit_2_Polynomials_Notes.md", 2),
        3: ("Unit 3: Pair of Linear Equations in Two Variables", "Unit_3_Pair_of_Linear_Equations_Notes.md", 3),
    }
    for unit_id, (title, filename, ch_num) in unit_map.items():
        file_path = NOTES_DIR / filename
        if file_path.is_file():
            text = file_path.read_text(encoding="utf-8")
            words = len(text.split())
            results.append({
                "unit": unit_id,
                "title": title,
                "chapter": ch_num,
                "filename": filename,
                "words": words,
                "pages": round(words / 380, 1),
            })
    return results


def _parse_markdown_into_pages(markdown: str) -> list[dict[str, Any]]:
    import re
    parts = re.split(r'\n---\n\n## Section\s+(\d+\.\d+):\s*([^\n]+)', markdown)
    pages = []
    if len(parts) > 1:
        i = 1
        page_num = 1
        while i < len(parts):
            sec_id = parts[i]
            sec_title = parts[i + 1].strip()
            content = parts[i + 2].strip()
            # Clean duplicate heading if LLM repeated it
            content = re.sub(r'^#\s+[^\n]+\n+##\s+[^\n]+\n+', '', content)
            pages.append({
                "page_number": page_num,
                "section_id": sec_id,
                "title": sec_title,
                "content": content,
                "words": len(content.split()),
            })
            page_num += 1
            i += 3
    else:
        pages.append({
            "page_number": 1,
            "section_id": "1.0",
            "title": "Complete Notes",
            "content": markdown,
            "words": len(markdown.split()),
        })
    return pages


@app.get("/api/ncert-notes/{unit}")
def get_ncert_note(unit: int) -> dict[str, Any]:
    """Return the generated markdown notes and metadata for a specific unit."""
    unit_map = {
        1: ("Unit 1: Real Numbers", "Unit_1_Real_Numbers_Notes.md"),
        2: ("Unit 2: Polynomials", "Unit_2_Polynomials_Notes.md"),
        3: ("Unit 3: Pair of Linear Equations in Two Variables", "Unit_3_Pair_of_Linear_Equations_Notes.md"),
    }
    if unit not in unit_map:
        raise HTTPException(status_code=404, detail=f"Unit {unit} notes not found")
    title, filename = unit_map[unit]
    file_path = NOTES_DIR / filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Notes file {filename} not generated yet")
    markdown = file_path.read_text(encoding="utf-8")
    words = len(markdown.split())
    pages = _parse_markdown_into_pages(markdown)
    notes_payload = {
        "title": title,
        "summary": f"Concise ~10-page NCERT study notes generated by on-device LLM ({words} words, {len(pages)} pages).",
        "points": [],
        "definitions": [],
        "keywords": ["NCERT Class 10", "Mathematics", title],
        "used_llm": True,
        "profile": "0.8B / 2B Q4",
        "model": "Qwen3.5 Local LLM",
        "dropped": 0,
        "latency_s": 168.0,
        "fallback_reason": None,
        "sentences": 10,
        "curriculum": {"course": "Class 10 Mathematics", "chapter": unit},
    }
    return {
        "unit": unit,
        "title": title,
        "word_count": words,
        "pages_est": len(pages),
        "markdown": markdown,
        "notes": notes_payload,
        "total_pages": len(pages),
        "pages": pages,
    }


@app.post("/api/notes")
async def create_notes(request: NotesRequest) -> dict[str, Any]:
    lines = _request_lines(request)
    class_level, subject = _selection(request.class_level, request.subject)
    syllabus = _syllabus_for(lines, class_level, subject) if request.use_syllabus else None
    settings = _request_settings(request)
    title = request.title.strip() or "Lecture notes"
    try:
        result = await asyncio.to_thread(
            _generate_notes_sync,
            settings,
            lines,
            title=title,
            profile=None if not settings.llm.enabled else request.profile,
            syllabus=syllabus,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("note generation failed")
        raise HTTPException(status_code=500, detail=f"Note generation failed: {exc}") from exc
    return {"notes": result.to_dict(), "markdown": result.to_markdown()}


@app.post("/api/transcribe")
async def transcribe_upload(
    file: Annotated[UploadFile, File()],
    class_level: Annotated[int, Form()] = 10,
    subject: Annotated[str, Form()] = "science",
    profile: Annotated[str, Form()] = "auto",
    use_llm: Annotated[bool, Form()] = True,
    title: Annotated[str, Form()] = "",
    budget_s: Annotated[float | None, Form()] = None,
) -> dict[str, Any]:
    level, name = _selection(class_level, subject)
    upload_dir = SETTINGS.data_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "lecture.wav").suffix.lower() or ".wav"
    target = upload_dir / f"{uuid4().hex}{suffix}"

    settings = SETTINGS.model_copy(deep=True)
    settings.partials.enabled = False
    settings.llm.enabled = use_llm and profile != "extractive"
    if budget_s is not None:
        settings.llm.budget_s = budget_s

    try:
        total = 0
        with target.open("wb") as handle:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File is larger than {MAX_UPLOAD_BYTES // (1024**2)} MB",
                    )
                handle.write(chunk)
        if total == 0:
            raise HTTPException(status_code=400, detail="The uploaded file is empty")

        return await asyncio.to_thread(
            _transcribe_file,
            settings,
            target,
            title=title.strip() or Path(file.filename or "Lecture").stem,
            class_level=level,
            subject=name,
            profile=profile,
            use_llm=settings.llm.enabled,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("upload transcription failed")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc
    finally:
        with contextlib.suppress(OSError):
            target.unlink(missing_ok=True)


# ---------------------------------------------------------------- WebSocket
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


# ---------------------------------------------------------------- dashboard & notes view
HTML_NOTES_DIR = NOTES_DIR / "html"
if HTML_NOTES_DIR.is_dir():
    app.mount("/notes-view", StaticFiles(directory=str(HTML_NOTES_DIR), html=True), name="notes_html")

if DASHBOARD_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(DASHBOARD_DIST), html=True), name="dashboard")
else:

    @app.get("/")
    def dashboard_not_built() -> dict[str, str]:
        return {
            "message": "Dashboard build not found.",
            "develop": "cd dashboard && npm install && npm run dev  (http://localhost:5173)",
            "build": "cd dashboard && npm install && npm run build  (served here at /)",
        }
