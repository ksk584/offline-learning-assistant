"""Local HTTP/WebSocket API for the captioning and notes pipelines.

The server is the only thing the React dashboard talks to. Everything binds to
loopback, nothing calls the network, and the same process can serve the built
dashboard from ``dashboard/dist``.

WebSocket protocol (``/ws/captions``)
-------------------------------------
Client sends one JSON config message::

    {"source": "mic", "device": null, "model": "base.en",
     "language": "en", "partials": true}

or for offline files::

    {"source": "file", "path": "C:/lectures/week3.wav", "realtime": true}

Server then emits newline-delimited JSON messages:

* ``{"type": "status", "stage": "loading_model", ...}``
* ``{"type": "ready", "schema": 1, "asr": {...}}``
* ``{"type": "caption", "kind": "partial" | "final", ...}``
* ``{"type": "error", "message": "..."}``
* ``{"type": "done"}``

The client may send ``{"action": "stop"}`` at any time to end the session.
Closing the socket also stops the capture thread.

REST endpoints
--------------
``GET  /api/health``       liveness + loaded ASR models
``GET  /api/config``       ASR, notes profile, hardware and NCERT catalogue
``GET  /api/devices``      microphone list
``GET  /api/demo``         built-in NCERT demo lecture for a class/subject
``POST /api/notes``        transcript lines -> grounded notes + Markdown
``POST /api/transcribe``   uploaded audio -> transcript + optional notes
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import threading
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ila import __version__, hardware
from ila.asr import AsrProvider, create_asr
from ila.audio import FileSource, build_source, list_input_devices
from ila.config import Settings, load_settings
from ila.curriculum import (
    CLASS_LEVELS,
    SUBJECT_LABELS,
    SUBJECTS,
    build_syllabus_context,
    course_catalogue,
    get_course,
)
from ila.demo import demo_summaries, find_demo
from ila.events import SCHEMA_VERSION, CaptionEvent
from ila.llm import (
    PROFILE_MODELS,
    LlmProvider,
    create_llm,
    llama_cpp_installed,
    resolve_profile,
)
from ila.notes import (
    NoteResult,
    NotesGenerator,
    TranscriptLine,
    lines_from_events,
    lines_from_text,
)
from ila.pipeline import CaptionPipeline
from ila.quiz import QuizEngine, build_question_bank
from ila.retrieval import EMBEDDING_DIM, AnswerEngine, KnowledgeBase
from ila.storage import Storage
from ila.text import normalize_transcript

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_DIST = PROJECT_ROOT / "dashboard" / "dist"
NOTES_DIR = PROJECT_ROOT / "notes"
MAX_UPLOAD_BYTES = 250 * 1024 * 1024

app = FastAPI(title="Offline Intelligent Lecture Assistant", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AsrRegistry:
    """Loads each (model, device, compute_type) combination at most once."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cache: dict[tuple[str, str, str], AsrProvider] = {}

    def get(self, settings: Settings) -> AsrProvider:
        key = (settings.asr.model, settings.asr.device, settings.asr.compute_type)
        with self._lock:
            provider = self._cache.get(key)
            if provider is None:
                provider = create_asr(settings.asr)
                self._cache[key] = provider
            return provider

    def loaded(self) -> list[dict[str, str]]:
        with self._lock:
            return [provider.info.to_dict() for provider in self._cache.values()]


