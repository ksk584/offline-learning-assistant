"""Shared test fixtures: synthetic audio that behaves like real speech input."""

from __future__ import annotations

import numpy as np
import pytest

SAMPLE_RATE = 16_000


def tone(seconds: float, *, dbfs: float = -20.0, freq: float = 220.0) -> np.ndarray:
    """Sine wave at a known loudness (RMS dBFS)."""
    amplitude = 10 ** (dbfs / 20) * np.sqrt(2.0)
    samples = int(round(seconds * SAMPLE_RATE))
    t = np.arange(samples, dtype=np.float32) / SAMPLE_RATE
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def silence(seconds: float) -> np.ndarray:
    return np.zeros(int(round(seconds * SAMPLE_RATE)), dtype=np.float32)


def noise(seconds: float, *, dbfs: float = -45.0, seed: int = 7) -> np.ndarray:
    """Low-level room tone."""
    rng = np.random.default_rng(seed)
    samples = int(round(seconds * SAMPLE_RATE))
    amplitude = 10 ** (dbfs / 20)
    return (rng.standard_normal(samples) * amplitude).astype(np.float32)


def speech_like(seconds: float, *, dbfs: float = -20.0) -> np.ndarray:
    """Amplitude-modulated tone: closer to speech than a steady sine."""
    base = tone(seconds, dbfs=dbfs)
    mod = 0.55 + 0.45 * np.sin(2 * np.pi * 3.5 * np.arange(base.size) / SAMPLE_RATE)
    return (base * mod).astype(np.float32)


@pytest.fixture
def sr() -> int:
    return SAMPLE_RATE
