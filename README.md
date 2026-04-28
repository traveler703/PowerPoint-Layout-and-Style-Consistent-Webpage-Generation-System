# PowerPoint Layout and Style Consistent Webpage Generation System

本项目目标是实现“版式与风格一致”的网页化演示稿自动生成系统，采用“模板约束 + LLM 生成”的混合方案，支持输出 `HTML`/`Markdown`（不输出 `.pptx`）。

当前仓库包含两条并行能力：

- 工程主线：`Flask + Vue3 + MySQL` 的完整可运行产品链路。
- 研究主线：按需求规约抽象的 `framework/engine/generator/evaluator` 分层能力，用于版式推理、风格令牌注入与量化评估。

---

## 1. 对齐需求规约后的能力映射

根据 `reference/Introduction.md` 与 `reference/需求规约.md`，系统核心能力如下：

- 内容输入与结构化：支持标题层级、要点、图片/表格等语义结构。
- 版式自动选型：根据内容密度、要点数、图文特征进行布局推理。
- 风格令牌管理：通过主题 token 保证跨页一致性（颜色偏差 <= 5%）。
- LLM 代码生成：生成语义化且可分发的 `HTML`/`Markdown`。
- 预览与编辑：支持即时预览与后续编辑迭代。
- 量化评估：评估元素重叠率（目标 0%）和风格一致性。

---

## 2. 项目结构

```text
.
├── app.py                     # Flask 主入口（产品链路）
├── config.py                  # 环境变量与系统配置
├── database.py                # MySQL 连接管理
├── init_db.py                 # 初始化数据库
├── pipeline.py                # 参考流水线（内容->推理->生成->评估）
├── core/                      # 现有生成核心能力（设计基因/全局宪法等）
├── services/                  # 业务服务层（Project/Outline/Slide/PPT）
├── prompts/                   # 生成相关提示词
├── frontend/                  # Vue3 + Vite 前端
├── framework/                 # 结构化可复用表示层（token/layout/component）
│   └── data/                  # themes/layouts/default_tokens 配置数据
├── engine/                    # 内容解析与版式推理引擎
├── generator/                 # LLM 客户端与 HTML/Markdown 生成器
├── evaluator/                 # 布局与风格一致性评估模块
└── scripts/                   # 测试脚本
```

目录与模块对应关系

| 路径 | 功能 |
|------|------|
| `framework/` | 结构化表示：样式令牌（`tokens.py`）、布局原子（`layouts.py`）、组件规范（`components.py`）；数据见 `framework/data/themes.json`、`framework/data/layouts.json`（及 `default_tokens.json`）。 |
| `engine/` | 内容解析（`content.py`）、语义类型（`types.py`）、启发式版式规划（`reasoning.py`）、约束求解占位（`constraints.py`）。 |
| `generator/` | LLM（`llm_client.py` DeepSeek / 桩）、可选 LangChain（`langchain_chain.py`，需 `pip install -e ".[ai]"`）、Prompt（`prompts.py`）、HTML/Markdown 生成器。 |
| `evaluator/` | 量化评估：布局指标（`layout_metrics.py`）、风格一致性（`style_metrics.py`）、汇总报告（`report.py`）。 |
| `pipeline.py` | 将上述模块串成一条占位流水线，便于联调与扩展。 |
| `scripts/` | 自动化测试，可随功能补充用例。 |

---

## 3. 环境要求

- Python 3.10+（建议 3.11）
- Node.js 18+（建议 npm 9+）
- MySQL 8.x（或兼容版本）

---

## 4. 初始化与安装

后端依赖安装：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

前端依赖安装：

```bash
cd frontend
npm install
cd ..
```

---

## 5. 环境变量配置（`.env`）

在根目录创建或修改 `.env`：

```env
# DeepSeek
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_API_URL=https://api.deepseek.com/v1    //也可以选用学院的URLhttps://llmapi.tongji.edu.cn/v1
DEEPSEEK_MODEL=deepseek-chat

# MySQL
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=ppt1122
DB_USER=root
DB_PASSWORD=your_password
```

建议使用 `127.0.0.1` 作为 `DB_HOST`，减少本机 `localhost` 解析差异。

---

## 6. 初始化数据库

首先确保电脑上已安装MySQL

确保 MySQL 服务已经启动后，在项目根目录执行：

```bash
source .venv/bin/activate
python init_db.py
```

可选：连接测试

```bash
source .venv/bin/activate
python scripts/test_db.py
```

---

## 7. 启动开发环境

终端 A（后端）：

```bash
source .venv/bin/activate
python app.py
```

启动后可访问：

- 健康检查：`http://127.0.0.1:5000/health`

终端 B（前端）：

```bash
cd frontend
npm run dev
```

浏览器访问：

- 前端：`http://localhost:5173`
- 健康检查：`http://127.0.0.1:5000/health`

---

