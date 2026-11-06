# 项目交付清单

| 交付项 | 路径 | 完成定义 |
|---|---|---|
| 后端 API 与鉴权 | `backend/app/main.py`、`security.py`、`routers/` | FastAPI 服务运行；OAuth2/JWT、管理员访问控制、限定 CORS |
| 10 张业务表与迁移 | `backend/app/models.py`、`backend/migrations/` | Alembic 初始迁移可重复运行 |
| 用户端 | `user_frontend/` | React/Vite 用户注册、通讯录、群聊、分享加入、消息、表情/图片与 @ 员工 |
| 管理端 | `admin_frontend/` | 真实 API 页面：用户、聊天/风控、助手、模型、工具、员工、统计 |
| AI 工具安全与审计 | `backend/app/tool_registry.py`、`ai_service.py` | 固定白名单执行；tool_call 结果回喂；日志记录入参/结果/状态/耗时 |
| SSE 查询/风控 | `backend/app/routers/chat_assistant.py`、`admin.py` | 受限分析查询流式输出；风控推进度流式返回 |
| 运行配置与容器 | `.gitignore`、`backend/.env.example`、`compose.yaml`、各端 Dockerfile | 不提交秘密；前端代理；SQLite 命名卷 |
| 自动化验证 | `backend/tests/test_api.py` | 登录权限、聊天室、分享加入、WS、模型凭据、白名单工具与 SSE 集成测试 |
| 项目文档 | `README.md`、`docs/` | 启动、边界、验收和交付项可查 |

视觉参考图 `docs/users/`、`docs/admin/`、Stitch 原型及 DESIGN.md 在当前检出中不存在，故没有把不存在的资产列为本次已交付文件。
