"""Deterministic question generation, grading, adaptive mastery and gaps."""

from __future__ import annotations

from pathlib import Path

import pytest

from ila.demo import DEMOS
from ila.notes import TranscriptLine
from ila.quiz import (
    QuizEngine,
    build_question_bank,
    difficulty_for_mastery,
    grade_answer,
    update_mastery_score,
)
from ila.retrieval import KnowledgeBase
from ila.storage import Storage


@pytest.fixture()
def knowledge() -> KnowledgeBase:
    demo = next(item for item in DEMOS if item.id == "class10-maths-quadratics")
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


@pytest.fixture()
def store(tmp_path: Path) -> Storage:
    return Storage(tmp_path / "quiz.db")


def _records(storage: Storage, quiz_id: str) -> dict[str, dict[str, object]]:
    quiz = storage.get_quiz(quiz_id)
    assert quiz is not None
    return {item["id"]: item for item in quiz["state"]["questions"]}


def _wrong_index(record: dict[str, object]) -> int:
    answer_index = int(record["answer_index"])  # type: ignore[arg-type]
    options = record["options"]
    return (answer_index + 1) % len(options)  # type: ignore[arg-type]


def test_bank_is_grounded_and_deterministic(knowledge: KnowledgeBase) -> None:
    bank = build_question_bank(knowledge)
    again = build_question_bank(knowledge)
    assert len(bank) >= 5
    assert [question.id for question in bank] == [question.id for question in again]
    assert bank[0].chapter_number == 4
    for question in bank:
        assert question.prompt
        assert question.answer
        assert question.chapter_number in range(1, 15)
        if question.kind == "mcq":
            assert question.answer_index is not None
            assert question.options[question.answer_index] == question.answer
            assert len(question.options) >= 3


def test_bank_skips_noisy_placeholders(knowledge: KnowledgeBase) -> None:
    bank = build_question_bank(knowledge)
    prompts = " ".join(question.prompt.lower() for question in bank)
    assert "alpha" not in prompts
    assert "beta" not in prompts
    assert "summary checklist" not in prompts


def test_mcq_options_include_the_answer(knowledge: KnowledgeBase) -> None:
    bank = build_question_bank(knowledge)
    for question in bank:
        if question.kind == "mcq":
            assert question.answer in question.options


def test_grade_mcq_and_short_answers(knowledge: KnowledgeBase) -> None:
    bank = build_question_bank(knowledge)
    mcq = next(question for question in bank if question.kind == "mcq")
    assert grade_answer(mcq, answer_index=mcq.answer_index)[0] is True
    assert grade_answer(mcq, answer_index=_wrong_index(
        {"answer_index": mcq.answer_index, "options": mcq.options}
    ))[0] is False
    assert grade_answer(mcq, answer=mcq.options[mcq.answer_index or 0])[0] is True

    short = next(question for question in bank if question.kind == "short")
    assert grade_answer(short, answer=short.answer)[0] is True
    assert grade_answer(short, answer="completely unrelated words here")[0] is False


def test_mastery_moves_in_the_expected_direction() -> None:
    up = update_mastery_score(0.5, correct=True, difficulty=3)
    down = update_mastery_score(0.5, correct=False, difficulty=3)
    assert up > 0.5 > down
    assert 0.0 <= down < up <= 1.0
    assert update_mastery_score(0.5, correct=True, difficulty=3) > update_mastery_score(
        0.5, correct=True, difficulty=1
    )
    assert 0.02 <= update_mastery_score(0.99, correct=True, difficulty=3) <= 1.0
    assert 0.0 <= update_mastery_score(0.02, correct=False, difficulty=1) <= 0.99


def test_difficulty_tracks_mastery() -> None:
    assert difficulty_for_mastery(0.2) == 1
    assert difficulty_for_mastery(0.5) == 2
    assert difficulty_for_mastery(0.9) == 3


def test_all_correct_run_raises_mastery_and_difficulty(
    knowledge: KnowledgeBase, store: Storage
) -> None:
    engine = QuizEngine(store)
    session = engine.start(
        knowledge,
        student_id="student-a",
        class_level=10,
        subject="maths",
        length=5,
    )
    records = _records(store, session["quiz_id"])
    question = session["question"]
    first_difficulty = question["difficulty"]
    difficulties: list[int] = []
    result: dict[str, object] = {}

    for _ in range(5):
        record = records[question["id"]]
        difficulties.append(int(record["difficulty"]))
        if question["options"]:
            result = engine.answer(
                session["quiz_id"],
                question_id=question["id"],
                answer_index=int(record["answer_index"]),
                response_ms=2_000,
            )
        else:
            result = engine.answer(
                session["quiz_id"],
                question_id=question["id"],
                answer=str(record["answer"]),
                response_ms=2_000,
            )
        assert result["correct"] is True
        if result["completed"]:
            break
        question = result["next_question"]

    assert result["completed"] is True
    mastery = result["mastery"]
    assert mastery["mastery"] > 0.6
    assert 0.0 <= mastery["mastery"] <= 1.0
    assert result["target_difficulty"] == 3
    assert difficulties[-1] >= first_difficulty