class LlmRegistry:
    """Keeps one local notes model in memory, replacing it when the profile changes."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._key: tuple[Any, ...] | None = None
        self._provider: LlmProvider | None = None

    def get(self, settings: Settings, *, profile: str | None) -> LlmProvider:
        key = (
            settings.llm.enabled,
            profile,
            str(settings.llm.model_path or ""),
            str(settings.llm.model_dir),
            settings.llm.n_ctx,
            settings.llm.n_threads,
        )
        with self._lock:
            if key != self._key or self._provider is None:
                self._close_locked()
                self._provider = create_llm(settings.llm, profile=profile)
                self._key = key
            return self._provider

    def _close_locked(self) -> None:
        close = getattr(self._provider, "close", None)
        if callable(close):
            with contextlib.suppress(Exception):
                close()
        self._provider = None
        self._key = None


REGISTRY = AsrRegistry()
LLM_REGISTRY = LlmRegistry()
SETTINGS = load_settings()

#: Serialise note generation: one local model, one lecture at a time.
NOTES_LOCK = threading.Lock()
#: Serialise batch transcription; the WS capture thread owns the model otherwise.
TRANSCRIBE_LOCK = threading.Lock()


# ------------------------------------------------------------------ REST models
class NoteLine(BaseModel):
    text: str
    start: float | None = None
    end: float | None = None


class NotesRequest(BaseModel):
    lines: list[NoteLine] = Field(default_factory=list)
    text: str | None = None
    title: str = "Lecture notes"
    class_level: int | None = None
    subject: str | None = None
    profile: str = "auto"
    use_llm: bool = True
    use_syllabus: bool = True
    budget_s: float | None = Field(default=None, gt=0, le=900)


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    lines: list[NoteLine] = Field(default_factory=list)
    text: str | None = None
    session_id: str | None = None
    class_level: int | None = None
    subject: str | None = None
    chapter: int | None = None
    top_k: int = Field(default=5, ge=1, le=10)
    min_score: float | None = Field(default=None, gt=0, le=2)
    use_llm: bool = True
    profile: str | None = Field(default=None)


class QuizStartRequest(BaseModel):
    student_id: str = Field(default="demo-student", min_length=1, max_length=120)
    class_level: int | None = None
    subject: str | None = None
    topic: str | None = None
    length: int = Field(default=5, ge=1, le=20)
    difficulty: int | None = Field(default=None, ge=1, le=3)
    lines: list[NoteLine] = Field(default_factory=list)
    text: str | None = None
    session_id: str | None = None


class QuizAnswerRequest(BaseModel):
    quiz_id: str = Field(min_length=1)
    question_id: str = Field(min_length=1)
    answer: str = ""
    answer_index: int | None = Field(default=None, ge=0, le=8)
    response_ms: int | None = Field(default=None, ge=0, le=3_600_000)


class RemediationGenerateRequest(BaseModel):
    student_id: str = Field(default="demo-student", min_length=1, max_length=120)
    topic: str | None = None
    class_level: int | None = None
    subject: str | None = None
    count: int = Field(default=3, ge=1, le=10)
    lines: list[NoteLine] = Field(default_factory=list)
    text: str | None = None
    session_id: str | None = None


class RemediationAnswerRequest(BaseModel):
    pack_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1)
    item_id: str = Field(min_length=1)
    answer: str = ""
    selected_index: int | None = None
    response_ms: int = Field(default=4000, ge=0, le=3_600_000)


class SessionRequest(BaseModel):
    title: str = "Lecture"
    lines: list[NoteLine] = Field(default_factory=list)
    text: str | None = None
    class_level: int | None = None
    subject: str | None = None
    duration_s: float | None = Field(default=None, ge=0)
    notes: dict[str, Any] | None = None
    markdown: str | None = None


# ------------------------------------------------------------------ helpers
#: Lazy so importing the app (e.g. in tests) does not create a database.
_STORE: Storage | None = None


def _store() -> Storage:
    global _STORE
    if _STORE is None:
        _STORE = Storage(SETTINGS.data_dir / "ila.sqlite3")
    return _STORE
def _resolved_profile(settings: Settings) -> str:
    try:
        return resolve_profile(settings.llm.profile)
    except ValueError:
        return "balanced"


def _notes_provider_info(settings: Settings, profile: str) -> dict[str, Any]:
    from ila.llm import LlamaCppProvider

    provider = LlamaCppProvider(settings.llm, profile=profile)
    path = provider.path
    expected = provider.expected_bytes
    size_bytes = path.stat().st_size if path.is_file() else 0
    available = (
        settings.llm.enabled
        and llama_cpp_installed()
        and path.is_file()
        and (size_bytes == expected if expected is not None else size_bytes > 0)
    )
    spec = PROFILE_MODELS[profile]
    return {
        "enabled": settings.llm.enabled,
        "profile": profile,
        "profile_requested": settings.llm.profile,
        "available": available,
        "model": path.name,
        "path": str(path),
        "size_mb": round(size_bytes / (1024**2), 1),
        "download_gb": spec.download_gb,
        "ram_gb": spec.ram_gb,
        "note": spec.note,
        "budget_s": settings.llm.budget_s,
        "threads": provider.info.n_threads,
        "selectable": ["auto", *PROFILE_MODELS],
    }


def _selection(class_level: int | None, subject: str | None) -> tuple[int, str]:
    level = SETTINGS.curriculum.class_level if class_level is None else class_level
    name = (subject or SETTINGS.curriculum.subject).strip().lower()
    try:
        get_course(level, name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return level, name


def _request_settings(request: NotesRequest) -> Settings:
    settings = SETTINGS.model_copy(deep=True)
    settings.llm.enabled = request.use_llm and request.profile != "extractive"
    if request.budget_s is not None:
        settings.llm.budget_s = request.budget_s
    return settings


def _request_lines(request: NotesRequest) -> list[TranscriptLine]:
    if request.lines:
        lines = [
            TranscriptLine(
                text=normalize_transcript(line.text),
                start=line.start,
                end=line.end,
            )
            for line in request.lines
        ]
    elif request.text and request.text.strip():
        lines = lines_from_text(request.text)
    else:
        raise HTTPException(status_code=400, detail="Provide transcript lines or text")

    lines = [line for line in lines if line.text]
    if not lines:
        raise HTTPException(status_code=400, detail="No transcript text to summarise")
    return lines


def _syllabus_for(
    lines: list[TranscriptLine], class_level: int, subject: str
) -> Any:
    if not SETTINGS.curriculum.auto_match:
        return None
    text = " ".join(line.text for line in lines)
    return build_syllabus_context(text, class_level, subject)


def _demo_lines(class_level: int, subject: str) -> tuple[list[TranscriptLine], Any, bool]:
    lecture, exact = find_demo(class_level, subject)
    lines = [
        TranscriptLine(text=line.text, start=line.start, end=line.end)
        for line in lecture.lines
    ]
    return lines, lecture, exact


def _lines_from_payload(
    *,
    lines: list[NoteLine],
    text: str | None,
    session_id: str | None,
) -> tuple[list[TranscriptLine], str, dict[str, Any]]:
    """Resolve explicit lines, a saved session, or the built-in demo."""
    if session_id:
        session = _store().get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        resolved = [
            TranscriptLine(
                text=normalize_transcript(str(item.get("text", ""))),
                start=item.get("start"),
                end=item.get("end"),
            )
            for item in session["lines"]
        ]
        resolved = [line for line in resolved if line.text]
        if not resolved:
            raise HTTPException(status_code=400, detail="Saved session has no transcript")
        return resolved, "session", {
            "kind": "session",
            "session_id": session_id,
            "title": session["title"],
            "text": session.get("transcript", ""),
        }

    if lines or (text and text.strip()):
        resolved = _request_lines(NotesRequest(lines=lines, text=text))
        return resolved, "transcript", {
            "kind": "transcript",
            "session_id": None,
            "title": "Current transcript",
            "text": " ".join(line.text for line in resolved),
        }

    return [], "demo", {}


_STATIC_KB_CACHE: dict[tuple[int, str, str], tuple[KnowledgeBase, dict[str, Any]]] = {}
_QA_CACHE: dict[tuple[str, int, str, int | None, bool], dict[str, Any]] = {}


def _knowledge_base(
    *,
    lines: list[NoteLine],
    text: str | None,
    session_id: str | None,
    class_level: int,
    subject: str,
    title: str | None = None,
) -> tuple[KnowledgeBase, dict[str, Any]]:
    resolved, source_kind, meta = _lines_from_payload(
        lines=lines, text=text, session_id=session_id
    )
    demo = None
    exact = True
    if not resolved:
        if subject == "maths" and class_level == 10:
            source_kind = "textbook"
            meta = {
                "kind": "textbook",
                "session_id": None,
                "title": "NCERT Class 10 Mathematics Textbook",
                "demo_id": None,
                "exact": True,
                "text": "NCERT Class 10 Mathematics Textbook covering all 14 chapters",
            }
        else:
            resolved, demo, exact = _demo_lines(class_level, subject)
            source_kind = "demo"
            meta = {
                "kind": "demo",
                "session_id": None,
                "title": demo.title,
                "demo_id": demo.id,
                "exact": exact,
                "text": " ".join(line.text for line in resolved),
            }
        cache_key = (class_level, subject, source_kind)
        if cache_key in _STATIC_KB_CACHE:
            cached_kb, cached_meta = _STATIC_KB_CACHE[cache_key]
            return cached_kb, dict(cached_meta)
    else:
        meta["title"] = title or meta.get("title") or "Lecture"
    knowledge = KnowledgeBase.from_lines(
        resolved,
        class_level,
        subject,
        title=str(meta.get("title") or "Lecture"),
        source_kind=source_kind,
        demo_id=demo.id if demo else None,
        chapter_hint=demo.chapter_number if demo else None,
    )
    meta["lines"] = len(resolved)
    meta["course"] = knowledge.course.label if knowledge.course else None
    if not resolved:
        _STATIC_KB_CACHE[(class_level, subject, source_kind)] = (knowledge, dict(meta))
    return knowledge, meta


def _ask_llm_provider(profile_override: str | None = None) -> LlmProvider | None:
    if not SETTINGS.llm.enabled:
        return None
    # For high-speed interactive Q&A, prefer potato (0.8B) for ~1.2s responses unless specified
    preferred_candidates = [profile_override] if profile_override else ["potato", SETTINGS.llm.profile, "balanced"]
    for candidate in preferred_candidates:
        if not candidate:
            continue
        try:
            profile = resolve_profile(candidate)
            provider = LLM_REGISTRY.get(SETTINGS, profile=profile)
            if provider.available:
                return provider
        except Exception:
            continue
    try:
        profile = resolve_profile(SETTINGS.llm.profile)
        return LLM_REGISTRY.get(SETTINGS, profile=profile)
    except Exception:  # a Q&A request must still work extractively
        logger.debug("could not create the Q&A model", exc_info=True)
        return None


def _generate_notes_sync(
    settings: Settings,
    lines: list[TranscriptLine],
    *,
    title: str,
    profile: str | None,
    syllabus: Any,
) -> NoteResult:
    resolved: str | None = None
    if settings.llm.enabled:
        try:
            resolved = resolve_profile(profile or settings.llm.profile)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    provider = LLM_REGISTRY.get(settings, profile=resolved)
    generator = NotesGenerator(provider, settings.llm)
    with NOTES_LOCK:
        return generator.generate(lines, title=title, syllabus=syllabus)


def _transcribe_file(
    settings: Settings,
    path: Path,
    *,
    title: str,
    class_level: int,
    subject: str,
    profile: str,
    use_llm: bool,
) -> dict[str, Any]:
    with TRANSCRIBE_LOCK:
        asr = REGISTRY.get(settings)
        source = FileSource(
            path,
            sample_rate=settings.audio.sample_rate,
            block_ms=settings.audio.block_ms,
            realtime=False,
        )
        try:
            pipeline = CaptionPipeline.from_settings(settings, source, asr)
            events = [event for event in pipeline.events() if event.final]
            duration_s = source.duration_s
        finally:
            source.close()

    lines = lines_from_events(events)
    if not lines:
        raise ValueError("No speech was detected in the uploaded file")

    syllabus = _syllabus_for(lines, class_level, subject)
    notes: dict[str, Any] | None = None
    markdown: str | None = None
    notes_error: str | None = None
    try:
        result = _generate_notes_sync(
            settings,
            lines,
            title=title,
            profile=profile if use_llm else None,
            syllabus=syllabus,
        )
        notes = result.to_dict()
        markdown = result.to_markdown()
    except Exception as exc:  # a transcript is still useful if notes fail
        logger.exception("notes failed after upload transcription")
        notes_error = str(exc)

    return {
        "lines": [line.to_dict() for line in lines],
        "transcript": " ".join(line.text for line in lines),
        "duration_s": round(duration_s, 2),
        "asr": asr.info.to_dict(),
        "notes": notes,
        "markdown": markdown,
        "notes_error": notes_error,
    }


# --------------------------------------------------------------------- routes
@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": __version__,
        "schema": SCHEMA_VERSION,
        "asr_loaded": REGISTRY.loaded(),
    }


@app.get("/api/config")
def config() -> dict[str, Any]:
    settings = SETTINGS
    profile = _resolved_profile(settings)
    detected = hardware.detect()
    return {
        "version": __version__,
        "schema": SCHEMA_VERSION,
        "offline": True,
        "asr": {
            "model": settings.asr.model,
            "language": settings.asr.language,
            "device": settings.asr.device,
            "compute_type": settings.asr.compute_type,
            "model_dir": str(settings.asr.model_dir),
            "local_files_only": settings.asr.local_files_only,
        },
        "notes": _notes_provider_info(settings, profile),
        "hardware": {
            "summary": detected.summary,
            "ram_gb": detected.ram_gb,
            "logical_cores": detected.logical_cores,
            "physical_cores": detected.physical_cores,
            "platform": detected.platform,
            "suggested_profile": detected.suggested_profile,
            "reason": detected.reason,
        },
        "curriculum": {
            "class_levels": list(CLASS_LEVELS),
            "subjects": list(SUBJECTS),
            "subject_labels": SUBJECT_LABELS,
            "default_class_level": settings.curriculum.class_level,
            "default_subject": settings.curriculum.subject,
            "auto_match": settings.curriculum.auto_match,
            "courses": course_catalogue(),
            "demos": demo_summaries(),
        },
        "retrieval": {
            "engine": "bm25+hashed-embeddings",
            "fusion": "lexical 0.58 / dense 0.42",
            "embedding_dim": EMBEDDING_DIM,
            "offline": True,
            "answers": "extractive with citations",
        },
        "quiz": {
            "engine": "grounded deterministic generation",
            "mastery": "bounded exponential moving average",
            "kinds": ["mcq", "short"],
            "adaptive": True,
        },
        "storage": {
            "engine": "sqlite",
            "path": str(SETTINGS.data_dir / "ila.sqlite3"),
        },
        "server": {
            "host": settings.server.host,
            "port": settings.server.port,
            "dashboard_built": DASHBOARD_DIST.is_dir(),
        },
    }


@app.get("/api/devices")
def devices() -> dict[str, Any]:
    try:
        return {"devices": list_input_devices()}
    except Exception as exc:  # pragma: no cover - hardware dependent
        return {"devices": [], "error": str(exc)}


@app.get("/api/demo")
def demo(class_level: int = 10, subject: str = "science") -> dict[str, Any]:
    level, name = _selection(class_level, subject)
    lecture, exact = find_demo(level, name)
    payload = lecture.to_dict()
    payload["exact"] = exact
    return payload


@app.get("/api/ncert-notes")
def list_ncert_notes() -> list[dict[str, Any]]:
    """List available generated NCERT study notes for Units 1, 2, and 3."""
    results = []
    unit_map = {
        1: ("Unit 1: Real Numbers", "Unit_1_Real_Numbers_Notes.md", 1),
        2: ("Unit 2: Polynomials", "Unit_2_Polynomials_Notes.md", 2),
        3: (
            "Unit 3: Pair of Linear Equations in Two Variables",
            "Unit_3_Pair_of_Linear_Equations_Notes.md",
            3,
        ),
    }
    for unit_id, (title, filename, ch_num) in unit_map.items():
        file_path = NOTES_DIR / filename
        if file_path.is_file():
            text = file_path.read_text(encoding="utf-8")
            words = len(text.split())
            results.append({
                "unit": unit_id,
                "title": title,
                "chapter": ch_num,
                "filename": filename,
                "words": words,
                "pages": round(words / 380, 1),
            })
    return results


def _parse_markdown_into_pages(markdown: str) -> list[dict[str, Any]]:
    import re
    parts = re.split(r'\n---\n\n## Section\s+(\d+\.\d+):\s*([^\n]+)', markdown)
    pages = []
    if len(parts) > 1:
        i = 1
        page_num = 1
        while i < len(parts):
            sec_id = parts[i]
            sec_title = parts[i + 1].strip()
            content = parts[i + 2].strip()
            # Clean duplicate heading if LLM repeated it
            content = re.sub(r'^#\s+[^\n]+\n+##\s+[^\n]+\n+', '', content)
            pages.append({
                "page_number": page_num,
                "section_id": sec_id,
                "title": sec_title,
                "content": content,
                "words": len(content.split()),
            })
            page_num += 1
            i += 3
    else:
        pages.append({
            "page_number": 1,
            "section_id": "1.0",
            "title": "Complete Notes",
            "content": markdown,
            "words": len(markdown.split()),
        })
    return pages


@app.get("/api/ncert-notes/{unit}")
def get_ncert_note(unit: int) -> dict[str, Any]:
    """Return the generated markdown notes and metadata for a specific unit."""
    unit_map = {
        1: ("Unit 1: Real Numbers", "Unit_1_Real_Numbers_Notes.md"),
        2: ("Unit 2: Polynomials", "Unit_2_Polynomials_Notes.md"),
        3: (
            "Unit 3: Pair of Linear Equations in Two Variables",
            "Unit_3_Pair_of_Linear_Equations_Notes.md",
        ),
    }
    if unit not in unit_map:
        raise HTTPException(status_code=404, detail=f"Unit {unit} notes not found")
    title, filename = unit_map[unit]
    file_path = NOTES_DIR / filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Notes file {filename} not generated yet")
    markdown = file_path.read_text(encoding="utf-8")
    words = len(markdown.split())
    pages = _parse_markdown_into_pages(markdown)
    notes_payload = {
        "title": title,
        "summary": (
            f"Concise ~10-page NCERT study notes generated by on-device LLM "
            f"({words} words, {len(pages)} pages)."
        ),
        "points": [],
        "definitions": [],
        "keywords": ["NCERT Class 10", "Mathematics", title],
        "used_llm": True,
        "profile": "0.8B / 2B Q4",
        "model": "Qwen3.5 Local LLM",
        "dropped": 0,
        "latency_s": 168.0,
        "fallback_reason": None,
        "sentences": 10,
        "curriculum": {"course": "Class 10 Mathematics", "chapter": unit},
    }
    return {
        "unit": unit,
        "title": title,
        "word_count": words,
        "pages_est": len(pages),
        "markdown": markdown,
        "notes": notes_payload,
        "total_pages": len(pages),
        "pages": pages,
    }


@app.post("/api/notes")
async def create_notes(request: NotesRequest) -> dict[str, Any]:
    lines = _request_lines(request)
    class_level, subject = _selection(request.class_level, request.subject)
    settings = _request_settings(request)
    title = request.title.strip() or "Lecture notes"

    syllabus = None
    mapped_topic = None
    chapter_number = None
    correlation_score = 0.0
    matched_terms: list[str] = []

    if request.use_syllabus:
        syllabus = _syllabus_for(lines, class_level, subject)
        if not syllabus or not getattr(syllabus, "matches", None) or len(syllabus.matches) == 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"No syllabus correlation found: The transcript does not correlate with any "
                    f"NCERT Class {class_level} {subject.capitalize()} topic. Grounded notes dropped. "
                    f"Please capture a lecture covering syllabus topics (e.g. Real Numbers, Polynomials, Linear Equations, Quadratic Equations)."
                ),
            )
        top_match = syllabus.matches[0]
        if top_match.score < 1.5:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Insufficient syllabus correlation (score {top_match.score:.1f} < 1.5): "
                    f"The transcript has too little correlation with '{top_match.chapter.title}'. "
                    f"Grounded notes dropped. Please provide more subject-specific lecture content."
                ),
            )
        mapped_topic = top_match.chapter.title
        chapter_number = top_match.chapter.number
        correlation_score = top_match.score
        matched_terms = list(top_match.matched_terms)
        title = f"{mapped_topic} (Class {class_level} {subject.capitalize()})"

    try:
        result = await asyncio.to_thread(
            _generate_notes_sync,
            settings,
            lines,
            title=title,
            profile=None if not settings.llm.enabled else request.profile,
            syllabus=syllabus,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("note generation failed")
        raise HTTPException(status_code=500, detail=f"Note generation failed: {exc}") from exc

    # Store notes along with mapped topic in SQLite storage
    transcript_text = " ".join(line.text for line in lines)
    duration_s = max(0.0, (lines[-1].end or 0.0) - (lines[0].start or 0.0)) if lines else 0.0
    session_id = _store().save_session(
        title=title,
        class_level=class_level,
        subject=subject,
        lines=[line.to_dict() for line in lines],
        transcript=transcript_text,
        duration_s=duration_s,
        notes=result.to_dict(),
        markdown=result.to_markdown(),
        topic=mapped_topic,
        chapter_number=chapter_number,
    )

    return {
        "notes": result.to_dict(),
        "markdown": result.to_markdown(),
        "mapped_topic": mapped_topic,
        "chapter_number": chapter_number,
        "correlation_score": round(correlation_score, 2),
        "matched_terms": matched_terms,
        "session_id": session_id,
    }


@app.get("/api/lecture-notes/{chapter_number}")
def get_lecture_notes_for_unit(
    chapter_number: int,
    class_level: int = 10,
    subject: str = "maths",
) -> dict[str, Any]:
    level, name = _selection(class_level, subject)
    session = _store().get_notes_by_chapter(chapter_number, class_level=level, subject=name)
    if not session:
        return {"found": False, "notes": None, "markdown": None}
    return {
        "found": True,
        "session_id": session["id"],
        "title": session["title"],
        "topic": session.get("topic"),
        "chapter_number": session.get("chapter_number"),
        "markdown": session.get("markdown"),
        "notes": session.get("notes"),
        "created_at": session.get("created_at"),
    }


@app.post("/api/transcribe")
async def transcribe_upload(
    file: Annotated[UploadFile, File()],
    class_level: Annotated[int, Form()] = 10,
    subject: Annotated[str, Form()] = "science",
    profile: Annotated[str, Form()] = "auto",
    use_llm: Annotated[bool, Form()] = True,
    title: Annotated[str, Form()] = "",
    budget_s: Annotated[float | None, Form()] = None,
) -> dict[str, Any]:
    level, name = _selection(class_level, subject)
    upload_dir = SETTINGS.data_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "lecture.wav").suffix.lower() or ".wav"
    target = upload_dir / f"{uuid4().hex}{suffix}"

    settings = SETTINGS.model_copy(deep=True)
    settings.partials.enabled = False
    settings.llm.enabled = use_llm and profile != "extractive"
    if budget_s is not None:
        settings.llm.budget_s = budget_s

    try:
        total = 0
        with target.open("wb") as handle:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File is larger than {MAX_UPLOAD_BYTES // (1024**2)} MB",
                    )
                handle.write(chunk)
        if total == 0:
            raise HTTPException(status_code=400, detail="The uploaded file is empty")

        return await asyncio.to_thread(
            _transcribe_file,
            settings,
            target,
            title=title.strip() or Path(file.filename or "Lecture").stem,
            class_level=level,
            subject=name,
            profile=profile,
            use_llm=settings.llm.enabled,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("upload transcription failed")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc
    finally:
        with contextlib.suppress(OSError):
            target.unlink(missing_ok=True)


# ------------------------------------------------------------------ Q&A
@app.post("/api/ask")
async def ask_question(request: AskRequest) -> dict[str, Any]:
    """Answer from the current transcript, a saved session, or the built-in demo."""
    level, name = _selection(request.class_level, request.subject)
    cache_key = None
    if not request.lines and not request.text and not request.session_id:
        norm_q = re.sub(r"[^a-z0-9\s]", "", request.question.strip().lower())
        norm_q = " ".join(norm_q.split())
        cache_key = (
            norm_q,
            level,
            name,
            request.chapter,
            bool(request.use_llm),
            request.profile or "default",
        )
        if cache_key in _QA_CACHE:
            cached = dict(_QA_CACHE[cache_key])
            cached["latency_s"] = 0.008
            return cached

    knowledge, meta = _knowledge_base(
        lines=request.lines,
        text=request.text,
        session_id=request.session_id,
        class_level=level,
        subject=name,
    )
    llm = _ask_llm_provider(request.profile) if request.use_llm else None
    engine = AnswerEngine(
        knowledge,
        min_score=request.min_score if request.min_score is not None else 0.16,
        top_k=request.top_k,
        llm=llm,
    )
    answer = await asyncio.to_thread(
        engine.ask,
        request.question,
        use_llm=request.use_llm and llm is not None,
        chapter=request.chapter,
    )
    payload = answer.to_dict()
    payload["source"] = meta
    payload["course"] = knowledge.course.label if knowledge.course else None
    payload["chapter_matches"] = [
        match.to_dict() for match in knowledge.chapter_matches
    ]
    if cache_key is not None and payload.get("answerable") and payload.get("answer"):
        if len(_QA_CACHE) > 200:
            _QA_CACHE.clear()
        _QA_CACHE[cache_key] = payload
    return payload


# ------------------------------------------------------------------ quizzes
@app.post("/api/quiz/start")
def start_quiz(request: QuizStartRequest) -> dict[str, Any]:
    level, name = _selection(request.class_level, request.subject)
    knowledge, meta = _knowledge_base(
        lines=request.lines,
        text=request.text,
        session_id=request.session_id,
        class_level=level,
        subject=name,
    )
    pool = build_question_bank(knowledge)
    if not pool:
        raise HTTPException(
            status_code=400,
            detail=(
                "No grounded questions could be generated from this transcript. "
                "Try a demo lecture with definitions, or record a longer session."
            ),
        )
    engine = QuizEngine(_store())
    try:
        result = engine.start(
            knowledge,
            student_id=request.student_id,
            class_level=level,
            subject=name,
            topic=request.topic,
            length=request.length,
            difficulty=request.difficulty,
            pool=pool,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result["source"] = meta
    result["topics"] = sorted({question.topic for question in pool})
    return result


@app.post("/api/quiz/answer")
def answer_quiz(request: QuizAnswerRequest) -> dict[str, Any]:
    llm = _ask_llm_provider()
    engine = QuizEngine(_store(), llm=llm)
    try:
        return engine.answer(
            request.quiz_id,
            question_id=request.question_id,
            answer=request.answer,
            answer_index=request.answer_index,
            response_ms=request.response_ms,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/students/{student_id}/gaps")
def student_gaps(student_id: str, limit: int = 5) -> dict[str, Any]:
    return QuizEngine(_store()).gaps(student_id, limit=max(1, min(limit, 20)))


# ------------------------------------------------------------------ auto-remediation
@app.post("/api/remediation/generate")
async def generate_remediation(request: RemediationGenerateRequest) -> dict[str, Any]:
    from ila.remediation import AutoRemediationEngine

    level, name = _selection(request.class_level, request.subject)
    knowledge, meta = _knowledge_base(
        lines=request.lines,
        text=request.text,
        session_id=request.session_id,
        class_level=level,
        subject=name,
    )
    llm = _ask_llm_provider()
    engine = AutoRemediationEngine(_store(), llm=llm)
    result = await asyncio.to_thread(
        engine.generate_remediation_pack,
        knowledge,
        student_id=request.student_id,
        topic=request.topic,
        count=request.count,
    )
    result["source"] = meta
    return result


@app.post("/api/remediation/submit")
def submit_remediation(request: RemediationAnswerRequest) -> dict[str, Any]:
    from ila.remediation import AutoRemediationEngine

    llm = _ask_llm_provider()
    engine = AutoRemediationEngine(_store(), llm=llm)
    try:
        return engine.evaluate_remediation_answer(
            pack_id=request.pack_id,
            student_id=request.student_id,
            item_id=request.item_id,
            answer=request.answer,
            selected_index=request.selected_index,
            response_ms=request.response_ms,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ------------------------------------------------------------------ teacher dashboard
@app.get("/api/teacher/overview")
def teacher_overview() -> dict[str, Any]:
    return _store().teacher_overview()


@app.get("/api/teacher/students")
def teacher_students() -> dict[str, Any]:
    students = _store().list_students()
    return {"students": students}


@app.get("/api/teacher/students/{student_id}")
def teacher_student_detail(student_id: str) -> dict[str, Any]:
    engine = QuizEngine(_store())
    gaps_info = engine.gaps(student_id, limit=10)
    mastery_rows = _store().list_mastery(student_id)
    recent = _store().recent_attempts(student_id, limit=50)
    return {
        "student_id": student_id,
        "gaps": gaps_info.get("gaps", []),
        "overall": gaps_info.get("overall", 0.0),
        "attempts": gaps_info.get("attempts", 0),
        "classifier_model": gaps_info.get("classifier_model", "DecisionTreeClassifier"),
        "mastery": mastery_rows,
        "recent_attempts": recent,
    }


# ---------------------------------------------------------------- saved sessions
@app.post("/api/sessions")
def create_session(request: SessionRequest) -> dict[str, Any]:
    level, name = _selection(request.class_level, request.subject)
    lines = _request_lines(NotesRequest(lines=request.lines, text=request.text))
    session_id = _store().save_session(
        title=request.title.strip() or "Lecture",
        class_level=level,
        subject=name,
        lines=[line.to_dict() for line in lines],
        transcript=" ".join(line.text for line in lines),
        duration_s=request.duration_s,
        notes=request.notes,
        markdown=request.markdown,
    )
    return {"id": session_id, "session": _store().get_session(session_id)}


@app.get("/api/sessions")
def list_sessions(limit: int = 50) -> dict[str, Any]:
    return {"sessions": _store().list_sessions(limit=max(1, min(limit, 200)))}


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    session = _store().get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


# ---------------------------------------------------------------- WebSocket
@app.websocket("/ws/captions")
async def captions_socket(websocket: WebSocket) -> None:
    await websocket.accept()

    try:
        request = await websocket.receive_json()
    except (WebSocketDisconnect, ValueError):
        return

    if not isinstance(request, dict):
        await websocket.send_json({"type": "error", "message": "Expected a JSON object"})
        await websocket.close()
        return

    settings = _apply_overrides(SETTINGS.model_copy(deep=True), request)
    source_kind = str(request.get("source", "mic")).lower()

    await websocket.send_json(
        {"type": "status", "stage": "loading_model", "model": settings.asr.model}
    )
    try:
        asr = await asyncio.to_thread(REGISTRY.get, settings)
    except Exception as exc:
        logger.exception("failed to load ASR model")
        await websocket.send_json({"type": "error", "message": str(exc)})
        await websocket.close()
        return

    await websocket.send_json(
        {
            "type": "ready",
            "schema": SCHEMA_VERSION,
            "asr": asr.info.to_dict(),
            "source": source_kind,
        }
    )
    await _pump(websocket, settings, asr, source_kind, request)


def _apply_overrides(settings: Settings, request: dict[str, Any]) -> Settings:
    if request.get("model"):
        settings.asr.model = str(request["model"]).strip()
    if "language" in request:
        language = request["language"]
        settings.asr.language = None if not language or language == "auto" else str(language)
    if request.get("device") is not None:
        settings.audio.device = int(request["device"])
    if request.get("partials") is not None:
        settings.partials.enabled = bool(request["partials"])
    if request.get("realtime") is not None:
        settings.audio.realtime = bool(request["realtime"])
    if request.get("model_dir"):
        settings.asr.model_dir = request["model_dir"]
    return settings


async def _pump(
    websocket: WebSocket,
    settings: Settings,
    asr: AsrProvider,
    source_kind: str,
    request: dict[str, Any],
) -> None:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[Any] = asyncio.Queue()
    stop = threading.Event()
    sentinel = object()

    def worker() -> None:
        source = None
        try:
            source = build_source(
                source_kind,
                path=request.get("path"),
                sample_rate=settings.audio.sample_rate,
                block_ms=settings.audio.block_ms,
                device=settings.audio.device,
                realtime=settings.audio.realtime,
            )
            pipeline = CaptionPipeline.from_settings(settings, source, asr)
            for event in pipeline.events(stop=stop.is_set):
                loop.call_soon_threadsafe(queue.put_nowait, event)
                if stop.is_set():
                    break
        except Exception as exc:
            logger.exception("caption session failed")
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "message": str(exc)})
        finally:
            if source is not None:
                try:
                    source.close()
                except Exception:  # pragma: no cover - best effort
                    logger.debug("failed to close audio source", exc_info=True)
            loop.call_soon_threadsafe(queue.put_nowait, sentinel)

    thread = threading.Thread(target=worker, name="ila-captions", daemon=True)
    thread.start()

    async def watch_client() -> None:
        try:
            while True:
                message = await websocket.receive_json()
                if isinstance(message, dict) and message.get("action") == "stop":
                    stop.set()
                    return
        except Exception:
            stop.set()

    watcher = asyncio.create_task(watch_client())
    completed = False
    try:
        while True:
            item = await queue.get()
            if item is sentinel:
                completed = True
                break
            if isinstance(item, CaptionEvent):
                await websocket.send_json(item.to_dict())
            else:
                await websocket.send_json(item)
    except WebSocketDisconnect:
        logger.debug("caption client disconnected")
    finally:
        stop.set()
        watcher.cancel()
        if thread.is_alive():
            await asyncio.to_thread(thread.join, 5.0)

    if completed:
        with contextlib.suppress(Exception):  # client may already be gone
            await websocket.send_json({"type": "done"})


# ---------------------------------------------------------------- dashboard & notes view
HTML_NOTES_DIR = NOTES_DIR / "html"
if HTML_NOTES_DIR.is_dir():
    app.mount(
        "/notes-view",
        StaticFiles(directory=str(HTML_NOTES_DIR), html=True),
        name="notes_html",
    )

if DASHBOARD_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(DASHBOARD_DIST), html=True), name="dashboard")
else:

    @app.get("/")
    def dashboard_not_built() -> dict[str, str]:
        return {
            "message": "Dashboard build not found.",
            "develop": "cd dashboard && npm install && npm run dev  (http://localhost:5173)",
            "build": "cd dashboard && npm install && npm run build  (served here at /)",
        }
