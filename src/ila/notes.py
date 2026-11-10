"""Grounded note generation from a lecture transcript.

Pipeline
--------
1. **Extract** -- sentences are scored with TextRank (TF-IDF cosine + PageRank)
   and the most informative, non-redundant ones are kept. This runs with no
   model and is the guaranteed baseline.
2. **Rewrite** -- a small local GGUF model receives only those sentences, in
   chunks that fit comfortably in a 4k context, and returns a summary, key
   points and term definitions.
3. **Verify** -- every generated line must share its content words with the
   transcript evidence; unsupported lines are dropped and counted. The result
   is "fewer notes", never invented ones.
4. **Fallback** -- if no model is installed, the runtime is missing, or the
   time budget runs out, the extractive sentences are returned verbatim with
   their timestamps.

Nothing here touches the network. Model loading lives behind :class:`LlmProvider`.
"""

from __future__ import annotations

import logging
import math
import re
import time
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ila.config import LlmSettings
from ila.events import CaptionEvent
from ila.llm import LlmProvider, create_llm
from ila.text import normalize_transcript

if TYPE_CHECKING:  # pragma: no cover
    from ila.curriculum import SyllabusContext

logger = logging.getLogger(__name__)

_WORD = re.compile(r"[a-z0-9][a-z0-9'\-]*")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_DEFINITION = re.compile(
    r"^(?P<term>[A-Za-z][\w\s\-]{1,48}?)\s+"
    r"(?:is|are|means|refers to|is defined as|are defined as|is called|are called)\s+"
    r"(?P<body>.{12,})$",
    re.IGNORECASE,
)
_BULLET = re.compile(r"^\s*(?:[-*\u2022]|\d+[.)])\s+(?P<text>.*\S)\s*$")
_SUMMARY = re.compile(r"^\W*summary\W*:?\s*(?P<text>.+)$", re.IGNORECASE)
_POINTS_HEADER = re.compile(r"^\W*(?:key\s+)?(?:points?|notes?)\W*:?\s*$", re.IGNORECASE)
_TERMS_HEADER = re.compile(r"^\W*(?:key\s+)?(?:terms?|definitions?)\W*:?\s*$", re.IGNORECASE)
_FENCE = re.compile(r"^```[a-zA-Z]*\s*$")
_REFUSAL = re.compile(
    r"\b(?:as an ai|i cannot|i can't|i am unable|i'm sorry|here (?:is|are) (?:a|the|your)|"
    r"sure[,!]|certainly[,!])\b",
    re.IGNORECASE,
)

STOPWORDS = frozenset(
    """
    a about above after again against all also am an and any are aren't as at be because been
    before being below between both but by can can't cannot could couldn't did didn't do does
    doesn't doing don't down during each few for from further had hadn't has hasn't have haven't
    having he her here hers herself him himself his how i if in into is isn't it it's its itself
    just let's me more most mustn't my myself no nor not of off on once only or other ought our
    ours ourselves out over own same shan't she should shouldn't so some such than that that's the
    their theirs them themselves then there there's these they they're this those through to too
    under until up very was wasn't we were weren't what what's when where which while who whom why
    will with won't would wouldn't you your yours yourself yourselves
    """.split()  # noqa: SIM905 - a word list reads better than a 150-item literal
)

#: Tokens that carry meaning in a generated sentence but never prove grounding.
_META_WORDS = frozenset(
    """
    summary summarize summarises summarising point points key idea ideas term terms lecture
    professor teacher speaker instructor explain explains explained discussing discuss
    discusses mentioned mentions covers cover covered talk talks talked topic topics
    """.split()  # noqa: SIM905
)


# --------------------------------------------------------------------------- input
@dataclass(frozen=True, slots=True)
class TranscriptLine:
    """One finalized caption or transcript paragraph."""

    text: str
    start: float | None = None
    end: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "start": self.start, "end": self.end}


def lines_from_events(events: Iterable[CaptionEvent]) -> list[TranscriptLine]:
    """Keep only finalized captions -- partials are previews, not content."""
    lines: list[TranscriptLine] = []
    for event in events:
        if not event.final:
            continue
        text = normalize_transcript(event.text)
        if text:
            lines.append(TranscriptLine(text=text, start=event.start, end=event.end))
    return lines


