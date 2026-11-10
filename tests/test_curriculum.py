"""NCERT curriculum matching and its effect on the notes prompt."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from ila.curriculum import (
    CLASS_LEVELS,
    SUBJECTS,
    build_syllabus_context,
    course_catalogue,
    get_course,
    list_courses,
    match_chapters,
    normalize_subject,
)
from ila.demo import DEMOS, DEMOS_BY_ID, find_demo
from ila.llm.base import LlmInfo, Message
from ila.notes import NotesGenerator, TranscriptLine

LIGHT_TEXT = (
    "Today we study light, reflection and refraction from Chapter 9 of the NCERT Class 10 "
    "Science book. A concave mirror converges light and a convex mirror diverges it. The "
    "refractive index measures how much a medium slows down light."
)

MOTION_TEXT = (
    "Today we discuss motion, distance, displacement, speed, velocity and acceleration. "
    "A velocity-time graph gives acceleration, and the area under it gives displacement."
)


class CapturingLlm:
    def __init__(self, reply: str, *, available: bool = True) -> None:
        self.reply = reply
        self._available = available
        self.messages: list[list[Message]] = []
        self.calls = 0

    @property
    def info(self) -> LlmInfo:
        return LlmInfo(engine="fake", model="fake-2b", profile="balanced")

    @property
    def available(self) -> bool:
        return self._available

    def complete(
        self,
        messages: Sequence[Message],
        *,
        max_tokens: int = 320,
        temperature: float = 0.2,
        stop: Sequence[str] | None = None,
    ) -> str:
        self.calls += 1
        self.messages.append(list(messages))
        return self.reply


def test_all_six_ncert_courses_are_available() -> None:
    assert len(list_courses()) == 6
    for class_level in CLASS_LEVELS:
        for subject in SUBJECTS:
            course = get_course(class_level, subject)
            assert course.chapters
            assert course.label.startswith(f"Class {class_level}")


def test_catalogue_is_json_ready() -> None:
    catalogue = course_catalogue()
    assert len(catalogue) == 6
    first = catalogue[0]
    assert isinstance(first["chapters"], list)
    assert {"number", "title"} <= set(first["chapters"][0])


def test_subject_aliases() -> None:
    assert normalize_subject("Mathematics") == "maths"
    assert normalize_subject("math") == "maths"
    assert normalize_subject("SCIENCE") == "science"
    with pytest.raises(ValueError):
        normalize_subject("history")


def test_invalid_class_is_rejected() -> None:
    with pytest.raises(ValueError):
        get_course(11, "science")


def test_light_lecture_matches_chapter_nine() -> None:
    context = build_syllabus_context(LIGHT_TEXT, 10, "science")
    assert context.matches
    top = context.matches[0]
    assert top.chapter.number == 9
    assert "light" in top.matched_terms
    assert "reflection" in top.matched_terms
    assert "refraction" in top.matched_terms


def test_motion_lecture_does_not_match_light() -> None:
    context = build_syllabus_context(MOTION_TEXT, 9, "science")
    assert context.matches
    assert context.matches[0].chapter.number == 7
    assert all(match.chapter.title != "Light" for match in context.matches)


def test_explicit_chapter_mention_is_strong_evidence() -> None:
    course = get_course(10, "maths")
    matches = match_chapters("Chapter 4 is about quadratic equations.", course)
    assert matches[0].chapter.number == 4


def test_prompt_keeps_grounding_rules() -> None:
    prompt = build_syllabus_context(LIGHT_TEXT, 10, "science").prompt()
    assert "Class 10 Science" in prompt
    assert "Chapter 9" in prompt
    assert "Do not add facts" in prompt
    assert "terminology hint" in prompt


def test_notes_prompt_gets_syllabus_context_and_markdown_section() -> None:
    reply = """SUMMARY: Light reflects from mirrors and refracts when it moves between media.
POINTS:
- The angle of incidence is equal to the angle of reflection.
- A concave mirror converges light and a convex mirror diverges light.
- Refraction happens because the speed of light changes between media.
TERMS:
- reflection: the bouncing back of light from a surface
"""
    demo = DEMOS_BY_ID["class10-science-light"]
    lines = [TranscriptLine(line.text, line.start, line.end) for line in demo.lines]
    context = build_syllabus_context(" ".join(line.text for line in lines), 10, "science")
    llm = CapturingLlm(reply)

    result = NotesGenerator(llm).generate(lines, title="Light", syllabus=context)

    assert result.used_llm is True
    assert result.curriculum is not None
    assert result.curriculum["matches"][0]["number"] == 9
    assert llm.messages
    system = llm.messages[0][0]
    assert system["role"] == "system"
    assert "NCERT" in system["content"]
    assert "Chapter 9" in system["content"]
    assert "Never add outside facts" in system["content"]
    markdown = result.to_markdown()
    assert "## Syllabus alignment" in markdown
    assert "Light - Reflection and Refraction" in markdown


def test_extractive_notes_still_report_curriculum() -> None:
    demo = DEMOS_BY_ID["class10-science-light"]
    lines = [TranscriptLine(line.text, line.start, line.end) for line in demo.lines]
    context = build_syllabus_context(" ".join(line.text for line in lines), 10, "science")
    result = NotesGenerator(CapturingLlm("", available=False)).generate(
        lines, title="Light", syllabus=context
    )
    assert result.used_llm is False
    assert result.curriculum is not None


def test_demo_for_every_class_and_subject() -> None:
    for class_level in CLASS_LEVELS:
        for subject in SUBJECTS:
            demo, exact = find_demo(class_level, subject)
            assert exact is True
            assert demo.class_level == class_level
            assert demo.subject == subject
            assert len(demo.lines) >= 8


def test_demo_fallback_is_explicit() -> None:
    demo, exact = find_demo(10, "science")
    assert exact is True
    assert demo is not None
    assert len(DEMOS) == 6
