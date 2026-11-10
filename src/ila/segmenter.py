"""Energy-based VAD and utterance segmentation.

Streaming ASR quality depends almost entirely on where you cut the audio. This
module tracks an adaptive noise floor, applies hysteresis to find speech
boundaries, keeps pre/post-roll so words are not clipped, and only finalizes an
utterance once the speaker has actually stopped.

The segmenter is a pure function of the audio it is fed: no threads, no
sleeping, no I/O. That makes it fully unit-testable with synthetic signals.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

import numpy as np

_DB_FLOOR = 1e-10


def rms_db(frame: np.ndarray) -> float:
    """Frame loudness in dBFS (clamped to a sane floor)."""
    if frame.size == 0:
        return -100.0
    samples = frame.astype(np.float64, copy=False)
    rms = float(np.sqrt(np.mean(samples * samples)))
    return 20.0 * math.log10(max(rms, _DB_FLOOR))


@dataclass(slots=True)
class Utterance:
    """A window of speech, either in progress (``final=False``) or complete."""

    utterance_id: int
    start: float
    end: float
    audio: np.ndarray
    final: bool

    @property
    def duration_s(self) -> float:
        return max(0.0, self.end - self.start)


class SpeechSegmenter:
    """Turns a stream of audio blocks into utterance windows.

    Feed arbitrary block sizes via :meth:`feed`; it buffers internally and only
    consumes whole VAD frames. Call :meth:`flush` at end of stream.
    """

    def __init__(
        self,
        sample_rate: int = 16_000,
        *,
        frame_ms: int = 30,
        start_margin_db: float = 8.0,
        end_margin_db: float = 3.0,
        min_silence_ms: int = 450,
        pre_roll_ms: int = 240,
        post_roll_ms: int = 240,
        min_speech_ms: int = 350,
        max_segment_s: float = 20.0,
        partial_after_s: float = 1.2,
        partial_interval_s: float = 2.0,
        initial_noise_db: float = -55.0,
    ) -> None:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if frame_ms <= 0:
            raise ValueError("frame_ms must be positive")

        self.sample_rate = int(sample_rate)
        self.frame_samples = max(1, int(round(self.sample_rate * frame_ms / 1000)))
        self.frame_s = self.frame_samples / self.sample_rate

        self.start_margin_db = float(start_margin_db)
        self.end_margin_db = float(end_margin_db)

        self._min_silence_frames = self._frames(min_silence_ms)
        self._pre_roll_frames = max(1, self._frames(pre_roll_ms))
        self._post_roll_frames = self._frames(post_roll_ms, minimum=0)
        self._min_speech_frames = max(1, self._frames(min_speech_ms))
        self._max_frames = max(2, int(max_segment_s / self.frame_s))
        self._partial_after_frames = max(1, self._frames(partial_after_s * 1000))
        self._partial_interval_frames = max(1, self._frames(partial_interval_s * 1000))
        #: Search window used to find a quiet cut point on a forced split.
        self._split_search_frames = max(2, self._frames(1500))

        self._residual = np.zeros(0, dtype=np.float32)
        self._frames_seen = 0
        self._noise_db = float(initial_noise_db)
        self._initial_noise_db = float(initial_noise_db)
        #: Rolling window used to estimate the room's noise floor.
        self._level_history: deque[float] = deque(maxlen=max(10, self._frames(10_000)))
        self._calibration_frames = max(3, self._frames(450))
        self._noise_rise_db_per_frame = 0.15

        self._preroll: deque[np.ndarray] = deque(maxlen=self._pre_roll_frames)
        self._speech_run = 0

        self._in_utterance = False
        self._utt_frames: list[np.ndarray] = []
        self._utt_db: list[float] = []
        self._utt_start_frame = 0
        self._last_voice_frame = -1
        self._silence_run = 0
        self._next_partial_frame = 0
        self._current_id = -1
        self._next_id = 0

    # ------------------------------------------------------------------ helpers
    def _frames(self, ms: float, *, minimum: int = 1) -> int:
        return max(minimum, int(round(ms / 1000 / self.frame_s)))

    def _frame_time(self, frame_index: int) -> float:
        return frame_index * self.frame_s

    @property
    def in_utterance(self) -> bool:
        return self._in_utterance

    @property
    def noise_floor_db(self) -> float:
        return self._noise_db

    def _update_noise_floor(self, db: float) -> None:
        """Track the room tone with a rolling low percentile.

        Downward moves are immediate (a quiet room can be trusted instantly),
        upward moves are rate limited so a long stretch of speech cannot be
        mistaken for noise. During the first half second, if the room starts
        quiet, the floor snaps to it instead of creeping down to it.
        """
        self._level_history.append(db)
        if len(self._level_history) < 5:
            candidate = min(self._level_history)
        else:
            candidate = float(np.percentile(self._level_history, 12))
        candidate = min(max(candidate, -70.0), -20.0)

        if candidate < self._noise_db:
            self._noise_db = candidate
        else:
            self._noise_db = min(candidate, self._noise_db + self._noise_rise_db_per_frame)

        if len(self._level_history) == self._calibration_frames:
            # Only trust an initial jump if the stream evidently starts quiet;
            # otherwise the rate-limited climb handles a noisy room.
            quiet_start = min(self._level_history)
            if quiet_start <= self._initial_noise_db + 15.0:
                self._noise_db = max(quiet_start, -70.0)

    # --------------------------------------------------------------------- API
    def feed(self, block: np.ndarray) -> list[Utterance]:
        """Consume audio (mono float32) and return any utterance events."""
        if block is None or block.size == 0:
            return []
        if block.ndim > 1:
            block = block.reshape(-1)
        block = np.ascontiguousarray(block, dtype=np.float32)

        if self._residual.size:
            block = np.concatenate((self._residual, block))

        events: list[Utterance] = []
        offset = 0
        while block.size - offset >= self.frame_samples:
            frame = block[offset : offset + self.frame_samples]
            offset += self.frame_samples
            events.extend(self._process_frame(frame))
        self._residual = block[offset:].copy()
        return events

    def flush(self) -> list[Utterance]:
        """Finalize any in-progress utterance (end of stream)."""
        if not self._in_utterance:
            self._residual = np.zeros(0, dtype=np.float32)
            return []
        events = self._finalize()
        self._residual = np.zeros(0, dtype=np.float32)
        self._preroll.clear()
        return events

    # ------------------------------------------------------------------ internal
    def _process_frame(self, frame: np.ndarray) -> list[Utterance]:
        index = self._frames_seen
        self._frames_seen += 1
        db = rms_db(frame)
        self._update_noise_floor(db)
        self._preroll.append(frame)

        start_threshold = self._noise_db + self.start_margin_db
        end_threshold = self._noise_db + self.end_margin_db

        if not self._in_utterance:
            if db >= start_threshold:
                self._speech_run += 1
            else:
                self._speech_run = 0
            if self._speech_run < 2:
                return []
            # The pre-roll snapshot already contains the current frame.
            self._begin_utterance(index)
        else:
            self._utt_frames.append(frame)
            self._utt_db.append(db)

        if db >= end_threshold:
            self._last_voice_frame = len(self._utt_frames) - 1
            self._silence_run = 0
        else:
            self._silence_run += 1

        events: list[Utterance] = []
        reached_silence = self._silence_run >= self._min_silence_frames
        reached_length = len(self._utt_frames) >= self._max_frames

        if not reached_silence and not reached_length:
            events.extend(self._maybe_partial(index))

        if reached_silence:
            events.extend(self._finalize())
            # Keep the pre-roll clean for the next onset.
            self._preroll.clear()
        elif reached_length:
            events.extend(self._split_long_utterance(index))
        return events

    def _begin_utterance(self, index: int) -> None:
        frames = list(self._preroll)
        if not frames:  # pragma: no cover - defensive
            return
        self._utt_frames = frames
        self._utt_db = [rms_db(frame) for frame in frames]
        self._utt_start_frame = max(0, index - len(frames) + 1)
        self._last_voice_frame = len(frames) - 1
        self._silence_run = 0
        self._speech_run = 0
        self._in_utterance = True
        self._current_id = self._next_id
        self._next_id += 1
        self._next_partial_frame = index + self._partial_after_frames

    def _maybe_partial(self, index: int) -> list[Utterance]:
        if index < self._next_partial_frame:
            return []
        if len(self._utt_frames) < self._partial_after_frames:
            return []
        self._next_partial_frame = index + self._partial_interval_frames
        return [
            Utterance(
                utterance_id=self._current_id,
                start=self._frame_time(self._utt_start_frame),
                end=self._frame_time(index + 1),
                audio=np.concatenate(self._utt_frames),
                final=False,
            )
        ]

    def _voiced_frames(self) -> int:
        threshold = self._noise_db + self.end_margin_db
        return sum(1 for db in self._utt_db if db >= threshold)

    def _finalize(self) -> list[Utterance]:
        frames = self._utt_frames
        if not frames:
            self._reset_utterance()
            return []

        voiced = self._voiced_frames()
        keep = len(frames)
        if self._last_voice_frame >= 0:
            keep = min(len(frames), self._last_voice_frame + 1 + self._post_roll_frames)
        frames = frames[:keep]

        utterance_id = self._current_id
        start = self._frame_time(self._utt_start_frame)
        end = start + len(frames) * self.frame_s
        audio = np.concatenate(frames)
        self._reset_utterance()

        if voiced < self._min_speech_frames:
            return []
        return [Utterance(utterance_id, start, end, audio, True)]

    def _split_long_utterance(self, index: int) -> list[Utterance]:
        """Cut an over-long utterance at its quietest recent frame.

        Cutting at a local energy minimum lands between words far more often
        than a hard time cut, which keeps transcription accuracy intact.
        """
        total = len(self._utt_frames)
        search = min(self._split_search_frames, total)
        tail = np.asarray(self._utt_db[total - search :], dtype=np.float64)
        cut = total - search + int(np.argmin(tail))
        cut = max(cut, self._min_speech_frames)
        rest = total - cut

        if rest < self._frames(400):
            # Too little room for a second utterance: close this one cleanly.
            events = self._finalize()
            self._preroll.clear()
            return events

        left_frames = self._utt_frames[:cut]
        left_db = self._utt_db[:cut]
        utterance_id = self._current_id
        start = self._frame_time(self._utt_start_frame)
        end = start + cut * self.frame_s
        audio = np.concatenate(left_frames)
        voiced = sum(1 for db in left_db if db >= self._noise_db + self.end_margin_db)

        self._utt_frames = self._utt_frames[cut:]
        self._utt_db = self._utt_db[cut:]
        self._utt_start_frame += cut
        self._last_voice_frame = max(0, len(self._utt_frames) - 1)
        self._silence_run = 0
        self._current_id = self._next_id
        self._next_id += 1
        self._next_partial_frame = index + self._partial_interval_frames

        if voiced < self._min_speech_frames:
            return []
        return [Utterance(utterance_id, start, end, audio, True)]

    def _reset_utterance(self) -> None:
        self._in_utterance = False
        self._utt_frames = []
        self._utt_db = []
        self._silence_run = 0
        self._speech_run = 0
        self._last_voice_frame = -1
        self._utt_start_frame = 0
        self._next_partial_frame = 0
