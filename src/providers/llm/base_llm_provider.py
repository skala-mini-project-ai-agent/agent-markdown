"""Base LLM provider abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class LLMResponse:
    text: str
    metadata: dict[str, Any] | None = None


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate_text(self, prompt: str, *, system_prompt: str | None = None) -> LLMResponse:
        raise NotImplementedError

