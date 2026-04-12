"""HTTP client for LLM APIs. Stub returns fixed string; replace with httpx + streaming."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClient(ABC):
    @abstractmethod
    async def complete(self, system: str, user: str) -> str:
        raise NotImplementedError


class StubLLMClient(LLMClient):
    async def complete(self, system: str, user: str) -> str:
        return (
            "<!-- StubLLMClient: implement DeepSeek/OpenAI call in a subclass -->\n"
            f"<section><pre>{user[:200]!r}</pre></section>"
        )
