"""内容解析与版式推理单元测试。"""

from __future__ import annotations

from engine.content import parse_user_document
from engine.reasoning import HeuristicReasoningEngine
from engine.types import SemanticPageInput
from framework.layouts import LayoutRegistry


def test_split_pages_by_dash() -> None:
    text = "# A\n\n- x\n\n---\n\n# B\n\n- y\n"
    pages = parse_user_document(text)
    assert len(pages) == 2
    assert pages[0].title == "A"
    assert pages[1].title == "B"


def test_heuristic_picks_three_column() -> None:
    reg = LayoutRegistry.default_from_package_data()
    eng = HeuristicReasoningEngine()
    sem = SemanticPageInput(
        bullet_points=["a", "b", "c"],
        bullet_items=[],
    )
    plan = eng.plan_page(sem, reg)
    assert plan.layout_id == "three-column"


def test_heuristic_image_layout() -> None:
    reg = LayoutRegistry.default_from_package_data()
    eng = HeuristicReasoningEngine()
    sem = SemanticPageInput(
        title="图",
        image_urls=["https://example.com/x.png"],
        summary="x" * 500,
    )
    plan = eng.plan_page(sem, reg)
    assert plan.layout_id == "image-text-top"


def test_heuristic_table() -> None:
    from engine.types import TableData

    reg = LayoutRegistry.default_from_package_data()
    eng = HeuristicReasoningEngine()
    sem = SemanticPageInput(
        title="表",
        has_table=True,
        table=TableData(headers=["a", "b"], rows=[["1", "2"]]),
    )
    plan = eng.plan_page(sem, reg)
    assert plan.layout_id == "table-focus"
