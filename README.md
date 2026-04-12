# PowerPoint-Layout-and-Style-Consistent-Webpage-Generation-System

同济大学软件工程专业软件工程管理与经济课程项目。

详细背景与模块说明见仓库根目录的 [Introduction.md](Introduction.md)。

## 环境准备

1. 使用 **Python 3.10+**。
2. 建议在项目根目录创建虚拟环境并安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

3. **DeepSeek API**：在根目录中创建`.env`文件，填写 `DEEPSEEK_API_KEY`（必要时修改 `DEEPSEEK_API_BASE`）。`.env` 已在 `.gitignore` 中，请勿把真实密钥提交到 Git。  
   命令行与 `demo` 服务启动时会通过 `python-dotenv` 自动加载根目录的 `.env`。

## 如何运行

- **命令行跑通端到端占位流水线**（不启动 Web）：

```bash
python pipeline.py
```

- **启动带预览页的演示服务**（在项目根目录执行，保证能解析 `demo` 包与 `pipeline`）：

```bash
uvicorn demo.app:app --reload --app-dir .
```

浏览器访问：<http://127.0.0.1:8000/> ，在页面中输入文本并点击「生成预览」即可调用 `POST /api/generate`。

- **运行测试**：

```bash
pytest
```

## 目录与模块对应关系

| 路径 | 功能 |
|------|------|
| `framework/` | 结构化表示：样式令牌（`tokens.py`）、布局原子（`layouts.py`）、组件规范（`components.py`）；示例令牌见 `framework/data/default_tokens.json`。 |
| `engine/` | 布局推理与约束：语义输入类型（`types.py`）、布局规划（`reasoning.py`）、约束求解占位（`constraints.py`）。 |
| `generator/` | LLM 与代码生成：Prompt 组装（`prompts.py`）、LLM 客户端抽象（`llm_client.py`）、HTML/Markdown 生成器（`html_generator.py`、`markdown_generator.py`）。 |
| `evaluator/` | 量化评估：布局指标（`layout_metrics.py`）、风格一致性（`style_metrics.py`）、汇总报告（`report.py`）。 |
| `demo/` | 前端预览与交互：`demo/static/` 为 HTML/CSS/JS；`demo/app.py` 为 FastAPI 入口与 API 桩。 |
| `pipeline.py` | 将上述模块串成一条占位流水线，便于联调与扩展。 |
| `tests/` | 自动化测试，可随功能补充用例。 |
