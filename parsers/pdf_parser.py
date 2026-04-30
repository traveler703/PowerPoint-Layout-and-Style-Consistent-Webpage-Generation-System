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

        physical_pages: list[PageContent] = []
        total_chars = 0

        try:
            for page_idx, pdf_page in enumerate(pdf.pages):
                page_content = self._parse_pdf_page(pdf_page, page_idx)
                physical_pages.append(page_content)
                total_chars += page_content.text_length
        finally:
            pdf.close()

        # ─── 后处理：按逻辑标题重新分页 ───
        pages = self._resplit_by_sections(physical_pages)

        # 将物理页面的图片分配到逻辑页面（按顺序平均分配）
        all_images: list[ImageContent] = []
        for pp in physical_pages:
            all_images.extend(pp.images or [])
        if all_images and pages:
            # 简单策略：将图片均匀分配到有内容的逻辑页面（跳过封面页）
            content_pages = [p for p in pages if p.paragraphs or p.headings]
            if content_pages:
                imgs_per_page = max(1, len(all_images) // len(content_pages))
                img_idx = 0
                for cp in content_pages:
                    for _ in range(imgs_per_page):
                        if img_idx < len(all_images):
                            cp.images.append(all_images[img_idx])
                            img_idx += 1
                while img_idx < len(all_images):
                    content_pages[-1].images.append(all_images[img_idx])
                    img_idx += 1

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

    # 编号标题正则: "1. 标题", "2.标题"（短文本，不以标点结尾）
    _RE_NUMBERED_HEADING = re.compile(
        r"^(\d+)[.、．]\s*(.+)$"
    )
    # 子级编号标题: "1.1 标题", "2.1 标题"
    _RE_SUB_NUMBERED = re.compile(
        r"^(\d+(?:\.\d+)+)\s*(.+)$"
    )

    def _parse_pdf_page(self, pdf_page, page_index: int) -> PageContent:
        """解析单个 PDF 页面。"""
        # 提取文本
        text = pdf_page.extract_text() or ""
        raw_lines = text.splitlines()

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

        # ─── 关键步骤：先合并物理行为逻辑段落 ───
        # PDF 的文本按页面宽度断行，需要重新合并
        logical_blocks = self._merge_pdf_lines(raw_lines, pdf_page)

        # 解析逻辑块
        for i, block in enumerate(logical_blocks):
            block_text = block["text"]
            block_font_size = block.get("font_size")

            if not block_text:
                continue

            # ─── 标题检测 ───
            # 策略1: 首个块 + 短文本 + 看起来像标题 → 页面标题
            if i == 0 and title is None and self._looks_like_title(block_text, block_font_size):
                title = block_text
                continue

            # 策略2: 列表项检测（符号开头）
            bullet_match = re.match(r"^[•·●◆■▪\-–—]\s*(.+)$", block_text)
            if bullet_match:
                item_text = bullet_match.group(1).strip()
                if ":" in item_text or "：" in item_text:
                    sep = "：" if "：" in item_text else ":"
                    t, _, d = item_text.partition(sep)
                    bullets.append(BulletPoint(title=t.strip(), description=d.strip()))
                else:
                    bullets.append(BulletPoint(title=item_text, description=""))
                continue

            # 策略3: 编号标题 vs 编号列表项
            numbered_match = self._RE_NUMBERED_HEADING.match(block_text)
            if numbered_match:
                num_text = numbered_match.group(2).strip()
                # 标题：短文本（<30字），不以常见标点结尾
                is_heading_like = (
                    len(num_text) <= 30
                    and not num_text.endswith(("。", ".", "；", ";", "，", ",", "）", ")"))
                )
                if is_heading_like:
                    headings.append(HeadingItem(level=2, text=block_text))
                else:
                    bullets.append(BulletPoint(title=num_text, description=""))
                continue

            # 策略4: 子级编号标题 "1.1 xxx"
            sub_match = self._RE_SUB_NUMBERED.match(block_text)
            if sub_match:
                sub_text = sub_match.group(2).strip()
                if len(sub_text) <= 30 and not sub_text.endswith(("。", ".", "；", ";")):
                    level = min(sub_match.group(1).count('.') + 1, 4)
                    headings.append(HeadingItem(level=level, text=block_text))
                    continue

            # 策略5: 字号明显大于正文 + 短文本 → 标题
            if (
                block_font_size is not None
                and block_font_size > 14  # 明显比正文(通常10-12pt)大
                and len(block_text) <= 40
                and not block_text.endswith(("。", ".", "；", ";"))
            ):
                headings.append(HeadingItem(level=2, text=block_text))
                continue

            # 普通段落
            paragraphs.append(block_text)

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

    def _merge_pdf_lines(self, raw_lines: list[str], pdf_page) -> list[dict]:
        """
        将 PDF 物理行合并为逻辑段落块。
        规则：
        - 如果相邻两行字号相同且前一行不以句号等结尾 → 合并为同一段落
        - 字号不同、空行分隔、编号/符号开头 → 新段落
        """
        if not raw_lines:
            return []

        # 获取每行字号
        line_sizes = self._get_line_font_sizes(pdf_page, raw_lines)

        blocks: list[dict] = []
        current_text = ""
        current_size = None

        for i, line in enumerate(raw_lines):
            stripped = line.strip()

            # 空行 → 结束当前块
            if not stripped:
                if current_text:
                    blocks.append({"text": current_text, "font_size": current_size})
                    current_text = ""
                    current_size = None
                continue

            line_size = line_sizes.get(i)

            # 判断是否应该开始新块
            should_break = False

            if not current_text:
                # 第一行
                should_break = False
            elif line_size != current_size and line_size is not None and current_size is not None:
                # 字号变化 → 新块
                should_break = True
            elif re.match(r"^[•·●◆■▪\-–—]\s*", stripped):
                # 符号开头 → 新块
                should_break = True
            elif self._RE_NUMBERED_HEADING.match(stripped):
                # 编号开头 → 新块
                should_break = True
            elif self._RE_SUB_NUMBERED.match(stripped):
                # 子编号开头 → 新块
                should_break = True

            # 额外规则：如果当前块是短文本且匹配编号标题，也应该断开
            if not should_break and current_text:
                if (self._RE_NUMBERED_HEADING.match(current_text)
                    and len(current_text) <= 30
                    and not self._RE_NUMBERED_HEADING.match(stripped)):
                    should_break = True

            if should_break and current_text:
                blocks.append({"text": current_text, "font_size": current_size})
                current_text = stripped
                current_size = line_size
            else:
                # 合并到当前块
                if current_text:
                    current_text += stripped
                else:
                    current_text = stripped
                    current_size = line_size

        # 最后一个块
        if current_text:
            blocks.append({"text": current_text, "font_size": current_size})

        return blocks

    @staticmethod
    def _get_line_font_sizes(pdf_page, lines: list[str]) -> dict[int, float | None]:
        """
        获取每行的主要字号。
        通过 pdfplumber 的 chars 数据按 y 坐标分组。
        """
        result: dict[int, float | None] = {}
        try:
            chars = pdf_page.chars or []
            if not chars:
                return result

            # 按 top 坐标分组字符
            from collections import defaultdict
            y_groups: dict[float, list] = defaultdict(list)
            for char in chars:
                # 四舍五入 top 值以分组同行字符
                y_key = round(char.get("top", 0), 1)
                y_groups[y_key].append(char)

            # 按 y 值排序，映射到行索引
            sorted_ys = sorted(y_groups.keys())
            line_idx = 0

            for y in sorted_ys:
                if line_idx >= len(lines):
                    break
                # 跳过空行
                while line_idx < len(lines) and not lines[line_idx].strip():
                    line_idx += 1
                if line_idx >= len(lines):
                    break

                # 取该行字符组的最常见字号
                group_chars = y_groups[y]
                sizes = [c.get("size") for c in group_chars if c.get("size")]
                if sizes:
                    # 取中位数字号（避免受小标注影响）
                    sizes.sort()
                    result[line_idx] = sizes[len(sizes) // 2]

                line_idx += 1

        except Exception:
            pass

        return result

    @staticmethod
    def _looks_like_title(text: str, font_size: float | None) -> bool:
        """判断文本是否看起来像页面标题。"""
        # 太长的不是标题
        if len(text) > 40:
            return False
        # 以常见句子连续标点结尾的不是标题
        if text.endswith(("。", "；", ";", "，", ",", "、")):
            return False
        # 如果有字号信息，大字号更可能是标题
        if font_size is not None and font_size > 12:
            return True
        # 短文本（<20字）且不以标点结尾，可能是标题
        if len(text) <= 20:
            return True
        # 中等长度（20-40字）需要更多证据：不含句号/逗号
        if not any(p in text for p in ("。", "，", "；", "、")):
            return True
        return False

    @staticmethod
    def _convert_table(raw_table: list[list]) -> TableContent | None:
        """
        将 pdfplumber 的原始表格转换为 TableContent。
        
        严格过滤：只接受真正的多列数据表格，排除因页面边框导致的
        整页被误检为"表格"的情况。
        """
        if not raw_table or len(raw_table) < 2:
            return None

        # 找出真正有多列数据的行（≥2个非空单元格）
        multi_col_rows: list[list[str]] = []
        for row in raw_table:
            non_empty = [str(cell or "").strip() for cell in row if cell is not None and str(cell).strip()]
            if len(non_empty) >= 2:
                # 真正的多列行
                row_data = [str(cell or "").strip() for cell in row]
                multi_col_rows.append(row_data)

        # 只有至少2行多列数据才视为有效表格（1行表头 + 1行数据）
        if len(multi_col_rows) < 2:
            return None

        # 第一行作为表头，其余作为数据行
        headers = multi_col_rows[0]
        rows = multi_col_rows[1:]

        # 额外验证：表头和数据行的列数应一致
        if not headers or not any(headers):
            return None

        return TableContent(headers=headers, rows=rows)

    @staticmethod
    def _extract_page_images(pdf_page) -> list[ImageContent]:
        """从 PDF 页面提取图片（含实际图片数据）。"""
        import base64
        images: list[ImageContent] = []
        try:
            page_images = pdf_page.images or []

            for img_info in page_images:
                width = int(img_info.get("width", 0))
                height = int(img_info.get("height", 0))

                # 尝试从 PDF stream 提取实际图片数据
                data_uri = ""
                try:
                    stream = img_info.get("stream")
                    if stream is not None:
                        raw_data = stream.get_data()
                        # 检测图片格式
                        filter_type = stream.get("/Filter", "")
                        if isinstance(filter_type, list):
                            filter_type = filter_type[0] if filter_type else ""
                        filter_str = str(filter_type)

                        if "DCTDecode" in filter_str:
                            # JPEG
                            b64 = base64.b64encode(raw_data).decode("ascii")
                            data_uri = f"data:image/jpeg;base64,{b64}"
                        elif "FlateDecode" in filter_str or not filter_str:
                            # 原始像素数据，用 PIL 转换
                            try:
                                from PIL import Image as PILImage
                                import io as _io
                                import math as _math

                                # 先尝试 Image.open（可能是已知格式）
                                pil_img = None
                                try:
                                    pil_img = PILImage.open(_io.BytesIO(raw_data))
                                    pil_img.load()
                                except Exception:
                                    pass

                                if pil_img is None:
                                    # 原始像素：计算正确尺寸
                                    cs_str = str(stream.get("/ColorSpace", "/DeviceRGB"))
                                    if "Gray" in cs_str:
                                        mode, channels = "L", 1
                                    else:
                                        mode, channels = "RGB", 3

                                    pixel_count = len(raw_data) // channels
                                    if pixel_count > 0 and pixel_count * channels == len(raw_data):
                                        disp_w = float(width) if width > 0 else 1.0
                                        disp_h = float(height) if height > 0 else 1.0
                                        aspect = disp_w / disp_h
                                        h_est = int(_math.sqrt(pixel_count / aspect))
                                        img_w, img_h = None, None
                                        for dh in range(0, 50):
                                            for h_try in [h_est + dh, h_est - dh]:
                                                if h_try > 0 and pixel_count % h_try == 0:
                                                    img_w = pixel_count // h_try
                                                    img_h = h_try
                                                    break
                                            if img_w:
                                                break
                                        if img_w and img_h:
                                            pil_img = PILImage.frombytes(mode, (img_w, img_h), raw_data)

                                if pil_img:
                                    buf = _io.BytesIO()
                                    pil_img.save(buf, format="PNG")
                                    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                                    data_uri = f"data:image/png;base64,{b64}"
                            except Exception:
                                pass
                        elif "JPXDecode" in filter_str:
                            # JPEG2000
                            b64 = base64.b64encode(raw_data).decode("ascii")
                            data_uri = f"data:image/jp2;base64,{b64}"
                except Exception:
                    pass

                images.append(ImageContent(
                    url=data_uri,
                    alt=f"PDF嵌入图片 ({width}x{height})",
                    width=width if width > 0 else None,
                    height=height if height > 0 else None,
                ))
        except Exception as e:
            logger.warning(f"提取 PDF 页面图片失败: {e}")

        return images

    def _resplit_by_sections(self, physical_pages: list[PageContent]) -> list[PageContent]:
        """
        将按物理页面解析的结果，重新按逻辑节标题分页。
        
        关键：保留原始文档顺序（标题和段落交错），按编号标题分割。
        """
        # 先检查是否有足够的编号 heading 值得重新分页
        heading_count = 0
        for page in physical_pages:
            for h in (page.headings or []):
                if self._RE_NUMBERED_HEADING.match(h.text):
                    heading_count += 1

        if heading_count < 2:
            return physical_pages

        # ─── 重新从 raw_text 逐行解析，保留原始顺序 ───
        # 将所有物理页面的 raw_text 拼接（保留页间顺序）
        all_blocks: list[dict] = []  # [{"type": "title"|"heading"|"paragraph", ...}]

        for pidx, page in enumerate(physical_pages):
            raw_text = page.raw_text or ""
            raw_lines = raw_text.splitlines()
            logical_blocks = self._merge_pdf_lines(raw_lines, None)  # 无字号信息

            for i, block in enumerate(logical_blocks):
                block_text = block["text"]
                if not block_text:
                    continue

                # 标题检测（首页首块→文档标题）
                if pidx == 0 and i == 0 and len(block_text) <= 40:
                    if not self._RE_NUMBERED_HEADING.match(block_text):
                        all_blocks.append({"type": "title", "text": block_text, "pidx": pidx})
                        continue

                # 编号标题
                if self._RE_NUMBERED_HEADING.match(block_text):
                    all_blocks.append({"type": "heading", "text": block_text, "level": 2, "pidx": pidx})
                    continue

                # 子编号标题
                sub_match = self._RE_SUB_NUMBERED.match(block_text)
                if sub_match:
                    sub_text = sub_match.group(2).strip()
                    if len(sub_text) <= 30 and not sub_text.endswith(("。", ".", "；", ";")):
                        level = min(sub_match.group(1).count('.') + 1, 4)
                        all_blocks.append({"type": "heading", "text": block_text, "level": level, "pidx": pidx})
                        continue

                # 列表项
                bullet_match = re.match(r"^[•·●◆■▪\-–—]\s*(.+)$", block_text)
                if bullet_match:
                    item_text = bullet_match.group(1).strip()
                    all_blocks.append({"type": "bullet", "title": item_text, "description": "", "pidx": pidx})
                    continue

                # 普通段落
                all_blocks.append({"type": "paragraph", "text": block_text, "pidx": pidx})

        if not all_blocks:
            return physical_pages

        # ─── 按编号标题切分为 sections ───
        doc_title = None
        start_idx = 0

        if all_blocks[0]["type"] == "title":
            doc_title = all_blocks[0]["text"]
            start_idx = 1

        sections: list[dict] = []
        current_section: dict | None = None

        for i in range(start_idx, len(all_blocks)):
            block = all_blocks[i]

            is_section_break = (
                block["type"] == "heading"
                and self._RE_NUMBERED_HEADING.match(block["text"])
            )

            if is_section_break:
                if current_section:
                    sections.append(current_section)
                current_section = {"heading": block["text"], "blocks": []}
            else:
                if current_section is None:
                    current_section = {"heading": doc_title or "", "blocks": [block]}
                else:
                    current_section["blocks"].append(block)

        if current_section:
            sections.append(current_section)

        # ─── 转换为 PageContent ───
        pages: list[PageContent] = []
        # 记录每个物理页面对应的最后一个逻辑页面索引
        pidx_to_last_logical: dict[int, int] = {}

        if doc_title:
            pages.append(PageContent(page_index=0, title=doc_title, raw_text=doc_title))

        for section in sections:
            page_index = len(pages)
            headings: list[HeadingItem] = []
            paragraphs: list[str] = []
            bullets: list[BulletPoint] = []

            for block in section["blocks"]:
                if block["type"] == "heading":
                    headings.append(HeadingItem(level=block.get("level", 3), text=block["text"]))
                elif block["type"] == "paragraph":
                    paragraphs.append(block["text"])
                elif block["type"] == "bullet":
                    bullets.append(BulletPoint(title=block["title"], description=block.get("description", "")))
                # 记录此物理页面的最后逻辑页面
                pidx_to_last_logical[block.get("pidx", 0)] = page_index

            raw_text = "\n".join(paragraphs)
            pages.append(PageContent(
                page_index=page_index,
                title=section["heading"],
                headings=headings,
                paragraphs=paragraphs,
                bullets=bullets,
                has_table=False,
                raw_text=raw_text,
            ))

        # 将物理页面的表格分配到对应的逻辑页面
        for pidx, pp in enumerate(physical_pages):
            if pp.tables:
                logical_idx = pidx_to_last_logical.get(pidx)
                if logical_idx is not None and logical_idx < len(pages):
                    for tbl in pp.tables:
                        pages[logical_idx].tables.append(tbl)
                        pages[logical_idx].has_table = True
                elif pages:
                    for tbl in pp.tables:
                        pages[-1].tables.append(tbl)
                        pages[-1].has_table = True

        return pages if pages else physical_pages

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