def lines_from_text(text: str) -> list[TranscriptLine]:
    """Split a plain transcript into paragraph-ish lines, keeping no timestamps."""
    chunks = [normalize_transcript(part) for part in re.split(r"\n\s*\n|\r\n\s*\r\n", text)]
    lines = [TranscriptLine(text=chunk) for chunk in chunks if chunk]
    if lines:
        return lines
    whole = normalize_transcript(text)
    return [TranscriptLine(text=whole)] if whole else []


@dataclass(frozen=True, slots=True)
class Sentence:
    text: str
    start: float | None
    order: int


def split_sentences(lines: Sequence[TranscriptLine]) -> list[Sentence]:
    sentences: list[Sentence] = []
    for line in lines:
        for part in _SENTENCE_END.split(line.text):
            text = part.strip()
            if len(text) < 8:
                continue
            sentences.append(Sentence(text=text, start=line.start, order=len(sentences)))
    return sentences


# ----------------------------------------------------------------------- tokenizing
def words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def content_tokens(text: str) -> list[str]:
    """Meaning-bearing tokens used for similarity, ranking and grounding."""
    return [token for token in words(text) if token not in STOPWORDS and len(token) > 2]


def _stem(token: str) -> str:
    """Crude suffix stripping so paraphrase variants still match.

    The verifier compares vocabulary, not vectors; without this, "document" and
    "documents" (or "vector" and "vectors") count as different evidence and a
    perfectly good definition gets dropped. Applied to both sides of every
    comparison, so consistency matters more than linguistic accuracy.
    """
    if len(token) > 5 and token.endswith("ies"):
        return token[:-3] + "y"
    for suffix in ("ing", "ed", "es", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            base = token[: -len(suffix)]
            if len(base) > 3 and base[-1] == base[-2]:
                base = base[:-1]
            return base
    return token


def _evidence_tokens(text: str) -> set[str]:
    return {
        _stem(token)
        for token in content_tokens(text)
        if token not in _META_WORDS
    }


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


# ------------------------------------------------------------------------ TextRank
def _vectors(sentences: Sequence[Sentence]) -> tuple[list[dict[str, float]], dict[str, float]]:
    token_lists = [content_tokens(sentence.text) for sentence in sentences]
    document_frequency: Counter[str] = Counter()
    for tokens in token_lists:
        document_frequency.update(set(tokens))

    total = max(1, len(sentences))
    idf = {
        token: math.log((total + 1) / (count + 1)) + 1.0
        for token, count in document_frequency.items()
    }

    vectors: list[dict[str, float]] = []
    for tokens in token_lists:
        counts = Counter(tokens)
        vector = {
            token: (1.0 + math.log(count)) * idf.get(token, 1.0)
            for token, count in counts.items()
        }
        norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
        vectors.append({token: value / norm for token, value in vector.items()})
    return vectors, idf


def textrank(
    sentences: Sequence[Sentence], *, damping: float = 0.85, iterations: int = 30
) -> list[float]:
    """PageRank over sentence-similarity edges, with a mild position prior."""
    count = len(sentences)
    if count == 0:
        return []
    if count == 1:
        return [1.0]

    vectors, _ = _vectors(sentences)
    similarity = [[0.0] * count for _ in range(count)]
    for i in range(count):
        for j in range(i + 1, count):
            # Vectors are L2-normalized, so the dot product is cosine similarity.
            score = sum(value * vectors[j].get(token, 0.0) for token, value in vectors[i].items())
            similarity[i][j] = similarity[j][i] = max(0.0, score)

    scores = [1.0 / count] * count
    for _ in range(iterations):
        updated = [(1.0 - damping) / count] * count
        for i in range(count):
            total = sum(similarity[i])
            if total <= 0.0:
                continue
            weight = damping * scores[i] / total
            for j in range(count):
                if similarity[i][j] > 0.0:
                    updated[j] += weight * similarity[i][j]
        scores = updated

    # Lectures start with framing and definitions; nudge the opening sentences.
    for index in range(count):
        scores[index] *= 1.0 + 0.25 * math.exp(-index / 6.0)
    return scores


def select_sentences(
    sentences: Sequence[Sentence],
    *,
    limit: int,
    redundancy: float = 0.65,
) -> list[Sentence]:
    """Top-ranked sentences without near-duplicates, in lecture order."""
    scores = textrank(sentences)
    ranked = sorted(range(len(sentences)), key=lambda index: scores[index], reverse=True)
    token_sets = [set(content_tokens(sentence.text)) for sentence in sentences]

    chosen: list[int] = []
    for index in ranked:
        if len(chosen) >= limit:
            break
        if len(token_sets[index]) < 3:
            continue
        if any(_jaccard(token_sets[index], token_sets[other]) >= redundancy for other in chosen):
            continue
        chosen.append(index)

    return [sentences[index] for index in sorted(chosen)]


def desired_sentence_count(total: int) -> int:
    """How much of a lecture the model should see: enough to matter, small enough to run."""
    if total <= 6:
        return total
    return min(28, max(6, round(total * 0.18)))


# ------------------------------------------------------------------------ keywords
def extract_keywords(sentences: Sequence[Sentence], *, limit: int = 12) -> list[str]:
    token_lists = [content_tokens(sentence.text) for sentence in sentences]
    document_frequency: Counter[str] = Counter()
    term_frequency: Counter[str] = Counter()
    for tokens in token_lists:
        document_frequency.update(set(tokens))
        term_frequency.update(tokens)

    total = max(1, len(token_lists))
    min_count = 2 if len(token_lists) >= 8 else 1
    scored: list[tuple[float, str]] = []
    for token, count in term_frequency.items():
        if count < min_count:
            continue
        idf = math.log((total + 1) / (document_frequency[token] + 1)) + 1.0
        scored.append((count * idf, token))
    scored.sort(key=lambda item: (-item[0], item[1]))

    keywords = [token for _, token in scored[:limit]]

    bigrams: Counter[str] = Counter()
    for tokens in token_lists:
        for left, right in zip(tokens, tokens[1:], strict=False):
            if len(left) > 3 and len(right) > 3:
                bigrams[f"{left} {right}"] += 1
    for phrase, count in bigrams.most_common(3):
        if count >= 2 and len(keywords) < limit + 2:
            keywords.append(phrase)
    return keywords


# -------------------------------------------------------------------- definitions
def find_definitions(sentences: Sequence[Sentence], *, limit: int = 6) -> list[Definition]:
    found: list[Definition] = []
    seen: set[str] = set()
    for sentence in sentences:
        match = _DEFINITION.match(sentence.text)
        if not match:
            continue
        term = " ".join(content_tokens(match.group("term"))[:4]).strip()
        if not term or term in seen:
            continue
        seen.add(term)
        found.append(Definition(term=term, text=sentence.text, start=sentence.start))
        if len(found) >= limit:
            break
    return found


# --------------------------------------------------------------------------- notes
@dataclass(frozen=True, slots=True)
class NotePoint:
    text: str
    start: float | None = None
    source: str = "extractive"

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "start": self.start, "source": self.source}


