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

    # 用于检测纯文本中的编号标题的正则
    # 顶级编号: "1. 标题", "2. 标题", "第一章 标题" 等
    _RE_TOP_SECTION = re.compile(
        r"^(?:"
        r"(\d+)\.\s+(.+)"          # "1. 标题"
        r"|第[一二三四五六七八九十\d]+[章节部分]\s*[:：]?\s*(.+)?"  # "第一章 标题"
        r")$"
    )
    # 子级编号: "1.1 标题", "1.2 标题", "2.1.1 标题" 等
    _RE_SUB_SECTION = re.compile(
        r"^(\d+(?:\.\d+)+)\s+(.+)$"  # "1.1 标题" or "1.2.1 标题"
    )

    def parse(self, source: str | Path | bytes, filename: str = "") -> DocumentParseResult:
        """
        解析 Markdown/TXT 内容。

        Args:
            source: 文件路径(Path)、文本字符串(str)或字节流(bytes)
            filename: 原始文件名
        """
        text = self._read_source(source)
        fmt = self.detect_format(filename) if filename else SourceFormat.MARKDOWN

        # 判断是否为纯文本模式（无 Markdown 标记）
        is_plain_text = self._is_plain_text(text)

        if is_plain_text:
            pages = self._parse_plain_text(text)
        else:
            # Markdown 模式：按 --- 分页
            raw_pages = self._split_pages(text)
            pages = []
            for idx, block in enumerate(raw_pages):
                page = self._parse_page_block(block, idx)
                pages.append(page)

        # 提取文档标题（首个有标题的页面）
        doc_title = "未命名文档"
        for p in pages:
            if p.title:
                doc_title = p.title
                break

        # ─── 后处理：为孤立子标题页补全父标题 ───
        pages = self._fill_parent_titles(pages)

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
    def _is_plain_text(text: str) -> bool:
        """
        判断文本是否为纯文本（非 Markdown）。
        如果没有 Markdown 标记（# 标题、--- 分页）但有编号标题，则视为纯文本。
        """
        lines = text.strip().splitlines()
        has_md_heading = any(re.match(r"^#{1,4}\s+", l.strip()) for l in lines)
        has_md_separator = any(re.match(r"^---\s*$", l.strip()) for l in lines)

        if has_md_heading or has_md_separator:
            return False

        # 检查是否有编号式标题（至少出现 2 个顶级编号）
        top_section_count = 0
        re_top = re.compile(
            r"^(?:(\d+)\.\s+(.+)|第[一二三四五六七八九十\d]+[章节部分])"
        )
        for l in lines:
            if re_top.match(l.strip()):
                top_section_count += 1

        return top_section_count >= 2

    def _parse_plain_text(self, text: str) -> list[PageContent]:
        """
        解析纯文本，智能识别编号标题进行分页。
        规则：
        - 文档首行（短文本、独立行）→ 标题页
        - "N. 标题" → 顶级节 → 新的一页
        - "N.N 标题" → 子节 → 当前页内的 heading
        - 其他内容 → 段落或列表
        """
        lines = text.strip().splitlines()
        if not lines:
            return [PageContent(page_index=0, title="空文档", raw_text="")]

        # ─── 第1步：识别文档标题（首行，通常短且独立） ───
        doc_title: str | None = None
        content_start = 0

        first_line = lines[0].strip()
        # 如果第一行不是编号标题、长度适中、后跟空行，视为文档标题
        if (
            first_line
            and not self._RE_TOP_SECTION.match(first_line)
            and not self._RE_SUB_SECTION.match(first_line)
            and len(first_line) <= 50
        ):
            # 检查后面是否有空行分隔
            if len(lines) > 1 and lines[1].strip() == "":
                doc_title = first_line
                content_start = 2  # 跳过标题和空行
            else:
                doc_title = first_line
                content_start = 1

        # ─── 第2步：将文本按顶级编号切分为 sections ───
        sections: list[dict] = []  # [{"title": str, "lines": [str]}]
        current_section: dict | None = None

        for i in range(content_start, len(lines)):
            line = lines[i].strip()

            # 检测顶级编号标题
            top_match = self._RE_TOP_SECTION.match(line)
            if top_match:
                title = top_match.group(2) or top_match.group(3) or line
                # 保存上一个 section
                if current_section is not None:
                    sections.append(current_section)
                current_section = {"title": title.strip(), "lines": []}
                continue

            # 不是顶级标题的行，追加到当前 section
            if current_section is not None:
                current_section["lines"].append(lines[i])
            else:
                # 在顶级标题之前的内容，归入文档摘要
                if not sections:
                    # 创建一个无标题的 intro section
                    current_section = {"title": doc_title or "简介", "lines": [lines[i]]}

        # 别忘记最后一个 section
        if current_section is not None:
            sections.append(current_section)

        # ─── 第3步：将 sections 转换为 PageContent ───
        pages: list[PageContent] = []

        # 如果有文档标题，创建标题页
        if doc_title:
            pages.append(PageContent(
                page_index=0,
                title=doc_title,
                raw_text=doc_title,
            ))

        for section in sections:
            section_lines = section["lines"]
            section_title = section["title"]

            # 先收集所有内容块，按顺序保存 (type, data)
            ordered_items: list[tuple[str, str]] = []  # ("heading"|"paragraph"|"bullet", text)

            for raw_line in section_lines:
                line = raw_line.strip()
                if not line:
                    continue

                # 子级编号标题
                sub_match = self._RE_SUB_SECTION.match(line)
                if sub_match:
                    heading_text = sub_match.group(2).strip()
                    ordered_items.append(("heading", heading_text))
                    continue

                # 列表项（• 或 - 开头）
                bullet_match = re.match(r"^[•·\-\*\+]\s*(.+)$", line)
                if bullet_match:
                    ordered_items.append(("bullet", bullet_match.group(1).strip()))
                    continue

                # 普通段落
                ordered_items.append(("paragraph", line))

            # 统计子标题数量
            sub_heading_count = sum(1 for t, _ in ordered_items if t == "heading")

            if sub_heading_count >= 2:
                # 多个子标题：按子标题拆分为多页，每页共享父标题
                current_heading: str | None = None
                current_paragraphs: list[str] = []
                current_bullets: list[BulletPoint] = []

                def flush_sub_page():
                    if current_heading is None and not current_paragraphs and not current_bullets:
                        return
                    page_index = len(pages)
                    headings = [HeadingItem(level=2, text=current_heading)] if current_heading else []
                    raw_text = "\n".join(current_paragraphs)
                    pages.append(PageContent(
                        page_index=page_index,
                        title=section_title,
                        headings=headings,
                        paragraphs=current_paragraphs[:],
                        bullets=current_bullets[:],
                        has_table=False,
                        raw_text=raw_text,
                    ))

                for item_type, item_text in ordered_items:
                    if item_type == "heading":
                        # 遇到新子标题 → 刷新之前的子页
                        flush_sub_page()
                        current_heading = item_text
                        current_paragraphs = []
                        current_bullets = []
                    elif item_type == "paragraph":
                        current_paragraphs.append(item_text)
                    elif item_type == "bullet":
                        if ":" in item_text or "：" in item_text:
                            sep = "：" if "：" in item_text else ":"
                            t, _, d = item_text.partition(sep)
                            current_bullets.append(BulletPoint(title=t.strip(), description=d.strip()))
                        else:
                            current_bullets.append(BulletPoint(title=item_text, description=""))

                flush_sub_page()
            else:
                # 0-1 个子标题：作为单页
                page_index = len(pages)
                headings: list[HeadingItem] = []
                paragraphs: list[str] = []
                bullets: list[BulletPoint] = []

                for item_type, item_text in ordered_items:
                    if item_type == "heading":
                        headings.append(HeadingItem(level=2, text=item_text))
                    elif item_type == "paragraph":
                        paragraphs.append(item_text)
                    elif item_type == "bullet":
                        if ":" in item_text or "：" in item_text:
                            sep = "：" if "：" in item_text else ":"
                            t, _, d = item_text.partition(sep)
                            bullets.append(BulletPoint(title=t.strip(), description=d.strip()))
                        else:
                            bullets.append(BulletPoint(title=item_text, description=""))

                raw_text = "\n".join(section_lines).strip()
                pages.append(PageContent(
                    page_index=page_index,
                    title=section_title,
                    headings=headings,
                    paragraphs=paragraphs,
                    bullets=bullets,
                    has_table=False,
                    raw_text=raw_text,
                ))

        # 如果没有成功分页，回退为单页
        if not pages:
            pages.append(PageContent(
                page_index=0,
                title=doc_title or "未命名文档",
                paragraphs=[text.strip()],
                raw_text=text.strip(),
            ))

        return pages

    def _fill_parent_titles(self, pages: list[PageContent]) -> list[PageContent]:
        """
        后处理：为孤立的子标题页补全父标题。
        
        例如:
          Page 1: title="1. 简介", headings=["1.1 胡萝卜的概念"]
          Page 2: title="1.2 胡萝卜的品种", headings=[]
        
        Page 2 的标题是子级编号（1.2），需要补全父标题 → title="1. 简介", headings=["1.2 胡萝卜的品种"]
        """
        # 用于检测子级标题的正则（如 "1.2 标题", "2.1 标题"）
        re_sub_title = re.compile(r"^(\d+)\.(\d+(?:\.\d+)*)\s+(.+)$")
        # 用于检测顶级标题的正则（如 "1. 简介", "2. 营养价值"）
        re_top_title = re.compile(r"^(\d+)\.\s+(.+)$")

        # 跟踪最近的父级标题 {顶级编号: 完整标题}
        parent_map: dict[str, str] = {}

        for page in pages:
            if not page.title:
                continue

            # 检测是否为顶级标题
            top_match = re_top_title.match(page.title)
            if top_match:
                num = top_match.group(1)
                parent_map[num] = page.title
                continue

            # 检测是否为子级标题
            sub_match = re_sub_title.match(page.title)
            if sub_match:
                parent_num = sub_match.group(1)  # "1" from "1.2"
                sub_title_text = page.title  # "1.2 胡萝卜的品种"

                parent_title = parent_map.get(parent_num)
                if parent_title:
                    # 将子标题降级为 heading，父标题升级为 page title
                    new_headings = [HeadingItem(level=2, text=sub_title_text)]
                    if page.headings:
                        new_headings.extend(page.headings)
                    page.title = parent_title
                    page.headings = new_headings

        return pages

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
