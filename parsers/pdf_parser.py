"""
PDF 文档解析器。
使用 pdfplumber 库解析 PDF 文档，提取文本、表格和图片。
"""

from __future__ import annotations

import base64
import io
import logging
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

logger = logging.getLogger(__name__)


class PdfParser(BaseDocumentParser):
    """解析 PDF 文档为标准化结构。"""

    def parse(self, source: str | Path | bytes, filename: str = "") -> DocumentParseResult:
        """
        解析 PDF 文件。

        Args:
            source: 文件路径(Path/str) 或字节流(bytes)
            filename: 原始文件名
        """
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("需要安装 pdfplumber: pip install pdfplumber")

        # 打开 PDF
        if isinstance(source, bytes):
            pdf = pdfplumber.open(io.BytesIO(source))
        elif isinstance(source, (str, Path)):
            pdf = pdfplumber.open(str(source))
        else:
            raise ValueError(f"不支持的 source 类型: {type(source)}")

        pages: list[PageContent] = []
        total_chars = 0

        try:
            for page_idx, pdf_page in enumerate(pdf.pages):
                page_content = self._parse_pdf_page(pdf_page, page_idx)
                pages.append(page_content)
                total_chars += page_content.text_length
        finally:
            pdf.close()

        # 提取文档标题
        doc_title = self._infer_title(pages, filename)

        metadata = DocumentMetadata(
            title=doc_title,
            source_format=SourceFormat.PDF,
            source_filename=filename,
            page_count=len(pages),
            total_chars=total_chars,
        )

        return DocumentParseResult(metadata=metadata, pages=pages)

    # ─────────────────────────────────────────
    # 内部方法
    # ─────────────────────────────────────────

    def _parse_pdf_page(self, pdf_page, page_index: int) -> PageContent:
        """解析单个 PDF 页面。"""
        # 提取文本
        text = pdf_page.extract_text() or ""
        lines = text.splitlines()

        title: str | None = None
        headings: list[HeadingItem] = []
        paragraphs: list[str] = []
        bullets: list[BulletPoint] = []
        tables: list[TableContent] = []
        images: list[ImageContent] = []

        # 提取表格
        raw_tables = pdf_page.extract_tables() or []
        for raw_table in raw_tables:
            table = self._convert_table(raw_table)
            if table:
                tables.append(table)

        # 提取图片
        page_images = self._extract_page_images(pdf_page)
        images.extend(page_images)

        # 解析文本行
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # 启发式标题检测（首行、较短的加粗文本）
            if i == 0 and len(line) < 60 and title is None:
                title = line
                continue

            # 列表项检测
            bullet_match = re.match(r"^[•·●◆■▪\-–—]\s*(.+)$", line)
            if bullet_match:
                item_text = bullet_match.group(1).strip()
                if ":" in item_text or "：" in item_text:
                    sep = "：" if "：" in item_text else ":"
                    t, _, d = item_text.partition(sep)
                    bullets.append(BulletPoint(title=t.strip(), description=d.strip()))
                else:
                    bullets.append(BulletPoint(title=item_text, description=""))
                continue

            # 编号列表
            numbered_match = re.match(r"^\d+[.、)]\s*(.+)$", line)
            if numbered_match:
                item_text = numbered_match.group(1).strip()
                bullets.append(BulletPoint(title=item_text, description=""))
                continue

            # 启发式子标题检测（较短行，全文本，非句子）
            if len(line) < 40 and not line.endswith(("。", ".", "；", ";", "，", ",")):
                headings.append(HeadingItem(level=2, text=line))
                continue

            # 普通段落
            paragraphs.append(line)

        raw_text = text.strip()
        has_table = len(tables) > 0

        return PageContent(
            page_index=page_index,
            title=title,
            headings=headings,
            paragraphs=paragraphs,
            bullets=bullets,
            tables=tables,
            images=images,
            has_chart=False,
            has_table=has_table,
            raw_text=raw_text,
        )

    @staticmethod
    def _convert_table(raw_table: list[list]) -> TableContent | None:
        """将 pdfplumber 的原始表格转换为 TableContent。"""
        if not raw_table or len(raw_table) < 2:
            return None

        # 第一行作为表头
        headers = [str(cell or "").strip() for cell in raw_table[0]]
        rows: list[list[str]] = []

        for row in raw_table[1:]:
            row_data = [str(cell or "").strip() for cell in row]
            # 过滤全空行
            if any(cell for cell in row_data):
                rows.append(row_data)

        if not headers or not any(headers):
            return None

        return TableContent(headers=headers, rows=rows)

    @staticmethod
    def _extract_page_images(pdf_page) -> list[ImageContent]:
        """从 PDF 页面提取图片。"""
        images: list[ImageContent] = []
        try:
            page_images = pdf_page.images or []
            for img_info in page_images:
                # pdfplumber 提供图片位置信息
                width = int(img_info.get("width", 0))
                height = int(img_info.get("height", 0))

                images.append(ImageContent(
                    url="",  # PDF 图片需要额外处理才能提取实际数据
                    alt=f"PDF嵌入图片 ({width}x{height})",
                    width=width if width > 0 else None,
                    height=height if height > 0 else None,
                ))
        except Exception as e:
            logger.warning(f"提取 PDF 页面图片失败: {e}")

        return images

    @staticmethod
    def _infer_title(pages: list[PageContent], filename: str) -> str:
        """从解析结果中推断文档标题。"""
        # 优先取第一页的标题
        if pages and pages[0].title:
            return pages[0].title

        # 从文件名推断
        if filename:
            stem = Path(filename).stem
            # 去掉常见的文件名前缀/后缀
            cleaned = re.sub(r"[-_]+", " ", stem).strip()
            if cleaned:
                return cleaned

        return "未命名文档"
