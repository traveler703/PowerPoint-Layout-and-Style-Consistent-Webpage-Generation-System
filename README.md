# PowerPoint Layout and Style Consistent Webpage Generation System

本项目是一个前后端分离的 AI PPT 生成系统：

- 后端：`Flask`（默认 `127.0.0.1:5000`）
- 前端：`Vue 3 + Vite`（默认 `localhost:5173`）
- 数据库：`MySQL`

---

## 1. 环境要求

- Python 3.10+（推荐 3.11）
- Node.js 18+（建议配套 npm 9+）
- MySQL 8.x（或兼容版本）

---

## 2. 克隆项目后首次初始化

输入下面的指令来安装相关的包

在项目根目录执行：

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

## 3. 配置环境变量（`.env`）

在项目根目录创建或修改 `.env`（与实际环境一致）：

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

说明：

- 建议 `DB_HOST` 使用 `127.0.0.1`，避免 `localhost` 在个别机器上的解析差异。
- 未配置 `DEEPSEEK_API_KEY` 时，涉及 LLM 生成的功能会失败。

---

## 4. 初始化数据库

首先确保电脑上已安装MySQL

确保 MySQL 服务已经启动后，在项目根目录执行：

```bash
source .venv/bin/activate
python init_db.py
```

如果看到类似 `Database initialized!`，表示建库建表成功。

可选：快速检查数据库连接

```bash
source .venv/bin/activate
python - <<'PY'
from database import test_connection
print(test_connection())
PY
```

---

## 5. 启动项目（开发模式）

需要两个终端窗口。

### 终端 A：启动后端

```bash
source .venv/bin/activate
python app.py
```

启动后可访问：

- 健康检查：`http://127.0.0.1:5000/health`

### 终端 B：启动前端

```bash
cd frontend
npm run dev
```

浏览器访问：

- `http://localhost:5173`

> 不要直接访问 `http://127.0.0.1:5000/` 作为前端页面。
> 该地址是后端服务地址，前端请使用 Vite 地址 `5173`。

---

## 6. 常见问题排查

### 6.1 `Can't connect to MySQL server ... Connection refused`

原因：MySQL 未启动、端口不对或主机不对。  
处理：

1. 检查 MySQL 是否运行（3306 是否监听）
2. 确认 `.env` 的 `DB_HOST/DB_PORT/DB_USER/DB_PASSWORD`
3. 用命令手工验证连接：

```bash
mysql -h 127.0.0.1 -P 3306 -u root -p
```

---

### 6.2 打开后端首页报错 `TemplateNotFound: index.html`

原因：后端 `/` 路由尝试 `render_template('index.html')`，但默认模板目录里没有该文件。  
这不影响前后端分离开发流程，正确做法是启动前端并访问：

- `http://localhost:5173`

---

### 6.3 前端请求 `/api/projects` 返回 `403 Forbidden`

典型现象：浏览器 Network 显示 `projects 403`，响应头里可能出现 `Server: AirTunes`。  
原因：机器上的 `localhost:5000` 被其他服务占用，请求没到 Flask。

已在项目中处理：`frontend/vite.config.js` 代理目标改为：

- `http://127.0.0.1:5000`

如果你本地仍异常，请：

1. 重启前端开发服务器（`npm run dev`）
2. 确认后端运行在 `127.0.0.1:5000`
3. 再次测试新建项目

---

## 7. 项目结构（核心目录）

```text
.
├── app.py                 # Flask 主入口
├── config.py              # 环境变量与系统配置
├── database.py            # DB 连接与游标管理
├── init_db.py             # 数据库初始化脚本
├── services/              # 业务服务层（Project/Outline/Slide/PPT）
├── requirements.txt       # Python 依赖
└── frontend/              # Vue + Vite 前端
```

---

## 8. 团队协作建议

- 后端改动前先跑 `python init_db.py` 确认表结构一致
- 前端改动后确保 API 基地址仍走 Vite 代理（`/api`）
- 提交前至少验证：
  - `GET /health` 正常
  - 前端可以“新建项目”成功
  - 数据库连接测试通过

