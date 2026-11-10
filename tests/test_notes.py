"""Note-generation tests: extractive ranking, LLM parsing, grounding and fallbacks.

The fake provider implements the `LlmProvider` protocol, so these run without
llama-cpp-python or a GGUF download.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from ila.config import LlmSettings
from ila.llm.base import LlmInfo, Message
from ila.notes import (
    NotesGenerator,
    TranscriptLine,
    desired_sentence_count,
    extract_keywords,
    find_definitions,
    format_timestamp,
    generate_notes,
    lines_from_events,
    lines_from_text,
    parse_note_block,
    select_sentences,
    split_sentences,
)

LECTURE = [
    TranscriptLine("Today we will discuss retrieval augmented generation.", 0.0, 3.0),
    TranscriptLine(
        "Retrieval augmented generation combines a retriever with a language model.", 4.0, 8.0
    ),
    TranscriptLine(
        "The retriever finds relevant passages from a local document store.", 9.0, 13.0
    ),
    TranscriptLine(
        "The language model then answers using only those retrieved passages.", 14.0, 18.0
    ),
    TranscriptLine(
        "This grounding reduces hallucination because every answer cites a source.", 19.0, 23.0
    ),
    TranscriptLine("Chunking controls how much context each passage contains.", 24.0, 28.0),
    TranscriptLine(
        "Overlapping chunks help preserve sentences that cross a boundary.", 29.0, 33.0
    ),
    TranscriptLine("Finally we evaluate the system with a fixed question set.", 34.0, 38.0),
]

GOOD_BLOCK = """SUMMARY: Retrieval augmented generation combines retrieval with a language \
model to ground answers.
POINTS:
- The retriever finds relevant passages from a local document store.
- Grounding reduces hallucination because every answer cites a source.
- Overlapping chunks help preserve sentences that cross a boundary.
- Photosynthesis converts light into chemical energy.
TERMS:
- chunking: controls how much context each passage contains
"""


class FakeLlm:
    def __init__(self, *, available: bool = True, reply: str = GOOD_BLOCK) -> None:
        self._available = available
        self.reply = reply
        self.calls = 0

    @property
    def info(self) -> LlmInfo:
        return LlmInfo(engine="fake", model="fake-2b", profile="balanced")

    @property
    def available(self) -> bool:
        return self._available

    def complete(
        self,
        messages: Sequence[Message],
        *,
        max_tokens: int = 320,
        temperature: float = 0.2,
        stop: Sequence[str] | None = None,
    ) -> str:
        self.calls += 1
        return self.reply


# ------------------------------------------------------------------ input parsing
def test_lines_from_events_keeps_only_finals() -> None:
    from ila.events import CaptionEvent

    events = [
        CaptionEvent(utterance_id=0, text="First sentence here.", start=0.0, end=2.0, final=False),
        CaptionEvent(utterance_id=0, text="First sentence here.", start=0.0, end=2.0, final=True),
        CaptionEvent(utterance_id=1, text="", start=2.0, end=3.0, final=True),
        CaptionEvent(utterance_id=2, text="Second sentence here.", start=3.0, end=5.0, final=True),
    ]
    lines = lines_from_events(events)
    assert [line.text for line in lines] == ["First sentence here.", "Second sentence here."]
    assert lines[1].start == 3.0


def test_lines_from_text_keeps_paragraphs() -> None:
    lines = lines_from_text("Alpha beta gamma.\n\nDelta epsilon zeta.")
    assert len(lines) == 2
    assert lines[0].start is None


def test_split_sentences_ignores_fragments() -> None:
    sentences = split_sentences([TranscriptLine("Hi. This is a full sentence. Ok.")])
    assert [sentence.text for sentence in sentences] == ["This is a full sentence."]


# -------------------------------------------------------------------- extraction
def test_keywords_prefer_repeated_content_words() -> None:
    keywords = extract_keywords(split_sentences(LECTURE))
    assert "retrieval" in keywords
    assert "generation" in keywords
    assert "the" not in keywords


def test_definition_heuristic_finds_term() -> None:
    sentences = split_sentences(
        [TranscriptLine("Retrieval is the process of finding relevant passages.")]
    )
    definitions = find_definitions(sentences)
    assert definitions
    assert definitions[0].term == "retrieval"


def test_selection_respects_limit_and_deduplicates() -> None:
    lines = [
        TranscriptLine("Entropy measures uncertainty in a random variable.", 0.0),
        TranscriptLine("Entropy measures uncertainty in a random variable.", 1.0),
        TranscriptLine("Entropy measures uncertainty in a random variable.", 2.0),
        TranscriptLine("A coin flip has two equally likely outcomes.", 3.0),
        TranscriptLine("Information theory studies the cost of encoding messages.", 4.0),
    ]
    sentences = split_sentences(lines)
    selected = select_sentences(sentences, limit=4)
    texts = [sentence.text for sentence in selected]
    assert len(selected) <= 3  # the three identical sentences collapse to one
    assert len(set(texts)) == len(texts)


def test_desired_sentence_count_is_bounded() -> None:
    assert desired_sentence_count(4) == 4
    assert desired_sentence_count(80) == 14
    assert desired_sentence_count(10_000) == 28


# ------------------------------------------------------------------------ parsing
def test_parse_block_handles_markdown_noise() -> None:
    raw = """
    **SUMMARY:** Entropy measures uncertainty.

    **POINTS:**
    1. Entropy quantifies uncertainty.
    2. A coin flip has two outcomes.

    **TERMS:**
    - entropy: a measure of uncertainty
    """
    summary, points, terms = parse_note_block(raw)
    assert summary == "Entropy measures uncertainty."
    assert len(points) == 2
    assert terms == [("entropy", "a measure of uncertainty")]


def test_parse_block_falls_back_to_sentences() -> None:
    summary, points, _ = parse_note_block(
        "Entropy measures uncertainty in a system. A fair coin has two outcomes."
    )
    assert summary is None
    assert points


# ---------------------------------------------------------------------- generator
def test_llm_notes_are_parsed_and_hallucinations_dropped() -> None:
    llm = FakeLlm()
    result = NotesGenerator(llm, LlmSettings()).generate(LECTURE, title="RAG")

    assert result.used_llm is True
    assert result.model == "fake-2b"
    assert "retrieval" in result.summary.lower()
    assert result.dropped == 1
    assert all("photosynthesis" not in point.text.lower() for point in result.points)
    assert any(point.start == 19.0 for point in result.points)
    assert [item.term for item in result.definitions] == ["chunking"]
    assert "## Key points" in result.to_markdown()


def test_morphological_variants_count_as_grounded() -> None:
    reply = """SUMMARY: Retrieval augmented generation grounds answers in retrieved passages.
