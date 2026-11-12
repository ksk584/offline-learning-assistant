"""Auto-Remediation System for targeted practice on identified knowledge gaps.

Generates targeted practice items (fill-in-the-blank, true/false, short answer, and MCQ)
focused specifically on student weak topics using the downloaded local LLM (Qwen 3.5)
grounded on NCERT master notes and lecture transcripts, closing the adaptive feedback loop.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from ila.gaps import KNOWLEDGE_GAP_CLASSIFIER, KnowledgeGapDiagnosis
from ila.quiz import (
    QuizQuestion,
    evaluate_semantic_answer,
    grade_answer,
    update_mastery_score,
)
from ila.retrieval import KnowledgeBase, Passage, content_terms
from ila.storage import Storage

if TYPE_CHECKING:  # pragma: no cover
    from ila.llm import LlmProvider

logger = logging.getLogger(__name__)

RemediationKind = Literal["cloze", "true_false", "short_answer", "mcq"]


@dataclass(frozen=True, slots=True)
class RemediationItem:
    id: str
    kind: RemediationKind
    prompt: str
    options: tuple[str, ...]
    expected: str
    explanation: str
    topic: str
    difficulty: int
    primer: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "prompt": self.prompt,
            "options": list(self.options),
            "expected": self.expected,
            "explanation": self.explanation,
            "topic": self.topic,
            "difficulty": self.difficulty,
            "primer": self.primer,
            "source": self.source,
        }

    def public(self) -> dict[str, Any]:
        """Student-facing payload omitting the expected answer before grading."""
        return {
            "id": self.id,
            "kind": self.kind,
            "prompt": self.prompt,
            "options": list(self.options),
            "topic": self.topic,
            "difficulty": self.difficulty,
            "primer": self.primer,
            "source": self.source,
        }


class AutoRemediationEngine:
    """Manages targeted remediation pack generation and mastery feedback loop."""

    def __init__(self, storage: Storage, llm: LlmProvider | None = None) -> None:
        self.storage = storage
        self.llm = llm

    def generate_remediation_pack(
        self,
        knowledge: KnowledgeBase,
        *,
        student_id: str,
        topic: str | None = None,
        count: int = 3,
    ) -> dict[str, Any]:
        """Generate targeted practice items focusing on the student's weakest topic."""
        # 1. Identify target topic if not explicitly given
        target_topic = topic
        diagnosis: KnowledgeGapDiagnosis | None = None

        if not target_topic:
            mastery_rows = self.storage.list_mastery(student_id)
            if mastery_rows:
                # Run Knowledge Gap Classifier across topics to pick top priority
                diagnoses = [
                    KNOWLEDGE_GAP_CLASSIFIER.diagnose_topic(
                        row["topic"],
                        score=float(row["score"]),
                        attempts=int(row["attempts"]),
                        correct=int(row["correct"]),
                    )
                    for row in mastery_rows
                ]
                # Sort by highest gap probability & lowest mastery
                diagnoses.sort(key=lambda d: (-d.gap_probability, d.mastery))
                diagnosis = diagnoses[0]
                target_topic = diagnosis.topic
            else:
                # Default to first chapter topic if no history
                if knowledge.course and knowledge.course.chapters:
                    target_topic = knowledge.course.chapters[0].title
                else:
                    target_topic = "Real Numbers: Fundamental Theorem"

        # 2. Gather relevant passages for this topic
        passages = [p for p in knowledge.passages if p.is_content]
        if target_topic:
            needle = target_topic.lower()
            matching = [p for p in passages if needle in p.text.lower()]
            if matching:
                passages = matching

        context_text = "\n\n".join(p.text[:600] for p in passages[:4])

        # 3. Use Downloaded Local LLM if available to generate customized remediation items
        items: list[RemediationItem] = []
        primer = f"Core review for {target_topic}: Focus on the foundational definitions, formulas, and step-by-step theorems."

        if self.llm is not None and getattr(self.llm, "available", False):
            items, primer = self._generate_with_llm(
                self.llm,
                topic=target_topic,
                context=context_text,
                count=count,
            )

        # Fallback to grounded extractive generation if LLM didn't return enough items
        if len(items) < count:
            fallback_items = self._generate_fallback(target_topic, passages, primer, count - len(items))
            items.extend(fallback_items)

        # Store remediation pack in SQLite session if needed
        import uuid
        pack_id = f"rem-{student_id[:8]}-{abs(hash(target_topic)) % 10000}-{uuid.uuid4().hex[:6]}"
        self.storage.create_quiz(
            quiz_id=pack_id,
            student_id=student_id,
            class_level=knowledge.course.class_level if knowledge.course else 10,
            subject=knowledge.course.subject if knowledge.course else "maths",
            topic=target_topic,
            state={
                "pack_id": pack_id,
                "topic": target_topic,
                "primer": primer,
                "items": [item.to_dict() for item in items],
                "answered": 0,
                "correct": 0,
            },
        )

        return {
            "pack_id": pack_id,
            "student_id": student_id,
            "topic": target_topic,
            "primer": primer,
            "total_items": len(items),
            "items": [item.public() for item in items],
            "diagnosis": diagnosis.to_dict() if diagnosis else None,
            "source": knowledge.source_kind,
        }

    def evaluate_remediation_answer(
        self,
        *,
        pack_id: str,
        student_id: str,
        item_id: str,
        answer: str,
        selected_index: int | None = None,
        response_ms: int = 4000,
    ) -> dict[str, Any]:
        """Evaluate a remediation item answer and update student mastery."""
        quiz = self.storage.get_quiz(pack_id)
        if not quiz:
            raise ValueError(f"Remediation pack {pack_id} not found")

        state = quiz["state"]
        raw_items = state.get("items", [])
        target_item = next((it for it in raw_items if it["id"] == item_id), None)
        if not target_item:
            raise ValueError(f"Item {item_id} not found in pack")

        expected = target_item["expected"].strip()
        kind = target_item["kind"]
        options = target_item.get("options", [])
        topic = target_item["topic"]

        # Grade answer
        correct = False
        evaluator = "rule"
        reason = ""
        submitted = answer.strip()
        if kind == "mcq" and selected_index is not None and 0 <= selected_index < len(options):
            submitted = options[selected_index]
            correct = submitted.lower() == expected.lower()
            evaluator = "mcq"
            reason = "Correct option chosen." if correct else f"Selected option: {submitted}"
        elif kind == "true_false":
            correct = submitted.lower() == expected.lower()
            evaluator = "true_false"
            reason = "Exact True/False match." if correct else f"Submitted {submitted}."
        else:
            # Semantic evaluation by meaning & intent using local LLM
            correct, evaluator, reason = evaluate_semantic_answer(
                prompt=target_item["prompt"],
                expected=expected,
                submitted=submitted,
                llm=self.llm,
            )

        # Update mastery in SQLite (Feedback loop)
        prev_row = self.storage.get_mastery(student_id, topic)
        prev_score = float(prev_row["score"]) if prev_row else 0.5
        prev_attempts = int(prev_row["attempts"]) if prev_row else 0
        prev_correct = int(prev_row["correct"]) if prev_row else 0

        # Remediation gives higher recovery credit to help close gaps
        new_score = update_mastery_score(
            prev_score,
            correct=correct,
            difficulty=target_item.get("difficulty", 1),
            response_ms=response_ms,
        )
        if correct:
            new_score = min(1.0, new_score + 0.08)  # remediation boost

        updated_mastery = self.storage.save_mastery(
            student_id,
            topic,
            attempts=prev_attempts + 1,
            correct=prev_correct + (1 if correct else 0),
            score=new_score,
        )

        # Run diagnosis to show gap progression
        new_diag = KNOWLEDGE_GAP_CLASSIFIER.diagnose_topic(
            topic,
            score=new_score,
            attempts=prev_attempts + 1,
            correct=prev_correct + (1 if correct else 0),
            avg_response_ms=response_ms,
        )

        # Record attempt in SQLite
        self.storage.record_attempt(
            quiz_id=pack_id,
            student_id=student_id,
            question_id=item_id,
            topic=topic,
            difficulty=target_item.get("difficulty", 1),
            prompt=target_item["prompt"],
            expected=expected,
            response=submitted,
            correct=correct,
            response_ms=response_ms,
        )

        explanation = (target_item.get("explanation") or "").strip()
        if not explanation:
            explanation = (
                f"**Concept:** {topic}\n\n"
                f"**Expected Definition / Rule:** {expected}\n\n"
                f"**Pedagogical Breakdown:** Grounded in NCERT Class 10 {topic} syllabus. "
                f"Mastering this foundational rule closes your diagnosed learning gap and allows accurate problem-solving."
            )

        return {
            "pack_id": pack_id,
            "item_id": item_id,
            "correct": correct,
            "submitted": submitted,
            "expected": expected,
            "explanation": explanation,
            "feedback": (
                f"Excellent! {reason}"
                if correct
                else f"Keep practicing. The expected answer was: {expected}."
            ),
            "evaluation_reason": reason,
            "evaluator": evaluator,
            "previous_mastery": round(prev_score, 4),
            "new_mastery": round(new_score, 4),
            "prev_mastery": round(prev_score, 4),
            "updated_mastery": round(new_score, 4),
            "diagnosis": new_diag.to_dict(),
            "post_diagnosis": new_diag.to_dict(),
        }

    def _generate_with_llm(
        self,
        llm: LlmProvider,
        *,
        topic: str,
        context: str,
        count: int,
    ) -> tuple[list[RemediationItem], str]:
        """Use Qwen 3.5 local LLM to generate targeted conceptual remediation questions."""
        prompt = (
            f"You are an expert NCERT teacher. A student has a knowledge gap in the topic: '{topic}'.\n"
            f"Based on these syllabus excerpts:\n{context[:1200]}\n\n"
            f"Write:\n"
            f"1. A 2-sentence 'PRIMER' summarizing the core rule or formula to remember.\n"
            f"2. {count} targeted remediation questions (Fill-in-the-blank, True/False, and Short Answer).\n\n"
            f"Format your output as JSON with this exact structure:\n"
            f"{{\n"
            f'  "primer": "Two sentences explaining the key concept.",\n'
            f'  "questions": [\n'
            f'    {{"kind": "cloze", "prompt": "Sentence with ___ missing.", "expected": "word", "options": ["opt1", "opt2", "word", "opt4"], "explanation": "Why this is correct."}},\n'
            f'    {{"kind": "true_false", "prompt": "Statement about the concept.", "expected": "True", "options": ["True", "False"], "explanation": "Reasoning."}},\n'
            f'    {{"kind": "short_answer", "prompt": "Direct question asking for formula or definition.", "expected": "Brief answer", "options": [], "explanation": "Detailed explanation."}}\n'
            f"  ]\n"
            f"}}"
        )
        messages = [
            {"role": "system", "content": "You generate structured educational JSON for personalized auto-remediation drills. Output only valid JSON."},
            {"role": "user", "content": prompt},
        ]
        try:
            raw_reply = llm.complete(messages, max_tokens=550, temperature=0.15)
            # Extract JSON block
            json_match = re.search(r"\{.*\}", raw_reply, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                primer = data.get("primer", "")
                parsed_items: list[RemediationItem] = []
                for idx, q in enumerate(data.get("questions", [])):
                    kind = q.get("kind", "short_answer")
                    if kind not in ("cloze", "true_false", "short_answer", "mcq"):
                        kind = "short_answer"
                    parsed_items.append(
                        RemediationItem(
                            id=f"rem-{idx+1}-{abs(hash(q.get('prompt', ''))) % 10000}",
                            kind=kind,
                            prompt=q.get("prompt", ""),
                            options=tuple(q.get("options", [])),
                            expected=q.get("expected", ""),
                            explanation=q.get("explanation", ""),
                            topic=topic,
                            difficulty=1,  # Foundation tier for remediation
                            primer=primer,
                            source="Local LLM Remediation Generator",
                        )
                    )
                if parsed_items:
                    return parsed_items, primer
        except Exception as err:
            logger.debug("LLM auto-remediation generation failed: %s; falling back to rule-based generator", err)

        return [], f"Core review for {topic}: Review the foundational theorems and practice worked examples."

    def _generate_fallback(
        self,
        topic: str,
        passages: list[Passage],
        primer: str,
        count: int,
    ) -> list[RemediationItem]:
        """Deterministic fallback question generator for auto-remediation."""
        items: list[RemediationItem] = []
        for idx, passage in enumerate(passages[:count]):
            sentence = passage.text.split(".")[0].strip()
            words = sentence.split()
            if len(words) > 5:
                # Blank out key content word
                key_word = max(words[3:], key=len).strip(",.;:'\"()")
                prompt_cloze = sentence.replace(key_word, "______", 1)
                items.append(
                    RemediationItem(
                        id=f"rem-fb-{idx+1}",
                        kind="cloze",
                        prompt=f"Complete the rule: {prompt_cloze}",
                        options=(key_word, "constant", "variable", "factor"),
                        expected=key_word,
                        explanation=f"According to NCERT syllabus: '{sentence}'.",
                        topic=topic,
                        difficulty=1,
                        primer=primer,
                        source="NCERT Grounded Syllabus",
                    )
                )

        if not items:
            items.append(
                RemediationItem(
                    id="rem-fb-default",
                    kind="true_false",
                    prompt=f"True or False: Every topic in {topic} has a formal mathematical proof or algorithmic solution.",
                    options=("True", "False"),
                    expected="True",
                    explanation=f"Yes, all Class 10 NCERT theorems in {topic} are derived constructively.",
                    topic=topic,
                    difficulty=1,
                    primer=primer,
                    source="NCERT Curriculum",
                )
            )
        return items
