### 集合：`users`（用户信息表）

**业务用途**：管理问卷发布者与填写者的账号、鉴权与数据隔离。

| 字段名 | BSON类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `_id` | ObjectId | 是 | 自动生成 | 主键 |
| `username` | String | 是 | 无 | 用户名，建议唯一索引 `{ username: 1 }` |
| `passwordHash` | String | 是 | 无 | 密码哈希 |
| `createdAt` | Date | 是 | 当前时间 | 创建时间 |
| `updatedAt` | Date | 是 | 当前时间 | 更新时间 |
| `isDeleted` | Boolean | 否 | false | 软删除标识 |

------

### 集合：`questions`（题库版本表）

**业务用途**：独立存储题目定义，支撑题目复用、版本隔离、版本历史、多版本共存、跨用户共享访问与个人题库管理。

**模型设计策略**：采用“稳定业务主键 + 版本文档”设计。`questionId` 表示逻辑题目身份，单条文档表示该题的一个具体版本。问卷不直接引用“最新题目”，而是引用某个确定版本并在问卷中保存快照。

| 字段名 | BSON类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `_id` | ObjectId | 是 | 自动生成 | 当前版本文档主键，也可视为 `versionId` |
| `questionId` | String | 是 | 无 | 稳定题目标识，同一题目的所有版本共享 |
| `userId` | ObjectId | 是 | 无 | 题目所有者；Stage 1 不支持分享 |
| `version` | Int32 | 是 | 无 | 从 1 开始递增 |
| `previousVersionId` | ObjectId/null | 否 | null | 指向上一版本，形成 `v1 -> v2 -> v3` 链 |
| `versionChainRootId` | ObjectId | 是 | 无 | 指向首版本 `_id`，方便按整条版本链查询 |
| `sharedWith` | Array | 否 | [] | 共享授权列表，按 `questionId` 维度在所有版本上保持一致 |
| ├── `userId` | ObjectId | 是 | 无 | 被共享用户 ID |
| ├── `sharedAt` | Date | 是 | 当前时间 | 共享建立时间 |
| `libraryMembers` | Array | 否 | [] | 已将该题加入题库的用户列表，按 `questionId` 维度在所有版本上保持一致 |
| ├── `userId` | ObjectId | 是 | 无 | 题库所属用户 ID |
| ├── `addedAt` | Date | 是 | 当前时间 | 加入题库时间 |
| `type` | String | 是 | 无 | `ChoiceQuestion` / `TextQuestion` / `NumberQuestion` |
| `title` | String | 是 | 无 | 题目标题 |
| `isRequired` | Boolean | 是 | true | 必答标识 |
| `options` | Array | 否 | [] | 选择题选项列表 |
| `minSelect` / `maxSelect` | Int32 | 否 | null | 选择题数量限制 |
| `minLength` / `maxLength` | Int32 | 否 | null | 文本题长度限制 |
| `minValue` / `maxValue` | Double | 否 | null | 数字题范围限制 |
| `mustBeInteger` | Boolean | 否 | false | 数字题整数约束 |
| `createdAt` | Date | 是 | 当前时间 | 该版本创建时间 |
| `updatedAt` | Date | 是 | 当前时间 | 该版本更新时间 |

**索引建议**：

- `{ userId: 1, questionId: 1 }`
- `{ questionId: 1, version: 1 }` 唯一索引
- `{ versionChainRootId: 1, version: 1 }`
- `{ questionId: 1, "sharedWith.userId": 1 }`
- `{ questionId: 1, "libraryMembers.userId": 1 }`

------

### 集合：`surveys`（问卷配置与快照表）

**业务用途**：存储问卷元数据、问卷使用的题目版本引用，以及保存时固化的题目快照和跳转规则。

**模型设计策略**：采用“引用 + 快照”的混合设计。问卷中的每一道题都绑定某个题目版本，但同时内嵌快照内容，确保后续题库继续升级时，旧问卷内容保持稳定。

