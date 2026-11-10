"""Pipeline behaviour with a fake ASR engine (no model download needed)."""

from __future__ import annotations

import numpy as np
import pytest

from ila.asr.base import AsrInfo, AsrProvider, TranscriptResult
from ila.audio import ArraySource
from ila.config import PartialSettings
from ila.pipeline import CaptionPipeline
from ila.segmenter import SpeechSegmenter
from tests.conftest import silence, speech_like

SR = 16_000


class FakeAsr:
    """Records calls and returns a canned transcript."""

    def __init__(self, text: str = "hello world", *, no_speech: float = 0.0, logprob: float = -0.1):
        self.text = text
        self.no_speech = no_speech
        self.logprob = logprob
        self.calls: list[tuple[float, str | None]] = []

    @property
    def info(self) -> AsrInfo:
        return AsrInfo("fake", "tiny", "cpu", "int8")

    def transcribe(
        self,
        audio: np.ndarray,
        *,
        initial_prompt: str | None = None,
        language: str | None = None,
    ) -> TranscriptResult:
        self.calls.append((float(audio.size) / SR, initial_prompt))
        return TranscriptResult(
            text=f"  {self.text}  ",
            language="en",
            avg_logprob=self.logprob,
            no_speech_prob=self.no_speech,
            duration_s=float(audio.size) / SR,
        )


def build(asr: FakeAsr, audio: np.ndarray, *, partials: bool = True) -> CaptionPipeline:
    source = ArraySource(audio, sample_rate=SR, block_ms=40)
    return CaptionPipeline(
        source,
        asr,
        segmenter=SpeechSegmenter(SR, partial_after_s=1.0, partial_interval_s=1.5),
        partials=PartialSettings(enabled=partials, after_s=1.0, interval_s=1.5),
    )


def test_fake_provider_satisfies_protocol():
    assert isinstance(FakeAsr(), AsrProvider)


def test_partials_precede_a_single_clean_final():
    audio = np.concatenate([silence(0.5), speech_like(4.0), silence(1.0)])
    events = list(build(FakeAsr(), audio).events())

    partials = [event for event in events if not event.final]
    found = [event for event in events if event.final]

    assert len(found) == 1
    assert len(partials) >= 2
    assert {event.utterance_id for event in partials} == {found[0].utterance_id}
    assert found[0].text == "hello world"
    assert events[-1].final is True


def test_previous_text_seeds_the_next_prompt():
    audio = np.concatenate(
        [silence(0.5), speech_like(1.5), silence(0.9), speech_like(1.5), silence(0.9)]
    )
    asr = FakeAsr()
    found = [event for event in build(asr, audio).events() if event.final]

    assert len(found) == 2
    first_prompt = asr.calls[0][1]
    last_prompt = asr.calls[-1][1]
    assert first_prompt is None
    assert last_prompt is not None and "hello world" in last_prompt


def test_low_confidence_final_is_dropped_as_hallucination():
    audio = np.concatenate([silence(0.5), speech_like(1.5), silence(1.0)])
    asr = FakeAsr(no_speech=0.95, logprob=-1.8)
    events = list(build(asr, audio, partials=False).events())

    assert events == []
    assert asr.calls  # the audio was still submitted to the model


def test_disabling_partials_hides_previews_only():
    audio = np.concatenate([silence(0.5), speech_like(4.0), silence(1.0)])
    events = list(build(FakeAsr(), audio, partials=False).events())

    assert len(events) == 1
    assert events[0].final is True


def test_stop_callback_ends_the_stream_early():
    audio = np.concatenate([silence(0.5), speech_like(2.0), silence(1.0)])
    pipeline = build(FakeAsr(), audio)
    assert list(pipeline.events(stop=lambda: True)) == []


def test_events_serialize_with_stable_schema():
    audio = np.concatenate([silence(0.3), speech_like(1.2), silence(0.8)])
    event = next(iter(build(FakeAsr(), audio, partials=False).events()))
    payload = event.to_dict()

    assert payload["type"] == "caption"
    assert payload["kind"] == "final"
    assert payload["schema"] == 1
    assert set(payload) >= {"utterance_id", "text", "start", "end", "latency_ms"}


def test_empty_transcript_is_not_emitted():
    audio = np.concatenate([silence(0.3), speech_like(1.2), silence(0.8)])
    events = list(build(FakeAsr(text="   "), audio, partials=False).events())
    assert events == []


@pytest.mark.parametrize("block_ms", [10, 40, 100])
def test_block_size_does_not_change_transcript(block_ms: int):
    audio = np.concatenate([silence(0.5), speech_like(1.4), silence(1.0)])
    source = ArraySource(audio, sample_rate=SR, block_ms=block_ms)
    pipeline = CaptionPipeline(
        source,
        FakeAsr(),
        segmenter=SpeechSegmenter(SR),
        partials=PartialSettings(enabled=False),
    )
    found = [event for event in pipeline.events() if event.final]
    assert len(found) == 1
