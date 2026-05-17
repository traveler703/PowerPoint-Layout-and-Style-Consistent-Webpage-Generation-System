"""
Template Generator - LLM 驱动：只输出 HTML，从 HTML 直接提取模板信息。

LLM 输出 HTML → 系统从 HTML 解析 CSS 变量、skeleton、page_type → 零 JSON 歧义。

用法:
    python scripts/template_generator.py "设计一个森林主题的PPT模板"

返回格式:
    {
        "success": true,
        "response": {"html": str},
        "parsed": {template_dict},
        "validation": (bool, errors),
        "model": "deepseek-chat"
    }
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import Any

sys_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if sys_path not in __import__("sys").path:
    __import__("sys").path.insert(0, sys_path)

from generator.llm_client import default_llm_client, LLMClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

STANDARD_PAGE_TYPES = {"cover", "toc", "section", "content", "ending"}

LAYOUT_PAGE_TYPE_ORDER = [
    "hero-title-body",
    "two-column",
    "three-column",
    "image-text-left",
    "image-text-top",
    "chart-focus",
    "table-focus",
    "title-only",
    "quote-highlight",
    "timeline",
    "comparison",
    "statistics",
]

LAYOUT_PAGE_TYPES = set(LAYOUT_PAGE_TYPE_ORDER)

SUPPORTED_PAGE_TYPES = STANDARD_PAGE_TYPES | LAYOUT_PAGE_TYPES

PAGE_TYPE_PLACEHOLDERS = {
    "cover": ("title", "subtitle", "date_badge"),
    "toc": ("title", "toc_items"),
    "section": ("chapter_tag", "title", "subtitle"),
    "content": ("title", "content"),
    "ending": ("title", "message"),
    "hero-title-body": ("title", "content"),
    "two-column": ("title", "left", "right"),
    "three-column": ("title", "col1", "col2", "col3"),
    "image-text-left": ("title", "media", "content"),
    "image-text-top": ("title", "media", "content"),
    "chart-focus": ("title", "chart", "content"),
    "table-focus": ("title", "table", "content"),
    "title-only": ("title", "subtitle"),
    "quote-highlight": ("title", "quote", "attribution"),
    "timeline": ("title", "timeline_items"),
    "comparison": ("title", "left_title", "left", "right_title", "right"),
    "statistics": ("title", "stat1", "stat2", "stat3", "content"),
}


# ============================================================
# Prompt：只输出 HTML
# ============================================================

TEMPLATE_GENERATION_SYSTEM_PROMPT = """你是一位极具创意的前端设计师。请为 PPT 演示系统生成一个主题模板。

## 输出要求

只输出一个 HTML 代码块（```html），不要有任何解释文字。

HTML 要求：
- 完整、可直接运行的 HTML 文件，包含至少 12 个 slide 页面示例：
  - 基础页：cover、toc、section、content、ending
  - 扩展版式页：hero-title-body、two-column、three-column、image-text-left、image-text-top、chart-focus、table-focus、title-only、quote-highlight、timeline、comparison、statistics
- 每个页面用 `<div class="slide [page_type]">` 包裹，page_type 取值必须来自上面的基础页或扩展版式页
- **【最重要】所有页面都必须遵循统一的结构规范**：

  **外层容器结构**（必须严格遵守）：
  ```html
  <body>
    <div class="slides-wrapper" id="slidesWrapper">
      <div class="slides-track" id="slidesTrack">
        <!-- 所有 slide 页面放这里 -->
      </div>
    </div>
    <div class="nav-dots" id="navDots"></div>     <!-- JS 动态生成，HTML 留空 -->
    <div class="nav-arrows">
      <div class="nav-arrow" id="prevBtn" onclick="prevSlide()">◀</div>
      <div class="nav-arrow" id="nextBtn" onclick="nextSlide()">▶</div>
    </div>
    <div class="page-indicator"><span class="current" id="currentPage">1</span> / <span id="totalPages">{{TOTAL_PAGES}}</span></div>
  </body>
  ```
  - 外层必须用 `.slides-wrapper` + `.slides-track`（横向 flex 排列）
  - 导航点容器 `.nav-dots` 的 HTML 必须留空（id="navDots"），由 JS 动态生成 dot
  - **禁止**在 `.nav-dots` 内硬编码任何 `<button>` 或 `<div class="nav-dot">` 元素
  - 箭头用 `<div>`（非 `<button>`），且要绑定 onclick 属性

  **导航 JS**（必须包含）：
  ```javascript
  const navDots = document.getElementById('navDots');
  for (let i = 0; i < totalSlides; i++) {
    const dot = document.createElement('div');
    dot.className = 'nav-dot' + (i === 0 ? ' active' : '');
    dot.onclick = () => goToSlide(i);
    navDots.appendChild(dot);
  }
  ```
  - 必须用 JS 动态生成导航点，绝对不能在 HTML 里硬编码

  **页面切换机制**：
  - 用 CSS `transform: translateX()` 横向滑动切换页面
  - 不要用 opacity 切换（opacity 切换体验差）
  - 示例 `.slides-track { display: flex; transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1); }`

- **关键占位符**：`{{SLIDES_CONTENT}}`（在 .slides-track 内）和 `{{TOTAL_PAGES}}`（在 JS 和 page-indicator 中）
- slide 尺寸 1280×720px，**必须用 `width: 1280px; height: 720px`**，禁止使用 `min-width` 或其他相对尺寸
- **【重要】布局方式：必须使用 absolute 绝对定位**：
  - `.slide` 的 CSS 必须是 `position: relative; overflow: hidden`
  - `.page-title` 必须用 `position: absolute; top: 40px; left: 60px`（或其他合适坐标）
  - `.page-content` 必须用 `position: absolute; top: 130px; left: 60px; right: 60px; bottom: 60px`（或其他合适坐标）
  - `.slide-footer` 必须用 `position: absolute; bottom: 15px` 居中或靠右
  - **禁止使用 `display: flex; flex-direction: column`** 作为 slide 的主布局方式
  - 装饰元素也使用 absolute 定位固定在 slide 内
  - 页面切换必须用 `transform: translateX()` 滑动，不许用 opacity 切换
- **禁止在 CSS 伪元素（`::before` / `::after`）中使用 `{{content}}` 占位符或任何内容**
- 字体使用真实 Google Fonts
- 页面示例内容由你自由创意设计（主题由用户描述指定）

## 每种 page_type 的占位符要求和结构规范（必须严格遵守）

### cover 封面页（必须严格遵守以下结构）
```html
<div class="slide cover">
  <div class="slide-footer"><span class="page-num">{{page_number}}</span></div>
</div>
```
**严格要求**：封面页也必须有 `.slide-footer` + `.page-num` 结构，且放在 slide 内部底部。
标题（h1）、副标题（.subtitle）、日期徽章（.date-badge）可以自由排列，但必须在外层 slide 内部，使用 absolute 定位。

### toc 目录页（必须严格遵守以下结构）
```html
<div class="slide toc">
  <div class="page-title">{{title}}</div>
  <div class="page-content">{{toc_items}}</div>
  <div class="slide-footer"><span class="page-num">{{page_number}}</span></div>
</div>
```
**严格要求**：`{{title}}` 用 `.page-title` div 包裹，`{{toc_items}}` 用 `.page-content` div 包裹，末尾必须有 `.slide-footer`。
这些元素在 CSS 中必须用 absolute 定位（top/left/right/bottom）。

### section 章节页（必须严格遵守以下结构）
```html
<div class="slide section">
  <div class="page-title">{{chapter_tag}}</div>
  <h1 class="section-title">{{title}}</h1>
  <p class="subtitle">{{subtitle}}</p>
  <div class="slide-footer"><span class="page-num">{{page_number}}</span></div>
</div>
```
**严格要求**：`{{chapter_tag}}`（如"第一章"）用 `.page-title` 包裹，`{{title}}` 用 `<h1 class="section-title">` 包裹，`{{subtitle}}` 用 `<p class="subtitle">` 包裹，末尾必须有 `.slide-footer`。
这些元素在 CSS 中必须用 absolute 定位。

### content 内容页（核心要求 - 必须严格遵守）
```html
<div class="slide content">
  <div class="page-title">{{title}}</div>
  <div class="page-content">{{content}}</div>
  <div class="slide-footer"><span class="page-num">{{page_number}}</span></div>