@dataclass(frozen=True, slots=True)
class Definition:
    term: str
    text: str
    start: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"term": self.term, "text": self.text, "start": self.start}


@dataclass(slots=True)
class NoteResult:
    title: str
    summary: str
    points: list[NotePoint] = field(default_factory=list)
    definitions: list[Definition] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    used_llm: bool = False
    profile: str = "none"
    model: str | None = None
    dropped: int = 0
    latency_s: float = 0.0
    fallback_reason: str | None = None
    sentences: int = 0
    #: Serialized :class:`ila.curriculum.SyllabusContext`, when requested.
    curriculum: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "points": [point.to_dict() for point in self.points],
            "definitions": [item.to_dict() for item in self.definitions],
            "keywords": self.keywords,
            "used_llm": self.used_llm,
            "profile": self.profile,
            "model": self.model,
            "dropped": self.dropped,
            "latency_s": round(self.latency_s, 2),
            "fallback_reason": self.fallback_reason,
            "sentences": self.sentences,
            "curriculum": self.curriculum,
        }

    def to_markdown(self) -> str:
        lines = [f"# {self.title}", "", "## Summary", "", self.summary, ""]
        if self.points:
            lines += ["## Key points", ""]
            for point in self.points:
                stamp = f"`{format_timestamp(point.start)}` " if point.start is not None else ""
                lines.append(f"- {stamp}{point.text}")
            lines.append("")
        if self.definitions:
            lines += ["## Terms", ""]
            for item in self.definitions:
                lines.append(f"- **{item.term}** - {item.text}")
            lines.append("")
        if self.curriculum and self.curriculum.get("matches"):
            lines += ["## Syllabus alignment", ""]
            course = str(self.curriculum.get("course", "NCERT"))
            for match in self.curriculum["matches"]:
                terms = ", ".join(match.get("matched_terms", [])[:6])
                suffix = f" - matched: {terms}" if terms else ""
                lines.append(
                    f"- **{course}** - Chapter {match['number']}: {match['title']}{suffix}"
                )
            lines.append("")
        if self.keywords:
            lines += ["## Keywords", "", ", ".join(f"`{word}`" for word in self.keywords), ""]

        engine = (
            f"local model `{self.model}` ({self.profile})"
            if self.used_llm
            else "extractive fallback (TextRank only)"
        )
        lines.append("---")
        lines.append(
            f"Generated on-device with {engine} from {self.sentences} transcript sentences "
            f"in {self.latency_s:.1f}s."
        )
        if self.dropped:
            lines.append(
                f"{self.dropped} generated line(s) were dropped because the transcript "
                "did not support them."
            )
        if self.fallback_reason and not self.used_llm:
            lines.append(f"Fallback reason: {self.fallback_reason}.")
        return "\n".join(lines).strip() + "\n"


