"""Markdown 导出路径。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from engine.reasoning import PagePlan
from engine.types import SemanticPageInput
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
        semantic: SemanticPageInput | None = None,
    ) -> str:
        raise NotImplementedError


class DocumentMarkdownGenerator(MarkdownGenerator):
    async def generate(
        self,
        *,
        body: str,
        tokens: StyleTokens,
        plan: PagePlan,
        title: str = "Slide",
        semantic: SemanticPageInput | None = None,
    ) -> str:
        _ = body
        lines: list[str] = [f"# {title}", "", f"<!-- layout: {plan.layout_id} -->", ""]
        if semantic:
            if semantic.summary:
                lines.append(semantic.summary)
                lines.append("")
            for bi in semantic.bullet_items:
                lines.append(f"- **{bi.title}**{'：' + bi.description if bi.description else ''}")
            for bp in semantic.bullet_points:
                lines.append(f"- {bp}")
            for h in semantic.headings:
                prefix = "#" * min(h.level, 4)
                lines.append(f"{prefix} {h.text}")
            for u in semantic.image_urls:
                lines.append(f"![]({u})")
            if semantic.table and semantic.table.headers:
                def _cell(c: str) -> str:
                    return c.replace("|", "\\|").replace("\n", " ")

                hdr = "| " + " | ".join(_cell(c) for c in semantic.table.headers) + " |"
                sep = "| " + " | ".join(["---"] * len(semantic.table.headers)) + " |"
                lines.extend(["", hdr, sep])
                for row in semantic.table.rows:
                    lines.append("| " + " | ".join(_cell(c) for c in row) + " |")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 模型生成片段")
        lines.append(body.strip() or "_（空）_")
        lines.append("")
        lines.append("> 主题色参考：`" + tokens.colors.get("primary", "") + "`")
        return "\n".join(lines)


class StubMarkdownGenerator(DocumentMarkdownGenerator):
    pass
