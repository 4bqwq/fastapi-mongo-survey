# 1

```
问卷系统第一阶段已完成，题目以内嵌方式存在于问卷中。根据用户反馈的新使用场景，需要对题目管理方式进行根本性改造。
  
**核心目标：**
  
让题目独立存储，支持版本控制，问卷通过快照副本引用题目。具体包括：
1. 题目复用 — 题目保存到题库，可被多个问卷使用
2. 版本隔离 — 修改题目不影响已发布的问卷
3. 修改历史 — 题目版本形成 v1→v2→v3 的链表
4. 多版本共存 — 同一题目的不同版本可同时存在
  
**本阶段不包含的内容：**
  
题目分享给其他用户、题库管理页面、跨问卷统计、题目使用查询。这些属于后续stage。
  
**项目整体计划：**
  
本次只做stage 1（题目独立存储+版本控制+问卷快照引用），后续还有stage 2（题目分享）、stage 3（题库管理页面）、stage 4（跨问卷统计）。
  
**核心原则（必须严格遵循）：**
  
文档与代码必须保持同步。整个开发过程遵循“先文档、后代码、再验证”的工作流程：先理解并更新需求文档和设计文档，再据此修改代码，最后确认代码实现与文档描述是否一致。先把doc/下所有文档全部同步，再改代码。
  
**建议的执行思路：**
  
1. 阅读需求文档（大作业一.md、大作业一：需求变更.md）理解题目独立存储和版本控制的需求
2. 阅读现有代码（app/models/survey.py、app/api/surveys.py、doc/04-db-design.md）理解当前实现
3. 更新doc/下所有受影响的文档（数据库设计、架构设计、API规格说明），确保文档准确反映新的系统设计
4. 根据文档实施代码改造（新建Question模型和question_service、修改survey模型适配快照引用、创建questions API）
5. 编写测试验证功能（题目创建、版本升级、问卷快照保存、版本隔离）
6. 反向验证代码是否忠实实现了文档描述，确认文档与代码一致
  
我不会为你限定具体的开发步骤和细节，请基于上述原则自行规划任务和执行顺序。
当前已通过 docker compose 启动 Docker 环境，可供直接使用进行测试。请注意，所有 Python 代码及依赖必须通过 uv 进行管理（安装、运行等），否则环境无法识别或运行相关代码。
  
**完成后请说明：**
  
新增/修改了哪些文件、questions集合的设计、surveys.questions的新结构、测试覆盖的场景、代码和文档是否一致。
```

回答：

```
# 结果

本次 stage 1 已完成，文档先行同步后再完成代码改造，并已通过 uv run pytest 全量验证，结果为 11 passed。

# 改动范围

新增了题目版本化相关代码：app/models/question.py、app/services/question_service.py、app/api/questions.py。

重构了问卷与填写主链路：app/models/survey.py、app/api/surveys.py、app/api/answers.py、app/main.py。

同步更新了文档：doc/01-prd.md、doc/02-architecture.md、doc/03-api-spec.md、doc/04-db-design.md、doc/05-test-cases.md、doc/07-frontend-spec.md。

测试侧更新了现有用例并新增版本隔离专项测试：tests/test_questions.py、tests/test_editor.py、tests/test_filling.py、tests/test_stats.py、tests/test_e2e.py、tests/test_extreme.py、tests/test_surveys.py。

# 数据设计

questions 集合现在是"题目版本表"，每条文档代表一个具体版本，核心字段是 questionId、version、previousVersionId、versionChainRootId，再加当前版本的题目内容。实现位置在 app/services/question_service.py:26 和 app/api/questions.py:18。这满足了题目独立存储、版本链、修改历史和多版本共存。

surveys.questions 已不再存内嵌题目原始定义，而是改为"版本引用 + 快照"结构，保存逻辑在 app/api/surveys.py:177。单题结构是：

- questionId
- version
- versionId
- orderIndex
- snapshot

snapshot 内保存当次装配进问卷时的题面、校验规则和题型配置。后续填写和统计都只认这个快照，不回源题库最新版本，相关实现分别在 app/api/answers.py:75 和 app/api/surveys.py:255。

# 接口与行为

新增了 questions API：

- POST /api/v1/questions
- POST /api/v1/questions/{question_id}/versions
- GET /api/v1/questions/{question_id}
- GET /api/v1/questions/{question_id}/versions/{version}

问卷保存 schema 时，现在提交的是 questionId + version + orderIndex，后端会读取对应题目版本并固化快照，见 app/api/surveys.py:201。

跳转规则仍保留在问卷侧，但校验目标已切为问卷快照，选择题仍采用"行号完整匹配"，见 app/api/surveys.py:29。

# 测试覆盖

本次测试覆盖了这些场景：

- 题目首版本创建、基于旧版本创建新版本、版本链查询、版本详情查询。
- 问卷保存时按题目版本生成快照。
- 同一题目的 v1 和 v2 被不同问卷同时引用，旧问卷快照不漂移。
- 填写校验继续覆盖必答、文本长度、数字范围、整数约束、匿名提交、截止时间、关闭状态。
- 跳转逻辑继续覆盖选择题完整组合匹配。
- 统计继续覆盖选择题分布、数字题均值与明细。
- 边界值与并发风格提交继续可用。
- 端到端主路径仍然可跑通。

验证命令是 uv run pytest，结果 11 passed。

# 一致性结论

代码和文档现在是一致的，且已经按"先文档、后代码、再验证"的顺序完成。

Stage 1 的范围也已经严格收口到"题目独立存储 + 版本控制 + 问卷快照引用"，没有实现题目分享、题库管理页面、跨问卷统计、题目使用查询。


On branch main
Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
        modified:   app/api/answers.py
        new file:   app/api/questions.py
        modified:   app/api/surveys.py
        modified:   app/main.py
        new file:   app/models/question.py
        modified:   app/models/survey.py
        new file:   app/services/question_service.py
        modified:   doc/01-prd.md
        modified:   doc/02-architecture.md
        modified:   doc/03-api-spec.md
        modified:   doc/04-db-design.md
        modified:   doc/05-test-cases.md
        modified:   doc/07-frontend-spec.md
        modified:   tests/test_e2e.py
        modified:   tests/test_editor.py
        modified:   tests/test_extreme.py
        modified:   tests/test_filling.py
        new file:   tests/test_questions.py
        modified:   tests/test_stats.py
        modified:   tests/test_surveys.py
```

