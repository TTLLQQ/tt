# 灵犀智能 AI 客服系统

三端项目：FastAPI + SQLAlchemy 后端、React 用户端、React 管理端。用户可注册登录、创建群聊/私聊、加好友、邀请数字员工并使用 `@员工名称` 提问；管理员可维护模型、白名单 Function 工具、数字员工、消息风险和数据看板。

## 技术结构

```text
backend/
  app/                 FastAPI 路由、SQLAlchemy 模型、JWT、安全工具执行
  migrations/          Alembic 初始迁移（10 张业务表）
  requirements.txt
user_frontend/         React 19 + Vite 8，默认 http://localhost:5173
admin_frontend/        React 19 + Vite 8，默认 http://localhost:5174
```

## 本地启动

需要 Python 3.11+、Node.js 20.19+（建议 Node 24）及 npm。

```bash
# Terminal 1: 后端
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
# 编辑 backend/.env，设置随机 JWT_SECRET_KEY、DATA_ENCRYPTION_KEY；
# 添加可选的 BOOTSTRAP_ADMIN_USERNAME / BOOTSTRAP_ADMIN_PASSWORD。
cd backend
set -a; . ./.env; set +a
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: 用户端
cd user_frontend
npm ci
npm run dev

# Terminal 3: 管理端
cd admin_frontend
npm ci
npm run dev
```

首次注册的普通账户不会自动成为管理员。要创建管理员，请在首次启动前配置 `BOOTSTRAP_ADMIN_USERNAME` 与强密码 `BOOTSTRAP_ADMIN_PASSWORD`；服务启动时只在该账户不存在时创建。

## 容器启动

在仓库根目录创建 `.env` 并至少设置：

```dotenv
JWT_SECRET_KEY=<至少 32 字符的随机值>
DATA_ENCRYPTION_KEY=<至少 32 字符的独立随机值>
BOOTSTRAP_ADMIN_USERNAME=admin
BOOTSTRAP_ADMIN_PASSWORD=<至少 10 字符的强密码>
```

然后执行 `docker compose up --build`。SQLite 数据保存在 `tt-data` 卷；API、用户端、管理端分别开放 8000、5173、5174 端口。不要提交实际 `.env` 或生产密钥。

## 接入模型

在管理员“大模型管理”中填写 OpenAI-compatible Base URL、模型名称与 API Key。API Key 使用 `DATA_ENCRYPTION_KEY` 加密后入库；响应不会返回明文。将模型设为默认并运行连通性测试后，可给数字员工绑定模型和工具。天气服务需另外设置 `WEATHER_API_KEY`。

Function 执行严格按 `builtin_key` 白名单分派；`function_code` 只作为审阅元数据保存，永不由 `exec`/`eval` 执行。提供天气查询、受限计算器、日期格式化、文本处理和随机数工具。计算器仅解析有限 AST 节点，内置函数不可访问。

## 测试与迁移

```bash
cd backend
python -m alembic upgrade head
python -m pytest -q
cd ../user_frontend && npm run build
cd ../admin_frontend && npm run build
npm audit --audit-level=moderate
```

后端迁移在应用启动时运行，重复 `alembic upgrade head` 不会重复创建表。生产部署前还需配置 TLS 反向代理、备份、速率限制和集中日志；聊天内容不应包含未经授权的个人敏感信息。
