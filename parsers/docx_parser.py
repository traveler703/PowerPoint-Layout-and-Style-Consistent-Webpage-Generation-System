from __future__ import annotations

import base64
from typing import Any

from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

from .base import ParsedNode, ParsedTable


def parse_docx(path: str) -> tuple[list[ParsedNode], int]:
    doc = Document(path)
    nodes: list[ParsedNode] = []
    current: ParsedNode | None = None
    image_count = 0

    def ensure_root() -> ParsedNode:
        nonlocal current
        if current is None:
            current = ParsedNode(level=1, title="文档内容")
            nodes.append(current)
        return current

    def paragraph_heading_level(p: Paragraph) -> int:
        style_name = (p.style.name or "").lower() if p.style else ""
        if "heading" in style_name:
            digits = "".join(ch for ch in style_name if ch.isdigit())
            return int(digits) if digits else 1
        # 兼容中文样式名
        if "标题" in (p.style.name or ""):
            digits = "".join(ch for ch in (p.style.name or "") if ch.isdigit())
            return int(digits) if digits else 1
        return 0

    def paragraph_has_image(p: Paragraph) -> bool:
        # 命名空间在不同环境下 XPath 可能不一致，直接检查段落 XML 更稳
        xml = p._p.xml or ""
        return ("w:drawing" in xml) or ("pic:pic" in xml) or ("w:pict" in xml)

    def _image_part_to_data_uri(image_part: Any) -> str:
        blob = getattr(image_part, "blob", None)
        if not blob:
            return ""
        content_type = (getattr(image_part, "content_type", "") or "").lower()
        if "png" in content_type:
            mime = "image/png"
        elif "jpeg" in content_type or "jpg" in content_type:
            mime = "image/jpeg"
        elif "gif" in content_type:
            mime = "image/gif"
        elif "webp" in content_type:
            mime = "image/webp"
        elif "bmp" in content_type:
            mime = "image/bmp"
        else:
            mime = "image/png"
        b64 = base64.b64encode(blob).decode("ascii")
        return f"data:{mime};base64,{b64}"

    def paragraph_extract_images(p: Paragraph) -> list[dict[str, str]]:
        images: list[dict[str, str]] = []
        rel_ids = p._element.xpath(".//a:blip/@r:embed")
        for rel_id in rel_ids:
            rel = doc.part.related_parts.get(rel_id)
            if rel is None:
                continue
            data_uri = _image_part_to_data_uri(rel)
            if not data_uri:
                continue
            images.append({"path": data_uri, "caption": "", "source": "docx"})
        return images

    # 按文档 body 顺序遍历（段落/表格交织），把表格/图片挂到“当前章节”上
    body = doc.element.body
    for child in body.iterchildren():
        if isinstance(child, CT_P):
            p = Paragraph(child, doc)
            text = (p.text or "").strip()
            lvl = paragraph_heading_level(p)
            if lvl > 0 and text:
                current = ParsedNode(level=lvl, title=text)
                nodes.append(current)
                continue

            node = ensure_root()
            if paragraph_has_image(p):
                for img in paragraph_extract_images(p):
                    image_count += 1
                    img["caption"] = f"图片 {image_count}"
                    node.images.append(img)

            if not text:
                continue

            if text.startswith(("-", "*", "+")):
                node.bullets.append({"title": text[1:].strip(), "description": ""})
            else:
                node.raw_text = (node.raw_text + "\n" + text).strip()

        elif isinstance(child, CT_Tbl):
            table = Table(child, doc)
            rows = []
            for row in table.rows:
                rows.append([(cell.text or "").strip() for cell in row.cells])
            if not rows:
                continue
            headers = rows[0]
            body_rows = rows[1:] if len(rows) > 1 else []
            ensure_root().tables.append(ParsedTable(headers=headers, rows=body_rows, caption=""))

    return nodes, image_count
