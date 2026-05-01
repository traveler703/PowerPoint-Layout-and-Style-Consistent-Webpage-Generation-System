"""Prompts package for PPT generation.

Modules:
- content_html: Content page HTML generation prompts (two-stage approach)
- layout_analysis: Layout expert analysis prompts (first stage of two-stage approach)
- original: Original prompt templates for backward compatibility
"""

from generator.prompts.content_html import (
    build_content_html_prompt,
    build_html_generation_prompt,
    generate_color_scheme_from_template,
    parse_html_response,
)

from generator.prompts.layout_analysis import (
    build_layout_analysis_prompt,
    parse_layout_analysis,
)

from generator.prompts.original import (
    PromptContext,
    build_semantic_payload,
    build_system_prompt,
    build_user_prompt,
    _extract_keywords,
)

from generator.prompts.document_parsing import (
    build_document_parsing_prompt,
    parse_document_parsing_response,
)

__all__ = [
    # Content HTML generation (direct, single-stage)
    "build_content_html_prompt",
    "generate_color_scheme_from_template",
    "parse_html_response",
    # Two-stage: layout analysis (stage 1)
    "build_layout_analysis_prompt",
    "parse_layout_analysis",
    # Two-stage: HTML generation (stage 2)
    "build_html_generation_prompt",
    # Original prompts
    "PromptContext",
    "build_semantic_payload",
    "build_system_prompt",
    "build_user_prompt",
    "_extract_keywords",
    # Document parsing
    "build_document_parsing_prompt",
    "parse_document_parsing_response",
]
