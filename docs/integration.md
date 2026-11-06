# 三端联调记录

## 自动化测试

`backend/tests/test_api.py` 使用 SQLite 临时库及 OpenAI-compatible mock 服务验证：

- 管理员/普通用户登录和权限边界、30 分钟 token 声明。
- 注册、好友添加、群聊创建、成员与数字员工加入、分享链接加入、消息历史。
- WebSocket 鉴权与 emoji 房间广播，非法图片地址拒绝。
- 模拟模型发出 calculator tool_call，安全白名单执行 `2 + 3`，将结果返回模型并保存员工答复；数字员工 sender_id 为负数，调用日志可查。
- 恶意表达式被拒绝；模型 API Key 入库后不从配置 API 回显。
- 对话助手 SSE 六类事件，用户资料修改、敏感分析与数据统计。

## 本次本地运行验证

- `python -m pytest -q`：2 个集成测试通过。
- 用户端、管理端 `npm run build`：成功；Vite 提醒 JS chunk 超过 500 KB，需要后续代码分割优化。
- 三端 HTTP 联调：后端 `/healthz` 200，5173/5174 首页 200；两端 `/api/users/me` 通过 Vite proxy 到 API 并因缺少凭据返回 401；bootstrap 管理员表单登录发出 Bearer token。
- 没有使用或提交真实模型 API Key；mock 成功不代表教师提供的 LLM 已接通。
