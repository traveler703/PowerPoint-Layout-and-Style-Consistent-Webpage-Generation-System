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


# ============================================================
# Prompt：只输出 HTML
# ============================================================

TEMPLATE_GENERATION_SYSTEM_PROMPT = """你是一位极具创意的前端设计师。请为 PPT 演示系统生成一个主题模板。

## 输出要求

只输出一个 HTML 代码块（```html），不要有任何解释文字。

HTML 要求：
- 完整、可直接运行的 HTML 文件，包含 5 个 slide 页面示例（封面、目录、章节、内容、结尾各一页）
- 每个页面用 `<div class="slide [page_type]">` 包裹，page_type 取值为：cover、toc、section、content、ending
- 页脚固定结构：`<div class="slide-footer"><span class="page-num">页码</span></div>`
- `:root` 中定义所有 CSS 变量（color-*、font-*）
- 导航 UI（nav-dots、nav-arrows、page-indicator）
- **关键占位符**：`{{SLIDES_CONTENT}}`（在 .slides-track 内）和 `{{TOTAL_PAGES}}`（在 JS 和 page-indicator 中）
- slide 尺寸 1280×720px，字体使用真实 Google Fonts
- 页面示例内容由你自由创意设计（主题由用户描述指定）

## 每种 page_type 的占位符要求（必须严格遵守）

### cover 封面页
```html
<div class="slide cover">
  <h1>{{title}}</h1>
  <div class="subtitle">{{subtitle}}</div>
  <div class="date-badge">{{date_badge}}</div>
</div>
```

### toc 目录页
```html
<div class="slide toc">
  <div class="page-title">{{title}}</div>
  <div class="toc-list">{{toc_items}}</div>
</div>
```

### section 章节页（重点：chapter_tag 和 title 是两个不同的占位符）
```html
<div class="slide section">
  <div class="chapter-tag">{{chapter_tag}}</div>
  <h1>{{title}}</h1>
  <p class="subtitle">{{subtitle}}</p>
</div>
```
**注意**：`{{chapter_tag}}`（如"第一章"）和 `{{title}}`（如"森林探险"）是**两个不同的占位符**，不可省略 `{{title}}`。

### content 内容页（重点要求）
```html
<div class="slide content">
  <div class="page-title">{{title}}</div>
  <div class="page-content">{{content}}</div>
</div>
```
- **必须有 `{{title}}` 且在 `{{content}}` 之上**，两者缺一不可

### ending 结尾页
```html
<div class="slide ending">
  <h1>{{title}}</h1>
  <p class="ending-message">{{message}}</p>
</div>
```

## 重要约束（必须遵守）

1. **每种 page_type 都必须生成示例页面**：cover、toc、section、content、ending
2. **占位符使用双花括号**：`{{title}}`、`{{subtitle}}`、`{{date_badge}}`、`{{chapter_tag}}`、`{{content}}`、`{{toc_items}}`、`{{message}}`
3. **color-* 和 font-* CSS 变量必须全部填写**，不得为空
4. **页面中要有装饰元素**（emoji、几何图形、渐变等），体现主题特色

现在开始生成！"""


# ============================================================
# 从 HTML 提取模板信息的核心逻辑
# ============================================================

def _extract_css_variables(html: str) -> dict[str, str]:
    """从 HTML 的 :root 中提取 CSS 变量。"""
    vars_map = {
        "color-primary":      (r"--color-primary\s*:\s*([^;]+);",      "#2d5a27"),
        "color-secondary":    (r"--color-secondary\s*:\s*([^;]+);",    "#8B6914"),
        "color-background":  (r"--color-background\s*:\s*([^;]+);",  "#ffffff"),
        "color-surface":     (r"--color-surface\s*:\s*([^;]+);",     "#f5f5f5"),
        "color-text":        (r"--color-text\s*:\s*([^;]+);",        "#1a1a1a"),
        "color-card":        (r"--color-card\s*:\s*([^;]+);",        "#ffffff"),
        "color-text-muted":  (r"--color-text-muted\s*:\s*([^;]+);",  "#888888"),
        "color-accent":      (r"--color-accent\s*:\s*([^;]+);",      "#4CAF50"),
        "font-body":         (r"--font-body\s*:\s*([^;]+);",         "serif"),
        "font-heading":      (r"--font-heading\s*:\s*([^;]+);",     "sans-serif"),
    }
    result = {}
    for key, (pattern, fallback) in vars_map.items():
        m = re.search(pattern, html, re.IGNORECASE)
        val = m.group(1).strip() if m else fallback
        if val:
            result[key] = val
    return result


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

    VALID_TYPES = {"cover", "toc", "section", "content", "ending"}
    PLACEHOLDER_MAP = {
        "cover":    ("title", "subtitle", "date_badge"),
        "toc":      ("title", "toc_items"),
        "section":  ("chapter_tag", "title", "subtitle"),
        "content":  ("title", "content"),
        "ending":   ("title", "message"),
    }

    soup = BeautifulSoup(html, "html.parser")
    result = {}

    for ptype in VALID_TYPES:
        div = soup.find("div", class_=lambda c: c and ptype in c.split())
        if not div:
            continue

        raw_skeleton = str(div)

        for ph in PLACEHOLDER_MAP[ptype]:
            ph_double = f"{{{{{ph}}}}}"
            raw_skeleton = re.sub(
                rf"(?i)\{{\{{\s*{re.escape(ph)}\s*\}}\}}",
                ph_double,
                raw_skeleton,
            )

        result[ptype] = {
            "skeleton": raw_skeleton,
            "placeholders": list(PLACEHOLDER_MAP[ptype]) + ["page_number"],
        }

    return result


