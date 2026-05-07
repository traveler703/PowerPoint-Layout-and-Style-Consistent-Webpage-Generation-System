"""可选：LangChain 组装 Prompt（未安装 ``langchain-openai`` 时自动跳过）。"""

from __future__ import annotations

import os
from typing import Any


def build_lc_model() -> Any:
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        return None
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not key:
        return None
    raw = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com").strip().rstrip("/")
    if raw.endswith("/v1"):
        base = raw
    else:
        base = raw + "/v1"
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    return ChatOpenAI(
        api_key=key,
        base_url=base,
        model=model,
        temperature=0.4,
        timeout=60,
    )


async def run_langchain_slide(system: str, user: str) -> str:
    try:
        from langchain_core.prompts import ChatPromptTemplate
    except ImportError:
        return ""
    llm = build_lc_model()
    if llm is None:
        return ""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "{system}"),
            ("human", "{user}"),
        ]
    )
    chain: Any = prompt | llm
    msg = await chain.ainvoke({"system": system, "user": user})
    content = getattr(msg, "content", None)
    return content if isinstance(content, str) else str(msg)
