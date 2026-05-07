from __future__ import annotations

import base64
import statistics
from typing import Any

import fitz

from .base import ParsedNode, ParsedTable


def _collect_page_blocks(page: fitz.Page) -> list[dict[str, Any]]:
    """按阅读顺序（从上到下、从左到右）收集文本块。"""
    d = page.get_text("dict")
    out: list[dict[str, Any]] = []
    for b in d.get("blocks", []):
        if b.get("type") != 0:
            continue
        bbox = b.get("bbox")
        if not bbox:
            continue
        parts: list[str] = []
        sizes: list[float] = []
        bold_hits = 0
        span_hits = 0
        for line in b.get("lines", []):
            for span in line.get("spans", []):
                t = (span.get("text") or "").strip()
                if not t:
                    continue
                parts.append(t)
                sz = float(span.get("size", 0) or 0)
                if sz > 0:
                    sizes.append(sz)
                span_hits += 1
                fn = (span.get("font") or "").lower()
                if "bold" in fn or int(span.get("flags", 0) or 0) & 2:
                    bold_hits += 1
        if not parts:
            continue
        text = " ".join(parts)
        avg_size = sum(sizes) / len(sizes) if sizes else 0.0
        bold_ratio = (bold_hits / span_hits) if span_hits else 0.0
        out.append(
            {
                "bbox": bbox,
                "text": text,
                "avg_size": avg_size,
                "bold_ratio": bold_ratio,
            }
        )
    out.sort(key=lambda x: (x["bbox"][1], x["bbox"][0]))
    return out