</div>
```
**严格要求**：
- `{{title}}` 必须用 `.page-title` div 包裹
- `{{content}}` 必须用 `.page-content` div 包裹
- 末尾必须有 `.slide-footer` + `.page-num`
- 这些元素在 CSS 中必须用 absolute 定位（`.page-title` 顶部定位，`.page-content` 四边约束）
- **`{{content}}` 内部必须完全空白**：禁止在 `{{content}}` 中放任何内容，包括：
  - 装饰性 div / svg / span 元素
  - HTML 注释 `<!-- -->`
  - 背景色块、波浪、图标、emoji 文字
  - 任何文字内容
- `.page-content` 标签本身可以有背景色、内边距等样式属性，但标签内部除了 `{{content}}` 占位符之外不能有任何其他内容
- 正确示例：`<div class="page-content">{{content}}</div>`（内部只有占位符）
- 错误示例：`<div class="page-content"><!-- 装饰 -->...很多div...</div>`（会被系统拒绝）

### 扩展版式页（用于适配更多场景）
扩展版式页也必须是 `<div class="slide [page_type]">`，必须包含 `.page-title` 和 `.slide-footer`，内部必须使用对应占位符：
- `hero-title-body`: `{{title}}`, `{{content}}`
- `two-column`: `{{title}}`, `{{left}}`, `{{right}}`
- `three-column`: `{{title}}`, `{{col1}}`, `{{col2}}`, `{{col3}}`
- `image-text-left`: `{{title}}`, `{{media}}`, `{{content}}`
- `image-text-top`: `{{title}}`, `{{media}}`, `{{content}}`
- `chart-focus`: `{{title}}`, `{{chart}}`, `{{content}}`
- `table-focus`: `{{title}}`, `{{table}}`, `{{content}}`
- `title-only`: `{{title}}`, `{{subtitle}}`
- `quote-highlight`: `{{title}}`, `{{quote}}`, `{{attribution}}`
- `timeline`: `{{title}}`, `{{timeline_items}}`
- `comparison`: `{{title}}`, `{{left_title}}`, `{{left}}`, `{{right_title}}`, `{{right}}`
- `statistics`: `{{title}}`, `{{stat1}}`, `{{stat2}}`, `{{stat3}}`, `{{content}}`

### ending 结尾页（必须严格遵守以下结构）
```html
<div class="slide ending">
  <div class="ending-content">
    <h1>{{title}}</h1>
    <p class="ending-message">{{message}}</p>
  </div>
  <div class="slide-footer"><span class="page-num">{{page_number}}</span></div>
