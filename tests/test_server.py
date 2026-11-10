"""REST surface used by the dashboard: catalogue, demos and extractive notes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ila.server import app

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
