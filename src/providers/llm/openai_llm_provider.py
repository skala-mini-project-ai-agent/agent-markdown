"""OpenAI-backed text generation provider."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from .base_llm_provider import BaseLLMProvider, LLMResponse


@dataclass(slots=True)
class OpenAILLMProvider(BaseLLMProvider):
    api_key: str
    model: str = "gpt-4.1-mini"
    endpoint: str = "https://api.openai.com/v1/chat/completions"

    def generate_text(self, prompt: str, *, system_prompt: str | None = None) -> LLMResponse:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": self.model, "messages": messages, "temperature": 0}
        request = Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except URLError as exc:  # pragma: no cover - network path
            raise RuntimeError(f"OpenAI generation failed: {exc}") from exc

        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        text = str(message.get("content") or "")
        return LLMResponse(text=text, metadata={"model": self.model, "raw": data})
