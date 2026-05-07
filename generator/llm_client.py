"""HTTP 客户端：DeepSeek（OpenAI 兼容）或占位桩。"""

from __future__ import annotations

import logging
import os
import ssl
from abc import ABC, abstractmethod
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_DEFAULT_CLIENT: LLMClient | None = None


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
        raw = (
            base_url
            or os.getenv("DEEPSEEK_API_BASE", "")
            or os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com")
        ).strip().rstrip("/")
        if raw.endswith("/v1"):
            raw = raw[:-3].rstrip("/")
        self._api_root = raw
        self._model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self._timeout = timeout_s

        # 诊断日志：打印网络环境
        proxy_keys = ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY"]
        proxies = {k: os.environ.get(k) or os.environ.get(k.lower()) for k in proxy_keys}
        proxies = {k: v for k, v in proxies.items() if v}
        if proxies:
            logger.warning(f"[DeepSeek] 检测到代理配置: {proxies}")
        else:
            logger.info("[DeepSeek] 未检测到代理配置")

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

        try:
            # 不走系统代理，避免 Flask 进程的代理配置问题
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout, connect=15.0),
                trust_env=False,
            ) as client:
                logger.info(f"[DeepSeek] 发起请求: {url}")
                r = await client.post(url, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
            choices = data.get("choices") or []
            if not choices:
                return "<!-- empty completion -->"
            msg = choices[0].get("message") or {}
            content = msg.get("content")
            return content if isinstance(content, str) else ""
        except httpx.TimeoutException:
            logger.error("[DeepSeek] 请求超时")
            return "<!-- LLM 调用超时，请检查网络后重试 -->"
        except httpx.HTTPStatusError as e:
            logger.error(f"[DeepSeek] HTTP 错误 {e.response.status_code}: {e.response.text[:200]}")
            return f"<!-- LLM HTTP 错误 {e.response.status_code}: {e.response.text[:200]} -->"
        except Exception as e:
            logger.error(f"[DeepSeek] 调用失败: {type(e).__name__}: {e}")
            return f"<!-- LLM 调用失败: {type(e).__name__}: {e} -->"


def default_llm_client() -> LLMClient:
    """若存在 ``DEEPSEEK_API_KEY`` 则使用 DeepSeek；否则桩。"""
    global _DEFAULT_CLIENT
    if _DEFAULT_CLIENT is not None:
        return _DEFAULT_CLIENT
    if os.getenv("PPT_USE_STUB", "").strip().lower() in ("1", "true", "yes"):
        _DEFAULT_CLIENT = StubLLMClient()
        return _DEFAULT_CLIENT
    c = DeepSeekChatClient()
    if c.configured:
        _DEFAULT_CLIENT = c
        return _DEFAULT_CLIENT
    _DEFAULT_CLIENT = StubLLMClient()
    return _DEFAULT_CLIENT