</div>
```
**严格要求**：标题用 `<h1>`，消息用 `<p class="ending-message">`，全部包裹在 `.ending-content` 内，末尾必须有 `.slide-footer`。
这些元素在 CSS 中必须用 absolute 定位。

## 重要约束（必须遵守）

1. **每种基础 page_type 都必须生成示例页面**：cover、toc、section、content、ending；同时尽量生成全部扩展版式页
2. **占位符使用双花括号**：`{{title}}`、`{{subtitle}}`、`{{date_badge}}`、`{{chapter_tag}}`、`{{content}}`、`{{toc_items}}`、`{{message}}`、`{{page_number}}` 以及扩展版式页要求的占位符
3. **color-* 和 font-* CSS 变量必须全部填写**，不得为空
4. **页面中要有装饰元素**（emoji、几何图形、渐变等），体现主题特色，装饰元素只能放在 slide 外层或 `.page-title` 旁边，**禁止放在 `.page-content` 内部**
5. **【最关键】`{{content}}` 占位符内部必须保持空白**：
   - `.page-content` 标签内部**只能有 `{{content}}` 占位符**，禁止有任何其他内容
   - 不能有装饰性 div、svg、span、emoji、HTML 注释
   - 错误写法：`<div class="page-content"><!-- 装饰 -->...</div>`（会被系统拒绝）
   - 正确写法：`<div class="page-content">{{content}}</div>`
6. **【关键】外层容器和导航结构必须符合标准**：
   - 必须使用 `.slides-wrapper` + `.slides-track` 外层结构
   - `.nav-dots` 容器必须留空，由 JS 动态生成
   - 禁止在 `.nav-dots` 内硬编码任何导航点元素
   - 页面切换必须用 `transform: translateX()` 滑动，不许用 opacity 切换
7. **【关键】slide 尺寸必须固定**：
   - `.slide` 的 CSS 必须用 `width: 1280px; height: 720px`
   - **禁止使用 `min-width: 100%`**，必须用固定宽高
   - **【重要】布局方式：必须使用 absolute 绝对定位**
   - `.slide` 必须为 `position: relative; overflow: hidden`
   - `.page-title` 必须用 `position: absolute; top: 40px; left: 60px` 等固定坐标
   - `.page-content` 必须用 `position: absolute; top: 130px; left: 60px; right: 60px; bottom: 60px` 等四边约束
   - `.slide-footer` 必须用 `position: absolute; bottom: 15px` 等固定坐标
   - **禁止使用 `display: flex; flex-direction: column`** 作为 slide 主布局

现在开始生成！"""


# ============================================================
# 从 HTML 提取模板信息的核心逻辑
# ============================================================

def _extract_css_variables(html: str) -> dict[str, str]:
    """从 HTML 中全面提取 CSS 变量，支持任意命名格式及硬编码颜色兜底。"""
    result = {}

    # 策略1：从 :root {} 块中提取所有 --* 变量
    root_match = re.search(r":root\s*\{([^}]+)\}", html, re.DOTALL | re.IGNORECASE)
    if root_match:
        root_content = root_match.group(1)
        all_vars = re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", root_content, re.IGNORECASE)
        for var_name, var_value in all_vars:
            result[var_name] = var_value.strip()
    else:
        # 策略2：从整个 HTML 中扫描所有 --* 变量
        all_vars = re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", html, re.IGNORECASE)
        for var_name, var_value in all_vars:
            if var_name not in result:
                result[var_name] = var_value.strip()

    # 策略3：标准化映射
    STANDARD_KEYS = {
        "color-primary":      "--color-primary",
        "color-secondary":    "--color-secondary",
        "color-accent":       "--color-accent",
        "color-background":    "--color-background",
        "color-surface":      "--color-surface",
        "color-text":         "--color-text",
        "color-text-muted":   "--color-text-muted",
        "color-card":         "--color-card",
        "font-body":          "--font-body",
        "font-heading":       "--font-heading",
    }
    FALLBACKS = {
        "color-primary":      "#4CAF50",
        "color-secondary":    "#2196F3",
        "color-accent":      "#FF9800",
        "color-background":  "#ffffff",
        "color-surface":     "#f5f5f5",
        "color-text":        "#1a1a1a",
        "color-text-muted":  "#888888",
        "color-card":        "#ffffff",
        "font-body":         "sans-serif",
        "font-heading":      "sans-serif",
    }

    standardized = {}
    for std_key, raw_key in STANDARD_KEYS.items():
        if raw_key in result and result[raw_key]:
            val = result[raw_key].strip()
            if len(val) >= 4:
                standardized[std_key] = val

    # 策略4（兜底）：从硬编码颜色中提取主题色
    if not standardized.get("color-primary"):
        # 取 body background 作为主色
        body_bg = re.search(r"body\s*\{[^}]*background\s*:\s*([^;]+)", html, re.IGNORECASE | re.DOTALL)
        if body_bg:
            bg_val = body_bg.group(1).strip()
            first_hex = re.search(r"#([0-9a-fA-F]{6})", bg_val)
            if first_hex:
                standardized["color-background"] = "#" + first_hex.group(1).lower()
        # 取 slide.cover 的主色
        cover_bg = re.search(r"\.slide\.cover\s*\{[^}]*background\s*:\s*([^;]+)", html, re.IGNORECASE | re.DOTALL)
        if cover_bg:
            bg_val = cover_bg.group(1).strip()
            first_hex = re.search(r"#([0-9a-fA-F]{6})", bg_val)
            if first_hex:
                standardized["color-primary"] = "#" + first_hex.group(1).lower()
        # 取 slide.content 的背景
        content_bg = re.search(r"\.slide\.content\s*\{[^}]*background(?:\s*|-)\s*([^;]+)", html, re.IGNORECASE | re.DOTALL)
        if content_bg:
            bg_val = content_bg.group(1).strip()
            first_hex = re.search(r"#([0-9a-fA-F]{6})", bg_val)
            if first_hex:
                standardized["color-surface"] = "#" + first_hex.group(1).lower()
        # 取文字颜色
        text_color = re.search(r"\.slide\s*\{[^}]*color\s*:\s*#([0-9a-fA-F]{6})\b", html, re.IGNORECASE | re.DOTALL)
        if not text_color:
            text_color = re.search(r"color\s*:\s*#([0-9a-fA-F]{6})\b", html)
        if text_color:
            standardized["color-text"] = "#" + text_color.group(1).lower()
        # 取 accent/primary 颜色
        accent_color = re.search(r"(?:accent|highlight)(?:\s*:\s*|[-:]\s*)#([0-9a-fA-F]{6})\b", html, re.IGNORECASE)
        if not accent_color:
            accent_color = re.search(r"\.page-num[^{]*background\s*:\s*#([0-9a-fA-F]{6})", html, re.IGNORECASE | re.DOTALL)
        if accent_color:
            standardized["color-accent"] = "#" + accent_color.group(1).lower()
        # 字体
        font_match = re.search(r"font-family\s*:\s*([^;]+)", html, re.IGNORECASE)
        if font_match:
            font_val = font_match.group(1).strip().strip("'\"")
            if font_val:
                standardized["font-body"] = font_val
                standardized["font-heading"] = font_val

    # 补全未提取到的标准 key
    for std_key in STANDARD_KEYS:
        if std_key not in standardized:
            standardized[std_key] = FALLBACKS.get(std_key, "")

    return standardized



def _normalize_skeleton(ptype: str, skeleton: str) -> str:
    """
    规范化 skeleton 结构，确保所有 page_type 符合标准结构规范。

    规则：
    - 所有页面末尾必须有 <div class="slide-footer"><span class="page-num">{{page_number}}</span></div>
    - toc/section/content 页必须有 .page-title 和 .page-content 包裹
    - section 页的 title 必须在 .page-title 或单独的标题元素中
    - ending 页必须在 .ending-content 内
    """
    skeleton = skeleton.strip()

    # 统一 page_number 占位符
    skeleton = re.sub(
        r'<span[^>]*class="[^"]*\bpage-num\b[^"]*"[^>]*>[^<]*</span>',
        '<span class="page-num">{{page_number}}</span>',
        skeleton,
        flags=re.IGNORECASE,
    )

    # 确保末尾有 slide-footer（content/section/toc 必须有，cover/ending 也要有）
    has_footer = 'slide-footer' in skeleton
    if not has_footer:
        footer = '<div class="slide-footer"><span class="page-num">{{page_number}}</span></div>'
        # 找到 </div> 结束标签（slide 的结束标签）
        # 简单策略：追加到骨架末尾
        skeleton = skeleton + '\n' + footer

    # cover 页：识别 h1 为 title，.subtitle 为 subtitle，.date-badge 为 date_badge
    if ptype == "cover":
        # 处理 h1：如果有文本内容但没有占位符，替换为占位符
        h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', skeleton, re.DOTALL | re.IGNORECASE)
        if h1_match:
            h1_inner = h1_match.group(1).strip()
            # 如果 h1 内没有 {{title}} 占位符，替换为占位符
            if '{{title}}' not in h1_inner and '{{title}}' not in skeleton:
                skeleton = re.sub(
                    r'<h1[^>]*>.*?</h1>',
                    '<h1>{{title}}</h1>',
                    skeleton,
                    count=1,
                    flags=re.DOTALL | re.IGNORECASE,
                )
            elif '{{title}}' not in skeleton:
                # h1 有占位符但主骨架没有，把 h1 里的占位符合并到主骨架
                skeleton = skeleton.replace('{{title}}', '')
                skeleton = re.sub(r'<h1[^>]*>', '<h1>{{title}}', skeleton, count=1)
                skeleton = re.sub(r'</h1>', '</h1>', skeleton, count=1)
        # 处理 .subtitle：如果有文本但没有 {{subtitle}} 占位符
        subtitle_match = re.search(r'<div[^>]*class="[^"]*\bsubtitle\b[^"]*"[^>]*>(.*?)</div>', skeleton, re.DOTALL | re.IGNORECASE)
        if subtitle_match:
            sub_inner = subtitle_match.group(1).strip()
            if '{{subtitle}}' not in sub_inner:
                skeleton = re.sub(
                    r'<div[^>]*class="[^"]*\bsubtitle\b[^"]*"[^>]*>.*?</div>',
                    '<div class="subtitle">{{subtitle}}</div>',
                    skeleton,
                    count=1,
                    flags=re.DOTALL | re.IGNORECASE,
                )
        # 处理 .date-badge
        badge_match = re.search(r'<div[^>]*class="[^"]*\bdate-badge\b[^"]*"[^>]*>(.*?)</div>', skeleton, re.DOTALL | re.IGNORECASE)
        if badge_match:
            badge_inner = badge_match.group(1).strip()
            if '{{date_badge}}' not in badge_inner:
                skeleton = re.sub(
                    r'<div[^>]*class="[^"]*\bdate-badge\b[^"]*"[^>]*>.*?</div>',
                    '<div class="date-badge">{{date_badge}}</div>',
                    skeleton,
                    count=1,
                    flags=re.DOTALL | re.IGNORECASE,
                )

    if ptype == "toc":
        # toc 页（净化阶段已完成，内容已替换为 {{toc_items}}）：
        # 只处理结构包装，确保 .page-title 和 .page-content 包裹正确
        # 提取 .page-content 块
        pc_match = re.search(
            r'(<div\s+class="[^"]*\bpage-content\b[^"]*"[^>]*>)(.*?)(</div>)',
            skeleton,
            re.DOTALL | re.IGNORECASE,
        )
        if pc_match:
            open_tag = pc_match.group(1)
            inner = pc_match.group(2)
            close_tag = pc_match.group(3)
            # 如果内部不是 {{toc_items}}（含标签），强制替换
            if '{{toc_items}}' not in inner:
                new_inner = "\n{{toc_items}}\n"
                skeleton = skeleton[:pc_match.start()] + open_tag + new_inner + close_tag + skeleton[pc_match.end():]
        # 确保 title 有 .page-title 包裹
        if '{{title}}' in skeleton and '<div class="page-title">' not in skeleton:
            skeleton = skeleton.replace('{{title}}', '<div class="page-title">{{title}}</div>')
    elif ptype == "section":
        # section 页：chapter_tag 用 .page-title，title 用 <h1> 或 .section-title，subtitle 用 <p class="subtitle">
        if '{{chapter_tag}}' in skeleton and '<div class="page-title">' not in skeleton:
            skeleton = skeleton.replace('{{chapter_tag}}', '<div class="page-title">{{chapter_tag}}</div>')
        # 确保 title 有包裹
        if '{{title}}' in skeleton:
            if '<h1' not in skeleton and '<div class="page-title">' in skeleton:
                # title 在 page-title 之后，不需要额外包裹
                pass
            elif '<h1' not in skeleton:
                skeleton = skeleton.replace('{{title}}', '<h1 class="section-title">{{title}}</h1>')
        # 确保 subtitle 有包裹
        if '{{subtitle}}' in skeleton and '<p class="subtitle">' not in skeleton and '<p class="subtitle"' not in skeleton:
            skeleton = skeleton.replace('{{subtitle}}', '<p class="subtitle">{{subtitle}}</p>')
    elif ptype == "content":
        # content 页：title 用 .page-title，content 用 .page-content
        if "{{title}}" not in skeleton:
            page_title_pattern = (
                r'(<div\s+class="[^"]*\bpage-title\b[^"]*"[^>]*>)(.*?)(</div>)'
            )
            if re.search(page_title_pattern, skeleton, re.DOTALL | re.IGNORECASE):
                skeleton = re.sub(
                    page_title_pattern,
                    r"\1{{title}}\3",
                    skeleton,
                    count=1,
                    flags=re.DOTALL | re.IGNORECASE,
                )
            elif re.search(r"<h[12][^>]*>.*?</h[12]>", skeleton, re.DOTALL | re.IGNORECASE):
                skeleton = re.sub(
                    r"(<h[12][^>]*>)(.*?)(</h[12]>)",
                    r"\1{{title}}\3",
                    skeleton,
                    count=1,
                    flags=re.DOTALL | re.IGNORECASE,
                )
            else:
                skeleton = re.sub(
                    r'(<div\s+class="[^"]*\bslide\b[^"]*"[^>]*>)',
                    r'\1\n<div class="page-title">{{title}}</div>',
                    skeleton,
                    count=1,
                    flags=re.IGNORECASE,
                )
        if "{{content}}" not in skeleton:
            content_container_pattern = (
                r'(<div\s+class="[^"]*\b(?:page-content|content-body)\b[^"]*"[^>]*>)(.*?)(</div>)'
            )
            if re.search(content_container_pattern, skeleton, re.DOTALL | re.IGNORECASE):
                skeleton = re.sub(
                    content_container_pattern,
                    r"\1{{content}}\3",
                    skeleton,
                    count=1,
                    flags=re.DOTALL | re.IGNORECASE,
                )
            else:
                skeleton = re.sub(
                    r'(<div\s+class="[^"]*\bslide\b[^"]*"[^>]*>)',
                    r'\1\n<div class="page-content">{{content}}</div>',
                    skeleton,
                    count=1,
                    flags=re.IGNORECASE,
                )
        if "{{title}}" in skeleton and not re.search(
            r'<div\s+class="[^"]*\bpage-title\b[^"]*"',
            skeleton,
            re.IGNORECASE,
        ):
            skeleton = skeleton.replace('{{title}}', '<div class="page-title">{{title}}</div>')
        if "{{content}}" in skeleton and not re.search(
            r'<div\s+class="[^"]*\bpage-content\b[^"]*"',
            skeleton,
            re.IGNORECASE,
        ):
            skeleton = skeleton.replace('{{content}}', '<div class="page-content">{{content}}</div>')
    elif ptype == "ending":
        # ending 页：title 在 h1 中，message 在 p.ending-message 中，且在 .ending-content 内
        if '<div class="ending-content">' not in skeleton and '{{title}}' in skeleton:
            # 包裹 ending 内容
            ending_content_match = re.search(r'(<div class="ending-content">)(.*?)(</div>)', skeleton, re.DOTALL)
            if not ending_content_match:
                # 用 ending-content 包裹 h1 和 ending-message
                skeleton = re.sub(
                    r'(<h1[^>]*>.*?</h1>\s*<p[^>]*class="[^"]*\bending-message\b[^"]*>[^<]*</p>)',
                    r'<div class="ending-content">\1</div>',
                    skeleton,
                    flags=re.DOTALL | re.IGNORECASE,
                )
                # 如果还没包裹，直接构造
                if '<div class="ending-content">' not in skeleton:
                    skeleton = re.sub(
                        r'(<h1[^>]*>)({{title}})(</h1>)',
                        r'\1\2\3\n    <p class="ending-message">{{message}}</p>',
                        skeleton,
                    )
                    skeleton = re.sub(
                        r'(<p[^>]*class="[^"]*\bending-message\b[^>]*>)({{message}})(</p>)',
                        r'<div class="ending-content">\1\2\3</div>',
                        skeleton,
                    )
                    # 兜底
                    if '<div class="ending-content">' not in skeleton:
                        skeleton = re.sub(
                            r'(<p[^>]*>[^<]*{{message}}[^<]*</p>)',
                            r'<div class="ending-content">\1</div>',
                            skeleton,
                        )
    elif ptype in LAYOUT_PAGE_TYPES:
        if "{{title}}" not in skeleton:
            page_title_pattern = (
                r'(<div\s+class="[^"]*\bpage-title\b[^"]*"[^>]*>)(.*?)(</div>)'
            )
            if re.search(page_title_pattern, skeleton, re.DOTALL | re.IGNORECASE):
                skeleton = re.sub(
                    page_title_pattern,
                    r"\1{{title}}\3",
                    skeleton,
                    count=1,
                    flags=re.DOTALL | re.IGNORECASE,
                )
            else:
                skeleton = re.sub(
                    r'(<div\s+class="[^"]*\bslide\b[^"]*"[^>]*>)',
                    r'\1\n<div class="page-title">{{title}}</div>',
                    skeleton,
                    count=1,
                    flags=re.IGNORECASE,
                )

    return skeleton


def _check_navigation_structure(html: str) -> list[str]:
    """
    检查 HTML 的导航结构是否符合标准：
    - .nav-dots 必须是空容器（由 JS 动态生成）
    - 禁止在 .nav-dots 内硬编码导航点元素
    """
    errors = []

    # 检查 nav-dots 是否为空（允许只有空白）
    nav_dots_pattern = re.compile(
        r'<div[^>]+class="[^"]*\bnav-dots\b[^"]*"[^>]*>(.*?)</div>',
        re.DOTALL | re.IGNORECASE,
    )
    match = nav_dots_pattern.search(html)
    if match:
        inner = match.group(1).strip()
        # 检查是否包含任何 nav-dot 元素（排除只有空白的情况）
        if re.search(r'<button[^>]+class="[^"]*\bnav-dot\b', inner, re.IGNORECASE):
            errors.append(
                ".nav-dots 内硬编码了 <button class=\"nav-dot\">，"
                "导航点必须由 JS 动态生成，禁止在 HTML 中硬编码"
            )
        if re.search(r'<div[^>]+class="[^"]*\bnav-dot\b', inner, re.IGNORECASE):
            errors.append(
                ".nav-dots 内硬编码了 <div class=\"nav-dot\">，"
                "导航点必须由 JS 动态生成，禁止在 HTML 中硬编码"
            )

    # 检查外层容器结构
    if 'class="slides-wrapper"' not in html and 'id="slidesWrapper"' not in html:
        errors.append(
            "缺少 .slides-wrapper 外层容器，"
            "必须使用 .slides-wrapper + .slides-track 结构"
        )
    if 'class="slides-track"' not in html and 'id="slidesTrack"' not in html:
        errors.append(
            "缺少 .slides-track 容器，"
            "必须使用 .slides-wrapper + .slides-track 结构"
        )

    # 检查导航箭头
    arrow_pattern = re.compile(r'<button[^>]+class="[^"]*\bnav-arrow\b', re.IGNORECASE)
    if arrow_pattern.search(html):
        errors.append(
            "导航箭头使用了 <button> 元素，应使用 <div> 并绑定 onclick 属性"
        )

    return errors


def _extract_page_types(html: str) -> dict[str, dict[str, Any]]:
    """
    从 HTML 中提取每种 page_type 的 skeleton。

    策略：使用 BeautifulSoup 解析 HTML，
    找到 <div class="slide XX"> 区块（支持任意嵌套深度），
    将示例内容文字替换为占位符，保留装饰元素。
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("BeautifulSoup 未安装，回退到正则提取")
        return _extract_page_types_regex(html)

    VALID_TYPES = SUPPORTED_PAGE_TYPES
    PLACEHOLDER_MAP = PAGE_TYPE_PLACEHOLDERS

    soup = BeautifulSoup(html, "html.parser")
    result = {}

    for ptype in VALID_TYPES:
        div = soup.find("div", class_=lambda c: c and ptype in c.split())
        if not div:
            continue

        raw_skeleton = str(div)

        # ---- 内容净化阶段 ----
        # 使用 BeautifulSoup DOM 操作，而非正则，以正确处理任意深度嵌套
        if ptype == "content":
            ph_key = "{{content}}"
            ph_soup = BeautifulSoup(ph_key, "html.parser")
            sk_soup = BeautifulSoup(raw_skeleton, "html.parser")
            pc = sk_soup.find("div", class_=lambda c: c and "page-content" in c)
            if pc:
                for child in list(pc.children):
                    child.decompose()
                pc.append(ph_soup)
                raw_skeleton = str(sk_soup)
            for ph in PLACEHOLDER_MAP[ptype]:
                ph_double = f"{{{{{ph}}}}}"
                raw_skeleton = re.sub(
                    rf"(?i)\{{\{{\s*{re.escape(ph)}\s*\}}\}}",
                    ph_double,
                    raw_skeleton,
                )
        elif ptype == "toc":
            # toc 页：
            # 1. 把 page-content 内部替换为 {{toc_items}}（由渲染器生成真实目录）
            # 2. 删除 page-content 外部残留的 toc-item 元素（LLM 示例中的溢出内容）
            ph_key = "{{toc_items}}"
            ph_soup = BeautifulSoup(ph_key, "html.parser")
            sk_soup = BeautifulSoup(raw_skeleton, "html.parser")
            pc = sk_soup.find("div", class_=lambda c: c and "page-content" in c)
            if pc:
                for child in list(pc.children):
                    child.decompose()
                pc.append(ph_soup)
            # 删除 page-content 外部的 toc-item 元素
            for toc_el in sk_soup.find_all("div", class_=lambda c: c and "toc-item" in c):
                toc_el.decompose()
            raw_skeleton = str(sk_soup)
        else:
            for ph in PLACEHOLDER_MAP[ptype]:
                ph_double = f"{{{{{ph}}}}}"
                raw_skeleton = re.sub(
                    rf"(?i)\{{\{{\s*{re.escape(ph)}\s*\}}\}}",
                    ph_double,
                    raw_skeleton,
                )

        result[ptype] = {
            "skeleton": _normalize_skeleton(ptype, raw_skeleton),
            "placeholders": list(PLACEHOLDER_MAP[ptype]) + ["page_number"],
        }

    return result


def _replace_page_content_block(skeleton: str, placeholder: str) -> str:
    """用栈匹配算法找到 page-content div 的完整范围，清空内部为 placeholder。

    比正则的 .+? 更可靠，能正确处理任意深度嵌套。
    同时彻底清理 HTML 注释、装饰性 div/svg 元素。
    """
    pattern = re.compile(r"<div\s[^>]*class\s*=\s*['\"][^'\"]*\bpage-content\b[^'\"]*['\"][^>]*>", re.IGNORECASE)
    open_match = pattern.search(skeleton)
    if not open_match:
        return skeleton
    start = open_match.start()
    # 找开标签后的位置，从那里开始找闭合 div
    search_from = open_match.end()
    depth = 1
    i = search_from
    while i < len(skeleton) and depth > 0:
        if skeleton[i:i+5] == "<div" and (i == 0 or skeleton[i-1] not in ("'", '"', ">")):
            depth += 1
            i += 4
        elif skeleton[i:i+6] == "</div>":
            depth -= 1
            if depth == 0:
                end = i + 6
                inner = skeleton[open_match.end():i]
                # ---- 彻底净化：移除 HTML 注释 ----
                inner = re.sub(r"<!--.*?-->", "", inner, flags=re.DOTALL)
                # ---- 彻底净化：移除装饰性 div/svg/span 元素 ----
                # 移除含 style="position:absolute 的装饰 div（典型装饰模式）
                inner = re.sub(
                    r"<div\s[^>]*style\s*=\s*['\"][^'\"]*(?:position\s*:\s*absolute|opacity\s*:\s*0\.\d|font-size\s*:\s*\d+px|z-index\s*:\s*0)[^'\"]*['\"][^>]*>.*?</div>",
                    "",
                    inner,
                    flags=re.DOTALL | re.IGNORECASE,
                )
                # 移除纯装饰性的独立 div（只有背景色、圆角等装饰属性，无实质内容）
                inner = re.sub(
                    r"<div\s[^>]*>\s*</div>",
                    "",
                    inner,
                    flags=re.DOTALL | re.IGNORECASE,
                )
                # 移除 svg 装饰元素（通常用于装饰性波浪、形状等）
                inner = re.sub(r"<svg[^>]*>.*?</svg>", "", inner, flags=re.DOTALL | re.IGNORECASE)
                # 移除 emoji/spacer span
                inner = re.sub(
                    r"<span\s[^>]*>\s*(?:🌊|✨|🪼|✦|[\s\.\-~^]+)\s*</span>",
                    "",
                    inner,
                    flags=re.DOTALL | re.IGNORECASE,
                )
                # 清理残留空白，但保留换行结构
                inner = re.sub(r"\n{3,}", "\n", inner)
                inner_stripped = inner.strip()
                return skeleton[:open_match.end()] + "\n" + placeholder + "\n" + skeleton[i:]
    return skeleton


def _extract_page_types_regex(html: str) -> dict[str, dict[str, Any]]:
    """回退：使用正则提取（不支持嵌套 div）。"""
    VALID_TYPES = SUPPORTED_PAGE_TYPES
    PLACEHOLDER_MAP = PAGE_TYPE_PLACEHOLDERS
    PAGE_TYPE_CLASSES = {ptype: f"slide {ptype}" for ptype in VALID_TYPES}

    result = {}
    for ptype in VALID_TYPES:
        class_pat = re.escape(PAGE_TYPE_CLASSES[ptype])
        pattern = rf'<div\s+class="[^"]*?\b{class_pat}\b[^"]*?"[^>]*>(.*?)</div>'
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)

        if not match:
            pattern2 = rf'<div\s+class="[^"]*{class_pat}[^"]*"[^>]*>(.*?)</div>'
            match = re.search(pattern2, html, re.DOTALL | re.IGNORECASE)

        if not match:
            continue

        raw_skeleton = match.group(0)

        # ---- 内容净化阶段 ----
        # content: 用栈匹配找 page-content 的闭合 div，替换内部为占位符
        if ptype == "content":
            ph_key = "{{content}}"
            raw_skeleton = _replace_page_content_block(raw_skeleton, ph_key)
        elif ptype == "toc":
            # toc 页：
            # 1. 把 page-content 内部替换为 {{toc_items}}（由渲染器生成真实目录）
            # 2. 删除 page-content 外部残留的 toc-item 元素（LLM 示例中的溢出内容）
            ph_key = "{{toc_items}}"
            ph_soup = BeautifulSoup(ph_key, "html.parser")
            sk_soup = BeautifulSoup(raw_skeleton, "html.parser")
            pc = sk_soup.find("div", class_=lambda c: c and "page-content" in c)
            if pc:
                for child in list(pc.children):
                    child.decompose()
                pc.append(ph_soup)
            # 删除 page-content 外部的 toc-item 元素
            for toc_el in sk_soup.find_all("div", class_=lambda c: c and "toc-item" in c):
                toc_el.decompose()
            raw_skeleton = str(sk_soup)
        else:
            for ph in PLACEHOLDER_MAP[ptype]:
                ph_double = f"{{{{{ph}}}}}"
                raw_skeleton = re.sub(
                    rf"(?i)\{{\{{\s*{re.escape(ph)}\s*\}}\}}",
                    ph_double,
                    raw_skeleton,
                )

        result[ptype] = {
            "skeleton": _normalize_skeleton(ptype, raw_skeleton),
            "placeholders": list(PLACEHOLDER_MAP[ptype]) + ["page_number"],
        }

    return result


def _infer_theme_name(description: str) -> str:
    """从描述中提取主题名称作为 template_name（仅用于显示）。"""
    name = description.strip()
    name = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name[:20] or "未命名主题"


# ============================================================
# 提取器：从 LLM HTML 响应中提取模板定义
# ============================================================

def extract_template_from_response(response: str, user_description: str = "") -> dict[str, Any]:
    """
    从 LLM 的纯 HTML 输出中提取模板定义。

    提取步骤：
    1. 清理 markdown 代码块包裹
    2. 从 :root 提取 CSS 变量
    3. 从 <div class="slide XX"> 提取每种 page_type 的 skeleton
    4. 合成 template_id、template_name、viewport、tags
    """
    html = response.strip()
    html = re.sub(r"^```html\s*", "", html)
    html = re.sub(r"\s*```\s*$", "", html)

    if not html or "<html" not in html.lower():
        raise ValueError(f"LLM 响应不包含有效 HTML。响应前 300 字符: {response[:300]}")

    css_vars = _extract_css_variables(html)
    page_types = _extract_page_types(html)

    if not page_types:
        raise ValueError(
            "无法从 HTML 中提取到任何 page_type skeleton。"
            "请确保每个 slide 页面用 <div class=\"slide XX\"> 包裹，XX 为 page_type。"
        )

    missing_types = {"cover", "toc", "section", "content", "ending"} - set(page_types.keys())
    if missing_types:
        logger.warning(f"HTML 中缺少以下 page_type: {missing_types}，将使用占位符 skeleton")

    for ptype in missing_types:
        page_types[ptype] = {
            "skeleton": f'<div class="slide {ptype}"><div class="slide-content">{{{{title}}}}</div><div class="slide-footer"><span class="page-num">{{{{page_number}}}}</span></div></div>',
            "placeholders": ["title", "page_number"],
        }

    missing_layout_types = [
        ptype for ptype in LAYOUT_PAGE_TYPE_ORDER if ptype not in page_types
    ]
    for ptype in missing_layout_types:
        page_types[ptype] = {
            "skeleton": _fallback_layout_skeleton(ptype),
            "placeholders": _infer_placeholders(ptype),
        }

    # 重点校验：content 页的 {{title}} 必须在 {{content}} 之前
    content_skeleton = page_types.get("content", {}).get("skeleton", "")
    if content_skeleton:
        title_pos = content_skeleton.find("{{title}}")
        content_pos = content_skeleton.find("{{content}}")
        if title_pos != -1 and content_pos != -1 and title_pos > content_pos:
            raise ValueError(
                "content 页中 {{title}} 出现在 {{content}} 之后，"
                "违反了\"标题在上、内容在下\"的布局要求。"
                f"请确保 LLM 生成的 HTML 中标题在内容之上。"
            )
        # 同时检查 content 页必须包含 {{title}} 占位符
        if title_pos == -1:
            raise ValueError(
                "content 页缺少 {{title}} 占位符。"
                "内容页的标题必须使用 {{title}} 占位符，不能硬编码。"
            )
    # section 页的 title 也必须存在
    section_skeleton = page_types.get("section", {}).get("skeleton", "")
    if section_skeleton:
        if "{{title}}" not in section_skeleton:
            raise ValueError(
                "section 页缺少 {{title}} 占位符。"
                "章节标题必须使用 {{title}} 占位符，不能硬编码。"
            )

    # 导航结构检查
    nav_errors = _check_navigation_structure(html)
    if nav_errors:
        raise ValueError(
            "HTML 导航结构不符合标准规范：\n"
            + "\n".join(f"  - {e}" for e in nav_errors)
        )

    # slide 尺寸检查
    dim_errors = _validate_slide_dimensions(html)
    if dim_errors:
        raise ValueError(
            "HTML slide 尺寸 CSS 不符合标准规范：\n"
            + "\n".join(f"  - {e}" for e in dim_errors)
        )

    # 布局方式检查：禁止 flex column 布局
    layout_errors = _validate_layout_positioning(html)
    if layout_errors:
        raise ValueError(
            "HTML 布局方式不符合标准规范：\n"
            + "\n".join(f"  - {e}" for e in layout_errors)
        )

    # content/toc 区域清洁度检查（提前到提取阶段，拒绝污染 skeleton）
    # 注意：content 页必须完全空白；toc 页允许保留示例列表结构（供 CSS 样式参考）
    for ptype in ("content",):
        if ptype in page_types:
            sk = page_types[ptype]["skeleton"]
            clean_errors = _validate_content_cleanliness(sk, ptype)
            if clean_errors:
                raise ValueError(
                    f"HTML 中 {ptype} 页的骨架结构不符合规范：\n"
                    + "\n".join(f"  - {e}" for e in clean_errors)
                )

    raw_html = _clean_page_content_visual_styles(_clean_css_placeholders(html))
    if missing_layout_types:
        raw_html = _append_missing_layout_skeletons(raw_html, missing_layout_types)

    template_dict: dict[str, Any] = {
        "template_id": _make_template_id(user_description or "template"),
        "template_name": _infer_theme_name(user_description),
        "description": f"用户需求: {user_description}" if user_description else "",
        "version": "1.0.0",
        "css_variables": css_vars,
        "page_types": page_types,
        "viewport": {"width": 1280, "height": 720},
        "tags": _infer_tags(user_description),
        "is_default": False,
        "raw_html": raw_html,
    }

    return template_dict


