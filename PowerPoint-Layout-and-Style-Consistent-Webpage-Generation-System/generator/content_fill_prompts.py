"""Content fill prompts for template-driven generation.

This module provides prompts that guide the LLM to fill content into templates
without generating layout code. The template already defines the visual structure.
"""

from __future__ import annotations

import json
from typing import Any

from engine.reasoning import PagePlan
from engine.types import SemanticPageInput
from templates.template import Template, PageType


def build_content_fill_prompt(
    template: Template,
    page_type: str,
    content: SemanticPageInput,
    *,
    include_skeleton: bool = True,
) -> tuple[str, str]:
    """
    Build a prompt for filling content into a template.

    The LLM should NOT generate HTML layout code. Instead, it should provide
    structured content that will be rendered into the template's placeholders.

    Args:
        template: The template providing the structure
        page_type: The type of page (cover, content, toc, etc.)
        content: The parsed semantic content from user input
        include_skeleton: Whether to include skeleton HTML in the prompt

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    system_prompt = _build_system_prompt(template, page_type)
    user_prompt = _build_user_prompt(template, page_type, content)

    return system_prompt, user_prompt


def _build_system_prompt(template: Template, page_type: str) -> str:
    """Build the system prompt."""
    css_vars = json.dumps(template.css_variables, indent=2, ensure_ascii=False)

    rules = [
        "你是一个专业的内容创作助手，负责为PPT幻灯片生成丰富、有吸引力的内容。",
        "【重要】不要生成任何HTML标签、布局代码或CSS样式。只输出纯文本内容或JSON。",
        "【重要】严格遵循模板的风格定义，使用指定的颜色和字体。",
        "【重要】内容应该丰富、专业、有深度，能充分展现主题。",
        "",
        "【模板风格定义】",
        f"{css_vars}",
        "",
        "【页面类型详细说明】",
        _get_page_type_details(),
        "",
        f"【当前页面类型】{page_type}",
        "",
        "请根据提供的内容生成符合当前页面类型的填充数据。",
        "输出格式：JSON对象，包含页面类型所需的各个字段。",
    ]

    return "\n".join(rules)


def _get_page_type_details() -> str:
    """Get detailed instructions for each page type."""
    return """
    【cover - 封面页】
    需要生成：
    - main_title: 主标题（简洁有力，不超过20字）
    - subtitle: 副标题（概括主题，10-30字）
    - date_badge: 日期徽章文字（如"2026年春季"）
    - tagline: 标语/口号（可选，增强感染力）
    
    【toc - 目录页】
    需要生成：
    - toc_items: 目录项列表，每项包含：
      - number: 编号（如"01"）
      - title: 章节标题
      - description: 章节描述（1-2句话概括内容）
      - icon: 可选图标标识
    
    【content - 内容页】
    需要生成：
    - title: 页面标题
    - content: 详细正文内容（100-300字，包含深入分析）
    - highlights: 亮点列表（3-5个关键点）
    - conclusion: 本页小结（可选）
    
    【compare - 对比页】
    需要生成：
    - items: 对比卡片列表，每项包含：
      - title: 卡片标题（如时代名称）
      - era: 时代/类别标识
      - description: 详细描述（50-100字）
      - features: 特点列表（3-5个）
      - highlight: 亮点/贡献
    
    【timeline - 时间轴页】
    需要生成：
    - timeline_items: 时间节点列表，每项包含：
      - year: 年份/时间点
      - title: 事件标题
      - description: 详细描述（30-80字）
      - icon: 可选图标
    
    【qa - 问答页】
    需要生成：
    - qa_items: 问答对列表，每对包含：
      - question: 问题（具体、明确）
      - answer: 答案（详细、有深度，50-150字）
    
    【ending - 结尾页】
    需要生成：
    - message: 结束语/感谢语（简洁有力）
    - emoji: 表情符号（可选）
    - summary: 总结语（可选，1-2句话回顾主题）
    """


def _build_user_prompt(
    template: Template,
    page_type: str,
    content: SemanticPageInput,
) -> str:
    """Build the user prompt with content details."""
    parts = []

    # Title
    if content.title:
        parts.append(f"【标题】{content.title}")

    # Subtitle
    if content.summary:
        parts.append(f"【副标题/摘要】{content.summary}")

    # Page type specific fields
    if page_type == "toc" and content.toc_items:
        parts.append("【目录项】")
        for idx, item in enumerate(content.toc_items, 1):
            title = item.get("title", f"章节{idx}")
            desc = item.get("description", "")
            parts.append(f"  {idx}. {title}" + (f" - {desc}" if desc else ""))

    if page_type == "compare" and content.comparison_items:
        parts.append("【对比项】")
        for item in content.comparison_items:
            title = item.get("title", "")
            era = item.get("era", "")
            desc = item.get("description", "")
            features = item.get("features", [])
            parts.append(f"  ■ {title} ({era})")
            if desc:
                parts.append(f"    描述: {desc}")
            if features:
                parts.append(f"    特点: {', '.join(features)}")

    if page_type == "timeline" and content.timeline_items:
        parts.append("【时间轴】")
        for item in content.timeline_items:
            year = item.get("year", "")
            title = item.get("title", "")
            desc = item.get("description", "")
            parts.append(f"  {year}: {title}")
            if desc:
                parts.append(f"    {desc}")

    if page_type == "qa" and content.qa_items:
        parts.append("【问答对】")
        for idx, item in enumerate(content.qa_items, 1):
            q = item.get("question", "")
            a = item.get("answer", "")
            parts.append(f"  问{idx}: {q}")
            if a:
                parts.append(f"  答{idx}: {a}")

    # Bullet points
    if content.bullet_points:
        bullets = "\n".join(f"- {b}" for b in content.bullet_points)
        parts.append(f"【要点列表】\n{bullets}")

    # Bullet items (with title and description)
    if content.bullet_items:
        items = []
        for item in content.bullet_items:
            if item.description:
                items.append(f"- {item.title}: {item.description}")
            else:
                items.append(f"- {item.title}")
        if items:
            parts.append(f"【详细条目】\n" + "\n".join(items))

    # Headings
    if content.headings:
        headings = []
        for h in content.headings:
            level = "#" * h.level
            headings.append(f"{level} {h.text}")
        parts.append(f"【章节标题】\n" + "\n".join(headings))

    # Images
    if content.image_urls:
        parts.append(f"【图片URL】\n" + "\n".join(content.image_urls))

    # Table
    if content.has_table and content.table:
        parts.append(f"【表格数据】")
        parts.append(f"表头: {', '.join(content.table.headers)}")
        for row in content.table.rows[:5]:  # Limit rows
            parts.append(f"  - {', '.join(row)}")

    # Special markers
    if content.has_chart:
        parts.append("【特殊标记】包含图表内容")

    # Page info
    parts.append(f"【页码】{content.page_index + 1}")

    # Additional instructions based on page type
    if page_type == "content":
        parts.append("""
