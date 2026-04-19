### 一、用户账号模块

#### 接口名称：用户注册

**请求方式与路径**：`POST /api/v1/auth/register`

**请求头/鉴权**：无

**请求参数**：

```json
{
  "username": "test_user",
  "password": "secure_password_123"
}
```

**返回结果**：

- **成功 (200 OK)**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "user_id": "usr_1001",
    "username": "test_user",
    "created_at": "2026-04-02T16:22:25Z"
  }
}
```

- **失败 (400 Bad Request)**

```json
{
  "code": 40001,
  "message": "用户名已存在"
}
```

#### 接口名称：用户登录

**请求方式与路径**：`POST /api/v1/auth/login`

**请求头/鉴权**：无

**请求参数**：

```json
{
  "username": "test_user",
  "password": "secure_password_123"
}
```

**返回结果**：

- **成功 (200 OK)**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR...",
    "token_type": "Bearer"
  }
}
```

------

### 二、题目库与版本控制模块

Stage 1 只覆盖“题目独立存储 + 版本控制 + 问卷快照引用”。题目分享、题库管理页面、跨问卷统计、题目被哪些问卷使用查询均不在本阶段 API 范围内。

#### 接口名称：创建题目首个版本

**请求方式与路径**：`POST /api/v1/questions`

**请求头/鉴权**：`Authorization: Bearer <Token>`

**请求参数**：

```json
{
  "type": "ChoiceQuestion",
  "title": "你的年龄段",
  "isRequired": true,
  "options": ["18岁以下", "18-25岁", "26-35岁", "36岁及以上"],
  "minSelect": 1,
  "maxSelect": 1
}
```

**说明**：

- 创建成功后自动生成一个稳定的 `questionId`，同时落地版本 `version = 1`。
- 题目版本内容不包含 `orderIndex`，因为顺序属于问卷快照而不是题库定义。

**返回结果**：

```json
{
  "code": 200,
  "data": {
    "question_id": "q_bank_001",
    "version": 1,
    "version_id": "66112233aa44bb55cc66dd77",
    "version_chain_root_id": "66112233aa44bb55cc66dd77"
  }
}
```

#### 接口名称：基于已有版本创建新版本

**请求方式与路径**：`POST /api/v1/questions/{question_id}/versions`

**请求头/鉴权**：`Authorization: Bearer <Token>`

**请求参数**：

```json
{
  "base_version": 1,
  "title": "你的年龄",
  "isRequired": true,
  "type": "NumberQuestion",
  "minValue": 0,
  "maxValue": 120,
  "mustBeInteger": true
}
```

**说明**：

- `base_version` 必须存在且属于当前用户。
- 新版本会写入 `previousVersionId`，形成 `v1 -> v2 -> v3` 单链。
- 同一 `questionId` 下允许多个版本同时被不同问卷快照引用。

**返回结果**：

```json
{
  "code": 200,
  "data": {
    "question_id": "q_bank_001",
    "version": 2,
    "version_id": "77112233aa44bb55cc66dd88",
    "previous_version_id": "66112233aa44bb55cc66dd77"
  }
}
```

#### 接口名称：获取题目版本链

**请求方式与路径**：`GET /api/v1/questions/{question_id}`

**请求头/鉴权**：`Authorization: Bearer <Token>`

**返回结果**：

```json
{
  "code": 200,
  "data": {
    "question_id": "q_bank_001",
    "versions": [
      {
        "version": 1,
        "version_id": "66112233aa44bb55cc66dd77",
        "type": "ChoiceQuestion",
        "title": "你的年龄段"
      },
      {
        "version": 2,
        "version_id": "77112233aa44bb55cc66dd88",
        "type": "NumberQuestion",
        "title": "你的年龄"
      }
    ]
  }
}
```

#### 接口名称：获取题目指定版本详情

**请求方式与路径**：`GET /api/v1/questions/{question_id}/versions/{version}`

**请求头/鉴权**：`Authorization: Bearer <Token>`

**返回结果**：

```json
{
  "code": 200,
  "data": {
    "question_id": "q_bank_001",
    "version": 2,
    "version_id": "77112233aa44bb55cc66dd88",
    "previous_version_id": "66112233aa44bb55cc66dd77",
    "type": "NumberQuestion",
    "title": "你的年龄",
    "isRequired": true,
    "minValue": 0,
    "maxValue": 120,
    "mustBeInteger": true
  }
}
```

------

### 三、问卷管理与配置模块

#### 接口名称：创建基础问卷

**请求方式与路径**：`POST /api/v1/surveys`

**请求头/鉴权**：`Authorization: Bearer <Token>`

**请求参数**：

```json
{
  "title": "2026年度产品满意度调查",
  "description": "请协助我们改进产品体验",
  "is_anonymous": true,
  "end_time": "2026-04-30T23:59:59Z"
}
```

**返回结果**：

```json
{
  "code": 200,
  "data": {
    "survey_id": "sv_8a9b2c",
    "status": "DRAFT"
  }
}
```