def _make_template_id(_name: str) -> str:
    """用时间戳生成唯一 template_id。"""
    return f"gen_{int(time.time())}"


def _infer_tags(_description: str) -> list[str]:
    """不从描述推断标签，统一返回通用标签。"""
    return ["通用"]


def _infer_placeholders(ptype: str) -> list[str]:
    """根据 page_type 推断需要的占位符。"""
    base = list(PAGE_TYPE_PLACEHOLDERS.get(ptype, ("title",)))
    if "page_number" not in base:
        base.append("page_number")
    return base


def _fallback_layout_skeleton(ptype: str) -> str:
    placeholders = PAGE_TYPE_PLACEHOLDERS.get(ptype, ("title", "content"))
    body_parts = []
    for ph in placeholders:
        if ph == "title":
            continue
        body_parts.append(f'<div class="layout-slot layout-slot-{ph}">{{{{{ph}}}}}</div>')
    body_html = "\n    ".join(body_parts) or '<div class="layout-slot layout-slot-content">{{content}}</div>'
    return (
        f'<div class="slide {ptype}">\n'
        f'  <div class="page-title">{{{{title}}}}</div>\n'
        f'  <div class="page-content layout-{ptype}">\n'
        f'    {body_html}\n'
        f'  </div>\n'
        f'  <div class="slide-footer"><span class="page-num">{{{{page_number}}}}</span></div>\n'
        f'</div>'
    )