def test_wrong_answers_lower_mastery_and_ease_difficulty(
    knowledge: KnowledgeBase, store: Storage
) -> None:
    engine = QuizEngine(store)
    session = engine.start(
        knowledge,
        student_id="student-b",
        class_level=10,
        subject="maths",
        length=4,
        difficulty=3,
    )
    records = _records(store, session["quiz_id"])
    question = session["question"]
    result: dict[str, object] = {}

    for _ in range(4):
        record = records[question["id"]]
        if question["options"]:
            result = engine.answer(
                session["quiz_id"],
                question_id=question["id"],
                answer_index=_wrong_index(record),
            )
        else:
            result = engine.answer(
                session["quiz_id"],
                question_id=question["id"],
                answer="completely unrelated words here",
            )
        assert result["correct"] is False
        if result["completed"]:
            break
        question = result["next_question"]

    assert result["completed"] is True
    assert result["mastery"]["mastery"] < 0.5
    assert result["target_difficulty"] == 1


def test_gaps_list_the_three_weakest_topics(store: Storage) -> None:
    for topic, score in (("Algebra", 0.9), ("Geometry", 0.2), ("Numbers", 0.5), ("Light", 0.1)):
        store.save_mastery("student-c", topic, attempts=2, correct=1, score=score)
    engine = QuizEngine(store)
    gaps = engine.gaps("student-c", limit=3)
    assert [gap["topic"] for gap in gaps["gaps"]] == ["Light", "Geometry", "Numbers"]
    assert gaps["attempts"] == 8
    assert gaps["gaps"][0]["recommended_difficulty"] == 1


def test_start_rejects_an_empty_pool(knowledge: KnowledgeBase, store: Storage) -> None:
    engine = QuizEngine(store)
    with pytest.raises(ValueError):
        engine.start(
            knowledge,
            student_id="student-d",
            class_level=10,
            subject="maths",
            pool=[],
        )


def test_start_rejects_an_unknown_topic(knowledge: KnowledgeBase, store: Storage) -> None:
    engine = QuizEngine(store)
    with pytest.raises(ValueError):
        engine.start(
            knowledge,
            student_id="student-e",
            class_level=10,
            subject="maths",
            topic="Photosynthesis",
        )


def test_topic_filter_accepts_a_chapter_number(knowledge: KnowledgeBase, store: Storage) -> None:
    engine = QuizEngine(store)
    session = engine.start(
        knowledge,
        student_id="student-f",
        class_level=10,
        subject="maths",
        topic="4",
        length=3,
    )
    assert session["question"]["chapter_number"] == 4
    assert session["total"] == 3


def test_answer_rejects_out_of_order_question(knowledge: KnowledgeBase, store: Storage) -> None:
    engine = QuizEngine(store)
    session = engine.start(
        knowledge,
        student_id="student-g",
        class_level=10,
        subject="maths",
        length=3,
    )
    with pytest.raises(ValueError):
        engine.answer(
            session["quiz_id"],
            question_id="not-the-current-question",
            answer_index=0,
        )


def test_answer_rejects_an_unknown_quiz(store: Storage) -> None:
    engine = QuizEngine(store)
    with pytest.raises(ValueError):
        engine.answer("missing-quiz", question_id="x", answer_index=0)


def test_evaluate_semantic_answer_understands_concept_intent() -> None:
    from ila.quiz import evaluate_semantic_answer

    class MockLlm:
        available = True

        def complete(self, messages, **kwargs):
            content = messages[0]["content"]
            if "irrational" in content.lower() and "p/q" in content.lower():
                return "CORRECT: YES\nREASON: The student correctly identified that an irrational number cannot be expressed as p/q."
            if "triangle" in content.lower():
                return "CORRECT: NO\nREASON: A triangle is a geometric shape, not a number definition."
            return "CORRECT: YES\nREASON: Valid formulation."

    # Test student formulation of irrational number (the user's exact case!)
    correct, evaluator, reason = evaluate_semantic_answer(
        prompt="State the definition of an irrational number.",
        expected="A real number that cannot be expressed as a ratio of two integers.",
        submitted="cannot be expressed in the form p/q where p and q are integers",
        llm=MockLlm(),
    )
    assert correct is True
    assert evaluator == "llm"
    assert "p/q" in reason

    # Test factually wrong answer
    wrong, w_eval, w_reason = evaluate_semantic_answer(
        prompt="State the definition of a rational number.",
        expected="A number that can be expressed as a ratio p/q.",
        submitted="A triangle with three sides",
        llm=MockLlm(),
    )
    assert wrong is False
    assert w_eval == "llm"

    # Test fast-path exact match
    exact_c, exact_eval, _ = evaluate_semantic_answer(
        prompt="Define prime.",
        expected="A natural number greater than 1.",
        submitted="A natural number greater than 1.",
        llm=MockLlm(),
    )
    assert exact_c is True
    assert exact_eval == "exact"
