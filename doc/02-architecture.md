# 问卷系统架构设计文档

### 一、 系统全景概览

| 维度 | 架构级定义 |
| :--- | :--- |
| **系统定位** | 轻量级、高扩展性的在线问卷构建、分发与数据收集分析平台 |
| **核心业务目标** | 提供动态多态问卷配置、灵活逻辑跳转流转及实时结构化数据统计能力 |
| **受众隔离** | 问卷发布者（B端视角/管理域）、问卷填写者（C端视角/收集域） |
| **关键非功能需求** | 支撑中低频并发访问，单节点满足 500+ QPS；保证数据强隔离与输入校验可靠性 |
| **演进约束** | 架构极简，规避过度设计，但必须预留题型扩展接口与存储水平扩展空间 |

### 二、 整体架构与模块划分

```mermaid
flowchart TD
    Client[客户端浏览器 / H5] --> Gateway[API 网关 / 路由接入]
    
    Gateway --> AuthCenter[身份认证模块]
    Gateway --> SurveyBiz[问卷业务服务]
    Gateway --> StatBiz[数据统计服务]

    subgraph 核心业务逻辑层
        AuthCenter
        SurveyBiz --> Config[问卷配置模块]
        SurveyBiz --> Editor[题目与逻辑流转模块]
        SurveyBiz --> Fill[问卷填写与校验模块]
        StatBiz --> Agg[聚合计算模块]
    end

    subgraph 数据持久化层
        Config --> Mongo[(MongoDB)]
        Editor --> Mongo
        Fill --> Mongo
        Agg --> Mongo
    end
```

| 模块名称 | 职责边界与核心行为 |
| :--- | :--- |
| **身份认证模块** | 承担用户注册鉴权、会话生命周期管理，确立租户/用户数据隔离屏障 |
| **问卷配置模块** | 维护问卷元数据（标题、状态、截止时间、是否允许匿名填写），控制问卷启停状态 |
| **题目与逻辑模块** | 管理多态题型（单选、多选、文本、数字）组件及其校验规则，装配动态跳转引擎配置 |
| **填写校验模块** | 承接 C 端流量，执行输入边界断言、路径推演与答卷数据持久化，拦截非法提交 |
| **数据统计模块** | 执行宏观问卷回收率统计与微观题目聚合分析（选项频次计数、数字均值计算、文本与数字明细汇总） |

### 三、 技术选型与依据

| 技术领域 | 选型决定 | 核心考量依据 |
| :--- | :--- | :--- |
| **开发语言** | Python 3.11+ | 语法极简，开发敏捷，完美匹配微型项目规模与数据聚合计算场景 |
| **依赖与环境管理** | uv | Rust 构建的下一代 Python 工具，极大提升依赖解析与虚拟环境构建速度 |
| **Web 应用框架** | FastAPI | 原生异步支持，内置 Pydantic 数据验证引擎，极其契合问卷多变、嵌套的数据结构校验 |
| **主数据库** | MongoDB | 文档型 NoSQL。Schema-free 特性天然兼容多态题型文档与动态问卷结构，支持问卷-题目聚簇存储结构，减少联表开销 |
| **缓存与状态** | 进程内内存缓存 | 基于极小规模约束，暂缓引入独立 Redis 组件，以降低系统运维复杂度，代码层预留 Cache 接口规范 |

### 四、 部署架构与拓扑

```mermaid
flowchart LR
    Browser[浏览器] --> App[FastAPI 应用]
    App --> Mongo[(MongoDB)]
```

当前实现说明：

- 仓库当前提供的是单个 FastAPI 应用实例加单个 MongoDB 实例的开发部署形态。
- MongoDB 通常通过 Docker Compose 启动，FastAPI 通过 `uv run uvicorn app.main:app --reload` 启动。
- 文档中的架构描述以当前实际交付形态为准，不描述尚未在仓库中落地的 Nginx 或多节点集群。

### 五、 核心数据流向

**链路：动态问卷加载与作答提交流程**

