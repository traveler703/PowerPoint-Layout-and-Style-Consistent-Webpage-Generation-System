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
import logging
import os
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from engine.page_types import PageType
from engine.types import SemanticPageInput
from evaluator.layout_metrics import overlap_ratio_from_html
from evaluator.readability_metrics import fix_readability_colors, readability_from_html
from evaluator.style_metrics import color_consistency_from_html
from generator.llm_client import LLMClient, default_llm_client
from generator.prompts import (
    build_html_generation_prompt,
    build_layout_analysis_prompt,
    parse_html_response,
    parse_layout_analysis,
)
from templates.renderer import TemplateRenderer
from templates.template_loader import Template, load_template

logger = logging.getLogger(__name__)

MAX_CONTENT_GENERATION_ATTEMPTS = 4
MAX_COLOR_DEVIATION_PERCENT = 5.0
MAX_OVERLAP_RATIO = 0.0

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
    include_section_page: bool = True


@dataclass
class PresentationOutline:
    """演示文稿大纲"""
    title: str
    subtitle: str
    date_badge: str = ""
    toc_items: list[dict[str, str]] = field(default_factory=list)
    include_toc: bool = True
    include_ending: bool = True
    sections: list[SectionInput] = field(default_factory=list)
    ending_title: str = "谢谢观看"
    ending_message: str = ""