def _page_body_baseline(blocks: list[dict[str, Any]]) -> float:
    """用偏小字号的分位数估计「正文」基准字号，避免标题字号拉高 median。"""
    sizes: list[float] = []
    for b in blocks:
        if b["avg_size"] and b["avg_size"] > 0:
            sizes.append(b["avg_size"])
    if not sizes:
        return 12.0
    sizes.sort()
    # 下四分位更接近大多数正文 span
    q = max(0, len(sizes) // 4)
    return float(sizes[q])


def _global_body_baseline(doc: fitz.Document) -> float:
    """整篇文档 span 字号的下四分位，封面单独一页时比单页估计更稳。"""
    sizes: list[float] = []
    for page in doc:
        d = page.get_text("dict")
        for b in d.get("blocks", []):
            if b.get("type") != 0:
                continue
            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    sz = float(span.get("size", 0) or 0)
                    if sz > 0:
                        sizes.append(sz)
    if not sizes:
        return 11.0
    sizes.sort()
    q = max(0, len(sizes) // 4)
    return float(sizes[q])


def _is_heading_fragment(b: dict[str, Any], body_baseline: float) -> bool:
    """
    判断块是否像「标题行」（包括被拆成多行的主标题）。
    放宽长度上限，避免把副标题行误判成正文。
    """
    text = (b.get("text") or "").strip()
    if not text:
        return False
    sz = float(b.get("avg_size") or 0)
    # 明显大于正文的字号，或粗体且略大于正文
    if sz >= body_baseline * 1.28:
        return len(text) <= 180
    if sz >= body_baseline * 1.18 and b.get("bold_ratio", 0) >= 0.4:
        return len(text) <= 160
    # 单独一行很短且字号不比正文小太多 —— 常见于封面拆行标题
    if len(text) <= 90 and sz >= body_baseline * 1.05:
        return True
    return False


def _merge_blocks_to_segments(blocks: list[dict[str, Any]], body_baseline: float) -> list[tuple[str, str]]:
    """
    将同一页的块转为 (segment_type, text) 序列。
    segment_type: 'heading' | 'body'
    连续、垂直距离近的标题碎片合并为一个 heading。
    """
    segments: list[tuple[str, str]] = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        if _is_heading_fragment(b, body_baseline):
            parts = [b["text"].strip()]
            prev_bottom = b["bbox"][3]
            j = i + 1
            while j < len(blocks) and _is_heading_fragment(blocks[j], body_baseline):
                gap = blocks[j]["bbox"][1] - prev_bottom
                # 同一标题簇：行距较小；允许跨行封面标题
                if gap <= 55:
                    parts.append(blocks[j]["text"].strip())
                    prev_bottom = blocks[j]["bbox"][3]
                    j += 1
                else:
                    break
            segments.append(("heading", " ".join(parts)))
            i = j
        else:
            segments.append(("body", b["text"].strip()))
            i += 1
    return segments


def _collapse_leading_empty_sections(nodes: list[ParsedNode]) -> list[ParsedNode]:
    """
    合并「只有标题、没有正文也没有表格」的连续章节到后面第一个有内容的章节标题上。
    解决封面标题被切成多节、前几节为空的问题。
    """
    pending_titles: list[str] = []
    out: list[ParsedNode] = []
    for n in nodes:
        has_stuff = bool((n.raw_text or "").strip()) or bool(n.tables)
        if not has_stuff:
            pending_titles.append((n.title or "").strip())
            continue
        if pending_titles:
            prefix = " — ".join(t for t in pending_titles if t)
            n.title = f"{prefix} — {n.title}".strip(" —") if prefix else n.title
            pending_titles = []
        out.append(n)
    if pending_titles:
        joined = " — ".join(t for t in pending_titles if t)
        if out:
            out[0].title = f"{joined} — {out[0].title}".strip(" —") if joined else out[0].title
        else:
            out.append(ParsedNode(level=1, title=joined or "文档内容", raw_text=""))
    return out


def _extract_tables(page: fitz.Page) -> list[ParsedTable]:
    tables: list[ParsedTable] = []
    if not hasattr(page, "find_tables"):
        return tables
    try:
        ft = page.find_tables()
        for t in ft.tables:
            matrix = t.extract()
            if not matrix:
                continue
            headers = [str(x or "").strip() for x in matrix[0]]
            rows = [[str(x or "").strip() for x in r] for r in matrix[1:]]
            tables.append(ParsedTable(headers=headers, rows=rows, caption=""))
    except Exception:
        return tables
    return tables


def _extract_page_images(doc: fitz.Document, page: fitz.Page) -> list[dict[str, str]]:
    images: list[dict[str, str]] = []
    for img in page.get_images(full=True):
        xref = int(img[0]) if img else 0
        if not xref:
            continue
        try:
            extracted = doc.extract_image(xref)
        except Exception:
            continue
        raw = extracted.get("image", b"") if extracted else b""
        ext = (extracted.get("ext", "") if extracted else "").lower()
        if not raw:
            continue
        if ext in {"jpg", "jpeg"}:
            mime = "image/jpeg"
        elif ext == "png":
            mime = "image/png"
        elif ext == "gif":
            mime = "image/gif"
        elif ext == "webp":
            mime = "image/webp"
        elif ext in {"jp2", "jpx"}:
            mime = "image/jp2"
        else:
            mime = "image/png"
        b64 = base64.b64encode(raw).decode("ascii")
        images.append({"path": f"data:{mime};base64,{b64}", "caption": "", "source": "pdf"})
    return images


def parse_pdf(path: str) -> tuple[list[ParsedNode], int]:
    doc = fitz.open(path)
    image_count = 0

    global_base = _global_body_baseline(doc)

    nodes: list[ParsedNode] = []
    current: ParsedNode | None = None

    for page in doc:
        blocks = _collect_page_blocks(page)
        if not blocks:
            plain = (page.get_text("text") or "").strip()
            if plain:
                blocks = [
                    {
                        "bbox": (0, 0, 0, 0),
                        "text": plain,
                        "avg_size": 0.0,
                        "bold_ratio": 0.0,
                    }
                ]

        page_base = _page_body_baseline(blocks)
        # 单页几乎只有标题时 page_base 会偏大，用全文基线兜底
        body_base = min(global_base, page_base) if page_base > 0 else global_base
        segments = _merge_blocks_to_segments(blocks, body_base)

        for kind, text in segments:
            if not text:
                continue
            if kind == "heading":
                current = ParsedNode(level=1, title=text)
                nodes.append(current)
            else:
                if current is None:
                    current = ParsedNode(level=1, title="文档内容")
                    nodes.append(current)
                current.raw_text = (current.raw_text + "\n" + text).strip()

        page_tables = _extract_tables(page)
        if page_tables:
            if current is None:
                current = ParsedNode(level=1, title="文档内容")
                nodes.append(current)
            current.tables.extend(page_tables)

        page_images = _extract_page_images(doc, page)
        if page_images:
            if current is None:
                current = ParsedNode(level=1, title="文档内容")
                nodes.append(current)
            for img in page_images:
                image_count += 1
                img["caption"] = f"PDF图片 {image_count}"
                current.images.append(img)

    nodes = _collapse_leading_empty_sections(nodes)

    # 若仍无任何正文（极端 PDF），整页纯文本兜底
    if not any((n.raw_text or "").strip() for n in nodes):
        merged = ParsedNode(level=1, title="文档内容", raw_text="")
        for page in doc:
            merged.raw_text = (merged.raw_text + "\n" + (page.get_text("text") or "")).strip()
        for n in nodes:
            merged.tables.extend(n.tables or [])
        nodes = [merged] if merged.raw_text.strip() or merged.tables else nodes

    return nodes, image_count
