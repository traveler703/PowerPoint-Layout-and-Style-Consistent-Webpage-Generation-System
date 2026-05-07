# 内容页 HTML 生成 - 两阶段布局方法

## 概述

内容页 HTML 生成采用**两阶段方法**，由布局专家先分析内容特点并推荐最适合的布局，再由 HTML 生成器根据专家建议生成具体代码。

### 优势

- **布局多样性**：每页根据内容特点选择最合适的布局（时间线、卡片网格、放射布局等）
- **设计专业性**：由"布局专家"给出详细的设计建议，包含结构、视觉元素、氛围等
- **溢出安全**：通过专家指导 + 严格的溢出控制规则，确保内容完整显示

---

## 核心流水线

```
┌─────────────────────────────────────────────────────────────────────┐
│                        完整 PPT 生成流程                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. 加载模板 (load_template)                                        │
│     └── 获取 CSS 变量、背景样式、字体配置                               │
│                                                                     │
│  2. 生成封面页 (render_cover_page)                                  │
│     └── 使用模板预定义的封面布局                                       │
│                                                                     │
│  3. 生成目录页 (render_toc_page)                                    │
│     └── 根据章节列表生成目录                                          │
│                                                                     │
│  4. 遍历每个章节                                                    │
│     ├── 章节分隔页 (render_page)                                     │
│     └── 内容页 (两阶段):                                              │
│         ├── Stage 1: 布局专家分析                                     │
│         │   └── build_layout_analysis_prompt()                        │
│         │   └── LLM 返回: layout_type, design_suggestions            │
│         │                                                                  │
│         └── Stage 2: HTML 生成                                         │
│             ├── generate_color_scheme_from_template()                  │
│             ├── build_html_generation_prompt()                         │
│             ├── LLM 返回: HTML 代码片段                                │
│             └── parse_html_response() → 清理 HTML                       │
│                                                                     │
│  5. 合并所有页面 (merge_pages_to_document)                           │
│     └── 将所有页面 HTML 合并为完整演示文稿                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 快速使用

### 方法 1：使用便捷函数

```python
import asyncio
from pipeline import generate_presentation

outline = {
    "title": "人工智能技术专题",
    "subtitle": "从基础理论到行业应用",
    "date_badge": "2026年度",
    "sections": [
        {
            "title": "人工智能发展史",
            "content_pages": [
                {
                    "title": "图灵时代",
                    "summary": "AI概念萌芽与早期探索",
                    "bullets": [
                        "1950年：图灵发表《计算机器与智能》",
                        "1956年：达特茅斯会议，AI正式诞生",
                    ]
                },
            ]
        },
    ]
}

# 异步调用
result = asyncio.run(generate_presentation(outline))

if result.success:
    print(f"Output: {result.output_path}")
    print(f"Pages: {result.page_count}")
```

### 方法 2：使用生成器类

```python
import asyncio
from pipeline import PresentationGenerator, PresentationOutline, SectionInput, ContentPageInput

# 构建大纲对象
outline = PresentationOutline(
    title="人工智能技术专题",
    subtitle="从基础理论到行业应用",
    date_badge="2026年度",
    sections=[
        SectionInput(
            title="人工智能发展史",
            content_pages=[
                ContentPageInput(
                    title="图灵时代",
                    summary="AI概念萌芽与早期探索",
                    bullet_points=[
                        "1950年：图灵发表《计算机器与智能》",
                        "1956年：达特茅斯会议，AI正式诞生",
                    ]
                ),
            ]
        ),
    ]
)

# 生成
generator = PresentationGenerator(template_name="tech")
result = await generator.generate_presentation(outline)
```

### 方法 3：向后兼容接口

```python
import asyncio
from pipeline import run_pipeline

# 字符串输入（按 --- 分页）
text = """
# 封面标题

---

## 第一章

内容页1

---

## 第二章

内容页2
"""

html, result = asyncio.run(run_pipeline(text))
```

---

## 核心模块

### 1. `generator/prompts/layout_analysis.py`

**布局专家阶段** - 分析内容并推荐布局

```python
from generator.prompts import build_layout_analysis_prompt, parse_layout_analysis

# 生成布局分析提示词
system_prompt, user_prompt = build_layout_analysis_prompt(page)

