# Part 1：内容输入模块与结构化可复用框架

> 开发分支：`feat/part-1`  
> 完成日期：2026-04-30

---

## 一、功能概述

本轮实现了四阶段流程中的**第 1 阶段**——内容输入模块和结构化可复用框架：

### 实现目标（对照需求规约）

| 需求要点 | 实现情况 |
|----------|----------|
| 支持四种格式文档的解析 | ✅ 支持 Markdown/TXT、PDF、DOCX、PPTX |
| 准确提取各级标题 | ✅ 支持 Word 标题样式 + 启发式检测（加粗/字号/编号模式） |
| 准确提取表格 | ✅ 所有格式均能正确提取表格并放到正确的逻辑页面 |
| 准确提取图片 | ✅ DOCX/PPTX 提取嵌入图片为 base64；PDF 提取嵌入图片并自动转 PNG；Markdown 保留图片路径 |
| 长段落调用大模型进行压缩 | ✅ `TextCompressor` 支持按阈值自动调用 DeepSeek 压缩 |
| 输出 JSON 格式便于后续处理 | ✅ 统一 `DocumentParseResult` Schema，自动保存到 `output/` |
| 结构化可复用框架补充细化 | ✅ 版式库 12 种、组件规格库 11 种、主题库 6 种 |

### 核心模块

```
parsers/                    # 内容输入模块
├── base.py                 # 统一 Schema + 解析器基类
├── markdown_parser.py      # Markdown/TXT 解析
├── pdf_parser.py           # PDF 解析（pdfplumber）
├── docx_parser.py          # Word 解析（python-docx）
├── pptx_parser.py          # PowerPoint 解析（python-pptx）
└── text_compressor.py      # LLM 长文本压缩

framework/data/             # 结构化可复用框架
├── layouts.json            # 版式原子库（12 种）
├── components.json         # 组件规格约束库（11 种）
└── themes.json             # 主题样式库（6 种）
```

---

## 二、前端功能演示操作指南

### 启动方式

```bash
# 终端 1：启动后端
source .venv/bin/activate && python app.py

# 终端 2：启动前端
cd frontend && npm run dev
```

打开浏览器访问 `http://localhost:5173`

### 操作流程

1. **创建/选择项目** → 进入「文档输入」步骤
2. **切换到「上传文件」标签** → 拖拽或点击选择文件
3. **上传文档**（支持 `.md` `.txt` `.pdf` `.docx` `.pptx`，最大 20MB）
4. **查看解析结果**：右侧面板自动展示：
   - 📄 文档标题
   - 📑 按逻辑章节分页的内容（标题、副标题、要点列表、正文）
   - 📊 **表格**（以标准 HTML table 形式展示，含表头和数据行）
   - 🖼️ **图片**（内嵌预览，base64 编码）
5. **点击「开始应用」** → 保存解析结果并进入大纲编辑

### 各格式特殊说明

| 格式 | 图片处理 | 备注 |
|------|----------|------|
| **DOCX** | 嵌入图片自动转 base64，按文档位置分配到正确页面 | 支持标题样式和启发式标题检测 |
| **PPTX** | 嵌入图片自动转 base64 | 每张幻灯片对应一个逻辑页面 |
| **PDF** | 嵌入图片提取为 PNG base64 | 自动按编号标题重新分页 |
| **Markdown** | ⚠️ **仅保留图片路径引用**，不提取实际图片数据 | 因为 `.md` 中的 `![alt](path)` 是相对路径或 URL，不含图片本身。前端会显示路径但不能预览图片 |
| **TXT** | 无图片 | 按 Markdown 规则解析 |

### API 返回与 JSON 保存

**API 直接返回完整的 `DocumentParseResult` JSON**（在响应的 `result` 字段中），这是下一阶段（版式选型）的主要输入来源。

同时，为方便调试，解析结果也会自动保存一份到 `output/` 目录：