# 2

```
## 背景

Stage 1 已完成：题目独立存储、版本控制、问卷快照引用。题目现在存在 questions 集合，每条文档是一个版本，问卷中保存版本快照。

## 本阶段范围

**核心目标**：让用户可以把题目分享给其他用户，并查看某题被哪些问卷使用。

具体实现以下需求：

1. **题目分享（需求二）** — 用户可以把题目共享给指定的其他用户，被分享的用户可以在自己的问卷里使用这些题目，共享后仍然继续使用同一个题目（不是复制，是共享访问权）
2. **使用查询（需求六）** — 用户可以查看某个题被哪些问卷使用，了解题目的使用情况

**不包含在本阶段**：

- 题库管理页面（需求七）
- 跨问卷统计（需求八）

## 项目整体计划

- **Stage 1（已完成）**：题目独立存储 + 版本控制 + 问卷快照引用
- **Stage 2（本次）**：题目分享 + 使用查询
- **Stage 3**：题库管理页面
- **Stage 4**：跨问卷统计

## 核心原则

文档与代码必须保持同步。整个开发过程遵循"先文档、后代码、再验证"的工作流程：先更新需求文档和设计文档，再据此修改代码，最后确认代码实现与文档描述是否一致。

## 执行思路（仅供参考，具体步骤自行规划）

1. 理解需求：阅读大作业一：需求变更.md 中需求二和需求六，理解分享和使用查询的业务场景
2. 阅读代码：查看 app/models/question.py 和 app/services/question_service.py，理解现有题目模型和服务
3. 更新文档：同步更新 doc/ 下受影响的文档（数据库设计、API规格说明等）
4. 实施改造：扩展 question_service 和 questions API，支持分享权限和使用查询
5. 编写测试：验证分享功能和使用查询功能
6. 验证：运行测试，确认代码和文档一致

## 环境

当前已通过 docker compose 启动 Docker 环境，可供直接使用进行测试。所有 Python 代码及依赖必须通过 uv 进行管理。

## 完成后请说明

新增/修改了哪些文件、分享功能的设计（如何存储和校验共享权限）、使用查询的设计、测试覆盖的场景、代码和文档是否一致。
```

回答：

