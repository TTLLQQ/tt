# 项目验收核对表

责任人与实际时间由小组补录；仓库代码和命令输出为验收证据，截图或口头声明不能替代链路运行。

| 状态 | 阶段 | 核验标准 | 当前证据/说明 |
|---|---|---|---|
| [x] | 环境/骨架 | Python API 与两个 React 开发服务器启动；API 代理工作 | 三端本地联调：HTML 200、API 未授权请求经代理到达并返回 401 |
| [x] | 数据/迁移 | 10 张表创建；Alembic 重复 upgrade 安全 | 初始迁移运行成功；schema 检查包含十表与 `alembic_version` |
| [x] | 鉴权 | OAuth2 表单登录、Bearer JWT、管理员依赖、30 分钟 TTL | 后端测试检查管理员与普通用户权限、TTL |
| [x] | 用户主链路 | 注册/登录、好友、建群拉好友/员工、分享加入、历史消息 | `backend/tests/test_api.py` 集成测试 |
| [x] | 实时聊天 | WS 成员校验、三类消息、房间广播；数字员工负数 sender_id | 测试覆盖 emoji 广播与 tool-call 回复身份 |
| [x] | Function 安全 | 内置工具可测；非白名单/代码文本不执行；调用有日志 | 计算器合法/恶意输入测试与日志断言 |
| [x] | 管理端 | 用户、消息风控、模型、工具、员工、分析模块加载真实 API | API 集成测试及 `admin_frontend` 生产构建 |
| [x] | SSE | 助手发送六类事件；敏感分析发送进度 | 测试检查 tool_call/tool_result/chart_call/chart_result/content/done 及风控 progress/done |
| [x] | 前端 | 两端生产构建通过，四种问答图表按类型渲染 | `npm run build` 两端成功；包体仍有 Vite 大 chunk 提示 |
| [x] | 依赖风险 | 前端依赖 audit 无中危及以上告警 | 用户端与管理端 `npm audit --audit-level=moderate` 均为 0；ECharts 已升级至修复版 |
| [x] | 容器验证 | 三镜像构建、服务健康、前端页面和 API 代理可用 | Compose 全量构建通过；容器健康；三端 HTTP 200；管理员登录后 dashboard 与 5 个内置工具可读取；迁移创建 10 张业务表 |
| [ ] | 真实服务接入 | 配置教师/小组实际模型凭据，连通性测试成功并完成现场 LLM 工具链演示 | 当前只用本地模拟 OpenAI-compatible 服务验证，不代表真实服务已接通 |
| [ ] | UI 现场验收 | 在验收机按 5173/5174 现场操作并留存约定截图/录屏 | 尚未由验收人员签字 |
| [ ] | 发布追溯 | 按小组分支与过程提交要求形成可审阅 Git 历史 | 当前仓库起始历史只有初始提交；本次改动尚未提交 |
| [ ] | 生产部署 | 持久卷备份、HTTPS、限流、监控及故障演练 | Compose 本地容器通过；生产配置与故障演练不在当前证据内 |

## 验收执行命令

```bash
cd backend
PYTHONPATH=. python -m pytest -q
python -m alembic upgrade head
cd ../user_frontend && npm run build
cd ../admin_frontend && npm run build
npm audit --audit-level=moderate
```

不要在报告中把本地 mock provider 测试写成真实模型服务验证。NL 统计问答仅开放固定类型的 SQLAlchemy 聚合查询，不执行模型生成的 SQL；敏感内容扫描使用内置关键词策略，不调用外部模型。
