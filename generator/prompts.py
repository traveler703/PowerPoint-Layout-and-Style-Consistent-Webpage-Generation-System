"""System / user prompt templates. Team: version and A/B test prompt variants here."""

from __future__ import annotations

from pydantic import BaseModel, Field

from engine.reasoning import PagePlan
from framework.tokens import StyleTokens


class PromptContext(BaseModel):
    """Everything needed to steer the model toward on-brand output."""

    style_tokens: StyleTokens
    page_plan: PagePlan
    user_content: str = ""
    output_format: str = Field(default="html", description="html | markdown")


def build_system_prompt(ctx: PromptContext) -> str:
    """Assemble system prompt with token injection (minimal stub)."""
    token_hint = ctx.style_tokens.model_dump_json(indent=2)
    return (
        "You are a front-end assistant that outputs accessible, responsive "
        f"{ctx.output_format} matching the design tokens below.\n"
        f"DESIGN_TOKENS_JSON:\n{token_hint}\n"
        f"LAYOUT_ID: {ctx.page_plan.layout_id}\n"
        "Implement the page strictly following the layout and tokens."
    )