```
本次 stage 2 已完成，文档、代码、测试已经同步，并通过 `uv run pytest` 验证，结果是 12 passed。当前还存在一批既有 `datetime.utcnow()` 的弃用告警，但不影响本次功能正确性。

## 新增/修改文件

代码侧新增或改动了这些核心文件：

- `app/models/question.py`
- `app/services/question_service.py`
- `app/api/questions.py`
- `app/api/surveys.py`

文档侧同步更新了：

- `doc/01-prd.md`
- `doc/02-architecture.md`
- `doc/03-api-spec.md`
- `doc/04-db-design.md`
- `doc/05-test-cases.md`
- `doc/07-frontend-spec.md`

测试侧新增了 stage 2 专项用例：

- `tests/test_question_sharing.py`

## 分享功能设计

共享关系存储在 questions 集合内的 `sharedWith` 字段里，结构是一个授权数组，每个元素至少包含 `userId` 和 `sharedAt`，定义见 `app/models/question.py:9`。

共享是按逻辑题目 `questionId` 生效，不是按单个版本零散授权。实现时会把同一 `questionId` 的所有版本文档同步维护同一份共享列表，这样版本链不会被权限切断，见 `app/services/question_service.py:211`。

权限校验分成两层：

- **owner**：可以创建版本、共享题目、查看共享列表、查看使用情况。
- **shared user**：可以查看版本链、查看版本详情、把共享题装配进自己的问卷、查看该题使用情况，但不能创建新版本，也不能管理共享列表。

统一访问过滤逻辑在 `app/services/question_service.py:26`，问卷保存 schema 时也已经从 owner-only 改成 owner/shared 通吃，见 `app/api/surveys.py:201`。

新增的 questions API 包括：

- `POST /api/v1/questions/{question_id}/shares`
- `GET /api/v1/questions/{question_id}/shares`
- `GET /api/v1/questions/{question_id}/usage`

实现入口在 `app/api/questions.py:108`。

## 使用查询设计

使用查询不是单独建新集合，而是直接扫描 `surveys.questions.questionId` 来找所有引用该逻辑题的问卷。实现位置在 `app/services/question_service.py:236`。

返回结果按"问卷引用"展开，包含：

- `survey_id`
- `survey_title`
- `survey_owner_id`
- `survey_owner_username`
- `status`
- `question_version`
- `order_index`

这意味着：

- 所有者可以看到自己和被共享用户的问卷引用情况。
- 共享用户也可以查看自己有权访问的题被哪些问卷使用。
- 若 A 问卷用 v1、B 问卷用 v2，返回中会明确区分版本号。

## 测试覆盖

本次新增和验证的场景包括：

- owner 共享题给指定用户成功。
- recipient 在共享后能查看版本链和版本详情。
- recipient 能把共享题装配进自己的问卷。
- stranger 未共享时无法查看题详情，也无法把题装配进问卷。
- recipient 不能基于共享题创建新版本。
- recipient 不能查看或管理共享列表。
- owner 的 usage 查询能同时看到 owner 和 recipient 的问卷引用。
- recipient 的 usage 查询也能返回同一题的使用列表。
- 既有 stage 1 的版本链、快照隔离、填写校验、统计、并发和端到端流程都仍然通过。

## 一致性结论

代码和文档现在是一致的。

文档已经明确升级到 stage 2，覆盖了共享授权模型、共享权限边界、问卷装配共享题、以及题目使用查询；代码实现与测试结果也与这些描述一致。

On branch main
Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
        modified:   app/api/questions.py
        modified:   app/api/surveys.py
        modified:   app/models/question.py
        modified:   app/services/question_service.py
        modified:   doc/01-prd.md
        modified:   doc/02-architecture.md
        modified:   doc/03-api-spec.md
        modified:   doc/04-db-design.md
        modified:   doc/05-test-cases.md
        modified:   doc/07-frontend-spec.md
        new file:   tests/test_question_sharing.py
```

# 3

```
## 背景

Stage 1 完成了题目独立存储和版本控制，Stage 2 完成了题目分享。

## 本阶段范围

**核心目标**：让用户可以管理自己的题库，包括把题目加入题库、从题库移除题目、浏览题库内容。

具体实现以下需求：

1. **加入题库** — 用户可以把题目标记为"在题库中"，方便后续快速查找和使用
2. **移出题库** — 用户可以把题目从题库中移除，但题目本身仍然保留
3. **浏览题库** — 用户可以查看自己题库中的所有题目（自己的 + 被分享的）

**不包含在本阶段**：

- 跨问卷统计（需求八）

## 项目整体计划

- **Stage 1（已完成）**：题目独立存储 + 版本控制 + 问卷快照引用
- **Stage 2（已完成）**：题目分享 + 使用查询
- **Stage 3（本次）**：题库管理
- **Stage 4**：跨问卷统计
- **Stage 5**：前端改造（题库选题 + 跨问卷统计页面）

## 核心原则

文档与代码必须保持同步。整个开发过程遵循"先文档、后代码、再验证"的工作流程：先更新需求文档和设计文档，再据此修改代码，最后确认代码实现与文档描述是否一致。

## 执行思路（仅供参考，具体步骤自行规划）

1. 理解需求：阅读大作业一：需求变更.md 中需求七，理解题库管理的业务场景
2. 阅读代码：查看 app/models/question.py 和 app/services/question_service.py，理解现有题目模型和服务
3. 更新文档：同步更新 doc/ 下受影响的文档（数据库设计、API规格说明等）
4. 实施改造：在 question_service 和 questions API 中增加题库标记和浏览功能
5. 编写测试：验证加入题库、移出题库、浏览题库功能
6. 验证：运行测试，确认代码和文档一致

## 环境

当前已通过 docker compose 启动 Docker 环境，可供直接使用进行测试。所有 Python 代码及依赖必须通过 uv 进行管理。

## 完成后请说明

新增/修改了哪些文件、题库功能的设计（如何标记、查询）、测试覆盖的场景、代码和文档是否一致。
```

回答：

