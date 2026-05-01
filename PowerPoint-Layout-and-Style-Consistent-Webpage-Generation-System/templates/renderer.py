"""Template renderer for filling placeholders and merging pages."""

from __future__ import annotations

import re
import json
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
        """
        Render a single page with the given content.

        Args:
            page_type: The type of page (cover, content, toc, etc.)
            title: Page title
            subtitle: Page subtitle (for cover pages)
            content: Main content (HTML or text)
            bullets: List of bullet points
            page_number: Current page number
            total_pages: Total number of pages
            extra: Additional placeholder values

        Returns:
            Rendered HTML for the page
        """
        page_config = self.template.get_page_type_config(page_type)

        if page_config is None:
            # Fallback to default content skeleton
            return self._render_default_page(
                title=title,
                content=content,
                bullets=bullets,
                page_number=page_number,
                total_pages=total_pages,
            )

        # Prepare placeholders
        placeholders = {
            "title": html_lib.escape(title) if title else "",
            "subtitle": html_lib.escape(subtitle) if subtitle else "",
            "content": content,
            "bullets": self._render_bullets(bullets or []),
            "page_number": str(page_number),
            "total_pages": str(total_pages),
            "page_type": page_type,
        }

        # Add extra placeholders
        if extra:
            for key, value in extra.items():
                placeholders[key] = str(value)

        # Replace placeholders in skeleton
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
        """Render a cover/title page."""
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
        """Render a content page."""
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
        """Render a table of contents page."""
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
        content: str = "",
        emoji: str = "",
        page_number: int = 1,
        total_pages: int = 1,
    ) -> str:
        """Render an ending/thank you page."""
        return self.render_page(
            page_type=PageType.ENDING,
            title="",  # Empty title for ending page
            content="",  # Not used, we use message placeholder
            extra={
                "emoji": emoji,
                "message": content,  # Pass content as message
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
        """Render a comparison page with multiple cards."""
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
        """Render a timeline page."""
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
        """Render a Q&A page."""
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
        """
        Merge multiple rendered pages into a complete HTML document.

        Args:
            pages: List of rendered page HTML strings
            document_title: Title for the document
            navigation: Whether to include navigation UI

        Returns:
            Complete HTML document with all pages
        """
        if not pages:
            return ""

        total_pages = len(pages)

        # Build slide containers with rendered content
        slide_containers = []
        for idx, page_html in enumerate(pages):
            page_num = idx + 1
            container = f'''
            <div class="slide-container">
                <div class="slide-wrapper" data-page="{page_num}">
                    {page_html}
                </div>
            </div>
            '''
            slide_containers.append(container)

        slides_inner = "\n".join(slide_containers)

        # Navigation UI
        nav_html = ""
        if navigation:
            nav_html = self._generate_navigation(total_pages)

        # Use the template's raw HTML as the base
        base_html = self.template.raw_html

        # Replace placeholders
        base_html = base_html.replace("{{SLIDES_CONTENT}}", slides_inner)
        base_html = base_html.replace("{{TOTAL_PAGES}}", str(total_pages))
        base_html = base_html.replace("<title>PPT Template</title>", f"<title>{html_lib.escape(document_title)}</title>")

        # If navigation is disabled, remove nav elements
        if not navigation:
            base_html = base_html.replace('<div class="nav-dots" id="navDots"></div>', '')
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
        """Render a page using the default content skeleton."""
        bullets_html = self._render_bullets(bullets or [])
        combined_content = f"{content}\n{bullets_html}" if content else bullets_html

        return f'''
        <div class="slide content">
            <div class="page-title">{html_lib.escape(title)}</div>
            <div class="page-content">{combined_content}</div>
            <div class="pagination">
                <span class="current-page">{page_number}</span> / <span class="total-pages">{total_pages}</span>
            </div>
        </div>
        '''

    def _render_bullets(self, bullets: list[str]) -> str:
        """Render bullet points as HTML list."""
        if not bullets:
            return ""
        items = []
        for bullet in bullets:
            escaped = html_lib.escape(bullet)
            items.append(f"<li>{escaped}</li>")
        return f"<ul>{''.join(items)}</ul>"

    def _render_toc_items(self, items: list[dict[str, str]]) -> str:
        """Render TOC items as HTML."""
        if not items:
            return ""
        html_parts = []
        for idx, item in enumerate(items, 1):
            number = f"{idx:02d}"
            title = html_lib.escape(item.get("title", ""))
            description = html_lib.escape(item.get("description", ""))
            html_parts.append(f'''
                <div class="toc-item">
                    <div class="toc-number">{number}</div>
                    <div class="toc-text">
                        <h3>{title}</h3>
                        <p>{description}</p>
                    </div>
                </div>
            ''')
        return "".join(html_parts)

    def _render_comparison_items(self, items: list[dict[str, Any]]) -> str:
        """Render comparison cards as HTML."""
        if not items:
            return ""
        html_parts = []
        for item in items:
            title = html_lib.escape(item.get("title", ""))
            era = item.get("era", "")
            description = item.get("description", "")
            features = item.get("features", [])

            features_html = ""
            for feature in features:
                features_html += f"<li>{html_lib.escape(feature)}</li>"

            html_parts.append(f'''
                <div class="compare-card">
                    <h3>{title}</h3>
                    <span class="era">{html_lib.escape(era)}</span>
                    <p>{html_lib.escape(description)}</p>
                    <ul>{features_html}</ul>
                </div>
            ''')
        return "".join(html_parts)

    def _render_timeline_items(self, items: list[dict[str, str]]) -> str:
        """Render timeline items as HTML."""
        if not items:
            return ""
        html_parts = []
        for item in items:
            title = html_lib.escape(item.get("title", ""))
            description = html_lib.escape(item.get("description", ""))
            icon = item.get("icon", "●")
            html_parts.append(f'''
                <div class="timeline-item">
                    <div class="timeline-content">
                        <h3>{icon} {title}</h3>
                        <p>{description}</p>
                    </div>
                </div>
            ''')
        return "".join(html_parts)

    def _render_qa_items(self, items: list[dict[str, str]]) -> str:
        """Render Q&A items as HTML."""
        if not items:
            return ""
        html_parts = []
        for item in items:
            question = html_lib.escape(item.get("question", ""))
            answer = html_lib.escape(item.get("answer", ""))
            html_parts.append(f'''
                <div class="qa-card">
                    <div class="question">{question}</div>
                    <div class="answer">{answer}</div>
                </div>
            ''')
        return "".join(html_parts)

    def _generate_navigation(self, total_pages: int) -> str:
        """Generate navigation UI HTML."""
        dots = []
        for i in range(total_pages):
            active = "active" if i == 0 else ""
            dots.append(f'<div class="nav-dot {active}" data-page="{i + 1}"></div>')

        return f'''
        <div class="nav-dots" id="navDots">
            {"".join(dots)}
        </div>
        <div class="nav-arrows">
            <div class="nav-arrow" id="prevBtn" onclick="prevSlide()">
                <i class="fa-solid fa-chevron-left"></i>
            </div>
            <div class="nav-arrow" id="nextBtn" onclick="nextSlide()">
                <i class="fa-solid fa-chevron-right"></i>
            </div>
        </div>
        <div class="page-indicator" id="pageIndicator">
            <span class="current" id="currentPage">1</span> / <span id="totalPages">{total_pages}</span>
        </div>
        '''

    def _extract_template_css(self) -> str:
        """Extract CSS from the template's raw HTML."""
        import re
        style_match = re.search(r"<style>(.*?)</style>", self.template.raw_html, re.DOTALL)
        if style_match:
            return style_match.group(1)
        return ""

    def _extract_template_js(self) -> str:
        """Extract JavaScript from the template's raw HTML."""
        import re
        script_match = re.search(r"<script>(.*?)</script>", self.template.raw_html, re.DOTALL)
        if script_match:
            return script_match.group(1)
        return ""
