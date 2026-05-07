"""Content page HTML generation prompts.

This module provides prompts that guide the LLM to directly generate
creative HTML layout code for content pages. The layout is flexible
and adapts to the template's color scheme.
"""

from __future__ import annotations

import json
from typing import Any

from engine.types import SemanticPageInput


# ============================================================
# 共享的配色提示词模板
# ============================================================

COLOR_PROMPT_TEMPLATE = """配色风格 - 必须遵守（基于模板CSS变量自动适配）：
- **必须使用模板CSS变量中的颜色**，不要自行决定颜色
- 使用以下颜色变量生成配色：
  * 主题色：{THEME_COLOR}
  * 卡片背景：{CARD_BG}
  * 文字浅色：{TEXT_LIGHT}
  * 文字强调：{THEME_COLOR}
  * 文字次要：{TEXT_MUTED}
  * 背景半透明低：{BG_CARD_LOW}
  * 背景半透明中：{BG_CARD_MID}
  * 背景半透明高：{BG_CARD_HIGH}
  * 边框低：{BORDER_LOW}
  * 边框中：{BORDER_MID}
  * 边框高：{BORDER_HIGH}

配色参考：直接把上方变量值应用到对应的CSS属性中，保持与模板风格完全一致。"""


def _build_color_prompt(colors: dict[str, str]) -> str:
    """Build color prompt by substituting variables."""
    return COLOR_PROMPT_TEMPLATE.format(**colors)


def _get_default_css_variables() -> dict[str, str]:
    """Get default CSS variables."""
    return {
        "color-primary": "#00ffff",
        "color-text": "#e0e0e0",
        "color-text-muted": "#a0a0a0",
        "color-card": "#151a2d",
        "color-background": "#0a0c14",
    }


def generate_color_scheme_from_template(css_variables: dict[str, str]) -> dict[str, str]:
    """
    Generate color scheme variables from template CSS variables.
    
    This function automatically derives all color variants from the
    template's primary color and text colors.
    """
    primary = css_variables.get("color-primary", "#00ffff")
    text_light = css_variables.get("color-text", "#e0e0e0")
    text_muted = css_variables.get("color-text-muted", "#a0a0a0")
    card_bg = css_variables.get("color-card", "#151a2d")

    def hex_to_rgb(hex_color: str) -> tuple:
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    r, g, b = hex_to_rgb(primary)

    return {
        "THEME_COLOR": primary,
        "TEXT_LIGHT": text_light,
        "TEXT_MUTED": text_muted,
        "CARD_BG": card_bg,
        "BG_CARD_LOW": f"rgba({r},{g},{b},0.05)",
        "BG_CARD_MID": f"rgba({r},{g},{b},0.10)",
        "BG_CARD_HIGH": f"rgba({r},{g},{b},0.15)",
        "BORDER_LOW": f"rgba({r},{g},{b},0.2)",
        "BORDER_MID": f"rgba({r},{g},{b},0.3)",
        "BORDER_HIGH": f"rgba({r},{g},{b},0.4)",
        "BG_DARK_1": f"rgba({r},{g},{b},0.08)",
        "BG_DARK_2": f"rgba({r},{g},{b},0.12)",
        "TEXT_ACCENT": primary,
    }


def _extract_style_parts(template_info: dict | None) -> list[str]:
    """从 template_info 中提取风格描述行列表。"""
    if not template_info:
        return []
    parts = []
    name = template_info.get("name", "")
    description = template_info.get("description", "")
    tags = template_info.get("tags", [])
    font_body = template_info.get("font_body", "")
    font_heading = template_info.get("font_heading", "")
    aesthetic = template_info.get("aesthetic", "")
    layout_tendency = template_info.get("layout_tendency", "")
    if name:
        parts.append(f"- 模板名称：{name}")
    if description:
        parts.append(f"- 风格描述：{description}")
    if tags:
        parts.append(f"- 风格标签：{'、'.join(tags)}")
    if font_body:
        parts.append(f"- 正文字体风格：{font_body}")
    if font_heading:
        parts.append(f"- 标题字体风格：{font_heading}")
    if aesthetic:
        parts.append(f"- 视觉美学：{aesthetic}")
    if layout_tendency:
        parts.append(f"- 布局倾向：{layout_tendency}")
    return parts


