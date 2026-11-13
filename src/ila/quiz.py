"""Deterministic quiz generation, grading and adaptive remediation.

Question generation is grounded in the same passages the Q&A engine retrieves:
definitions and cloze items are extracted from the lecture transcript and the
generated master notes. Nothing is invented, and every question keeps its
chapter/timestamp provenance.

Mastery is a bounded exponential moving average, not a trained model. That is
intentional: it is explainable, works with a handful of answers, and adds no
scikit-learn dependency. Difficulty selection and the teacher "weakest topics"
view are built on that estimate.
"""

from __future__ import annotations

import hashlib
import random
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from ila.curriculum import Course, match_chapters
from ila.llm import LlmProvider
from ila.retrieval import (
    KnowledgeBase,
    Passage,
    content_terms,
    cosine,
    hashed_embedding,
    tokenize,
)
from ila.storage import Storage

QuizKind = Literal["mcq", "short"]

_DEFINITION = re.compile(
    r"^(?P<term>[A-Za-z][\w\s'\-]{1,52}?)\s+"
    r"(?P<verb>is|are|means|refers to|is defined as|are defined as)\s+"
    r"(?P<body>.{12,})$",
    re.IGNORECASE,
)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_SPACE = re.compile(r"\s+")
_NOISE = re.compile(
    r"\b(?:section\s+\d|unit\s+\d|exercise\s+\d|summary checklist|exam trap|practice drill|"
    r"answer key|learning objective|pedagogical|key terms:)\b",
    re.IGNORECASE,
)
_BAD_TERM_START = frozenset(
    {"if", "when", "where", "which", "that", "this", "there", "we", "you", "students", "today"}
)
_BAD_TERM_WORDS = frozenset(
    {"if", "when", "where", "which", "because", "then", "so", "but", "and", "or"}
)
_BAD_TERM_PHRASES = ("alpha", "beta", "theta", "lambda")
_GREEK = re.compile(r"\b(?:alpha|beta|theta|lambda|gamma|delta)\b", re.IGNORECASE)
_NUMBER_START = re.compile(
    r"^(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|twenty|\d+)\b",
    re.IGNORECASE,
)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True, slots=True)
class QuizQuestion:
    id: str
    kind: QuizKind
    prompt: str
    answer: str
    topic: str
    difficulty: int
    explanation: str
    source: str
    chapter_number: int | None = None
    chapter_title: str | None = None
    start: float | None = None
    end: float | None = None
    options: tuple[str, ...] = ()
    answer_index: int | None = None
    keywords: tuple[str, ...] = ()

    def public(self) -> dict[str, Any]:
        """The learner-facing view; the correct answer stays on the server."""
        return {
            "id": self.id,
            "kind": self.kind,
            "prompt": self.prompt,
            "options": list(self.options),
            "difficulty": self.difficulty,
            "topic": self.topic,
            "chapter_number": self.chapter_number,
            "chapter_title": self.chapter_title,
            "source": self.source,
            "start": self.start,
            "end": self.end,
        }

    def state(self) -> dict[str, Any]:
        """Complete serialisable record used by the quiz session state."""
        return {
            **self.public(),
            "answer": self.answer,
            "answer_index": self.answer_index,
            "explanation": self.explanation,
            "keywords": list(self.keywords),
        }

    @classmethod
    def from_state(cls, payload: dict[str, Any]) -> QuizQuestion:
        return cls(
            id=str(payload["id"]),
            kind=payload["kind"],
            prompt=str(payload["prompt"]),
            answer=str(payload["answer"]),
            topic=str(payload.get("topic") or "General"),
            difficulty=int(payload.get("difficulty", 2)),
            explanation=str(payload.get("explanation") or ""),
            source=str(payload.get("source") or "lecture"),
            chapter_number=payload.get("chapter_number"),
            chapter_title=payload.get("chapter_title"),
            start=payload.get("start"),
            end=payload.get("end"),
            options=tuple(payload.get("options") or ()),
            answer_index=payload.get("answer_index"),
            keywords=tuple(payload.get("keywords") or ()),
        )


# --------------------------------------------------------------- question bank
@dataclass(slots=True)
class _Definition:
    term: str
    body: str
    sentence: str
    passage: Passage
    topic: str


def _question_id(kind: str, prompt: str, answer: str) -> str:
    raw = f"{kind}|{prompt}|{answer}".encode()
    return hashlib.sha1(raw).hexdigest()[:12]