```mermaid
sequenceDiagram
    actor User as 问卷填写者
    participant UI as 前端渲染引擎
    participant API as 后端核心服务
    participant DB as MongoDB 集群

    User->>UI: 访问专属链接 (/survey/uuid)
    UI->>API: GET /api/v1/surveys/{uuid}/schema
    API->>DB: 聚合查询问卷元数据、题目集与跳转规则
    DB-->>API: 返回 JSON Document
    API-->>UI: 下发完整问卷 Schema 与 RuleSet
    
    loop 逐题动态推演
        User->>UI: 输入/选择答题数据
        UI->>UI: 触发本地断言（必答/极值/字数边界）
        UI->>UI: 运行规则引擎匹配条件，推演下一题游标
        UI->>User: 动态呈现目标题目（隐蔽中间跳过节点）
    end
    
    User->>UI: 触发问卷提交
    UI->>API: POST /api/v1/surveys/{uuid}/answers
    API->>API: 执行服务端防篡改二次强校验
    API->>DB: 答卷文档落库 (Answers Collection)
    DB-->>API: 确认持久化
    API-->>UI: 返回提交成功 Ack
```

### 六、 核心领域模型与类设计

```mermaid
classDiagram
    class User {
        +String user_id
        +String username
        +String password_hash
        +DateTime created_at
    }

    class Survey {
        +String survey_id
        +String title
        +Boolean is_anonymous
        +DateTime end_time
        +String status
        +publish()
        +close()
    }

    class Question {
        <<Abstract>>
        +String question_id
        +String type
        +Boolean is_required
        +Int order_index
        +validate(input_data)
    }

    class ChoiceQuestion {
        +List~String~ options
        +Int min_select
        +Int max_select
    }

    class TextQuestion {
        +Int min_length
        +Int max_length
    }

    class NumberQuestion {
        +Float min_value
        +Float max_value
        +Boolean must_be_integer
    }

    class LogicRule {
        +String rule_id
        +String source_question_id
        +String target_question_id
        +String trigger_condition
        +evaluate(current_answer) Boolean
    }

    class AnswerSheet {
        +String answer_id
        +String survey_id
        +String respondent_id
        +Boolean is_anonymous_submission
        +Map~question_id, response~ payloads
        +DateTime submitted_at
    }

    User "1" --> "0..*" Survey : owns
    Survey "1" *-- "1..*" Question : aggregates
    Survey "1" *-- "0..*" LogicRule : routes_by
    Survey "1" <-- "0..*" AnswerSheet : generates
    Question <|-- ChoiceQuestion
    Question <|-- TextQuestion
    Question <|-- NumberQuestion
```

### 七、 关键算法与业务状态流转

**7.1 问卷生命周期状态机**

```mermaid
stateDiagram-v2
    [*] --> DRAFT : 创建初始态
    DRAFT --> PUBLISHED : 配置完毕，生成分发链接
    PUBLISHED --> CLOSED : 触达截止时间
    PUBLISHED --> CLOSED : 发布者手动干预
    CLOSED --> [*] : 终止收集
```

**7.2 动态路径路由算法流转**

```mermaid
flowchart TD
    Capture([捕获当前题目输入]) --> Verify[执行当前题目合法性断言]
    Verify --> HasRules{所属问卷是否存在跳转规则?}
    HasRules -- 否 --> Advance[游标步进: 题号 + 1]
    HasRules -- 是 --> Filter[提取关联当前题目的规则集]
    Filter --> Eval[对规则条件表达式进行求值运算]
    Eval --> Match{是否存在命中规则?}
    Match -- 是 --> Redirect[游标重定向: 目标题号]
    Match -- 否 --> Advance
    Advance --> Render[挂载并渲染游标指向的新题目]
    Redirect --> Render
```

**伪代码实现参考：**

```python
def compute_next_question(current_q: Question, payload: Any, rules: List[LogicRule]) -> Question:
    """计算问卷流转的下一游标"""
    current_q.validate(payload)
    
    for rule in rules:
        if rule.source_question_id == current_q.id and rule.evaluate(payload):
            return survey.get_question_by_id(rule.target_question_id)
            
    return survey.get_question_by_order(current_q.order_index + 1)
```

补充约束：
对于单选题与多选题，`LogicRule.trigger_condition` 存储的是按空格分隔的选项行号组合。规则求值前必须先将用户当前答案转换为同样的标准化行号字符串，再执行全量相等比较，而不是基于单个选项做包含判断。

当前实现补充：

- `GET /api/v1/surveys/{survey_id}/schema` 当前实现不强制鉴权，也不会因为问卷关闭或逾期而拒绝返回 schema。
- 统计模块对文本题最多返回 20 条明细，对数字题最多返回 50 条明细，用于前端展示。