```
本次 stage 3 已完成，文档、代码、测试都已经同步，uv run pytest 结果为 13 passed。

题库功能这次没有新建独立集合，而是在现有 questions 版本文档上增加了按用户记录的题库标记 libraryMembers，设计落在 app/models/question.py 和 app/services/question_service.py。它和 sharedWith 一样，都是按 questionId 维度在整条版本链上保持一致，因此"加入题库/移出题库"不会把同一逻辑题拆成多个碎片版本。用户可以把自己拥有的题加入题库，也可以把别人共享给自己的题加入题库；移出题库只去掉自己的标记，不删除题目、不影响共享、不影响问卷快照和已有使用关系。

API 侧新增了题库管理入口，实现在 app/api/questions.py：

- POST /api/v1/questions/{question_id}/library
- DELETE /api/v1/questions/{question_id}/library
- GET /api/v1/questions/library

GET /api/v1/questions/library 返回的是当前用户题库里的逻辑题摘要列表，而不是按版本平铺的明细，包含 owner、最新版本、最新标题、题型、是否为共享题、是否在题库中等信息。由于问卷装配仍然走"可访问题目"校验，题从题库中移除后依然可以被读取和使用，只是不再出现在"我的题库"列表里。

本次新增/修改的主要文件有：

- app/models/question.py
- app/services/question_service.py
- app/api/questions.py
- doc/01-prd.md
- doc/02-architecture.md
- doc/03-api-spec.md
- doc/04-db-design.md
- doc/05-test-cases.md
- doc/07-frontend-spec.md
- tests/test_library.py

测试覆盖了这些场景：

- owner 把自己的题加入题库并成功浏览到。
- recipient 把共享题加入自己的题库并成功浏览到。
- stranger 无法把无权访问的题加入题库。
- 用户把题移出题库后，题库列表中消失。
- 题移出题库后仍可读取、仍可装配进问卷。
- libraryMembers 标记在版本链上按 questionId 一致维护。
- 既有 stage 1 和 stage 2 的分享、版本隔离、使用查询、填写、统计、并发与 e2e 流程仍全部通过。

代码和文档现在是一致的。Stage 3 的范围也按要求收住了：实现了加入题库、移出题库、浏览题库，没有去做跨问卷统计。


On branch main
Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
        modified:   app/api/questions.py
        modified:   app/models/question.py
        modified:   app/services/question_service.py
        modified:   doc/01-prd.md
        modified:   doc/02-architecture.md
        modified:   doc/03-api-spec.md
        modified:   doc/04-db-design.md
        modified:   doc/05-test-cases.md
        modified:   doc/07-frontend-spec.md
        new file:   tests/test_library.py
```

# 4

```
## 背景

Stage 1 完成了题目独立存储和版本控制，Stage 2 完成了题目分享，Stage 3 完成了题库管理。

## 本阶段范围

**核心目标**：让用户可以查看某个题在所有问卷中的回答情况汇总。

具体实现以下需求：

**需求八（跨问卷统计）** — 用户把题目保存下来重复使用，统计时希望能看某一道题在所有问卷中的回答情况汇总。例如"你的年龄"这个题在多个问卷中都用了，想知道所有问卷里年龄的总体分布。

**实现重点**：

- 按题目 questionId 聚合，跨所有问卷收集该题的回答数据
- 选择题返回各选项的汇总分布
- 数字题返回平均值和总体分布
- 文本题返回汇总明细
- 权限：只有题目owner和被共享的用户可以查看该题的跨问卷统计

**不包含在本阶段**：

- 前端页面改造（属于 Stage 5）

## 项目整体计划

- **Stage 1（已完成）**：题目独立存储 + 版本控制 + 问卷快照引用
- **Stage 2（已完成）**：题目分享 + 使用查询
- **Stage 3（已完成）**：题库管理
- **Stage 4（本次）**：跨问卷统计
- **Stage 5**：前端改造（题库选题 + 跨问卷统计页面）

## 核心原则

文档与代码必须保持同步。整个开发过程遵循"先文档、后代码、再验证"的工作流程：先更新需求文档和设计文档，再据此修改代码，最后确认代码实现与文档描述是否一致。

## 执行思路（仅供参考，具体步骤自行规划）

1. 理解需求：阅读大作业一：需求变更.md 中需求八，理解跨问卷统计的业务场景
2. 阅读代码：查看 app/api/surveys.py 中的统计实现，理解现有统计逻辑
3. 更新文档：同步更新 doc/ 下受影响的文档（数据库设计、API规格）
```

回答：

