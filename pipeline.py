"""
End-to-end placeholder pipeline:
内容语义占位 → 布局推理 → LLM 片段 → HTML 包裹 → 评估

Run: `python pipeline.py` from repo root (with venv + deps installed).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from dotenv import load_dotenv

from engine.reasoning import StubReasoningEngine
from engine.types import SemanticPageInput
from evaluator.layout_metrics import overlap_ratio_stub
from evaluator.report import EvaluationReport, Severity
from evaluator.style_metrics import color_delta_stub
from framework.layouts import LayoutRegistry
from framework.tokens import load_style_tokens
from generator.html_generator import StubHtmlGenerator
from generator.llm_client import StubLLMClient
from generator.prompts import PromptContext, build_system_prompt

load_dotenv(Path(__file__).resolve().parent / ".env")


async def run_once(user_text: str = "示例：项目里程碑与风险") -> tuple[str, EvaluationReport]:
    token_path = Path(__file__).resolve().parent / "framework" / "data" / "default_tokens.json"
    tokens = load_style_tokens(token_path)
    registry = LayoutRegistry.with_minimal_defaults()
    engine = StubReasoningEngine()
    semantic = SemanticPageInput(title="Demo", summary=user_text, bullet_points=["A", "B"])
    plan = engine.plan_page(semantic, registry)

    ctx = PromptContext(
        style_tokens=tokens,
        page_plan=plan,
        user_content=user_text,
        output_format="html",
    )
    system = build_system_prompt(ctx)
    llm = StubLLMClient()
    fragment = await llm.complete(system, user_text)
    html = await StubHtmlGenerator().generate(
        body_fragment=fragment, tokens=tokens, plan=plan, title=semantic.title or "Slide"
    )

    layout_m = overlap_ratio_stub(html)
    style_m = color_delta_stub(html, tokens)
    report = EvaluationReport(
        passed=True,
        severity=Severity.INFO,
        layout=layout_m,
        style=style_m,
        notes=["stub evaluators; tighten thresholds in production"],
    )
    return html, report


def main() -> None:
    html, report = asyncio.run(run_once())
    print(report.model_dump_json(indent=2))
    print("--- HTML length:", len(html))


if __name__ == "__main__":
    main()