def _append_missing_layout_skeletons(html: str, missing_layout_types: list[str]) -> str:
    if not missing_layout_types:
        return html
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return html

    soup = BeautifulSoup(html, "html.parser")
    track = soup.find("div", class_=lambda c: c and "slides-track" in c.split())
    if not track:
        return html

    for ptype in missing_layout_types:
        skeleton_soup = BeautifulSoup(_fallback_layout_skeleton(ptype), "html.parser")
        slide = skeleton_soup.find("div", class_=lambda c: c and "slide" in c.split())
        if slide:
            track.append(slide)

    return str(soup)


# ============================================================
# 校验器
# ============================================================

REQUIRED_FIELDS = {
    "css_variables", "page_types", "viewport", "raw_html"
}

REQUIRED_PAGE_TYPES = {"cover", "toc", "section", "content", "ending"}

REQUIRED_CSS_KEYS = {
    "color-primary", "color-secondary", "color-background",
    "color-surface", "color-text", "color-card"
}


def _clean_css_placeholders(html: str) -> str:
    """清理 raw_html 中 CSS 块（<style>）里的 {{...}} 占位符，避免污染渲染产物。

    场景：LLM 有时会在 CSS ::before 伪元素的 content 属性中放置 {{content}} 提示文字，
    这会导致渲染后的 HTML 中出现未替换的占位符文本。
    """
    def _strip_style_placeholders(style_content: str) -> str:
        # 移除 CSS content 属性中含 {{...}} 的行
        cleaned = re.sub(r"content\s*:\s*['\"]?[^{]*\{\{[^}]+\}\}[^{]*['\"]?\s*;", ";", style_content)
        # 移除任何 {{...}} 残留模式
        cleaned = re.sub(r"\{\{[^}]+\}\}", "", cleaned)
        return cleaned

    return re.sub(
        r"(<style[^>]*>)(.*?)(</style>)",
        lambda m: m.group(1) + _strip_style_placeholders(m.group(2)) + m.group(3),
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )


def _clean_page_content_visual_styles(html: str) -> str:
    """移除 raw_html 中 .page-content 的所有视觉样式属性。

    .page-content 是内容占位容器，必须保持完全透明，不能有任何背景色、
    backdrop-filter、border、border-radius、box-shadow 等视觉装饰。
    否则会遮挡页面上装饰元素（波浪、生物、几何图形等）。
    """
    def _strip_visual_props(css_block: str) -> str:
        # 匹配 .page-content { ... } 块
        def _remove_page_content_styles(match):
            full_rule = match.group(0)
            brace_content = match.group(1)
            # 移除所有视觉样式属性
            props_to_remove = [
                r"background(?:\s*:\s*[^;]+;)",
                r"backdrop-filter(?:\s*:\s*[^;]+;)",
                r"border(?:\s*:\s*[^;]+;)",
                r"border-radius(?:\s*:\s*[^;]+;)",
                r"box-shadow(?:\s*:\s*[^;]+;)",
                r"padding(?:\s*:\s*[^;]+;)",
            ]
            for prop in props_to_remove:
                brace_content = re.sub(prop, "", brace_content, flags=re.IGNORECASE)
            # 保留 position / top / left / right / bottom / z-index / font-size / line-height / color
            return f".page-content {{{brace_content}}}"
        return re.sub(
            r"\.page-content\s*\{([^{}]*)\}",
            _remove_page_content_styles,
            css_block,
            flags=re.DOTALL | re.IGNORECASE,
        )
    return re.sub(
        r"(<style[^>]*>)(.*?)(</style>)",
        lambda m: m.group(1) + _strip_visual_props(m.group(2)) + m.group(3),
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )


def _validate_content_cleanliness(skeleton: str, ptype: str) -> list[str]:
    """
    验证 skeleton 的 content 区域是否干净（不含装饰/注释污染）。
    仅对 content/toc 类型进行检查。
    """
    errors = []
    if ptype not in ("content", "toc"):
        return errors

    ph_key = "{{content}}" if ptype == "content" else "{{toc_items}}"
    ph_pos = skeleton.find(ph_key)
    if ph_pos == -1:
        return errors

    # 找到 page-content div 的范围
    pattern = re.compile(
        r"<div\s[^>]*class\s*=\s*['\"][^'\"]*\bpage-content\b[^'\"]*['\"][^>]*>",
        re.IGNORECASE,
    )
    open_match = pattern.search(skeleton)
    if not open_match:
        return errors

    search_from = open_match.end()
    depth = 1
    i = search_from
    while i < len(skeleton) and depth > 0:
        if skeleton[i:i+5] == "<div" and (i == 0 or skeleton[i-1] not in ("'", '"', ">")):
            depth += 1
            i += 4
        elif skeleton[i:i+6] == "</div>":
            depth -= 1
            if depth == 0:
                inner = skeleton[open_match.end():i]
                # 移除 {{content}} 本身后检查剩余内容
                inner_without_ph = inner.replace(ph_key, "").strip()

                # 检查是否还有 HTML 注释
                if re.search(r"<!--.*?-->", inner_without_ph, re.DOTALL):
                    errors.append(
                        f"page_types.{ptype} 的 {{content}} 区域内含有 HTML 注释，"
                        "content 区域必须是纯净占位符，禁止有任何注释"
                    )
                # 检查是否有装饰性 div/svg 元素
                if re.search(r"<div\s[^>]*>", inner_without_ph) or re.search(
                    r"<svg\s[^>]*>", inner_without_ph, re.IGNORECASE
                ):
                    errors.append(
                        f"page_types.{ptype} 的 {{content}} 区域内含有 div/svg 元素，"
                        "content 区域必须是纯净占位符，禁止有任何子元素"
                    )
                break
        i += 1

    return errors


