# Part 1：内容输入模块与结构化可复用框架

> 开发分支：`feat/part-1`  
> 完成日期：2026-04-29

---

## 一、本轮改动概述

本轮实现了**流程 1**的两个核心子模块：

1. **内容输入模块**（`parsers/`）：支持 4 种文档格式的结构化解析
2. **结构化可复用框架补充**（`framework/data/`）：扩展版式原子库、新增组件规格库、扩展主题库

---

## 二、内容输入模块（`parsers/`）

### 2.1 模块结构

```
parsers/
├── __init__.py              # 统一导出
├── base.py                  # 统一 Schema（DocumentParseResult）+ 解析器基类
├── markdown_parser.py       # Markdown/TXT 解析器
├── pdf_parser.py            # PDF 解析器（pdfplumber）
├── docx_parser.py           # Word 解析器（python-docx）
├── pptx_parser.py           # PowerPoint 解析器（python-pptx）
└── text_compressor.py       # LLM 长文本智能压缩
```

### 2.2 支持的文档格式

| 格式 | 扩展名 | 解析库 | 提取内容 |
|------|--------|--------|----------|
| Markdown | `.md` | 内置正则解析 | 多级标题、列表、GFM 表格、图片链接 |
| 纯文本 | `.txt` | 同上 | 同上（按纯文本处理） |
| PDF | `.pdf` | pdfplumber | 文本块、表格、嵌入图片位置 |
| Word | `.docx` | python-docx | 段落/标题层级、列表、表格、嵌入图片(base64) |
| PowerPoint | `.pptx` | python-pptx | 幻灯片标题、文本框、表格、嵌入图片(base64) |

### 2.3 统一输出 JSON 格式（`DocumentParseResult`）

所有解析器最终输出统一的 `DocumentParseResult` 结构，可直接序列化为 JSON 文件：

```json
{
  "metadata": {
    "title": "文档标题",
    "source_format": "docx",
    "source_filename": "report.docx",
    "page_count": 5,
    "total_chars": 3200,
    "author": "作者名"
  },
  "pages": [
    {
      "page_index": 0,
      "title": "页面主标题",
      "headings": [{"level": 2, "text": "子标题"}],
      "paragraphs": ["正文段落..."],
      "bullets": [{"title": "要点", "description": "详细描述"}],
      "tables": [{"headers": ["列1","列2"], "rows": [["数据1","数据2"]]}],
      "images": [{"url": "data:image/png;base64,...", "alt": "描述"}],
      "has_chart": false,
      "has_table": true,
      "raw_text": "原始文本...",
      "compressed": false
    }
  ]
}
```

### 2.4 JSON 输出位置说明

**⚠️ 重要：下一步接手者请注意**

内容输入模块的 JSON 结果通过以下方式获取：

1. **后端 API 调用**：`POST /api/upload-document` 上传文件，返回 JSON 格式的 `DocumentParseResult`
2. **程序化调用**：
   ```python
   from parsers.markdown_parser import MarkdownParser
   
   parser = MarkdownParser()
   result = parser.parse("your_file.md", filename="your_file.md")
   
   # 序列化为 JSON 字符串
   json_str = result.to_json(indent=2)
   
   # 保存为 JSON 文件
   result.save_json("output/parsed_result.json")
   
   # 从 JSON 加载
   restored = DocumentParseResult.load_json("output/parsed_result.json")
   ```

3. **前端上传**：用户在前端上传文件 → 后端解析 → 返回 JSON → 前端展示解析结果 → 用户确认后进入大纲编辑

### 2.5 长文本压缩

当页面文本超过阈值（默认 800 字符/页，300 字符/段落），自动调用 DeepSeek LLM 进行压缩：

```python
from parsers.text_compressor import TextCompressor

compressor = TextCompressor(page_threshold=800, paragraph_threshold=300)
compressed_doc = await compressor.compress_document(parse_result)
```

压缩后：
- `page.compressed = True`
- `page.compressed_from` 保留原始文本
- 长段落被替换为结构化 `bullets`

---

## 三、结构化可复用框架补充

### 3.1 版式原子库扩展（`framework/data/layouts.json`）

从原有 7 种扩展到 **12 种**：