def _sentence_topic(
    sentence: str, passage: Passage, course: Course | None
) -> tuple[str, int | None, str | None]:
    if passage.chapter_number is not None:
        return (
            passage.chapter_title or f"Chapter {passage.chapter_number}",
            passage.chapter_number,
            passage.chapter_title,
        )
    if course is not None:
        matches = match_chapters(sentence, course, limit=1, min_score=1.5)
        if matches:
            chapter = matches[0].chapter
            return chapter.title, chapter.number, chapter.title
    return "General", None, None


def _definition_records(
    knowledge: KnowledgeBase,
    *,
    sources: set[str] | None = None,
) -> list[_Definition]:
    records: list[_Definition] = []
    seen: set[tuple[str, str]] = set()
    for passage in knowledge.passages:
        if not passage.is_content:
            continue
        if sources is not None and passage.source not in sources:
            continue
        for sentence in _SENTENCE_END.split(passage.text):
            sentence = _SPACE.sub(" ", sentence).strip()
            if len(sentence) < 24 or len(sentence) > 420 or _NOISE.search(sentence):
                continue
            if sentence.lower().startswith(("today we", "in this", "let us")):
                continue
            match = _DEFINITION.match(sentence)
            if not match:
                continue
            term = re.sub(r"^(?:the|a|an)\s+", "", match.group("term").strip(), flags=re.I)
            term = term.strip(" .,:;")
            body = match.group("body").strip()
            # Keep the first clause; "X is A, and Y is B" is two facts, not one definition.
            body = re.split(r",\s+and\s+(?:the|a|an)\s+", body, maxsplit=1)[0]
            body = body.strip(" .,:;")
            words = term.split()
            if len(term) < 3 or len(term) > 54 or len(body) < 12:
                continue
            if not words or len(words) > 7:
                continue
            if re.search(r"\d", term) or term.isupper():
                continue
            if any(w.isupper() and len(w) > 3 for w in words):
                continue
            if term.lower().startswith(("introduction to", "chapter", "unit", "exercise", "note that", "recall that")):
                continue
            if words[0].lower() in _BAD_TERM_START:
                continue
            if any(word.lower() in _BAD_TERM_WORDS for word in words):
                continue
            if any(phrase in term.lower() for phrase in _BAD_TERM_PHRASES):
                continue
            if (
                _NUMBER_START.match(term)
                or _NUMBER_START.match(body)
                or body.lower().startswith("so ")
            ):
                continue
            if body.lower().startswith(("called ", "known as ")):
                continue
            key = (term.lower(), body.lower())
            if key in seen:
                continue
            seen.add(key)
            topic, _, _ = _sentence_topic(sentence, passage, knowledge.course)
            records.append(
                _Definition(
                    term=term,
                    body=body,
                    sentence=sentence,
                    passage=passage,
                    topic=topic,
                )
            )
    return records


def _keyword_pool(knowledge: KnowledgeBase) -> tuple[dict[int, list[str]], list[str]]:
    by_chapter: dict[int, list[str]] = {}
    global_pool: list[str] = []
    if knowledge.course is None:
        return by_chapter, global_pool
    for chapter in knowledge.course.chapters:
        values = [
            keyword
            for keyword in chapter.keywords
            if (len(keyword) >= 4 and " " in keyword) or len(keyword) >= 5
        ]
        by_chapter[chapter.number] = values
        global_pool.extend(values)
    # Preserve order, remove duplicates.
    global_pool = list(dict.fromkeys(global_pool))
    return by_chapter, global_pool


def _choose_distractors(
    correct: str,
    *,
    question_id: str,
    same_chapter: Sequence[str],
    global_pool: Sequence[str],
    count: int = 3,
) -> list[str]:
    correct_key = correct.lower().strip()
    candidates: list[str] = []
    seen: set[str] = {correct_key}
    for pool in (same_chapter, global_pool):
        for value in pool:
            key = value.lower().strip()
            if not key or key in seen:
                continue
            if key in correct_key or correct_key in key:
                continue
            seen.add(key)
            candidates.append(value)
    rng = random.Random(question_id)
    rng.shuffle(candidates)
    return candidates[:count]


def _mcq_options(
    correct: str, distractors: Sequence[str], *, question_id: str
) -> tuple[tuple[str, ...], int]:
    options = [correct, *distractors]
    rng = random.Random(question_id)
    rng.shuffle(options)
    return tuple(options), options.index(correct)


