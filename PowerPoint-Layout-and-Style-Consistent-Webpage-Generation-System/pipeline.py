"""
PPT 生成引擎 - 基于两阶段布局方法的完整流水线

流程：
1. 加载模板 → 获取 CSS 变量和渲染器
2. 渲染封面页 → 模板预定义布局
3. 渲染目录页 → 根据章节列表生成
4. 遍历章节 → 渲染章节分隔页 + 生成内容页
5. 合并所有页面 → 输出完整 HTML 文档

内容页采用两阶段生成方法：
- Stage 1: 布局专家分析 → 推荐布局类型和设计建议
- Stage 2: HTML 生成 → 基于分析结果生成具体代码

依赖模块：
- templates/: 模板加载和渲染
- generator/: LLM 客户端和提示词
- engine/types.py: 数据类型定义
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any

from engine.types import SemanticPageInput
from generator.llm_client import LLMClient, default_llm_client
from generator.prompts import (
    build_html_generation_prompt,
    build_layout_analysis_prompt,
    generate_color_scheme_from_template,
    parse_html_response,
    parse_layout_analysis,
)
from templates.renderer import TemplateRenderer
from templates.template_loader import Template, load_template


# ============================================================
# 数据类型
# ============================================================

@dataclass
class ContentPageInput:
    """内容页输入数据"""
    title: str
    summary: str
    bullet_points: list[str]


@dataclass
class SectionInput:
    """章节输入数据"""
    title: str
    content_pages: list[ContentPageInput]


@dataclass
class PresentationOutline:
    """演示文稿大纲"""
    title: str
    subtitle: str
    date_badge: str = ""
    sections: list[SectionInput] = field(default_factory=list)


@dataclass
class GenerationResult:
    """生成结果"""
    success: bool
    output_path: str | None = None
    page_count: int = 0
    document_size: int = 0
    error: str | None = None
    page_layouts: list[dict[str, str]] = field(default_factory=list)


# ============================================================
# 生成器
# ============================================================

class PresentationGenerator:
    """
    演示文稿生成器

    使用两阶段布局方法生成内容页：
    1. 加载模板
    2. 渲染封面、目录、章节页（使用模板预定义布局）
    3. 生成内容页（两阶段：布局分析 + HTML 生成）
    4. 合并所有页面为完整 HTML 文档
    """

    def __init__(
        self,
        template_name: str = "tech",
        llm_client: LLMClient | None = None,
    ):
        """
        初始化生成器

        Args:
            template_name: 模板名称（默认 "tech"）
            llm_client: LLM 客户端（默认使用 default_llm_client）
        """
        self.template_name = template_name
        self.template: Template | None = None
        self.renderer: TemplateRenderer | None = None
        self.colors: dict[str, str] = {}
        self.llm_client = llm_client

    async def initialize(self) -> None:
        """初始化：加载模板和 LLM 客户端"""
        # 加载模板
        self.template = load_template(self.template_name)
        self.renderer = TemplateRenderer(self.template)
        self.colors = generate_color_scheme_from_template(self.template.css_variables)

        # 获取 LLM 客户端
        if self.llm_client is None:
            self.llm_client = default_llm_client()

    async def generate_content_page_html(
        self,
        page: SemanticPageInput,
    ) -> tuple[str, dict]:
        """
        使用两阶段方法生成内容页 HTML

        Args:
            page: 语义页面输入

        Returns:
            (html_content, layout_info) 元组
        """
        # Stage 1: 布局专家分析
        sys_prompt, user_prompt = build_layout_analysis_prompt(page)
        response = await self.llm_client.complete(sys_prompt, user_prompt)
        layout_analysis = parse_layout_analysis(response)

        layout_info = {
            "layout_type": layout_analysis.get("layout_type", "card_grid"),
            "design_suggestions": layout_analysis.get("design_suggestions", []),
            "reasoning": layout_analysis.get("reasoning", ""),
        }

        # Stage 2: HTML 生成
        sys_prompt, user_prompt = build_html_generation_prompt(
            page=page,
            layout_analysis=layout_analysis,
            colors=self.colors,
        )
        response = await self.llm_client.complete(sys_prompt, user_prompt)
        html = parse_html_response(response)

        return html, layout_info

    async def generate_content_pages_parallel(
        self,
        content_pages: list[tuple[int, ContentPageInput]],
        total_pages: int,
    ) -> list[tuple[int, str, dict]]:
        """
        并行生成多个内容页 HTML

        Args:
            content_pages: [(page_number, ContentPageInput), ...]
            total_pages: 总页数

        Returns:
            [(page_number, html_content, layout_info), ...]
        """
        async def generate_one(page_num: int, cp: ContentPageInput) -> tuple[int, str, dict]:
            semantic_page = SemanticPageInput(
                page_index=page_num - 1,
                title=cp.title,
                summary=cp.summary,
                page_type="content",
                bullet_points=cp.bullet_points,
            )
            html, layout_info = await self.generate_content_page_html(semantic_page)
            return page_num, html, layout_info

        tasks = [generate_one(pn, cp) for pn, cp in content_pages]
        results = await asyncio.gather(*tasks)
        return results

    async def generate_presentation(
        self,
        outline: PresentationOutline | dict,
        output_filename: str = "presentation.html",
        navigation: bool = True,
        save_pages: bool = False,
    ) -> GenerationResult:
        """
        生成完整演示文稿

        Args:
            outline: 演示文稿大纲（dict 或 PresentationOutline）
            output_filename: 输出文件名
            navigation: 是否启用导航
            save_pages: 是否保存单页文件

        Returns:
            GenerationResult: 生成结果
        """
        # 转换 dict 为 PresentationOutline
        if isinstance(outline, dict):
            outline = outline_from_dict(outline)

        if self.renderer is None:
            await self.initialize()

        try:
            # 计算总页数
            total_sections = len(outline.sections)
            total_content_pages = sum(len(s.content_pages) for s in outline.sections)
            total_pages = 1 + 1 + total_sections + total_content_pages

            # ============================================================
            # 构建页面列表（按正确顺序）
            # ============================================================
            pages_list: list[tuple[int, str, str, dict]] = []
            current_page_number = 1

            # Page 1: Cover
            cover_page = self.renderer.render_cover_page(
                title=outline.title,
                subtitle=outline.subtitle,
                date_badge=outline.date_badge,
                page_number=current_page_number,
                total_pages=total_pages,
            )
            pages_list.append((current_page_number, "cover", cover_page, {"type": "cover", "title": outline.title}))
            current_page_number += 1

            # Page 2: TOC
            toc_items = [
                {"title": s.title, "description": f"{len(s.content_pages)} 页内容"}
                for s in outline.sections
            ]
            toc_page = self.renderer.render_toc_page(
                title="目录",
                toc_items=toc_items,
                page_number=current_page_number,
                total_pages=total_pages,
            )
            pages_list.append((current_page_number, "toc", toc_page, {"type": "toc", "title": "目录"}))
            current_page_number += 1

            # 收集所有需要生成的内容页信息
            content_pages_for_parallel: list[tuple[int, ContentPageInput]] = []

            for section_idx, section in enumerate(outline.sections, 1):
                # Section Page
                section_page = self.renderer.render_page(
                    page_type="cover",
                    title=f"第{_roman_numeral(section_idx)}章",
                    subtitle=section.title,
                    page_number=current_page_number,
                    total_pages=total_pages,
                )
                pages_list.append((current_page_number, "section", section_page, {"type": "section", "title": section.title}))
                current_page_number += 1

                # Content Pages - 收集到并行队列
                for content_page in section.content_pages:
                    content_pages_for_parallel.append((current_page_number, content_page))
                    # 占位符，稍后替换
                    pages_list.append((current_page_number, "content", "", {}))
                    current_page_number += 1

            # ============================================================
            # 并行生成所有内容页
            # ============================================================
            if content_pages_for_parallel:
                results = await self.generate_content_pages_parallel(
                    content_pages_for_parallel, total_pages
                )

                # 创建 page_number -> (html, layout_info) 的映射
                results_map = {pn: (html, layout) for pn, html, layout in results}

                # 替换占位符为实际内容
                for i, (pn, ptype, _, _) in enumerate(pages_list):
                    if ptype == "content" and pn in results_map:
                        html_content, layout_info = results_map[pn]
                        # 找到对应的 content_page 获取标题
                        cp = next((cp for pnum, cp in content_pages_for_parallel if pnum == pn), None)
                        page_title = cp.title if cp else ""

                        content_page_rendered = self.renderer.render_content_page(
                            title=page_title,
                            content=html_content,
                            bullets=None,
                            page_number=pn,
                            total_pages=total_pages,
                        )
                        pages_list[i] = (pn, ptype, content_page_rendered, {
                            "type": "content",
                            "title": page_title,
                            **layout_info,
                        })

            # 提取最终的 pages 和 page_layouts
            pages = [page_html for _, _, page_html, _ in pages_list]
            page_layouts = []
            for pn, ptype, page_html, layout in pages_list:
                layout_with_page = {"page_number": pn, **layout}
                page_layouts.append(layout_with_page)

            # ============================================================
            # Merge and Save
            # ============================================================
            document = self.renderer.merge_pages_to_document(
                pages=pages,
                document_title=outline.title,
                navigation=navigation,
            )

            output_path = os.path.join(
                os.path.dirname(__file__) if __file__ else ".",
                "output",
                output_filename,
            )
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(document)

            # 如果需要保存单页
            if save_pages:
                pages_dir = os.path.join(os.path.dirname(output_path), "pages")
                os.makedirs(pages_dir, exist_ok=True)
                self._save_individual_pages(
                    pages, page_layouts, total_pages, pages_dir
                )

            return GenerationResult(
                success=True,
                output_path=output_path,
                page_count=len(pages),
                document_size=len(document),
                page_layouts=page_layouts,
            )

        except Exception as e:
            return GenerationResult(
                success=False,
                error=str(e),
            )

    def _save_individual_pages(
        self,
        pages: list[str],
        page_layouts: list[dict],
        total_pages: int,
        pages_dir: str,
    ) -> None:
        """保存每个页面为独立的完整 HTML 文档"""
        if not self.template:
            return

        for idx, (page_html, layout) in enumerate(zip(pages, page_layouts)):
            page_num = idx + 1
            ptype = layout.get("type", "content")
            title = layout.get("title", "")

            slides_inner = f'''
                <div class="slide-container">
                    <div class="slide-wrapper" data-page="{page_num}">
                        {page_html}
                    </div>
                </div>
            '''

            # 使用模板 raw_html 作为基础
            single_html = self.template.raw_html
            single_html = single_html.replace("{{SLIDES_CONTENT}}", slides_inner)
            single_html = single_html.replace("{{TOTAL_PAGES}}", str(total_pages))

            # 隐藏导航
            single_html = single_html.replace('<div class="nav-dots"', '<div class="nav-dots" style="display:none"')
            single_html = single_html.replace('<div class="nav-arrows">', '<div class="nav-arrows" style="display:none">')
            single_html = single_html.replace('<div class="page-indicator"', '<div class="page-indicator" style="display:none"')

            # 保存文件
            safe_title = title.replace("/", "_")[:20] if title else ""
            filename = f"{page_num:02d}_{ptype}_{safe_title}.html"
            filepath = os.path.join(pages_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(single_html)


# ============================================================
# 辅助函数
# ============================================================

def _roman_numeral(num: int) -> str:
    """将数字转换为罗马数字"""
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ['M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I']
    roman_num = ''
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            roman_num += syms[i]
            num -= val[i]
        i += 1
    return roman_num


def outline_from_dict(data: dict) -> PresentationOutline:
    """从字典创建 PresentationOutline"""
    sections = []
    for section_data in data.get("sections", []):
        content_pages = []
        for cp_data in section_data.get("content_pages", []):
            content_pages.append(ContentPageInput(
                title=cp_data["title"],
                summary=cp_data.get("summary", ""),
                bullet_points=cp_data.get("bullets", []),
            ))
        sections.append(SectionInput(
            title=section_data["title"],
            content_pages=content_pages,
        ))
    return PresentationOutline(
        title=data.get("title", ""),
        subtitle=data.get("subtitle", ""),
        date_badge=data.get("date_badge", ""),
        sections=sections,
    )


# ============================================================
# 便捷函数
# ============================================================

async def generate_presentation(
    outline: PresentationOutline | dict,
    template_name: str = "tech",
    output_filename: str = "presentation.html",
    navigation: bool = True,
) -> GenerationResult:
    """
    生成演示文稿的便捷函数

    Args:
        outline: 演示文稿大纲（dict 或 PresentationOutline）
        template_name: 模板名称
        output_filename: 输出文件名
        navigation: 是否启用导航

    Returns:
        GenerationResult: 生成结果

    Example:
        >>> outline = {
        ...     "title": "我的演示",
        ...     "subtitle": "副标题",
        ...     "sections": [...]
        ... }
        >>> result = await generate_presentation(outline)
    """
    if isinstance(outline, dict):
        outline = outline_from_dict(outline)

    generator = PresentationGenerator(template_name=template_name)
    return await generator.generate_presentation(
        outline=outline,
        output_filename=output_filename,
        navigation=navigation,
    )


# ============================================================
# 主入口
# ============================================================

async def main():
    """演示用法"""
    # 示例大纲
    outline = {
        "title": "人工智能技术专题",
        "subtitle": "从基础理论到行业应用",
        "date_badge": "2026年度",
        "sections": [
            {
                "title": "人工智能发展史",
                "content_pages": [
                    {
                        "title": "图灵时代",
                        "summary": "AI概念萌芽与早期探索",
                        "bullets": [
                            "1950年：图灵发表《计算机器与智能》",
                            "图灵测试：机器能否思考的哲学思考",
                            "1956年：达特茅斯会议，AI正式诞生",
                        ]
                    },
                ]
            },
        ]
    }

    print("Generating presentation...")
    result = await generate_presentation(outline)

    if result.success:
        print(f"Success! Output: {result.output_path}")
        print(f"Pages: {result.page_count}, Size: {result.document_size:,} chars")
        print("\nPage Layouts:")
        for i, layout in enumerate(result.page_layouts, 1):
            print(f"  {i}. [{layout['type']}] {layout.get('title', '')}")
            if "layout_type" in layout:
                print(f"      Layout: {layout['layout_type']}")
    else:
        print(f"Error: {result.error}")


# ============================================================
# 向后兼容接口
# ============================================================

async def run_pipeline(
    input_data: dict | str,
    output_format: str = "html",
) -> tuple[str, GenerationResult]:
    """
    向后兼容的流水线接口

    Args:
        input_data: 输入数据（dict 或 str）
        output_format: 输出格式（仅支持 html）

    Returns:
        (html_string, GenerationResult)
    """
    # 处理字符串输入
    if isinstance(input_data, str):
        from engine.content import parse_user_document
        pages = parse_user_document(input_data)
        sections = []
        for sem in pages:
            bullets = sem.bullet_points or [b.title for b in sem.bullet_items if b.title]
            sections.append(SectionInput(
                title=sem.title or f"内容页 {sem.page_index + 1}",
                content_pages=[ContentPageInput(
                    title=sem.title or "",
                    summary=sem.summary or "",
                    bullet_points=bullets,
                )],
            ))
        input_data = {
            "title": "演示文稿",
            "subtitle": "",
            "sections": sections,
        }

    # 构建大纲
    if isinstance(input_data, dict):
        outline = outline_from_dict(input_data)
    else:
        outline = input_data

    # 生成
    result = await generate_presentation(outline)

    # 读取生成的 HTML 文件
    html_content = ""
    if result.success and result.output_path:
        with open(result.output_path, "r", encoding="utf-8") as f:
            html_content = f.read()

    return html_content, result


if __name__ == "__main__":
    asyncio.run(main())