| ID | 名称 | 适用场景 | 新增 |
|----|------|----------|------|
| hero-title-body | 标题+正文 | 封面/过渡/内容 | - |
| two-column | 双栏要点 | 内容页 | - |
| three-column | 三栏要点 | 内容页 | - |
| image-text-left | 左图右文 | 内容页 | - |
| image-text-top | 上图下文 | 内容页 | - |
| chart-focus | 图表强调 | 数据页 | - |
| table-focus | 表格版式 | 数据页 | - |
| **title-only** | 纯标题封面 | 封面/过渡页 | ✅ |
| **quote-highlight** | 引言金句 | 过渡/内容页 | ✅ |
| **timeline** | 时间线版式 | 内容页 | ✅ |
| **comparison** | 对比版式 | 内容页 | ✅ |
| **statistics** | 数据统计版式 | 数据/内容页 | ✅ |

### 3.2 组件规格库（`framework/data/components.json`）— 新增

定义了 11 种组件的详细约束（字体大小范围、间距、尺寸限制等）：

- title、subtitle、heading、paragraph
- bullet_list、image、table、chart
- quote、statistic、timeline_item

还包括全局间距规则和画布尺寸配置。

### 3.3 主题扩展（`framework/data/themes.json`）

从 3 个扩展到 **6 个**：

| 主题 ID | 风格 | 新增 |
|---------|------|------|
| business_blue | 商务蓝 | - |
| academic_gray | 学术灰 | - |
| vibrant_orange | 活力橙 | - |
| **tech_dark** | 科技暗色 | ✅ |
| **nature_green** | 自然绿 | ✅ |
| **minimal_white** | 极简白 | ✅ |

---

## 四、后端 API 变更

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/upload-document` | POST | 文件上传解析（multipart/form-data） |
| `/api/supported-formats` | GET | 获取支持的文件格式列表 |

### `/api/upload-document` 请求示例

```bash
curl -X POST http://localhost:5000/api/upload-document \
  -F "file=@report.docx"
```

响应：
```json
{
  "success": true,
  "result": { /* DocumentParseResult JSON */ },
  "meta": {
    "filename": "report.docx",
    "format": "docx",
    "file_size": 45231,
    "page_count": 5,
    "total_chars": 3200
  }
}
```

---

## 五、前端变更

- `frontend/src/services/api.js`：新增 `uploadDocument(file)` 和 `getSupportedFormats()` 函数
- `frontend/src/components/DocumentInputPanel.vue`：
  - 文件上传区支持 `.pptx` 格式
  - 实现真正的后端文件上传（非前端 FileReader 读文本）
  - 上传进度状态、成功回显（格式/大小/页数）
  - 解析结果自动转换为 store 格式展示

---

## 六、新增依赖（`requirements.txt`）

```
# 文档解析
pdfplumber>=0.10.0
python-docx>=1.1.0
python-pptx>=0.6.23
Pillow>=10.0.0
```

---

## 七、如何测试

### 快速验证

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行集成测试脚本
python scripts/test_parsers.py
```

### 手动测试 API

```bash
# 启动后端
source .venv/bin/activate && python app.py

# 另一个终端，上传文件测试
curl -X POST http://localhost:5000/api/upload-document -F "file=@your_file.docx"
```

### 前端完整流程测试

1. 启动后端：`source .venv/bin/activate && python app.py`
2. 启动前端：`cd frontend && npm run dev`
3. 浏览器打开 `http://localhost:5173`
4. 创建项目 → 进入「文档输入」步骤 → 切换到「上传文件」标签 → 拖拽/选择文件上传
5. 验证解析结果正确显示

---

## 八、下一步（流程 2）衔接点

流程 2（自动化版式选型和代码生成）需要：

1. **输入**：本模块输出的 `DocumentParseResult` JSON（通过 `result.to_json()` 或 API 返回值获取）
2. **框架数据**：
   - `framework/data/layouts.json` — 版式原子库
   - `framework/data/components.json` — 组件约束规格
   - `framework/data/themes.json` — 主题样式
3. **关键类**：
   - `parsers.base.PageContent` — 单页结构化内容
   - `framework.layouts.LayoutRegistry` — 版式注册表
   - `framework.tokens.StyleTokens` — 样式 Token

接手者可从 `DocumentParseResult.pages` 遍历每一页，结合 `PageContent` 的属性（`has_table`、`has_chart`、`effective_bullet_count`、`images`）进行版式匹配。
