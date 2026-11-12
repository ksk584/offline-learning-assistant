"""Retrieval and grounded Q&A: citation accuracy and refusal behaviour."""

from __future__ import annotations

from functools import cache

import pytest

from ila.demo import DEMOS
from ila.notes import TranscriptLine
from ila.retrieval import AnswerEngine, KnowledgeBase, chunk_text, content_terms, tokenize


@cache
def knowledge(demo_id: str) -> KnowledgeBase:
    demo = next(item for item in DEMOS if item.id == demo_id)
    lines = [
        TranscriptLine(text=line.text, start=line.start, end=line.end)
        for line in demo.lines
    ]
    return KnowledgeBase.from_lines(
        lines,
        demo.class_level,
        demo.subject,
        title=demo.title,
        source_kind="demo",
        demo_id=demo.id,
        chapter_hint=demo.chapter_number,
    )


def engine(demo_id: str, **kwargs: object) -> AnswerEngine:
    return AnswerEngine(knowledge(demo_id), **kwargs)  # type: ignore[arg-type]


#: Twenty questions spread across the six built-in demos. ``expected`` is the
#: NCERT chapter number a grounded answer must cite.
CASES: tuple[tuple[str, str, int], ...] = (
    ("class8-science-crops", "What are kharif crops?", 1),
    ("class8-science-crops", "What is manure?", 1),
    ("class8-science-crops", "What is ploughing?", 1),
    ("class9-science-motion", "What is displacement?", 7),
    ("class9-science-motion", "What is acceleration?", 7),
    ("class9-science-motion", "What does the slope of a velocity-time graph give?", 7),
    ("class10-science-light", "What is reflection?", 9),
    ("class10-science-light", "What is the law of reflection?", 9),
    ("class10-science-light", "What is a concave mirror?", 9),
    ("class10-science-light", "What is the refractive index?", 9),
    ("class8-maths-squares", "What is a perfect square?", 5),
    ("class8-maths-squares", "What is the square root?", 5),
    ("class8-maths-squares", "What is the radical sign?", 5),
    ("class9-maths-number-systems", "What are rational numbers?", 1),
    ("class9-maths-number-systems", "What are irrational numbers?", 1),
    ("class9-maths-number-systems", "What is rationalisation?", 1),
    ("class10-maths-quadratics", "What is a quadratic equation?", 4),
    ("class10-maths-quadratics", "What is the discriminant?", 4),
    ("class10-maths-quadratics", "What is the quadratic formula?", 4),
    ("class10-maths-quadratics", "What is the sum of the roots?", 4),
)


@pytest.mark.parametrize(("demo_id", "question", "expected"), CASES)
def test_answer_cites_expected_chapter(demo_id: str, question: str, expected: int) -> None:
    answer = engine(demo_id).ask(question)
    assert answer.answerable is True, answer.answer
    assert answer.citations, "a grounded answer must always carry a citation"
    assert answer.citations[0]["chapter_number"] == expected
    assert answer.answer


def test_citation_accuracy_meets_acceptance_threshold() -> None:
    hits = 0
    for demo_id, question, expected in CASES:
        answer = engine(demo_id).ask(question)
        if (
            answer.answerable
            and answer.citations
            and answer.citations[0]["chapter_number"] == expected
        ):
            hits += 1
    assert hits / len(CASES) >= 0.80


def test_unrelated_question_is_refused() -> None:
    answer = engine("class10-science-light").ask("Who won the 2011 cricket World Cup?")
    assert answer.answerable is False
    assert answer.citations == ()
    assert "could not find" in answer.answer.lower()


def test_no_answer_without_a_source_above_threshold() -> None:
    strict = engine("class10-science-light", min_score=2.0)
    answer = strict.ask("What is reflection?")
    assert answer.answerable is False
    assert answer.citations == ()


def test_search_can_exclude_syllabus_cards() -> None:
    base = knowledge("class10-science-light")
    results = base.search("What is reflection?", top_k=10, content_only=True)
    assert results
    assert all(item.passage.is_content for item in results)


def test_search_results_are_ranked_and_scored() -> None:
    base = knowledge("class10-maths-quadratics")
    results = base.search("What is the discriminant?", top_k=5)
    assert results
    assert results[0].passage.chapter_number == 4
    assert results == sorted(results, key=lambda item: (-item.score, item.passage.id))


def test_chunk_text_splits_long_markdown() -> None:
    text = "# Reflection\n\n" + "Reflection is the bouncing back of light. " * 60
    chunks = chunk_text(text, max_chars=300, overlap_chars=60)
    assert len(chunks) > 1
    assert all(len(chunk) <= 300 for chunk in chunks)
    assert all("#" not in chunk for chunk in chunks)


def test_tokenize_stems_and_drops_stopwords() -> None:
    tokens = tokenize("The reflecting light and the reflections")
    assert "the" not in tokens
    assert "reflect" in tokens
    assert "light" in tokens


def test_content_terms_strip_question_meta_words() -> None:
    terms = content_terms("Explain the definition of reflecting, professor")
    assert "reflect" in terms
    assert "explain" not in terms
    assert "definition" not in terms
