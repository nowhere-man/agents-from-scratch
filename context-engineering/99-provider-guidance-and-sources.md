---
title: 官方指南与来源
aliases:
  - Context Engineering Sources
  - Provider Guidance for Context Engineering
tags:
  - context-engineering
  - sources
status: active
created: 2026-07-18
last_reviewed: 2026-07-23
sources:
  - https://developers.openai.com/api/docs/guides/prompt-engineering
  - https://developers.openai.com/api/docs/guides/prompt-caching
  - https://developers.openai.com/api/docs/guides/retrieval
  - https://platform.claude.com/docs/en/build-with-claude/context-windows
  - https://platform.claude.com/docs/en/build-with-claude/prompt-caching
  - https://ai.google.dev/gemini-api/docs/long-context
  - https://ai.google.dev/gemini-api/docs/caching
---

# 官方指南与来源：怎样维护一套不会过时的 Context Engineering 笔记

> [!abstract] 本篇学习终点
> 读完后，你应能区分跨供应商稳定的工程原则、会随 API 和模型版本变化的行为、以及有实验条件的研究结论；更新来源时，能知道什么该进入稳定正文，什么只能留在本篇并标注复查日期。

## 为什么来源需要单独成篇

前面的笔记讲的是一条不依赖具体平台的 Context Pipeline：定义任务、发现来源、验证、选择、组装、执行、观察和恢复。

但以下事实会变化：

- 某个模型的 context window；
- prompt cache 的最小长度、TTL（条目有效时长）、命中字段和价格；
- API 是否自动保存 conversation 或 tool state；
- tool result 的消息格式；
- hosted retrieval 的过滤字段和文件保留期；
- thinking、compaction 和多模态输入的限制。

如果把这些数字和字段写进稳定正文，供应商更新后，读者会把旧行为误认为通用原则。来源附录的职责是保存证据、适用范围和复查协议，而不是替代主题文章的因果解释。

## 三层来源模型

### 第一层：跨供应商相对稳定的工程原则

例如：

- 只给模型完成当前任务所需的相关材料；
- 规则、状态、证据和不可信内容要有清晰边界；
- 长输入需要预算、顺序和真实 eval；
- tool result 需要状态、来源和错误边界；
- 多轮任务需要显式 state 与恢复策略；
- retrieval 需要权限、版本、缺失和引用；
- 模型候选不能未经验证直接写入可信状态。

这些原则进入 00–15 的稳定正文，并用供应商文档和研究资料作为支撑，而不是依赖某个字段名称。

### 第二层：模型与 API 行为

例如：

- 某 API 使用哪些消息角色；
- cache breakpoint 如何声明；
- tool result 需要什么原生结构；
- provider 是否自动保留历史；
- 文件和会话数据保存多久。

这些内容可以帮助实现，但必须注明供应商、API surface、版本和复查日期。它们主要留在本篇或相邻 provider-specific 笔记中。

API surface 指同一供应商对外提供的具体接口形态，例如聊天接口、Responses、Files 或独立的工具协议；同一家供应商的不同 surface 也可能有不同的状态和保留语义。

### 第三层：研究论文与实验结论

论文告诉我们某种机制在特定模型、数据集、长度、提示和评测下观察到什么。例如长上下文位置效应、RAG 召回、外部 memory 或工具交互研究。

论文结论不能直接变成“所有模型都如此”。正文应把它转译为待验证的工程假设，并在自己的模型和任务集上复测。

## 跨供应商共识与正文落点

| 共识 | 在本系列中的落点 |
|---|---|
| 只注入完成任务所需的材料 | [[context-engineering/04-context-selection\|Context Selection]]、[[context-engineering/05-context-assembly\|Context Assembly]] |
| 窗口大小不等于有效容量 | [[context-engineering/03-context-window-management\|Context Window Management]] |
| 稳定前缀可获得缓存收益，但需失效策略 | [[context-engineering/03-context-window-management\|Context Window Management]] |
| 外部材料和工具结果不能改变控制面 | [[context-engineering/01-context-architecture\|Context Architecture]]、[[context-engineering/13-tool-context\|Tool Context]] |
| 多轮任务需要结构化状态和恢复 | [[context-engineering/10-conversation-context\|Conversation Context]]、[[context-engineering/14-planning-context\|Planning Context]] |
| Retrieval 需要元数据、过滤、排序和引用 | [[context-engineering/12-retrieval-engineering\|Retrieval Engineering]] |
| Workspace 是动态快照而非静态知识库 | [[context-engineering/15-workspace-context\|Workspace Context]] |
| 长期 memory 需要写入门槛和遗忘 | [[context-engineering/11-memory-engineering\|Memory Engineering]] |

