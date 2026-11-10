"""Audio sources: microphone capture and offline file playback.

Every source yields mono ``float32`` blocks at 16 kHz so downstream stages never
have to care where the audio came from.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

import numpy as np

logger = logging.getLogger(__name__)


class AudioSource(Protocol):
    """Stream of mono float32 audio blocks at ``sample_rate``."""

    sample_rate: int

    def blocks(self) -> Iterator[np.ndarray]: ...

    def close(self) -> None: ...


class _Pacer:
    """Throttles a block iterator to real time without accumulating drift."""

    def __init__(self, sample_rate: int) -> None:
        self._sample_rate = sample_rate
        self._started_at = 0.0
        self._samples = 0

    def reset(self) -> None:
        self._started_at = time.monotonic()
        self._samples = 0

    def wait(self, frames: int) -> None:
        self._samples += frames
        target = self._started_at + self._samples / self._sample_rate
        delay = target - time.monotonic()
        if delay > 0:
            time.sleep(delay)


class ArraySource:
    """Streams an already-decoded array in fixed-size blocks."""

    def __init__(
        self,
        samples: np.ndarray,
        *,
        sample_rate: int = 16_000,
        block_ms: int = 40,
        realtime: bool = False,
    ) -> None:
        self.sample_rate = sample_rate
        self._samples = np.ascontiguousarray(samples, dtype=np.float32).reshape(-1)
        self._block = max(1, int(sample_rate * block_ms / 1000))
        self._realtime = realtime

    def blocks(self) -> Iterator[np.ndarray]:
        pacer = _Pacer(self.sample_rate) if self._realtime else None
        if pacer:
            pacer.reset()
        for start in range(0, self._samples.size, self._block):
            block = self._samples[start : start + self._block]
            if block.size == 0:
                break
            yield block
            if pacer:
                pacer.wait(block.size)

    def close(self) -> None:
        return None


class FileSource(ArraySource):
    """Decode an audio/video file (anything PyAV understands) and stream it."""

    def __init__(
        self,
        path: str | Path,
        *,
        sample_rate: int = 16_000,
        block_ms: int = 40,
        realtime: bool = False,
    ) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Audio file not found: {self.path}")
        samples = decode_audio(self.path, sample_rate=sample_rate)
        super().__init__(samples, sample_rate=sample_rate, block_ms=block_ms, realtime=realtime)

    @property
    def duration_s(self) -> float:
        return float(self._samples.size) / self.sample_rate


def decode_audio(path: str | Path, *, sample_rate: int = 16_000) -> np.ndarray:
    """Decode any PyAV-supported media file to mono float32 at ``sample_rate``."""
    from faster_whisper.audio import decode_audio as fw_decode

    audio = fw_decode(str(path), sampling_rate=sample_rate)
    return np.ascontiguousarray(audio, dtype=np.float32).reshape(-1)


class MicrophoneSource:
    """Live microphone capture via PortAudio/sounddevice."""

    def __init__(
        self,
        *,
        sample_rate: int = 16_000,
        block_ms: int = 40,
        device: int | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self._block = max(1, int(sample_rate * block_ms / 1000))
        self._device = device
        self._closed = False
        self._stream = None

    def blocks(self) -> Iterator[np.ndarray]:
        try:
            import sounddevice as sd
        except OSError as exc:  # pragma: no cover - platform dependent
            raise RuntimeError(
                "Microphone support needs PortAudio. On Windows, reinstalling "
                "`sounddevice` normally restores it."
            ) from exc

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            blocksize=self._block,
            channels=1,
            dtype="float32",
            device=self._device,
        )
        with self._stream:
            logger.debug("microphone open: device=%s rate=%s", self._device, self.sample_rate)
            while not self._closed:
                data, overflowed = self._stream.read(self._block)
                if overflowed:
                    logger.debug("audio input overflow (host dropped samples)")
                if data.size == 0:
                    break
                yield np.ascontiguousarray(data[:, 0], dtype=np.float32)
        self._stream = None

    def close(self) -> None:
        self._closed = True
        if self._stream is not None:
            try:
                self._stream.stop()
            except Exception:  # pragma: no cover - best effort shutdown
                logger.debug("failed to stop microphone stream", exc_info=True)


def list_input_devices() -> list[dict[str, object]]:
    """Describe available input devices (index, name, channels, host API)."""
    import sounddevice as sd

    default_input = sd.default.device[0]
    devices: list[dict[str, object]] = []
    for index, info in enumerate(sd.query_devices()):
        if int(info["max_input_channels"]) < 1:
            continue
        host = sd.query_hostapis(info["hostapi"])["name"]
        devices.append(
            {
                "index": index,
                "name": info["name"],
                "channels": int(info["max_input_channels"]),
                "host_api": host,
                "default": index == default_input,
                "sample_rate": int(info["default_samplerate"]),
            }
        )
    return devices


def build_source(
    kind: str,
    *,
    path: str | Path | None = None,
    sample_rate: int = 16_000,
    block_ms: int = 40,
    device: int | None = None,
    realtime: bool = False,
) -> AudioSource:
    """Create an audio source by name: ``mic`` or ``file``."""
    normalized = kind.strip().lower()
    if normalized in {"mic", "microphone", "live"}:
        return MicrophoneSource(sample_rate=sample_rate, block_ms=block_ms, device=device)
    if normalized == "file":
        if path is None:
            raise ValueError("A file path is required for the 'file' source")
        return FileSource(path, sample_rate=sample_rate, block_ms=block_ms, realtime=realtime)
    raise ValueError(f"Unknown audio source: {kind!r} (expected 'mic' or 'file')")
