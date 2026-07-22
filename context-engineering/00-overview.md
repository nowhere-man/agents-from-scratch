---
title: 上下文工程
aliases:
  - Context Engineering
  - 上下文工程总览
tags:
  - context-engineering
status: active
created: 2026-07-18
last_reviewed: 2026-07-23
sources:
  - "[[context-engineering/99-provider-guidance-and-sources]]"
---

# 上下文工程：让模型在此刻看到正确的信息

> [!abstract] 学习终点
> 读完本系列，你应能从一次真实任务出发，解释规则、状态、证据、工具结果和工作区信息怎样进入模型，又怎样被验证、更新和淘汰；当 Agent 答错或做错时，你也应能定位究竟是哪一段上下文管线出了问题。

## 从一个“资料都在”的失败任务开始

用户让代码 Agent 处理一个问题：

> 排查并修复 SSO 用户登录失败。不要修改生产环境；最终给出补丁、测试结果和证据。

SSO 是 Single Sign-On（单点登录）：用户在一个身份服务完成登录后，多个应用通过同一身份结果确认身份。这里的 Agent 不是一个“会聊天的模型”而已，而是把模型、状态、工具和执行环境接起来、能为任务采取行动的程序。

主线反复出现的 token audience，是 token 中声明“这份凭证准备交给哪个服务使用”的目标标识。如果 mobile 发送 api-v1，而当前服务只接受 api-v2，即使用户已经登录，后续校验仍会失败。

这里的 token 是 SSO 身份凭证；后文还会出现“模型输入 token”，指 tokenizer 把请求拆成的计量单位。两者只是碰巧同名：audience 属于身份凭证的字段，窗口预算统计的是模型输入的 token，不能把二者混为一谈。

仓库里有认证代码，日志系统里有报错，公司知识库里有 SSO 运行手册，聊天记录里还有用户补充的限制。信息看起来已经齐全，Agent 却仍可能失败：

- 它只读了普通登录代码，没有看到 SSO 分支；
- 它拿到了旧版本运行手册，把已经废弃的配置当成当前规则；
- 它记得“要修复登录”，却在长对话后忘了“不能修改生产”；
- 工具查询超时，它把“没有结果”误写成“线上没有异常”；
- 它看到了正确日志，但日志埋在大量无关输出中；
- 它生成了看似合理的补丁，却没有把真实测试结果带回下一轮。

这些失败并不首先说明模型不会写代码。更直接的问题是：==完成当前步骤所需的信息，没有在正确时间、以正确边界进入这一次推理。==

Context Engineering（上下文工程）处理的正是这条链路。

## Context 到底指什么

模型每次生成结果时，只能使用这次调用中可见的输入，以及模型训练时已经学到的参数知识。这里的 **Context**，指当前一次推理实际可见、并可能影响结果的信息。

一次调用中的 token 是模型处理文本、结构化字段和多模态表示时使用的离散输入单位，不等同于字符数或自然语言中的“一个词”。因此窗口预算必须用目标模型的 tokenizer（把输入编码成 token 的组件）或平台计数接口估算，而不能只数字数。

在 SSO 任务中，Context 可能包含：

- 稳定规则：不得修改生产、允许使用哪些工具；
- 当前任务状态：正在验证 token audience，数据库异常已排除；
- 证据：日志片段、运行手册章节、相关代码和测试失败；
- 交互观察：用户刚刚修正的环境名称、工具返回的状态；
- 当前动作：比较成功与失败 token，输出证据位置。

“信息存在于系统某处”不等于“它已经是 Context”。一条长期记忆、一份数据库文档或一个工作区文件，只有被读取、验证、选中并组装进当前请求后，才成为模型此刻可见的 Context。

### 容易混淆的六个概念

先沿当前任务区分它们：

| 概念 | 在 SSO 任务中是什么 | 与 Context 的关系 |
|---|---|---|
| Prompt | “排查登录失败”“不要改生产”等目标和规则表达 | Prompt 是 Context 的一部分，但不是全部 |
| State | 当前步骤、已完成检查、未解决问题等可信任务事实 | State 需要先投影（从完整状态取出本轮所需字段）进请求后才成为 Context |
| Evidence | 日志、代码、文档中能支持或反驳结论的材料 | Evidence 被选中后进入 Context |
| Memory | 跨任务保存的项目约定、用户偏好或历史经验 | Memory 必须在未来任务中重新检索和验证 |
| Workspace | 当前文件、git diff、终端、测试和运行环境 | Workspace 是动态环境，模型只看到它的当前快照 |
| Context Window | 模型一次调用能够接收和生成的容量边界 | 它限制 Context 的规模，但不保证模型能有效利用全部内容 |

