"""Hardware detection and model-profile tests (no native dependencies)."""

from __future__ import annotations

import hashlib

import pytest

from ila.hardware import PROFILES, Hardware, detect, physical_cores, suggest_profile
from ila.llm.download import verify_model
from ila.llm.profiles import PROFILE_MODELS, ModelSpec, resolve_profile


def test_profiles_cover_every_supported_model() -> None:
    assert set(PROFILE_MODELS) == set(PROFILES)


def test_potato_profile_for_small_machines() -> None:
    profile, reason = suggest_profile(4.0, 4)
    assert profile == "potato"
    assert "RAM" in reason


def test_potato_profile_for_two_threads() -> None:
    assert suggest_profile(16.0, 2)[0] == "potato"


def test_balanced_profile_for_mid_range_laptop() -> None:
    assert suggest_profile(8.0, 8)[0] == "balanced"


def test_full_profile_for_strong_machine() -> None:
    assert suggest_profile(32.0, 16)[0] == "full"


def test_unknown_ram_is_safe() -> None:
    assert suggest_profile(0.0, 8)[0] == "balanced"


def test_resolve_profile_validates_explicit_names() -> None:
    assert resolve_profile("potato") == "potato"
    assert resolve_profile("auto", ram_gb=4.0, cores=4) == "potato"
    try:
        resolve_profile("huge")
    except ValueError as exc:
        assert "huge" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_detect_returns_a_supported_profile() -> None:
    hw = detect()
    assert isinstance(hw, Hardware)
    assert hw.suggested_profile in PROFILES
    assert hw.logical_cores >= 1
    assert hw.physical_cores >= 1


def test_physical_cores_assumes_smt() -> None:
    assert physical_cores(12) == 6
    assert physical_cores(1) == 1


def _spec(data: bytes) -> ModelSpec:
    return ModelSpec(
        repo="test/model",
        filename="model.gguf",
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        download_gb=0.0,
        ram_gb=0.0,
        note="test",
    )


def test_verify_model_accepts_matching_file(tmp_path) -> None:
    data = b"not a real model"
    path = tmp_path / "model.gguf"
    path.write_bytes(data)
    verify_model(path, _spec(data))


def test_verify_model_rejects_truncated_file(tmp_path) -> None:
    data = b"not a real model"
    path = tmp_path / "model.gguf"
    path.write_bytes(data[:-4])
    with pytest.raises(RuntimeError, match="expected"):
        verify_model(path, _spec(data))


def test_verify_model_rejects_wrong_checksum(tmp_path) -> None:
    data = b"not a real model"
    path = tmp_path / "model.gguf"
    path.write_bytes(data)
    spec = _spec(data)
    tampered = ModelSpec(
        repo=spec.repo,
        filename=spec.filename,
        size_bytes=spec.size_bytes,
        sha256="0" * 64,
        download_gb=0.0,
        ram_gb=0.0,
        note="test",
    )
    with pytest.raises(RuntimeError, match="SHA-256"):
        verify_model(path, tampered)