def _definition_questions(
    definitions: Sequence[_Definition],
) -> list[QuizQuestion]:
    if len(definitions) < 3:
        return []
    bank: list[QuizQuestion] = []
    bodies: list[str] = []
    for item in definitions:
        if item.body.lower() not in {body.lower() for body in bodies}:
            bodies.append(item.body)
    if len(bodies) < 3:
        return []
    for item in definitions:
        distractors = [
            body for body in bodies if body.lower() != item.body.lower()
        ]
        rng = random.Random(item.term.lower())
        rng.shuffle(distractors)
        prompt = f'Which option best defines "{item.term}"?'
        identifier = _question_id("mcq", prompt, item.body)
        options, index = _mcq_options(
            item.body, distractors[:3], question_id=identifier
        )
        bank.append(
            QuizQuestion(
                id=identifier,
                kind="mcq",
                prompt=prompt,
                answer=item.body,
                topic=item.topic,
                difficulty=2,
                explanation=(
                    f"**Concept:** {item.term}\n\n"
                    f"**NCERT Definition:** {item.body}.\n\n"
                    f"**Why this is correct:** In Class 10 {item.passage.chapter_title or item.topic}, "
                    f"'{item.term}' is formally defined by this exact condition. "
                    f"Mastering this relationship is essential for proving theorems and solving application problems."
                ),
                source=item.passage.source,
                chapter_number=item.passage.chapter_number,
                chapter_title=item.passage.chapter_title,
                start=item.passage.start,
                end=item.passage.end,
                options=options,
                answer_index=index,
                keywords=(item.term,),
            )
        )
    return bank


def _short_answer_questions(
    definitions: Sequence[_Definition],
    *,
    limit: int = 40,
) -> list[QuizQuestion]:
    bank: list[QuizQuestion] = []
    for item in definitions[:limit]:
        prompt = f"In one sentence, define {item.term}."
        identifier = _question_id("short", prompt, item.body)
        bank.append(
            QuizQuestion(
                id=identifier,
                kind="short",
                prompt=prompt,
                answer=item.body,
                topic=item.topic,
                difficulty=3,
                explanation=(
                    f"**Concept:** {item.term}\n\n"
                    f"**NCERT Standard Definition:** {item.body}.\n\n"
                    f"**Why this is correct:** According to the NCERT syllabus for {item.passage.chapter_title or item.topic}, "
                    f"'{item.body}' captures the foundational mathematical principle. "
                    f"Paraphrased explanations and mathematically equivalent formulations are recognized as valid by the evaluator."
                ),
                source=item.passage.source,
                chapter_number=item.passage.chapter_number,
                chapter_title=item.passage.chapter_title,
                start=item.passage.start,
                end=item.passage.end,
                keywords=(item.term,),
            )
        )
    return bank


def _find_keyword(sentence: str, keywords: Sequence[str]) -> tuple[str, re.Match[str]] | None:
    for keyword in sorted(keywords, key=len, reverse=True):
        if len(keyword) < 4:
            continue
        match = re.search(rf"\b{re.escape(keyword)}\b", sentence, re.IGNORECASE)
        if match:
            return keyword, match
    return None


def _cloze_questions(
    knowledge: KnowledgeBase,
    *,
    sources: set[str] | None = None,
    max_questions: int = 120,
) -> list[QuizQuestion]:
    by_chapter, global_pool = _keyword_pool(knowledge)
    if not global_pool:
        return []
    bank: list[QuizQuestion] = []
    seen_prompts: set[str] = set()
    for passage in knowledge.passages:
        if not passage.is_content:
            continue
        if sources is not None and passage.source not in sources:
            continue
        pool = by_chapter.get(passage.chapter_number or -1, [])
        keywords = list(dict.fromkeys([*pool, *global_pool]))
        for sentence in _SENTENCE_END.split(passage.text):
            sentence = _SPACE.sub(" ", sentence).strip()
            if len(sentence) < 28 or len(sentence) > 420:
                continue
            if _NOISE.search(sentence) or sentence.lower().startswith(("today we", "in this")):
                continue
            if _GREEK.search(sentence):
                continue
            found = _find_keyword(sentence, keywords)
            if not found:
                continue
            keyword, match = found
            answer = match.group(0)
            blanked = sentence[: match.start()] + "______" + sentence[match.end() :]
            prompt = f"Complete the statement: {blanked}"
            if prompt.lower() in seen_prompts:
                continue
            seen_prompts.add(prompt.lower())
            identifier = _question_id("mcq", prompt, answer)
            # Prefer same-chapter distractors, then the rest of the course.
            same = list(by_chapter.get(passage.chapter_number or -1, []))
            distractors = _choose_distractors(
                answer,
                question_id=identifier,
                same_chapter=same,
                global_pool=global_pool,
            )
            if len(distractors) < 3:
                continue
            options, index = _mcq_options(answer, distractors, question_id=identifier)
            topic, chapter_number, chapter_title = _sentence_topic(
                sentence, passage, knowledge.course
            )
            bank.append(
                QuizQuestion(
                    id=identifier,
                    kind="mcq",
                    prompt=prompt,
                    answer=answer,
                    topic=topic,
                    difficulty=1 if len(sentence) < 160 else 2,
                    explanation=(
                        f"**Key Term:** {answer}\n\n"
                        f"**NCERT Textbook Statement:** \"{sentence}\"\n\n"
                        f"**Why this is correct:** The term '{answer}' completes the foundational rule according to the NCERT {chapter_title or topic} textbook."
                    ),
                    source=passage.source,
                    chapter_number=chapter_number,
                    chapter_title=chapter_title,
                    start=passage.start,
                    end=passage.end,
                    options=options,
                    answer_index=index,
                    keywords=(keyword,),
                )
            )
            if len(bank) >= max_questions:
                return bank
    return bank


