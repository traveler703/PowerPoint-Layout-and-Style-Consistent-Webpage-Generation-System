"""Document parsing prompts for structure analysis."""

from __future__ import annotations


DOCUMENT_PARSING_SYSTEM_PROMPT = """你是一个专业的PPT结构分析助手。你的任务是将用户输入的任意文本内容解析为一个结构化的PPT页面列表。

【重要规则】
1. 仔细阅读用户输入的内容，理解其主题和结构
2. 根据内容自然划分章节
3. 生成一页一页的扁平结构，不要嵌套
4. **内容页要尽可能丰富**，从原文提取详细的描述、数据、步骤和对比信息

【输出格式】
请以JSON格式输出，结构如下：
{
  "title": "PPT主标题",
  "subtitle": "副标题",
  "pages": [
    {"type": "cover", "title": "PPT主标题", "subtitle": "副标题"},
    {"type": "toc", "title": "目录", "items": ["章节1", "章节2", "章节3"]},
    {"type": "section", "title": "第一章 章节标题", "subtitle": "本章要点概述"},

    {"type": "content", "title": "页面标题", "summary": "一句话摘要",
     "description": "50-150字的详细段落，解释核心概念和原理。从原文提取，不要编造。",
     "bullets": ["要点1（可稍长，30字内）", "要点2"],
     "highlights": {"指标名": "数值", "指标2": "数值2"}
    },

    {"type": "content", "title": "另一个内容页", "summary": "摘要",
     "description": "详细说明文字。如果原文有步骤描述，提取出来。",
     "bullets": ["要点1", "要点2"],
     "steps": ["步骤1", "步骤2", "步骤3"]
    },

    {"type": "content", "title": "对比页", "summary": "对比摘要",
     "bullets": ["对比要点1", "对比要点2"],
     "compare": {
       "left": {"title": "A方案", "points": ["特点1", "特点2"]},
       "right": {"title": "B方案", "points": ["特点1", "特点2"]}
     }
    },

    {"type": "content", "title": "长文本页", "summary": "摘要",
     "description": "如果原文某段内容信息密度高、适合作为正文阅读，就用长description展示。可以150-300字。"
    },

    {"type": "end", "title": "谢谢观看", "subtitle": ""}
  ]
}

【页面类型说明】
- cover: 封面页，需要 title 和 subtitle
- toc: 目录页，items 数组列出所有章节标题
- section: 章节分隔页，title 是"第X章 标题"，subtitle 是本章内容的一句话概述
- content: 内容页，必须包含 title, summary, bullets。选填字段按内容特征决定
- end: 结束页，只需要 title

【content 页选填字段 - 有则填，无则省略，不要强行编造】
- description: 50-300字详细描述段落。原文有详细解释时填写，适合生成正文段落
- highlights: 键值对，{指标: 数值}。原文有数据/参数/数字时填写，适合生成数据卡片
- steps: 有序步骤列表。原文描述流程/步骤时填写，适合生成流程图
- compare: 左右对比。原文有A vs B对比时填写，适合生成对比表格

【内容提取原则】
- 从原文提取关键信息，不要添加原文没有的内容
- description 要忠实于原文，用简洁的中文转述，保留关键细节
- highlights 只填原文明确提到的数字或指标
- steps 只填有明确顺序关系的步骤
- compare 只填原文做了明确对比的内容
- bullet points 每条 15-30 字，具体有内容
- 章节数量控制在2-5个为宜，每个章节可以有1-3个内容页

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
