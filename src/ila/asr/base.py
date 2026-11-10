"""Engine-agnostic ASR types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np


@dataclass(slots=True, frozen=True)
class TranscriptResult:
    """Result of transcribing one utterance window."""

    text: str
    language: str | None = None
    avg_logprob: float = 0.0
    no_speech_prob: float = 0.0
    duration_s: float = 0.0


@dataclass(slots=True, frozen=True)
class AsrInfo:
    """What the loaded engine is actually running."""

    engine: str
    model: str
    device: str
    compute_type: str

    def to_dict(self) -> dict[str, str]:
        return {
            "engine": self.engine,
            "model": self.model,
            "device": self.device,
            "compute_type": self.compute_type,
        }


@runtime_checkable
class AsrProvider(Protocol):
    """Minimal interface every speech-to-text backend must satisfy."""

    @property
    def info(self) -> AsrInfo: ...

    def transcribe(
        self,
        audio: np.ndarray,
        *,
        initial_prompt: str | None = None,
        language: str | None = None,
    ) -> TranscriptResult: ...
