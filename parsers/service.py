from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from .base import ParsedNode, ParsedTable
from .docx_parser import parse_docx
from .markdown_parser import parse_markdown_text
from .pdf_parser import parse_pdf
from .pptx_parser import parse_pptx
from .text_compressor import compress_many_long_texts
from .text_parser import parse_plain_text


SUPPORTED_EXTENSIONS = {".docx", ".pptx", ".txt", ".md", ".pdf"}
TITLE_NUM_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\s+(.+?)\s*$")
INLINE_TITLE_RE = re.compile(r"(\d+(?:\.\d+)*)\s+([^\n]+?)(?=(?:\s+\d+(?:\.\d+)*\s+)|$)")
RAW_SUBTITLE_RE = re.compile(r"^\s*(\d+\.\d+(?:\.\d+)*)\s+(.+?)\s*$")


def _node_table_to_dict(table: ParsedTable | dict[str, Any]) -> dict[str, Any]:
    if isinstance(table, dict):
        return {
            "headers": table.get("headers", []),
            "rows": table.get("rows", []),
            "caption": table.get("caption", ""),
        }
    return {
        "headers": table.headers,
        "rows": table.rows,
        "caption": table.caption,
    }


def _node_image_to_dict(image: Any) -> dict[str, Any]:
    if isinstance(image, dict):
        return {
            "path": image.get("path", ""),
            "caption": image.get("caption", ""),
            "source": image.get("source", ""),
        }
    return {
        "path": getattr(image, "path", ""),
        "caption": getattr(image, "caption", ""),
        "source": getattr(image, "source", ""),
    }


def _insert_node(tree: list[dict[str, Any]], stack: list[tuple[int, dict[str, Any]]], node: dict[str, Any]) -> None:
    while stack and stack[-1][0] >= node["level"]:
        stack.pop()
    if not stack:
        tree.append(node)
    else:
        stack[-1][1]["children"].append(node)
    stack.append((node["level"], node))


def _to_chapter_node(idx: int, node: ParsedNode) -> dict[str, Any]:
    tables = [_node_table_to_dict(t) for t in (node.tables or [])]
    images = [_node_image_to_dict(i) for i in (node.images or [])]
    return {
        "level": node.level,
        "chapter_id": str(idx),
        "chapter_title": node.title,
        "bullets": node.bullets or [],
        "tables": tables,
        "images": images,
        "charts": [],
        "has_chart": False,
        "has_table": bool(tables),
        "has_image": bool(images),
        "raw_text": (node.raw_text or "").strip(),
        "compressed": False,
        "children": [],
    }


def _renumber(nodes: list[dict[str, Any]], prefix: str = "") -> None:
    for idx, node in enumerate(nodes, start=1):
        node_id = f"{prefix}.{idx}" if prefix else str(idx)
        node["chapter_id"] = node_id
        _renumber(node.get("children", []), node_id)


def _parse_by_extension(file_path: str, ext: str) -> tuple[list[ParsedNode], int]:
    if ext == ".docx":
        return parse_docx(file_path)
    if ext == ".pptx":
        return parse_pptx(file_path)
    if ext == ".pdf":
        return parse_pdf(file_path)
    if ext == ".md":
        text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        nodes = parse_markdown_text(text, source_path=file_path)
        image_count = sum(len(n.images or []) for n in nodes)
        return nodes, image_count
    if ext == ".txt":
        text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        return parse_plain_text(text), 0
    raise ValueError(f"不支持的文件类型: {ext}")


def _depth_from_numbered_title(title: str) -> int | None:
    m = TITLE_NUM_RE.match((title or "").strip())
    if not m:
        return None
    return m.group(1).count(".") + 1


def _split_inline_titles(title: str) -> list[tuple[int, str]]:
    """
    处理这类被合并的标题:
    "3 Project Scope 3.1 In Scope" -> [(1,"3 Project Scope"), (2,"3.1 In Scope")]
    """
    text = (title or "").strip()
    matches = list(INLINE_TITLE_RE.finditer(text))
    if len(matches) <= 1:
        d = _depth_from_numbered_title(text)
        return [(d or 1, text)] if text else []

    out: list[tuple[int, str]] = []
    for m in matches:
        num = m.group(1).strip()
        rest = m.group(2).strip()
        depth = num.count(".") + 1
        out.append((depth, f"{num} {rest}".strip()))
    return out


