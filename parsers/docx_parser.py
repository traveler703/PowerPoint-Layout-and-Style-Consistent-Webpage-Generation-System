"""
DOCX 文档解析器。
使用 python-docx 库解析 Word 文档，提取标题层级、段落、表格和图片。
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


class DocxParser(BaseDocumentParser):
    """解析 DOCX 文档为标准化结构。"""

    def parse(self, source: str | Path | bytes, filename: str = "") -> DocumentParseResult:
        """
        解析 DOCX 文件。

        Args:
            source: 文件路径(Path/str) 或字节流(bytes)
            filename: 原始文件名
        """
        try:
            from docx import Document
            from docx.opc.constants import RELATIONSHIP_TYPE as RT
        except ImportError:
            raise ImportError("需要安装 python-docx: pip install python-docx")

        # 打开文档
        if isinstance(source, bytes):
            doc = Document(io.BytesIO(source))
        elif isinstance(source, (str, Path)):
            doc = Document(str(source))
        else:
            raise ValueError(f"不支持的 source 类型: {type(source)}")

        # 提取文档属性
        core_props = doc.core_properties
        doc_title = core_props.title or ""
        doc_author = core_props.author or ""

        # 解析段落和表格，按标题分页
        pages = self._extract_pages(doc)

        # 如果没有从属性中获取标题，取首个 H1
        if not doc_title:
            for p in pages:
                if p.title:
                    doc_title = p.title
                    break
            if not doc_title:
                doc_title = Path(filename).stem if filename else "未命名文档"

        # 提取图片
        images_by_rel = self._extract_images(doc)

        # 将图片分配到对应页面
        self._assign_images_to_pages(pages, images_by_rel)

        total_chars = sum(p.text_length for p in pages)
        metadata = DocumentMetadata(
            title=doc_title,
            source_format=SourceFormat.DOCX,
            source_filename=filename,
            page_count=len(pages),
            total_chars=total_chars,
            author=doc_author,
        )

        return DocumentParseResult(metadata=metadata, pages=pages)

    # ─────────────────────────────────────────
    # 内部方法
    # ─────────────────────────────────────────

    def _extract_pages(self, doc) -> list[PageContent]:
        """
        按标题层级拆分文档为多页。
        遇到 Heading 1 或 Heading 2 时开始新页。
        """
        pages: list[PageContent] = []
        current_page = PageContent(page_index=0)
        page_index = 0

        for element in doc.element.body:
            tag = element.tag.split("}")[-1]  # 去掉命名空间

            if tag == "p":
                # 段落元素
                para = self._find_paragraph(doc, element)
                if para is None:
                    continue

                style_name = (para.style.name or "").lower() if para.style else ""
                text = para.text.strip()

                if not text:
                    continue

                # 标题检测
                if "heading" in style_name:
                    level = self._heading_level(style_name)

                    # H1/H2 开始新页面
                    if level <= 2 and (current_page.title or current_page.paragraphs or current_page.bullets):
                        pages.append(current_page)
                        page_index += 1
                        current_page = PageContent(page_index=page_index)

                    if level == 1 and current_page.title is None:
                        current_page.title = text
                    else:
                        current_page.headings.append(HeadingItem(level=min(level, 4), text=text))

                # 列表检测
                elif self._is_list_item(para):
                    if ":" in text or "：" in text:
                        sep = "：" if "：" in text else ":"
                        t, _, d = text.partition(sep)
                        current_page.bullets.append(BulletPoint(title=t.strip(), description=d.strip()))
                    else:
                        current_page.bullets.append(BulletPoint(title=text, description=""))

                # 普通段落
                else:
                    current_page.paragraphs.append(text)
                    # 累加原始文本
                    current_page.raw_text += text + "\n"

            elif tag == "tbl":
                # 表格元素
                table = self._parse_table_element(doc, element)
                if table:
                    current_page.tables.append(table)
                    current_page.has_table = True

        # 添加最后一页
        if current_page.title or current_page.paragraphs or current_page.bullets or current_page.tables:
            pages.append(current_page)

        # 确保至少有一页
        if not pages:
            pages.append(PageContent(page_index=0))

        return pages

    @staticmethod
    def _find_paragraph(doc, element):
        """通过 element 找到对应的 Paragraph 对象。"""
        for para in doc.paragraphs:
            if para._element is element:
                return para
        return None

    @staticmethod
    def _heading_level(style_name: str) -> int:
        """从样式名称中提取标题级别。"""
        match = re.search(r"(\d+)", style_name)
        if match:
            return min(int(match.group(1)), 4)
        return 2  # 默认作为 H2

    @staticmethod
    def _is_list_item(para) -> bool:
        """检测段落是否为列表项。"""
        # 检查 numbering 属性
        pPr = para._element.find(
            ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}numPr"
        )
        if pPr is not None:
            return True
        # 检查文本是否以列表标记开头
        text = para.text.strip()
        if re.match(r"^[•·\-–—]\s+", text):
            return True
        if re.match(r"^\d+[.、)]\s+", text):
            return True
        return False

    def _parse_table_element(self, doc, tbl_element) -> TableContent | None:
        """解析 Word 表格元素。"""
        try:
            from docx.table import Table
            table = Table(tbl_element, doc)

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
            logger.warning(f"解析表格失败: {e}")
            return None

    @staticmethod
    def _extract_images(doc) -> list[ImageContent]:
        """从文档中提取所有嵌入图片。"""
        images: list[ImageContent] = []
        try:
            for rel_id, rel in doc.part.rels.items():
                if "image" in rel.reltype:
                    image_part = rel.target_part
                    img_bytes = image_part.blob
                    content_type = image_part.content_type or "image/png"
                    ext = content_type.split("/")[-1]

                    # 转为 base64 data URI
                    b64 = base64.b64encode(img_bytes).decode("ascii")
                    data_uri = f"data:{content_type};base64,{b64}"

                    images.append(ImageContent(
                        url=data_uri,
                        alt=f"嵌入图片 ({ext})",
                    ))
        except Exception as e:
            logger.warning(f"提取图片失败: {e}")

        return images

    @staticmethod
    def _assign_images_to_pages(pages: list[PageContent], images: list[ImageContent]) -> None:
        """将图片均匀分配到页面（简单策略：按页面数平分）。"""
        if not images or not pages:
            return

        # 简单策略：将图片分配到第一个没有太多内容的页面
        # 后续可优化为基于段落中图片引用的精确匹配
        imgs_per_page = max(1, len(images) // len(pages))
        img_idx = 0

        for page in pages:
            for _ in range(imgs_per_page):
                if img_idx < len(images):
                    page.images.append(images[img_idx])
                    img_idx += 1

        # 剩余图片放到最后一页
        while img_idx < len(images):
            pages[-1].images.append(images[img_idx])
            img_idx += 1
