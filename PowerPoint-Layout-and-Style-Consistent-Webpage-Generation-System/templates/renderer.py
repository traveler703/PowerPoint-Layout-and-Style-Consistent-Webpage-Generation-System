"""Template renderer for filling placeholders and merging pages."""

from __future__ import annotations

import re
import html as html_lib
from typing import Any

from templates.template import Template, PageType


class TemplateRenderer:
    """Renders content into template placeholders."""

    def __init__(self, template: Template) -> None:
        self.template = template

    def render_page(
        self,
        page_type: str,
        *,
        title: str = "",
        subtitle: str = "",
        content: str = "",
        bullets: list[str] | None = None,
        page_number: int = 1,
        total_pages: int = 1,
        extra: dict[str, Any] | None = None,
    ) -> str:
        page_config = self.template.get_page_type_config(page_type)

        if page_config is None:
            if page_type == "section":
                fallback = self.template.get_page_type_config("cover")
                if fallback is not None:
                    page_config = fallback
            if page_config is None:
                return self._render_default_page(
                    title=title,
                    content=content,
                    bullets=bullets,
                    page_number=page_number,
                    total_pages=total_pages,
                )

        placeholders = {
            "title": html_lib.escape(title) if title else "",
            "subtitle": html_lib.escape(subtitle) if subtitle else "",
            "content": content,
            "bullets": self._render_bullets(bullets or []),
            "page_number": str(page_number),
            "total_pages": str(total_pages),
            "page_type": page_type,
        }

        if extra:
            for key, value in extra.items():
                placeholders[key] = str(value)

        rendered = page_config.skeleton
        for key, value in placeholders.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", str(value))

        return rendered

    def render_cover_page(
        self,
        title: str,
        subtitle: str = "",
        date_badge: str = "",
        page_number: int = 1,
        total_pages: int = 1,
    ) -> str:
        return self.render_page(
            page_type=PageType.COVER,
            title=title,
            subtitle=subtitle,
            extra={"date_badge": date_badge},
            page_number=page_number,
            total_pages=total_pages,
        )

    def render_content_page(
        self,
        title: str,
        content: str = "",
        bullets: list[str] | None = None,
        page_number: int = 1,
        total_pages: int = 1,
    ) -> str:
        return self.render_page(
            page_type=PageType.CONTENT,
            title=title,
            content=content,
            bullets=bullets,
            page_number=page_number,
            total_pages=total_pages,
        )

    def render_toc_page(
        self,
        title: str,
        toc_items: list[dict[str, str]] | None = None,
        page_number: int = 1,
        total_pages: int = 1,
    ) -> str:
        toc_html = self._render_toc_items(toc_items or [])
        return self.render_page(
            page_type=PageType.TOC,
            title=title,
            extra={"toc_items": toc_html},
            page_number=page_number,
            total_pages=total_pages,
        )

    def render_ending_page(
        self,
        title: str = "谢谢观看",
        content: str = "",
        emoji: str = "",
        page_number: int = 1,
        total_pages: int = 1,
    ) -> str:
        return self.render_page(
            page_type=PageType.ENDING,
            title=title,
            content="",
            extra={
                "emoji": emoji,
                "message": content,
            },
            page_number=page_number,
            total_pages=total_pages,
        )

    def render_comparison_page(
        self,
        title: str,
        items: list[dict[str, Any]] | None = None,
        page_number: int = 1,
        total_pages: int = 1,
    ) -> str:
        items_html = self._render_comparison_items(items or [])
        return self.render_page(
            page_type=PageType.COMPARE,
            title=title,
            extra={"items": items_html},
            page_number=page_number,
            total_pages=total_pages,
        )

    def render_timeline_page(
        self,
        title: str,
        timeline_items: list[dict[str, str]] | None = None,
        page_number: int = 1,
        total_pages: int = 1,
    ) -> str:
        timeline_html = self._render_timeline_items(timeline_items or [])
        return self.render_page(
            page_type=PageType.TIMELINE,
            title=title,
            extra={"timeline_items": timeline_html},
            page_number=page_number,
            total_pages=total_pages,
        )

    def render_qa_page(
        self,
        title: str,
        qa_items: list[dict[str, str]] | None = None,
        page_number: int = 1,
        total_pages: int = 1,
    ) -> str:
        qa_html = self._render_qa_items(qa_items or [])
        return self.render_page(
            page_type=PageType.QA,
            title=title,
            extra={"qa_items": qa_html},
            page_number=page_number,
            total_pages=total_pages,
        )

    def merge_pages_to_document(
        self,
        pages: list[str],
        *,
        document_title: str = "演示文稿",
        navigation: bool = True,
    ) -> str:
        if not pages:
            return ""

        total_pages = len(pages)

        # Build slide containers
        slide_containers = []
        for idx, page_html in enumerate(pages):
            page_num = idx + 1
            container = (
                f'<div class="slide-container">'
                f'<div class="slide-wrapper" data-page="{page_num}">{page_html}</div>'
                f'</div>'
            )
            slide_containers.append(container)
        slides_inner = "".join(slide_containers)

        base_html = self.template.raw_html

        # Try BeautifulSoup for robust HTML manipulation
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            base_html = base_html.replace("{{SLIDES_CONTENT}}", slides_inner)
            base_html = base_html.replace("{SLIDES_CONTENT}", slides_inner)
            base_html = base_html.replace("{{TOTAL_PAGES}}", str(total_pages))
            base_html = base_html.replace("{TOTAL_PAGES}", str(total_pages))
            base_html = base_html.replace("<title>PPT Template</title>", f"<title>{html_lib.escape(document_title)}</title>")
            if not navigation:
                base_html = re.sub(r'<div class="nav-dots"[^>]*></div>', '', base_html)
                base_html = base_html.replace('<div class="nav-arrows">', '<div class="nav-arrows" style="display:none">')
            return base_html

        soup = BeautifulSoup(base_html, "html.parser")

        # Find slides-track
        track = soup.find("div", class_=lambda c: c and "slides-track" in c.split())
        if track:
            # 只删除 slides-track 的直接子元素中属于示例 slide 的部分
            # 不递归删除（避免把 slide-container / slide-wrapper 也删掉）
            for child in list(track.children):
                if not hasattr(child, 'name') or child.name != 'div':
                    continue
                child_class = child.get('class', [])
                child_class_str = ' '.join(child_class) if isinstance(child_class, list) else str(child_class)
                # 只删除直接的示例 slide div（不是 slide-container / slide-wrapper）
                is_example_slide = (
                    'slide' in child_class_str.split()
                    and 'container' not in child_class_str
                    and 'wrapper' not in child_class_str
                )
                if is_example_slide:
                    # 删除示例 slide 内部的 footer（避免合并后出现两套 footer）
                    for footer in child.find_all("div", class_=lambda c: c and 'slide-footer' in c.split()):
                        footer.decompose()
                    child.decompose()
            # 移除 track 内的文本节点/注释
            for child in list(track.children):
                if hasattr(child, 'name') and child.name is None:
                    child.extract()
            # 注入渲染后的页面
            pages_soup = BeautifulSoup(slides_inner, "html.parser")
            for child in list(pages_soup.find_all("div", recursive=False)):
                track.append(child)

        base_html = str(soup)
        base_html = base_html.replace("{{TOTAL_PAGES}}", str(total_pages))
        base_html = base_html.replace("{TOTAL_PAGES}", str(total_pages))
        base_html = base_html.replace("<title>PPT Template</title>", f"<title>{html_lib.escape(document_title)}</title>")

        if not navigation:
            base_html = re.sub(r'<div class="nav-dots"[^>]*></div>', '', base_html)
            base_html = base_html.replace('<div class="nav-arrows">', '<div class="nav-arrows" style="display:none">')

        return base_html

    def _render_default_page(
        self,
        title: str,
        content: str,
        bullets: list[str] | None,
        page_number: int,
        total_pages: int,
    ) -> str:
        bullets_html = self._render_bullets(bullets or [])
        combined_content = f"{content}\n{bullets_html}" if content else bullets_html

        return (
            f'<div class="slide content">'
            f'<div class="page-title">{html_lib.escape(title)}</div>'
            f'<div class="page-content">{combined_content}</div>'
            f'<div class="pagination">'
            f'<span class="current-page">{page_number}</span> / <span class="total-pages">{total_pages}</span>'
            f'</div>'
            f'</div>'
        )

    def _render_bullets(self, bullets: list[str]) -> str:
        if not bullets:
            return ""
        items = []
        for bullet in bullets:
            escaped = html_lib.escape(bullet)
            items.append(f"<li>{escaped}</li>")
        return f"<ul>{''.join(items)}</ul>"

    def _render_toc_items(self, items: list[dict[str, str]]) -> str:
        if not items:
            return ""
        html_parts = []
        for idx, item in enumerate(items, 1):
            number = f"{idx:02d}"
            title_esc = html_lib.escape(item.get("title", ""))
            desc_esc = html_lib.escape(item.get("description", ""))
            html_parts.append(
                f'<div class="toc-item">'
                f'<div class="toc-number">{number}</div>'
                f'<div class="toc-text"><h3>{title_esc}</h3><p>{desc_esc}</p></div>'
                f'</div>'
            )
        return "".join(html_parts)

    def _render_comparison_items(self, items: list[dict[str, Any]]) -> str:
        if not items:
            return ""
        html_parts = []
        for item in items:
            title_esc = html_lib.escape(item.get("title", ""))
            era = item.get("era", "")
            desc_esc = html_lib.escape(item.get("description", ""))
            features = item.get("features", [])
            features_html = "".join(f"<li>{html_lib.escape(f)}</li>" for f in features)
            html_parts.append(
                f'<div class="compare-card">'
                f'<h3>{title_esc}</h3>'
                f'<span class="era">{html_lib.escape(era)}</span>'
                f'<p>{desc_esc}</p>'
                f'<ul>{features_html}</ul>'
                f'</div>'
            )
        return "".join(html_parts)

    def _render_timeline_items(self, items: list[dict[str, str]]) -> str:
        if not items:
            return ""
        html_parts = []
        for item in items:
            title_esc = html_lib.escape(item.get("title", ""))
            desc_esc = html_lib.escape(item.get("description", ""))
            icon = item.get("icon", "●")
            html_parts.append(
                f'<div class="timeline-item">'
                f'<div class="timeline-content"><h3>{icon} {title_esc}</h3><p>{desc_esc}</p></div>'
                f'</div>'
            )
        return "".join(html_parts)

    def _render_qa_items(self, items: list[dict[str, str]]) -> str:
        if not items:
            return ""
        html_parts = []
        for item in items:
            q_esc = html_lib.escape(item.get("question", ""))
            a_esc = html_lib.escape(item.get("answer", ""))
            html_parts.append(
                f'<div class="qa-card">'
                f'<div class="question">{q_esc}</div>'
                f'<div class="answer">{a_esc}</div>'
                f'</div>'
            )
        return "".join(html_parts)

    def _generate_navigation(self, total_pages: int) -> str:
        dots = []
        for i in range(total_pages):
            active = "active" if i == 0 else ""
            dots.append(f'<div class="nav-dot {active}" data-page="{i + 1}"></div>')

        return (
            f'<div class="nav-dots" id="navDots">{"".join(dots)}</div>'
            f'<div class="nav-arrows">'
            f'<div class="nav-arrow" id="prevBtn" onclick="prevSlide()">'
            f'<i class="fa-solid fa-chevron-left"></i></div>'
            f'<div class="nav-arrow" id="nextBtn" onclick="nextSlide()">'
            f'<i class="fa-solid fa-chevron-right"></i></div>'
            f'</div>'
            f'<div class="page-indicator" id="pageIndicator">'
            f'<span class="current" id="currentPage">1</span> / <span id="totalPages">{total_pages}</span>'
            f'</div>'
        )

    def _extract_template_css(self) -> str:
        style_match = re.search(r"<style>(.*?)</style>", self.template.raw_html, re.DOTALL)
        if style_match:
            return style_match.group(1)
        return ""

    def _extract_template_js(self) -> str:
        script_match = re.search(r"<script>(.*?)</script>", self.template.raw_html, re.DOTALL)
        if script_match:
            return script_match.group(1)
        return ""
