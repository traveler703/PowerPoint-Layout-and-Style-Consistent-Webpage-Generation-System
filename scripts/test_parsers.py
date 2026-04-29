"""
Part 1 集成测试脚本
测试内容输入模块（parsers/）和结构化可复用框架的完整性。

运行方式：
    source .venv/bin/activate
    python scripts/test_parsers.py
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ═══════════════════════════════════════════
# 测试 1：统一 Schema 模型
# ═══════════════════════════════════════════

def test_schema():
    """测试 DocumentParseResult 模型的创建和序列化"""
    from parsers.base import (
        DocumentParseResult, DocumentMetadata, PageContent,
        HeadingItem, BulletPoint, TableContent, ImageContent,
        SourceFormat,
    )

    # 构造测试数据
    page = PageContent(
        page_index=0,
        title="测试页面",
        headings=[HeadingItem(level=2, text="子标题A")],
        paragraphs=["这是一个测试段落。"],
        bullets=[BulletPoint(title="要点1", description="描述1")],
        tables=[TableContent(headers=["名称", "值"], rows=[["A", "1"], ["B", "2"]])],
        images=[ImageContent(url="https://example.com/img.png", alt="示例图")],
        has_table=True,
        raw_text="测试原始文本",
    )

    doc = DocumentParseResult(
        metadata=DocumentMetadata(
            title="测试文档",
            source_format=SourceFormat.MARKDOWN,
            source_filename="test.md",
            page_count=1,
            total_chars=100,
        ),
        pages=[page],
    )

    # JSON 序列化
    json_str = doc.to_json()
    assert len(json_str) > 0, "JSON 序列化失败"

    # JSON 反序列化
    restored = DocumentParseResult.from_json(json_str)
    assert restored.metadata.title == "测试文档"
    assert len(restored.pages) == 1
    assert restored.pages[0].title == "测试页面"
    assert restored.pages[0].has_table is True

    # 属性计算
    assert page.text_length > 0
    assert page.effective_bullet_count == 1

    print("✅ 测试 1 通过：Schema 模型创建和序列化正确")


# ═══════════════════════════════════════════
# 测试 2：Markdown 解析器
# ═══════════════════════════════════════════

def test_markdown_parser():
    """测试 Markdown 解析器的各种结构提取"""
    from parsers.markdown_parser import MarkdownParser

    md_text = """# 项目季度报告

## 背景与目标
本项目旨在实现自动化文档处理。
- 目标A：支持多格式解析
- 目标B：提高效率50%

---

## 数据分析
| 指标 | Q1 | Q2 |
|------|----|----|
| 用户数 | 1000 | 2500 |
| 收入 | 50万 | 120万 |

核心发现：用户增长超预期。

---

