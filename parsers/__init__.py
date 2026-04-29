"""
文档解析模块 (parsers)
支持 Markdown/TXT、PDF、DOCX、PPTX 四种格式的统一解析。
输出标准化 JSON 结构 (DocumentParseResult)，供下游版式推理与代码生成使用。
"""

from parsers.base import (
    DocumentParseResult,
    PageContent,
    HeadingItem,
    BulletPoint,
    TableContent,
    ImageContent,
    DocumentMetadata,
)
from parsers.markdown_parser import MarkdownParser
from parsers.pdf_parser import PdfParser
from parsers.docx_parser import DocxParser
from parsers.pptx_parser import PptxParser
from parsers.text_compressor import TextCompressor

__all__ = [
    "DocumentParseResult",
    "PageContent",
    "HeadingItem",
    "BulletPoint",
    "TableContent",
    "ImageContent",
    "DocumentMetadata",
    "MarkdownParser",
    "PdfParser",
    "DocxParser",
    "PptxParser",
    "TextCompressor",
]