```
# Stage 4 完成报告

本次 stage 4 已完成，跨问卷统计已经落地，文档和代码同步更新，并通过 `uv run pytest` 全量验证，结果是 14 passed。

## 改动内容

核心实现集中在这几个文件：

- `app/services/question_service.py`
- `app/api/questions.py`

文档同步更新了：

- `doc/01-prd.md`
- `doc/02-architecture.md`
- `doc/03-api-spec.md`
- `doc/04-db-design.md`
- `doc/05-test-cases.md`

新增的专项测试文件：

- `tests/test_cross_stats.py`

## 跨问卷统计设计

新增接口是 `GET /api/v1/questions/{question_id}/statistics`，入口在 `app/api/questions.py`。

权限模型沿用 stage 2 和 stage 3：只有题目 owner 和被共享用户可以访问；无权限用户会拿到 404。

统计实现按 questionId 聚合，具体流程在 `app/services/question_service.py`：

1. 先扫描所有 `surveys.questions.questionId == question_id` 的问卷快照使用记录。
2. 再从对应问卷的 `answers.payloads.<questionId>` 收集答案。
3. 按题型执行不同统计逻辑。

返回口径是：

- 选择题：`distribution` 汇总所有问卷中的选项分布，`total_answers` 按答卷数统计。
- 数字题：返回 `average_value`、`distribution` 和 `text_list`。
- 文本题：返回 `text_list` 和 `total_answers`。

为了避免语义错误，我加了一个保护规则：如果同一 questionId 在不同问卷快照里出现了不同题型版本，接口会直接返回 422，提示"该题存在多种题型版本，无法直接合并统计"。这个检查在 `app/services/question_service.py` 的 `ensure_consistent_cross_survey_type` 里。

## 测试覆盖

本次新增测试覆盖了：

- 选择题跨 2 个问卷聚合分布。
- 数字题跨 2 个问卷聚合平均值与数值分布。
- 文本题跨 2 个问卷聚合明细。
- owner 可以查看跨问卷统计。
- shared user 也可以查看跨问卷统计。
- stranger 无权限查看。
- 同一 questionId 出现文本题版本和数字题版本时，跨问卷统计被拒绝。

同时，既有阶段的功能仍全部通过，包括：

- 版本控制
- 问卷快照引用
- 题目分享
- 题库管理
- 使用查询
- 单问卷统计
- 填写校验
- 并发与 e2e 路径

## 一致性

代码和文档现在是一致的。

stage 4 的范围也按要求收住了：只实现了后端跨问卷统计，没有做前端页面改造。

补充一点：当前全量测试仍有一批既有 `datetime.utcnow()` 的弃用警告，但不影响本次功能正确性；如果你要继续做 stage 5，我建议顺手把这一批时间处理统一换成 timezone-aware UTC。

On branch main
Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
        modified:   app/api/questions.py
        modified:   app/services/question_service.py
        modified:   doc/01-prd.md
        modified:   doc/02-architecture.md
        modified:   doc/03-api-spec.md
        modified:   doc/04-db-design.md
        modified:   doc/05-test-cases.md
        new file:   tests/test_cross_stats.py
```

# 5

```
## 背景

Stage 1-4 已完成后端改造：题目独立存储、版本控制、分享、题库管理、跨问卷统计 API 已全部完成。

## 本阶段范围

**核心目标**：改造前端页面，让用户能使用上述后端功能。

具体实现以下改造：

1. **问卷编辑器改造** — 用户在问卷中添加题目时，可以从自己的题库中选择题目（通过 GET /api/v1/questions/library 接口获取题库列表），而不是每次都重新创建题目。选中的题目在保存问卷时通过 POST /api/v1/surveys/{id}/schema 接口装配进问卷。

2. **跨问卷统计入口和页面** — 在题目详情页或题库页面增加"跨问卷统计"入口，用户点击后通过 GET /api/v1/questions/{question_id}/statistics 查看该题在所有问卷中的回答情况汇总。

3. **顺手修复 datetime.utcnow() 弃用警告** — 代码库中有一批 `datetime.utcnow()` 的弃用警告，请统一替换为 timezone-aware UTC 处理方式（用 `datetime.now(timezone.utc)` 或 `datetime.utcnow().replace(tzinfo=timezone.utc)`）。

**不包含在本阶段**：

- 不需要新增或大幅改造页面结构，只需要在前端增加对已有 API 的调用和展示

## 项目整体计划

- **Stage 1-4（已完成）**：后端改造
- **Stage 5（本次）**：前端改造 + datetime 警告修复
- **之后**：最终验收测试、报告整理

## 核心原则

文档与代码必须保持同步。整个开发过程遵循"先文档、后代码、再验证"的工作流程：先更新前端规格文档，再据此修改代码，最后确认代码实现与文档描述是否一致。

## 执行思路（仅供参考，具体步骤自行规划）

1. 阅读前端文档：查看 doc/07-frontend-spec.md，理解当前前端规格
2. 阅读前端代码：查看 templates/ 目录下的 HTML 模板和 static/ 目录下的 JS，理解当前前端实现
3. 更新文档：同步更新 doc/07-frontend-spec.md，说明前端改造内容
4. 实施改造：
   - 修改 templates/editor.html，增加题库选题功能
   - 修改 templates/stats.html 或新建页面，实现跨问卷统计展示
   - 统一修复 datetime.utcnow() 弃用警告
5. 验证：启动前端，确认功能可用

## 环境

当前已通过 docker compose 启动 Docker 环境，可供直接使用进行测试。所有 Python 代码及依赖必须通过 uv 进行管理。

## 完成后请说明

新增/修改了哪些文件、前端改造的内容、datetime 警告修复情况。
```

回答：

