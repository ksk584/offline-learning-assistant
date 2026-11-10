"""One-time download of the local notes model.

The runtime never touches the network: this module exists so that setup can
fetch a single GGUF file into ``ILA_HOME/models/llm`` and every later run is
fully offline. Downloads are verified against the size and SHA-256 recorded in
the profile catalogue, because a truncated GGUF loads as a corrupted model.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from ila.config import LlmSettings
from ila.llm.profiles import PROFILE_MODELS, ModelSpec, resolve_profile

logger = logging.getLogger(__name__)


def verify_model(path: Path, spec: ModelSpec) -> None:
    """Raise when the file is not exactly the model the catalogue expects."""
    size = path.stat().st_size
    if size != spec.size_bytes:
        raise RuntimeError(
            f"{path.name} is {size} bytes, expected {spec.size_bytes}. "
            "Delete it and run `ila download-llm` again."
        )

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    actual = digest.hexdigest()
    if actual != spec.sha256:
        logger.error("checksum mismatch for %s: %s", path, actual)
        raise RuntimeError(
            f"{path.name} failed its SHA-256 check. Delete it and download again."
        )


def download_model(settings: LlmSettings, *, profile: str = "auto") -> Path:
    """Fetch the GGUF file for ``profile``, verify it, and return its path."""
    from huggingface_hub import hf_hub_download

    resolved = resolve_profile(profile)
    spec = PROFILE_MODELS[resolved]
    target_dir = Path(settings.model_dir).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)

    path = Path(
        hf_hub_download(
            repo_id=spec.repo,
            filename=spec.filename,
            local_dir=str(target_dir),
        )
    )
    verify_model(path, spec)
    return path
