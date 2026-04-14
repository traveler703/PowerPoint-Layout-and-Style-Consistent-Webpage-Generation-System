# PowerPoint-Layout-and-Style-Consistent-Webpage-Generation-System

同济大学软件工程专业软件工程管理与经济课程项目。

详细背景与模块说明见仓库根目录的 [Introduction.md](Introduction.md)。

## 环境准备（首次克隆后执行一次）

1. **Python 版本**：需要 **Python 3.10 及以上**。
2. **进入仓库根目录**，创建并激活虚拟环境，安装依赖：

```bash
cd PowerPoint-Layout-and-Style-Consistent-Webpage-Generation-System   # 按你的实际路径

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
pip install -e .
```

3. **（可选）LangChain 调用链**：若希望用 LangChain 封装 DeepSeek 调用，再执行：

```bash
pip install -e ".[ai]"
```

4. **配置 API（可选）**  
   - 需要**真实生成**时：在仓库根目录创建 `.env`，写入 `DEEPSEEK_API_KEY`；可选 `DEEPSEEK_API_BASE`（默认 `https://api.deepseek.com`）、`DEEPSEEK_MODEL`（默认 `deepseek-chat`）。  
   - `.env` 已被 `.gitignore` 忽略，请勿提交密钥。  
   - **离线演示 / 不想调 API**：设置环境变量 `PPT_USE_STUB=1`，将使用占位 LLM 输出（仍可跑通流水线）。运行测试时默认会启用桩（见 `tests/conftest.py`）。

---

## 如何运行

以下命令均在**仓库根目录**、且已**激活虚拟环境**的前提下执行。

### 1. 命令行跑流水线（不启动网页）

不启动浏览器，直接执行 `pipeline.py`，在终端打印评估报告并生成一段 HTML：

```bash
# 使用真实 DeepSeek（需配置 .env 中的 DEEPSEEK_API_KEY，且不要设 PPT_USE_STUB）
python pipeline.py

# 离线占位（不消耗 API）
PPT_USE_STUB=1 python pipeline.py
```

### 2. 启动 Web 演示（推荐）

用 Uvicorn 启动 FastAPI，浏览器里输入内容、选主题、预览 HTML 或导出 Markdown：

```bash
uvicorn demo.app:app --reload --app-dir .
```

- 浏览器打开：<http://127.0.0.1:8000/>  
- 页面上可输入多页内容（用单独一行的 `---` 分页）、选择主题与输出格式、勾选是否走 LangChain（需已 `pip install -e ".[ai]"` 且配置 Key）。  
- 健康检查：<http://127.0.0.1:8000/health>  
- 主题列表：`GET` <http://127.0.0.1:8000/api/themes>  

**说明**：`--app-dir .` 表示把当前目录加入 Python 路径，以便导入根目录下的 `pipeline`、`framework` 等包。

### 3. 自动化测试

```bash
pytest
```

测试默认使用 LLM 桩，无需网络与 API Key。

### 接口说明（供联调或脚本调用）

`POST /api/generate`，JSON 示例：

```json
{
  "text": "# 标题\n\n- 要点一\n- 要点二\n\n---\n\n## 第二页\n",
  "theme_id": "business_blue",
  "output_format": "html",
  "prefer_langchain": false
}
```

- `theme_id`：`business_blue` | `academic_gray` | `vibrant_orange`（与 `framework/data/themes.json` 一致）。  
- `output_format`：`html` 或 `markdown`。  
- 响应字段：`content`（生成正文）、`format`、`report`（含布局与颜色评估）。

## 现有目录与模块对应关系

| 路径 | 功能 |
|------|------|
| `framework/` | 结构化表示：样式令牌（`tokens.py`）、布局原子（`layouts.py`）、组件规范（`components.py`）；数据见 `framework/data/themes.json`、`framework/data/layouts.json`（及 `default_tokens.json`）。 |
| `engine/` | 内容解析（`content.py`）、语义类型（`types.py`）、启发式版式规划（`reasoning.py`）、约束求解占位（`constraints.py`）。 |
| `generator/` | LLM（`llm_client.py` DeepSeek / 桩）、可选 LangChain（`langchain_chain.py`，需 `pip install -e ".[ai]"`）、Prompt（`prompts.py`）、HTML/Markdown 生成器。 |
| `evaluator/` | 量化评估：布局指标（`layout_metrics.py`）、风格一致性（`style_metrics.py`）、汇总报告（`report.py`）。 |
| `demo/` | 前端预览与交互：`demo/static/` 为 HTML/CSS/JS；`demo/app.py` 为 FastAPI 入口与 API 桩。 |
| `pipeline.py` | 将上述模块串成一条占位流水线，便于联调与扩展。 |
| `tests/` | 自动化测试，可随功能补充用例。 |
