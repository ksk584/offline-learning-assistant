"""REST surface used by the dashboard: catalogue, demos and extractive notes."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import ila.server as server_module
from ila.server import app
from ila.storage import Storage

client = TestClient(app)

LIGHT_TEXT = (
    "Today we study light, reflection and refraction from Chapter 9 of the NCERT Class 10 "
    "Science book. A concave mirror converges light and a convex mirror diverges it. The "
    "refractive index measures how much a medium slows down light."
)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_config_exposes_profiles_and_curriculum() -> None:
    response = client.get("/api/config")
    assert response.status_code == 200
    body = response.json()
    assert body["offline"] is True
    assert body["notes"]["profile"] in {"potato", "balanced", "full"}
    assert body["notes"]["selectable"][0] == "auto"
    assert body["curriculum"]["class_levels"] == [8, 9, 10]
    assert body["curriculum"]["subjects"] == ["science", "maths"]
    assert len(body["curriculum"]["courses"]) == 6
    assert len(body["curriculum"]["demos"]) == 6
    assert body["hardware"]["summary"]


def test_demo_returns_requested_course() -> None:
    response = client.get("/api/demo", params={"class_level": 9, "subject": "maths"})
    assert response.status_code == 200
    body = response.json()
    assert body["exact"] is True
    assert body["class_level"] == 9
    assert body["subject"] == "maths"
    assert len(body["lines"]) >= 8
    assert body["lines"][0]["text"]


def test_demo_rejects_unknown_subject() -> None:
    response = client.get("/api/demo", params={"class_level": 10, "subject": "history"})
    assert response.status_code == 400


def test_extractive_notes_include_curriculum_alignment() -> None:
    response = client.post(
        "/api/notes",
        json={
            "text": LIGHT_TEXT,
            "title": "Light",
            "class_level": 10,
            "subject": "science",
            "use_llm": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    notes = body["notes"]
    assert notes["used_llm"] is False
    assert notes["points"]
    assert notes["curriculum"]["matches"][0]["number"] == 9
    assert "## Syllabus alignment" in body["markdown"]
    assert "Light - Reflection and Refraction" in body["markdown"]


def test_notes_accept_lines_with_timestamps() -> None:
    response = client.post(
        "/api/notes",
        json={
            "lines": [
                {"text": "Light travels in straight lines.", "start": 0.0, "end": 3.0},
                {
                    "text": "Reflection is the bouncing back of light from a surface.",
                    "start": 3.4,
                    "end": 8.0,
                },
            ],
            "class_level": 10,
            "subject": "science",
            "use_llm": False,
        },
    )
    assert response.status_code == 200
    notes = response.json()["notes"]
    assert notes["points"]
    assert any(point["start"] is not None for point in notes["points"])


def test_notes_reject_unknown_subject() -> None:
    response = client.post(
        "/api/notes",
        json={"text": LIGHT_TEXT, "class_level": 10, "subject": "history", "use_llm": False},
    )
    assert response.status_code == 400


def test_notes_reject_empty_transcript() -> None:
    response = client.post("/api/notes", json={"text": "   ", "use_llm": False})
    assert response.status_code == 400


def test_upload_rejects_empty_file() -> None:
    response = client.post(
        "/api/transcribe",
        files={"file": ("lecture.wav", b"", "audio/wav")},
    )
    assert response.status_code == 400


# ------------------------------------------------------------------- Q&A / quiz
@pytest.fixture()
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Storage:
    storage = Storage(tmp_path / "server.db")
    monkeypatch.setattr(server_module, "_STORE", storage)
    return storage


def test_config_reports_retrieval_quiz_and_storage() -> None:
    body = client.get("/api/config").json()
    assert body["retrieval"]["engine"] == "bm25+hashed-embeddings"
    assert body["retrieval"]["offline"] is True
    assert body["quiz"]["adaptive"] is True
    assert body["quiz"]["kinds"] == ["mcq", "short"]
    assert body["storage"]["engine"] == "sqlite"


def test_ask_falls_back_to_the_selected_demo(store: Storage) -> None:
    response = client.post(
        "/api/ask",
        json={"question": "What is reflection?", "class_level": 10, "subject": "science"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answerable"] is True
    assert body["citations"]
    assert body["citations"][0]["chapter_number"] == 9
    assert body["source"]["kind"] == "demo"
    assert body["source"]["exact"] is True
    assert body["course"] == "Class 10 Science"


def test_ask_refuses_an_ungrounded_question(store: Storage) -> None:
    response = client.post(
        "/api/ask",
        json={
            "question": "Who won the 2011 cricket World Cup?",
            "class_level": 10,
            "subject": "science",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answerable"] is False
    assert body["citations"] == []
    assert body["confidence"] == 0.0


def test_quiz_flow_tracks_mastery_and_gaps(store: Storage) -> None:
    start = client.post(
        "/api/quiz/start",
        json={
            "student_id": "api-student",
            "class_level": 10,
            "subject": "maths",
            "length": 4,
        },
    )
    assert start.status_code == 200
    session = start.json()
    quiz_id = session["quiz_id"]
    assert session["total"] >= 1

    quiz = store.get_quiz(quiz_id)
    assert quiz is not None
    records = {item["id"]: item for item in quiz["state"]["questions"]}
    question = session["question"]
    result = start.json()

    for _ in range(4):
        record = records[question["id"]]
        payload: dict[str, object] = {
            "quiz_id": quiz_id,
            "question_id": question["id"],
            "response_ms": 1_500,
        }
        if question["options"]:
            payload["answer_index"] = record["answer_index"]
        else:
            payload["answer"] = record["answer"]
        answer = client.post("/api/quiz/answer", json=payload)
        assert answer.status_code == 200
        result = answer.json()
        assert result["correct"] is True
        if result["completed"]:
            break
        question = result["next_question"]

    assert result["completed"] is True
    assert result["mastery"]["mastery"] > 0.5
    assert 0.0 <= result["mastery"]["mastery"] <= 1.0
    assert result["gaps"]["attempts"] >= 1

    gaps = client.get("/api/students/api-student/gaps")
    assert gaps.status_code == 200
    assert gaps.json()["gaps"]
    assert gaps.json()["gaps"][0]["recommended_difficulty"] in {1, 2, 3}


def test_quiz_rejects_an_out_of_order_answer(store: Storage) -> None:
    session = client.post(
        "/api/quiz/start",
        json={"student_id": "api-student-2", "class_level": 10, "subject": "maths"},
    ).json()
    response = client.post(
        "/api/quiz/answer",
        json={
            "quiz_id": session["quiz_id"],
            "question_id": "not-the-current-question",
            "answer_index": 0,
        },
    )
    assert response.status_code == 400


def test_quiz_start_rejects_ungrounded_text(store: Storage) -> None:
    response = client.post(
        "/api/quiz/start",
        json={
            "student_id": "api-student-3",
            "class_level": 10,
            "subject": "science",
            "text": "Birds sing loudly near the window every morning.",
        },
    )
    assert response.status_code == 400


def test_session_persistence_and_ask_from_saved_session(store: Storage) -> None:
    created = client.post(
        "/api/sessions",
        json={
            "title": "Light revision",
            "class_level": 10,
            "subject": "science",
            "lines": [
                {
                    "text": "Reflection is the bouncing back of light from a polished surface.",
                    "start": 0.0,
                    "end": 4.0,
                },
                {
                    "text": "The angle of incidence equals the angle of reflection.",
                    "start": 4.0,
                    "end": 8.0,
                },
            ],
        },
    )
    assert created.status_code == 200
    session_id = created.json()["id"]

    listed = client.get("/api/sessions").json()["sessions"]
    assert any(item["id"] == session_id for item in listed)

    detail = client.get(f"/api/sessions/{session_id}")
    assert detail.status_code == 200
    assert detail.json()["title"] == "Light revision"

    ask = client.post(
        "/api/ask",
        json={
            "question": "What is reflection?",
            "session_id": session_id,
            "class_level": 10,
            "subject": "science",
        },
    )
    assert ask.status_code == 200
    body = ask.json()
    assert body["answerable"] is True
    assert body["source"]["kind"] == "session"
    assert body["citations"][0]["source"] == "lecture"


def test_session_and_ask_return_404_for_unknown_id(store: Storage) -> None:
    assert client.get("/api/sessions/does-not-exist").status_code == 404
    response = client.post(
        "/api/ask",
        json={"question": "What is reflection?", "session_id": "does-not-exist"},
    )
    assert response.status_code == 404


def test_remediation_lifecycle_and_feedback_loop(store: Storage) -> None:
    # 1. Generate remediation pack
    gen_res = client.post(
        "/api/remediation/generate",
        json={
            "student_id": "student-rem-1",
            "class_level": 10,
            "subject": "science",
            "count": 2,
        },
    )
    assert gen_res.status_code == 200
    pack = gen_res.json()
    assert pack["pack_id"]
    assert pack["items"]
    assert len(pack["items"]) >= 1
    assert pack["primer"]

    first_item = pack["items"][0]
    # 2. Submit remediation answer
    submit_res = client.post(
        "/api/remediation/submit",
        json={
            "pack_id": pack["pack_id"],
            "student_id": "student-rem-1",
            "item_id": first_item["id"],
            "answer": "Light",
            "response_ms": 3500,
        },
    )
    assert submit_res.status_code == 200
    ans_body = submit_res.json()
    assert "correct" in ans_body
    assert "updated_mastery" in ans_body
    assert "post_diagnosis" in ans_body


def test_teacher_endpoints_and_overview(store: Storage) -> None:
    # Seed attempt and student
    store.save_mastery("student-teacher-test", "Reflection", attempts=3, correct=2, score=0.65)
    overview_res = client.get("/api/teacher/overview")
    assert overview_res.status_code == 200
    ov = overview_res.json()
    assert "total_sessions" in ov
    assert "total_attempts" in ov
    assert "topics" in ov
    assert len(ov["topics"]) >= 1
    assert "subject" in ov["topics"][0]
    assert "subject_label" in ov["topics"][0]

    st_res = client.get("/api/teacher/students")
    assert st_res.status_code == 200
    assert "student-teacher-test" in st_res.json()["students"]

    detail_res = client.get("/api/teacher/students/student-teacher-test")
    assert detail_res.status_code == 200
    det = detail_res.json()
    assert det["student_id"] == "student-teacher-test"
    assert "classifier_model" in det


