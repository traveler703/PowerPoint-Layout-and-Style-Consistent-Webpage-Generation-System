"""将用户粘贴的大纲/讲稿解析为多页 ``SemanticPageInput``。"""

from __future__ import annotations

import re

from engine.types import BulletItem, HeadingBlock, SemanticPageInput, TableData


def _split_pages(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return [""]
    parts = re.split(r"(?m)^---\s*$", text)
    out = [p.strip() for p in parts if p.strip()]
    return out if out else [""]


def _parse_markdown_table(lines: list[str], start: int) -> tuple[TableData | None, int]:
    """从 ``start`` 起解析 GitHub 风格表格，返回表格与下一行索引。"""
    if start >= len(lines):
        return None, start
    line = lines[start].strip()
    if "|" not in line:
        return None, start
    sep_idx = start + 1
    if sep_idx >= len(lines) or not re.match(r"^\s*\|?[\s\-:|]+\|\s*$", lines[sep_idx]):
        return None, start
    header_cells = [c.strip() for c in line.strip("|").split("|")]
    rows: list[list[str]] = []
    i = sep_idx + 1
    while i < len(lines):
        row_line = lines[i].strip()
        if "|" not in row_line:
            break
        rows.append([c.strip() for c in row_line.strip("|").split("|")])
        i += 1
    return TableData(headers=header_cells, rows=rows), i


def _extract_images(line: str) -> tuple[str, list[str]]:
    """返回去掉图片语法后的行文本，以及 URL 列表。"""
    urls: list[str] = []
    for m in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", line):
        urls.append(m.group(2).strip())
    cleaned = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", "", line).strip()
    return cleaned, urls


def parse_page_block(block: str, page_index: int) -> SemanticPageInput:
    lines = block.splitlines()
    title: str | None = None
    headings: list[HeadingBlock] = []
    bullet_points: list[str] = []
    bullet_items: list[BulletItem] = []
    image_urls: list[str] = []
    summary_parts: list[str] = []
    has_chart = False
    table: TableData | None = None
    i = 0
    while i < len(lines):
        raw = lines[i]
        line_stripped = raw.strip()
        if not line_stripped:
            i += 1
            continue
        if re.match(r"^#{1,4}\s+", line_stripped):
            m = re.match(r"^(#{1,4})\s+(.*)$", line_stripped)
            if m:
                level = len(m.group(1))
                rest = m.group(2).strip()
                rest, imgs = _extract_images(rest)
                image_urls.extend(imgs)
                if level == 1 and title is None:
                    title = rest
                else:
                    headings.append(HeadingBlock(level=min(level, 4), text=rest))
            i += 1
            continue
        if line_stripped.lower().startswith(("[chart]", "chart:", "【图表】")):
            has_chart = True
            i += 1
            continue
        tbl, next_i = _parse_markdown_table(lines, i)
        if tbl is not None:
            table = tbl
            i = next_i
            continue
        m = re.match(r"^[-*]\s+(.+)$", line_stripped)
        if m:
            item = m.group(1).strip()
            item, imgs = _extract_images(item)
            image_urls.extend(imgs)
            if ":" in item:
                t, _, d = item.partition(":")
                bullet_items.append(BulletItem(title=t.strip(), description=d.strip()))
            else:
                bullet_points.append(item)
            i += 1
            continue
        line_stripped, imgs = _extract_images(line_stripped)
        image_urls.extend(imgs)
        summary_parts.append(line_stripped)
        i += 1

    summary = "\n".join(summary_parts).strip() or None
    if not title and headings:
        title = headings[0].text
        headings = headings[1:]
    raw_notes = block.strip()

    return SemanticPageInput(
        page_index=page_index,
        title=title,
        summary=summary,
        bullet_points=bullet_points,
        headings=headings,
        bullet_items=bullet_items,
        image_urls=list(dict.fromkeys(image_urls)),
        table=table,
        has_chart=has_chart,
        has_table=table is not None,
        raw_notes=raw_notes,
        features={"source": "markdown-like"},
    )


def parse_user_document(text: str) -> list[SemanticPageInput]:
    """按 ``---`` 分页；无分隔符时整段作为一页。"""
    chunks = _split_pages(text)
    if len(chunks) == 1 and not chunks[0].strip():
        return [parse_page_block("", 0)]
    return [parse_page_block(c, idx) for idx, c in enumerate(chunks)]