def format_timestamp(seconds: float | None) -> str:
    if seconds is None:
        return "--:--"
    minutes, rest = divmod(max(0.0, seconds), 60)
    return f"{int(minutes):02d}:{int(rest):02d}"


# ---------------------------------------------------------------------- prompting
SYSTEM_PROMPT = (
    "You are an offline study-notes assistant. Use only the transcript excerpt "
    "the user provides. Never add outside facts, examples, or opinions. If the "
    "excerpt does not support a point, leave it out. Write plain text in the "
    "same language as the excerpt."
)


def build_system_prompt(syllabus: SyllabusContext | None = None) -> str:
    """Keep the grounding rules and append only a terminology-level syllabus hint."""
    if syllabus is None:
        return SYSTEM_PROMPT
    return f"{SYSTEM_PROMPT}\n\n{syllabus.prompt()}"

BLOCK_PROMPT = """Transcript excerpt:
{excerpt}

Write study notes for this excerpt using exactly this layout:

SUMMARY: <one sentence>
POINTS:
- <key idea>
- <key idea>
TERMS:
- <term>: <short definition>

Rules: 2 to 5 POINTS, at most 3 TERMS, no preamble, no headings.
"""

REDUCE_PROMPT = """These are summaries of consecutive parts of one lecture:
{summaries}

Write one 2-sentence summary of the whole lecture. Use only the information above.
"""


def parse_note_block(raw: str) -> tuple[str | None, list[str], list[tuple[str, str]]]:
    """Best-effort parse of the requested layout; tolerant of small-model noise."""
    text = raw.strip()
    if text.startswith("```"):
        rows = [row for row in text.splitlines() if not _FENCE.match(row.strip())]
        text = "\n".join(rows)

    summary: str | None = None
    points: list[str] = []
    terms: list[tuple[str, str]] = []
    section = "points"

    for row in text.splitlines():
        line = row.strip().lstrip("#").strip()
        if not line:
            continue
        summary_match = _SUMMARY.match(line)
        if summary_match:
            summary = _clean_line(summary_match.group("text"))
            section = "points"
            continue
        if _POINTS_HEADER.match(line):
            section = "points"
            continue
        if _TERMS_HEADER.match(line):
            section = "terms"
            continue
        bullet = _BULLET.match(line)
        if bullet:
            content = _clean_line(bullet.group("text"))
            if section == "terms":
                term, _, body = content.partition(":")
                if body.strip():
                    terms.append((_clean_line(term), _clean_line(body)))
                else:
                    points.append(content)
            elif content:
                points.append(content)

    if not points and not terms:
        # Model ignored the layout: keep its sentences rather than failing.
        fallback = [
            _clean_line(part)
            for part in _SENTENCE_END.split(text)
            if len(_clean_line(part)) >= 20
        ]
        points = fallback[:5]

    return summary, points, terms


def _clean_line(text: str) -> str:
    return " ".join(text.replace("**", "").replace("__", "").split()).strip(" -:\t")


def _acceptable(text: str, evidence: set[str]) -> bool:
    text = text.strip()
    if not 15 <= len(text) <= 400:
        return False
    if not any(char.isalnum() for char in text):
        return False
    if _REFUSAL.search(text):
        return False
    candidate = _evidence_tokens(text)
    if len(candidate) < 2:
        return False
    support = len(candidate & evidence) / len(candidate)
    return support >= 0.34


def _summarisable(text: str, evidence: set[str]) -> bool:
    if not 20 <= len(text) <= 600 or _REFUSAL.search(text):
        return False
    candidate = _evidence_tokens(text)
    if len(candidate) < 3:
        return False
    return len(candidate & evidence) / len(candidate) >= 0.25


