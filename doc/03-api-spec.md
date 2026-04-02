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
- `is_anonymous` (Boolean, 必填): 是否匿名填写。
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

**请求参数**：

聚合提交题目集与逻辑规则集，利用 MongoDB 文档特性整体落库。

JSON

```
{
  "questions": [
    {
      "question_id": "q_001",
      "type": "ChoiceQuestion",
      "is_required": true,
      "order_index": 1,
      "options": ["满意", "一般", "不满意"],
      "min_select": 1,
      "max_select": 1
    },
    {
      "question_id": "q_002",
      "type": "NumberQuestion",
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
      "trigger_condition": "不满意"
    }
  ]
}
```

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
    "message": "参数校验失败: q_001 的最大选择数不能小于最小选择数"
  }
  ```

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
