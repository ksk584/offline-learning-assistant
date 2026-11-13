"""llama.cpp implementation of the local note model.

Loaded lazily so that ``ila notes --no-llm``, the extractive fallback and the
unit tests never pay for a multi-hundred-megabyte model load. The import of
``llama_cpp`` also happens inside ``_load``: the package is an optional extra,
and a missing native extension must degrade to extractive notes, not crash.
"""

from __future__ import annotations

import importlib.util
import logging
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ila import hardware
from ila.config import LlmSettings
from ila.llm.base import LlmInfo, Message
from ila.llm.profiles import PROFILE_MODELS, resolve_profile

if TYPE_CHECKING:  # pragma: no cover
    from llama_cpp import Llama

logger = logging.getLogger(__name__)

#: ChatML stops; Qwen models emit ``<|im_end|>`` and may hallucinate the rest.
_STOP = ["<|im_end|>", "<|endoftext|>"]


def llama_cpp_installed() -> bool:
    return importlib.util.find_spec("llama_cpp") is not None


class LlamaCppProvider:
    """Runs a quantised GGUF model on the CPU (no GPU or server required)."""

    def __init__(self, settings: LlmSettings, *, profile: str | None = None) -> None:
        self._settings = settings
        self._profile = profile or resolve_profile(settings.profile)
        self._model: Llama | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ paths
    @property
    def profile(self) -> str:
        return self._profile

    @property
    def path(self) -> Path:
        explicit = self._settings.model_path
        if explicit:
            return Path(explicit).expanduser()
        spec = PROFILE_MODELS[self._profile]
        return Path(self._settings.model_dir).expanduser() / spec.filename

    @property
    def expected_bytes(self) -> int | None:
        """Exact size for catalogue models; ``None`` for a user-supplied file."""
        if self._settings.model_path:
            return None
        return PROFILE_MODELS[self._profile].size_bytes

    @property
    def available(self) -> bool:
        path = self.path
        if not llama_cpp_installed() or not path.is_file():
            return False
        size = path.stat().st_size
        expected = self.expected_bytes
        if expected is not None:
            return size == expected
        return size >= self._settings.min_model_bytes

    @property
    def info(self) -> LlmInfo:
        return LlmInfo(
            engine="llama.cpp",
            model=self.path.name,
            path=str(self.path),
            n_ctx=self._settings.n_ctx,
            n_threads=self._threads(),
            profile=self._profile,
        )

    def _threads(self) -> int:
        if self._settings.n_threads > 0:
            return self._settings.n_threads
        phys = hardware.physical_cores()
        # Benchmark shows 8 threads yields ~20 tok/s on CPU (33% faster throughput)
        return min(8, max(phys, 4))

    # ------------------------------------------------------------------ loading
    def _load(self) -> Llama:
        from llama_cpp import Llama

        settings = self._settings
        path = self.path
        if not self.available:
            raise RuntimeError(
                f"Local note model not found at {path}. Run "
                "`ila download-llm` once while online, or disable the LLM."
            )

        threads = self._threads()
        ctx = min(settings.n_ctx, 2048)
        batch = max(min(settings.n_batch, ctx), 512)
        logger.info(
            "loading note model %s (ctx=%d threads=%d batch=%d)",
            path.name,
            ctx,
            threads,
            batch,
        )
        return Llama(
            model_path=str(path),
            n_ctx=ctx,
            n_batch=batch,
            n_threads=threads,
            use_mmap=True,
            use_mlock=False,
            verbose=False,
        )

    def _ensure_loaded(self) -> Llama:
        with self._lock:
            if self._model is None:
                self._model = self._load()
            return self._model

    def close(self) -> None:
        with self._lock:
            self._model = None

    # --------------------------------------------------------------- inference
    def complete(
        self,
        messages: Sequence[Message],
        *,
        max_tokens: int = 650,
        temperature: float = 0.2,
        stop: Sequence[str] | None = None,
    ) -> str:
        model = self._ensure_loaded()
        stops = list(stop) if stop else list(_STOP)

        try:
            result: dict[str, Any] = model.create_chat_completion(
                messages=list(messages),
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=self._settings.top_p,
                stop=stops,
            )
            return str(result["choices"][0]["message"]["content"]).strip()
        except (ValueError, RuntimeError) as exc:
            # Old/odd GGUF metadata can leave llama.cpp without a chat template.
            logger.debug("chat template unavailable (%s); using ChatML", exc)

        prompt = "".join(
            f"<|im_start|>{message['role']}\n{message['content']}<|im_end|>\n"
            for message in messages
        )
        prompt += "<|im_start|>assistant\n"
        result = model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=self._settings.top_p,
            stop=stops,
        )
        return str(result["choices"][0]["text"]).strip()
