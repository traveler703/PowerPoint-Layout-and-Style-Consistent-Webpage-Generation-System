"""将 PagePlan + tokens + LLM 输出组装为完整 HTML 文档。"""

from __future__ import annotations

import html as html_lib
import re
from abc import ABC, abstractmethod

from engine.reasoning import PagePlan
from framework.tokens import StyleTokens

_SCRIPT_RE = re.compile(
    r"(?is)<\s*script\b[^>]*>.*?</\s*script\s*>|<\s*script\b[^>]*/\s*>"
)
_EVENT_ATTR_RE = re.compile(r"\bon\w+\s*=")


def sanitize_fragment(fragment: str) -> str:
    """移除 script 与内联事件，降低 XSS 风险（用户内容与模型输出均建议经过）。"""
    s = _SCRIPT_RE.sub("", fragment)
    s = _EVENT_ATTR_RE.sub("data-removed-event=", s)
    return s


class HtmlGenerator(ABC):
    @abstractmethod
    async def generate(
        self,
        *,
        body_fragment: str,
        tokens: StyleTokens,
        plan: PagePlan,
        title: str = "Slide",
    ) -> str:
        raise NotImplementedError


class DocumentHtmlGenerator(HtmlGenerator):
    """包装为完整文档：注入 CSS 变量与版式 data 属性。"""

    async def generate(
        self,
        *,
        body_fragment: str,
        tokens: StyleTokens,
        plan: PagePlan,
        title: str = "Slide",
    ) -> str:
        safe = sanitize_fragment(body_fragment)
        css = tokens.to_css_variables_block()
        esc_title = html_lib.escape(title)
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc_title}</title>
  <style>{css}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: var(--font-body);
      color: var(--color-text);
      background: var(--color-surface);
      margin: 0;
      padding: var(--space-md);
      min-height: 100vh;
    }}
    .slide-root {{
      max-width: 1100px;
      margin: 0 auto;
    }}
    .slide-root section, .slide-root main {{
      max-width: 100%;
    }}
  </style>
</head>
<body>
  <div class="slide-root" data-layout="{html_lib.escape(plan.layout_id)}">
{safe}
  </div>
</body>
</html>"""


class StubHtmlGenerator(DocumentHtmlGenerator):
    """别名：与历史测试兼容。"""

    pass


def merge_slides_to_document(
    *,
    slides: list[tuple[str, PagePlan, str]],
    tokens: StyleTokens,
    doc_title: str = "演示文稿",
) -> str:
    """将多页 ``(title, plan, inner_html_fragment)`` 合并为单文件纵向滚动。"""
    css = tokens.to_css_variables_block()
    parts: list[str] = []
    for idx, (title, plan, frag) in enumerate(slides):
        safe = sanitize_fragment(frag)
        parts.append(
            f'<article class="deck-slide" id="slide-{idx}" data-layout="{html_lib.escape(plan.layout_id)}" '
            f'aria-label="{html_lib.escape(title)}">'
            f"<header class=\"deck-slide-title\"><h2>{html_lib.escape(title)}</h2></header>"
            f'<div class="deck-slide-body">{safe}</div></article>'
        )
    inner = "\n".join(parts)
    esc = html_lib.escape(doc_title)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc}</title>
  <style>{css}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: var(--font-body);
      color: var(--color-text);
      background: var(--color-surface);
      margin: 0;
      padding: var(--space-lg);
    }}
    .deck-slide {{
      background: var(--color-card);
      border-radius: var(--radius-card);
      box-shadow: 0 1px 3px rgba(15,23,42,0.08);
      padding: var(--space-lg);
      margin-bottom: var(--space-xl);
      max-width: 1100px;
      margin-left: auto;
      margin-right: auto;
    }}
    .deck-slide-title h2 {{
      margin: 0 0 var(--space-md);
      font-size: 1.35rem;
      color: var(--color-primary);
      font-family: var(--font-heading);
    }}
  </style>
</head>
<body>
{inner}
</body>
</html>"""