@dataclass
class GenerationResult:
    """生成结果"""
    success: bool
    output_path: str | None = None
    page_count: int = 0
    document_size: int = 0
    error: str | None = None
    page_layouts: list[dict[str, str]] = field(default_factory=list)
    pages_html: list[str] = field(default_factory=list)
    page_paths: list[str] = field(default_factory=list)


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
        self.llm_client = llm_client

    async def initialize(self) -> None:
        """初始化：加载模板和 LLM 客户端"""
        # 加载模板
        self.template = load_template(self.template_name)
        self.renderer = TemplateRenderer(self.template)

        logger.info(f"[Pipeline] 模板加载: {self.template_name}")
        logger.info(f"[Pipeline] CSS变量: {self.template.css_variables}")

        # 获取 LLM 客户端
        if self.llm_client is None:
            self.llm_client = default_llm_client()

    def _build_template_info(self) -> dict[str, Any]:
        """
        从当前模板构建风格信息字典，供 prompt 函数使用。

        包含：模板名称、描述、标签、字体风格、视觉美学、布局倾向。
        """
        if self.template is None:
            return {}

        css = self.template.css_variables
        # 从 css_variables 中提取字体信息
        font_body = css.get("font-body", css.get("font_body", ""))
        font_heading = css.get("font-heading", css.get("font_heading", ""))

        # 根据模板名称/描述推断视觉美学和布局倾向
        name = self.template.name
        description = self.template.description
        tags = self.template.tags

        aesthetic = ""
        layout_tendency = ""

        # 常见风格的视觉美学和布局倾向推断
        tag_str = " ".join(tags).lower()
        name_str = name.lower()
        desc_str = description.lower()

        if any(k in tag_str or k in name_str or k in desc_str for k in ["toy", "儿童", "活泼", "可爱", "积木"]):
            aesthetic = "活泼可爱、色彩明亮、圆润的边角、卡通装饰元素，适合儿童内容"
            layout_tendency = "卡片式布局为主，内容居中，大量留白，避免复杂排版"
        elif any(k in tag_str or k in name_str or k in desc_str for k in ["科技", "赛博", "cyber", "深色", "未来", "技术"]):
            aesthetic = "深邃科技感、霓虹光效、赛博朋克风格、发光边框和扫描线效果"
            layout_tendency = "紧凑的信息密度、HUD风格边框、网格背景、粒子动画装饰"
        elif any(k in tag_str or k in name_str or k in desc_str for k in ["水墨", "中国风", "传统", "文人", "古典", "雅致"]):
            aesthetic = "清新淡雅的中国传统水墨画风格，留白为美，印章点缀，衬线书法字体"
            layout_tendency = "简洁大方、左右对称或居中布局、留白充足、文字为主、避免过度装饰"
        elif any(k in tag_str or k in name_str or k in desc_str for k in ["商务", "企业", "报告", "正式"]):
            aesthetic = "商务专业、简洁干练、配色稳重、层次分明"
            layout_tendency = "标准化的卡片或列表布局、信息密度适中、清晰的视觉层级"
        elif any(k in tag_str or k in name_str or k in desc_str for k in ["简约", "极简", "干净", "清新"]):
            aesthetic = "简约极致、大量留白、克制用色、优雅精致"
            layout_tendency = "极简排版、单一内容突出、避免堆砌装饰元素"

        return {
            "name": name,
            "description": description,
            "tags": tags,
            "font_body": font_body,
            "font_heading": font_heading,
            "aesthetic": aesthetic,
            "layout_tendency": layout_tendency,
        }

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
        # Stage 1: 布局专家分析（传入CSS变量和模板风格信息）
        sys_prompt, user_prompt = build_layout_analysis_prompt(
            page, css_variables=self.template.css_variables, template_info=self._build_template_info()
        )
        logger.info("[Pipeline] [Stage1] ===== 布局专家分析 =====")
        logger.info(f"[Pipeline] [Stage1] 主题: {page.title}")
        logger.info(f"[Pipeline] [Stage1] sys_prompt:\n{sys_prompt}")
        logger.info(f"[Pipeline] [Stage1] user_prompt:\n{user_prompt}")
        response = await self.llm_client.complete(sys_prompt, user_prompt)
        logger.info(f"[Pipeline] [Stage1] LLM原始响应:\n{response}")
        try:
            layout_analysis = parse_layout_analysis(response)
        except Exception as parse_err:
            logger.error(f"[Pipeline] [Stage1] 解析失败: {parse_err}")
            raise
        logger.info(f"[Pipeline] [Stage1] 解析结果: {layout_analysis}")

        layout_info = {
            "layout_type": layout_analysis.get("layout_type", "card_grid"),
            "design_suggestions": layout_analysis.get("design_suggestions", []),
            "reasoning": layout_analysis.get("reasoning", ""),
        }

        logger.info(f"[Pipeline] 内容页生成 - 主题: {page.title}, 模板: {self.template_name}")

        html = ""
        quality_issues: list[str] = []
        prompt_page = page
        for attempt in range(MAX_CONTENT_GENERATION_ATTEMPTS):
            # Stage 2: HTML 生成（传入CSS变量和模板风格信息）
            sys_prompt, user_prompt = build_html_generation_prompt(
                page=prompt_page,
                layout_analysis=layout_analysis,
                css_variables=self.template.css_variables,
                template_info=self._build_template_info(),
            )
            logger.info(f"[Pipeline] [Stage2] ===== HTML生成 attempt={attempt + 1} =====")
            logger.info(f"[Pipeline] [Stage2] 主题: {page.title}")
            logger.info(f"[Pipeline] [Stage2] CSS变量: {self.template.css_variables}")
            logger.info(f"[Pipeline] [Stage2] sys_prompt:\n{sys_prompt}")
            logger.info(f"[Pipeline] [Stage2] user_prompt:\n{user_prompt}")
            response = await self.llm_client.complete(sys_prompt, user_prompt)
            logger.info(f"[Pipeline] [Stage2] LLM原始响应:\n{response[:1000]}")
            html = parse_html_response(response)
            logger.info(f"[Pipeline] [Stage2] 解析后HTML长度: {len(html)}")

            quality_issues = self._content_quality_issues(html)
            if not quality_issues:
                break
            logger.warning(
                "[Pipeline] 内容页质量检查未通过%s: page=%s issues=%s",
                "，将重试" if attempt + 1 < MAX_CONTENT_GENERATION_ATTEMPTS else "，已达到重试上限",
                page.title,
                "；".join(quality_issues),
            )
            if attempt + 1 >= MAX_CONTENT_GENERATION_ATTEMPTS:
                break
            prompt_page = SemanticPageInput(
                page_index=page.page_index,
                title=page.title,
                summary=(
                    (page.summary or "")
                    + "\n\n上一版页面质量检查未通过，请重新生成。必须修复："
                    + "；".join(quality_issues)
                    + "。不要重复标题，不要生成幻灯片外壳。元素重叠率必须为0，"
                    + "所有显式颜色必须来自模板CSS变量，色彩偏差率必须不超过5%。"
                    + "所有内容必须位于1160px x 530px内容区域内，禁止内容越界、"
                    + "ellipsis、line-clamp 或固定高度容器截断正文。"
                ),
                page_type=page.page_type,
                bullet_points=page.bullet_points,
                headings=page.headings,
                bullet_items=page.bullet_items,
                image_urls=page.image_urls,
                table=page.table,
                has_chart=page.has_chart,
                has_table=page.has_table,
                raw_notes=page.raw_notes,
                features=page.features,
            )

        if quality_issues:
            layout_info["quality_warnings"] = quality_issues

        html = self._fix_content_readability(html)
        return html, layout_info

    def _content_quality_issues(self, html: str) -> list[str]:
        """Check a generated content fragment against the report thresholds."""
        issues: list[str] = []
        if not html.strip():
            return ["内容为空"]
        if 'class="slide"' in html or "class='slide'" in html or "page-content" in html:
            issues.append("生成了嵌套幻灯片外壳")
        try:
            overlap_report = overlap_ratio_from_html(html)
            overlap = float(overlap_report.overlap_ratio or 0)
            if overlap > MAX_OVERLAP_RATIO:
                issues.append(f"元素重叠率为{overlap:.2%}，要求为0")
            if overlap_report.overflow_count:
                issues.append(f"{overlap_report.overflow_count}个绝对定位元素超出1160x530内容边界")
        except Exception as exc:
            logger.debug("[Pipeline] overlap check skipped: %s", exc)
        try:
            color_report = color_consistency_from_html(html, self.template.css_variables if self.template else {})
            deviation = float(color_report.global_color_deviation_percent or 0)
            if deviation > MAX_COLOR_DEVIATION_PERCENT:
                issues.append(
                    f"色彩偏差率为{deviation:.1f}%，要求不超过"
                    f"{MAX_COLOR_DEVIATION_PERCENT:.0f}%"
                )
        except Exception as exc:
            logger.debug("[Pipeline] color check skipped: %s", exc)
        try:
            readability = readability_from_html(html, self.template.css_variables if self.template else {})
            if readability.overflow_risk_count:
                issues.append(f"{readability.overflow_risk_count}处固定高度文本容器存在截断/越界风险")
        except Exception as exc:
            logger.debug("[Pipeline] readability check skipped: %s", exc)
        return issues

    def _fix_content_readability(self, html: str) -> str:
        """Fix low-contrast text colors in generated fragments without LLM retry."""
        try:
            fixed_html, fixed_count = fix_readability_colors(
                html,
                self.template.css_variables if self.template else {},
            )
            if fixed_count:
                logger.info("[Pipeline] 自动修正低对比度文字颜色: %s 处", fixed_count)
            return fixed_html
        except Exception as exc:
            logger.debug("[Pipeline] readability color fix skipped: %s", exc)
            return html

    async def generate_content_pages_parallel(
        self,
        content_pages: list[tuple[int, ContentPageInput]],
        total_pages: int,
        progress_callback: Callable[[int, int, dict[str, Any]], None] | None = None,
        page_ready_callback: Callable[[int, str, str, str], None] | None = None,
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

        tasks = [asyncio.create_task(generate_one(pn, cp)) for pn, cp in content_pages]
        results: list[tuple[int, str, dict]] = []
        titles = {pn: cp.title for pn, cp in content_pages}
        for task in asyncio.as_completed(tasks):
            page_num, html, layout_info = await task
            results.append((page_num, html, layout_info))
            title = next((cp.title for pn, cp in content_pages if pn == page_num), "")
            if progress_callback:
                rendered_html = self.renderer.render_content_page(
                    title=titles.get(page_num, ""),
                    content=html,
                    bullets=None,
                    page_number=page_num,
                    total_pages=total_pages,
                ) if self.renderer else html
                progress_callback(
                    page_num,
                    total_pages,
                    {
                        "page_number": page_num,
                        "page_type": "content",
                        "title": titles.get(page_num, ""),
                        "html": self._make_single_page_document(rendered_html, page_num, total_pages),
                        "layout_type": layout_info.get("layout_type", ""),
                        "quality_warnings": layout_info.get("quality_warnings", []),
                    },

                )
            if page_ready_callback:
                # 先包模板骨架，再包完整HTML文档，确保与 output/pages 一致
                skeleton = self.renderer.render_content_page(
                    title=title, content=html, bullets=None,
                    page_number=page_num, total_pages=total_pages,
                )
                standalone = self.render_standalone_page(skeleton, page_num)
                page_ready_callback(page_num, "content", title, standalone)
        return results

    async def generate_presentation(
        self,
        outline: PresentationOutline | dict,
        output_filename: str = "presentation.html",
        output_dir: str | None = None,
        navigation: bool = True,
        save_pages: bool = False,
        generate_content_with_llm: bool = True,
        progress_callback: Callable[[int, int, dict[str, Any]], None] | None = None,
        page_ready_callback: Callable[[int, str, str, str], None] | None = None,
    ) -> GenerationResult:
        """
        生成完整演示文稿

        Args:
            outline: 演示文稿大纲（dict 或 PresentationOutline）
            output_filename: 输出文件名
            output_dir: 输出目录；未指定时使用项目 output 目录
            navigation: 是否启用导航
            save_pages: 是否保存单页文件
            generate_content_with_llm: 内容页是否调用 LLM 生成；模板快速预览可关闭

        Returns:
            GenerationResult: 生成结果
        """
        # 转换 dict 为 PresentationOutline
        if isinstance(outline, dict):
            outline = outline_from_dict(outline)

        if self.renderer is None:
            await self.initialize()

        try:
            # 计算总页数：严格跟随前端大纲是否包含目录/结束页，避免生成页数凭空 +1。
            total_sections = sum(1 for s in outline.sections if s.include_section_page)
            total_content_pages = sum(len(s.content_pages) for s in outline.sections)
            total_pages = (
                1
                + (1 if outline.include_toc else 0)
                + total_sections
                + total_content_pages
                + (1 if outline.include_ending else 0)
            )

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
            if progress_callback:
                progress_callback(current_page_number, total_pages, {
                    "page_number": current_page_number,
                    "page_type": PageType.COVER.value,
                    "title": outline.title,
                    "html": self._make_single_page_document(cover_page, current_page_number, total_pages),

                })
            if page_ready_callback:
                page_ready_callback(current_page_number, "cover", outline.title,
                                    self.render_standalone_page(cover_page, current_page_number))
            current_page_number += 1

            # Optional TOC: only render it when the parsed/edited outline contains one.
            if outline.include_toc:
                toc_items = outline.toc_items or [
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
                if progress_callback:
                    progress_callback(current_page_number, total_pages, {
                        "page_number": current_page_number,
                        "page_type": PageType.TOC.value,
                        "title": "目录",
                        "html": self._make_single_page_document(toc_page, current_page_number, total_pages),
                    })
                current_page_number += 1


            # 收集所有需要生成的内容页信息
            content_pages_for_parallel: list[tuple[int, ContentPageInput]] = []

            for section_idx, section in enumerate(outline.sections, 1):
                # Section Page: only render when the source outline has an explicit section page.
                if section.include_section_page:
                    section_page = self.renderer.render_page(
                        page_type="section",
                        title=section.title,
                        subtitle="",
                        page_number=current_page_number,
                        total_pages=total_pages,
                        extra={"chapter_tag": f"第{_roman_numeral(section_idx)}章"},
                    )
                    pages_list.append((current_page_number, "section", section_page, {"type": "section", "title": section.title}))
                    if progress_callback:
                        progress_callback(current_page_number, total_pages, {
                            "page_number": current_page_number,
                            "page_type": PageType.SECTION.value,
                            "title": section.title,
                            "html": self._make_single_page_document(section_page, current_page_number, total_pages),
                        })
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
                if generate_content_with_llm:
                    results = await self.generate_content_pages_parallel(
                        content_pages_for_parallel,
                        total_pages,
                        progress_callback=progress_callback,
                        page_ready_callback=page_ready_callback,
                    )
                else:
                    results = []
                    for page_num, content_page in content_pages_for_parallel:
                        bullets_html = self.renderer._render_bullets(content_page.bullet_points)
                        content_html = bullets_html or content_page.summary
                        results.append((page_num, content_html, {"layout_type": "template"}))
                        if progress_callback:
                            rendered_html = self.renderer.render_content_page(
                                title=content_page.title,
                                content=content_html,
                                bullets=None,
                                page_number=page_num,
                                total_pages=total_pages,
                            )
                            progress_callback(
                                page_num,
                                total_pages,
                                {
                                    "page_number": page_num,
                                    "page_type": PageType.CONTENT.value,
                                    "title": content_page.title,
                                    "html": self._make_single_page_document(
                                        rendered_html, page_num, total_pages
                                    ),
                                    "layout_type": "template",
                                },
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

            # ============================================================
            # Last Page: Ending
            # ============================================================
            if outline.include_ending:
                ending_page = self.renderer.render_ending_page(
                    title=outline.ending_title,
                    content=outline.ending_message,
                    page_number=current_page_number,
                    total_pages=total_pages,
                )
                pages_list.append((current_page_number, "ending", ending_page, {
                    "type": "ending",
                    "title": outline.ending_title,
                }))
                if progress_callback:
                    progress_callback(current_page_number, total_pages, {
                        "page_number": current_page_number,
                        "page_type": PageType.ENDING.value,
                        "title": outline.ending_title,
                        "html": self._make_single_page_document(ending_page, current_page_number, total_pages),
                    })


            # 提取最终的 pages 和 page_layouts
            pages = [page_html for _, _, page_html, _ in pages_list]
            page_layouts = []
            for pn, _, _, layout in pages_list:
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

            resolved_output_dir = output_dir or os.path.join(
                os.path.dirname(__file__) if __file__ else ".",
                "output",
            )
            output_path = os.path.join(resolved_output_dir, output_filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(document)

            # 如果需要保存单页
            if save_pages:
                pages_dir = os.path.join(os.path.dirname(output_path), "pages")
                self._clear_pages_dir(pages_dir)
                page_paths = self._save_individual_pages(
                    pages, page_layouts, total_pages, pages_dir
                )
            else:
                page_paths = []

            return GenerationResult(
                success=True,
                output_path=output_path,
                page_count=len(pages),
                document_size=len(document),
                page_layouts=page_layouts,
                pages_html=pages,
                page_paths=page_paths,
            )

        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"[Pipeline] 未捕获异常:\n{tb}")
            return GenerationResult(
                success=False,
                error=f"{type(e).__name__}: {e}\n{tb}",
            )

    def _clear_pages_dir(self, pages_dir: str) -> None:
        """Clear stale per-page HTML files before saving a new presentation."""
        import shutil

        if os.path.isdir(pages_dir):
            shutil.rmtree(pages_dir)
            logger.info(f"[Pipeline] 清空旧页面目录: {pages_dir}")
        os.makedirs(pages_dir, exist_ok=True)


    def _save_individual_pages(
        self,
        pages: list[str],
        page_layouts: list[dict],
        total_pages: int,
        pages_dir: str,
    ) -> list[str]:
        """保存每个页面为独立的完整 HTML 文档"""
        if not self.template:
            return []

        page_paths: list[str] = []
        for idx, (page_html, layout) in enumerate(
            zip(pages, page_layouts, strict=False)
        ):
            page_num = idx + 1
            ptype = layout.get("type", "content")
            title = layout.get("title", "")

            single_html = self._make_single_page_document(page_html, page_num, total_pages)


            # 保存文件 - 加入模板名称前缀，避免不同模板的页面混淆
            safe_title = title.replace("/", "_")[:20] if title else ""
            # 文件名格式: {页码}_{模板名}_{类型}_{标题}.html
            filename = f"{page_num:02d}_{self.template_name}_{ptype}_{safe_title}.html"
            filepath = os.path.join(pages_dir, filename)
            
            # 先删除旧的同名文件（如果存在）
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"[Pipeline] 删除旧文件: {filename}")
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(single_html)
            logger.info(f"[Pipeline] 保存页面文件: {filename}")
            page_paths.append(filepath)
        return page_paths

    def _make_single_page_document(self, page_html: str, page_num: int, total_pages: int) -> str:
        """把单页片段包成完整 HTML，供缩略图/预览即时渲染。"""
        if not self.template or not self.renderer:
            return page_html
        slides_inner = f'''
            <div class="slide-container">
                <div class="slide-wrapper" data-page="{page_num}">
                    {page_html}
                </div>
            </div>
        '''
        single_html = self.template.raw_html
        if "{{SLIDES_CONTENT}}" in single_html:
            single_html = single_html.replace("{{SLIDES_CONTENT}}", slides_inner)
        elif "{SLIDES_CONTENT}" in single_html:
            single_html = single_html.replace("{SLIDES_CONTENT}", slides_inner)
        else:
            single_html = self._replace_slides_track_content(single_html, slides_inner)
        single_html = single_html.replace("{{TOTAL_PAGES}}", str(total_pages))
        single_html = single_html.replace("{TOTAL_PAGES}", str(total_pages))
        single_html = self.renderer._strip_inline_navigation_scripts(single_html)
        single_html = self.renderer._inject_runtime_overrides(single_html)
        single_html = single_html.replace('<div class="nav-dots"', '<div class="nav-dots" style="display:none"')
        single_html = single_html.replace('<div class="nav-arrows">', '<div class="nav-arrows" style="display:none">')
        single_html = single_html.replace('<div class="page-indicator"', '<div class="page-indicator" style="display:none"')
        return single_html

    def _replace_slides_track_content(self, html: str, slides_inner: str) -> str:
        """Replace sample slides in a raw template when it has no slides placeholder."""
        try:
            from bs4 import BeautifulSoup
        except Exception:
            return html

        soup = BeautifulSoup(html, "html.parser")
        track = soup.find("div", id="slidesTrack") or soup.find(
            "div",
            class_=lambda c: c and "slides-track" in str(c).split(),
        )
        if not track:
            return html

        track.clear()
        replacement = BeautifulSoup(slides_inner, "html.parser")
        for child in list(replacement.contents):
            track.append(child)
        return str(soup)


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
    def _clean_section_title(section_data: dict, index: int) -> str:
        """Pick a real section heading instead of a long summary/subtitle."""
        candidates = [
            section_data.get("page_title"),
            section_data.get("title"),
            section_data.get("name"),
            section_data.get("heading"),
        ]
        for candidate in candidates:
            title = str(candidate or "").strip()
            if not title:
                continue
            if len(title) <= 28:
                return title
            compact = title.replace("，", ",").replace("。", ".")
            if "," not in compact and "." not in compact and len(title) <= 40:
                return title

        fallback = str(section_data.get("title") or "").strip()
        if fallback:
            return fallback.split("，", 1)[0].split("。", 1)[0][:28]
        return f"第{index}章"

    sections = []
    for section_index, section_data in enumerate(data.get("sections", []), 1):
        content_pages = []
        for cp_data in section_data.get("content_pages", []):
            content_pages.append(ContentPageInput(
                title=cp_data["title"],
                summary=cp_data.get("summary", ""),
                bullet_points=cp_data.get("bullets", []),
            ))
        sections.append(SectionInput(
            title=_clean_section_title(section_data, section_index),
            content_pages=content_pages,
            include_section_page=bool(section_data.get("include_section_page", True)),
        ))
    return PresentationOutline(
        title=data.get("title", ""),
        subtitle=data.get("subtitle", ""),
        date_badge=data.get("date_badge", ""),
        toc_items=data.get("toc_items", []),
        include_toc=bool(data.get("include_toc", True)),
        include_ending=bool(data.get("include_ending", True)),
        sections=sections,
        ending_title=data.get("ending_title", "谢谢观看"),
        ending_message=data.get("ending_message", ""),
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
        "ending_title": "谢谢观看",
        "ending_message": "感谢您的聆听，期待与您深入交流！",
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
    outline = outline_from_dict(input_data) if isinstance(input_data, dict) else input_data

    # 生成
    result = await generate_presentation(outline)

    # 读取生成的 HTML 文件
    html_content = ""
    if result.success and result.output_path:
        with open(result.output_path, encoding="utf-8") as f:
            html_content = f.read()

    return html_content, result


if __name__ == "__main__":
    asyncio.run(main())
