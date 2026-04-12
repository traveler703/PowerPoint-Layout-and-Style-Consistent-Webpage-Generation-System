"""Optional Markdown path for export or static site generators."""

from __future__ import annotations

from abc import ABC, abstractmethod

from engine.reasoning import PagePlan
from framework.tokens import StyleTokens


class MarkdownGenerator(ABC):
    @abstractmethod
    async def generate(
        self,
        *,
        body: str,
        tokens: StyleTokens,
        plan: PagePlan,
        title: str = "Slide",
    ) -> str:
        raise NotImplementedError


class StubMarkdownGenerator(MarkdownGenerator):
    async def generate(
        self,
        *,
        body: str,
        tokens: StyleTokens,
        plan: PagePlan,
        title: str = "Slide",
    ) -> str:
        _ = tokens
        return f"# {title}\n\n<!-- layout: {plan.layout_id} -->\n\n{body}\n"
