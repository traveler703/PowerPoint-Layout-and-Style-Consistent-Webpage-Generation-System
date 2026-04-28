"""HTTP 客户端：DeepSeek（OpenAI 兼容）或占位桩。"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

import httpx


class LLMClient(ABC):
    @abstractmethod
    async def complete(self, system: str, user: str) -> str:
        raise NotImplementedError


class StubLLMClient(LLMClient):
    async def complete(self, system: str, user: str) -> str:
        return (
            "<!-- StubLLMClient：未配置 DEEPSEEK_API_KEY 时使用占位片段 -->\n"
            "<section class=\"gen-stub\"><p>请配置 <code>.env</code> 中的 "
            "<code>DEEPSEEK_API_KEY</code> 以启用真实生成。</p>"
            f"<pre>{user[:400]!r}</pre></section>"
        )


class DeepSeekChatClient(LLMClient):
    """调用 DeepSeek ``/v1/chat/completions``（与 OpenAI SDK 兼容的 HTTP 形态）。"""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_s: float = 60.0,
    ) -> None:
        self._api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "").strip()
        raw = (base_url or os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")).strip().rstrip("/")
        if raw.endswith("/v1"):
            raw = raw[:-3].rstrip("/")
        self._api_root = raw
        self._model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self._timeout = timeout_s

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    async def complete(self, system: str, user: str) -> str:
        if not self._api_key:
            return await StubLLMClient().complete(system, user)
        url = f"{self._api_root}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.4,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        choices = data.get("choices") or []
        if not choices:
            return "<!-- empty completion -->"
        msg = choices[0].get("message") or {}
        content = msg.get("content")
        return content if isinstance(content, str) else ""


def default_llm_client() -> LLMClient:
    """若存在 ``DEEPSEEK_API_KEY`` 则使用 DeepSeek；否则桩。

    设置环境变量 ``PPT_USE_STUB=1`` 可强制走桩（便于测试与离线运行）。
    """
    if os.getenv("PPT_USE_STUB", "").strip().lower() in ("1", "true", "yes"):
        return StubLLMClient()
    c = DeepSeekChatClient()
    if c.configured:
        return c
    return StubLLMClient()
