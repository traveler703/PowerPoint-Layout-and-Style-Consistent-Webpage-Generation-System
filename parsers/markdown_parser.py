"""
Markdown / TXT 文档解析器。
支持标准 Markdown 语法：多级标题、列表、表格、图片链接。
使用 --- 作为分页符。
"""

from __future__ import annotations

import re
from pathlib import Path

from parsers.base import (
    BaseDocumentParser,
    BulletPoint,
    DocumentMetadata,
    DocumentParseResult,
    HeadingItem,
    ImageContent,
    PageContent,
    SourceFormat,
    TableContent,
)


class MarkdownParser(BaseDocumentParser):
    """解析 Markdown / 纯文本文档为标准化结构。"""

    def parse(self, source: str | Path | bytes, filename: str = "") -> DocumentParseResult:
        """
        解析 Markdown/TXT 内容。

        Args:
            source: 文件路径(Path)、文本字符串(str)或字节流(bytes)
            filename: 原始文件名
        """
        text = self._read_source(source)
        fmt = self.detect_format(filename) if filename else SourceFormat.MARKDOWN

        # 按 --- 分页
        raw_pages = self._split_pages(text)
        pages: list[PageContent] = []

        for idx, block in enumerate(raw_pages):
            page = self._parse_page_block(block, idx)
            pages.append(page)

        # 提取文档标题（首个有标题的页面）
        doc_title = "未命名文档"
        for p in pages:
            if p.title:
                doc_title = p.title
                break

        metadata = DocumentMetadata(
            title=doc_title,
            source_format=fmt,
            source_filename=filename,
            page_count=len(pages),
            total_chars=len(text),
        )

        return DocumentParseResult(metadata=metadata, pages=pages)

    # ─────────────────────────────────────────
    # 内部方法
    # ─────────────────────────────────────────

    @staticmethod
    def _read_source(source: str | Path | bytes) -> str:
        """统一读取输入源为文本。"""
        if isinstance(source, bytes):
            return source.decode("utf-8", errors="replace")
        if isinstance(source, Path):
            return Path(source).read_text(encoding="utf-8")
        if isinstance(source, str):
            # 仅当字符串较短且看起来像路径时尝试文件读取
            if len(source) < 260 and "\n" not in source:
                p = Path(source)
                try:
                    if p.is_file():
                        return p.read_text(encoding="utf-8")
                except OSError:
                    pass
        # 直接是文本字符串
        return source

    @staticmethod
    def _split_pages(text: str) -> list[str]:
        """按 --- 分页。"""
        text = text.strip()
        if not text:
            return [""]
        parts = re.split(r"(?m)^---\s*$", text)
        out = [p.strip() for p in parts if p.strip()]
        return out if out else [""]

    def _parse_page_block(self, block: str, page_index: int) -> PageContent:
        """解析单个页面块。"""
        lines = block.splitlines()
        title: str | None = None
        headings: list[HeadingItem] = []
        paragraphs: list[str] = []
        bullets: list[BulletPoint] = []
        images: list[ImageContent] = []
        tables: list[TableContent] = []
        has_chart = False

        i = 0
        while i < len(lines):
            raw = lines[i]
            line = raw.strip()

            if not line:
                i += 1
                continue

            # 标题检测
            heading_match = re.match(r"^(#{1,4})\s+(.*)$", line)
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2).strip()
                # 提取标题中的图片
                text, imgs = self._extract_images(text)
                images.extend(imgs)

                if level == 1 and title is None:
                    title = text
                else:
                    headings.append(HeadingItem(level=min(level, 4), text=text))
                i += 1
                continue

            # 图表标记
            if line.lower().startswith(("[chart]", "chart:", "【图表】")):
                has_chart = True
                i += 1
                continue

            # 表格检测
            table, next_i = self._parse_table(lines, i)
            if table is not None:
                tables.append(table)
                i = next_i
                continue

            # 列表项检测
            bullet_match = re.match(r"^[-*+]\s+(.+)$", line)
            if bullet_match:
                item_text = bullet_match.group(1).strip()
                item_text, imgs = self._extract_images(item_text)
                images.extend(imgs)

                if ":" in item_text or "：" in item_text:
                    # 使用中英文冒号分割
                    sep = "：" if "：" in item_text else ":"
                    t, _, d = item_text.partition(sep)
                    bullets.append(BulletPoint(title=t.strip(), description=d.strip()))
                else:
                    bullets.append(BulletPoint(title=item_text, description=""))
                i += 1
                continue

            # 图片独立行
            img_match = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", line)
            if img_match:
                images.append(ImageContent(
                    url=img_match.group(2).strip(),
                    alt=img_match.group(1).strip(),
                ))
                i += 1
                continue

            # 普通段落
            line, imgs = self._extract_images(line)
            images.extend(imgs)
            if line:
                paragraphs.append(line)
            i += 1

        # 如果没有显式 H1 标题，取第一个标题
        if not title and headings:
            title = headings[0].text
            headings = headings[1:]

        raw_text = block.strip()
        has_table = len(tables) > 0

        return PageContent(
            page_index=page_index,
            title=title,
            headings=headings,
            paragraphs=paragraphs,
            bullets=bullets,
            tables=tables,
            images=images,
            has_chart=has_chart,
            has_table=has_table,
            raw_text=raw_text,
        )

    @staticmethod
    def _extract_images(text: str) -> tuple[str, list[ImageContent]]:
        """从文本中提取 Markdown 图片语法。"""
        images: list[ImageContent] = []
        for m in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", text):
            images.append(ImageContent(
                url=m.group(2).strip(),
                alt=m.group(1).strip(),
            ))
        cleaned = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", "", text).strip()
        return cleaned, images

    @staticmethod
    def _parse_table(lines: list[str], start: int) -> tuple[TableContent | None, int]:
        """解析 GitHub 风格 Markdown 表格。"""
        if start >= len(lines):
            return None, start

        line = lines[start].strip()
        if "|" not in line:
            return None, start

        # 检查下一行是否为分隔行
        sep_idx = start + 1
        if sep_idx >= len(lines) or not re.match(r"^\s*\|?[\s\-:|]+\|\s*$", lines[sep_idx]):
            return None, start

        # 解析表头
        header_cells = [c.strip() for c in line.strip("|").split("|")]

        # 解析数据行
        rows: list[list[str]] = []
        i = sep_idx + 1
        while i < len(lines):
            row_line = lines[i].strip()
            if "|" not in row_line:
                break
            row_cells = [c.strip() for c in row_line.strip("|").split("|")]
            rows.append(row_cells)
            i += 1

        table = TableContent(headers=header_cells, rows=rows)
        return table, i
