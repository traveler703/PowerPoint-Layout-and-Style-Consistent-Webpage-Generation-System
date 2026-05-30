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
        timeout_s: float = 900.0,
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
            return "__TIMEOUT__:模型响应超时，请重试"
        except httpx.HTTPStatusError as e:
            logger.error(f"[DeepSeek] HTTP 错误 {e.response.status_code}: {e.response.text[:200]}")
            return f"<!-- LLM HTTP 错误 {e.response.status_code}: {e.response.text[:200]} -->"
        except Exception as e:
            logger.error(f"[DeepSeek] 调用失败: {type(e).__name__}: {e}")
            return f"<!-- LLM 调用失败: {type(e).__name__}: {e} -->"


class MultiKeyLLMClient(LLMClient):
    """多 API Key 客户端池，每个 Key 独立限流，轮询分配请求。"""

    def __init__(self, api_keys: list[str], base_url: str = "", model: str = "", timeout_s: float = 90.0, max_per_key: int = 3):
        import threading as _threading
        self._clients = []
        self._semaphores = []
        self._idx = 0
        self._idx_lock = _threading.Lock()
        for key in api_keys:
            key = key.strip()
            if not key:
                continue
            self._clients.append(DeepSeekChatClient(
                api_key=key, base_url=base_url, model=model, timeout_s=timeout_s,
            ))
            self._semaphores.append(_threading.Semaphore(max_per_key))
        if not self._clients:
            self._clients.append(StubLLMClient())
            self._semaphores.append(_threading.Semaphore(1))

    async def complete(self, system: str, user: str) -> str:
        import asyncio as _asyncio
        n = len(self._clients)
        # 轮询选 Key
        with self._idx_lock:
            self._idx = (self._idx + 1) % n
            i = self._idx
        # threading.Semaphore 不绑定 event loop，用 run_in_executor 避免阻塞事件循环
        loop = _asyncio.get_running_loop()
        await loop.run_in_executor(None, self._semaphores[i].acquire)
        try:
            return await self._clients[i].complete(system, user)
        finally:
            self._semaphores[i].release()


def _parse_api_keys() -> list[str]:
    """从环境变量解析多个 API Key（逗号或换行分隔）。"""
    raw = os.getenv("DEEPSEEK_API_KEY", "")
    if not raw:
        return []
    # 支持逗号或换行分隔
    import re
    return [k.strip() for k in re.split(r'[,\n]', raw) if k.strip()]


def default_llm_client() -> LLMClient:
    """若存在 ``DEEPSEEK_API_KEY`` 则使用 DeepSeek；否则桩。多 Key 时自动启用池。"""
    global _DEFAULT_CLIENT
    if _DEFAULT_CLIENT is not None:
        return _DEFAULT_CLIENT
    if os.getenv("PPT_USE_STUB", "").strip().lower() in ("1", "true", "yes"):
        _DEFAULT_CLIENT = StubLLMClient()
        return _DEFAULT_CLIENT

    keys = _parse_api_keys()
    if len(keys) > 1:
        _DEFAULT_CLIENT = MultiKeyLLMClient(keys)
        logger.info(f"[MultiKey] 启用多 Key 池: {len(keys)} 个 Key，每个最多 3 并发")
        return _DEFAULT_CLIENT

    c = DeepSeekChatClient()
    if c.configured:
        _DEFAULT_CLIENT = c
        return _DEFAULT_CLIENT
    _DEFAULT_CLIENT = StubLLMClient()
    return _DEFAULT_CLIENT
