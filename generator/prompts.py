"""System / user prompt templates.

This module re-exports from the prompts package for backward compatibility.
The actual implementations are in the prompts/ subpackage.
"""

# Re-export from prompts package
from generator.prompts import (
    build_content_html_prompt,
    generate_color_scheme_from_template,
    parse_html_response,
)

# Also re-export the old-style functions if they exist
try:
    from generator.prompts.original import (
        PromptContext,
        build_semantic_payload,
        build_system_prompt,
        build_user_prompt,
        _extract_keywords,
    )
except ImportError:
    # If original module doesn't exist, these will not be available
    pass

__all__ = [
    "build_content_html_prompt",
    "generate_color_scheme_from_template",
    "parse_html_response",
]
