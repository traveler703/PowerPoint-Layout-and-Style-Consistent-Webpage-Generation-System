"""
大纲提示词 - LandPPT原版
步骤2: 生成大纲
步骤3: 验证/修复大纲
"""

OUTLINE_PROMPT = """你是专业的PPT大纲策划专家，请基于以下信息生成JSON格式大纲。

**主题信息**：
- 主题：{topic}
- 场景：{scenario}
- 受众：{audience}
- 要求页数：{page_count}页

**场景说明**：
- technology: 科技技术类
- business: 商业商务类
- education: 教育培训类
- medical: 医疗健康类
- finance: 金融投资类
- marketing: 市场营销类
- report: 分析报告类
- general: 通用场景

**输出格式要求**：
必须返回纯JSON格式，包含以下字段：
{{
    "title": "PPT标题",
    "subtitle": "副标题（可选）",
    "author": "作者信息（可选）",
    "slides": [
        {{
            "page_number": 1,
            "title": "页面标题",
            "content_points": ["要点1", "要点2", "要点3"],
            "slide_type": "title"
        }},
        ...
    ]
}}

**幻灯片类型说明**：
- title: 封面页
- agenda: 目录页
- content: 内容页
- section_header: 章节分隔页
- conclusion: 结论总结页
- thankyou: 感谢页

**结构要求**：
1. 第1页必须是封面页 (slide_type: title)
2. 第2页是目录页 (slide_type: agenda)，列出主要章节
3. 内容页 (slide_type: content) 至少占60%的页数
4. 最后一页是结论/感谢页 (slide_type: conclusion 或 thankyou)
5. 每页内容要点控制在2-5个，确保信息密度适中

**内容质量要求**：
- 内容要有深度和专业性，避免泛泛而谈
- 要点应包含具体数据、案例或观点
- 逻辑清晰，层次分明
- 符合场景特点（科技类偏技术细节，商业类偏价值主张）

请直接返回JSON格式，不要包含任何解释文字。
"""

OUTLINE_VALIDATION_PROMPT = """验证以下PPT大纲JSON是否有效。

**大纲内容**：
{outline_json}

**验证项目**：
1. 必须是有效的JSON格式
2. 必须包含 title 和 slides 字段
3. slides 必须是数组且长度与要求的page_count一致
4. 每页必须有 page_number, title, slide_type 字段
5. slide_type 必须是有效类型 (title/agenda/content/section_header/conclusion/thankyou)
6. 第1页必须是 title 类型
7. 最后一页必须是 conclusion 或 thankyou 类型

**修复规则**：
- 如果JSON格式错误，尝试修复
- 如果缺少必需字段，添加默认值
- 如果页数不对，调整slides数组长度
- 如果类型错误，修正为正确的类型

请返回修复后的JSON格式。
"""