POINTS:
- The retriever locates relevant passages in a local document store.
- Quantum tunnelling explains radioactive decay.
"""
    result = NotesGenerator(FakeLlm(reply=reply), LlmSettings()).generate(LECTURE)
    texts = [point.text.lower() for point in result.points]
    assert any("document store" in text for text in texts)
    assert all("quantum" not in text for text in texts)


def test_extractive_fallback_without_model() -> None:
    llm = FakeLlm(available=False)
    result = NotesGenerator(llm, LlmSettings()).generate(LECTURE)

    assert result.used_llm is False
    assert result.model is None
    assert result.fallback_reason
    assert result.points
    assert all(point.source == "extractive" for point in result.points)
    assert result.points[0].start is not None
    assert "TextRank" in result.to_markdown()


def test_budget_exhaustion_falls_back_instead_of_waiting() -> None:
    llm = FakeLlm()
    settings = LlmSettings(budget_s=0.0)
    result = NotesGenerator(llm, settings).generate(LECTURE)

    assert llm.calls == 0
    assert result.used_llm is False
    assert "budget" in (result.fallback_reason or "")


def test_disabled_llm_never_loads() -> None:
    llm = FakeLlm()
    result = NotesGenerator(llm, LlmSettings(enabled=False)).generate(LECTURE)
    assert result.used_llm is False
    assert result.fallback_reason == "LLM disabled in settings"
    assert llm.calls == 0


def test_generate_notes_wrapper_accepts_text() -> None:
    lines = lines_from_text("\n\n".join(line.text for line in LECTURE))
    result = generate_notes(lines, LlmSettings(enabled=False), title="Wrapper")
    assert result.title == "Wrapper"
    assert result.points
    assert result.to_dict()["used_llm"] is False


def test_empty_transcript_raises() -> None:
    with pytest.raises(ValueError):
        NotesGenerator(FakeLlm(), LlmSettings()).generate([])


def test_format_timestamp() -> None:
    assert format_timestamp(0) == "00:00"
    assert format_timestamp(65.9) == "01:05"
    assert format_timestamp(None) == "--:--"


def test_markdown_is_stable() -> None:
    result = NotesGenerator(FakeLlm(), LlmSettings()).generate(LECTURE, title="RAG")
    markdown = result.to_markdown()
    assert markdown.startswith("# RAG\n")
    assert "## Summary" in markdown
    assert "Generated on-device" in markdown
