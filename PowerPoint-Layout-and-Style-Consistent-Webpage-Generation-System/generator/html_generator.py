"""将 tokens + LLM 输出组装为完整 HTML 文档。"""

from __future__ import annotations

import re


_SCRIPT_RE = re.compile(
    r"(?is)<\s*script\b[^>]*>.*?</\s*script\s*>|<\s*script\b[^>]*/\s*>"
)
_EVENT_ATTR_RE = re.compile(r"\bon\w+\s*=")


def sanitize_fragment(fragment: str) -> str:
    """移除 script 与内联事件，降低 XSS 风险。"""
    s = _SCRIPT_RE.sub("", fragment)
    s = _EVENT_ATTR_RE.sub("data-removed-event=", s)
    return s


class HtmlGenerator:
    """HTML 生成器基类"""
    
    async def generate(
        self,
        *,
        body_fragment: str,
        title: str = "Slide",
    ) -> str:
        """生成完整 HTML 文档"""
        safe = sanitize_fragment(body_fragment)
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
            background: #ffffff;
        }}
    </style>
</head>
<body>
{body_fragment}
</body>
</html>"""


class StubHtmlGenerator(HtmlGenerator):
    """存根 HTML 生成器"""
    pass


__all__ = ["HtmlGenerator", "StubHtmlGenerator", "sanitize_fragment"]
