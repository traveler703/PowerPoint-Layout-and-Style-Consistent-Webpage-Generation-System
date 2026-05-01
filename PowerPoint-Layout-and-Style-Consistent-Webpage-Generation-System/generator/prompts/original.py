"""Original prompt templates - for backward compatibility."""

from __future__ import annotations

import html
import json
import re
from typing import Any

from pydantic import BaseModel, Field

from engine.reasoning import PagePlan
from engine.types import SemanticPageInput
from framework.tokens import StyleTokens


class PromptContext(BaseModel):
    """Everything needed to steer the model toward on-brand output."""

    style_tokens: StyleTokens
    page_plan: PagePlan
    user_content: str = ""
    semantic: SemanticPageInput | None = None
    output_format: str = Field(default="html", description="html | markdown")


def _extract_keywords(text: str, max_terms: int = 8) -> list[str]:
    """简单中文/英文分词：取较长词片段作关键词提示。"""
    parts = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_-]{2,}", text)
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        if p.lower() in seen:
            continue
        seen.add(p.lower())
        out.append(p)
        if len(out) >= max_terms:
            break
    return out


def build_semantic_payload(semantic: SemanticPageInput | None) -> dict[str, Any]:
    if semantic is None:
        return {}
    keywords = _extract_keywords(
        " ".join(
            [semantic.title or ""]
            + [b.title for b in semantic.bullet_items]
            + semantic.bullet_points
        )
    )
    return {
        "page_index": semantic.page_index,
        "title": semantic.title,
        "summary": semantic.summary,
        "bullet_points": semantic.bullet_points,
        "bullet_items": [bi.model_dump() for bi in semantic.bullet_items],
        "headings": [h.model_dump() for h in semantic.headings],
        "image_urls": semantic.image_urls,
        "has_chart": semantic.has_chart,
        "has_table": semantic.has_table,
        "keywords": keywords,
    }


def build_system_prompt(ctx: PromptContext) -> str:
    """组装 system prompt：注入设计令牌与版式说明。"""
    token_hint = ctx.style_tokens.model_dump_json(indent=2)
    plan = ctx.page_plan
    rules = [
        "你是资深前端与版式助手，只输出用户要求的格式片段，不要输出 ``` 围栏外的解释文字。",
        f"输出格式：{ctx.output_format}。若为 html，只返回 <main> 或 <section> 内部可嵌入的片段，勿含 <html>/<head>/<body>。",
        "禁止使用 position:absolute 或 position:fixed（避免元素重叠）；使用 flex 或 CSS grid。",
        "颜色与字体请使用 DESIGN_TOKENS 中的语义色与字体变量（可在片段内写内联 style 引用 var(--color-primary) 等）。",
        f"当前版式 ID：{plan.layout_id}。版式说明：{plan.rationale or ''}",
        f"版式槽位：{plan.assignments}",
    ]
    return (
        "\n".join(rules)
        + "\n\nDESIGN_TOKENS_JSON:\n"
        + token_hint
    )


def build_user_prompt(ctx: PromptContext) -> str:
    """用户消息：结构化内容 + 原始备注（转义防 XSS）。"""
    payload = build_semantic_payload(ctx.semantic)
    structured = json.dumps(payload, ensure_ascii=False, indent=2)
    raw = html.escape(ctx.user_content or "")
    if ctx.output_format == "markdown":
        return f"STRUCTURED_JSON:\n{structured}\n\nRAW_NOTES:\n{raw}"
    return f"STRUCTURED_JSON:\n{structured}\n\nRAW_NOTES:\n{raw}"
