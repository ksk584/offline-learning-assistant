"""ASR provider contract and factory.

The pipeline only depends on :class:`AsrProvider`, so the engine (currently
faster-whisper, later whisper.cpp) can be swapped without touching audio
capture, segmentation or the server.
"""

from __future__ import annotations

from ila.asr.base import AsrInfo, AsrProvider, TranscriptResult
from ila.asr.faster_whisper import FasterWhisperProvider
from ila.config import AsrSettings


def create_asr(settings: AsrSettings) -> AsrProvider:
    """Build the configured ASR provider (lazily loads the model)."""
    return FasterWhisperProvider(settings)


__all__ = ["AsrInfo", "AsrProvider", "FasterWhisperProvider", "TranscriptResult", "create_asr"]
