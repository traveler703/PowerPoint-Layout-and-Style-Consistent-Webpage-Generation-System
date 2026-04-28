"""
端到端流水线：内容解析 → 版式推理 → LLM 片段 → HTML/Markdown 包裹 → 评估。

运行：在项目根目录执行 ``python pipeline.py``（已安装依赖与可选 ``.env``）。
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from engine.content import parse_user_document
from engine.reasoning import HeuristicReasoningEngine, PagePlan
from evaluator.layout_metrics import overlap_ratio_from_html
from evaluator.report import EvaluationReport, Severity
from evaluator.style_metrics import color_consistency_from_html
from framework.layouts import LayoutRegistry
from framework.tokens import get_theme, load_theme_catalog
from generator.html_generator import DocumentHtmlGenerator, merge_slides_to_document
from generator.langchain_chain import run_langchain_slide
from generator.llm_client import default_llm_client
from generator.markdown_generator import DocumentMarkdownGenerator
from generator.prompts import PromptContext, build_system_prompt, build_user_prompt

load_dotenv(Path(__file__).resolve().parent / ".env")

_REPO = Path(__file__).resolve().parent


def _themes_path() -> Path:
    return _REPO / "framework" / "data" / "themes.json"


def _registry() -> LayoutRegistry:
    return LayoutRegistry.default_from_package_data(_REPO / "framework")


async def _complete_llm(
    system: str,
    user: str,
    *,
    prefer_langchain: bool,
) -> str:
    if prefer_langchain and os.getenv("DEEPSEEK_API_KEY", "").strip():
        lc_text = await run_langchain_slide(system, user)
        if lc_text.strip():
            return lc_text
    client = default_llm_client()
    return await client.complete(system, user)


async def run_pipeline(
    user_text: str,
    *,
    theme_id: str = "business_blue",
    output_format: str = "html",
    prefer_langchain: bool = False,
) -> tuple[str, EvaluationReport]:
    """多页解析、启发式版式、生成并汇总评估。"""
    catalog = load_theme_catalog(_themes_path())
    tokens = get_theme(catalog, theme_id)
    registry = _registry()
    engine = HeuristicReasoningEngine()
    pages = parse_user_document(user_text)
    if not pages:
        pages = [parse_user_document("空白页")[0]]

    html_gen = DocumentHtmlGenerator()
    md_gen = DocumentMarkdownGenerator()
    slides: list[tuple[str, PagePlan, str]] = []
    md_chunks: list[str] = []

    for sem in pages:
        plan = engine.plan_page(sem, registry)
        ctx = PromptContext(
            style_tokens=tokens,
            page_plan=plan,
            user_content=sem.raw_notes or user_text,
            semantic=sem,
            output_format="markdown" if output_format == "markdown" else "html",
        )
        system = build_system_prompt(ctx)
        user_msg = build_user_prompt(ctx)

        fragment = await _complete_llm(system, user_msg, prefer_langchain=prefer_langchain)

        title = sem.title or f"第 {sem.page_index + 1} 页"
        if output_format == "markdown":
            md = await md_gen.generate(
                body=fragment,
                tokens=tokens,
                plan=plan,
                title=title,
                semantic=sem,
            )
            md_chunks.append(md)
        else:
            slides.append((title, plan, fragment))

    if output_format == "markdown":
        out = "\n\n".join(md_chunks)
        layout_m = overlap_ratio_from_html("<!DOCTYPE html><html><body></body></html>")
        style_m = color_consistency_from_html("", tokens)
    else:
        if len(slides) == 1:
            title, plan, frag = slides[0]
            out = await html_gen.generate(
                body_fragment=frag, tokens=tokens, plan=plan, title=title
            )
        else:
            out = merge_slides_to_document(
                slides=slides,
                tokens=tokens,
                doc_title="演示文稿",
            )
        layout_m = overlap_ratio_from_html(out)
        style_m = color_consistency_from_html(out, tokens)

    notes: list[str] = []
    if layout_m.overlap_ratio > 0:
        notes.append(
            f"检测到绝对定位重叠约 {layout_m.overlap_ratio:.2%}，建议避免 position:absolute 或调整布局。"
        )
    pct = style_m.global_color_deviation_percent
    if pct is not None and pct > 5.0:
        notes.append(f"全局颜色偏差约 {pct:.1f}%（目标 ≤5%）")
    notes.extend(style_m.token_violations)

    passed = layout_m.overlap_ratio == 0.0 and (pct is None or pct <= 5.0)
    severity = Severity.INFO if passed else Severity.WARN

    report = EvaluationReport(
        passed=passed,
        severity=severity,
        layout=layout_m,
        style=style_m,
        notes=notes or ["评估通过：未检测到绝对定位重叠；颜色与令牌基本一致。"],
    )
    return out, report


async def run_once(user_text: str = "示例：项目里程碑与风险") -> tuple[str, EvaluationReport]:
    """单入口兼容测试与旧版 API。"""
    return await run_pipeline(user_text, theme_id="business_blue", output_format="html")


def main() -> None:
    html, report = asyncio.run(run_once())
    print(report.model_dump_json(indent=2))
    print("--- HTML length:", len(html))


if __name__ == "__main__":
    main()
