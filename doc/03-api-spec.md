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

### 二、题目库、共享与版本控制模块

Stage 4 在 Stage 3 的基础上新增“跨问卷统计”，支持按 `questionId` 汇总该题在多个问卷中的回答情况。

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

- `base_version` 必须存在且当前用户对该题具有所有权。
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

**说明**：

- 所有者可以查看自己题目的全部版本链。
- 被共享用户也可以查看被共享题目的版本链，用于在问卷中选择具体版本。

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

#### 接口名称：共享题目给指定用户

**请求方式与路径**：`POST /api/v1/questions/{question_id}/shares`

**请求头/鉴权**：`Authorization: Bearer <Token>`

**请求参数**：

```json
{
  "username": "teammate_user"
}
```

**说明**：

- 只有题目所有者可以发起共享。
- 共享关系对同一 `questionId` 的整个版本链生效，而不是只对单个版本生效。
- 共享后，被共享用户拥有“查看版本详情 + 在自己问卷中使用”的权限，但没有创建新版本或继续转授的权限。

**返回结果**：

```json
{
  "code": 200,
  "data": {
    "question_id": "q_bank_001",
    "shared_with": [
      {
        "user_id": "6611aa22bb33cc44dd55ee66",
        "username": "teammate_user"
      }
    ]
  }
}
```

#### 接口名称：查看题目共享列表

**请求方式与路径**：`GET /api/v1/questions/{question_id}/shares`

**请求头/鉴权**：`Authorization: Bearer <Token>`

**说明**：

- 只有题目所有者可以查看共享列表。

#### 接口名称：查看题目被哪些问卷使用

**请求方式与路径**：`GET /api/v1/questions/{question_id}/usage`

**请求头/鉴权**：`Authorization: Bearer <Token>`

**说明**：

- 题目所有者可以查看该题被所有问卷引用的情况，包括其他被共享用户创建的问卷。
- 被共享用户也可以查看该题的使用列表，但只能查看自己已经有权限使用的题。
- 返回结果按问卷维度展开，并标明使用的 `version`。

**返回结果**：

```json
{
  "code": 200,
  "data": {
    "question_id": "q_bank_001",
    "usages": [
      {
        "survey_id": "6622aa33bb44cc55dd66ee77",
        "survey_title": "2026年度产品满意度调查",
        "survey_owner_id": "55aa66bb77cc88dd99ee00ff",
        "survey_owner_username": "teammate_user",
        "status": "PUBLISHED",
        "question_version": 2,
        "order_index": 1
      }
    ]
  }
}
```

#### 接口名称：加入题库

**请求方式与路径**：`POST /api/v1/questions/{question_id}/library`

**请求头/鉴权**：`Authorization: Bearer <Token>`

**说明**：

- 当前用户可以把“自己拥有的题”或“别人共享给自己的题”加入自己的题库。
- 题库标记按 `questionId` 生效，对该逻辑题的全部版本保持一致。

**返回结果**：

```json
{
  "code": 200,
  "data": {
    "question_id": "q_bank_001",
    "in_library": true
  }
}
```

#### 接口名称：移出题库

**请求方式与路径**：`DELETE /api/v1/questions/{question_id}/library`

**请求头/鉴权**：`Authorization: Bearer <Token>`

**说明**：

- 只移除当前用户自己的题库标记，不删除题目实体，也不影响共享关系和已存在问卷。

#### 接口名称：浏览我的题库

**请求方式与路径**：`GET /api/v1/questions/library`

**请求头/鉴权**：`Authorization: Bearer <Token>`

**说明**：

- 返回当前用户题库中的全部逻辑题，覆盖“自己创建的题”和“别人共享给自己且已加入题库的题”。
- 每个逻辑题以题目维度返回一条摘要，而不是按版本重复展开。

**返回结果**：

```json
{
  "code": 200,
  "data": {
    "questions": [
      {
        "question_id": "q_bank_001",
        "owner_user_id": "6611aa22bb33cc44dd55ee66",
        "owner_username": "teacher_user",
        "latest_version": 2,
        "latest_title": "你的年龄",
        "type": "NumberQuestion",
        "is_shared": true,
        "in_library": true
      }
    ]
  }
}
```

#### 接口名称：查看题目的跨问卷统计

**请求方式与路径**：`GET /api/v1/questions/{question_id}/statistics`

**请求头/鉴权**：`Authorization: Bearer <Token>`

**说明**：

- 只有题目所有者和已获共享权限的用户可以查看。
- 统计按 `questionId` 聚合该题在所有引用问卷中的回答。
- 若该题在不同问卷快照中存在多种题型版本，接口返回 422，拒绝做统一统计。

**选择题返回示例**：

```json
{
  "code": 200,
  "data": {
    "question_id": "q_bank_001",
    "type": "ChoiceQuestion",
    "title": "你的年龄段",
    "survey_count": 3,
    "total_answers": 120,
    "distribution": {
      "18岁以下": 12,
      "18-25岁": 55,
      "26-35岁": 38,
      "36岁及以上": 15
    }
  }
}
```

**数字题返回示例**：

```json
{
  "code": 200,
  "data": {
    "question_id": "q_bank_002",
    "type": "NumberQuestion",
    "title": "你的年龄",
    "survey_count": 4,
    "valid_answers": 86,
    "average_value": 27.35,
    "distribution": {
      "18": 3,
      "19": 5,
      "20": 8
    },
    "text_list": ["18", "19", "20"]
  }
}
```

**文本题返回示例**：

```json
{
  "code": 200,
  "data": {
    "question_id": "q_bank_003",
    "type": "TextQuestion",
    "title": "你的建议",
    "survey_count": 2,
    "total_answers": 37,
    "text_list": ["希望优化加载速度", "增加导出功能"]
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
- 若某题来自共享，服务端会先校验当前用户是否对该 `questionId` 拥有共享使用权限，再允许装配进问卷。

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

- Stage 4 没有提供题目删除、恢复旧版本、题库管理页面接口。
- `GET /api/v1/surveys/{survey_id}/schema` 返回的是问卷快照，而不是题库实时版本。
- 同一 `questionId` 的多个版本可以同时被不同问卷引用，也可以在同一时刻分别存在于多个已发布问卷中。