def build_content_html_prompt(
    content: SemanticPageInput,
    css_variables: dict[str, str] | None = None,
    template_info: dict | None = None,
) -> tuple[str, str]:
    """
    Build a prompt for generating creative HTML layout for content pages.

    Args:
        content: The semantic page input with title, summary, and bullet points
        css_variables: Template CSS variables for color scheme (auto-generated if None)
        template_info: Template style metadata (name, description, tags, fonts, aesthetic)

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    if css_variables is None:
        css_variables = _get_default_css_variables()

    colors = generate_color_scheme_from_template(css_variables)
    color_prompt = _build_color_prompt(colors)
    theme_color = colors["THEME_COLOR"]

    # 构建模板风格信息
    style_parts = _extract_style_parts(template_info)

    # 用拼接方式构建 system_prompt
    system_prompt_parts = [
        "你是一位专业的前端开发工程师。",
        "",
        "重要规则：",
        "- 标题区域和页码由模板自动生成，请勿包含",
        "- 你只需要生成内容区域的 HTML 代码片段",
        f"- 主题色：{theme_color}",
        "",
        color_prompt,
        "",
        "创意布局 - 多样性是关键：",
        "- 不要只用卡片！每一页应该有独特的布局风格",
    ]

    if style_parts:
        system_prompt_parts.append("")
        system_prompt_parts.append("【模板风格信息 - 必须严格遵守】")
        system_prompt_parts.extend(style_parts)
        system_prompt_parts.append("请确保生成的内容页与该模板的整体风格完全一致。")

    system_prompt_parts.extend([
        "",
        "尝试以下布局方案：",
        "  * 时间线：横向或纵向的演进展示",
        "  * 阶梯式：像楼梯一样的递进层级",
        "  * 放射式：主题在中心，向外辐射",
        "  * 分栏式：左侧标题，右侧内容",
        "  * 杂志风：大标题 + 多栏排版",
        "  * 仪表盘：数字和指标展示",
        "  * 流程图：带箭头的流程展示",
        "  * 表格/网格：结构化数据展示",
        "  * 路线图：带里程碑的路径",
        "- 自由组合 flex、grid、position",
        "- 大量使用图标和 emoji",
        "",
        "尺寸约束 - 视觉质量的关键：",
        "- 内容区域：1160px 宽 x 530px 高",
        "- 所有内容必须在这个区域内，禁止溢出",
        "- 字体大小 14-18px",
        "- 使用 flex/grid 布局",
        "",
        "【溢出控制 - 最重要】",
        "- 每个容器 div 必须添加 `overflow: hidden` 防止内容溢出",
        "- 对长文本使用 `word-wrap: break-word`",
        "- 对单行文本使用 `text-overflow: ellipsis` 或 `white-space: nowrap`",
        "- 保持文字简洁，避免每行内容过多",
        "",
        "输出格式：",
        "- 用 ```html ... ``` 包裹",
        "- 只输出 div 代码片段",
        "- 不要使用 class=\"page-content\"",
        "",
        "【样式要求 - 最重要】",
        "- **禁止使用自定义 class，所有样式必须使用内联 style 属性**",
        "- **禁止使用 <style> 标签，不要生成任何 CSS 样式定义**",
        "- **禁止使用 overflow: visible，这会导致内容溢出**",
        "- 每个 div 必须有 `overflow: hidden` 或明确的 overflow 控制",
        "- 宽度和高度必须用具体数值（如 1160px, 100%）而不是 auto",
        "",
        "示例：",
        "```html",
        "<div style=\"width:1160px;height:530px;overflow:hidden;display:flex;\">",
        "  <div style=\"flex:1;background:rgba(0,0,0,0.05);overflow:hidden;\">内容...</div>",
        "</div>",
        "```",
    ])

    system_prompt = "\n".join(system_prompt_parts)

    bullet_lines = "\n".join(f"- {b}" for b in content.bullet_points)
    user_prompt = (
        f"请为内容区域生成创意布局。\n\n"
        f"标题：{content.title}\n"
        f"副标题/摘要：{content.summary}\n"
        f"要点：\n{bullet_lines}\n\n"
        f"约束条件：\n"
        f"1. 内容区域：1160px x 530px，禁止溢出\n"
        f"2. 不要生成 page-title\n"
        f"3. 字体 14-18px，保持内容简洁\n"
        f"4. 不要使用统一的 4 宫格布局\n"
        f"5. 使用创意、独特的布局\n"
        f"6. **关键**：每个卡片/容器必须添加 `overflow: hidden` 防止内容溢出\n"
        f"7. 避免文字重叠 - 使用适当的 padding、margin 和文字宽度控制"
    )

    return system_prompt, user_prompt


def parse_html_response(response: str) -> str:
    """Extract HTML from LLM response and clean up common issues."""
    import re

    # Remove code block markers
    response = re.sub(r'^```html\s*', '', response.strip(), flags=re.MULTILINE)
    response = re.sub(r'^```\s*', '', response.strip(), flags=re.MULTILINE)
    response = re.sub(r'\s*```$', '', response.strip())

    # Remove DOCTYPE declaration
    response = re.sub(r'<!DOCTYPE[^>]*>', '', response, flags=re.IGNORECASE)

    # Remove <html>, <head>, <body> tags (LLM sometimes generates full HTML document)
    response = re.sub(r'<\/?html[^>]*>', '', response, flags=re.IGNORECASE)
    response = re.sub(r'<\/?head[^>]*>.*?<\/?head>', '', response, flags=re.DOTALL | re.IGNORECASE)
    response = re.sub(r'<\/?body[^>]*>', '', response, flags=re.IGNORECASE)

    # Remove meta tags that might be present
    response = re.sub(r'<meta[^>]*>', '', response, flags=re.IGNORECASE)

    # Remove title tags
    response = re.sub(r'<title>.*?<\/title>', '', response, flags=re.DOTALL | re.IGNORECASE)

    # Remove <style> tags and their contents (LLM sometimes generates CSS)
    response = re.sub(r'<style[^>]*>.*?<\/style>', '', response, flags=re.DOTALL | re.IGNORECASE)

    # Remove any inline overflow: visible declarations
    response = re.sub(r'overflow\s*:\s*visible\s*;?', '', response, flags=re.IGNORECASE)

    # Strip leading/trailing whitespace but preserve structure
    response = response.strip()

    return response


# ============================================================
# 两阶段方法：基于布局分析的 HTML 生成
# ============================================================

def build_html_generation_prompt(
    page: SemanticPageInput,
    layout_analysis: dict,
    colors: dict | None = None,
    css_variables: dict[str, str] | None = None,
    template_info: dict | None = None,
) -> tuple[str, str]:
    """
    Build prompt for HTML generation based on layout expert analysis.

    This is the second stage of the two-stage approach where we use
    the layout expert's analysis to guide HTML generation.

    Args:
        page: The semantic page input with title, summary, and bullet points
        layout_analysis: Dict containing layout_type, design_suggestions, component_hints
        colors: Pre-generated color scheme (auto-generated if None)
        css_variables: Template CSS variables (used to generate colors if colors is None)
        template_info: Template style metadata (name, description, tags, fonts, aesthetic)

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    if colors is None:
        if css_variables is None:
            css_variables = _get_default_css_variables()
        colors = generate_color_scheme_from_template(css_variables)

    layout_type = layout_analysis.get("layout_type", "card_grid")
    design_suggestions = layout_analysis.get("design_suggestions", [])
    component_hints = layout_analysis.get("component_hints", [])
    reasoning = layout_analysis.get("reasoning", "")
    theme_color = colors["THEME_COLOR"]
    color_prompt = _build_color_prompt(colors)

    # 构建模板风格信息
    style_parts = _extract_style_parts(template_info)

    design_lines = "\n".join(f"- {s}" for s in design_suggestions)
    component_lines = "\n".join(f"- {c}" for c in component_hints)
    bullet_lines = "\n".join(f"- {b}" for b in page.bullet_points)

    sys_parts = [
        "你是一位专业的前端开发工程师。",
        "",
        "【你的任务】",
        "根据布局专家的分析结果，严格按照专家建议生成创意HTML布局。",
        "",
    ]

    if style_parts:
        sys_parts.append("【模板风格信息 - 必须严格遵守】")
        sys_parts.extend(style_parts)
        sys_parts.append("请确保生成的内容页与该模板的整体风格完全一致。")
        sys_parts.append("")

    sys_parts.extend([
        "重要规则：",
        "- 标题区域和页码、页脚都由模板自动生成，请勿包含",
        "- 你只需要生成内容区域的 HTML 代码片段",
        f"- 主题色：{theme_color}",
        "",
        color_prompt,
        "",
        "【布局专家分析结果 - 必须严格遵循】",
        f"推荐布局类型：{layout_type}",
        f"选择理由：{reasoning}",
        "",
        "专家设计建议（必须实现）：",
        design_lines,
        "",
        "可用组件：",
        component_lines,
        "",
        "尺寸约束：",
        "- 内容区域：1160px 宽 x 530px 高",
        "- 所有内容必须在这个区域内，禁止溢出",
        "- 字体大小 14-18px",
        "- 使用 flex/grid 布局",
        "",
        "【溢出控制 - 关键要求】",
        "- **文字必须完整显示，禁止使用 text-overflow: ellipsis 截断文字**",
        "- 每个容器 div 必须添加 `overflow: hidden` 防止内容溢出",
        "- 对长文本使用 `word-wrap: break-word` 和多行文本",
        "- **保持文字简短**，每行控制在10个中文字符以内，避免文字过长无法显示",
        "- **禁止使用绝对定位(absolute/fixed)**，会导致内容被裁剪或溢出",
        "- **必须使用 flex 或 grid 布局**，所有内容必须能完整显示在1160x530区域内",
        "- **文字必须完整显示**，卡片宽度必须足够容纳所有文字内容",
        "",
        "输出格式：",
        "- 用 ```html ... ``` 包裹",
        "- 只输出 div 代码片段",
        "- 不要使用 class=\"page-content\"",
        "",
        "【样式要求 - 最重要】",
        "- **禁止使用自定义 class，所有样式必须使用内联 style 属性**",
        "- **禁止使用 <style> 标签，不要生成任何 CSS 样式定义**",
        "- **禁止使用 overflow: visible，这会导致内容溢出**",
        "- 每个 div 必须有 `overflow: hidden` 或明确的 overflow 控制",
        "- 宽度和高度必须用具体数值（如 1160px, 100%）而不是 auto",
        "",
        "现在开始按照专家建议生成：",
    ])

    system_prompt = "\n".join(sys_parts)

    user_prompt = (
        f"请严格按照布局专家的设计建议生成HTML。\n\n"
        f"【标题】\n{page.title}\n\n"
        f"【副标题/摘要】\n{page.summary}\n\n"
        f"【要点列表】\n{bullet_lines}\n\n"
        f"【推荐布局类型】\n{layout_type}\n\n"
        f"【专家设计建议 - 必须遵循】\n{design_lines}\n\n"
        f"约束条件（必须严格遵守）：\n"
        f"1. 内容区域：1160px 宽 x 530px 高，**所有内容必须完整显示在此区域内**\n"
        f"2. **禁止使用绝对定位**，使用 flex/grid 布局\n"
        f"3. **禁止使用 text-overflow: ellipsis 截断文字**\n"
        f"4. **文字必须简短**：\n"
        f"   - 每行最多12个中文字符\n"
        f"   - 每张卡片最多2行文字\n"
        f"   - 总内容行数控制在4-6行以内\n"
        f"5. **卡片高度必须自适应内容**，不要设置固定max-height\n"
        f"6. **内容必须全部可见**，不允许任何溢出或裁剪"
    )

    return system_prompt, user_prompt