## 下一步计划
![规划图](https://example.com/plan.png)
- 完善解析模块
- 实现版式选型
- 优化生成质量
"""

    parser = MarkdownParser()
    result = parser.parse(md_text, filename="report.md")

    # 验证基本结构
    assert result.metadata.title == "项目季度报告"
    assert result.metadata.source_format.value == "markdown"
    assert result.metadata.page_count == 3

    # 验证第1页
    p1 = result.pages[0]
    assert p1.title == "项目季度报告"
    assert len(p1.bullets) == 2
    assert p1.bullets[0].title == "目标A"
    assert p1.bullets[0].description == "支持多格式解析"

    # 验证第2页（表格）
    p2 = result.pages[1]
    assert p2.has_table is True
    assert len(p2.tables) == 1
    assert p2.tables[0].headers == ["指标", "Q1", "Q2"]
    assert len(p2.tables[0].rows) == 2

    # 验证第3页（图片）
    p3 = result.pages[2]
    assert len(p3.images) == 1
    assert "example.com/plan.png" in p3.images[0].url
    assert len(p3.bullets) == 3

    print("✅ 测试 2 通过：Markdown 解析器正确提取标题/列表/表格/图片")


# ═══════════════════════════════════════════
# 测试 3：格式检测
# ═══════════════════════════════════════════

def test_format_detection():
    """测试文件格式检测"""
    from parsers.base import BaseDocumentParser, SourceFormat

    cases = {
        "report.md": SourceFormat.MARKDOWN,
        "doc.markdown": SourceFormat.MARKDOWN,
        "notes.txt": SourceFormat.TXT,
        "paper.pdf": SourceFormat.PDF,
        "report.docx": SourceFormat.DOCX,
        "slides.pptx": SourceFormat.PPTX,
        "unknown.xyz": SourceFormat.TXT,  # 默认
    }

    for filename, expected in cases.items():
        result = BaseDocumentParser.detect_format(filename)
        assert result == expected, f"格式检测错误: {filename} -> {result}, 期望 {expected}"

    print("✅ 测试 3 通过：文件格式检测正确")


# ═══════════════════════════════════════════
# 测试 4：Flask API 端点
# ═══════════════════════════════════════════

def test_upload_api():
    """测试 /api/upload-document 端点"""
    from io import BytesIO
    from app import app

    test_content = """# API测试文档

## 第一节
- 要点A
- 要点B：这是详细描述

---

## 第二节
| 列1 | 列2 |
|-----|-----|
| a   | b   |
""".encode('utf-8')

    with app.test_client() as client:
        # 正常上传
        data = {'file': (BytesIO(test_content), 'api_test.md')}
        response = client.post('/api/upload-document', data=data, content_type='multipart/form-data')
        result = response.get_json()

        assert response.status_code == 200
        assert result['success'] is True
        assert result['meta']['page_count'] == 2
        assert result['meta']['format'] == 'markdown'

        # 验证解析内容
        pages = result['result']['pages']
        assert pages[0]['title'] == "API测试文档"
        assert len(pages[0]['bullets']) == 2
        assert pages[1]['has_table'] is True

        # 测试空文件
        data = {'file': (BytesIO(b''), 'empty.md')}
        response = client.post('/api/upload-document', data=data, content_type='multipart/form-data')
        assert response.status_code == 400

        # 测试无文件
        response = client.post('/api/upload-document', data={}, content_type='multipart/form-data')
        assert response.status_code == 400

        # 测试 /api/supported-formats
        response = client.get('/api/supported-formats')
        result = response.get_json()
        assert result['success'] is True
        extensions = [f['extension'] for f in result['formats']]
        assert '.pdf' in extensions
        assert '.docx' in extensions
        assert '.pptx' in extensions

    print("✅ 测试 4 通过：Flask API 端点工作正常")


# ═══════════════════════════════════════════
# 测试 5：框架数据完整性
# ═══════════════════════════════════════════

def test_framework_data():
    """测试框架数据文件的完整性和格式"""
    data_dir = Path(__file__).resolve().parent.parent / "framework" / "data"

    # layouts.json
    layouts_file = data_dir / "layouts.json"
    assert layouts_file.exists(), "layouts.json 不存在"
    layouts = json.loads(layouts_file.read_text(encoding="utf-8"))
    assert len(layouts["layouts"]) == 12, f"期望 12 种版式，实际 {len(layouts['layouts'])}"

    layout_ids = [l["id"] for l in layouts["layouts"]]
    assert "title-only" in layout_ids
    assert "timeline" in layout_ids
    assert "comparison" in layout_ids
    assert "statistics" in layout_ids
    assert "quote-highlight" in layout_ids

    # components.json
    components_file = data_dir / "components.json"
    assert components_file.exists(), "components.json 不存在"
    components = json.loads(components_file.read_text(encoding="utf-8"))
    assert len(components["components"]) >= 11
    assert "title" in components["components"]
    assert "statistic" in components["components"]
    assert "timeline_item" in components["components"]
    assert "spacing_rules" in components
    assert "responsive_breakpoints" in components

    # themes.json
    themes_file = data_dir / "themes.json"
    assert themes_file.exists(), "themes.json 不存在"
    themes = json.loads(themes_file.read_text(encoding="utf-8"))
    assert len(themes["themes"]) == 6, f"期望 6 个主题，实际 {len(themes['themes'])}"
    assert "tech_dark" in themes["themes"]
    assert "nature_green" in themes["themes"]
    assert "minimal_white" in themes["themes"]

    # 验证每个主题结构
    for theme_id, theme in themes["themes"].items():
        assert "colors" in theme, f"主题 {theme_id} 缺少 colors"
        assert "typography" in theme, f"主题 {theme_id} 缺少 typography"
        assert "primary" in theme["colors"], f"主题 {theme_id} 缺少 primary 颜色"

    print("✅ 测试 5 通过：框架数据文件完整且格式正确")


# ═══════════════════════════════════════════
# 测试 6：JSON 文件保存和加载
# ═══════════════════════════════════════════

def test_json_save_load():
    """测试解析结果保存为 JSON 文件并重新加载"""
    import tempfile
    from parsers.markdown_parser import MarkdownParser
    from parsers.base import DocumentParseResult

    md_text = """# 保存测试

## 内容
- 测试要点1
- 测试要点2
"""

    parser = MarkdownParser()
    result = parser.parse(md_text, filename="save_test.md")

    # 保存到临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        tmp_path = f.name

    result.save_json(tmp_path)

    # 验证文件存在且内容有效
    assert Path(tmp_path).exists()
    content = Path(tmp_path).read_text(encoding='utf-8')
    data = json.loads(content)
    assert data['metadata']['title'] == "保存测试"
    assert len(data['pages']) == 1

    # 重新加载
    loaded = DocumentParseResult.load_json(tmp_path)
    assert loaded.metadata.title == "保存测试"
    assert loaded.pages[0].bullets[0].title == "测试要点1"

    # 清理
    Path(tmp_path).unlink()

    print("✅ 测试 6 通过：JSON 保存和加载功能正确")


# ═══════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("Part 1 集成测试：内容输入模块 & 结构化可复用框架")
    print("=" * 60)
    print()

    tests = [
        test_schema,
        test_markdown_parser,
        test_format_detection,
        test_upload_api,
        test_framework_data,
        test_json_save_load,
    ]

    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"❌ {test_fn.__name__} 失败: {e}")
            import traceback
            traceback.print_exc()
            print()

    print()
    print("=" * 60)
    total = passed + failed
    print(f"结果: {passed}/{total} 通过", end="")
    if failed:
        print(f", {failed} 失败 ❌")
    else:
        print(" ✅ 全部通过!")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)