def _split_raw_into_subsections(raw_text: str, parent_level: int) -> tuple[str, list[ParsedNode]]:
    """
    将 raw_text 内嵌的编号子标题提取出来（例如 6.1.1 / 6.1.2）。
    """
    lines = [ln.rstrip() for ln in (raw_text or "").splitlines()]
    if not lines:
        return "", []

    parent_lines: list[str] = []
    children: list[ParsedNode] = []
    current_child: ParsedNode | None = None
    child_lines: list[str] = []

    def flush_child() -> None:
        nonlocal current_child, child_lines
        if current_child is not None:
            current_child.raw_text = "\n".join(x for x in child_lines if x.strip()).strip()
            children.append(current_child)
        current_child = None
        child_lines = []

    for ln in lines:
        s = ln.strip()
        m = RAW_SUBTITLE_RE.match(s)
        if m:
            depth = m.group(1).count(".") + 1
            # 只有更深层级时，才视为当前节点的子标题
            if depth > parent_level:
                flush_child()
                current_child = ParsedNode(level=depth, title=f"{m.group(1)} {m.group(2).strip()}")
                continue

        if current_child is None:
            parent_lines.append(ln)
        else:
            child_lines.append(ln)

    flush_child()
    parent_raw = "\n".join(x for x in parent_lines if x.strip()).strip()
    return parent_raw, children


def _normalize_numbered_hierarchy(nodes: list[ParsedNode]) -> list[ParsedNode]:
    """
    修复 PDF 里常见的层级错误：
    1) 标题中拼接了父子标题（3 ... 3.1 ...）
    2) 子标题落进 raw_text（6.1.1 ... / 6.1.2 ...）
    """
    normalized: list[ParsedNode] = []
    for node in nodes:
        title_chunks = _split_inline_titles(node.title or "")
        if not title_chunks:
            continue

        # 先展开标题链。原节点的正文/表格/图片挂到最后一个 chunk。
        chain: list[ParsedNode] = []
        for idx, (lvl, ttl) in enumerate(title_chunks):
            n = ParsedNode(level=lvl, title=ttl)
            if idx == len(title_chunks) - 1:
                n.raw_text = node.raw_text
                n.bullets = list(node.bullets or [])
                n.tables = list(node.tables or [])
                n.images = list(node.images or [])
            chain.append(n)

        # 对最后一个节点再做 raw_text 子标题拆分
        leaf = chain[-1]
        parent_raw, extra_children = _split_raw_into_subsections(leaf.raw_text or "", leaf.level)
        leaf.raw_text = parent_raw

        normalized.extend(chain)
        normalized.extend(extra_children)

    return normalized


def parse_document_to_json(file_path: str, output_dir: str) -> tuple[dict[str, Any], str]:
    ext = Path(file_path).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"仅支持: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")

    parsed_nodes, image_count = _parse_by_extension(file_path, ext)
    if ext == ".pdf":
        parsed_nodes = _normalize_numbered_hierarchy(parsed_nodes)

    tree: list[dict[str, Any]] = []
    stack: list[tuple[int, dict[str, Any]]] = []
    for idx, node in enumerate(parsed_nodes, start=1):
        chapter = _to_chapter_node(idx, node)
        _insert_node(tree, stack, chapter)
    _renumber(tree)

    source_name = os.path.basename(file_path)
    title = Path(source_name).stem or "未命名文档"
    all_text = "\n".join((n.raw_text or "") for n in parsed_nodes)

    def count_tables(nodes: list[dict[str, Any]]) -> int:
        total = 0
        for n in nodes:
            total += len(n.get("tables", []) or [])
            total += count_tables(n.get("children", []) or [])
        return total

    total_tables = count_tables(tree)

    # 批量压缩长正文（尽量一次 LLM 请求）
    def collect_raw(nodes: list[dict[str, Any]], acc: list[dict[str, Any]]) -> None:
        for n in nodes:
            acc.append(n)
            collect_raw(n.get("children", []) or [], acc)

    flat: list[dict[str, Any]] = []
    collect_raw(tree, flat)
    texts = [n.get("raw_text", "") or "" for n in flat]
    compressed_texts, flags = compress_many_long_texts(texts, threshold=1200, target_chars=600)
    for n, t, flg in zip(flat, compressed_texts, flags):
        if flg:
            n["raw_text"] = t
            n["compressed"] = True

    result = {
        "metadata": {
            "title": title,
            "source_format": ext.lstrip("."),
            "source_filename": source_name,
            "page_count": len(parsed_nodes),
            "total_chars": len(all_text),
            "author": "",
            "extra": {
                "image_count": image_count,
                "table_count": total_tables,
            },
        },
        "chapters": tree,
    }

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"parsed_{int(time.time())}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result, output_path


