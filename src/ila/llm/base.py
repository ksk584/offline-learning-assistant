"""Provider contract for the on-device notes model.

The notes pipeline depends on this protocol, not on llama.cpp, so tests and the
extractive fallback can run without a model file or native extension.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

#: A chat message as accepted by every local runtime we support.
Message = dict[str, str]


@dataclass(frozen=True, slots=True)
class LlmInfo:
    engine: str
    model: str
    path: str | None = None
    n_ctx: int = 0
    n_threads: int = 0
    profile: str = "none"


class LlmProvider(Protocol):
    """A blocking, local chat-completion backend."""

    @property
    def info(self) -> LlmInfo: ...

    @property
    def available(self) -> bool:
        """True when a model is present and the runtime can be imported."""
        ...

    def complete(
        self,
        messages: Sequence[Message],
        *,
        max_tokens: int = 320,
        temperature: float = 0.2,
        stop: Sequence[str] | None = None,
    ) -> str:
        """Return raw completion text. May raise; callers must handle failure."""
        ...