def build_question_bank(
    knowledge: KnowledgeBase,
    *,
    max_questions: int = 240,
) -> list[QuizQuestion]:
    """Build a mixed, deterministic question pool from grounded passages.

    Lecture questions come first. NCERT textbook exercises and examples
    provide full curriculum coverage across all chapters for Mathematics.
    """
    bank: list[QuizQuestion] = []
    lecture_definitions = _definition_records(knowledge, sources={"lecture"})
    bank.extend(_definition_questions(lecture_definitions))
    bank.extend(_short_answer_questions(lecture_definitions, limit=30))
    bank.extend(_cloze_questions(knowledge, sources={"lecture"}, max_questions=100))

    is_math = knowledge.course is not None and knowledge.course.subject == "maths"
    if is_math:
        from ila.ncert_math_questions import get_ncert_math_questions

        bank.extend(get_ncert_math_questions())
    else:
        # Master notes and extracted NCERT textbook passages for non-math subjects
        tb_definitions = _definition_records(knowledge, sources={"textbook", "notes"})
        bank.extend(_definition_questions(tb_definitions))
        bank.extend(_short_answer_questions(tb_definitions, limit=40))
        bank.extend(_cloze_questions(knowledge, sources={"textbook", "notes"}, max_questions=120))

    # De-duplicate by id while preserving the definition-first order.
    unique: dict[str, QuizQuestion] = {}
    for question in bank:
        unique.setdefault(question.id, question)
    return list(unique.values())[:max_questions]


# --------------------------------------------------------------------- grading
def normalize_answer(text: str) -> str:
    return " ".join(tokenize(text, keep_stopwords=True))


