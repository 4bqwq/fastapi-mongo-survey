## 项目简介

本项目是一个基于 MongoDB 的在线问卷系统，目标是完成大作业一中第一阶段要求的主要程序实现。系统允许用户注册、登录、创建问卷、配置题目与跳转逻辑、发布问卷、填写问卷，并查看统计结果。

当前程序已经实现的核心能力包括：

- 用户注册与登录
- 问卷创建、列表查看、状态切换
- 问卷基础信息配置，包括标题、说明、是否允许匿名、截止时间
- 题目编辑，支持选择题、文本题、数字题
- 题目校验规则，包括必答、选择数量、文本长度、数字范围、整数限制
- 跳转逻辑配置与执行
- 问卷填写与提交
- 统计结果查看，包括选择题分布、文本题明细、数字题平均值与明细
- 自动化测试，包括单项测试、完整路径测试、边界测试和并发压力风格测试

## 项目文件结构

```text
.
├── .env.example
├── .gitignore
├── .python-version
├── AGENTS.md
├── README.md
├── app
│   ├── __init__.py
│   ├── api
│   │   ├── __init__.py
│   │   ├── answers.py
│   │   ├── auth.py
│   │   ├── deps.py
│   │   └── surveys.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── database.py
│   ├── main.py
│   ├── models
│   │   ├── __init__.py
│   │   ├── answer.py
│   │   ├── survey.py
│   │   └── user.py
│   ├── services
│   │   ├── __init__.py
│   │   └── auth.py
│   └── static
│       └── js
│           └── auth.js
├── doc
│   ├── 01-prd.md
│   ├── 02-architecture.md
│   ├── 03-api-spec.md
│   ├── 04-db-design.md
│   ├── 05-test-cases.md
│   ├── 06-deployment.md
│   ├── 07-frontend-spec.md
│   └── ADR
├── docker-compose.yml
├── pyproject.toml
├── templates
│   ├── dashboard.html
│   ├── editor.html
│   ├── login.html
│   ├── register.html
│   ├── stats.html
│   └── survey_fill.html
├── tests
│   ├── test_auth.py
│   ├── test_e2e.py
│   ├── test_editor.py
│   ├── test_extreme.py
│   ├── test_filling.py
│   ├── test_stats.py
│   └── test_surveys.py
└── uv.lock
```

整体架构可以概括为以下几层：

- `app/api`：FastAPI 路由层，负责对外提供注册、登录、问卷、答卷、统计接口。
- `app/models`：Pydantic 数据模型，负责请求和数据库文档的结构约束。
- `app/core`：基础设施层，负责配置加载和 MongoDB 连接。
- `app/services`：当前主要放认证相关的辅助逻辑。
- `templates`：前端页面模板，包含登录、注册、看板、编辑器、填写页、统计页。
- `app/static`：前端静态资源，目前主要是认证相关的通用脚本。
- `doc`：需求、架构、API、数据库、测试、部署等文档。
- `tests`：自动化测试。

## 部署方式

本项目推荐使用 `uv` 管理 Python 依赖，使用 Docker 运行 MongoDB。这样可以减少本地环境差异。

### 1. 准备环境

需要先安装以下工具：

- Python 3.12 或更高版本
- uv
- Docker

### 2. 配置环境变量

可以先复制一份示例配置：

```bash
cp .env.example .env
```

`.env` 中至少需要关注以下字段：

- `MONGO_INITDB_ROOT_USERNAME`
- `MONGO_INITDB_ROOT_PASSWORD`
- `MONGO_DB_NAME`
- `MONGODB_URL`
- `SECRET_KEY`
- `ACCESS_TOKEN_EXPIRE_MINUTES`

如果直接使用本项目默认的 Docker 配置，通常可以保留示例中的数据库名称和连接格式，只需根据需要修改用户名、密码和 JWT 密钥。

### 3. 启动 MongoDB

项目根目录已经提供了 `docker-compose.yml`，定义了两个服务：

- `mongodb`：MongoDB 数据库
- `mongo-express`：MongoDB 可视化管理工具

启动命令如下：

```bash
docker compose up -d
```

启动完成后：

- MongoDB 默认暴露在 `localhost:27017`
- Mongo Express 默认暴露在 `localhost:8081`

如果只想启动数据库，不启动可视化工具，也可以执行：

```bash
docker compose up -d mongodb
```

### 4. 安装依赖

本项目要求使用 `uv`

在项目根目录执行：

```bash
uv sync
```

该命令会根据 `pyproject.toml` 和 `uv.lock` 创建虚拟环境并安装依赖。

## 运行方法

### 1. 启动数据库

```bash
docker compose up -d
```

### 2. 同步依赖

```bash
uv sync
```

### 3. 启动后端服务

实际应用入口在 `app/main.py` 对应的 FastAPI 实例中。项目当前常用启动方式是：

```bash
uv run uvicorn app.main:app --reload
```

启动后可以访问：

- 登录页：`http://127.0.0.1:8000/login`
- 注册页：`http://127.0.0.1:8000/register`
- 问卷看板：`http://127.0.0.1:8000/dashboard`
- 健康检查：`http://127.0.0.1:8000/health`

### 4. 使用流程

可以按以下顺序手工体验：

1. 注册一个发布者账号。
2. 登录后进入看板。
3. 创建问卷，设置标题、说明、匿名选项、截止时间。
4. 进入编辑器添加题目和跳转规则。
5. 发布问卷，复制链接。
6. 使用另一个账号访问填写页并提交答卷。
7. 返回统计页查看回收情况、选择题分布、文本明细、数字平均值与数字明细。

## 测试指南

本项目当前使用 `pytest` 执行自动化测试，覆盖基础功能、完整流程、边界条件和并发提交场景。

统一执行命令如下：

```bash
uv run pytest
```

如果需要只运行某一个测试文件，可以执行：

```bash
uv run pytest tests/test_stats.py
```