```
本次 stage 5 已完成，前端已经接上题库选题和跨问卷统计入口，同时 `datetime.utcnow()` 弃用警告已统一清理。`uv run pytest` 结果为 16 passed，并且已经没有 utcnow() 相关警告。

这次新增/修改的主要文件有：

- `templates/editor.html`
- `templates/stats.html`
- `templates/survey_fill.html`
- `doc/07-frontend-spec.md`
- `app/core/time.py`
- `app/api/auth.py`
- `app/api/answers.py`
- `app/api/surveys.py`
- `app/models/user.py`
- `app/models/survey.py`
- `app/models/answer.py`

**第一块是编辑器。**现在 `templates/editor.html` 不再假设前端直接构造题目定义，而是以当前后端真实模型为准：

- 通过 `GET /api/v1/questions/library` 拉取题库。
- 在页面右侧和抽屉里展示题库题目列表。
- 用户点击"加入问卷"后，会调用 `GET /api/v1/questions/{question_id}/versions/{version}` 拿到题目版本详情，再把它作为 `questionId + version + snapshot` 的前端展示对象加入当前问卷。
- 保存时只提交 `questionId + version + orderIndex` 和 `logic_rules`，由后端继续固化快照。
- 已加入问卷的题支持上移、下移、移除、配置跳转规则。
- 每道题和每个题库条目都加了"跨问卷统计"按钮，会打开统计弹窗并调用 `GET /api/v1/questions/{question_id}/statistics`。

**第二块是统计页。**现在 `templates/stats.html` 在原有"单问卷统计"基础上，为每一道题增加了"跨问卷统计"入口：

- 点击后弹窗展示跨问卷统计结果。
- 选择题用图表展示汇总分布。
- 数字题展示平均值、总体分布和明细。
- 文本题展示汇总明细。

**第三块是填写页兼容修正。**由于后端 schema 早就改成了 `surveys.questions[].snapshot`，原来的 `templates/survey_fill.html` 其实已经和后端不一致了。这次一并修正成从 `snapshot` 读取 `type`、`title`、`options`、`isRequired`、`mustBeInteger` 等字段，保证当前前端能正确渲染 stage 1-4 改造后的问卷结构。

**datetime.utcnow() 的修复**这次是统一做的，不是局部替换。新增了 `app/core/time.py`，提供：

- `utc_now()`
- `ensure_utc()`
- `to_zulu()`

然后把 API、service、model 的默认时间和对外序列化都统一切到了这个 helper。这样做的结果是：

- 不再使用 `datetime.utcnow()`
- 内部统一用 timezone-aware UTC
- 对外字符串统一为 Z 结尾
- 对 Mongo 读出的 naive UTC 时间也通过 `ensure_utc()` 做了兼容，不会再触发 naive/aware 比较错误

也专门扫过一遍，当前代码里已经没有 `utcnow(` 残留。

**验证方面**，做了两层：

- 全量后端回归：`uv run pytest` 通过，16 passed
- 新增了模板 smoke test：`tests/test_frontend_templates.py`，确认编辑器和统计页已经渲染出题库选题和跨问卷统计入口

代码和文档现在是一致的。`doc/07-frontend-spec.md` 已经更新为当前真实实现：编辑器从题库选题、统计页打开跨问卷统计弹窗、填写页按快照渲染。

补充一点：这次没有新增或大改页面路由结构，而是在现有编辑页和统计页上直接挂接已有 API，符合你这阶段"不要大幅改造页面结构"的要求。

On branch main
Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
        modified:   app/api/answers.py
        modified:   app/api/auth.py
        modified:   app/api/surveys.py
        new file:   app/core/time.py
        modified:   app/models/answer.py
        modified:   app/models/question.py
        modified:   app/models/survey.py
        modified:   app/models/user.py
        modified:   app/services/auth.py
        modified:   app/services/question_service.py
        modified:   doc/07-frontend-spec.md
        modified:   templates/editor.html
        modified:   templates/stats.html
        modified:   templates/survey_fill.html
        modified:   tests/test_filling.py
        new file:   tests/test_frontend_templates.py
```

# 6

```
## 问题现状

当前前端代码有严重的用户流程断点：

1. **用户无法新建题目并存入题库** — 编辑器只有"从题库选题"，但题库是空的，用户根本不知道如何把题加入题库
2. **分享功能（需求二）没有入口** — 后端有 API，但前端无 UI
3. **版本历史（需求四）没有入口** — 后端有 API，但前端无 UI
4. **使用查询（需求六）没有入口** — 后端有 API，但前端无 UI
5. **题库管理（需求七）不完整** — 无法把题加入/移出题库

## 核心目标

打通用户使用全流程：让用户能够**创建题目 → 加入题库 → 装配进问卷 → 分享给他人 → 查看版本历史 → 查看使用情况 → 查看跨问卷统计**。

## 具体改造要求

### 1. 新建题目并加入题库（最高优先级）

这是当前最大的断点。用户必须能：

- 在编辑器中点击"新建题目"按钮
- 填写题目内容（类型、标题、选项、校验规则等）
- 选择"保存到题库"（默认勾选）
- 保存后该题出现在题库列表中
- 可以继续选择该题加入当前问卷

参考后端 API：`POST /api/v1/questions`（创建题目）、`POST /api/v1/questions/{id}/library`（加入题库）

### 2. 题库管理入口（需求七）

在题库列表或题目详情页提供：

- "加入题库"按钮（针对还没有加入的题）
- "移出题库"按钮（针对已经在库里的题）
- 参考后端 API：`DELETE /api/v1/questions/{id}/library`

### 3. 分享功能入口（需求二）

在题目详情页或题库列表提供：

- "分享给..."按钮
- 输入用户名，点击确认
- 显示已分享用户列表
- 参考后端 API：`POST /api/v1/questions/{id}/shares`、`GET /api/v1/questions/{id}/shares`

### 4. 版本历史入口（需求四、五）

在题库卡片或题目详情提供：

- "版本历史"入口
- 显示 v1→v2→v3 版本链
- 可以查看每个版本的详情
- 可以基于某个版本创建新版本（如果你是 owner）
- 参考后端 API：`GET /api/v1/questions/{id}`、`GET /api/v1/questions/{id}/versions/{v}`

### 5. 使用查询入口（需求六）

在题目详情或题库卡片提供：

- "查看使用情况"按钮
- 显示该题被哪些问卷使用（包含问卷名、版本、状态）
- 参考后端 API：`GET /api/v1/questions/{id}/usage`

### 6. 跨问卷统计入口（需求八）

在题库卡片和问卷题目处已有"跨问卷统计"按钮，确保其正常可用。

## 执行思路（仅供参考）

1. 先理解现有前端代码结构（templates/editor.html 等）
2. 识别用户流程断点
3. 在 editor.html 中新增"新建题目"模态框
4. 在题库卡片上增加"分享"、"版本历史"、"使用情况"、"加入/移出题库"等操作按钮
5. 调整布局，确保每个功能入口清晰可见
6. 更新 doc/07-frontend-spec.md 文档
7. 验证所有功能入口可正常操作

## 环境

所有 Python 代码及依赖必须通过 uv 管理。测试命令：`uv run pytest`

## 完成后请说明

新增/修改了哪些页面和组件、每个功能的入口在哪里、用户完整操作流程是怎样的、测试验证结果。
```

回答：

```
本次只改了前端规格和编辑器工作台，没有动后端接口。变更文件是 doc/07-frontend-spec.md、templates/editor.html、tests/test_frontend_templates.py。文档先更新，再按文档重做页面，最后用 uv run pytest 回归，结果是 16 passed in 18.72s。

前端改造集中在 templates/editor.html。编辑器现在是一个完整的"题目工作台 + 问卷装配"页面：

- "新建题目"入口在问卷题目区顶部。弹窗里可以填写题型、标题、选项、文本/数字校验规则，默认勾选"保存到题库"，并可选"创建后直接加入当前问卷"。
- 右侧"题目工作台"展示题库内容和本次会话中已创建/查看过的题。每张卡片都有"加入问卷 / 加入题库或移出题库 / 分享给... / 版本历史 / 查看使用情况 / 跨问卷统计 / 题目详情"入口。
- "题目详情"弹窗整合了版本详情、版本链、共享列表、使用情况和题库状态切换。owner 可在这里继续分享题目、基于任意版本创建新版本；共享用户会看到只读提示。
- 已加入问卷的题目卡片也补了"题目详情 / 版本历史 / 查看使用情况 / 跨问卷统计"入口，避免用户必须回题库找入口。

完整用户流程现在是：在编辑器点击"新建题目"，填写内容后默认保存到题库，可直接加入当前问卷；之后在右侧工作台里继续做题库加入/移出、分享给其他用户、查看版本历史、查看使用情况，以及打开跨问卷统计。问卷左侧仍负责顺序调整、移出问卷和跳转逻辑配置，保存时仍只提交 questionId + version + orderIndex + logic_rules，不改变后端契约。

测试方面，我把模板烟测补到了这些关键入口，见 tests/test_frontend_templates.py。新增校验了编辑器页面包含"新建题目""保存到题库""分享给...""版本历史""查看使用情况""移出题库"等关键文案，防止后续改动再把入口删掉。当前代码与 doc/07-frontend-spec.md 已同步，文档描述的创建、题库管理、分享、版本历史、使用查询和跨问卷统计入口都已经在页面里落地。

On branch main
Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
        modified:   doc/07-frontend-spec.md
        modified:   templates/editor.html
        modified:   tests/test_frontend_templates.py
```

# 7

````
请诊断并修复以下两个问卷系统问题：

**问题一：问卷加载问题**
填写问卷的人打开问卷时，页面一直显示“加载中...”，问卷正文无法显示。

**问题二：问卷分享功能失效**
- 分享者可以看到分享记录
- 但被分享者登录后在题目列表中看不到被分享的问卷

**需求**
1. 确认上述两个问题是否确实存在
2. 分析问题原因，判断是前端问题、后端问题还是两者都有
3. 修改相关代码修复这些问题

请提供完整的代码修改方案。

```
[...终端错误日志: FastAPI/ASGI 应用异常...]
PydanticSerializationError: Unable to serialize unknown type: <class 'bson.objectid.ObjectId'>
技术栈: FastAPI, Starlette, Uvicorn, Pydantic v2, MongoDB (bson)
错误发生在序列化响应时，JSON 序列化失败
[...]完整 traceback 已省略[...]
```
````

回答：

```
两个问题都确实存在，而且都已经修复。

**问题一**是后端问题，前端只是被动卡死。`GET /api/v1/surveys/{id}/schema` 在返回问卷结构时把 MongoDB 的 `versionId:ObjectId` 原样放进响应，Pydantic v2 在序列化阶段直接抛 `PydanticSerializationError`，所以填写页拿不到 schema，标题一直停在"加载中..."。修复在 `app/api/surveys.py:29` 和 `app/api/surveys.py:121`：我新增了 `serialize_schema_question()`，把 `questions[].versionId` 统一转成字符串后再返回。这个修复后，填写页对应的后端接口可以正常 JSON 序列化，问卷正文能正常加载。

**问题二**本质上是后端可见性策略问题，前端列表只是把它暴露出来。共享成功后，系统只写了 `sharedWith`，没有把题自动放进被分享者的 `libraryMembers`。而当前前端题目列表是基于 `GET /api/v1/questions/library` 渲染的，所以分享记录虽然 owner 看得到，但 recipient 登录后题库列表为空，看起来就像"分享失效"。修复在 `app/services/question_service.py:211`：分享时除了写 `sharedWith`，还会同步把该题加入被分享者的 `libraryMembers`。这样被分享者登录后会立即在题库列表里看到共享题，同时仍然保留"可自行移出题库但不影响共享权限"的行为。

我同时把文档同步更新了，避免实现和规范继续漂移：

- `doc/03-api-spec.md`
- `doc/04-db-design.md`

测试也补了两条关键回归：

- `tests/test_filling.py:66` 验证 `/schema` 返回 200，且 `versionId` 是字符串。
- `tests/test_question_sharing.py:73` 验证分享后被分享者无需额外操作就能在 `/questions/library` 中看到共享题。

本次修改的文件：

- `app/api/surveys.py`
- `app/services/question_service.py`
- `doc/03-api-spec.md`
- `doc/04-db-design.md`
- `tests/test_filling.py`
- `tests/test_question_sharing.py`

验证结果是 `uv run pytest` 全量通过，`16 passed in 16.94s`。

On branch main
Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
        modified:   app/api/surveys.py
        modified:   app/services/question_service.py
        modified:   doc/03-api-spec.md
        modified:   doc/04-db-design.md
        modified:   tests/test_filling.py
        modified:   tests/test_question_sharing.py
```

# 8

```
## 背景

当前代码里没有创建任何索引，所有查询都是暴力遍历。需要为 questions、surveys、answers 三个集合创建必要的索引。

## 执行步骤

1. 先阅读 app/core/database.py，确认数据库连接初始化代码在哪里
2. 在数据库初始化时添加以下索引（使用 Motor 的 create_indexes）：

   - questions 集合：
     - `{questionId: 1, version: 1}` 唯一索引
     - `{userId: 1, questionId: 1}`
     - `{versionChainRootId: 1, version: 1}`
   
   - surveys 集合：
     - `{userId: 1, createdAt: -1}`
     - `{status: 1}`
     - `{questions.questionId: 1}`（用于 list_question_snapshot_usages）

   - answers 集合：
     - `{surveyId: 1, submittedAt: -1}`
     - `{surveyId: 1, respondentId: 1}`

3. 更新 doc/04-db-design.md，说明索引已在代码中实现

## 环境

使用 uv 管理依赖，Motor 异步驱动。测试命令：`uv run pytest`
```

回答：

```
# 索引实现与文档同步

索引已经接入数据库初始化流程，并且文档已同步。实现位置在 `app/core/database.py:15` 到 `app/core/database.py:43`：新增了 `ensure_indexes()`，在 `connect_to_mongo()` 建立 Motor 连接后立即调用 `create_indexes()`，自动创建这几组索引：

- **questions**
  - `{ questionId: 1, version: 1 }` 唯一索引
  - `{ userId: 1, questionId: 1 }`
  - `{ versionChainRootId: 1, version: 1 }`

- **surveys**
  - `{ userId: 1, createdAt: -1 }`
  - `{ status: 1 }`
  - `{ "questions.questionId": 1 }`

- **answers**
  - `{ surveyId: 1, submittedAt: -1 }`
  - `{ surveyId: 1, respondentId: 1 }`

文档更新在 `doc/04-db-design.md:47`、`doc/04-db-design.md:107`、`doc/04-db-design.md:134`、`doc/04-db-design.md:159`。原来“当前代码不会自动创建索引”的描述已经改成“连接初始化时自动创建核心索引”。

这次接索引时还暴露出一个真实问题：统计接口原先没有显式排序，Mongo 在走新索引后返回顺序变了，导致数字题/文本题明细顺序不稳定。这个不是索引错误，而是原查询依赖自然顺序。我顺手把统计明细查询改成按 `submittedAt` 升序读取，位置在 `app/api/surveys.py:301` 和 `app/services/question_service.py:341`，这样和新索引配合后结果稳定、可预期。

本次实际修改文件：

- `app/core/database.py`
- `doc/04-db-design.md`

连带修正的稳定性文件：

- `app/api/surveys.py`
- `app/services/question_service.py`

验证结果：`uv run pytest` 已通过，**16 passed in 16.91s**。

On branch main
Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
        modified:   app/api/surveys.py
        modified:   app/core/database.py
        modified:   app/services/question_service.py
        modified:   doc/04-db-design.md
```

