"""Transcript text cleanup.

Whisper occasionally emits non-speech artefacts when a window is quiet or
ambiguous: block glyphs, zero-width characters, stray control codes. Those must
never reach the note/Q&A stages, so every caption is normalized here.
"""

from __future__ import annotations

import unicodedata

from ila.events import CaptionEvent

#: Unicode blocks that model hallucinations tend to land in.
_ARTEFACT_RANGES = (
    (0x2500, 0x257F),  # box drawing
    (0x2580, 0x259F),  # block elements
    (0x25A0, 0x25FF),  # geometric shapes
)


def _is_artefact(char: str) -> bool:
    code = ord(char)
    if unicodedata.category(char) in {"Cc", "Cf", "Cs", "Co", "Cn"}:
        return True
    return any(low <= code <= high for low, high in _ARTEFACT_RANGES)


def normalize_transcript(text: str) -> str:
    """Collapse whitespace and strip model artefacts (keeps normal punctuation)."""
    if not text:
        return ""
    kept: list[str] = []
    for char in text:
        if char.isspace():
            kept.append(" ")
        elif not _is_artefact(char):
            kept.append(char)
    return " ".join("".join(kept).split())


def has_content(text: str) -> bool:
    """True when the text carries real words, not just punctuation or symbols."""
    return any(char.isalnum() for char in text)


def clean_caption(event: CaptionEvent) -> CaptionEvent | None:
    """Return a normalized event, or ``None`` if nothing meaningful is left."""
    text = normalize_transcript(event.text)
    if not text or not has_content(text):
        return None
    if text == event.text:
        return event
    return CaptionEvent(
        utterance_id=event.utterance_id,
        text=text,
        start=event.start,
        end=event.end,
        final=event.final,
        language=event.language,
        avg_logprob=event.avg_logprob,
        no_speech_prob=event.no_speech_prob,
        latency_ms=event.latency_ms,
        audio_s=event.audio_s,
    )
