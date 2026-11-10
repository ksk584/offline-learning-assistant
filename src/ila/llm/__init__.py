"""Local LLM providers for note generation.

The base install ships without ``llama-cpp-python``: notes still work with the
extractive fallback. Install the optional extra to enable abstractive rewriting::

    uv pip install -e ".[llm]"
"""

from __future__ import annotations

from ila.config import LlmSettings
from ila.llm.base import LlmInfo, LlmProvider, Message
from ila.llm.llama_cpp import LlamaCppProvider, llama_cpp_installed
from ila.llm.profiles import PROFILE_MODELS, ModelSpec, resolve_profile

__all__ = [
    "PROFILE_MODELS",
    "LlmInfo",
    "LlmProvider",
    "LlamaCppProvider",
    "Message",
    "ModelSpec",
    "NullLlmProvider",
    "create_llm",
    "llama_cpp_installed",
    "resolve_profile",
]


class NullLlmProvider:
    """Used when the LLM is disabled; the notes pipeline stays extractive."""

    def __init__(self, reason: str = "LLM disabled") -> None:
        self.reason = reason

    @property
    def info(self) -> LlmInfo:
        return LlmInfo(engine="none", model="extractive")

    @property
    def available(self) -> bool:
        return False

    def complete(self, messages, *, max_tokens=320, temperature=0.2, stop=None) -> str:  # noqa: ARG002
        raise RuntimeError(self.reason)


def create_llm(settings: LlmSettings, *, profile: str | None = None) -> LlmProvider:
    if not settings.enabled:
        return NullLlmProvider()
    return LlamaCppProvider(settings, profile=profile)
