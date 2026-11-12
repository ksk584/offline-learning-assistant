"""Small SQLite store for sessions, quiz attempts and topic mastery.

SQLite is in the Python standard library, so the persistence layer adds no
download and no service to run. Every method opens a short-lived connection;
that keeps the store safe to call from FastAPI's thread pool without sharing a
connection across threads.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    title TEXT NOT NULL,
    class_level INTEGER,
    subject TEXT,
    duration_s REAL,
    transcript TEXT NOT NULL DEFAULT '',
    notes_json TEXT,
    markdown TEXT,
    topic TEXT,
    chapter_number INTEGER
);

CREATE TABLE IF NOT EXISTS utterances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL,
    text TEXT NOT NULL,
    start REAL,
    end REAL
);

CREATE TABLE IF NOT EXISTS notes (
    session_id TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
    markdown TEXT NOT NULL,
    notes_json TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quiz_sessions (
    id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL,
    class_level INTEGER,
    subject TEXT,
    topic TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0,
    score REAL NOT NULL DEFAULT 0,
    state_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    difficulty INTEGER NOT NULL,
    prompt TEXT NOT NULL,
    expected TEXT NOT NULL,
    response TEXT NOT NULL DEFAULT '',
    correct INTEGER NOT NULL,
    response_ms INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mastery (
    student_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    correct INTEGER NOT NULL DEFAULT 0,
    score REAL NOT NULL DEFAULT 0.5,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (student_id, topic)
);

CREATE INDEX IF NOT EXISTS idx_utterances_session ON utterances(session_id, idx);
CREATE INDEX IF NOT EXISTS idx_attempts_student ON quiz_attempts(student_id, created_at);
CREATE INDEX IF NOT EXISTS idx_attempts_quiz ON quiz_attempts(quiz_id);
CREATE INDEX IF NOT EXISTS idx_mastery_student ON mastery(student_id, score);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _loads(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


class Storage:
    """Thin, explicit data-access layer (no ORM, no migration framework)."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    # --------------------------------------------------------------- plumbing
    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path), timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _init(self) -> None:
        with self._connection() as connection:
            connection.executescript(SCHEMA)
            for col, col_type in [("topic", "TEXT"), ("chapter_number", "INTEGER")]:
                try:
                    connection.execute(f"ALTER TABLE sessions ADD COLUMN {col} {col_type}")
                except Exception:
                    pass

    # ---------------------------------------------------------------- sessions
    def save_session(
        self,
        *,
        title: str,
        class_level: int | None,
        subject: str | None,
        lines: Sequence[dict[str, Any]],
        transcript: str = "",
        duration_s: float | None = None,
        notes: dict[str, Any] | None = None,
        markdown: str | None = None,
        session_id: str | None = None,
        topic: str | None = None,
        chapter_number: int | None = None,
    ) -> str:
        identifier = session_id or uuid4().hex
        created = _now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO sessions
                    (id, created_at, title, class_level, subject, duration_s, transcript,
                     notes_json, markdown, topic, chapter_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    class_level=excluded.class_level,
                    subject=excluded.subject,
                    duration_s=excluded.duration_s,
                    transcript=excluded.transcript,
                    notes_json=excluded.notes_json,
                    markdown=excluded.markdown,
                    topic=excluded.topic,
                    chapter_number=excluded.chapter_number
                """,
                (
                    identifier,
                    created,
                    title,
                    class_level,
                    subject,
                    duration_s,
                    transcript,
                    json.dumps(notes, ensure_ascii=False) if notes is not None else None,
                    markdown,
                    topic,
                    chapter_number,
                ),
            )
            connection.execute("DELETE FROM utterances WHERE session_id = ?", (identifier,))
            connection.executemany(
                """
                INSERT INTO utterances (session_id, idx, text, start, end)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        identifier,
                        index,
                        str(line.get("text", "")),
                        line.get("start"),
                        line.get("end"),
                    )
                    for index, line in enumerate(lines)
                ],
            )
            if markdown is not None:
                connection.execute(
                    """
                    INSERT INTO notes (session_id, markdown, notes_json, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        markdown=excluded.markdown,
                        notes_json=excluded.notes_json,
                        updated_at=excluded.updated_at
                    """,
                    (
                        identifier,
                        markdown,
                        json.dumps(notes, ensure_ascii=False) if notes is not None else None,
                        created,
                    ),
                )
        return identifier

    def list_sessions(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT s.id, s.created_at, s.title, s.class_level, s.subject, s.duration_s,
                       s.transcript, s.markdown, COUNT(u.id) AS utterances
                FROM sessions s
                LEFT JOIN utterances u ON u.session_id = s.id
                GROUP BY s.id
                ORDER BY s.created_at DESC
                LIMIT ?
                """,
                (max(1, limit),),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "title": row["title"],
                "class_level": row["class_level"],
                "subject": row["subject"],
                "duration_s": row["duration_s"],
                "utterances": row["utterances"],
                "preview": (row["transcript"] or "")[:220],
                "has_notes": bool(row["markdown"]),
            }
            for row in rows
        ]

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            session = connection.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if session is None:
                return None
            rows = connection.execute(
                "SELECT text, start, end FROM utterances WHERE session_id = ? ORDER BY idx",
                (session_id,),
            ).fetchall()
            note_row = connection.execute(
                "SELECT markdown FROM notes WHERE session_id = ?", (session_id,)
            ).fetchone()
        return {
            "id": session["id"],
            "created_at": session["created_at"],
            "title": session["title"],
            "class_level": session["class_level"],
            "subject": session["subject"],
            "duration_s": session["duration_s"],
            "transcript": session["transcript"],
            "notes": _loads(session["notes_json"]),
            "markdown": note_row["markdown"] if note_row else session["markdown"],
            "lines": [dict(row) for row in rows],
            "topic": session["topic"] if "topic" in session.keys() else None,
            "chapter_number": session["chapter_number"] if "chapter_number" in session.keys() else None,
        }

    def get_notes_by_chapter(
        self,
        chapter_number: int,
        *,
        class_level: int | None = None,
        subject: str | None = None,
    ) -> dict[str, Any] | None:
        with self._connection() as connection:
            cursor = connection.execute(
                """
                SELECT id, created_at, title, class_level, subject, duration_s,
                       transcript, notes_json, markdown, topic, chapter_number
                FROM sessions
                WHERE chapter_number = ?
                  AND (class_level = ? OR ? IS NULL)
                  AND (subject = ? OR ? IS NULL)
                  AND markdown IS NOT NULL AND markdown != ''
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (chapter_number, class_level, class_level, subject, subject),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "created_at": row["created_at"],
                "title": row["title"],
                "class_level": row["class_level"],
                "subject": row["subject"],
                "duration_s": row["duration_s"],
                "transcript": row["transcript"],
                "notes": _loads(row["notes_json"]),
                "markdown": row["markdown"],
                "topic": row["topic"],
                "chapter_number": row["chapter_number"],
            }

    # ------------------------------------------------------------------ quizzes
    def create_quiz(
        self,
        *,
        student_id: str,
        class_level: int,
        subject: str,
        topic: str | None,
        state: dict[str, Any],
        quiz_id: str | None = None,
    ) -> str:
        identifier = quiz_id or uuid4().hex
        now = _now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO quiz_sessions
                    (id, student_id, class_level, subject, topic, created_at, updated_at,
                     completed, score, state_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, ?)
                """,
                (
                    identifier,
                    student_id,
                    class_level,
                    subject,
                    topic,
                    now,
                    now,
                    json.dumps(state, ensure_ascii=False),
                ),
            )
        return identifier

    def get_quiz(self, quiz_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM quiz_sessions WHERE id = ?", (quiz_id,)
            ).fetchone()
        if row is None:
            return None
        payload = dict(row)
        payload["state"] = _loads(row["state_json"]) or {}
        payload["completed"] = bool(row["completed"])
        return payload

    def update_quiz(
        self,
        quiz_id: str,
        *,
        state: dict[str, Any],
        completed: bool,
        score: float,
    ) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE quiz_sessions
                SET state_json = ?, completed = ?, score = ?, updated_at = ?
                WHERE id = ?
                """,
                (json.dumps(state, ensure_ascii=False), int(completed), score, _now(), quiz_id),
            )

    def record_attempt(
        self,
        *,
        quiz_id: str,
        student_id: str,
        question_id: str,
        topic: str,
        difficulty: int,
        prompt: str,
        expected: str,
        response: str,
        correct: bool,
        response_ms: int | None = None,
    ) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO quiz_attempts
                    (quiz_id, student_id, question_id, topic, difficulty, prompt, expected,
                     response, correct, response_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    quiz_id,
                    student_id,
                    question_id,
                    topic,
                    difficulty,
                    prompt,
                    expected,
                    response,
                    int(correct),
                    response_ms,
                    _now(),
                ),
            )

    def recent_attempts(self, student_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT question_id, topic, difficulty, prompt, expected, response, correct,
                       response_ms, created_at
                FROM quiz_attempts
                WHERE student_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (student_id, max(1, limit)),
            ).fetchall()
        return [{**dict(row), "correct": bool(row["correct"])} for row in rows]

    # ------------------------------------------------------------------ mastery
    def get_mastery(self, student_id: str, topic: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM mastery WHERE student_id = ? AND topic = ?",
                (student_id, topic),
            ).fetchone()
        return dict(row) if row else None

    def list_mastery(self, student_id: str) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM mastery WHERE student_id = ? ORDER BY score ASC, topic ASC",
                (student_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_mastery(
        self,
        student_id: str,
        topic: str,
        *,
        attempts: int,
        correct: int,
        score: float,
    ) -> dict[str, Any]:
        now = _now()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO mastery (student_id, topic, attempts, correct, score, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(student_id, topic) DO UPDATE SET
                    attempts=excluded.attempts,
                    correct=excluded.correct,
                    score=excluded.score,
                    updated_at=excluded.updated_at
                """,
                (student_id, topic, attempts, correct, max(0.0, min(1.0, score)), now),
            )
        return {
            "student_id": student_id,
            "topic": topic,
            "attempts": attempts,
            "correct": correct,
            "score": round(max(0.0, min(1.0, score)), 4),
            "updated_at": now,
        }

    def weakest_topics(self, student_id: str, *, limit: int = 3) -> list[dict[str, Any]]:
        return self.list_mastery(student_id)[: max(1, limit)]

    def list_students(self) -> list[str]:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT student_id FROM mastery
                UNION
                SELECT DISTINCT student_id FROM quiz_attempts
                ORDER BY student_id ASC
                """
            )
            return [row[0] for row in cursor.fetchall() if row[0]]

    def teacher_overview(self) -> dict[str, Any]:
        """Aggregate class-level analytics from local SQLite storage."""
        with self._connection() as conn:
            cursor = conn.cursor()

            # 1. Overall counts
            cursor.execute("SELECT COUNT(*) FROM sessions")
            total_sessions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*), AVG(correct), AVG(response_ms) FROM quiz_attempts")
            attempts_row = cursor.fetchone()
            total_attempts = attempts_row[0] or 0
            overall_accuracy = round(float(attempts_row[1] or 0.0), 4)
            avg_response_ms = int(attempts_row[2] or 0)

            # 2. Distinct students
            cursor.execute("SELECT COUNT(DISTINCT student_id) FROM mastery")
            total_students = cursor.fetchone()[0] or 0

            # 3. Overall class mastery
            cursor.execute("SELECT AVG(score) FROM mastery")
            avg_mastery = round(float(cursor.fetchone()[0] or 0.5), 4)

            # 4. Topic-wise breakdown
            cursor.execute(
                """
                SELECT topic, COUNT(*) as attempts_count,
                       SUM(correct) as correct_count,
                       AVG(response_ms) as avg_ms
                FROM quiz_attempts
                GROUP BY topic
                ORDER BY attempts_count DESC
                """
            )
            topic_rows = cursor.fetchall()
            topic_analytics = []
            for t_row in topic_rows:
                t_name, t_attempts, t_correct, t_avg_ms = t_row
                t_acc = (t_correct / t_attempts) if t_attempts > 0 else 0.0
                topic_analytics.append({
                    "topic": t_name,
                    "attempts": t_attempts,
                    "correct": t_correct,
                    "accuracy": round(t_acc, 4),
                    "avg_response_ms": int(t_avg_ms or 0),
                })

            # 5. Recent sessions
            cursor.execute(
                """
                SELECT id, created_at, title, class_level, subject, duration_s
                FROM sessions
                ORDER BY created_at DESC
                LIMIT 10
                """
            )
            recent_sessions = [
                {
                    "id": row[0],
                    "created_at": row[1],
                    "title": row[2],
                    "class_level": row[3],
                    "subject": row[4],
                    "duration_s": row[5],
                }
                for row in cursor.fetchall()
            ]

            return {
                "total_sessions": total_sessions,
                "total_attempts": total_attempts,
                "total_students": total_students,
                "overall_accuracy": overall_accuracy,
                "avg_response_ms": avg_response_ms,
                "class_mastery_avg": avg_mastery,
                "topics": topic_analytics,
                "recent_sessions": recent_sessions,
            }
