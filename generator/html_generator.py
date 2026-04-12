"""Turn PagePlan + tokens + LLM output into final HTML document."""

from __future__ import annotations

from abc import ABC, abstractmethod

from engine.reasoning import PagePlan
from framework.tokens import StyleTokens


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


class StubHtmlGenerator(HtmlGenerator):
    async def generate(
        self,
        *,
        body_fragment: str,
        tokens: StyleTokens,
        plan: PagePlan,
        title: str = "Slide",
    ) -> str:
        css = tokens.to_css_variables_block()
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>{css}
    body {{ font-family: var(--font-body); color: var(--color-text); background: var(--color-surface); margin: 0; padding: var(--space-md); }}
    .slide {{ max-width: 960px; margin: 0 auto; }}
  </style>
</head>
<body><div class="slide" data-layout="{plan.layout_id}">
{body_fragment}
</div></body>
</html>"""
