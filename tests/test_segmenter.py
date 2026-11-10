"""Segmentation behaviour on synthetic audio (no model required)."""

from __future__ import annotations

import numpy as np

from ila.segmenter import SpeechSegmenter, rms_db
from tests.conftest import noise, silence, speech_like, tone

SR = 16_000


def collect(segmenter: SpeechSegmenter, audio: np.ndarray, block: int | None = None):
    events = []
    step = block or audio.size
    for start in range(0, audio.size, step):
        events.extend(segmenter.feed(audio[start : start + step]))
    events.extend(segmenter.flush())
    return events


def finals(events):
    return [event for event in events if event.final]


def test_rms_db_of_known_signal():
    assert abs(rms_db(tone(0.1, dbfs=-20)) + 20.0) < 0.5
    assert rms_db(silence(0.1)) < -90.0


def test_single_utterance_with_roll_padding():
    audio = np.concatenate([silence(1.0), speech_like(1.0), silence(1.0)])
    detected = finals(collect(SpeechSegmenter(SR), audio))

    assert len(detected) == 1
    utterance = detected[0]
    assert 0.6 < utterance.start < 1.05  # pre-roll reaches slightly before onset
    assert 1.2 < utterance.duration_s < 1.7
    assert utterance.audio.dtype == np.float32


def test_pause_splits_two_utterances():
    audio = np.concatenate(
        [silence(0.8), speech_like(1.0), silence(0.9), speech_like(1.0), silence(0.8)]
    )
    detected = finals(collect(SpeechSegmenter(SR), audio))

    assert len(detected) == 2
    assert detected[0].start < detected[1].start
    assert detected[0].utterance_id < detected[1].utterance_id


def test_short_blip_is_discarded():
    audio = np.concatenate([silence(0.5), tone(0.12), silence(1.0)])
    assert finals(collect(SpeechSegmenter(SR), audio)) == []


def test_long_speech_produces_partials_then_one_final():
    audio = np.concatenate([silence(0.4), speech_like(6.0), silence(1.0)])
    events = collect(SpeechSegmenter(SR), audio)
    partials = [event for event in events if not event.final]
    detected = finals(events)

    assert len(detected) == 1
    assert len(partials) >= 2
    assert {event.utterance_id for event in partials} == {detected[0].utterance_id}


def test_forced_split_caps_utterance_length():
    segmenter = SpeechSegmenter(SR, max_segment_s=3.0)
    audio = np.concatenate([silence(0.3), speech_like(9.0), silence(0.8)])
    detected = finals(collect(segmenter, audio))

    assert len(detected) >= 2
    assert all(event.duration_s <= 3.4 for event in detected)


def test_flush_finalizes_trailing_speech():
    audio = np.concatenate([silence(0.3), speech_like(1.5)])
    detected = finals(collect(SpeechSegmenter(SR), audio))

    assert len(detected) == 1
    assert detected[0].end > 1.5


def test_room_tone_is_not_transcribed_as_speech():
    audio = np.concatenate([noise(2.0), speech_like(1.0), noise(1.0)])
    detected = finals(collect(SpeechSegmenter(SR), audio))

    assert len(detected) == 1


def test_arbitrary_block_sizes_do_not_change_boundaries():
    audio = np.concatenate(
        [silence(0.7), speech_like(1.2), silence(0.9), speech_like(1.1), silence(0.7)]
    )

    whole = collect(SpeechSegmenter(SR), audio)
    chunked = collect(SpeechSegmenter(SR), audio, block=137)

    assert len(finals(whole)) == len(finals(chunked)) == 2
    for left, right in zip(finals(whole), finals(chunked), strict=True):
        assert abs(left.start - right.start) < 0.05
        assert abs(left.end - right.end) < 0.05