def _collect_bullets(chapter: dict[str, Any]) -> list[str]:
    output: list[str] = []
    for bullet in chapter.get("bullets", []):
        if isinstance(bullet, dict):
            title = bullet.get("title", "").strip()
            desc = bullet.get("description", "").strip()
            text = f"{title}：{desc}" if title and desc else (title or desc)
        else:
            text = str(bullet).strip()
        if text:
            output.append(text)
    return output[:6]


def _chapter_to_content_pages(chapter: dict[str, Any]) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    bullets = _collect_bullets(chapter)
    if not bullets and (chapter.get("raw_text") or "").strip():
        bullets = _snippets_from_raw(chapter["raw_text"])
    pages.append(
        {
            "title": chapter.get("chapter_title", "未命名章节"),
            "summary": (chapter.get("raw_text", "") or "")[:280],
            "bullets": bullets,
        }
    )
    for child in chapter.get("children", []):
        pages.extend(_chapter_to_content_pages(child))
    return pages


def parsed_json_to_outline(parsed_json: dict[str, Any]) -> dict[str, Any]:
    metadata = parsed_json.get("metadata", {})
    title = metadata.get("title", "演示文稿")
    sections = []
    for chapter in parsed_json.get("chapters", []):
        sections.append(
            {
                "title": chapter.get("chapter_title", "章节"),
                "content_pages": _chapter_to_content_pages(chapter),
            }
        )
    return {
        "title": title,
        "subtitle": metadata.get("source_filename", ""),
        "sections": sections,
        "ending_title": "谢谢观看",
    }


def _snippets_from_raw(raw: str, limit: int = 8) -> list[str]:
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    out: list[str] = []
    for ln in lines[:limit]:
        if len(ln) > 160:
            ln = ln[:157] + "..."
        out.append(ln)
    return out


def parsed_json_to_frontend_pages(parsed_json: dict[str, Any]) -> list[dict[str, Any]]:
    """转为前端 / LLM 解析结果使用的扁平 pages 列表（cover/toc/section/content/end）。"""
    meta = parsed_json.get("metadata", {})
    doc_title = meta.get("title", "演示文稿")
    subtitle = meta.get("source_filename", "")
    chapters = parsed_json.get("chapters") or []

    pages: list[dict[str, Any]] = [
        {"type": "cover", "title": doc_title, "subtitle": subtitle},
    ]

    toc_items: list[str] = []

    def collect_titles(nodes: list[dict[str, Any]]) -> None:
        for ch in nodes:
            t = (ch.get("chapter_title") or "").strip()
            if t:
                toc_items.append(t)
            collect_titles(ch.get("children") or [])

    collect_titles(chapters)
    if toc_items:
        pages.append({"type": "toc", "title": "目录", "items": toc_items[:40]})

    def bullet_lines(chapter: dict[str, Any]) -> list[str]:
        raw = chapter.get("raw_text") or ""
        bullets: list[str] = []
        for b in chapter.get("bullets") or []:
            if isinstance(b, dict):
                t = (b.get("title") or "").strip()
                d = (b.get("description") or "").strip()
                line = f"{t}：{d}" if t and d else (t or d)
            else:
                line = str(b).strip()
            if line:
                bullets.append(line)
        for tb in chapter.get("tables") or []:
            if not isinstance(tb, dict):
                continue
            hdr = " | ".join(tb.get("headers") or [])
            if hdr:
                bullets.append(f"表格：{hdr}")
        if not bullets and raw:
            bullets.extend(_snippets_from_raw(raw))
        return bullets[:10]

    def walk(nodes: list[dict[str, Any]]) -> None:
        for ch in nodes:
            ct = (ch.get("chapter_title") or "未命名").strip()
            children = ch.get("children") or []
            raw = (ch.get("raw_text") or "").strip()
            if children:
                pages.append({"type": "section", "title": ct, "subtitle": ""})
                walk(children)
            else:
                summ = raw[:400] if raw else ""
                bl = bullet_lines(ch)
                pages.append(
                    {
                        "type": "content",
                        "title": ct,
                        "subtitle": summ,
                        "summary": summ,
                        "bullets": bl,
                    }
                )

    walk(chapters)

    if len(pages) <= 1:
        pages.append(
            {
                "type": "content",
                "title": "正文摘要",
                "subtitle": "未能从文档中解析出章节结构，以下为摘要。",
                "summary": "未能从文档中解析出章节结构。",
                "bullets": [],
            }
        )

    pages.append({"type": "end", "title": "谢谢观看", "subtitle": ""})
    return pages
