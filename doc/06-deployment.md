### 问卷系统部署指南

本项目采用容器化与本地环境结合的部署方案，后端基于 FastAPI 框架，数据库采用 MongoDB。**本项目强制使用 uv 进行依赖与 Python 环境管理**，以确保开发与部署环境的高度一致性。

#### 环境依赖
1. **Docker & Docker Compose**：用于运行 MongoDB 容器及生产环境编排。
2. **uv (Python 管理工具)**：用于本地开发环境的依赖解析、虚拟环境构建及后端服务启动。

#### 环境变量配置 (.env)
系统启动前需准备 `.env` 文件，包含以下核心参数：
- **MONGO_INITDB_ROOT_USERNAME/PASSWORD**：MongoDB 超级管理员账号。
- **MONGODB_URL**：后端连接数据库的 DSN，如 `mongodb://user:pass@localhost:27017/db?authSource=admin`。
- **SECRET_KEY**：用于 JWT 签名的随机密钥。

#### 本地开发启动 (使用 uv)
在项目根目录下，通过以下步骤快速启动：
1. **启动数据库**：运行 `docker compose up -d mongo` 启动 MongoDB。
2. **同步环境**：执行 `uv sync` 自动创建虚拟环境并安装所有声明在 `pyproject.toml` 中的依赖。
3. **运行服务**：执行 `uv run uvicorn main:app --reload` 启动 FastAPI 后端。