def _validate_slide_dimensions(raw_html: str) -> list[str]:
    """验证 slide 的尺寸 CSS 是否使用正确的 width/height（而非 min-width）。"""
    errors = []

    # 检查 .slide 的尺寸属性：必须用 width/height，不允许 min-width
    slide_dim_match = re.search(
        r"\.slide\s*\{([^}]+)\}",
        raw_html,
        re.DOTALL | re.IGNORECASE,
    )
    if slide_dim_match:
        dims = slide_dim_match.group(1)
        # 不允许 min-width
        if re.search(r"min-width\s*:", dims, re.IGNORECASE):
            errors.append(
                ".slide 的尺寸 CSS 中使用了 min-width 属性，"
                "请使用固定的 width: 1280px; height: 720px，禁止使用 min-width"
            )

    return errors


def _validate_layout_positioning(raw_html: str) -> list[str]:
    """验证 slide 是否使用了 absolute 绝对定位布局，而非 flex column 布局。"""
    errors = []

    # 检查 .slide 的主布局属性：不允许 flex-direction: column 作为 slide 主布局
    slide_match = re.search(
        r"\.slide\s*\{([^}]+)\}",
        raw_html,
        re.DOTALL | re.IGNORECASE,
    )
    if slide_match:
        slide_css = slide_match.group(1)
        # 检查是否有 display: flex 且 flex-direction: column（这是禁止的模式）
        has_flex = re.search(r"display\s*:\s*flex", slide_css, re.IGNORECASE)
        has_flex_col = re.search(r"flex-direction\s*:\s*column", slide_css, re.IGNORECASE)
        if has_flex and has_flex_col:
            errors.append(
                ".slide 的 CSS 使用了 `display: flex; flex-direction: column` 布局，"
                "这是禁止的。必须使用 `position: absolute` 绝对定位布局。"
            )

    return errors


