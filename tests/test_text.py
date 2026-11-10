"""Transcript normalization used by the caption pipeline."""

from __future__ import annotations

import pytest

from ila.events import CaptionEvent
from ila.text import clean_caption, has_content, normalize_transcript


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  hello   world  ", "hello world"),
        ("line\nbreak\tand  tabs", "line break and tabs"),
        ("block \u2588\u2588\u2588 glyph", "block glyph"),
        ("zero\u200bwidth\u200djoiner", "zerowidthjoiner"),
        ("non\u00a0breaking space", "non breaking space"),
        ("it\u2019s fine \u2014 really", "it\u2019s fine \u2014 really"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_normalize_transcript(raw: str, expected: str):
    assert normalize_transcript(raw) == expected


def test_has_content_rejects_symbols_only():
    assert has_content("hello")
    assert has_content("42")
    assert not has_content("...")
    assert not has_content("")


def _event(text: str) -> CaptionEvent:
    return CaptionEvent(utterance_id=1, text=text, start=0.0, end=1.0)


def test_clean_caption_returns_none_for_pure_artefacts():
    assert clean_caption(_event("\u2588\u2588\u2588")) is None
    assert clean_caption(_event("  ... ")) is None


def test_clean_caption_is_identity_when_already_clean():
    event = _event("retrieval augmented generation")
    assert clean_caption(event) is event


def test_clean_caption_preserves_metadata():
    event = CaptionEvent(
        utterance_id=7,
        text="  split \u2588 into chunks ",
        start=3.0,
        end=5.0,
        final=False,
        language="en",
        avg_logprob=-0.2,
        no_speech_prob=0.1,
        latency_ms=321.0,
        audio_s=2.0,
    )
    cleaned = clean_caption(event)

    assert cleaned is not None
    assert cleaned.text == "split into chunks"
    assert (cleaned.utterance_id, cleaned.start, cleaned.end) == (7, 3.0, 5.0)
    assert cleaned.final is False
    assert cleaned.language == "en"
    assert cleaned.latency_ms == 321.0
