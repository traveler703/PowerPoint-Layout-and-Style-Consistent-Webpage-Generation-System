from __future__ import annotations

import asyncio
import json
import re

from generator.llm_client import default_llm_client


async def _compress_with_llm(text: str, max_chars: int) -> str:
    llm = default_llm_client()
    system = "你是文档压缩助手。保留事实、数字、因果关系和专有名词，压缩冗长文本。"
    user = (
        f"请将以下正文压缩到不超过 {max_chars} 字符，保持信息完整度：\n\n"
        f"{text}"
    )
    result = await llm.complete(system, user)
    return (result or "").strip()

async def _compress_many_with_llm(texts: list[str], max_chars: int) -> list[str] | None:
    """
    将多个长文本一次性压缩，减少 LLM 请求次数。
    返回与 texts 等长的结果数组；失败返回 None。
    """
    llm = default_llm_client()
    system = (
        "你是文档压缩助手。"
        "请在保留事实、数字、因果关系和专有名词的前提下压缩文本。"
        "只输出JSON，不要输出额外解释。"
    )
    payload = {"max_chars": max_chars, "items": [{"id": i, "text": t} for i, t in enumerate(texts)]}
    user = (
        f"请将 items 中每个 text 压缩到不超过 {max_chars} 字符。\n"
        f"返回格式必须为：{{\"items\":[{{\"id\":0,\"text\":\"...\"}}, ...]}}。\n\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )
    resp = (await llm.complete(system, user)) or ""
    m = re.search(r"\{[\s\S]*\}", resp)
    if not m:
        return None
    try:
        data = json.loads(m.group())
        out = [""] * len(texts)
        for it in data.get("items", []):
            idx = int(it.get("id"))
            t = (it.get("text") or "").strip()
            if 0 <= idx < len(out):
                out[idx] = t[:max_chars]
        if any(out):
            # 用原文兜底空项
            for i in range(len(out)):
                if not out[i]:
                    out[i] = texts[i][:max_chars]
            return out
    except Exception:
        return None
    return None


def compress_long_text(text: str, threshold: int = 1200, target_chars: int = 600) -> tuple[str, bool]:
    if not text or len(text) <= threshold:
        return text, False

    try:
        compressed = asyncio.run(_compress_with_llm(text, target_chars))
        if compressed and not compressed.startswith("<!--"):
            return compressed[:target_chars], True
    except Exception:
        pass

    # LLM 不可用时回退到规则压缩
    head = int(target_chars * 0.65)
    tail = max(target_chars - head, 80)
    fallback = text[:head] + "\n...[中间内容省略]...\n" + text[-tail:]
    return fallback, True


def compress_many_long_texts(
    texts: list[str],
    threshold: int = 1200,
    target_chars: int = 600,
) -> tuple[list[str], list[bool]]:
    """
    批量压缩。会尽量用一次 LLM 请求完成。
    """
    if not texts:
        return [], []

    need_idx = [i for i, t in enumerate(texts) if t and len(t) > threshold]
    out = list(texts)
    flags = [False] * len(texts)
    if not need_idx:
        return out, flags

    need_texts = [texts[i] for i in need_idx]
    try:
        compressed = asyncio.run(_compress_many_with_llm(need_texts, target_chars))
        if compressed is not None:
            for local_i, i in enumerate(need_idx):
                out[i] = compressed[local_i]
                flags[i] = True
            return out, flags
    except Exception:
        pass

    # 回退：逐条规则压缩/单条LLM压缩
    for i in need_idx:
        out[i], flags[i] = compress_long_text(texts[i], threshold=threshold, target_chars=target_chars)
    return out, flags
