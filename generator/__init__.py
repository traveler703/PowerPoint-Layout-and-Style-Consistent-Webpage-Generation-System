"""
LLM prompt assembly and HTML/Markdown emitters.
Implement `LLMClient` for DeepSeek/OpenAI-compatible APIs.
"""

from generator.html_generator import HtmlGenerator, StubHtmlGenerator
from generator.llm_client import LLMClient, StubLLMClient
from generator.markdown_generator import MarkdownGenerator, StubMarkdownGenerator
from generator.prompts import PromptContext, build_system_prompt

__all__ = [
    "LLMClient",
    "StubLLMClient",
    "PromptContext",
    "HtmlGenerator",
    "MarkdownGenerator",
    "StubHtmlGenerator",
    "StubMarkdownGenerator",
    "build_system_prompt",
]
