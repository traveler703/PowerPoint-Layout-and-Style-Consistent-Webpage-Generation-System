"""
统一文档解析输出 Schema。
所有解析器（Markdown/PDF/DOCX/PPTX）最终都输出 DocumentParseResult 结构，
便于下游版式推理与代码生成模块统一消费。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# 数据模型
# ─────────────────────────────────────────────


class HeadingItem(BaseModel):
    """多级标题（1–4 级）。"""

    level: int = Field(ge=1, le=4, description="标题级别 1-4")
    text: str = Field(description="标题文本")


class BulletPoint(BaseModel):
    """要点条目：短标题 + 可选描述。"""

    title: str = Field(description="要点标题/关键词")
    description: str = Field(default="", description="要点详细描述")


class TableContent(BaseModel):
    """表格数据：表头 + 数据行。"""

    headers: list[str] = Field(default_factory=list, description="表头列名")
    rows: list[list[str]] = Field(default_factory=list, description="数据行")
    caption: str = Field(default="", description="表格标题/说明")


class ImageContent(BaseModel):
    """图片信息。"""

    url: str = Field(default="", description="图片 URL 或 base64 数据")
    alt: str = Field(default="", description="图片替代文本/描述")
    width: int | None = Field(default=None, description="图片宽度 px")
    height: int | None = Field(default=None, description="图片高度 px")


class PageContent(BaseModel):
    """单页/单节结构化内容。"""

    page_index: int = Field(default=0, description="页面索引（从 0 开始）")
    title: str | None = Field(default=None, description="页面主标题")
    headings: list[HeadingItem] = Field(default_factory=list, description="页面中的各级标题")
    paragraphs: list[str] = Field(default_factory=list, description="正文段落列表")
    bullets: list[BulletPoint] = Field(default_factory=list, description="要点列表")
    tables: list[TableContent] = Field(default_factory=list, description="表格列表")
    images: list[ImageContent] = Field(default_factory=list, description="图片列表")
    has_chart: bool = Field(default=False, description="是否包含图表")
    has_table: bool = Field(default=False, description="是否包含表格")
    raw_text: str = Field(default="", description="原始文本（用于回溯）")
    compressed: bool = Field(default=False, description="是否经过 LLM 压缩")
    compressed_from: str | None = Field(default=None, description="压缩前的原始文本（如已压缩）")

    @property
    def text_length(self) -> int:
        """计算页面总文本长度。"""
        total = 0
        if self.title:
            total += len(self.title)
        for h in self.headings:
            total += len(h.text)
        for p in self.paragraphs:
            total += len(p)
        for b in self.bullets:
            total += len(b.title) + len(b.description)
        return total

    @property
    def effective_bullet_count(self) -> int:
        """有效要点数量。"""
        return len(self.bullets)


class SourceFormat(str, Enum):
    """支持的输入文档格式。"""

    MARKDOWN = "markdown"
    TXT = "txt"
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"


class DocumentMetadata(BaseModel):
    """文档级元数据。"""

    title: str = Field(default="未命名文档", description="文档标题")
    source_format: SourceFormat = Field(default=SourceFormat.TXT, description="原始文件格式")
    source_filename: str = Field(default="", description="原始文件名")
    page_count: int = Field(default=0, description="解析出的页/节数量")
    total_chars: int = Field(default=0, description="原始文档总字符数")
    author: str = Field(default="", description="文档作者")
    extra: dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class DocumentParseResult(BaseModel):
    """
    统一文档解析结果。
    所有解析器最终输出此结构，可直接序列化为 JSON。
    """

    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    pages: list[PageContent] = Field(default_factory=list, description="页面/节内容列表")

    def to_json(self, indent: int = 2) -> str:
        """序列化为 JSON 字符串。"""
        return self.model_dump_json(indent=indent, exclude_none=True)

    def save_json(self, path: str | Path) -> None:
        """保存为 JSON 文件。"""
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def from_json(cls, json_str: str) -> DocumentParseResult:
        """从 JSON 字符串加载。"""
        return cls.model_validate_json(json_str)

    @classmethod
    def load_json(cls, path: str | Path) -> DocumentParseResult:
        """从 JSON 文件加载。"""
        text = Path(path).read_text(encoding="utf-8")
        return cls.from_json(text)


# ─────────────────────────────────────────────
# 解析器基类
# ─────────────────────────────────────────────


class BaseDocumentParser(ABC):
    """
    文档解析器基类。
    所有具体解析器必须实现 parse 方法。
    """

    @abstractmethod
    def parse(self, source: str | Path | bytes, filename: str = "") -> DocumentParseResult:
        """
        解析文档并返回统一结构化结果。

        Args:
            source: 文件路径、文本内容或文件字节流
            filename: 原始文件名（用于格式检测和元数据）

        Returns:
            DocumentParseResult 统一解析结果
        """
        raise NotImplementedError

    @staticmethod
    def detect_format(filename: str) -> SourceFormat:
        """根据文件扩展名检测格式。"""
        ext = Path(filename).suffix.lower()
        mapping = {
            ".md": SourceFormat.MARKDOWN,
            ".markdown": SourceFormat.MARKDOWN,
            ".txt": SourceFormat.TXT,
            ".pdf": SourceFormat.PDF,
            ".docx": SourceFormat.DOCX,
            ".pptx": SourceFormat.PPTX,
        }
        return mapping.get(ext, SourceFormat.TXT)