def _extract_page_types_regex(html: str) -> dict[str, dict[str, Any]]:
    """回退：使用正则提取（不支持嵌套 div）。"""
    VALID_TYPES = {"cover", "toc", "section", "content", "ending"}
    PLACEHOLDER_MAP = {
        "cover":    ("title", "subtitle", "date_badge"),
        "toc":      ("title", "toc_items"),
        "section":  ("chapter_tag", "title", "subtitle"),
        "content":  ("title", "content"),
        "ending":   ("title", "message"),
    }
    PAGE_TYPE_CLASSES = {
        "cover":    "slide cover",
        "toc":      "slide toc",
        "section":  "slide section",
        "content":  "slide content",
        "ending":   "slide ending",
    }

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

        for ph in PLACEHOLDER_MAP[ptype]:
            ph_double = f"{{{{{ph}}}}}"
            raw_skeleton = re.sub(
                rf"(?i)\{{\{{\s*{re.escape(ph)}\s*\}}\}}",
                ph_double,
                raw_skeleton,
            )

        result[ptype] = {
            "skeleton": raw_skeleton,
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
            "skeleton": f'<div class="slide {ptype}"><div class="slide-content">{{{{title}}}}</div></div>',
            "placeholders": ["title"],
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
        "raw_html": html,
    }

    return template_dict


def _make_template_id(_name: str) -> str:
    """用时间戳生成唯一 template_id。"""
    return f"gen_{int(time.time())}"


def _infer_tags(_description: str) -> list[str]:
    """不从描述推断标签，统一返回通用标签。"""
    return ["通用"]


def _infer_placeholders(ptype: str) -> list[str]:
    """根据 page_type 推断需要的占位符（仅保留 5 种标准类型）。"""
    mapping = {
        "cover":    ["title", "subtitle", "date_badge"],
        "toc":      ["title", "toc_items"],
        "section":  ["chapter_tag", "title", "subtitle"],
        "content":  ["title", "content"],
        "ending":   ["title", "message"],
    }
    base = mapping.get(ptype, ["title"])
    if "page_number" not in base:
        base.append("page_number")
    return base


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

    return len(errors) == 0, errors


# ============================================================
# 核心生成器
# ============================================================

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

    async def generate(self, user_description: str) -> dict[str, Any]:
        prompt = (
            TEMPLATE_GENERATION_SYSTEM_PROMPT
            + f"\n\n## 用户需求\n\n{user_description}\n\n"
            + "请只输出 HTML 代码块，不要有任何解释文字。"
        )

        logger.info(f"[TemplateGenerator] 调用 LLM 生成模板，描述: {user_description[:50]}")

        MAX_RETRIES = 3
        last_error = ""
        last_response = ""

        for attempt in range(MAX_RETRIES):
            if attempt > 0:
                retry_prompt = prompt + (
                    "\n\n## 重试提示\n"
                    "上一次生成的内容页缺少 `{{title}}` 占位符，或章节页标题硬编码了文字。\n"
                    "**再次强调**：`{{title}}` 和 `{{content}}` 是内容页的**两个不同占位符**，"
                    "必须同时存在且 `{{title}}` 在前。章节页的 `{{title}}` 也必须存在，不可省略。"
                )
                logger.info(f"[TemplateGenerator] 重试第 {attempt + 1} 次")
                response = await self.llm.complete(retry_prompt, "")
            else:
                response = await self.llm.complete(prompt, "")

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

def register_template_api_routes(app):
    """将模板生成 API 注册到 Flask app。"""

    @app.route("/api/llm/chat", methods=["POST"])
    def llm_chat():
        from flask import request, jsonify

        try:
            data = request.get_json() or {}
            messages = data.get("messages", [])
            mode = data.get("mode", "general")

            last_user_msg = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    last_user_msg = msg.get("content", "")
                    break

            if not last_user_msg:
                return jsonify({"error": "未找到用户消息"}), 400

            if mode == "template":
                generator = TemplateGenerator()
                result = asyncio.run(generator.generate(last_user_msg))
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
