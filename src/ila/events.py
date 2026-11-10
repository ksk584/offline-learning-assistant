"""Caption event contract shared by the CLI, the WebSocket server and, later,
the React teacher dashboard.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SCHEMA_VERSION = 1


@dataclass(slots=True, frozen=True)
class CaptionEvent:
    """A single caption update.

    A ``final`` event supersedes every partial event with the same
    ``utterance_id``. Partials are ephemeral previews and must never be stored
    as lecture content.
    """

    utterance_id: int
    text: str
    start: float
    end: float
    final: bool = True
    language: str | None = None
    avg_logprob: float | None = None
    no_speech_prob: float | None = None
    #: Wall-clock time spent transcribing this window (milliseconds).
    latency_ms: float | None = None
    #: Seconds of audio submitted to the model.
    audio_s: float | None = None

    @property
    def kind(self) -> str:
        return "final" if self.final else "partial"

    @property
    def duration_s(self) -> float:
        return max(0.0, self.end - self.start)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "caption",
            "schema": SCHEMA_VERSION,
            "kind": self.kind,
            "utterance_id": self.utterance_id,
            "text": self.text,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "language": self.language,
            "avg_logprob": self.avg_logprob,
            "no_speech_prob": self.no_speech_prob,
            "latency_ms": self.latency_ms,
            "audio_s": self.audio_s,
        }


@dataclass(slots=True)
class SessionSummary:
    """Aggregate stats for one captioning run."""

    utterances: int = 0
    audio_s: float = 0.0
    wall_s: float = 0.0
    events: list[CaptionEvent] = field(default_factory=list)

    @property
    def realtime_factor(self) -> float:
        """Audio seconds processed per wall second (>1 means faster than live)."""
        if self.wall_s <= 0:
            return 0.0
        return self.audio_s / self.wall_s

    @property
    def transcript(self) -> str:
        return " ".join(event.text for event in self.events if event.final).strip()
