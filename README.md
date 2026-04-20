## 项目简介

本项目是一个基于 MongoDB 的在线问卷系统，当前已经完成题目独立存储、版本控制、题目共享、题库管理、跨问卷统计以及对应前端工作台改造。系统允许用户注册、登录、创建问卷、在题库中管理题目、配置题目与跳转逻辑、发布问卷、填写问卷，并查看单问卷与跨问卷统计结果。

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
│   │   ├── questions.py
│   │   └── surveys.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   └── time.py
│   ├── main.py
│   ├── models
│   │   ├── __init__.py
│   │   ├── answer.py
│   │   ├── question.py
│   │   ├── survey.py
│   │   └── user.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── question_service.py
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
│   ├── AI_Chat_Log.md
│   ├── AI_Chat_Log2.md
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
│   ├── test_cross_stats.py
│   ├── test_e2e.py
│   ├── test_editor.py
│   ├── test_extreme.py
│   ├── test_filling.py
│   ├── test_frontend_templates.py
│   ├── test_library.py
│   ├── test_question_sharing.py
│   ├── test_questions.py
│   ├── test_stats.py
│   └── test_surveys.py
└── uv.lock
```

整体架构可以概括为以下几层：

- `app/api`：FastAPI 路由层，负责对外提供注册、登录、题目、问卷、答卷、统计接口。
- `app/models`：Pydantic 数据模型，负责请求和数据库文档的结构约束。
- `app/core`：基础设施层，负责配置加载、MongoDB 连接、索引初始化和时间工具。
- `app/services`：当前包含认证逻辑以及题目版本、共享、题库、跨问卷统计相关服务。
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
4. 进入编辑器，在右侧“题目工作台”中新建题目，默认保存到题库。
5. 在题库卡片或题目详情中执行加入题库、分享、查看版本历史、查看使用情况等操作。
6. 把题库中的题装配进当前问卷，配置跳转规则并保存。
7. 发布问卷，复制链接。
8. 使用另一个账号访问填写页并提交答卷。
9. 返回统计页查看单问卷统计；在编辑器或统计页中也可以打开跨问卷统计。

## 测试指南

本项目当前使用 `pytest` 执行自动化测试，覆盖基础功能、完整流程、边界条件、题目版本链、共享、题库管理、前端模板入口和并发提交场景。

统一执行命令如下：

```bash
uv run pytest
```

如果需要只运行某一个测试文件，可以执行：

```bash
uv run pytest tests/test_stats.py
```

## 文档位置说明

作业要求的项目文档，这些文档都可以在 `doc/` 目录下找到。各文件的内容如下：

- `doc/01-prd.md`
  需求说明文档。主要描述系统目标、用户角色、核心流程和具体功能要求。

- `doc/02-architecture.md`
  架构设计文档。主要说明系统模块划分、领域模型、数据流和当前实现所对应的整体结构。

- `doc/03-api-spec.md`
  API 说明文档。主要记录当前实际实现中的接口路径、请求参数、返回结构和主要校验规则。

- `doc/04-db-design.md`
  数据库设计文档。主要说明 MongoDB 中各集合的用途、字段结构，以及当前实现中的实际落库字段。

- `doc/05-test-cases.md`
  测试用例文档。主要整理创建问卷、添加题目、跳转逻辑、校验、提交、统计、边界值和压力风格测试场景。

- `doc/06-deployment.md`
  部署文档。主要说明如何配置环境变量、启动 MongoDB、安装依赖和运行后端服务。

- `doc/07-frontend-spec.md`
  前端功能规范文档。主要说明各页面应具备的交互和展示要求。

- `doc/AI_Chat_Log*.md`
  完成作业时与AI的对话历史记录，包括提问（Prompt）和回复。

- `doc/ADR/`
  架构决策记录目录。后续如果有重要设计变更或关键取舍，可以继续把决策记录放在这个目录下。
