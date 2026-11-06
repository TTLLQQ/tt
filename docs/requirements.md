# 老师项目需求与实现范围

## 三端架构

- **后端**：FastAPI、SQLAlchemy 2.x、Alembic；6 个路由模块 users、chatrooms、admin、ai_agents、chat_assistant、weather；房间 WebSocket `/ws/chat/{room_id}/{user_id}`。
- **用户端**：React、React Router、Ant Design、Zustand、Axios、Vite；端口 5173。实现注册/登录、联系人、群聊/私聊、分享加入、数字员工、消息和表情/图片消息。
- **管理端**：React、Ant Design、Axios、Vite、ECharts/Recharts、ReactMarkdown；端口 5174。实现用户、消息、模型、工具、数字员工、对话助手与统计页面。

## 核心业务验收链路

1. 用户注册/登录 → 添加好友 → 建立群聊并选择好友/数字员工 → 打开分享链接加入 → 通过 WebSocket 收发消息 → `@` 群内数字员工获取答复和工具调用记录。
2. 管理员通过环境变量引导创建 → 添加 OpenAI-compatible 模型 → 密钥加密存储并测试连通性 → 管理内置/自定义工具 → 运行白名单工具测试 → 创建员工、绑定模型/工具、生成提示词。
3. 管理员用自然语言提出统计问题 → 后端只执行固定的 ORM 聚合查询 → 通过 SSE 发送 tool、chart、content、done 事件 → 页面渲染图表。

## 数据结构

SQLAlchemy 声明十张业务表：`users`、`friends`、`chat_rooms`、`room_members`、`room_employees`、`messages`、`ai_models`、`ai_tools`、`digital_employees`、`tool_call_logs`。SQLite 外键启用；密钥以独立加密密钥派生 Fernet 密钥加密保存。Alembic 首始迁移在服务启动时执行。

## 安全边界

- JWT HS256 密钥只从环境变量读取，启动时强制至少 32 字符；token 默认 30 分钟。
- 密码经 SHA-256 预散列后再用带随机盐 bcrypt 哈希，避免 bcrypt 72 字节截断。
- CORS 只允许配置的两个开发来源。管理 API 均要求管理员角色。
- Function 只按 `builtin_key` 分派到固定白名单；工具源代码字段只保存为不执行的审阅文本。计算器使用 AST 递归求值和范围限制，不调用 `eval`/`exec`。
- 模型 API Key 加密入库，查询接口不返回明文。天气 Key 从环境变量读取。
- React 默认转义内容；图片消息只接受 HTTP(S) URL；没有 `dangerouslySetInnerHTML`。

## 明确的实现限制

实时员工问答和工具提案依赖管理员配置的真实 OpenAI-compatible 服务。本地测试用可控的模拟兼容服务验证工具调用闭环。对话分析实现的是受限固定 ORM 聚合问题，不接受模型生成 SQL，也没有执行任意 NL2SQL；敏感消息分析暂用关键词回退并 SSE 推进度，不会把聊天内容发送给未配置的第三方模型。