def _chunk(sentences: Sequence[Sentence], max_chars: int) -> list[list[Sentence]]:
    chunks: list[list[Sentence]] = []
    current: list[Sentence] = []
    size = 0
    for sentence in sentences:
        length = len(sentence.text) + 1
        if current and size + length > max_chars:
            chunks.append(current)
            current, size = [], 0
        current.append(sentence)
        size += length
    if current:
        chunks.append(current)
    return chunks


def _best_timestamp(text: str, candidates: Sequence[Sentence]) -> float | None:
    tokens = set(_evidence_tokens(text))
    best: tuple[float, float | None] = (0.0, None)
    for sentence in candidates:
        if sentence.start is None:
            continue
        score = _jaccard(tokens, set(_evidence_tokens(sentence.text)))
        if score > best[0]:
            best = (score, sentence.start)
    return best[1] if best[0] >= 0.3 else None


def _extractive_summary(sentences: Sequence[Sentence], keywords: Sequence[str]) -> str:
    if not sentences:
        return ""
    keyword_set = set(keywords)
    scored = [
        (len(keyword_set & set(content_tokens(sentence.text))), -sentence.order, sentence.text)
        for sentence in sentences
    ]
    return max(scored)[2]


# ---------------------------------------------------------------------- generator
class NotesGenerator:
    """Turns transcript lines into grounded, timestamped notes."""

    def __init__(
        self,
        llm: LlmProvider,
        settings: LlmSettings | None = None,
        *,
        max_points: int = 16,
    ) -> None:
        self.llm = llm
        self.settings = settings or LlmSettings()
        self.max_points = max_points

    @classmethod
    def from_settings(cls, settings: LlmSettings, *, profile: str | None = None) -> NotesGenerator:
        return cls(create_llm(settings, profile=profile), settings)

    # ------------------------------------------------------------------ public
    def generate(
        self,
        lines: Sequence[TranscriptLine],
        *,
        title: str = "Lecture notes",
        syllabus: SyllabusContext | None = None,
    ) -> NoteResult:
        started = time.perf_counter()
        sentences = split_sentences(lines)
        if not sentences:
            raise ValueError("No transcript sentences to summarise")

        evidence_text = " ".join(sentence.text for sentence in sentences)
        evidence = _evidence_tokens(evidence_text)
        selected = select_sentences(sentences, limit=desired_sentence_count(len(sentences)))
        keywords = extract_keywords(selected)
        definitions = find_definitions(selected)
        system_prompt = build_system_prompt(syllabus)

        points = [NotePoint(text=s.text, start=s.start) for s in selected]
        summary = _extractive_summary(selected, keywords)
        used_llm = False
        dropped = 0
        fallback: str | None = None

        if not self.settings.enabled:
            fallback = "LLM disabled in settings"
        elif not self.llm.available:
            fallback = self._unavailable_reason()
        else:
            deadline = started + self.settings.budget_s
            llm_points, summaries, llm_terms, dropped, fallback = self._rewrite(
                selected, evidence, deadline, system_prompt
            )
            if llm_points:
                used_llm = True
                points = llm_points
                definitions = _dedupe_definitions(llm_terms + definitions)[:6]
                summary = (
                    self._merge_summaries(summaries, evidence, deadline, system_prompt)
                    or summary
                )

        return NoteResult(
            title=title,
            summary=summary,
            points=points[: self.max_points],
            definitions=definitions,
            keywords=keywords,
            used_llm=used_llm,
            profile=getattr(self.llm.info, "profile", "none"),
            model=self.llm.info.model if used_llm else None,
            dropped=dropped,
            latency_s=time.perf_counter() - started,
            fallback_reason=fallback,
            sentences=len(sentences),
            curriculum=syllabus.to_dict() if syllabus is not None else None,
        )

    # ----------------------------------------------------------------- private
    def _unavailable_reason(self) -> str:
        from ila.llm import llama_cpp_installed

        if not llama_cpp_installed():
            return 'llama-cpp-python is not installed (uv pip install -e ".[llm]")'
        return f"no model file at {getattr(self.llm.info, 'path', None) or 'the configured path'}"

    def _rewrite(
        self,
        selected: Sequence[Sentence],
        evidence: set[str],
        deadline: float,
        system_prompt: str,
    ) -> tuple[list[NotePoint], list[str], list[Definition], int, str | None]:
        chunks = _chunk(selected, self.settings.chunk_chars)
        points: list[NotePoint] = []
        summaries: list[str] = []
        definitions: list[Definition] = []
        dropped = 0
        reason: str | None = None
        answered = 0

        for number, chunk in enumerate(chunks, start=1):
            if time.perf_counter() >= deadline:
                reason = (
                    f"stopped after {number - 1}/{len(chunks)} chunks "
                    "to stay within the time budget"
                )
                break
            excerpt = " ".join(sentence.text for sentence in chunk)
            try:
                raw = self.llm.complete(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": BLOCK_PROMPT.format(excerpt=excerpt)},
                    ],
                    max_tokens=self.settings.max_tokens,
                    temperature=self.settings.temperature,
                )
            except Exception as exc:  # runtime/model errors must not lose the transcript
                logger.warning("note chunk %d/%d failed: %s", number, len(chunks), exc)
                reason = f"model error: {exc}"
                continue

            answered += 1
            summary, raw_points, raw_terms = parse_note_block(raw)
            if summary and _summarisable(summary, evidence):
                summaries.append(summary)

            for candidate in raw_points:
                if not _acceptable(candidate, evidence):
                    dropped += 1
                    continue
                points.append(
                    NotePoint(
                        text=candidate,
                        start=_best_timestamp(candidate, chunk),
                        source="llm",
                    )
                )

            for term, body in raw_terms:
                text = f"{term}: {body}" if body else term
                term_tokens = _evidence_tokens(term)
                term_supported = bool(term_tokens) and (
                    len(term_tokens & evidence) / len(term_tokens) >= 0.5
                )
                if not _acceptable(text, evidence) or not term_supported:
                    dropped += 1
                    continue
                definitions.append(
                    Definition(
                        term=term,
                        text=body or term,
                        start=_best_timestamp(text, chunk),
                    )
                )

        if answered == 0 and reason is None:
            reason = "the model did not return usable notes"
        if answered < len(chunks) and reason is None:
            reason = f"only {answered}/{len(chunks)} chunks produced usable notes"

        return _dedupe_points(points), summaries, definitions, dropped, reason

    def _merge_summaries(
        self,
        summaries: Sequence[str],
        evidence: set[str],
        deadline: float,
        system_prompt: str,
    ) -> str | None:
        if not summaries:
            return None
        if len(summaries) == 1:
            return summaries[0]
        if time.perf_counter() < deadline:
            try:
                raw = self.llm.complete(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": REDUCE_PROMPT.format(
                            summaries="\n".join(f"- {item}" for item in summaries)
                        )},
                    ],
                    max_tokens=160,
                    temperature=self.settings.temperature,
                )
                candidate = _clean_line(raw.splitlines()[0]) if raw.strip() else ""
                if _summarisable(candidate, evidence):
                    return candidate
            except Exception as exc:
                logger.warning("summary merge failed: %s", exc)
        return " ".join(summaries[:2])


