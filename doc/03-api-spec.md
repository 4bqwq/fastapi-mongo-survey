### 一、 用户账号模块

#### 接口名称：用户注册

**请求方式与路径**：`POST /api/v1/auth/register`

**请求头/鉴权**：无

**请求参数**：

JSON

```
{
  "username": "test_user",
  "password": "secure_password_123"
}
```

- `username` (String, 必填): 用户名，需唯一。
- `password` (String, 必填): 密码。

**返回结果**：

- **成功 (200 OK)**:

  JSON

  ```
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

- **失败 (400 Bad Request)**:

  JSON

  ```
  {
    "code": 40001,
    "message": "用户名已存在"
  }
  ```

#### 接口名称：用户登录

**请求方式与路径**：`POST /api/v1/auth/login`

**请求头/鉴权**：无

**请求参数**：

JSON

```
{
  "username": "test_user",
  "password": "secure_password_123"
}
```

**返回结果**：

- **成功 (200 OK)**:

  JSON

  ```
  {
    "code": 200,
    "message": "success",
    "data": {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR...",
      "token_type": "Bearer"
    }
  }
  ```

- **失败 (401 Unauthorized)**:

  JSON

  ```
  {
    "code": 40101,
    "message": "用户名或密码错误"
  }
  ```

------

### 二、 问卷管理与配置模块

#### 接口名称：创建基础问卷

**请求方式与路径**：`POST /api/v1/surveys`

**请求头/鉴权**：`Authorization: Bearer <Token>` (发布者权限)

**请求参数**：

JSON

```
{
  "title": "2026年度产品满意度调查",
  "description": "请协助我们改进产品体验",
  "is_anonymous": true,
  "end_time": "2026-04-30T23:59:59Z"
}
```

- `title` (String, 必填): 问卷标题。
- `description` (String, 非必填): 问卷说明。
- `is_anonymous` (Boolean, 必填): 是否允许填写者在提交时选择匿名。
- `end_time` (DateTime, 非必填): 截止时间。

**返回结果**：

- **成功 (200 OK)**:

  JSON

  ```
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

**返回结果**：

- **成功 (200 OK)**:

  JSON

  ```
  {
    "code": 200,
    "data": [
      {
        "survey_id": "sv_8a9b2c",
        "title": "2026年度产品满意度调查",
        "description": "请协助我们改进产品体验",
        "status": "DRAFT",
        "is_anonymous": true,
        "end_time": "2026-04-30T23:59:59Z",
        "created_at": "2026-04-02T16:22:25Z"
      }
    ]
  }
  ```

#### 接口名称：更新问卷基础信息

**请求方式与路径**：`PATCH /api/v1/surveys/{survey_id}`

**请求头/鉴权**：`Authorization: Bearer <Token>` (需为该问卷创建者)

**请求参数**：

JSON

```
{
  "title": "2026年度产品满意度调查（第二版）",
  "description": "请在截止前完成填写",
  "is_anonymous": true,
  "end_time": "2026-05-15T23:59:59Z"
}
```

- `title` (String, 非必填): 问卷标题。
- `description` (String, 非必填): 问卷说明。
- `is_anonymous` (Boolean, 非必填): 是否允许填写者匿名提交。
- `end_time` (DateTime, 可空): 截止时间；传 `null` 表示清空。

**返回结果**：

- **成功 (200 OK)**:

  JSON

  ```
  {
    "code": 200,
    "data": {
      "survey_id": "sv_8a9b2c",
      "title": "2026年度产品满意度调查（第二版）",
      "description": "请在截止前完成填写",
      "is_anonymous": true,
      "end_time": "2026-05-15T23:59:59Z"
    }
  }
  ```

#### 接口名称：更新问卷状态（发布/关闭）

**请求方式与路径**：`PATCH /api/v1/surveys/{survey_id}/status`

**请求头/鉴权**：`Authorization: Bearer <Token>` (需为该问卷创建者)

**请求参数**：

JSON

```
{
  "status": "PUBLISHED"
}
```

- `status` (String, 必填): 目标状态，枚举值为 `PUBLISHED` 或 `CLOSED`。

**返回结果**：

- **成功 (200 OK)**:

  JSON

  ```
  {
    "code": 200,
    "data": {
      "survey_id": "sv_8a9b2c",
      "status": "PUBLISHED",
      "access_url": "/survey/sv_8a9b2c"
    }
  }
  ```

- **失败 (403 Forbidden)**:

  JSON

  ```
  {
    "code": 40301,
    "message": "无权操作此问卷"
  }
  ```

------

### 三、 题目与逻辑编辑模块

#### 接口名称：保存问卷结构与跳转逻辑

**请求方式与路径**：`PUT /api/v1/surveys/{survey_id}/schema`

**请求头/鉴权**：`Authorization: Bearer <Token>` (需为该问卷创建者)

**跳转逻辑校验规则**：
1. **单向性**：目标题目的 `orderIndex` 必须严格大于源题目的 `orderIndex`。
2. **唯一性**：同一源题目下，触发条件 `triggerCondition` 不可重复。
3. **存在性**：目标题目 ID 必须在提交的 `questions` 列表中存在。
4. **选择题格式**：若源题为选择题，`triggerCondition` 必须填写为选项行号组合，行号从 `1` 开始，多个行号以空格分隔。
5. **选择题完整匹配**：若源题为选择题，只有当填写者的最终选择与 `triggerCondition` 完全一致时才触发跳转。
6. **选择题合法性**：选择题 `triggerCondition` 中的行号不得重复，且不得超出选项总行数；若当前题是单选题，则只能配置一个行号。

**请求参数**：