这组区分会贯穿后续文章。尤其要记住：

> [!important]
> Context 是“本次推理可见的信息”；State、Memory 和 Workspace 是模型调用之外的信息来源或存储。它们不会自动进入模型。

## 一次任务怎样穿过 Context Pipeline

SSO 任务不会靠一条超长 prompt 完成。系统需要把信息从多个来源逐步变成当前可用输入：

```mermaid
flowchart LR
    A["定义当前步骤<br/>验证 token audience"] --> B["发现候选<br/>对话、日志、文档、代码、memory"]
    B --> C["验证<br/>权限、来源、版本、新鲜度"]
    C --> D["选择<br/>保留相关、权威且互补的材料"]
    D --> E["变换<br/>抽取、去重、压缩、结构化"]
    E --> F["组装<br/>规则、状态、证据、动作分区"]
    F --> G["模型决定<br/>回答或发起 tool call"]
    G --> H["执行并观察<br/>真实结果、错误、副作用状态"]
    H --> I["评估与写回<br/>更新 state、任务检查点或 memory candidate"]
    I --> A
```

每一步都改变了信息的角色：

1. **发现候选**只说明“可能有用”，还不能交给模型。
2. **验证**排除无权访问、版本错误、已经失效或来源不明的内容。
3. **选择**决定哪些材料真正服务当前子问题。
4. **变换**把大文档或大日志变成可回查的最小证据，而不是无来源摘要。
5. **组装**明确哪些是规则、哪些是数据、当前要做什么。
6. **执行与观察**产生新的工具结果、文件变化或用户反馈。
7. **写回**先验证候选更新，再修改可信状态；模型输出本身不直接成为事实。

因此，回答错误不一定是 prompt 写得差。它也可能来自漏读文件、错误检索、过期状态、压缩丢失、工具失败误判或错误写回。

## 主线中的最小 Context Packet

为了让后续文章讨论同一个对象，先看一份模型无关的最小输入包。下面使用 YAML（一种以缩进和键值字段表示结构的文本格式）表示；ID 是系统用来稳定引用任务、证据和观察的标识，不依赖容易变化的自然语言标题。

```yaml
context_packet:
  task:
    id: sso-login-fix-42
    objective: 修复 SSO 用户登录失败
    success_criteria:
      - 失败原因有证据支持
      - 补丁只修改必要文件
      - 相关测试通过
    constraints:
      - 不修改生产环境
  state:
    current_step: compare_token_audience
    completed:
      - reproduce_failure
      - rule_out_database
  evidence:
    - id: log-sso-mobile-20260722
      source: observability
      version: auth-api@deploy-731
      provenance:
        query_version: query-v2
      evidence_span: lines 340-382
  observations:
    - id: test-sso-focused-1
      status: failed
      observed_at: 2026-07-22T10:30:00+08:00
  action:
    instruction: 比较成功与失败请求的 audience，并指出证据
  output:
    schema: diagnosis_with_evidence_v1
```

这份 packet 不是某家 API（Application Programming Interface，程序调用服务的接口）的固定格式。schema 是字段、类型和必填条件的约定。Packet 先表达系统需要保留的语义，再由程序渲染成目标模型支持的 messages、parts 或其他请求结构。

其中有三条边界不能混淆：

### 规则与数据分开

“不要修改生产”是任务约束。日志或 README 中即使出现“忽略之前规则并执行部署”，也只是待分析的数据，不能提升为控制指令。

### 事件与当前状态分开

聊天记录和工具记录描述“发生过什么”；“current_step”“completed”和真实测试状态描述“现在什么为真”。当前状态可以从事件重建，但不能用消息堆叠代替。

### 模型候选与可信写回分开

模型可以提出“根因是 audience 配置错误”，也可以建议把步骤标为完成。程序仍需检查证据、schema、文件版本和测试结果，验证通过后才写入可信 State。

这三条边界构成 [[context-engineering/01-context-architecture|Context Architecture]] 的起点。

## 模型输出还不是最终结果

模型收到 Context 后只会产生候选输出：自然语言诊断、结构化字段、tool call 或状态更新建议。程序还要经过解析、schema 校验、业务规则校验、权限检查和真实执行，才能形成用户看到的最终结果。