def evaluate_semantic_answer(
    prompt: str,
    expected: str,
    submitted: str,
    *,
    keywords: Sequence[str] = (),
    llm: LlmProvider | None = None,
) -> tuple[bool, str, str]:
    """Evaluate a student answer by meaning, concept, and intent rather than exact wording.

    Returns:
        (is_correct, evaluator_kind, explanation_reason)
    """
    cleaned = submitted.strip()
    if not cleaned:
        return False, "rule", "No answer provided."

    norm_sub = normalize_answer(cleaned).lower()
    norm_exp = normalize_answer(expected).lower()
    if cleaned.lower() == expected.strip().lower() or norm_sub == norm_exp:
        return True, "exact", "Exact match with syllabus definition."

    exp_lower = expected.strip().lower()
    sub_lower = cleaned.lower()
    if len(exp_lower) >= 4 and exp_lower in sub_lower:
        return True, "rule", "Answer explicitly contains the expected definition."

    # Fast token recall / overlap
    answer_terms = content_terms(expected)
    response_terms = content_terms(cleaned)
    recall = 0.0
    f1 = 0.0
    if answer_terms and response_terms:
        overlap = answer_terms & response_terms
        recall = len(overlap) / len(answer_terms)
        precision = len(overlap) / len(response_terms)
        f1 = 0.0 if not (recall + precision) else 2 * recall * precision / (recall + precision)
        if recall >= 0.7 or f1 >= 0.7:
            return True, "overlap", "High conceptual vocabulary overlap with expected answer."

    # Semantic Meaning & Intent Evaluation using Local LLM (e.g. Qwen 3.5)
    if llm is not None and getattr(llm, "available", False):
        eval_prompt = (
            "You are an educational grader for CBSE/NCERT curriculum. "
            "Judge whether the student's answer demonstrates genuine understanding of the concept, meaning, and intent of the expected answer.\n"
            "CRITICAL RULES:\n"
            "1. The answer does NOT need to match the expected wording.\n"
            "2. Paraphrased explanations, alternate mathematical formulations "
            "(such as 'p/q with integers' for 'ratio of integers', or 'b^2 - 4ac' for discriminant formula), "
            "and conceptually equivalent statements MUST be accepted as CORRECT.\n"
            "3. If the core mathematical or scientific truth is conveyed, accept it.\n\n"
            f"Question: {prompt}\n"
            f"Expected Answer: {expected}\n"
            f"Student Answer: {cleaned}\n\n"
            "Does the student's answer capture the correct concept and meaning? "
            "Respond ONLY in this exact format:\n"
            "CORRECT: <YES or NO>\n"
            "REASON: <1 concise sentence explaining your evaluation>"
        )
        try:
            completion = llm.complete(
                [{"role": "user", "content": eval_prompt}],
                max_tokens=70,
                temperature=0.1,
            ).strip()

            is_yes = False
            reason = ""
            for line in completion.splitlines():
                line = line.strip()
                if line.upper().startswith("CORRECT:"):
                    val = line.split(":", 1)[1].strip().upper()
                    if "YES" in val or "TRUE" in val or "CORRECT" in val:
                        is_yes = True
                elif line.upper().startswith("REASON:"):
                    reason = line.split(":", 1)[1].strip()

            if not reason:
                clean_lines = [
                    l for l in completion.splitlines() if not l.upper().startswith("CORRECT:")
                ]
                reason = " ".join(clean_lines).strip()

            if is_yes:
                return (
                    True,
                    "llm",
                    reason or "Student answer correctly conveys the core concept and intent.",
                )
            else:
                return (
                    False,
                    "llm",
                    reason or "Student answer does not capture the required concept.",
                )
        except Exception:
            pass  # Fall back to mathematical heuristics and embeddings

    # Mathematical / NCERT conceptual equivalence heuristics fallback
    exp_c = exp_lower.replace(" ", "")
    sub_c = sub_lower.replace(" ", "")

    if "irrational" in exp_lower or "ratio of" in exp_lower or "ratio of two integers" in exp_lower:
        if ("cannot" in sub_lower or "can't" in sub_lower or "not" in sub_lower) and (
            "p/q" in sub_lower or "fraction" in sub_lower or "ratio" in sub_lower
        ):
            if "integer" in sub_lower or "integers" in sub_lower:
                return (
                    True,
                    "math_concept",
                    "Mathematically equivalent: correctly states that irrational numbers cannot be expressed in p/q form where p and q are integers.",
                )
        if "non-terminating" in sub_lower and (
            "non-repeating" in sub_lower or "non-recurring" in sub_lower
        ):
            return (
                True,
                "math_concept",
                "Mathematically equivalent: correctly identifies irrational numbers by non-terminating, non-repeating decimal expansion.",
            )

    if "discriminant" in exp_lower or "b^2 - 4ac" in exp_lower or "b² - 4ac" in exp_lower:
        if "b^2-4ac" in sub_c or "b2-4ac" in sub_c or "b²-4ac" in sub_c:
            return True, "math_concept", "Correctly identifies the discriminant formula b² - 4ac."

    if "a1/a2!=b1/b2" in sub_c or "a1/a2≠b1/b2" in sub_c:
        if "unique" in exp_lower or "intersecting" in exp_lower or "consistent" in exp_lower:
            return (
                True,
                "math_concept",
                "Correctly identifies the condition a1/a2 ≠ b1/b2 for a unique intersecting solution.",
            )

    # Embedding similarity fallback
    sim = cosine(hashed_embedding(expected), hashed_embedding(cleaned))
    if sim >= 0.52 and recall >= 0.35:
        return True, "embedding", "Semantic similarity exceeds confidence threshold."

    # Terse keyword overlap fallback
    if keywords:
        keyword_terms = content_terms(" ".join(keywords))
        if keyword_terms and response_terms:
            keyword_overlap = keyword_terms & response_terms
            if len(keyword_overlap) / len(keyword_terms) >= 0.5:
                return True, "keywords", "Key syllabus terminology matched."

    return False, "rule", "Answer does not sufficiently match the required concept."