| 字段名 | BSON类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `_id` | ObjectId | 是 | 自动生成 | 问卷主键 |
| `userId` | ObjectId | 是 | 无 | 创建者，建议索引 `{ userId: 1, createdAt: -1 }` |
| `title` | String | 是 | 无 | 问卷标题 |
| `description` | String | 否 | "" | 问卷说明 |
| `is_anonymous` | Boolean | 是 | false | 是否允许匿名提交 |
| `status` | String | 是 | `DRAFT` | `DRAFT` / `PUBLISHED` / `CLOSED` |
| `end_time` | Date/null | 否 | null | 截止时间 |
| `questions` | Array | 是 | [] | 问卷题目快照数组 |
| ├── `questionId` | String | 是 | 无 | 稳定题目标识 |
| ├── `version` | Int32 | 是 | 无 | 问卷绑定的题目版本号 |
| ├── `versionId` | ObjectId | 是 | 无 | 该快照来源的题目版本文档 `_id` |
| ├── `orderIndex` | Int32 | 是 | 无 | 题目在当前问卷中的顺序 |
| ├── `snapshot` | Object | 是 | 无 | 当前问卷固化的题目内容 |
| │   ├── `type` | String | 是 | 无 | 快照题型 |
| │   ├── `title` | String | 是 | 无 | 快照标题 |
| │   ├── `isRequired` | Boolean | 是 | true | 快照必答标识 |
| │   ├── `options` | Array | 否 | [] | 选择题选项 |
| │   ├── `minSelect` / `maxSelect` | Int32 | 否 | null | 选择数量限制 |
| │   ├── `minLength` / `maxLength` | Int32 | 否 | null | 文本长度限制 |
| │   ├── `minValue` / `maxValue` | Double | 否 | null | 数字范围限制 |
| │   ├── `mustBeInteger` | Boolean | 否 | false | 数字整数约束 |
| `logicRules` | Array | 是 | [] | 问卷跳转规则 |
| ├── `ruleId` | String | 是 | 无 | 规则业务标识 |
| ├── `sourceQuestionId` | String | 是 | 无 | 源题 questionId |
| ├── `targetQuestionId` | String | 是 | 无 | 目标题 questionId |
| ├── `triggerCondition` | String | 是 | 无 | 标准化触发条件 |
| `createdAt` | Date | 是 | 当前时间 | 创建时间 |
| `updatedAt` | Date | 是 | 当前时间 | 更新时间 |

**关键约束**：

- `surveys.questions.snapshot` 是后续填写、渲染、统计的唯一真值来源。
- 修改题库中的题目版本不会自动修改任何已存在问卷的快照。
- 问卷可以同时引用同一 `questionId` 的不同版本，只要 `questionId + version` 组合明确且顺序合法。
- 问卷装配题目时，允许引用“自己拥有的题目版本”或“别人共享给自己的题目版本”。

------

### 集合：`answers`（答卷明细表）

**业务用途**：记录填写者提交的问卷答案，并基于问卷快照进行单问卷统计与跨问卷统计。

| 字段名 | BSON类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `_id` | ObjectId | 是 | 自动生成 | 主键 |
| `surveyId` | ObjectId | 是 | 无 | 问卷引用，建议索引 `{ surveyId: 1, submittedAt: -1 }` |
| `respondentId` | Mixed | 是 | 无 | 实名时为用户 ObjectId，匿名时为 `-1` |
| `isAnonymousSubmission` | Boolean | 是 | false | 是否匿名提交 |
| `payloads` | Object | 是 | {} | 键为 `questionId`，值为答案 |
| `submittedAt` | Date | 是 | 当前时间 | 真实提交时间 |
| `createdAt` | Date | 是 | 当前时间 | 创建时间 |
| `updatedAt` | Date | 是 | 当前时间 | 更新时间 |

**说明**：

- `payloads` 继续使用 `questionId` 作为键，因为问卷快照内部的 `questionId` 在单份问卷内保持稳定。
- 单问卷统计与跨问卷统计都必须结合问卷快照解释答案，而不能回查题库最新版本。

------

### 四、MongoDB 设计决策说明

**1. 为什么从内嵌题目改成独立存储？**

第一阶段的“题目内嵌在问卷中”设计适合快速交付，但无法满足题目复用、版本链、修改历史和多版本共存。只要题目需要跨问卷复用，就必须把“题目定义”从“问卷实例”中抽离出来。

**2. 为什么仍然保留问卷内的快照？**

如果问卷只保存题目引用，不保存快照，那么题库中题目一旦升级，已发布问卷和旧答卷的语义就会漂移。Stage 1 的核心要求恰恰是版本隔离，因此问卷必须同时保存“引用哪个版本”和“当时的快照内容”。

**3. 为什么这个设计适合 MongoDB？**

- `questions` 集合适合存放版本化文档，每个版本天然就是一条独立文档。
- `sharedWith` 与 `libraryMembers` 都适合直接内嵌在题目版本文档中。它们都与逻辑题目强相关，且当前阶段不需要独立题库集合或复杂授权表。
- `surveys.questions` 中的 `snapshot` 适合使用 MongoDB 的内嵌文档表达，不需要联表即可完成填写和统计。
- “题库存版本、共享权限与题库标记，问卷存快照，答卷存动态 payload”形成了清晰的聚合边界，既满足演化需求，也保留读取效率。

### 五、当前实现补充说明

- 当前代码不会自动创建索引，也不会自动执行 MongoDB 分片配置。
- Stage 4 已支持题目分享、题目使用查询、题库管理与跨问卷统计，但仍不支持题库管理页面。
- 当前 `surveys` 集合实际继续使用字段名 `is_anonymous`、`end_time`、`logicRules`，与现有代码风格保持一致。
