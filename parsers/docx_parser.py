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

        # 后处理：如果页面无标题但有 heading，提升首个 heading 为标题
        for page in pages:
            if not page.title and page.headings:
                page.title = page.headings[0].text
                page.headings = page.headings[1:]

        # 如果没有从属性中获取标题，取首个 H1
        if not doc_title:
            for p in pages:
                if p.title:
                    doc_title = p.title
                    break
            if not doc_title:
                doc_title = Path(filename).stem if filename else "未命名文档"

        # 提取图片（按文档出现顺序）并分配到对应页面
        self._extract_and_assign_images_inline(doc, pages)

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
        支持两种标题检测：
        1. Word 标题样式（Heading 1/2/3）
        2. 启发式检测（加粗 + 大字号 + 短文本 → 视为标题）
        """
        # ─── 第1步：收集所有段落的元信息 ───
        para_infos = self._collect_paragraph_infos(doc)

        # ─── 第2步：判断标题检测策略 ───
        has_heading_styles = any(
            info.get("heading_level") is not None for info in para_infos
        )

        # 如果没有标题样式，启用启发式标题检测
        if not has_heading_styles:
            para_infos = self._heuristic_heading_detection(para_infos)

        # ─── 第3步：按标题层级拆分为页面 ───
        pages: list[PageContent] = []
        current_page = PageContent(page_index=0)
        page_index = 0

        for info in para_infos:
            if info["type"] == "table":
                table = info["table"]
                if table:
                    current_page.tables.append(table)
                    current_page.has_table = True
                continue

            text = info["text"]
            if not text:
                continue

            heading_level = info["heading_level"]

            if heading_level is not None:
                # 这是一个标题
                if heading_level <= 2 and (
                    current_page.title or current_page.paragraphs
                    or current_page.bullets or current_page.tables
                ):
                    # H1/H2 开始新页面
                    pages.append(current_page)
                    page_index += 1
                    current_page = PageContent(page_index=page_index)

                if heading_level == 1 and current_page.title is None:
                    current_page.title = text
                else:
                    current_page.headings.append(
                        HeadingItem(level=min(heading_level, 4), text=text)
                    )

            elif info["is_list"]:
                # 列表项
                if ":" in text or "：" in text:
                    sep = "：" if "：" in text else ":"
                    t, _, d = text.partition(sep)
                    current_page.bullets.append(
                        BulletPoint(title=t.strip(), description=d.strip())
                    )
                else:
                    current_page.bullets.append(BulletPoint(title=text, description=""))

            else:
                # 普通段落
                current_page.paragraphs.append(text)
                current_page.raw_text += text + "\n"

        # 添加最后一页
        if (
            current_page.title or current_page.paragraphs
            or current_page.bullets or current_page.tables
        ):
            pages.append(current_page)

        # 确保至少有一页
        if not pages:
            pages.append(PageContent(page_index=0))

        return pages

    def _collect_paragraph_infos(self, doc) -> list[dict]:
        """收集文档中所有段落/表格的元信息。"""
        infos = []

        for element in doc.element.body:
            tag = element.tag.split("}")[-1]

            if tag == "p":
                para = self._find_paragraph(doc, element)
                if para is None:
                    continue

                text = para.text.strip()
                if not text:
                    continue

                style_name = (para.style.name or "").lower() if para.style else ""
                heading_level = None
                if "heading" in style_name:
                    heading_level = self._heading_level(style_name)

                # 获取字体属性
                is_bold = self._para_is_bold(para)
                font_size = self._para_font_size(para)
                is_list = self._is_list_item(para)

                infos.append({
                    "type": "paragraph",
                    "text": text,
                    "style": style_name,
                    "heading_level": heading_level,
                    "is_bold": is_bold,
                    "font_size": font_size,
                    "is_list": is_list,
                    "text_length": len(text),
                })

            elif tag == "tbl":
                table = self._parse_table_element(doc, element)
                infos.append({"type": "table", "table": table})

        return infos

    def _heuristic_heading_detection(self, para_infos: list[dict]) -> list[dict]:
        """
        启发式标题检测：当文档没有使用 Word 标题样式时，
        通过字体大小、加粗、文本长度和编号模式来推断标题层级。
        """
        from collections import Counter

        # 收集所有段落的字号，找出正文字号（出现最多的）
        font_sizes = [
            info["font_size"]
            for info in para_infos
            if info.get("type") == "paragraph" and info["font_size"] is not None
        ]

        if not font_sizes:
            return para_infos

        # 正文字号 = 出现最频繁的字号
        size_counter = Counter(font_sizes)
        body_font_size = size_counter.most_common(1)[0][0]

        # 找出所有大于正文字号的唯一字号，排序后确定层级
        heading_sizes = sorted(set(s for s in font_sizes if s > body_font_size), reverse=True)
        # heading_sizes[0] → H1, heading_sizes[1] → H2, 以此类推

        # 编号模式正则
        re_numbered = re.compile(r"^\d+[.、．]\s*\S")

        for info in para_infos:
            if info.get("type") != "paragraph":
                continue
            if info["heading_level"] is not None:
                continue  # 已经有标题级别

            text = info["text"]
            is_bold = info["is_bold"]
            font_size = info["font_size"]
            text_len = info["text_length"]

            # 标题启发规则：加粗 + 字号大于正文 + 文本较短（<60字）
            if is_bold and font_size is not None and text_len <= 60 and font_size > body_font_size:
                if heading_sizes and font_size >= heading_sizes[0]:
                    # 最大字号 → H1（文档标题）
                    info["heading_level"] = 1
                    info["is_list"] = False
                else:
                    # 其他大字号 → H2（章节标题）
                    info["heading_level"] = 2
                    info["is_list"] = False

            # 加粗 + 正文字号 + 编号模式 + 短文本 → H2
            elif is_bold and font_size is not None and re_numbered.match(text) and text_len <= 60:
                info["heading_level"] = 2
                info["is_list"] = False

            # 纯编号模式（不加粗但有编号且很短）
            elif (
                not is_bold
                and re_numbered.match(text)
                and text_len <= 30
                and font_size is not None
                and font_size >= body_font_size
            ):
                info["heading_level"] = 3
                info["is_list"] = False

        return para_infos

    @staticmethod
    def _para_is_bold(para) -> bool:
        """检测段落是否整体加粗。"""
        if not para.runs:
            return False
        # 如果大部分 run 是粗体，则视为粗体段落
        bold_chars = 0
        total_chars = 0
        for run in para.runs:
            run_len = len(run.text)
            total_chars += run_len
            if run.bold:
                bold_chars += run_len
        return total_chars > 0 and (bold_chars / total_chars) >= 0.5

    @staticmethod
    def _para_font_size(para) -> float | None:
        """获取段落的主要字号（pt）。"""
        for run in para.runs:
            if run.font.size:
                return run.font.size.pt
        return None

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

    def _extract_and_assign_images_inline(self, doc, pages: list[PageContent]) -> None:
        """
        按文档体顺序提取图片，并根据图片在段落流中的位置分配到正确的页面。
        
        策略：遍历文档所有段落，检测含图片的段落，
        根据段落位置（相对于标题切分点）确定所属页面。
        """
        if not pages:
            return

        try:
            # 构建页面标题列表，用于定位图片所属页面
            # 收集所有段落，按顺序记录标题切分点
            page_boundaries: list[int] = []  # 每页开始的段落索引
            current_page_idx = 0
            para_idx = 0

            # 重新收集段落信息以确定页面边界
            para_infos = self._collect_paragraph_infos(doc)
            has_heading_styles = any(
                info.get("heading_level") is not None for info in para_infos
            )
            if not has_heading_styles:
                para_infos = self._heuristic_heading_detection(para_infos)

            # 模拟页面切分逻辑，记录每个段落属于哪个页面
            para_to_page: dict[int, int] = {}
            page_idx = 0
            has_content = False

            for i, info in enumerate(para_infos):
                if info.get("type") == "table":
                    para_to_page[i] = page_idx
                    has_content = True
                    continue

                text = info.get("text", "")
                if not text:
                    para_to_page[i] = page_idx
                    continue

                heading_level = info.get("heading_level")
                if heading_level is not None and heading_level <= 2 and has_content:
                    page_idx += 1
                    has_content = False

                para_to_page[i] = page_idx

                if heading_level is not None or info.get("is_list") or text:
                    has_content = True

            # 遍历文档段落，按顺序提取图片
            NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
            NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

            # 建立全文档段落和 para_infos 的对应关系
            # para_infos 跳过了空段落，所以需要映射
            doc_para_list = list(doc.paragraphs)
            info_idx = 0  # 当前 para_infos 索引
            all_elements = list(doc.element.body)

            # 按 element 顺序遍历，匹配 para_infos 索引
            info_cursor = 0
            last_page_idx = 0  # 跟踪当前所在页面
            for element in all_elements:
                tag = element.tag.split("}")[-1]

                if tag == "p":
                    # 检查段落是否有文本（决定是否推进 info_cursor）
                    para = None
                    for p in doc_para_list:
                        if p._element is element:
                            para = p
                            break
                    has_text = para and para.text.strip()

                    if has_text:
                        # 非空段落：更新 last_page_idx，然后推进 cursor
                        last_page_idx = para_to_page.get(info_cursor, last_page_idx)
                        info_cursor += 1

                    # 查找该段落中的图片
                    blips = element.findall(f".//{{{NS_A}}}blip")
                    for blip in blips:
                        embed_id = blip.get(f"{{{NS_R}}}embed")
                        if embed_id and embed_id in doc.part.rels:
                            rel = doc.part.rels[embed_id]
                            if "image" in rel.reltype:
                                image_part = rel.target_part
                                img_bytes = image_part.blob
                                content_type = image_part.content_type or "image/png"
                                ext = content_type.split("/")[-1]
                                b64 = base64.b64encode(img_bytes).decode("ascii")
                                data_uri = f"data:{content_type};base64,{b64}"
                                img = ImageContent(url=data_uri, alt=f"嵌入图片 ({ext})")

                                # 图片属于当前所在页面
                                if last_page_idx < len(pages):
                                    pages[last_page_idx].images.append(img)
                                elif pages:
                                    pages[-1].images.append(img)

                elif tag == "tbl":
                    last_page_idx = para_to_page.get(info_cursor, last_page_idx)
                    info_cursor += 1

        except Exception as e:
            logger.warning(f"内联提取图片失败: {e}")