JSON

```
{
  "questions": [
    {
      "questionId": "q_001",
      "type": "ChoiceQuestion",
      "title": "第1题标题",
      "isRequired": true,
      "orderIndex": 1,
      "options": ["满意", "一般", "不满意"],
      "minSelect": 1,
      "maxSelect": 1
    },
    {
      "questionId": "q_002",
      "type": "NumberQuestion",
      "title": "第2题标题",
      "isRequired": false,
      "orderIndex": 2,
      "minValue": 1,
      "maxValue": 100,
      "mustBeInteger": true
    }
  ],
  "logic_rules": [
    {
      "ruleId": "r_001",
      "sourceQuestionId": "q_001",
      "targetQuestionId": "q_003",
      "triggerCondition": "3"
    }
  ]
}
```

**`triggerCondition` 说明**：

- 选择题：使用选项行号组合，统一按升序、空格分隔，例如 `1`、`1 3`。
- 数字题：当前实现直接使用具体数值文本。

**返回结果**：

- **成功 (200 OK)**:

  JSON

  ```
  {
    "code": 200,
    "message": "Schema updated successfully"
  }
  ```

- **失败 (422 Unprocessable Entity)**:

  JSON

  ```
  {
    "code": 42201,
    "message": "第1题 的最大选择数不能小于最小选择数"
  }
  ```

**错误提示约束**：

- 所有题目相关报错都使用“第N题”顺序编号，不暴露内部 `questionId`。

------

### 四、 问卷填写与校验模块

#### 接口名称：获取问卷渲染配置 (Schema)

**请求方式与路径**：`GET /api/v1/surveys/{survey_id}/schema`

**请求头/鉴权**：当前实现不强制要求登录。

**请求参数**：无

**返回结果**：

- **成功 (200 OK)**:

  JSON

  ```
  {
    "code": 200,
    "data": {
      "title": "2026年度产品满意度调查",
      "description": "请协助我们改进产品体验",
      "is_anonymous": true,
      "status": "PUBLISHED",
      "end_time": "2026-04-30T23:59:59Z",
      "questions": [
        {
          "questionId": "q_001",
          "type": "ChoiceQuestion",
          "title": "第1题标题",
          "isRequired": true,
          "orderIndex": 1,
          "options": ["满意", "一般", "不满意"],
          "minSelect": 1,
          "maxSelect": 1
        }
      ],
      "logic_rules": []
    }
  }
  ```

**实现说明**：

- 当前实现即使问卷状态不是 `PUBLISHED`，也仍然会返回 schema。
- 当前实现不会因为问卷已截止而在本接口返回 `403`。

#### 接口名称：提交问卷答卷

**请求方式与路径**：`POST /api/v1/surveys/{survey_id}/answers`

**请求头/鉴权**：`Authorization: Bearer <Token>` (填写者必须登录)

**请求参数**：

JSON

```
{
  "submit_as_anonymous": true,
  "payloads": {
    "q_001": ["满意"],
    "q_002": 88,
    "q_003": "体验很好"
  }
}
```

- `submit_as_anonymous` (Boolean, 非必填): 是否以匿名方式提交。仅当问卷允许匿名时可传 `true`。
- `payloads` (Object, 必填): 作答内容。选择题为数组，文本题为字符串，数字题为数值。

**服务端校验要求**：

- 问卷未发布、已关闭或已超过截止时间时拒绝提交。
- 文本题校验最少字数、最多字数。
- 数字题校验最小值、最大值与整数约束。
- 选择题校验最少选择数、最多选择数。
- 所有错误提示都使用“第N题”格式。

**业务校验逻辑补充**：
1. 系统根据跳转逻辑推演用户实际可见的题目路径，仅对路径内的必答题执行非空校验。
2. 若本次提交选择匿名，`respondentId` 记录为 `-1`；否则记录当前登录用户的 ID。

**返回结果**：

- **成功 (200 OK)**:

  JSON

  ```
  {
    "code": 200,
    "data": {
      "answer_id": "ans_998877",
      "submitted_at": "2026-04-02T16:30:00Z"
    }
  }
  ```

- **失败 (422 Unprocessable Entity)**:

  JSON

  ```
  {
    "code": 42205,
    "message": "第2题 的数值不能大于 50"
  }
  ```

------

### 五、 数据统计模块

#### 接口名称：获取问卷数据统计

**请求方式与路径**：`GET /api/v1/surveys/{survey_id}/statistics`

**请求头/鉴权**：`Authorization: Bearer <Token>` (需为该问卷创建者)

**请求参数**：无

**返回结果**：

- **成功 (200 OK)**:

  JSON

  ```
  {
    "code": 200,
    "data": {
      "macro_stats": {
        "total_respondents": 156
      },
      "micro_stats": {
        "q_001": {
          "type": "ChoiceQuestion",
          "title": "第1题标题",
          "total_answers": 156,
          "distribution": {
            "满意": 100,
            "一般": 40,
            "不满意": 16
          }
        },
        "q_002": {
          "type": "NumberQuestion",
          "title": "第2题标题",
          "valid_answers": 150,
          "average_value": 78.5,
          "text_list": [
            "80",
            "76.5"
          ]
        },
        "q_003": {
          "type": "TextQuestion",
          "title": "第3题标题",
          "total_answers": 20,
          "text_list": [
            "UI很好看",
            "希望能增加护眼模式"
          ]
        }
      }
    }
  }
  ```

**实现说明**：

- 选择题返回选项分布。
- 数字题返回平均值和明细列表，明细列表当前最多返回 50 条，且按字符串形式输出。
- 文本题返回明细列表，当前最多返回 20 条。