# 解析 LLM 返回的 JSON 分析结果
layout_analysis = parse_layout_analysis(llm_response)
# 返回: {"layout_type": "timeline", "design_suggestions": [...], ...}
```

**布局类型库**：

| 类型 | 说明 | 适用场景 |
|------|------|---------|
| `timeline` | 时间线布局 | 历史演进、发展阶段、里程碑 |
| `card_grid` | 卡片网格 | 多个并列要点或项目 |
| `split_columns` | 分栏布局 | 左右或上下分栏，主次分明 |
| `magazine` | 杂志布局 | 大标题 + 多栏正文排版 |
| `dashboard` | 仪表盘 | 数字指标、统计数据展示 |
| `stepped` | 阶梯布局 | 像楼梯一样的递进层级关系 |
| `radial` | 放射布局 | 中心主题向外辐射 |
| `flowchart` | 流程图 | 步骤流程、因果关系 |
| `list` | 列表布局 | 简洁的条目列表 |
| `quote` | 引用布局 | 大段引文配合说明 |

**分析输出格式**：

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

---

### 2. `generator/prompts/content_html.py`

**HTML 生成阶段** - 基于布局分析生成具体代码

```python
from generator.prompts import (
    build_html_generation_prompt,
    generate_color_scheme_from_template,
    parse_html_response,
)

# 生成配色方案（从模板 CSS 变量）
colors = generate_color_scheme_from_template(css_variables)

# 生成 HTML 提示词（传入布局分析结果）
system_prompt, user_prompt = build_html_generation_prompt(
    page=page,
    layout_analysis=layout_analysis,
    colors=colors,
)

# 解析 LLM 返回的 HTML 代码
html = parse_html_response(llm_response)
```

**关键约束**：

| 约束 | 说明 |
|------|------|
| 尺寸 | 内容区域 1160px × 530px |
| 布局 | 必须使用 flex/grid，禁止绝对定位 |
| 样式 | **禁止使用自定义 class，所有样式必须使用内联 style 属性** |
| 样式 | **禁止使用 `<style>` 标签** |
| 溢出 | **禁止 `overflow: visible`，每个容器必须 `overflow: hidden`** |
| 文字 | 禁止 `text-overflow: ellipsis` 截断文字 |
| 风格 | 深色夜空背景，使用主题色渐变 |

---

## 已修复的问题

### 1. 自定义 class 导致布局失效

**问题**：LLM 有时会生成自定义 class（如 `radial-wrapper`, `ray-cards`），但没有定义对应的 CSS 样式，导致页面布局完全失效。

**解决方案**：
- 提示词明确禁止使用自定义 class
- 要求所有样式使用内联 `style` 属性

### 2. `<style>` 标签污染

**问题**：LLM 有时会生成 `<style>` 标签定义样式，这些样式可能与模板冲突或无法正确加载。

**解决方案**：
- 提示词明确禁止生成 `<style>` 标签
- `parse_html_response()` 自动清理 `<style>` 标签

### 3. `overflow: visible` 导致内容溢出

**问题**：LLM 有时会生成 `overflow: visible`，导致内容溢出容器。

**解决方案**：
- 提示词明确禁止 `overflow: visible`
- `parse_html_response()` 自动移除 `overflow: visible` 声明

---

## 配色方案

从模板 CSS 变量自动生成：

```python
colors = {
    "THEME_COLOR": "#00ffff",           # 主题色
    "TEXT_LIGHT": "#e0e0e0",           # 浅色文字
    "TEXT_MUTED": "#a0a0a0",           # 次要文字
    "CARD_BG": "#151a2d",              # 卡片背景
    "BG_CARD_LOW": "rgba(0,255,255,0.05)",   # 低强调背景
    "BG_CARD_MID": "rgba(0,255,255,0.10)",   # 中强调背景
    "BG_CARD_HIGH": "rgba(0,255,255,0.15)",  # 高强调背景
    "BORDER_LOW": "rgba(0,255,255,0.2)",     # 低强调边框
    "BORDER_MID": "rgba(0,255,255,0.3)",     # 中强调边框
    "BORDER_HIGH": "rgba(0,255,255,0.4)",    # 高强调边框
}
```

---

## 测试脚本

```bash
# 运行完整测试（生成 14 页演示文稿）
python test_complete_presentation.py

# 输出示例
# [1/14] Rendering cover page...
# [4/14] Generating content page...
#     标题: 图灵时代
#     布局类型: timeline
#     ✓ 生成完成
# ...
# [DONE] Complete presentation generated!
# Output: output/test_complete_presentation.html
```

---

## 注意事项

1. **溢出控制**：这是最重要的约束，生成的内容必须完整显示在 1160×530 区域内
2. **绝对定位禁用**：使用 flex/grid 布局，避免绝对定位导致的布局问题
3. **文字截断禁用**：禁止使用 `text-overflow: ellipsis`，所有文字必须完整显示
4. **布局多样性**：鼓励布局专家选择不同布局类型，避免所有页面使用相同布局
5. **内联样式必须**：禁止使用自定义 class，所有样式必须使用内联 `style` 属性

---

## 文件结构

```
pipeline.py                    # 主流水线：PresentationGenerator, generate_presentation()
generator/prompts/
├── __init__.py               # 导出所有函数
├── content_html.py            # HTML 生成提示词（含两阶段第二阶段）
├── layout_analysis.py         # 布局分析提示词（两阶段第一阶段）
└── original.py                # 原始提示词（向后兼容）
```
