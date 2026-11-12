"""SQLite persistence: sessions, quiz state, attempts and mastery."""

from __future__ import annotations

from pathlib import Path

from ila.storage import Storage

LINES = [
    {"text": "Reflection is the bouncing back of light.", "start": 0.0, "end": 4.0},
    {"text": "The angle of incidence equals the angle of reflection.", "start": 4.0, "end": 8.0},
]


def test_session_roundtrip(tmp_path: Path) -> None:
    store = Storage(tmp_path / "ila.db")
    session_id = store.save_session(
        title="Light revision",
        class_level=10,
        subject="science",
        lines=LINES,
        transcript=" ".join(line["text"] for line in LINES),  # type: ignore[arg-type]
        duration_s=8.0,
    )

    listed = store.list_sessions()
    assert [item["id"] for item in listed] == [session_id]
    assert listed[0]["utterances"] == 2
    assert listed[0]["has_notes"] is False

    loaded = store.get_session(session_id)
    assert loaded is not None
    assert loaded["title"] == "Light revision"
    assert loaded["class_level"] == 10
    assert loaded["subject"] == "science"
    assert [line["text"] for line in loaded["lines"]] == [line["text"] for line in LINES]

    assert store.get_session("missing") is None


def test_session_upsert_replaces_utterances(tmp_path: Path) -> None:
    store = Storage(tmp_path / "ila.db")
    session_id = store.save_session(
        title="First",
        class_level=10,
        subject="science",
        lines=LINES,
    )
    store.save_session(
        session_id=session_id,
        title="Second",
        class_level=10,
        subject="science",
        lines=LINES[:1],
        notes={"summary": "Short"},
        markdown="# Notes",
    )
    loaded = store.get_session(session_id)
    assert loaded is not None
    assert loaded["title"] == "Second"
    assert len(loaded["lines"]) == 1
    assert loaded["markdown"] == "# Notes"
    assert loaded["notes"] == {"summary": "Short"}
    assert len(store.list_sessions()) == 1


def test_quiz_state_roundtrip(tmp_path: Path) -> None:
    store = Storage(tmp_path / "ila.db")
    quiz_id = store.create_quiz(
        student_id="student",
        class_level=10,
        subject="maths",
        topic="Quadratic Equations",
        state={"current": "q1", "questions": [{"id": "q1"}]},
    )
    quiz = store.get_quiz(quiz_id)
    assert quiz is not None
    assert quiz["completed"] is False
    assert quiz["score"] == 0.0
    assert quiz["state"]["current"] == "q1"

    store.update_quiz(
        quiz_id,
        state={"current": None, "questions": [{"id": "q1"}]},
        completed=True,
        score=0.8,
    )
    updated = store.get_quiz(quiz_id)
    assert updated is not None
    assert updated["completed"] is True
    assert updated["score"] == 0.8
    assert updated["state"]["current"] is None

    assert store.get_quiz("missing") is None


def test_attempts_are_recorded_most_recent_first(tmp_path: Path) -> None:
    store = Storage(tmp_path / "ila.db")
    store.record_attempt(
        quiz_id="quiz",
        student_id="student",
        question_id="q1",
        topic="Quadratic Equations",
        difficulty=2,
        prompt="Which option defines a quadratic equation?",
        expected="an equation of degree two",
        response="an equation of degree two",
        correct=True,
        response_ms=1_200,
    )
    store.record_attempt(
        quiz_id="quiz",
        student_id="student",
        question_id="q2",
        topic="Quadratic Equations",
        difficulty=3,
        prompt="What is the discriminant?",
        expected="b squared minus four a c",
        response="unknown",
        correct=False,
        response_ms=4_000,
    )

    attempts = store.recent_attempts("student")
    assert [item["question_id"] for item in attempts] == ["q2", "q1"]
    assert attempts[0]["correct"] is False
    assert attempts[1]["correct"] is True
    assert attempts[1]["response_ms"] == 1_200


def test_mastery_is_upserted_and_clamped(tmp_path: Path) -> None:
    store = Storage(tmp_path / "ila.db")
    first = store.save_mastery("student", "Algebra", attempts=1, correct=1, score=0.7)
    assert first["score"] == 0.7
    assert store.get_mastery("student", "Algebra")["score"] == 0.7  # type: ignore[index]

    second = store.save_mastery("student", "Algebra", attempts=2, correct=1, score=1.6)
    assert second["score"] == 1.0
    row = store.get_mastery("student", "Algebra")
    assert row is not None
    assert row["attempts"] == 2
    assert row["correct"] == 1
    assert row["score"] == 1.0

    assert store.get_mastery("student", "Missing") is None


def test_weakest_topics_are_sorted_ascending(tmp_path: Path) -> None:
    store = Storage(tmp_path / "ila.db")
    for topic, score in (("Geometry", 0.9), ("Algebra", 0.2), ("Numbers", 0.5)):
        store.save_mastery("student", topic, attempts=1, correct=1, score=score)

    weakest = store.weakest_topics("student", limit=2)
    assert [item["topic"] for item in weakest] == ["Algebra", "Numbers"]
    assert [item["score"] for item in weakest] == [0.2, 0.5]


def test_database_is_reusable_after_reopening(tmp_path: Path) -> None:
    path = tmp_path / "ila.db"
    first = Storage(path)
    session_id = first.save_session(
        title="Persisted",
        class_level=9,
        subject="maths",
        lines=LINES,
    )

    second = Storage(path)
    loaded = second.get_session(session_id)
    assert loaded is not None
    assert loaded["title"] == "Persisted"
