"""Model catalogue and profile resolution.

Only Q4_K_M GGUF files are listed: they are the best size/quality trade-off for
CPU inference, and one quantisation keeps the supported surface small. The
``potato`` model is the floor -- if it does not fit, note generation degrades to
extractive instead of failing.
"""

from __future__ import annotations

from dataclasses import dataclass

from ila import hardware


@dataclass(frozen=True, slots=True)
class ModelSpec:
    repo: str
    filename: str
    size_bytes: int
    sha256: str
    download_gb: float
    ram_gb: float
    note: str


PROFILE_MODELS: dict[str, ModelSpec] = {
    "potato": ModelSpec(
        repo="unsloth/Qwen3.5-0.8B-GGUF",
        filename="Qwen3.5-0.8B-Q4_K_M.gguf",
        size_bytes=532_517_120,
        sha256="bd258782e35f7f458f8aced1adc053e6e92e89bc735ba3be89d38a06121dc517",
        download_gb=0.53,
        ram_gb=1.3,
        note="floor tier: 4 GB RAM / 2-core machines",
    ),
    "balanced": ModelSpec(
        repo="unsloth/Qwen3.5-2B-GGUF",
        filename="Qwen3.5-2B-Q4_K_M.gguf",
        size_bytes=1_280_835_840,
        sha256="aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223",
        download_gb=1.28,
        ram_gb=2.2,
        note="default: 8 GB RAM laptops",
    ),
    "full": ModelSpec(
        repo="unsloth/Qwen3.5-4B-GGUF",
        filename="Qwen3.5-4B-Q4_K_M.gguf",
        size_bytes=2_740_937_888,
        sha256="00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4",
        download_gb=2.74,
        ram_gb=3.5,
        note="strong CPUs / small GPUs",
    ),
}


def resolve_profile(requested: str = "auto", *, ram_gb: float = 0.0, cores: int = 0) -> str:
    """Turn ``auto`` into a concrete profile; validate an explicit one."""
    if requested == "auto":
        if not ram_gb and not cores:
            hw = hardware.detect()
            ram_gb, cores = hw.ram_gb, hw.logical_cores
        return hardware.suggest_profile(ram_gb, cores)[0]
    if requested not in PROFILE_MODELS:
        allowed = ", ".join(["auto", *PROFILE_MODELS])
        raise ValueError(f"Unknown LLM profile {requested!r}; choose one of: {allowed}")
    return requested
