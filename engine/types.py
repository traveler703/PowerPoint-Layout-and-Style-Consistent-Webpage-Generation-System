"""Shared types between engine and generator."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HeadingBlock(BaseModel):
    """多级标题（1–4 级）。"""

    level: int = Field(ge=1, le=4)
    text: str


class BulletItem(BaseModel):
    """要点：短标题 + 可选描述。"""

    title: str
    description: str = ""


class TableData(BaseModel):
    """简单表格：首行为表头。"""

    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)


class SemanticPageInput(BaseModel):
    """单页语义输入：由内容解析或上游抽取得到。"""

    page_index: int = 0
    title: str | None = None
    summary: str | None = None
    bullet_points: list[str] = Field(default_factory=list)
    headings: list[HeadingBlock] = Field(default_factory=list)
    bullet_items: list[BulletItem] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)
    table: TableData | None = None
    has_chart: bool = False
    has_table: bool = False
    raw_notes: str | None = None
    features: dict[str, Any] = Field(default_factory=dict)
    
    # 扩展字段：页面类型和目录项
    page_type: str | None = Field(default=None, description="页面类型：cover, content, toc, compare, chart, timeline, qa, ending")
    toc_items: list[dict[str, str]] = Field(default_factory=list, description="目录项列表，包含 title 和 description")
    
    # 扩展字段：丰富内容生成
    comparison_items: list[dict[str, Any]] = Field(default_factory=list, description="对比卡片列表")
    timeline_items: list[dict[str, str]] = Field(default_factory=list, description="时间轴项目列表")
    qa_items: list[dict[str, str]] = Field(default_factory=list, description="问答对列表")

    def effective_bullet_count(self) -> int:
        if self.bullet_items:
            return len(self.bullet_items)
        return len(self.bullet_points)

    def text_length(self) -> int:
        parts: list[str] = []
        if self.title:
            parts.append(self.title)
        if self.summary:
            parts.append(self.summary)
        parts.extend(self.bullet_points)
        for h in self.headings:
            parts.append(h.text)
        for b in self.bullet_items:
            parts.append(b.title)
            parts.append(b.description)
        if self.raw_notes:
            parts.append(self.raw_notes)
        return sum(len(p) for p in parts)
