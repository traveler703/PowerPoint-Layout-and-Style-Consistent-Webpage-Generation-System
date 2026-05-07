"""Document parsing prompts for structure analysis."""

from __future__ import annotations


DOCUMENT_PARSING_SYSTEM_PROMPT = """你是一个专业的PPT结构分析助手。你的任务是将用户输入的任意文本内容解析为一个结构化的PPT页面列表。

【重要规则】
1. 仔细阅读用户输入的内容，理解其主题和结构
2. 根据内容自然划分章节
3. 生成一页一页的扁平结构，不要嵌套

【输出格式】
请以JSON格式输出，结构如下：
{
  "title": "PPT主标题（从内容中提取或根据主题生成）",
  "subtitle": "副标题（可选）",
  "pages": [
    {"type": "cover", "title": "PPT主标题", "subtitle": "副标题"},
    {"type": "toc", "title": "目录", "items": ["章节1", "章节2", "章节3"]},
    {"type": "section", "title": "第一章 章节标题", "subtitle": ""},
    {"type": "content", "title": "页面标题", "summary": "页面摘要", "bullets": ["要点1", "要点2", "要点3"]},
    {"type": "section", "title": "第二章 章节标题", "subtitle": ""},
    {"type": "content", "title": "页面标题", "summary": "页面摘要", "bullets": ["要点1", "要点2"]},
    {"type": "end", "title": "谢谢观看", "subtitle": ""}
  ]
}

【页面类型说明】
- cover: 封面页，只需要 title 和 subtitle
- toc: 目录页，items 数组列出所有章节标题
- section: 章节标题页，title 是"第X章 标题"
- content: 内容页，包含 title, summary, bullets
- end: 结束页，只需要 title

【内容提取原则】
- 从原文提取关键信息，不要添加原文没有的内容
- bullet points 应该简洁，每个不超过20字
- 章节数量控制在2-5个为宜
- 每个章节可以有1-2个内容页

请直接输出JSON，不要有其他解释文字。"""


def build_document_parsing_prompt(user_text: str) -> tuple[str, str]:
    """
    构建文档解析的 prompt。
    
    Args:
        user_text: 用户输入的原始文本
        
    Returns:
        (system_prompt, user_prompt) 元组
    """
    system_prompt = DOCUMENT_PARSING_SYSTEM_PROMPT
    
    user_prompt = f"""请解析以下文本内容，生成PPT页面列表：

---
{user_text}
---

请直接输出JSON格式的页面列表。"""
    
    return system_prompt, user_prompt


def parse_document_parsing_response(response: str) -> dict:
    """
    解析 LLM 返回的 JSON 响应。
    
    Args:
        response: LLM 返回的文本
        
    Returns:
        解析后的页面列表字典
    """
    import json
    import re
    
    # 尝试提取 JSON
    json_pattern = r'\{[\s\S]*\}'
    match = re.search(json_pattern, response)
    
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    
    # 如果解析失败，返回默认结构
    return {
        "title": "PPT演示文稿",
        "subtitle": "",
        "pages": [
            {"type": "cover", "title": "PPT演示文稿", "subtitle": ""},
            {"type": "end", "title": "谢谢观看", "subtitle": ""}
        ]
    }