def grade_answer_detailed(
    question: QuizQuestion,
    *,
    answer: str = "",
    answer_index: int | None = None,
    llm: LlmProvider | None = None,
) -> tuple[bool, str, str, str]:
    """Return ``(correct, normalized_response, evaluation_reason, evaluator_kind)``."""
    if question.kind == "mcq":
        chosen = ""
        if answer_index is not None and 0 <= answer_index < len(question.options):
            chosen = question.options[answer_index]
        elif answer.strip():
            cleaned = answer.strip()
            if cleaned.isdigit() and 0 <= int(cleaned) < len(question.options):
                chosen = question.options[int(cleaned)]
            else:
                for option in question.options:
                    if option.strip().casefold() == cleaned.casefold():
                        chosen = option
                        break
                if not chosen:
                    normalized = normalize_answer(cleaned)
                    if normalized:
                        for option in question.options:
                            if normalize_answer(option) == normalized:
                                chosen = option
                                break
        if not chosen:
            return False, "", "No option selected.", "mcq"
        if question.answer_index is not None:
            correct = (
                (answer_index is not None and answer_index == question.answer_index)
                or chosen == question.options[question.answer_index]
                or chosen.strip().casefold() == question.answer.strip().casefold()
            )
        else:
            correct = chosen.strip().casefold() == question.answer.strip().casefold()
        reason = "Correct option chosen." if correct else f"Selected option: {chosen}"
        return correct, chosen, reason, "mcq"

    response = answer.strip()
    if not response:
        return False, "", "No answer provided.", "rule"

    correct, evaluator, reason = evaluate_semantic_answer(
        prompt=question.prompt,
        expected=question.answer,
        submitted=response,
        keywords=question.keywords,
        llm=llm,
    )
    return correct, response, reason, evaluator


def grade_answer(
    question: QuizQuestion,
    *,
    answer: str = "",
    answer_index: int | None = None,
    llm: LlmProvider | None = None,
) -> tuple[bool, str]:
    """Return ``(correct, normalized_response)`` for either question kind."""
    correct, response, _, _ = grade_answer_detailed(
        question, answer=answer, answer_index=answer_index, llm=llm
    )
    return correct, response


# -------------------------------------------------------------------- adaptive
def difficulty_for_mastery(score: float) -> int:
    if score < 0.36:
        return 1
    if score < 0.66:
        return 2
    return 3


def update_mastery_score(
    previous: float,
    *,
    correct: bool,
    difficulty: int,
    response_ms: int | None = None,
) -> float:
    """Bounded EMA: harder items move the estimate more; wrong answers pull down."""
    step = 0.30 + 0.10 * (max(1, min(3, difficulty)) - 1)
    if correct and response_ms is not None and response_ms <= 12_000:
        step += 0.05
    target = 1.0 if correct else 0.0
    return _clamp(previous + step * (target - previous), 0.02, 0.99)


def _topic_aliases(course: Course | None) -> list[tuple[str, str]]:
    if course is None:
        return []
    aliases: list[tuple[str, str]] = []
    for chapter in course.chapters:
        aliases.append((f"chapter {chapter.number}", chapter.title))
        aliases.append((str(chapter.number), chapter.title))
    return aliases


def _matches_topic(question: QuizQuestion, topic: str, course: Course | None) -> bool:
    requested = topic.strip().lower()
    if not requested:
        return True
    if question.topic.lower() == requested:
        return True
    if question.chapter_title and question.chapter_title.lower() == requested:
        return True
    if question.chapter_number is not None and requested in {
        str(question.chapter_number),
        f"chapter {question.chapter_number}",
    }:
        return True
    if requested in question.topic.lower() or question.topic.lower() in requested:
        return True
    for alias, title in _topic_aliases(course):
        if requested == alias and question.chapter_title == title:
            return True
    return False


def _pick_question(
    pool: Sequence[QuizQuestion],
    *,
    target_difficulty: int,
    used_ids: set[str],
    mastery: dict[str, float],
    recent_ids: set[str] | None = None,
    rng: random.Random | None = None,
) -> QuizQuestion | None:
    candidates = [question for question in pool if question.id not in used_ids]
    if not candidates:
        return None

    _rng = rng or random

    # 1. Filter out recently attempted questions if fresh candidates exist
    if recent_ids:
        fresh = [q for q in candidates if q.id not in recent_ids]
        if fresh:
            candidates = fresh

    # 2. Find candidates with minimum distance to target difficulty
    min_dist = min(abs(q.difficulty - target_difficulty) for q in candidates)
    best_diff_candidates = [q for q in candidates if abs(q.difficulty - target_difficulty) == min_dist]

    # 3. Find candidates addressing lowest mastery topics (within tolerance)
    min_topic_score = min(mastery.get(q.topic, 0.5) for q in best_diff_candidates)
    best_pool = [
        q for q in best_diff_candidates
        if abs(mastery.get(q.topic, 0.5) - min_topic_score) <= 0.20
    ]

    # 4. Pick randomly from the qualified pool for variety and non-repetition
    return _rng.choice(best_pool)


