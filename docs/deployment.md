# 本地与容器运行

## 本地

参照仓库根目录 [README](../README.md) 创建虚拟环境并安装 `backend/requirements.txt`；后端通过 `backend/.env.example` 配置环境变量。前端运行 `npm install && npm run dev`。Vite 配置 `/api` 与 `/ws` 代理到 `VITE_API_PROXY` 或默认 `127.0.0.1:8000`。

## Compose

在仓库根 `.env` 中提供 `JWT_SECRET_KEY` 与 `DATA_ENCRYPTION_KEY`（两者均至少 32 字符且互不相同），再运行：

```bash
docker compose config
docker compose up --build
```

端口为 API 8000、用户端 5173、管理端 5174。SQLite 文件保存在命名卷 `tt-data`。健康探针访问 `/healthz` 并执行数据库查询。不要把开发密钥用于生产。

## 生产部署缺项

需部署方配置 TLS/反向代理、强随机密钥管理、备份与恢复、限流、审计日志、监控告警、模型服务授权和数据保留策略。生产启用前还要进行安全评审与渗透测试。