def validate_template(template: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    校验模板配置的完整性。

    检查项：
    1. 必需字段存在
    2. viewport = 1280x720
    3. 5 种 page_type 全部存在
    4. 每种 page_type 的 skeleton 非空
    5. raw_html 非空
    6. 关键 CSS 变量已填写
    7. content 区域干净（无注释/装饰污染）
    8. slide 尺寸使用 width 而非 min-width
    """
    errors: list[str] = []

    for field in REQUIRED_FIELDS:
        if field not in template or not template[field]:
            errors.append(f"缺少或为空: {field}")

    vp = template.get("viewport", {})
    if vp.get("width") != 1280 or vp.get("height") != 720:
        errors.append(f"viewport 应为 1280x720，实际为 {vp.get('width')}x{vp.get('height')}")

    pt = template.get("page_types", {})
    for req_type in REQUIRED_PAGE_TYPES:
        if req_type not in pt:
            errors.append(f"缺少 page_type: {req_type}")

    for ptype, pconfig in pt.items():
        if not isinstance(pconfig, dict):
            errors.append(f"page_types.{ptype} 必须是对象")
            continue
        skeleton = pconfig.get("skeleton", "")
        if not skeleton or len(skeleton.strip()) < 10:
            errors.append(f"page_types.{ptype}.skeleton 为空或太短")

        placeholders = pconfig.get("placeholders", [])
        if "page_number" not in placeholders:
            pconfig["placeholders"] = list(placeholders) + ["page_number"]

        # ---- 新增：content/toc 区域清洁度检查 ----
        errors.extend(_validate_content_cleanliness(skeleton, ptype))

    css = template.get("css_variables", {})
    for key in REQUIRED_CSS_KEYS:
        val = css.get(key, "")
        if not val or not isinstance(val, str) or len(val) < 4:
            errors.append(f"CSS 变量 {key} 未填写或值不合法: {val!r}")

    # 重点：content 页 title 必须在 content 之前
    content_sk = pt.get("content", {}).get("skeleton", "")
    if content_sk:
        title_pos = content_sk.find("{{title}}")
        content_pos = content_sk.find("{{content}}")
        if title_pos != -1 and content_pos != -1 and title_pos > content_pos:
            errors.append("content 页中 {{title}} 出现在 {{content}} 之后，违反标题在上布局")
        if title_pos == -1:
            errors.append("content 页缺少 {{title}} 占位符")

    # section 页 title 不能硬编码
    section_sk = pt.get("section", {}).get("skeleton", "")
    if section_sk and "{{title}}" not in section_sk:
        errors.append("section 页缺少 {{title}} 占位符")

    # 所有 page_type 的 skeleton 必须包含 slide-footer
    for ptype, pconfig in pt.items():
        sk = pconfig.get("skeleton", "")
        if sk and "slide-footer" not in sk:
            errors.append(f"page_types.{ptype} 的 skeleton 缺少 slide-footer 结构")

    # 导航结构检查
    raw_html = template.get("raw_html", "")
    if raw_html:
        nav_errors = _check_navigation_structure(raw_html)
        errors.extend(nav_errors)
        # ---- 新增：slide 尺寸 CSS 检查 ----
        dim_errors = _validate_slide_dimensions(raw_html)
        errors.extend(dim_errors)

        # ---- 新增：布局方式检查 ----
        layout_errors = _validate_layout_positioning(raw_html)
        errors.extend(layout_errors)

    return len(errors) == 0, errors


# ============================================================
# 核心生成器
# ============================================================

def _truncate_text(value: str, max_chars: int = 12000) -> str:
    if len(value) <= max_chars:
        return value
    head = int(max_chars * 0.65)
    tail = max_chars - head
    return (
        value[:head]
        + "\n\n[... 中间内容已截断，保留首尾用于模板修改上下文 ...]\n\n"
        + value[-tail:]
    )


def _compact_current_template(current_template: dict[str, Any] | None) -> dict[str, Any]:
    if not current_template:
        return {}

    compact = {
        "template_id": current_template.get("template_id"),
        "template_name": current_template.get("template_name"),
        "description": current_template.get("description"),
        "css_variables": current_template.get("css_variables", {}),
        "page_types": current_template.get("page_types", {}),
        "viewport": current_template.get("viewport"),
        "tags": current_template.get("tags", []),
    }
    raw_html = current_template.get("raw_html") or ""
    if raw_html:
        compact["raw_html"] = _truncate_text(str(raw_html))
    return compact


def _build_template_user_prompt(
    user_description: str,
    *,
    conversation_context: str = "",
    current_template: dict[str, Any] | None = None,
) -> str:
    parts = []
    if conversation_context:
        parts.append("## 对话历史\n\n" + _truncate_text(conversation_context, 6000))

    compact_template = _compact_current_template(current_template)
    if compact_template:
        parts.append(
            "## 当前模板配置\n\n"
            "用户可能是在这个模板基础上继续修改。若用户表达的是调整、继续、变更、优化，"
            "请保留当前模板的核心结构和主题，只按最新需求修改。\n\n"
            "```json\n"
            + json.dumps(compact_template, ensure_ascii=False, indent=2)
            + "\n```"
        )

    parts.append("## 用户最新需求\n\n" + user_description)
    return "\n\n".join(parts)


class TemplateGenerator:
    """
    根据用户需求生成 PPT 模板的 LLM 服务。

    流程：
    1. 发送 HTML 输出 prompt
    2. 从 HTML 直接提取模板定义（CSS 变量、skeleton、raw_html）
    3. 校验模板结构
    4. 返回模板字典
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client or default_llm_client()

    async def generate(
        self,
        user_description: str,
        *,
        conversation_context: str = "",
        current_template: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        user_prompt = (
            _build_template_user_prompt(
                user_description,
                conversation_context=conversation_context,
                current_template=current_template,
            )
            + "\n\n请只输出 HTML 代码块，不要有任何解释文字。"
        )

        logger.info(f"[TemplateGenerator] 调用 LLM 生成模板，描述: {user_description[:50]}")

        MAX_RETRIES = 3
        last_error = ""
        last_response = ""

        for attempt in range(MAX_RETRIES):
            if attempt > 0:
                retry_prompt = user_prompt + (
                    "\n\n## 重试提示\n"
                    "上一次生成存在以下问题之一：\n"
                    "1. 内容页缺少 `{{title}}` 占位符，或章节页标题硬编码了文字\n"
                    "2. `.nav-dots` 内硬编码了导航点元素（应为空，由 JS 动态生成）\n"
                    "3. 缺少 `.slides-wrapper` + `.slides-track` 外层结构\n"
                    "4. 导航箭头使用了 `<button>` 而非 `<div onclick=...>`\n"
                    "5. `.page-content` 内部填充了装饰性 div/svg/注释（必须完全空白，只有 {{content}}）\n"
                    "6. `.slide` CSS 使用了 `min-width` 而非固定的 `width: 1280px; height: 720px`\n"
                    "**再次强调**（违反会被系统拒绝）：\n"
                    "- `{{title}}` 和 `{{content}}` 是内容页的**两个不同占位符**，必须同时存在且 `{{title}}` 在前\n"
                    "- 章节页的 `{{title}}` 也必须存在，不可省略\n"
                    "- `.page-content` 内部必须**完全空白**，只能有 `{{content}}` 这一个占位符，禁止放任何装饰元素、注释、svg、div\n"
                    "- `.nav-dots` 容器必须留空，导航点由 JS 动态生成\n"
                    "- `.slide` 必须用固定的 `width: 1280px; height: 720px`，禁止 `min-width`\n"
                    "- 布局必须用 absolute 绝对定位，禁止 flex column 布局\n"
                    "- 页面切换必须用 `transform: translateX()` 滑动，不许用 opacity 切换"
                )
                logger.info(f"[TemplateGenerator] 重试第 {attempt + 1} 次")
                response = await self.llm.complete(TEMPLATE_GENERATION_SYSTEM_PROMPT, retry_prompt)
            else:
                response = await self.llm.complete(TEMPLATE_GENERATION_SYSTEM_PROMPT, user_prompt)

            last_response = response

            try:
                parsed = extract_template_from_response(response, user_description)
                is_valid, errors = validate_template(parsed)

                if is_valid:
                    return {
                        "success": True,
                        "response": {"html": response},
                        "parsed": parsed,
                        "validation": (is_valid, errors),
                        "model": getattr(self.llm, "_model", "unknown"),
                    }
                else:
                    last_error = "; ".join(errors)
                    logger.warning(f"[TemplateGenerator] 第 {attempt + 1} 次尝试校验失败: {last_error}")

            except ValueError as e:
                last_error = str(e)
                logger.warning(f"[TemplateGenerator] 第 {attempt + 1} 次尝试提取失败: {last_error}")

            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(1)

        # 所有重试都失败
        logger.error(f"[TemplateGenerator] 模板生成失败（已重试 {MAX_RETRIES} 次）: {last_error}")
        return {
            "success": False,
            "response": {"html": last_response},
            "parsed": None,
            "validation": (False, [f"重试 {MAX_RETRIES} 次后失败: {last_error}"]),
            "model": getattr(self.llm, "_model", "unknown"),
        }

    def generate_sync(self, user_description: str) -> dict[str, Any]:
        """同步包装器。"""
        return asyncio.run(self.generate(user_description))


# ============================================================
# Flask API 路由（保留，兼容现有系统）
# ============================================================

def _extract_last_user_message(messages: list[dict[str, Any]]) -> tuple[str, int]:
    for idx in range(len(messages) - 1, -1, -1):
        msg = messages[idx]
        if msg.get("role") == "user":
            return str(msg.get("content", "")), idx
    return "", -1


def _build_conversation_context(messages: list[dict[str, Any]], last_user_idx: int) -> str:
    context_lines = []
    for msg in messages[:last_user_idx]:
        role = msg.get("role")
        if role not in {"user", "assistant"}:
            continue
        content = str(msg.get("content", "")).strip()
        if not content:
            continue
        label = "用户" if role == "user" else "AI"
        context_lines.append(f"{label}: {content}")
    return "\n\n".join(context_lines[-8:])


def register_template_api_routes(app):
    """将模板生成 API 注册到 Flask app。"""

    @app.route("/api/llm/chat", methods=["POST"])
    def llm_chat():
        from flask import request, jsonify

        try:
            data = request.get_json() or {}
            messages = data.get("messages", [])
            mode = data.get("mode", "general")
            current_template = data.get("current_template") or {}

            last_user_msg, last_user_idx = _extract_last_user_message(messages)

            if not last_user_msg:
                return jsonify({"error": "未找到用户消息"}), 400

            if mode == "template":
                conversation_context = _build_conversation_context(messages, last_user_idx)
                generator = TemplateGenerator()
                result = asyncio.run(
                    generator.generate(
                        last_user_msg,
                        conversation_context=conversation_context,
                        current_template=current_template,
                    )
                )
                return jsonify({
                    "success": result["success"],
                    "response": result["response"],
                    "parsed": result["parsed"],
                    "validation": {
                        "valid": result["validation"][0],
                        "errors": result["validation"][1],
                    },
                    "model": result["model"],
                })
            else:
                llm = default_llm_client()
                response = asyncio.run(
                    llm.complete(
                        "你是一个有帮助的助手，请用中文回答用户的问题。",
                        last_user_msg,
                    )
                )
                return jsonify({
                    "success": True,
                    "response": response,
                    "model": getattr(llm, "_model", "unknown"),
                })

        except Exception as e:
            logger.error(f"LLM chat error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    return app


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="PPT 模板生成器（LLM 驱动，只输出 HTML）")
    parser.add_argument("description", nargs="?", default=None, help="模板需求描述")
    parser.add_argument("--validate", action="store_true", help="仅验证现有 JSON 文件")
    parser.add_argument("--json-file", type=str, help="指定 JSON 文件路径进行验证")

    args = parser.parse_args()

    if args.validate and args.json_file:
        with open(args.json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        is_valid, errors = validate_template(data)
        print(f"\n验证结果: {'通过' if is_valid else '失败'}")
        if errors:
            for err in errors:
                print(f"  - {err}")
        else:
            print("  无错误。")
        sys.exit(0 if is_valid else 1)

    if args.validate:
        print("请使用 --json-file 指定要验证的 JSON 文件。")
        sys.exit(1)

    desc = args.description
    if not desc:
        print("请输入你想要的模板风格描述（输入后回车）：")
        desc = input().strip()

    if not desc:
        print("描述不能为空。")
        sys.exit(1)

    print(f"\n正在生成模板: {desc[:50]}{'...' if len(desc) > 50 else ''}")
    print("-" * 40)

    try:
        generator = TemplateGenerator()
        result = generator.generate_sync(desc)
    except ValueError as e:
        print(f"\n生成失败: {e}")
        sys.exit(1)

    print(f"\n模型: {result['model']}")
    print(f"成功: {result['success']}")

    is_valid, errors = result["validation"]
    print(f"校验: {'通过' if is_valid else '失败'}")
    for err in errors:
        print(f"  警告: {err}")

    if result["success"] and result["parsed"]:
        tpl = result["parsed"]
        print(f"\n生成结果:")
        print(f"  模板ID: {tpl.get('template_id')}")
        print(f"  模板名: {tpl.get('template_name')}")
        print(f"  描述:   {tpl.get('description', '')[:80]}")
        print(f"  标签:   {', '.join(tpl.get('tags', []))}")
        print(f"  配色:   {len(tpl.get('css_variables', {}))} 个变量")
        print(f"  页面类型: {', '.join(tpl.get('page_types', {}).keys())}")

        output_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates", "data", "user_generated"
        )
        os.makedirs(output_dir, exist_ok=True)
        tpl_id = tpl.get("template_id", f"gen_{int(time.time())}")
        output_path = os.path.join(output_dir, f"{tpl_id}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(tpl, f, ensure_ascii=False, indent=2)
        print(f"\n已保存到: {output_path}")

        print(f"\n--- JSON 模板（前 500 字符）---")
        print(json.dumps(tpl, ensure_ascii=False, indent=2)[:500])
        if len(json.dumps(tpl)) > 500:
            print("... (已截断)")
    else:
        print(f"\n生成失败。")
        sys.exit(1)