```
output/<文件名>_<时间戳>.json
```

> `output/` 中的文件仅用于调试和离线查看，不影响正常流程。API 响应的 `meta.json_output_path` 字段记录了保存路径。

---

## 三、测试方式

### 3.1 自动化测试（`scripts/test_parsers.py`）

```bash
source .venv/bin/activate
python scripts/test_parsers.py
```

覆盖 6 项自动化验证：

| 测试项 | 验证内容 |
|--------|----------|
| 测试 1 | Schema 模型创建、序列化（to_json）、反序列化（load_json） |
| 测试 2 | Markdown 解析器正确提取标题/列表/表格/图片引用 |
| 测试 3 | 文件格式自动检测（按扩展名 → 正确解析器） |
| 测试 4 | Flask API 端点（`/api/upload-document`、`/api/supported-formats`）响应正确 |
| 测试 5 | 框架数据文件完整性（layouts/components/themes JSON 格式校验） |
| 测试 6 | JSON 保存和加载往返一致性 |

预期输出：
```
✅ 测试 1 通过：Schema 模型创建和序列化正确
✅ 测试 2 通过：Markdown 解析器正确提取标题/列表/表格/图片
✅ 测试 3 通过：文件格式检测正确
✅ 测试 4 通过：Flask API 端点工作正常
✅ 测试 5 通过：框架数据文件完整且格式正确
✅ 测试 6 通过：JSON 保存和加载功能正确
============================================================
结果: 6/6 通过 ✅ 全部通过!
============================================================
```

### 3.2 手动测试（`testcases/carrot/`）

`testcases/carrot/` 目录提供了一套完整的"胡萝卜简介"测试文档，同一内容覆盖所有格式：

```
testcases/carrot/
├── carrot_md.md          # Markdown 格式
├── carrot_txt.txt        # 纯文本格式
├── carrot_pdf.pdf        # PDF 格式
├── carrot_word.docx      # Word 格式
├── carrot_ppt.pptx       # PowerPoint 格式
├── carrot_01.jpg         # 测试图片 1（md 引用）
└── carrot_02.jpg         # 测试图片 2（md 引用）
```

#### 手动测试方法 A：通过前端上传

1. 启动前后端服务
2. 依次上传 `testcases/carrot/` 中的 5 个文档
3. 验证每个格式的解析结果：
   - **4 个逻辑页面**：胡萝卜简介 → 什么是胡萝卜 → 品种有哪些 → 怎么吃
   - **表格**在"3.胡萝卜怎么吃"页面正确展示（萝卜品种 | 胡萝卜 | 白萝卜）
   - **图片**在正确的页面显示（DOCX/PPTX/PDF 为 base64 预览；MD 为路径引用）

#### 手动测试方法 B：通过 Python 脚本

```bash
source .venv/bin/activate
python3 -c "
import sys; sys.path.insert(0, '.')
from parsers.docx_parser import DocxParser
from parsers.pdf_parser import PdfParser
from parsers.pptx_parser import PptxParser
from parsers.markdown_parser import MarkdownParser

# 测试 DOCX
parser = DocxParser()
with open('testcases/carrot/carrot_word.docx', 'rb') as f:
    result = parser.parse(f.read(), filename='carrot_word.docx')
print(f'DOCX: {len(result.pages)} pages')
for p in result.pages:
    print(f'  Page {p.page_index} ({p.title}): {len(p.images)} imgs, {len(p.tables)} tables')

# 测试 PDF
parser = PdfParser()
with open('testcases/carrot/carrot_pdf.pdf', 'rb') as f:
    result = parser.parse(f.read(), filename='carrot_pdf.pdf')
print(f'PDF: {len(result.pages)} pages')
for p in result.pages:
    print(f'  Page {p.page_index} ({p.title}): {len(p.images)} imgs, {len(p.tables)} tables')

# 测试 PPTX
parser = PptxParser()
with open('testcases/carrot/carrot_ppt.pptx', 'rb') as f:
    result = parser.parse(f.read(), filename='carrot_ppt.pptx')
print(f'PPTX: {len(result.pages)} pages')
for p in result.pages:
    print(f'  Page {p.page_index} ({p.title}): {len(p.images)} imgs, {len(p.tables)} tables')
"
```

