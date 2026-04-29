"""
PPTX 文档解析器。
使用 python-pptx 库解析 PowerPoint 文档，提取幻灯片标题、文本、表格和图片。
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


class PptxParser(BaseDocumentParser):
    """解析 PPTX 文档为标准化结构。"""

    def parse(self, source: str | Path | bytes, filename: str = "") -> DocumentParseResult:
        """
        解析 PPTX 文件。

        Args:
            source: 文件路径(Path/str) 或字节流(bytes)
            filename: 原始文件名
        """
        try:
            from pptx import Presentation
        except ImportError:
            raise ImportError("需要安装 python-pptx: pip install python-pptx")

        # 打开演示文稿
        if isinstance(source, bytes):
            prs = Presentation(io.BytesIO(source))
        elif isinstance(source, (str, Path)):
            prs = Presentation(str(source))
        else:
            raise ValueError(f"不支持的 source 类型: {type(source)}")

        pages: list[PageContent] = []
        total_chars = 0

        for slide_idx, slide in enumerate(prs.slides):
            page = self._parse_slide(slide, slide_idx)
            pages.append(page)
            total_chars += page.text_length

        # 提取文档标题
        doc_title = self._infer_title(pages, filename)

        metadata = DocumentMetadata(
            title=doc_title,
            source_format=SourceFormat.PPTX,
            source_filename=filename,
            page_count=len(pages),
            total_chars=total_chars,
        )

        return DocumentParseResult(metadata=metadata, pages=pages)

    # ─────────────────────────────────────────
    # 内部方法
    # ─────────────────────────────────────────

    def _parse_slide(self, slide, slide_index: int) -> PageContent:
        """解析单张幻灯片。"""
        from pptx.util import Inches, Pt
        from pptx.enum.shapes import MSO_SHAPE_TYPE

        title: str | None = None
        headings: list[HeadingItem] = []
        paragraphs: list[str] = []
        bullets: list[BulletPoint] = []
        tables: list[TableContent] = []
        images: list[ImageContent] = []
        raw_parts: list[str] = []

        for shape in slide.shapes:
            # 标题占位符
            if shape.has_text_frame:
                if shape.shape_id == slide.shapes.title_id or (
                    hasattr(shape, "placeholder_format")
                    and shape.placeholder_format is not None
                    and shape.placeholder_format.idx == 0
                ):
                    # 标题形状
                    text = shape.text_frame.text.strip()
                    if text and title is None:
                        title = text
                        raw_parts.append(text)
                        continue

                # 普通文本框
                self._parse_text_frame(
                    shape.text_frame, headings, paragraphs, bullets, raw_parts
                )

            # 表格
            if shape.has_table:
                table = self._parse_table(shape.table)
                if table:
                    tables.append(table)

            # 图片
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                img = self._extract_image(shape)
                if img:
                    images.append(img)

        raw_text = "\n".join(raw_parts)
        has_table = len(tables) > 0

        return PageContent(
            page_index=slide_index,
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
    def _parse_text_frame(
        text_frame,
        headings: list[HeadingItem],
        paragraphs: list[str],
        bullets: list[BulletPoint],
        raw_parts: list[str],
    ) -> None:
        """解析文本框中的段落。"""
        for para in text_frame.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            raw_parts.append(text)

            # 通过缩进级别判断层级
            level = para.level if para.level is not None else 0

            # 检测是否为列表项（有项目符号或缩进）
            is_bullet = level > 0

            if is_bullet:
                if ":" in text or "：" in text:
                    sep = "：" if "：" in text else ":"
                    t, _, d = text.partition(sep)
                    bullets.append(BulletPoint(title=t.strip(), description=d.strip()))
                else:
                    bullets.append(BulletPoint(title=text, description=""))
            elif len(text) < 50 and level == 0:
                # 短文本可能是子标题
                headings.append(HeadingItem(level=2, text=text))
            else:
                paragraphs.append(text)

    @staticmethod
    def _parse_table(table) -> TableContent | None:
        """解析 PPTX 表格。"""
        try:
            if not table.rows:
                return None

            # 第一行作为表头
            headers = [cell.text.strip() for cell in table.rows[0].cells]
            rows: list[list[str]] = []

            for row in table.rows[1:]:
                row_data = [cell.text.strip() for cell in row.cells]
                rows.append(row_data)

            return TableContent(headers=headers, rows=rows)
        except Exception as e:
            logger.warning(f"解析 PPTX 表格失败: {e}")
            return None

    @staticmethod
    def _extract_image(shape) -> ImageContent | None:
        """从图片形状中提取图片数据。"""
        try:
            image = shape.image
            img_bytes = image.blob
            content_type = image.content_type or "image/png"
            ext = content_type.split("/")[-1]

            # 转为 base64 data URI
            b64 = base64.b64encode(img_bytes).decode("ascii")
            data_uri = f"data:{content_type};base64,{b64}"

            # 获取尺寸
            width = shape.width.pt if shape.width else None
            height = shape.height.pt if shape.height else None

            return ImageContent(
                url=data_uri,
                alt=f"幻灯片图片 ({ext})",
                width=int(width) if width else None,
                height=int(height) if height else None,
            )
        except Exception as e:
            logger.warning(f"提取 PPTX 图片失败: {e}")
            return None

    @staticmethod
    def _infer_title(pages: list[PageContent], filename: str) -> str:
        """从解析结果中推断文档标题。"""
        if pages and pages[0].title:
            return pages[0].title

        if filename:
            stem = Path(filename).stem
            cleaned = re.sub(r"[-_]+", " ", stem).strip()
            if cleaned:
                return cleaned

        return "未命名演示文稿"