#### 接口名称：获取当前用户问卷列表

**请求方式与路径**：`GET /api/v1/surveys`

**请求头/鉴权**：`Authorization: Bearer <Token>`

#### 接口名称：更新问卷基础信息

**请求方式与路径**：`PATCH /api/v1/surveys/{survey_id}`

**请求头/鉴权**：`Authorization: Bearer <Token>`

#### 接口名称：更新问卷状态（发布/关闭）

**请求方式与路径**：`PATCH /api/v1/surveys/{survey_id}/status`

**请求头/鉴权**：`Authorization: Bearer <Token>`

**请求参数**：

```json
{
  "status": "PUBLISHED"
}
```

------

### 四、问卷题目快照与逻辑编辑模块

#### 接口名称：保存问卷结构与跳转逻辑

**请求方式与路径**：`PUT /api/v1/surveys/{survey_id}/schema`

**请求头/鉴权**：`Authorization: Bearer <Token>`

**请求参数**：

```json
{
  "questions": [
    {
      "questionId": "q_bank_001",
      "version": 2,
      "orderIndex": 1
    },
    {
      "questionId": "q_bank_010",
      "version": 1,
      "orderIndex": 2
    }
  ],
  "logic_rules": [
    {
      "ruleId": "r_001",
      "sourceQuestionId": "q_bank_001",
      "targetQuestionId": "q_bank_010",
      "triggerCondition": "3"
    }
  ]
}
```

**保存语义**：

- 请求中的 `questions` 只声明“问卷使用哪一个题目的哪一个版本，以及它在当前问卷中的顺序”。
- 服务端会读取 `questions` 集合中的对应版本定义，并把当时的题目内容固化到 `surveys.questions[].snapshot` 中。
- 问卷一旦保存完成，后续题库中该题继续升级版本，不会反向修改已保存问卷的 `snapshot`。

**`surveys.questions` 落库结构说明**：

```json
{
  "questionId": "q_bank_001",
  "version": 2,
  "versionId": "77112233aa44bb55cc66dd88",
  "orderIndex": 1,
  "snapshot": {
    "type": "NumberQuestion",
    "title": "你的年龄",
    "isRequired": true,
    "minValue": 0,
    "maxValue": 120,
    "mustBeInteger": true
  }
}
```

**跳转逻辑校验规则**：

1. `sourceQuestionId` 与 `targetQuestionId` 必须存在于当前问卷 `questions` 中。
2. 跳转目标的 `orderIndex` 必须严格大于源题。
3. 同一源题下 `triggerCondition` 不可重复。
4. 若源题快照类型为选择题，`triggerCondition` 必须使用选项行号表示法，多个行号按升序、空格分隔。
5. 选择题跳转仅在“完整组合完全一致”时命中，不允许部分匹配。

#### 接口名称：获取问卷渲染 Schema

**请求方式与路径**：`GET /api/v1/surveys/{survey_id}/schema`

**请求头/鉴权**：无

**返回结果**：

```json
{
  "code": 200,
  "data": {
    "title": "2026年度产品满意度调查",
    "description": "请协助我们改进产品体验",
    "is_anonymous": true,
    "status": "PUBLISHED",
    "questions": [
      {
        "questionId": "q_bank_001",
        "version": 2,
        "orderIndex": 1,
        "snapshot": {
          "type": "NumberQuestion",
          "title": "你的年龄",
          "isRequired": true,
          "minValue": 0,
          "maxValue": 120,
          "mustBeInteger": true
        }
      }
    ],
    "logic_rules": []
  }
}
```

------

### 五、问卷填写与统计模块

#### 接口名称：提交答卷

**请求方式与路径**：`POST /api/v1/surveys/{survey_id}/answers`

**请求头/鉴权**：`Authorization: Bearer <Token>`

**请求参数**：

```json
{
  "submit_as_anonymous": false,
  "payloads": {
    "q_bank_001": 25,
    "q_bank_010": ["满意", "推荐"]
  }
}
```

**校验语义**：

- 所有校验均基于 `surveys.questions[].snapshot` 执行，不访问题库最新版本。
- 错误提示必须使用“第N题”，不能暴露内部 `questionId`。

#### 接口名称：查看问卷统计

**请求方式与路径**：`GET /api/v1/surveys/{survey_id}/statistics`

**请求头/鉴权**：`Authorization: Bearer <Token>`

**统计语义**：

- 统计维度与题型解释均基于问卷快照。
- 不做跨问卷统计，不提供“某题被哪些问卷使用”的查询接口。

### 六、当前实现补充

- Stage 1 没有提供题目删除、恢复旧版本、跨用户分享题目接口。
- `GET /api/v1/surveys/{survey_id}/schema` 返回的是问卷快照，而不是题库实时版本。
- 同一 `questionId` 的多个版本可以同时被不同问卷引用，也可以在同一时刻分别存在于多个已发布问卷中。
