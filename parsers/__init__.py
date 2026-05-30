"""文档解析器统一入口。"""

from .service import (
    parse_document_to_json,
    parsed_json_to_outline,
    parsed_json_to_frontend_pages,
    extract_text_from_file,
)

__all__ = [
    "parse_document_to_json",
    "parsed_json_to_outline",
    "parsed_json_to_frontend_pages",
    "extract_text_from_file",
]
