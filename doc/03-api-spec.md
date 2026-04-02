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
1. **单向性**：目标题目的 `order_index` 必须严格大于源题目的 `order_index`。
2. **唯一性**：同一源题目下，触发条件 (`trigger_condition`) 不可重复。
3. **存在性**：目标题目 ID 必须在提交的 `questions` 列表中存在。
4. **选择题格式**：若源题为单选题或多选题，`trigger_condition` 必须填写为选项行号组合，行号从 `1` 开始，多个行号以空格分隔，例如 `1 3`。
5. **选择题完整匹配**：若源题为单选题或多选题，只有当填写者的最终选择与 `trigger_condition` 完全一致时才触发跳转。
6. **选择题合法性**：选择题 `trigger_condition` 中的行号不得重复，且不得超出选项总行数；单选题只能配置一个行号。

**请求参数**：

聚合提交题目集与逻辑规则集，利用 MongoDB 文档特性整体落库。

JSON

```
{
  "questions": [
    {
      "question_id": "q_001",
      "type": "ChoiceQuestion",
      "title": "第1题标题",
      "is_required": true,
      "order_index": 1,
      "options": ["满意", "一般", "不满意"],
      "min_select": 1,
      "max_select": 1
    },
    {
      "question_id": "q_002",
      "type": "NumberQuestion",
      "title": "第2题标题",
      "is_required": false,
      "order_index": 2,
      "min_value": 1,
      "max_value": 100,
      "must_be_integer": true
    }
  ],
  "logic_rules": [
    {
      "rule_id": "r_001",
      "source_question_id": "q_001",
      "target_question_id": "q_003",
      "trigger_condition": "3"
    }
  ]
}
```

**`trigger_condition` 说明**：

- 单选题/多选题：使用选项行号组合，统一按升序、空格分隔。例如 `1`、`1 3`。
- 数字题：继续使用具体数值文本。

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
    "message": "参数校验失败: 第1题的最大选择数不能小于最小选择数"
  }
  ```

**错误提示约束**：

- 所有题目相关报错必须使用“第N题”顺序编号，不得暴露内部 `question_id`。
- 选择题跳转条件填写错误时，报错信息需明确指出是第几题的行号格式、重复行号或越界问题。

------

### 四、 问卷填写与校验模块

#### 接口名称：获取问卷渲染配置 (Schema)

**请求方式与路径**：`GET /api/v1/surveys/{survey_id}/schema`

**请求头/鉴权**：`Authorization: Bearer <Token>` (填写者必须登录)

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
      "questions": [
        {
          "question_id": "q_001",
          "type": "ChoiceQuestion",
          "title": "第1题标题",
          "is_required": true,
          "order_index": 1,
          "options": ["满意", "一般", "不满意"],
          "min_select": 1,
          "max_select": 1
        }
      ],
      "logic_rules": []
    }
  }
  ```

- **失败 (403 Forbidden)**:

  JSON

  ```
  {
    "code": 40302,
    "message": "该问卷已关闭或已逾期"
  }
  ```

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
- `payloads` (Object, 必填): 作答内容。

**服务端校验要求**：

- 问卷未发布、已关闭或已超过截止时间时必须拒绝提交。
- 文本题需校验最少字数、最多字数。
- 数字题需校验最小值、最大值与整数约束。
- 所有错误提示必须使用“第N题”格式。

**请求头/鉴权**：`Authorization: Bearer <Token>` (强制要求登录)

**业务校验逻辑补充**：
1. **基于路径的必答校验**：系统根据跳转逻辑推演用户实际可见的题目路径，仅对路径内的必答题执行非空校验。
2. **身份标识**：
    - 若问卷开启匿名 (`is_anonymous: true`)，`respondent_id` 统一记录为 `-1`。
    - 若问卷未开启匿名，`respondent_id` 记录当前登录用户的 ID。

**请求参数**：

JSON

```
{
  "payloads": {
    "q_001": ["满意"],
    "q_002": 85,
    "q_003": "产品界面非常友好，但加载速度稍慢。"
  }
}
```

- `payloads` (Map, 必填): 题目ID到回答内容的键值对。单/多选为数组，填空为字符串，数字为数值。

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
    "message": "服务端二次校验失败: q_002 输入值(85)超过设定最大值(50)"
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
          "total_answers": 156,
          "distribution": {
            "满意": 100,
            "一般": 40,
            "不满意": 16
          }
        },
        "q_002": {
          "type": "NumberQuestion",
          "valid_answers": 150,
          "average_value": 78.5
        },
        "q_003": {
          "type": "TextQuestion",
          "total_answers": 45,
          "text_list": [
            "UI很好看",
            "希望能增加护眼模式"
          ]
        }
      }
    }
  }
  ```

- **失败 (403 Forbidden)**:

  JSON

  ```
  {
    "code": 40301,
    "message": "无权查看此问卷的统计数据"
  }
  ```