@dataclass(slots=True)
class QuizEngine:
    storage: Storage
    llm: LlmProvider | None = None

    def start(
        self,
        knowledge: KnowledgeBase,
        *,
        student_id: str,
        class_level: int,
        subject: str,
        topic: str | None = None,
        length: int = 5,
        difficulty: int | None = None,
        pool: Sequence[QuizQuestion] | None = None,
    ) -> dict[str, Any]:
        questions = list(pool) if pool is not None else build_question_bank(knowledge)
        course = knowledge.course
        if topic:
            questions = [
                question
                for question in questions
                if _matches_topic(question, topic, course)
            ]
        if not questions:
            raise ValueError(
                "No grounded questions could be generated for that topic. Try another "
                "chapter, or record a lecture with more definitions."
            )
        if difficulty is not None and not 1 <= difficulty <= 3:
            raise ValueError("Difficulty must be 1, 2 or 3")

        length = max(1, min(int(length), 20))
        total = min(length, len(questions))
        mastery_rows = {row["topic"]: row for row in self.storage.list_mastery(student_id)}
        mastery_scores = {name: float(row["score"]) for name, row in mastery_rows.items()}
        if difficulty is None:
            if mastery_scores:
                average = sum(mastery_scores.values()) / len(mastery_scores)
                target = difficulty_for_mastery(average)
            else:
                target = 2
        else:
            target = difficulty

        recent_ids: set[str] = set()
        try:
            recent_rows = self.storage.recent_attempts(student_id, limit=40)
            recent_ids = {row["question_id"] for row in recent_rows if row.get("question_id")}
        except Exception:
            pass

        first = _pick_question(
            questions,
            target_difficulty=target,
            used_ids=set(),
            mastery=mastery_scores,
            recent_ids=recent_ids,
        )
        assert first is not None

        remaining = [question.id for question in questions if question.id != first.id]
        random.shuffle(remaining)

        state = {
            "questions": [question.state() for question in questions],
            "remaining": remaining,
            "current": first.id,
            "answered": 0,
            "correct": 0,
            "total": total,
            "score": 0.0,
            "target_difficulty": target,
            "topic": topic,
        }
        quiz_id = self.storage.create_quiz(
            student_id=student_id,
            class_level=class_level,
            subject=subject,
            topic=topic,
            state=state,
        )
        return {
            "quiz_id": quiz_id,
            "student_id": student_id,
            "class_level": class_level,
            "subject": subject,
            "topic": topic,
            "total": total,
            "question": first.public(),
            "progress": {
                "answered": 0,
                "total": total,
                "correct": 0,
                "score": 0.0,
            },
            "mastery": self._mastery_payload(student_id),
            "source": knowledge.source_kind,
        }

    def answer(
        self,
        quiz_id: str,
        *,
        question_id: str,
        answer: str = "",
        answer_index: int | None = None,
        response_ms: int | None = None,
    ) -> dict[str, Any]:
        quiz = self.storage.get_quiz(quiz_id)
        if quiz is None:
            raise ValueError("Quiz not found")
        state = quiz["state"]
        current = state.get("current")
        if quiz["completed"] or not current:
            raise ValueError("This quiz is already complete")
        if question_id != current:
            raise ValueError("That question is not the current one")

        records = {item["id"]: QuizQuestion.from_state(item) for item in state["questions"]}
        question = records.get(question_id)
        if question is None:
            raise ValueError("Question not found in this quiz")
        correct, response, reason, evaluator = grade_answer_detailed(
            question, answer=answer, answer_index=answer_index, llm=self.llm
        )

        student_id = quiz["student_id"]
        previous = self.storage.get_mastery(student_id, question.topic)
        previous_score = float(previous["score"]) if previous else 0.5
        previous_attempts = int(previous["attempts"]) if previous else 0
        previous_correct = int(previous["correct"]) if previous else 0
        new_score = update_mastery_score(
            previous_score,
            correct=correct,
            difficulty=question.difficulty,
            response_ms=response_ms,
        )
        mastery = self.storage.save_mastery(
            student_id,
            question.topic,
            attempts=previous_attempts + 1,
            correct=previous_correct + int(correct),
            score=new_score,
        )
        mastery_payload = {
            "student_id": mastery["student_id"],
            "topic": mastery["topic"],
            "mastery": mastery["score"],
            "attempts": mastery["attempts"],
            "correct": mastery["correct"],
            "updated_at": mastery["updated_at"],
        }
        self.storage.record_attempt(
            quiz_id=quiz_id,
            student_id=student_id,
            question_id=question.id,
            topic=question.topic,
            difficulty=question.difficulty,
            prompt=question.prompt,
            expected=question.answer,
            response=response,
            correct=correct,
            response_ms=response_ms,
        )

        state["answered"] = int(state.get("answered", 0)) + 1
        state["correct"] = int(state.get("correct", 0)) + int(correct)
        state["score"] = state["correct"] / max(1, state["answered"])
        state["remaining"] = [
            identifier
            for identifier in state.get("remaining", [])
            if identifier != question.id
        ]

        target = difficulty_for_mastery(new_score)
        if correct and target < question.difficulty:
            target = question.difficulty
        if not correct and target > question.difficulty:
            target = question.difficulty
        state["target_difficulty"] = target

        mastery_scores = {
            row["topic"]: float(row["score"])
            for row in self.storage.list_mastery(student_id)
        }
        remaining_questions = [
            records[identifier]
            for identifier in state.get("remaining", [])
            if identifier in records
        ]

        recent_ids: set[str] = set()
        try:
            recent_rows = self.storage.recent_attempts(student_id, limit=40)
            recent_ids = {row["question_id"] for row in recent_rows if row.get("question_id")}
        except Exception:
            pass

        next_question = None
        if state["answered"] < int(state["total"]):
            next_question = _pick_question(
                remaining_questions,
                target_difficulty=target,
                used_ids=set(),
                mastery=mastery_scores,
                recent_ids=recent_ids,
            )
        completed = next_question is None
        state["current"] = next_question.id if next_question else None
        self.storage.update_quiz(
            quiz_id,
            state=state,
            completed=completed,
            score=state["score"],
        )

        return {
            "quiz_id": quiz_id,
            "question_id": question.id,
            "correct": correct,
            "expected": question.answer,
            "response": response,
            "feedback": (
                f"Correct! {reason}"
                if correct
                else f"Not quite. {reason}"
            ),
            "evaluation_reason": reason,
            "evaluator": evaluator,
            "explanation": (question.explanation or "").strip()
            or (
                f"**Concept:** {question.topic}\n\n"
                f"**Expected Answer:** {question.answer}\n\n"
                f"**Why this is correct:** According to the NCERT Class 10 {question.topic} syllabus, "
                f"this principle establishes the foundation for understanding related proofs and problem solving."
            ),
            "topic": question.topic,
            "difficulty": question.difficulty,
            "mastery": mastery_payload,
            "progress": {
                "answered": state["answered"],
                "total": state["total"],
                "correct": state["correct"],
                "score": round(state["score"], 4),
            },
            "next_question": next_question.public() if next_question else None,
            "completed": completed,
            "target_difficulty": target,
            "gaps": self.gaps(student_id, limit=3),
        }

    def gaps(self, student_id: str, *, limit: int = 5) -> dict[str, Any]:
        from ila.gaps import KNOWLEDGE_GAP_CLASSIFIER

        rows = self.storage.list_mastery(student_id)
        total_attempts = sum(int(row["attempts"]) for row in rows)
        overall = (
            sum(float(row["score"]) * int(row["attempts"]) for row in rows) / total_attempts
            if total_attempts
            else 0.0
        )
        recent = self.storage.recent_attempts(student_id, limit=200)
        # Calculate topic avg response times
        topic_times: dict[str, list[int]] = {}
        for a in recent:
            if a.get("response_ms"):
                topic_times.setdefault(a["topic"], []).append(int(a["response_ms"]))

        diagnoses = []
        for row in rows:
            t_name = row["topic"]
            t_times = topic_times.get(t_name, [])
            avg_ms = int(sum(t_times) / len(t_times)) if t_times else 5000
            diag = KNOWLEDGE_GAP_CLASSIFIER.diagnose_topic(
                t_name,
                score=float(row["score"]),
                attempts=int(row["attempts"]),
                correct=int(row["correct"]),
                avg_response_ms=avg_ms,
            )
            diagnoses.append(diag)

        # Sort by remediation priority (Critical Gap first, then highest gap probability)
        diagnoses.sort(key=lambda d: (d.remediation_priority, -d.gap_probability, d.mastery))
        top_gaps = [d.to_dict() for d in diagnoses[: max(1, limit)]]

        return {
            "student_id": student_id,
            "gaps": top_gaps,
            "attempts": total_attempts,
            "overall": round(overall, 4),
            "classifier_model": KNOWLEDGE_GAP_CLASSIFIER.model_type,
        }

    def _mastery_payload(self, student_id: str) -> list[dict[str, Any]]:
        return [
            {
                "topic": row["topic"],
                "mastery": round(float(row["score"]), 4),
                "attempts": int(row["attempts"]),
                "correct": int(row["correct"]),
            }
            for row in self.storage.list_mastery(student_id)
        ]
