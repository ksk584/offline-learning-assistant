"""Offline syllabus retrieval and grounded question answering.

The roadmap calls for dense + lexical retrieval (MiniLM + FAISS + BM25). Those
libraries are excellent, but they are a poor fit for the project's constraint:
the whole product must run on a low-end, offline classroom PC. This module
therefore implements the same *shape* with the standard library only:

* **Lexical BM25** over sentence-sized passages (the ``BM25`` half).
* **Hashed lexical embeddings** -- word, bigram and character features projected
  into a fixed-size signed vector and compared with cosine similarity (the
  "dense" half, without a model download).
* **Fusion** of the two normalised scores, plus a small exact-phrase bonus.
* **Extractive answers** that quote the retrieved passage and always carry a
  citation. If no passage clears the confidence threshold the engine refuses to
  answer rather than guess.

The interfaces are deliberately small. A real MiniLM ONNX embedder can be
dropped in later without changing the Q&A or quiz code.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import time
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ila.curriculum import Chapter, Course, get_course, match_chapters
from ila.notes import TranscriptLine

if TYPE_CHECKING:  # pragma: no cover
    from ila.llm import LlmProvider

_WORD = re.compile(r"[a-z0-9][a-z0-9'\-]*")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_MARKDOWN = re.compile(r"[#*_`>]+")
_LATEX = re.compile(r"\$+[^$]*\$+")
_SPACE = re.compile(r"\s+")
#: Boilerplate from generated notes that reads like an answer but carries no fact.
_ANSWER_NOISE = re.compile(
    r"\b(?:correct approach|formula:|summary checklist|exam trap|practice drill|"
    r"answer key|learning objective|pedagogical|blueprint|syllabus scope)\b",
    re.IGNORECASE,
)
_CONDITIONAL = re.compile(r"^(?:if|when|whenever|suppose|assume|unless)\b", re.IGNORECASE)

STOPWORDS = frozenset(
    """
    a about above after again against all also am an and any are as at be because been before
    being below between both but by can could did do does doing down during each few for from
    further had has have having he her here him his how i if in into is it its itself just me
    more most my no nor not of off on once only or other our out over own same she should so
    some such than that the their them then there these they this those through to too under
    until up very was we were what when where which while who whom why will with would you your
    """.split()  # noqa: SIM905 - a word list reads better than a long literal
)

#: Words that never help a retrieval query or a generated answer.
META_WORDS = frozenset(
    """
    according ask answer chapter class describe discuss explain give lecture mention professor
    question say says speak teacher tell topic define definition meaning
    """.split()  # noqa: SIM905
)


def stem(token: str) -> str:
    """A deliberately small stemmer (enough for English lecture text)."""
    if len(token) > 5 and token.endswith("ies"):
        return token[:-3] + "y"
    for suffix in ("ing", "edly", "ed", "es", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            base = token[: -len(suffix)]
            if len(base) > 3 and base[-1] == base[-2]:
                base = base[:-1]
            return base
    return token


def tokenize(text: str, *, keep_stopwords: bool = False) -> list[str]:
    tokens = _WORD.findall(text.lower())
    if keep_stopwords:
        return tokens
    return [stem(token) for token in tokens if token not in STOPWORDS and len(token) > 1]


def content_terms(text: str) -> set[str]:
    return {token for token in tokenize(text) if token not in META_WORDS}


def clean_markdown(text: str) -> str:
    """Flatten Markdown/LaTeX enough for retrieval and question generation."""
    text = _LATEX.sub(" ", text)
    text = _MARKDOWN.sub(" ", text)
    text = text.replace("\\", " ").replace("|", " ")
    return _SPACE.sub(" ", text).strip()


# --------------------------------------------------------------------- passages
@dataclass(frozen=True, slots=True)
class Passage:
    """A retrievable chunk with enough provenance to cite it."""

    id: str
    text: str
    source: str  # "lecture" | "notes" | "syllabus"
    title: str
    chapter_number: int | None = None
    chapter_title: str | None = None
    start: float | None = None
    end: float | None = None
    keywords: tuple[str, ...] = ()

    @property
    def is_content(self) -> bool:
        """Syllabus cards are useful for citations, not for quiz generation."""
        return self.source in {"lecture", "notes", "textbook"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "source": self.source,
            "title": self.title,
            "chapter_number": self.chapter_number,
            "chapter_title": self.chapter_title,
            "start": self.start,
            "end": self.end,
            "keywords": list(self.keywords),
        }


def chunk_text(
    text: str,
    *,
    max_chars: int = 900,
    overlap_chars: int = 120,
) -> list[str]:
    """Split text into overlapping, sentence-aware chunks."""
    text = clean_markdown(text)
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    sentences = [part.strip() for part in _SENTENCE_END.split(text) if part.strip()]
    if not sentences:
        sentences = [text]

    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for sentence in sentences:
        if current and size + len(sentence) + 1 > max_chars:
            chunks.append(" ".join(current))
            # Keep a small tail so a definition split across chunks is still findable.
            tail: list[str] = []
            tail_size = 0
            for previous in reversed(current):
                if tail_size + len(previous) > overlap_chars:
                    break
                tail.insert(0, previous)
                tail_size += len(previous) + 1
            current = tail
            size = tail_size
        current.append(sentence)
        size += len(sentence) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


def _notes_files(notes_dir: Path) -> dict[int, Path]:
    """Generated master notes currently cover Class 10 Maths Units 1-3."""
    return {
        1: notes_dir / "Unit_1_Real_Numbers_Notes.md",
        2: notes_dir / "Unit_2_Polynomials_Notes.md",
        3: notes_dir / "Unit_3_Pair_of_Linear_Equations_Notes.md",
    }


# ------------------------------------------------------------------ knowledge base
@dataclass(slots=True)
class KnowledgeBase:
    """All sources the Q&A and quiz engines may cite."""

    course: Course | None
    passages: tuple[Passage, ...]
    transcript: str = ""
    title: str = "Lecture"
    source_kind: str = "transcript"
    demo_id: str | None = None
    chapter_matches: tuple[Any, ...] = ()
    _bm25: BM25 | None = field(default=None, init=False, repr=False)
    _embeddings: list[dict[int, float]] = field(default_factory=list, init=False, repr=False)

    @classmethod
    def from_lines(
        cls,
        lines: Sequence[TranscriptLine],
        class_level: int,
        subject: str,
        *,
        title: str = "Lecture",
        source_kind: str = "transcript",
        demo_id: str | None = None,
        chapter_hint: int | None = None,
        include_syllabus: bool = True,
        include_notes: bool = True,
        notes_dir: Path | None = None,
    ) -> KnowledgeBase:
        course = get_course(class_level, subject)
        transcript = " ".join(line.text for line in lines if line.text).strip()
        matches = tuple(match_chapters(transcript, course, limit=4)) if transcript else ()
        hinted = course.chapter(chapter_hint) if chapter_hint else None
        global_chapter = hinted
        if global_chapter is None and matches:
            top = matches[0]
            runner_up = matches[1].score if len(matches) > 1 else 0.0
            if len(matches) == 1 or top.score >= 1.8 * max(1.0, runner_up):
                global_chapter = top.chapter

        passages: list[Passage] = []
        for index, line in enumerate(lines):
            text = line.text.strip()
            if not text:
                continue
            chapter = hinted
            if chapter is None:
                line_matches = match_chapters(text, course, limit=1, min_score=1.5)
                chapter = line_matches[0].chapter if line_matches else global_chapter
            passages.append(
                Passage(
                    id=f"lecture-{index}",
                    text=text,
                    source="lecture",
                    title=title,
                    chapter_number=chapter.number if chapter else None,
                    chapter_title=chapter.title if chapter else None,
                    start=line.start,
                    end=line.end,
                    keywords=chapter.keywords if chapter else (),
                )
            )

        if include_notes:
            passages.extend(
                _notes_passages(course, notes_dir or _default_notes_dir())
            )
            passages.extend(_textbook_passages(course))

        if include_syllabus:
            for chapter in course.chapters:
                keywords = ", ".join(chapter.keywords[:12])
                passages.append(
                    Passage(
                        id=f"syllabus-{chapter.number}",
                        text=(
                            f"Chapter {chapter.number}: {chapter.title}. "
                            f"NCERT key terms: {keywords}."
                        ),
                        source="syllabus",
                        title=f"Chapter {chapter.number}: {chapter.title}",
                        chapter_number=chapter.number,
                        chapter_title=chapter.title,
                        keywords=chapter.keywords,
                    )
                )

        return cls(
            course=course,
            passages=tuple(passages),
            transcript=transcript,
            title=title,
            source_kind=source_kind,
            demo_id=demo_id,
            chapter_matches=matches,
        )

    # ------------------------------------------------------------- index building
    def _ensure_index(self) -> None:
        if self._bm25 is not None:
            return
        self._bm25 = BM25([tokenize(passage.text) for passage in self.passages])
        self._embeddings = [hashed_embedding(passage.text) for passage in self.passages]

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        min_score: float = 0.0,
        content_only: bool = False,
    ) -> list[RetrievedPassage]:
        self._ensure_index()
        assert self._bm25 is not None
        terms = tokenize(query)
        if not terms:
            return []

        lexical = self._bm25.scores(terms)
        query_vector = hashed_embedding(query)
        dense = [
            cosine(query_vector, vector) if query_vector and vector else 0.0
            for vector in self._embeddings
        ]

        max_lexical = max(lexical, default=0.0) or 1.0
        query_lower = " ".join(_WORD.findall(query.lower()))
        results: list[RetrievedPassage] = []
        for index, passage in enumerate(self.passages):
            if content_only and not passage.is_content:
                continue
            lexical_norm = lexical[index] / max_lexical
            coverage = len(set(terms) & content_terms(passage.text)) / max(1, len(set(terms)))
            # Hashed vectors can collide; without a shared word the match is noise.
            if lexical[index] == 0.0 and coverage == 0.0:
                continue
            dense_score = max(0.0, dense[index])
            score = 0.58 * lexical_norm + 0.42 * dense_score

            # Exact phrase / term coverage is a strong precision signal.
            score += 0.10 * coverage
            if query_lower and len(query_lower) > 8 and f" {query_lower} " in (
                f" {clean_markdown(passage.text).lower()} "
            ):
                score += 0.12
            if passage.source == "syllabus":
                score *= 0.72
            if passage.source == "notes":
                score *= 0.96

            if score >= min_score:
                results.append(RetrievedPassage(passage=passage, score=round(score, 6)))

        results.sort(key=lambda item: (-item.score, item.passage.id))
        return results[:top_k]

    def covered_chapters(self) -> list[Chapter]:
        seen: dict[int, Chapter] = {}
        for passage in self.passages:
            if passage.chapter_number is None or not self.course:
                continue
            chapter = self.course.chapter(passage.chapter_number)
            if chapter is not None:
                seen.setdefault(chapter.number, chapter)
        return [seen[number] for number in sorted(seen)]


@dataclass(frozen=True, slots=True)
class RetrievedPassage:
    passage: Passage
    score: float

    def citation(self, *, snippet_chars: int = 320) -> dict[str, Any]:
        snippet = self.passage.text.strip()
        if len(snippet) > snippet_chars:
            snippet = snippet[:snippet_chars].rsplit(" ", 1)[0] + "…"
        return {
            "id": self.passage.id,
            "source": self.passage.source,
            "title": self.passage.title,
            "chapter_number": self.passage.chapter_number,
            "chapter_title": self.passage.chapter_title,
            "start": self.passage.start,
            "end": self.passage.end,
            "score": round(self.score, 4),
            "snippet": snippet,
        }


def _default_notes_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "notes"


def _notes_passages(course: Course, notes_dir: Path) -> list[Passage]:
    if course.class_level != 10 or course.subject != "maths":
        return []
    passages: list[Passage] = []
    for chapter_number, path in _notes_files(notes_dir).items():
        if not path.is_file():
            continue
        chapter = course.chapter(chapter_number)
        raw = path.read_text(encoding="utf-8", errors="replace")
        title = f"Unit {chapter_number}: {chapter.title if chapter else path.stem}"
        for index, chunk in enumerate(chunk_text(raw)):
            passages.append(
                Passage(
                    id=f"notes-{chapter_number}-{index}",
                    text=chunk,
                    source="notes",
                    title=title,
                    chapter_number=chapter_number,
                    chapter_title=chapter.title if chapter else None,
                    keywords=chapter.keywords if chapter else (),
                )
            )
    return passages


_TEXTBOOK_CACHE: list[Passage] | None = None


def _textbook_passages(course: Course) -> list[Passage]:
    """Load and chunk passages directly from all 14 Class 10 NCERT Math textbook PDFs."""
    global _TEXTBOOK_CACHE
    if course.class_level != 10 or course.subject != "maths":
        return []
    if _TEXTBOOK_CACHE is not None:
        return _TEXTBOOK_CACHE

    json_path = (
        Path(__file__).resolve().parents[2]
        / "ncert_books"
        / "extracted_math_textbooks.json"
    )
    if not json_path.is_file():
        return []

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logging.getLogger(__name__).warning("Could not read extracted math textbooks: %s", exc)
        return []

    passages: list[Passage] = []
    for ch_str, info in data.items():
        ch_num = int(ch_str)
        chapter = course.chapter(ch_num)
        ch_title = chapter.title if chapter else info.get("title", f"Chapter {ch_num}")
        keywords = chapter.keywords if chapter else tuple(info.get("keywords", ()))
        for p in info.get("pages", []):
            page_num = p.get("page_number", 1)
            raw = p.get("text", "")
            if not raw.strip():
                continue
            for chunk_idx, chunk in enumerate(chunk_text(raw, max_chars=750, overlap_chars=120)):
                passages.append(
                    Passage(
                        id=f"textbook-{ch_num}-p{page_num}-{chunk_idx}",
                        text=chunk,
                        source="textbook",
                        title=f"NCERT Class 10 Mathematics · Chapter {ch_num}: {ch_title} (Page {page_num})",
                        chapter_number=ch_num,
                        chapter_title=ch_title,
                        keywords=keywords,
                    )
                )
    _TEXTBOOK_CACHE = passages
    return passages


# ------------------------------------------------------------------------- BM25
class BM25:
    """Standard Okapi BM25 over a fixed corpus of token lists."""

    def __init__(self, documents: Sequence[Sequence[str]], *, k1: float = 1.4, b: float = 0.72):
        self.documents = [list(document) for document in documents]
        self.k1 = k1
        self.b = b
        self.lengths = [len(document) for document in self.documents]
        self.avg_length = (sum(self.lengths) / len(self.lengths)) if self.lengths else 0.0
        self.term_frequencies = [Counter(document) for document in self.documents]
        document_frequency: Counter[str] = Counter()
        for frequencies in self.term_frequencies:
            document_frequency.update(frequencies.keys())
        total = len(self.documents)
        self.idf = {
            term: math.log(1.0 + (total - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def scores(self, query_terms: Iterable[str]) -> list[float]:
        query = Counter(query_terms)
        results = [0.0] * len(self.documents)
        for index, frequencies in enumerate(self.term_frequencies):
            length = self.lengths[index] or 1
            score = 0.0
            for term, query_frequency in query.items():
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                idf = self.idf.get(term, 0.0)
                denominator = frequency + self.k1 * (
                    1.0 - self.b + self.b * length / (self.avg_length or 1.0)
                )
                score += idf * (frequency * (self.k1 + 1.0) / denominator) * query_frequency
            results[index] = score
        return results


# ------------------------------------------------------------- hashed embeddings
EMBEDDING_DIM = 384


def _hash_feature(feature: str) -> tuple[int, float]:
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
    value = int.from_bytes(digest, "big")
    index = value % EMBEDDING_DIM
    sign = 1.0 if (value >> 63) & 1 else -1.0
    return index, sign


def hashed_embedding(text: str) -> dict[int, float]:
    """Signed feature hashing over words, bigrams and character trigrams."""
    tokens = tokenize(text)
    if not tokens:
        return {}
    features: Counter[str] = Counter()
    for token in tokens:
        features[f"w:{token}"] += 1.0
    for first, second in zip(tokens, tokens[1:], strict=False):
        features[f"b:{first}_{second}"] += 0.6
    for token in tokens:
        if len(token) >= 5:
            for start in range(len(token) - 2):
                features[f"c:{token[start:start + 3]}"] += 0.18

    vector: dict[int, float] = {}
    for feature, weight in features.items():
        index, sign = _hash_feature(feature)
        vector[index] = vector.get(index, 0.0) + sign * (1.0 + math.log(weight))
    norm = math.sqrt(sum(value * value for value in vector.values()))
    if norm:
        vector = {index: value / norm for index, value in vector.items()}
    return vector


def cosine(left: dict[int, float], right: dict[int, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(index, 0.0) for index, value in left.items())


# ------------------------------------------------------------------------ answer
@dataclass(frozen=True, slots=True)
class Answer:
    question: str
    answer: str
    answerable: bool
    confidence: float
    citations: tuple[dict[str, Any], ...]
    topics: tuple[dict[str, Any], ...]
    engine: str = "extractive"
    latency_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "answerable": self.answerable,
            "confidence": round(self.confidence, 3),
            "citations": list(self.citations),
            "topics": list(self.topics),
            "engine": self.engine,
            "latency_s": round(self.latency_s, 3),
        }


class AnswerEngine:
    """Retrieve-then-quote Q&A with a hard "no source, no answer" rule."""

    def __init__(
        self,
        knowledge: KnowledgeBase,
        *,
        min_score: float = 0.16,
        top_k: int = 5,
        llm: LlmProvider | None = None,
    ) -> None:
        self.knowledge = knowledge
        self.min_score = min_score
        self.top_k = top_k
        self.llm = llm

    def ask(self, question: str, *, use_llm: bool = False) -> Answer:
        started = time.perf_counter()
        question = question.strip()
        if not question:
            return Answer(
                question=question,
                answer="Ask a question about the lecture or the selected NCERT chapter.",
                answerable=False,
                confidence=0.0,
                citations=(),
                topics=(),
                latency_s=time.perf_counter() - started,
            )

        retrieved = self.knowledge.search(
            question,
            top_k=self.top_k,
            min_score=self.min_score,
            content_only=True,
        )
        if not retrieved:
            return Answer(
                question=question,
                answer=(
                    "I could not find a passage above the confidence threshold in the "
                    "lecture transcript or the selected NCERT sources. Try rephrasing the "
                    "question, or record a lecture that covers this topic."
                ),
                answerable=False,
                confidence=0.0,
                citations=(),
                topics=(),
                latency_s=time.perf_counter() - started,
            )

        top = retrieved[0]
        answer_text = _extract_answer(question, retrieved)
        engine = "extractive"
        if use_llm and self.llm is not None:
            composed = _llm_answer(self.llm, question, retrieved)
            if composed:
                answer_text = composed
                engine = "llm+verified"

        citations = tuple(item.citation() for item in retrieved[:3])
        topics = _topics(retrieved, self.knowledge)
        confidence = _confidence(top.score, len(retrieved))
        return Answer(
            question=question,
            answer=answer_text,
            answerable=True,
            confidence=confidence,
            citations=citations,
            topics=topics,
            engine=engine,
            latency_s=time.perf_counter() - started,
        )


def _extract_answer(question: str, retrieved: Sequence[RetrievedPassage]) -> str:
    terms = content_terms(question)
    focus = _focus_phrase(question)
    focus_terms = content_terms(focus) if focus else set()
    best_sentences: list[tuple[float, str, bool]] = []
    for rank, item in enumerate(retrieved):
        sentences = [part.strip() for part in _SENTENCE_END.split(item.passage.text)]
        for index, sentence in enumerate(sentences):
            if len(sentence) < 12:
                continue
            lowered = sentence.lower()
            if (
                "key terms:" in lowered
                or lowered.startswith(("unit ", "section ", "chapter "))
                or _ANSWER_NOISE.search(sentence)
            ):
                continue
            sentence_terms = content_terms(sentence)
            overlap = len(terms & sentence_terms)
            if not overlap:
                continue
            score = overlap / max(1, len(terms))
            score += 0.08 / (1 + index)
            score += 0.05 / (1 + rank)
            is_definition = False
            if focus:
                definition = _definition_pattern(lowered, focus.lower())
                if definition:
                    is_definition = True
                    score += definition
                if focus_terms and focus_terms <= sentence_terms:
                    score += 0.18
            if item.passage.source == "lecture":
                score += 0.04
            if item.passage.chapter_title and any(
                term in content_terms(item.passage.chapter_title) for term in terms
            ):
                score += 0.05
            best_sentences.append((score, sentence, is_definition))

    if not best_sentences:
        # Fall back to the retrieved passage itself; it already cleared the gate.
        text = retrieved[0].passage.text
        return text if len(text) <= 420 else text[:420].rsplit(" ", 1)[0] + "…"

    best_sentences.sort(key=lambda pair: (-pair[0], len(pair[1])))
    first_score, first_sentence, first_is_definition = best_sentences[0]
    if first_is_definition and len(first_sentence) >= 60 and first_score >= 0.5:
        return first_sentence

    chosen: list[str] = []
    seen: set[str] = set()
    for _, sentence, _ in best_sentences:
        key = sentence.lower()
        if key in seen:
            continue
        seen.add(key)
        chosen.append(sentence)
        if sum(len(item) for item in chosen) >= 360 or len(chosen) >= 2:
            break
    return " ".join(chosen)


def _definition_pattern(sentence: str, focus: str) -> float:
    """How strongly does this sentence define the question's focus phrase?"""
    word = re.escape(focus)
    stripped = re.sub(r"^(?:the|a|an)\s+", "", sentence.strip(), flags=re.I)
    is_conditional = bool(_CONDITIONAL.match(sentence.strip()))
    starts_with_focus = bool(re.match(rf"{word}\b", stripped, re.IGNORECASE))
    defines_forward = bool(
        re.search(rf"\b{word}\b\s+(?:is|are|means|refers to)\b", sentence, re.IGNORECASE)
    )
    defines_reverse = bool(
        re.search(
            rf"\b(?:is|are|means)\s+(?:called|known as)\s+(?:the\s+|a\s+|an\s+)?\b{word}\b",
            sentence,
            re.IGNORECASE,
        )
    )
    defines_article = bool(
        re.search(rf"\b(?:is|are)\s+(?:a|an|the)\s+{word}\b", sentence, re.IGNORECASE)
    )
    if is_conditional:
        return 0.0
    if starts_with_focus and defines_forward:
        return 0.55
    if defines_reverse:
        return 0.42
    if defines_article:
        return 0.20
    if defines_forward:
        return 0.12
    if re.search(rf"\b{word}\b", sentence, re.IGNORECASE):
        return 0.05
    return 0.0