【内容扩展要求】
请为上述内容生成：
1. 详细的正文段落（100-300字），深入阐述主题
2. 3-5个亮点/关键点
3. 可选的总结语
""")

    elif page_type == "compare":
        parts.append("""
【对比内容扩展要求】
请为每个对比项生成：
1. 详细的描述（50-100字）
2. 3-5个核心特点
3. 该时代的亮点或历史贡献
""")

    elif page_type == "timeline":
        parts.append("""
【时间轴内容扩展要求】
请为每个时间节点生成：
1. 详细的描述（30-80字）
2. 该事件的影响或意义
""")

    elif page_type == "qa":
        parts.append("""
【问答内容扩展要求】
请为每个问答对生成：
1. 具体明确的问题
2. 详细深入的答案（50-150字）
""")

    return "\n\n".join(parts)


def build_toc_prompt(
    template: Template,
    sections: list[dict[str, Any]],
) -> tuple[str, str]:
    """
    Build a prompt specifically for generating TOC (Table of Contents) page.

    Args:
        template: The template
        sections: List of section dictionaries with 'title' and optional 'description'

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    system_prompt = _build_system_prompt(template, "toc")
    user_prompt = "请为以下章节生成目录内容：\n\n"

    for idx, section in enumerate(sections, 1):
        title = section.get("title", f"章节{idx}")
        description = section.get("description", "")
        user_prompt += f"{idx}. {title}"
        if description:
            user_prompt += f" - {description}"
        user_prompt += "\n"

    return system_prompt, user_prompt