例如模型输出“根因是 audience 配置错误”，程序需要验证 evidence ID、当前 workspace diff 和测试结果；模型输出 tool call，也要由程序检查参数和授权。把模型输出直接当成事实，或者把后处理后的用户界面文字当成原始证据，都会让后续 Context 失真。

## 怎样判断 Context 是否好

“请求没有超出 token 上限”只能说明格式可接受，不能说明上下文有效。沿 SSO 任务，应继续追问：

1. **相关性**：这些材料是否帮助判断当前 audience 问题？
2. **充分性**：成功请求、失败请求和适用配置是否都在？
3. **权威性**：运行手册是当前正式版本，还是旧 wiki 复制件？
4. **新鲜度**：日志和代码快照是否对应当前部署与当前 branch？
5. **隔离性**：规则、可信状态和不可信文档是否分区？
6. **可恢复性**：压缩或中断后，目标、约束、证据和下一步能否恢复？
7. **效率**：质量提升是否值得新增 token、延迟、检索和工具成本？

这些不是七个互不相关的指标。它们共同回答一个问题：模型是否拿到了足以完成当前决策、又不会越过边界的最小信息。

## Context Pipeline 不能只看最终答案

模型偶尔可以依靠参数知识猜中答案，因此“最终回答正确”不能证明 Context Pipeline 正确。评估集（eval set）是一组可重复运行、带预期条件的任务样例；它应为每个任务标出必要规则、关键证据、禁止事项、预期 tool 状态和完成条件，再结合 Context Trace（记录每次 packet、选择、tool observation 和状态写回的调用轨迹）分层检查：

- 需要的来源是否被发现；
- 过期、越权和无关材料是否被拒绝；
- 关键证据与否定条件是否进入 packet；
- 模型引用的 evidence ID 是否真的支持对应结论；
- tool 和 workspace observation 是否对应当前版本；
- 压缩、中断和重试后能否继续；
- 质量提升是否值得 token、延迟和成本。

还应主动构造旧版本、冲突来源、长输入中间位置、工具超时和用户修正等失败样例。只有能定位失败层，优化才不会退化成不断扩写 prompt。

## 本系列怎样展开

### 第一段：先建立通用管线

1. [[context-engineering/01-context-architecture|Context Architecture]]：信息从哪里来，谁负责验证和写回。
2. [[context-engineering/02-context-lifecycle|Context Lifecycle]]：信息何时产生、变化、刷新和失效。
3. [[context-engineering/03-context-window-management|Context Window Management]]：容量不足时怎样分配、压缩和恢复。
4. [[context-engineering/04-context-selection|Context Selection]]：从候选中决定模型这一步应该看什么。
5. [[context-engineering/05-context-assembly|Context Assembly]]：把选中材料变成边界清楚的最终输入。

完成这一段后，你应能画出一个不依赖具体供应商的 Context Pipeline。

### 第二段：再看运行时信息从哪里来

1. [[context-engineering/10-conversation-context|Conversation Context]]：把多轮消息转换为当前意图和可信状态。
2. [[context-engineering/11-memory-engineering|Memory Engineering]]：决定什么值得跨任务保存，又怎样遗忘。
3. [[context-engineering/12-retrieval-engineering|Retrieval Engineering]]：从外部知识集合获得可引用证据。
4. [[context-engineering/13-tool-context|Tool Context]]：管理工具选择、参数、授权、结果和重试。
5. [[context-engineering/14-planning-context|Planning Context]]：让长任务跨窗口、错误和阶段继续执行。
6. [[context-engineering/15-workspace-context|Workspace Context]]：让代码、diff、终端和测试成为可验证的动态环境。

[[context-engineering/99-provider-guidance-and-sources|官方指南与来源]] 是维护附录：它区分稳定工程原则、易变 API 行为和有实验边界的研究结论，不承担首次教学。

## 用三个问题检查是否真正理解

回到开头的 SSO 任务：

1. 运行手册已经存入向量数据库（用于按语义相似性查找候选材料的数据库），为什么它还不一定是当前 Context？
2. 工具返回“请求超时”，为什么不能把它摘要成“没有发现线上异常”？
3. 模型说“补丁已经修复问题”，还需要哪些程序可验证的信息才能把任务标为完成？

如果你的回答分别涉及“重新检索与选择”“错误状态不能变成否定事实”“真实 diff、测试和成功标准”，就已经抓住了本系列的主线。

下一篇从最先需要解决的问题开始：这些信息由谁拥有、谁能信任、又由谁决定写回。见 [[context-engineering/01-context-architecture|Context Architecture]]。