def _focus_phrase(question: str) -> str | None:
    patterns = (
        r"\b(?:what|which)\s+(?:is|are|does|do)\s+(?:the\s+|a\s+|an\s+)?(?P<term>[^?]+)",
        r"\bdefine\s+(?P<term>[^?]+)",
        r"\bexplain\s+(?P<term>[^?]+)",
        r"\bmeaning\s+of\s+(?P<term>[^?]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            term = match.group("term").strip(" .,:;")
            if term:
                return term
    return None


def _topics(
    retrieved: Sequence[RetrievedPassage], knowledge: KnowledgeBase
) -> tuple[dict[str, Any], ...]:
    topics: dict[int, dict[str, Any]] = {}
    for item in retrieved:
        chapter = item.passage.chapter_number
        if chapter is None:
            continue
        topics.setdefault(
            chapter,
            {
                "chapter_number": chapter,
                "chapter_title": item.passage.chapter_title,
                "score": round(item.score, 4),
            },
        )
    if not topics and knowledge.chapter_matches:
        match = knowledge.chapter_matches[0]
        topics[match.chapter.number] = {
            "chapter_number": match.chapter.number,
            "chapter_title": match.chapter.title,
            "score": round(match.score, 4),
        }
    return tuple(topics[number] for number in list(topics)[:3])


def _confidence(score: float, result_count: int) -> float:
    # Scores are not probabilities; this is a conservative UI confidence.
    base = min(1.0, score / 0.55)
    if result_count >= 3:
        base = min(1.0, base + 0.05)
    return round(max(0.0, base), 3)


def _llm_answer(
    llm: LlmProvider,
    question: str,
    retrieved: Sequence[RetrievedPassage],
) -> str | None:
    """Optional local rewrite. Verified against the excerpts before use."""
    excerpts = "\n".join(
        f"[{index + 1}] {item.passage.text[:700]}"
        for index, item in enumerate(retrieved[:3])
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are a careful NCERT tutor. Answer only from the numbered excerpts. "
                "Do not add facts, formulas or examples that are not present. Keep the "
                "answer to two short sentences and do not mention the excerpts."
            ),
        },
        {
            "role": "user",
            "content": f"Question: {question}\n\nExcerpts:\n{excerpts}\n\nAnswer:",
        },
    ]
    try:
        if not llm.available:
            return None
        reply = llm.complete(messages, max_tokens=180, temperature=0.1).strip()
    except Exception:
        return None
    if not reply or len(reply) > 700:
        return None
    evidence = content_terms(" ".join(item.passage.text for item in retrieved))
    claim_terms = content_terms(reply)
    if not claim_terms:
        return None
    supported = len(claim_terms & evidence) / len(claim_terms)
    return reply if supported >= 0.55 else None