这些是设计判断的共同语言，不是某个 SDK（软件开发工具包）的复制说明。

## OpenAI：重点查什么

官方入口：

- [Prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering)
- [Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)
- [Retrieval](https://developers.openai.com/api/docs/guides/retrieval)
- [Function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [Evals](https://developers.openai.com/api/docs/guides/evals)

复查时关注：

- 消息角色、instruction 层级和输入组织；
- Prompt Caching 的前缀匹配、命中统计和失效条件；
- Retrieval、vector store、file search 与 metadata filtering；
- Function calling、Structured Outputs 和 tool result 消息；
- Responses API 的 conversation / state 语义与数据保留选项。

不要把以下内容写成稳定原则：

- 当前模型的窗口大小、知识截止日期和内部推理行为；
- cache 的折扣、最小长度、TTL、持续时间和命中字段；
- hosted retrieval 的计费、文件支持和限制；
- API 是否自动保存某类历史或 tool state。

## Anthropic Claude：重点查什么

官方入口：

- [Context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows)
- [Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [Tool use overview](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)
- [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)

复查时关注：

- context window、长输入行为和 token counting；
- cache control、breakpoint 和有效期；
- tool use 的定义、结果消息和并行调用；
- 长对话 compaction、agent state 与安全指南。

不要把以下内容写成跨模型永久事实：

- 当前模型系列的窗口、扩展上下文和 beta header（用于选择预览能力的请求头）；
- cache breakpoint 数量、TTL、价格和自动缓存行为；
- thinking、tool use 与 compaction 的版本专属限制。

## Google Gemini：重点查什么

官方入口：

- [Long context](https://ai.google.dev/gemini-api/docs/long-context)
- [Context caching](https://ai.google.dev/gemini-api/docs/caching)
- [Function calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [Prompt design strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies)

复查时关注：

- long context 的输入组织、token counting 和多模态限制；
- explicit / implicit context caching 的支持与计费；
- Files API、grounding（让输出连接搜索结果或可引用来源）、function calling 和 structured output；
- 视频、音频、图片和文档的输入表示。

不要把以下内容写成稳定正文：

- 当前 Gemini 型号的窗口、媒体限制和 thinking 行为；
- cache 的最低 token、TTL、隐式命中和价格；
- 不同 API surface 的文件保留期和状态语义。

## 研究来源与使用边界

| 主题 | 来源 | 在本系列中的用途 |
|---|---|---|
| 长上下文位置效应 | [Lost in the Middle](https://arxiv.org/abs/2307.03172) | 支持窗口位置退化假设，并要求真实长度 eval |
| Retrieval-Augmented Generation | [RAG](https://arxiv.org/abs/2005.11401) | 说明检索与生成的基本分工 |
| 外部记忆与分层上下文 | [MemGPT](https://arxiv.org/abs/2310.08560) | 支持 Memory / Context 的职责区分 |
| 工具交互循环 | [ReAct](https://arxiv.org/abs/2210.03629) | 支持观察、行动和继续条件的讨论 |
| 代码 Agent 的环境接口 | [SWE-agent](https://arxiv.org/abs/2405.15793) | 支持 Workspace 与工具边界的讨论 |
| 生成式 Agent 记忆 | [Generative Agents](https://arxiv.org/abs/2304.03442) | 提供 memory retrieval、reflection 和 consolidation 背景 |

使用研究时至少记录：

- 模型与版本；
- 数据集或任务类型；
- 输入长度与预算；
- baseline 和对照条件；
- 指标定义；
- 失败案例和适用边界。

例如“位置中间效果”可以成为一个 eval 假设，但不能从一篇论文推导出“所有模型只看开头和结尾”。

## 本地资料怎样互相衔接

- [[roadmap|AI Agents Roadmap]]：展示 RAG、Tool Use、Agent Loop 和 Memory 的主题地图；
- [[prompt-engineering/10-context-and-instruction-architecture|上下文与指令架构]]：解释 prompt 与 context、消息层级和信任边界；
- [[prompt-engineering/12-tools-state-and-authorization|工具、状态与授权边界]]：补充工具路由、授权和副作用；
- [[prompt-engineering/13-decomposition-and-agent-workflows|任务拆解与 Agent 工作流]]：补充 workflow、链式、并行和校验；
- [[prompt-engineering/04-reasoning-strategies|推理增强策略]]：说明 prompt、sampling、workflow 与 tool 层的区别；
- [[agent-skills/prompt-engineering/references/long-context.md|Long Context 参考]]：提供长上下文的额外资料；
- [[agent-skills/prompt-engineering/references/runtime.md|Runtime 参考]]：提供运行时实现线索。

这些链接是扩展入口。context-engineering 的核心术语和因果链必须能在本目录内独立阅读。

## 复查协议：更新来源而不是只改日期

复查本系列时，按以下顺序：

1. 打开所有官方链接，确认 URL、页面迁移和弃用状态；
2. 核对窗口、缓存、状态、工具、文件和数据保留说明；
3. 把跨供应商稳定原则与平台专属行为分开；
4. 对每个易变数字记录供应商、API surface、版本和日期；
5. 检查正文是否把某个字段或价格写成永久规则；
6. 用目标模型和真实任务重新运行长上下文、retrieval、cache、tool 和 recovery eval；
7. 更新来源状态、证据引用和 last_reviewed；
8. 对无法联网或无法确认的来源明确标注“未复核”，不能只因为 URL 存在就标为已验证。

来源复查完成后，还要重新检查下游文章：API 变化可能改变质量、延迟、成本和恢复行为，不是只更新一个链接。

## 当前来源状态

下表描述的是本次笔记重构时的记录状态，不是对供应商页面未来内容的保证：

| 来源 | 本次状态 | 使用限制 |
|---|---|---|
| OpenAI 官方指南 | URL 已记录；未在本次离线重构中重新核对所有页面内容 | 正文不依赖易变数字；实施前按复查协议访问 |
| Anthropic Claude 官方指南 | URL 已记录；版本行为需按目标 API 复查 | 不把 beta、TTL 和窗口写入稳定原则 |
| Google Gemini 官方指南 | URL 已记录；版本行为需按目标 API 复查 | 多模态和 cache 限制需以当前页面为准 |
| arXiv 研究论文 | 论文入口已记录 | 保留实验条件，不直接推广为模型定律 |
| 本地 prompt-engineering 与 roadmap | 已读取并作为相邻导航 | 相邻笔记的主题边界变化时重新核对链接 |

“未复核”不是错误隐藏，而是来源生命周期的一部分。只有实际读取并确认内容，才能把状态改为已核验。

## 常见误区

- **链接存在就等于事实已验证**：URL 只是入口，页面内容、版本和适用范围仍需检查；
- **把一家供应商的角色或 cache 规则写成通用架构**：正文应表达职责和边界，平台字段放在附录；
- **只更新数字不重跑 eval**：窗口或 tool 行为变化可能改变质量和恢复；
- **论文结论没有实验边界**：模型、数据集、预算变化会改变结果；
- **来源附录变成产品 API 手册**：本篇应服务于判断稳定性和复查，具体实现可链接官方文档；
- **把未访问页面标成已核验**：无法确认时明确记录限制。

## 自测：能否维护这套笔记

1. 某供应商把 cache TTL 从五分钟改为一小时，哪些文章需要改，哪些只需更新本篇？
2. 论文显示某模型在中间位置性能下降，怎样把它转成自己的 eval，而不是直接写成普遍规律？
3. 一个 API 新增了自动 conversation state，为什么仍不能删除本系列关于 Current View、Source of Truth 和恢复的讨论？

回到 [[context-engineering/00-overview|上下文工程总览]]，检查阅读地图、链接和来源状态是否仍然一致。