#### 手动测试方法 C：通过 curl 调用 API

```bash
# 启动后端
source .venv/bin/activate && python app.py &

# 上传测试
curl -s -X POST http://localhost:5000/api/upload-document \
  -F "file=@testcases/carrot/carrot_word.docx" | python3 -m json.tool | head -30
```

---

## 四、统一输出 JSON 格式（`DocumentParseResult`）

```json
{
  "metadata": {
    "title": "胡萝卜简介",
    "source_format": "docx",
    "source_filename": "carrot_word.docx",
    "page_count": 4,
    "total_chars": 680,
    "author": ""
  },
  "pages": [
    {
      "page_index": 0,
      "title": "胡萝卜简介",
      "headings": [],
      "paragraphs": [],
      "bullets": [],
      "tables": [],
      "images": [],
      "has_chart": false,
      "has_table": false,
      "raw_text": "",
      "compressed": false
    },
    {
      "page_index": 1,
      "title": "1.什么是胡萝卜",
      "headings": [],
      "paragraphs": ["胡萝卜(Daucus carota...)..."],
      "bullets": [],
      "tables": [],
      "images": [{"url": "data:image/png;base64,...", "alt": "嵌入图片 (png)"}],
      "has_chart": false,
      "has_table": false,
      "raw_text": "...",
      "compressed": false
    },
    {
      "page_index": 3,
      "title": "3.胡萝卜怎么吃",
      "paragraphs": ["..."],
      "tables": [
        {
          "headers": ["萝卜品种", "胡萝卜", "白萝卜"],
          "rows": [["营养指数", "3.3", "3.2"]]
        }
      ],
      "has_table": true
    }
  ]
}
```

---

## 五、结构化可复用框架

### 5.1 版式原子库（`framework/data/layouts.json`）— 12 种

| ID | 名称 | 适用场景 |
|----|------|----------|
| hero-title-body | 标题+正文 | 封面/过渡/内容 |
| two-column | 双栏要点 | 内容页 |
| three-column | 三栏要点 | 内容页 |
| image-text-left | 左图右文 | 内容页 |
| image-text-top | 上图下文 | 内容页 |
| chart-focus | 图表强调 | 数据页 |
| table-focus | 表格版式 | 数据页 |
| title-only | 纯标题封面 | 封面/过渡页 |
| quote-highlight | 引言金句 | 过渡/内容页 |
| timeline | 时间线版式 | 内容页 |
| comparison | 对比版式 | 内容页 |
| statistics | 数据统计版式 | 数据/内容页 |

### 5.2 组件规格库（`framework/data/components.json`）— 11 种

定义每种组件的字体大小范围、间距、尺寸限制等约束。包含：title、subtitle、heading、paragraph、bullet_list、image、table、chart、quote、statistic、timeline_item。

### 5.3 主题库（`framework/data/themes.json`）— 6 种

business_blue、academic_gray、vibrant_orange、tech_dark、nature_green、minimal_white。

---

## 六、新增依赖

```txt
pdfplumber>=0.10.0
python-docx>=1.1.0
python-pptx>=0.6.23
Pillow>=10.0.0
```

---

## 七、下一步（流程 2）衔接点

流程 2（自动化版式选型和代码生成）需要的输入：

1. **`DocumentParseResult` JSON**（通过 `output/` 目录文件或 API 响应获取）
2. **框架数据**：`framework/data/` 下的 layouts、components、themes
3. **关键属性**：每个 `PageContent` 的 `has_table`、`has_chart`、`effective_bullet_count`、`images` 等字段，用于版式匹配决策
