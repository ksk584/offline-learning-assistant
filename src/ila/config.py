"""Application settings.

Every value can be overridden with ``ILA_*`` environment variables or a
``.env`` file. Use ``__`` to address nested sections::

    ILA_ASR__MODEL=small.en
    ILA_VAD__MIN_SILENCE_MS=600
    ILA_PARTIALS__ENABLED=false
    ILA_LLM__PROFILE=potato

Models and session data live under ``ILA_HOME`` (default ``~/.ila``) so the
whole application folder stays portable and git-friendly.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def ila_home() -> Path:
    """Root folder for downloaded models and session data."""
    override = os.environ.get("ILA_HOME")
    return Path(override).expanduser() if override else Path.home() / ".ila"


def default_model_dir() -> Path:
    return ila_home() / "models"


def default_data_dir() -> Path:
    return ila_home() / "data"


def default_llm_dir() -> Path:
    return default_model_dir() / "llm"


class AudioSettings(BaseModel):
    """Audio capture / playback configuration."""

    sample_rate: int = 16_000
    block_ms: int = 40
    #: Input device index. ``None`` uses the system default microphone.
    device: int | None = None
    #: Pace file playback at real time (useful for demos of "live" behaviour).
    realtime: bool = False


class VadSettings(BaseModel):
    """Energy-based voice activity detection and utterance segmentation."""

    frame_ms: int = 30
    #: Speech starts when a frame is this far above the adaptive noise floor.
    start_margin_db: float = 8.0
    #: Speech continues while frames stay this far above the noise floor.
    end_margin_db: float = 3.0
    min_silence_ms: int = 450
    pre_roll_ms: int = 240
    post_roll_ms: int = 240
    #: Minimum voiced (speech) audio required to keep an utterance.
    min_speech_ms: int = 350
    #: Hard cap on a single utterance; longer speech is cut at a quiet point.
    max_segment_s: float = 20.0


class PartialSettings(BaseModel):
    """Live "typing" captions for speech that is still in progress."""

    enabled: bool = True
    #: Do not transcribe a partial utterance before it is this long.
    after_s: float = 1.2
    #: Re-transcribe the in-progress utterance at this interval.
    interval_s: float = 2.0


class AsrSettings(BaseModel):
    """faster-whisper (CTranslate2 Whisper) configuration."""

    model: str = "base.en"
    device: Literal["auto", "cpu", "cuda"] = "auto"
    compute_type: str = "int8"
    cpu_threads: int = 0
    beam_size: int = 5
    #: ``None`` lets Whisper auto-detect the language (slower, multilingual).
    language: str | None = "en"
    #: Drop segments that are both likely non-speech and low confidence.
    no_speech_threshold: float = 0.6
    logprob_threshold: float = -1.0
    model_dir: Path = Field(default_factory=default_model_dir)
    #: Set to true once models are downloaded for a fully offline deployment.
    local_files_only: bool = False


class LlmSettings(BaseModel):
    """Local GGUF model used to rewrite selected transcript content into notes.

    Note generation is extractive-first: TextRank chooses the sentences that
    carry the lecture, and the model only rewrites those short excerpts. That
    keeps prompt sizes small enough for a 2B model on a 4-core CPU.
    """

    enabled: bool = True
    #: ``auto`` picks potato / balanced / full from detected hardware.
    profile: str = "auto"
    #: Explicit GGUF path; overrides ``profile`` when set.
    model_path: Path | None = None
    model_dir: Path = Field(default_factory=default_llm_dir)
    n_ctx: int = 4096
    #: ``0`` uses physical cores minus one.
    n_threads: int = 0
    n_batch: int = 256
    max_tokens: int = 320
    temperature: float = 0.2
    top_p: float = 0.9
    #: Wall-clock budget for all LLM calls on one lecture. The remaining chunks
    #: fall back to extractive notes instead of making the user wait.
    budget_s: float = 90.0
    #: Transcript characters sent per call; raise it on stronger machines.
    chunk_chars: int = 2200
    #: Refuse to load a model file smaller than this (catches broken downloads).
    min_model_bytes: int = 20_000_000


class ServerSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8765


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ILA_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    audio: AudioSettings = Field(default_factory=AudioSettings)
    vad: VadSettings = Field(default_factory=VadSettings)
    partials: PartialSettings = Field(default_factory=PartialSettings)
    asr: AsrSettings = Field(default_factory=AsrSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    #: Where transcripts / JSONL event logs are written by default.
    data_dir: Path = Field(default_factory=default_data_dir)


def load_settings() -> Settings:
    return Settings()