def build_cover_prompt(
    template: Template,
    main_title: str,
    subtitle: str = "",
    date_text: str = "",
) -> tuple[str, str]:
    """
    Build a prompt specifically for generating a cover page.

    Args:
        template: The template
        main_title: The main title
        subtitle: Optional subtitle
        date_text: Optional date text

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    system_prompt = _build_system_prompt(template, "cover")
    user_prompt = f"""请为封面页生成内容：

【主标题】{main_title}
【副标题】{subtitle if subtitle else '请根据主题生成一个吸引人的副标题'}
【日期】{date_text if date_text else '2026年'}

请确保标题简洁有力，副标题能够概括主题内容。"""

    return system_prompt, user_prompt


def build_ending_prompt(
    template: Template,
    theme: str = "",
) -> tuple[str, str]:
    """
    Build a prompt specifically for generating an ending page.

    Args:
        template: The template
        theme: The presentation theme

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    system_prompt = _build_system_prompt(template, "ending")

    user_prompt = f"""请为结尾页生成内容：

【主题】{theme if theme else '通用主题'}
【结束语】请生成一段简洁的感谢语或总结语

结尾页应该简洁有力，表达感谢或留下深刻印象。"""

    return system_prompt, user_prompt


def parse_llm_content_response(response: str, page_type: str) -> dict[str, Any]:
    """
    Parse the LLM response into structured content.

    Args:
        response: The LLM's text response
        page_type: The page type

    Returns:
        Dictionary with parsed content
    """
    import re

    result: dict[str, Any] = {"page_type": page_type}

    # Try to parse as JSON
    try:
        # Look for JSON in the response
        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            json_str = json_match.group()
            # Clean up common JSON issues
            json_str = _clean_json_string(json_str)
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Fallback: extract structured content from text
    if page_type == "cover":
        result.update(_parse_cover_content(response))

    elif page_type == "content":
        result.update(_parse_content_response(response))

    elif page_type == "toc":
        result.update(_parse_toc_response(response))

    elif page_type == "compare":
        result.update(_parse_compare_response(response))

    elif page_type == "timeline":
        result.update(_parse_timeline_response(response))

    elif page_type == "qa":
        result.update(_parse_qa_response(response))

    elif page_type == "ending":
        result.update(_parse_ending_response(response))

    else:
        result["raw_content"] = response

    return result


def _clean_json_string(json_str: str) -> str:
    """Clean up common JSON formatting issues."""
    import re
    
    # Remove trailing commas before closing braces/brackets
    json_str = re.sub(r",\s*([\]}])", r"\1", json_str)
    
    # Fix unquoted keys if any
    # This is a simple fix for common issues
    return json_str


