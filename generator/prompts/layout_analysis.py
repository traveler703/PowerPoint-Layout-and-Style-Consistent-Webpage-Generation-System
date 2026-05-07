"""Layout analysis prompts for two-stage HTML generation.

This module provides prompts for the layout expert to analyze content
and recommend appropriate layout designs before HTML generation.
"""

from __future__ import annotations

import json
import re
from typing import Any

from engine.types import SemanticPageInput


def build_layout_analysis_prompt(
    page: SemanticPageInput,
    css_variables: dict[str, str] | None = None,
    template_info: dict | None = None,
) -> tuple[str, str]:
    """
    Build prompt for layout expert to analyze content and recommend layouts.

    Args:
        page: The semantic page input with title, summary, and bullet points
        css_variables: Template CSS variables for color reference
        template_info: Template style metadata (name, description, tags, font info, aesthetic description)

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    # 构建模板风格描述块
    style_block = ""
    if template_info:
        name = template_info.get("name", "")
        description = template_info.get("description", "")
        tags = template_info.get("tags", [])
        font_body = template_info.get("font_body", "")
        font_heading = template_info.get("font_heading", "")
        aesthetic = template_info.get("aesthetic", "")
        layout_tendency = template_info.get("layout_tendency", "")

        style_parts = []
        if name:
            style_parts.append(f"- 模板名称：{name}")
        if description:
            style_parts.append(f"- 风格描述：{description}")
        if tags:
            style_parts.append(f"- 风格标签：{'、'.join(tags)}")
        if font_body:
            style_parts.append(f"- 正文字体风格：{font_body}")
        if font_heading:
            style_parts.append(f"- 标题字体风格：{font_heading}")
        if aesthetic:
            style_parts.append(f"- 视觉美学：{aesthetic}")
        if layout_tendency:
            style_parts.append(f"- 布局倾向：{layout_tendency}")

        if style_parts:
            style_block = "【模板风格信息 - 必须严格遵守】\n" + "\n".join(style_parts) + "\n\n请在设计建议中充分体现该模板的风格特征，使内容页与模板整体风格保持一致。\n\n"

    # 拼接CSS变量信息（避免f-string/.format中对花括号造成格式解析问题）
    css_info_block = ""
    if css_variables:
        color_vars = [(k, v) for k, v in css_variables.items() if k.startswith("color-")]
        if color_vars:
            css_info_block = "".join(f"- {k}: {v}\n" for k, v in color_vars).rstrip()
    if not css_info_block:
        css_info_block = "（无）"

    # 使用拼接字符串而非.format()，彻底避免JSON示例中的花括号被误解析为占位符
    system_prompt = (
        """你是一位资深的前端布局专家，精通各种创意页面布局设计。

你的任务是根据给定的内容，分析并推荐最适合的布局方案。

【配色参考 - 必须严格遵守】
模板CSS变量（直接使用变量名，不要硬编码颜色值）：
"""
        + css_info_block
        + """
- 如需描述颜色，统一使用语义名称：背景色用color-background，主色用color-primary，强调色用color-accent-xxx，文字色用color-text/color-text-muted
- **禁止在design_suggestions中使用任何硬编码颜色值**（如 #0f0c29、#1a1a2e、#FFFBEB 等）

"""
        + style_block
        + """【布局类型库】
请选择最合适的布局类型也可以你自己创造或可组合多种类型，请充分发挥你的创作能力，以下布局供参考：
1. 时间线布局 (timeline) - 展示历史演进、发展阶段、里程碑
2. 卡片网格布局 (card_grid) - 展示多个并列的要点或项目
3. 分栏布局 (split_columns) - 左右或上下分栏，主次分明
4. 杂志布局 (magazine) - 大标题 + 多栏正文排版
5. 仪表盘布局 (dashboard) - 数字指标、统计数据展示
6. 阶梯布局 (stepped) - 像楼梯一样的递进层级关系
7. 放射布局 (radial) - 中心主题向外辐射
8. 流程图布局 (flowchart) - 步骤流程、因果关系
9. 列表布局 (list) - 简洁的条目列表
10. 引用布局 (quote) - 大段引文配合说明

【分析维度】
1. 内容结构：是否有时序关系？是否需要对比？是否有主次之分？
2. 信息密度：内容简洁还是丰富？要点数量多少？
3. 视觉重点：强调的是什么？（数字、概念、对比、时间等）

【输出格式 - 非常重要】
请严格按以下JSON格式输出，design_suggestions必须详细描述具体实现方式：
```json
{
  "layout_type": "timeline",
  "secondary_layouts": [],
  "reasoning": "选择这种布局的简要理由（30字以内）",
  "design_suggestions": [
    "具体描述：应该使用什么样的布局结构",
    "具体描述：每个内容块应该怎么排列",
    "具体描述：需要什么样的视觉元素（图标、颜色、装饰等）",
    "具体描述：整体氛围和风格"
  ],
  "component_hints": [
    "具体组件1",
    "具体组件2"
  ]
}
```

design_suggestions示例（时间线布局）：
```json
"design_suggestions": [
  "左侧放置垂直时间轴线，用主题色渐变，从上到下依次排列4个年代节点",
  "右侧对应时间轴放置4张卡片，卡片内显示年代、标题、简要描述",
  "时间轴节点用发光圆点装饰，年代数字用大字号强调",
  "卡片背景使用半透明深色，带主题色边框"
]
```

design_suggestions示例（卡片网格）：
```json
"design_suggestions": [
  "使用2x2网格布局，每个格子放置一张等大的卡片",
  "每张卡片包含图标、标题、描述三个层次",
  "卡片带圆角、主题色边框、悬停发光效果",
  "标题用强调色，描述用次要文字色"
]
```
"""
    )

    user_prompt = f"""请分析以下内容，推荐最适合的布局方案：

【标题】
{page.title}

【副标题/摘要】
{page.summary}

【要点列表】
{chr(10).join(f"- {b}" for b in page.bullet_points)}

请分析内容特点，生成详细的布局建议。"""

    return system_prompt, user_prompt


def parse_layout_analysis(response: str) -> dict:
    """
    Parse layout analysis from LLM response.

    Args:
        response: The LLM response containing JSON layout analysis

    Returns:
        Dictionary with layout_type, reasoning, design_suggestions, component_hints
    """
    # Extract JSON from response
    match = re.search(r'\{[\s\S]*\}', response)
    if match:
        try:
            result = json.loads(match.group())
            # Ensure design_suggestions has enough detail
            if len(result.get("design_suggestions", [])) < 2:
                # Add default suggestions if too few
                result["design_suggestions"] = [
                    "使用推荐布局类型组织内容",
                    "配合适当的图标和装饰元素"
                ]
            return result
        except json.JSONDecodeError:
            pass

    # Fallback
    return {
        "layout_type": "card_grid",
        "secondary_layouts": [],
        "reasoning": "默认使用卡片网格布局",
        "design_suggestions": [
            "使用2x2网格布局展示要点",
            "每张卡片带图标、标题、描述",
            "卡片带圆角和主题色边框"
        ],
        "component_hints": ["卡片", "图标"]
    }
