from __future__ import annotations

import re

from .base import ParsedNode
from .markdown_parser import parse_markdown_text


INDEXED_HEADING_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)[\)\.\s-]+(.+)$")


def parse_plain_text(text: str) -> list[ParsedNode]:
    nodes: list[ParsedNode] = []
    current: ParsedNode | None = None

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        indexed = INDEXED_HEADING_RE.match(stripped)
        if indexed:
            level = indexed.group(1).count(".") + 1
            title = f"{indexed.group(1)} {indexed.group(2)}".strip()
            current = ParsedNode(level=level, title=title)
            nodes.append(current)
            continue

        if stripped.startswith("#"):
            # 允许 txt 里混用 markdown 风格标题
            return parse_markdown_text(text)

        if current is None:
            current = ParsedNode(level=1, title="文档内容")
            nodes.append(current)

        if stripped.startswith(("-", "*", "+")):
            current.bullets.append({"title": stripped[1:].strip(), "description": ""})
        else:
            current.raw_text = (current.raw_text + "\n" + stripped).strip()

    return nodes