def _parse_cover_content(response: str) -> dict[str, Any]:
    """Parse cover page content from LLM response."""
    import re
    
    result = {}
    
    # Extract main_title
    patterns = [
        r"[\"']?main_title[\"']?\s*:\s*[\"'](.+?)[\"']",
        r"主标题[：:]\s*(.+?)(?:\n|$)",
        r"#\s*(.+?)(?:\n|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, response)
        if match:
            result["main_title"] = match.group(1).strip()
            break
    
    # Extract subtitle
    patterns = [
        r"[\"']?subtitle[\"']?\s*:\s*[\"'](.+?)[\"']",
        r"副标题[：:]\s*(.+?)(?:\n|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, response)
        if match:
            result["subtitle"] = match.group(1).strip()
            break
    
    # Extract date_badge
    patterns = [
        r"[\"']?date_badge[\"']?\s*:\s*[\"'](.+?)[\"']",
        r"日期[：:]\s*(.+?)(?:\n|$)",
        r"(\d{4}年[春夏秋冬]?季?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, response)
        if match:
            result["date_badge"] = match.group(1).strip()
            break
    
    # Extract tagline
    match = re.search(r"[\"']?tagline[\"']?\s*:\s*[\"'](.+?)[\"']", response)
    if match:
        result["tagline"] = match.group(1).strip()
    
    return result


def _parse_content_response(response: str) -> dict[str, Any]:
    """Parse content page response with rich details."""
    import re
    
    result: dict[str, Any] = {"highlights": []}
    
    # Extract main content
    content_match = re.search(r"[\"']?content[\"']?\s*:\s*[\"'](.+?)[\"'](?:\n|,|$)", response, re.DOTALL)
    if content_match:
        result["content"] = content_match.group(1).strip()
    else:
        # Extract content from markdown format
        lines = response.split("\n")
        content_lines = []
        in_content = False
        for line in lines:
            if any(marker in line.lower() for marker in ["content", "正文", "详细内容"]):
                in_content = True
                continue
            if in_content and line.strip():
                if line.startswith("-") or line.startswith("*") or line.startswith("#"):
                    break
                content_lines.append(line.strip())
        if content_lines:
            result["content"] = "\n".join(content_lines)
    
    # Extract highlights/bullet points
    highlight_matches = re.findall(r"- (.+?)(?:\n|$)", response)
    if highlight_matches:
        result["highlights"] = [h.strip() for h in highlight_matches[:5]]
    
    return result


def _parse_toc_response(response: str) -> dict[str, Any]:
    """Parse TOC page response."""
    import re
    
    items = []
    
    # Pattern for numbered items: 1. Title - description
    for match in re.finditer(r"(\d+)[.、]\s*([^-\n]+?)(?:\s*[-:]\s*(.+))?(?:\n|$)", response):
        number = match.group(1).strip()
        title = match.group(2).strip()
        description = match.group(3).strip() if match.group(3) else ""
        items.append({
            "number": number,
            "title": title,
            "description": description
        })
    
    # Alternative pattern: Title only
    if not items:
        for match in re.finditer(r"[■▪]\s*(.+?)(?:\n|$)", response):
            title = match.group(1).strip()
            items.append({
                "number": str(len(items) + 1),
                "title": title,
                "description": ""
            })
    
    return {"toc_items": items}


def _parse_compare_response(response: str) -> dict[str, Any]:
    """Parse comparison page response with detailed cards."""
    import re
    
    items = []
    
    # Pattern for comparison cards
    card_pattern = r"■|▪|\*\*(.+?)\*\*"
    current_card = {}
    
    for line in response.split("\n"):
        line = line.strip()
        if not line:
            continue
        
        # New card indicator
        if re.match(r"[■▪]", line):
            if current_card:
                items.append(current_card)
            current_card = {"features": []}
            title = re.sub(r"[■▪]\s*", "", line)
            current_card["title"] = title
            # Check for era in parentheses
            era_match = re.search(r"\(([^)]+)\)", title)
            if era_match:
                current_card["era"] = era_match.group(1)
                current_card["title"] = re.sub(r"\s*\([^)]+\)", "", title).strip()
        
        # Features
        elif line.startswith("-"):
            feature = re.sub(r"^-\s*", "", line).strip()
            if "features" not in current_card:
                current_card["features"] = []
            current_card["features"].append(feature)
        
        # Description
        elif any(marker in line for marker in ["描述", "说明", "特点"]):
            desc = re.sub(r".*[：:]\s*", "", line).strip()
            current_card["description"] = desc
        
        # Highlight
        elif "亮点" in line or "贡献" in line:
            highlight = re.sub(r".*[：:]\s*", "", line).strip()
            current_card["highlight"] = highlight
    
    if current_card:
        items.append(current_card)
    
    return {"items": items}


def _parse_timeline_response(response: str) -> dict[str, Any]:
    """Parse timeline page response."""
    import re
    
    items = []
    
    # Pattern: Year: Title - description
    for match in re.finditer(r"(\d{4}年?)\s*[:：]\s*(.+?)(?:\s*[-:]\s*(.+))?$", response, re.MULTILINE):
        year = match.group(1).strip()
        title = match.group(2).strip()
        description = match.group(3).strip() if match.group(3) else ""
        items.append({
            "year": year,
            "title": title,
            "description": description
        })
    
    # Alternative pattern without year prefix
    if not items:
        for match in re.finditer(r"[■▪]\s*(.+?)(?:\n|$)", response):
            parts = match.group(1).split("-")
            if len(parts) >= 2:
                items.append({
                    "year": parts[0].strip(),
                    "title": parts[1].strip(),
                    "description": parts[2].strip() if len(parts) > 2 else ""
                })
    
    return {"timeline_items": items}


def _parse_qa_response(response: str) -> dict[str, Any]:
    """Parse Q&A page response."""
    import re
    
    items = []
    current_q = ""
    current_a = ""
    
    for line in response.split("\n"):
        line = line.strip()
        if not line:
            continue
        
        # Question
        if re.match(r"^[问Qq][\.、:：]?\s*", line) or re.search(r"[\"']?question[\"']?\s*:\s*", line, re.I):
            if current_q and current_a:
                items.append({"question": current_q, "answer": current_a})
            current_q = re.sub(r"^[问Qq][\.、:：]\s*", "", line)
            current_q = re.sub(r"[\"']?question[\"']?\s*:\s*", "", current_q, flags=re.I).strip()
            current_a = ""
        
        # Answer
        elif re.match(r"^[答Aa][\.、:：]?\s*", line) or re.search(r"[\"']?answer[\"']?\s*:\s*", line, re.I):
            current_a = re.sub(r"^[答Aa][\.、:：]\s*", "", line)
            current_a = re.sub(r"[\"']?answer[\"']?\s*:\s*", "", current_a, flags=re.I).strip()
    
    # Add last Q&A pair
    if current_q and current_a:
        items.append({"question": current_q, "answer": current_a})
    
    return {"qa_items": items}


def _parse_ending_response(response: str) -> dict[str, Any]:
    """Parse ending page response."""
    import re
    
    result = {}
    
    # Extract message/thank you
    patterns = [
        r"[\"']?message[\"']?\s*:\s*[\"'](.+?)[\"']",
        r"感谢语[：:]\s*(.+?)(?:\n|$)",
        r"(谢谢|感谢观看|感谢聆听|再见)[！。]?",
    ]
    for pattern in patterns:
        match = re.search(pattern, response)
        if match:
            result["message"] = match.group(1).strip() if "message" in pattern else match.group(0).strip()
            break
    
    # Extract emoji
    emoji_match = re.search(r"[\"']?emoji[\"']?\s*:\s*[\"'](.+?)[\"']", response)
    if emoji_match:
        result["emoji"] = emoji_match.group(1).strip()
    else:
        # Find emoji in text
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF]+"
        )
        emojis = emoji_pattern.findall(response)
        if emojis:
            result["emoji"] = emojis[0]
    
    # Extract summary
    summary_match = re.search(r"总结[：:]\s*(.+?)(?:\n|$)", response)
    if summary_match:
        result["summary"] = summary_match.group(1).strip()
    
    return result


def infer_page_type_from_content(content: SemanticPageInput) -> str:
    """
    Infer the appropriate page type from semantic content.

    Args:
        content: The semantic page input

    Returns:
        Inferred page type string
    """
    # Check for specific markers
    if content.has_chart:
        return PageType.CHART

    if content.has_table:
        # If there's a table with many rows, might be comparison
        if content.table and len(content.table.rows) >= 3:
            return PageType.COMPARE
        return PageType.CONTENT

    # Check bullet count for TOC
    bullet_count = len(content.bullet_points) + len(content.bullet_items)
    if bullet_count >= 5 and not content.title:
        return PageType.TOC

    # Check if it's the first page (likely cover)
    if content.page_index == 0 and not content.bullet_points:
        return PageType.COVER

    # Check for Q&A pattern
    if any("?" in (content.title or "") for _ in [1]) or \
       any("?" in bp for bp in (content.bullet_points or [])):
        return PageType.QA

    # Check for timeline pattern (years, dates)
    text_content = f"{content.title or ''} {content.summary or ''}"
    if any(kw in text_content for kw in ["年", "时代", "阶段", "时间线"]):
        return PageType.TIMELINE

    # Default to content page
    return PageType.CONTENT