def _dedupe_definitions(items: Sequence[Definition]) -> list[Definition]:
    seen: set[str] = set()
    kept: list[Definition] = []
    for item in items:
        key = " ".join(_stem(token) for token in content_tokens(item.term))
        if not key or key in seen:
            continue
        seen.add(key)
        kept.append(item)
    return kept


def _dedupe_points(points: Sequence[NotePoint], *, redundancy: float = 0.75) -> list[NotePoint]:
    kept: list[NotePoint] = []
    seen: list[set[str]] = []
    for point in points:
        tokens = set(_evidence_tokens(point.text))
        if any(_jaccard(tokens, other) >= redundancy for other in seen):
            continue
        seen.append(tokens)
        kept.append(point)
    return kept


def generate_notes(
    lines: Sequence[TranscriptLine],
    settings: LlmSettings,
    *,
    title: str = "Lecture notes",
    profile: str | None = None,
    class_level: int | None = None,
    subject: str | None = None,
) -> NoteResult:
    """Convenience wrapper: build the configured provider and generate notes.

    When ``class_level`` and ``subject`` are given, the transcript is matched to
    the NCERT course and the resulting chapter hint is added to the prompt.
    """
    syllabus = None
    if class_level is not None and subject is not None:
        from ila.curriculum import build_syllabus_context

        text = " ".join(line.text for line in lines)
        syllabus = build_syllabus_context(text, class_level, subject)
    return NotesGenerator.from_settings(settings, profile=profile).generate(
        lines, title=title, syllabus=syllabus
    )
