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
last_reviewed: 2026-07-18
sources:
  - https://developers.openai.com/api/docs/guides/prompt-engineering
  - https://developers.openai.com/api/docs/guides/prompt-caching
  - https://developers.openai.com/api/docs/guides/retrieval
  - https://platform.claude.com/docs/en/build-with-claude/context-windows
  - https://platform.claude.com/docs/en/build-with-claude/prompt-caching
  - https://ai.google.dev/gemini-api/docs/long-context
  - https://ai.google.dev/gemini-api/docs/caching
---

# 官方指南与来源

> [!important] 一句话核心
> Context Engineering 的稳定原则是选择、边界、来源、生命周期和评估；模型窗口、缓存条件、状态 API、工具格式与价格属于供应商和版本特性，必须隔离并定期复查。

## 来源策略

本系列采用三层来源：

1. **稳定工程原则**：跨供应商长期成立，进入主题正文。
2. **模型与 API 行为**：可能随版本变化，集中记录在本篇。
3. **研究结论**：说明实验条件和适用范围，不直接当成所有模型的永久规律。

正文避免固化模型名称、最大 context window、价格、缓存折扣、默认参数和未验证字段。

## 跨供应商共识

| 共识 | 本系列中的落点 |
|---|---|
| 只提供完成任务所需的相关材料 | [[04-context-selection]]、[[05-context-assembly]] |
| 长上下文需要预算、顺序和真实 eval | [[03-context-window-management]] |
| 稳定前缀可以获得缓存收益 | [[03-context-window-management]] |
| Tool 和外部材料需要清晰边界 | [[13-tool-context]] |
| 多轮任务需要显式 state 和恢复策略 | [[10-conversation-context]]、[[14-planning-context]] |
| Retrieval 需要来源、过滤和评估 | [[12-retrieval-engineering]] |
| 不可信内容不能改变系统权限 | [[01-context-architecture]]、[[15-workspace-context]] |

具体消息角色、缓存键、自动状态保留和工具协议仍需查目标 API。

## OpenAI

### 需要关注

- Prompt engineering、消息角色和 instruction 层级。
- Prompt Caching 的前缀匹配、缓存可见性和使用统计。
- Retrieval、vector store、file search 与 metadata filtering。
- Function calling、Structured Outputs 和 tool result 消息格式。
- Responses API 的 conversation / state 语义与数据保留选项。

### 官方来源

- [Prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering)
- [Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)
- [Retrieval](https://developers.openai.com/api/docs/guides/retrieval)
- [Function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [Evals](https://developers.openai.com/api/docs/guides/evals)

### 不应写死在稳定正文

- 当前模型的窗口大小和知识截止时间。
- Cache 的折扣、最小长度、持续时间和命中字段。
- Hosted retrieval 的限制、计费和文件支持范围。
- API 是否自动保存某类历史或 tool state。

## Anthropic Claude

### 需要关注

- Context window、长输入行为和 token counting。
- Prompt Caching 的 cache control、breakpoint 和有效期。
- Tool use 的定义、结果消息和并行调用。
- 长对话 compaction、agent state 和安全指南。

### 官方来源

- [Context windows](https://platform.claude.com/docs/en/build-with-claude/context-windows)
- [Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [Tool use overview](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)
- [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)

### 不应写死在稳定正文

- 当前模型系列的窗口、扩展上下文和 beta header。
- Cache breakpoint 数量、TTL、价格和自动缓存行为。
- Thinking、tool use 与 compaction 的版本专属限制。

## Google Gemini

### 需要关注

- Long context 的输入组织、token counting 和多模态限制。
- Explicit / implicit context caching 的支持与计费。
- Files API、grounding、function calling 和 structured output。
- 视频、音频、图片和文档的输入表示。

### 官方来源

- [Long context](https://ai.google.dev/gemini-api/docs/long-context)
- [Context caching](https://ai.google.dev/gemini-api/docs/caching)
- [Function calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [Prompt design strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies)

### 不应写死在稳定正文

- 当前 Gemini 型号的窗口、媒体限制和 thinking 行为。
- Cache 的最低 token、TTL、隐式命中和价格。
- 不同 API surface 的文件保留期和状态语义。

## 研究来源

| 主题 | 来源 | 本系列用途 |
|---|---|---|
| 长上下文位置效应 | [Lost in the Middle](https://arxiv.org/abs/2307.03172) | [[03-context-window-management]] 的位置退化与 eval |
| Retrieval-Augmented Generation | [RAG](https://arxiv.org/abs/2005.11401) | [[12-retrieval-engineering]] 的基础架构 |
| 外部记忆与分层上下文 | [MemGPT](https://arxiv.org/abs/2310.08560) | [[11-memory-engineering]] 的 memory / context 分工 |
| 工具交互推理 | [ReAct](https://arxiv.org/abs/2210.03629) | [[13-tool-context]] 与 [[14-planning-context]] 的观察循环 |
| 代码 Agent 的环境接口 | [SWE-agent](https://arxiv.org/abs/2405.15793) | [[15-workspace-context]] 的 workspace / tool 设计 |
| 生成式 Agent 记忆 | [Generative Agents](https://arxiv.org/abs/2304.03442) | Memory retrieval、reflection 与 consolidation 的研究背景 |

研究论文的模型、数据集和实验条件有边界。应把可验证的工程假设带到自己的任务集，而不是直接复制排行榜结论。

## 本地资料

- [[roadmap|AI Agents Roadmap]]
- [[prompt-engineering/10-context-and-instruction-architecture|上下文与指令架构]]
- [[prompt-engineering/12-tools-state-and-authorization|工具、状态与授权边界]]
- [[prompt-engineering/13-decomposition-and-agent-workflows|任务拆解与 Agent 工作流]]
- [[llm-basic/03-inference-context-and-efficiency|推理、Context 与效率]]
- [[llm-basic/08-using-assistant-models-in-agents|在 Agent 中正确使用 Assistant Model]]
- [[agent-skills/prompt-engineering/references/long-context.md|Long Context 参考]]
- [[agent-skills/prompt-engineering/references/runtime.md|Runtime 参考]]

## 复查协议

复查本系列时：

1. 打开全部官方链接，确认 URL、弃用和模型/API 变化。
2. 检查窗口、缓存、状态、工具和文件保留相关说明。
3. 只把跨供应商稳定原则提升到主题正文。
4. 把具体数字、字段和价格保留在供应商小节并注明日期。
5. 用目标模型和真实任务重新运行长上下文、retrieval、cache 和 recovery eval。
6. 更新 `last_reviewed`，不把未访问的来源标为已核验。

## 常见误区

- **把当前模型限制写成永久原则**：窗口、价格、缓存和 API 字段会变化。
- **只看一家供应商文档**：平台特性容易被误写成跨模型规律。
- **论文结论没有实验边界**：数据集和模型差异会改变效果。
- **链接存在就标记为已核验**：还需读取内容并确认与正文表述一致。
- **更新数字却不重新运行 eval**：API 变化可能同时改变质量、延迟和成本。

## 检查表

- [ ] 核心正文只包含跨供应商相对稳定的原则。
- [ ] 模型、API、窗口、缓存和价格信息标明供应商与复查日期。
- [ ] 全部官方链接可访问且未被弃用页面替代。
- [ ] 研究结论保留任务、模型和实验条件边界。
- [ ] 本地文档的 wikilinks 可以解析。
- [ ] 更新供应商说明后重新运行相关 eval。

## 来源状态

| 来源 | 最后复查 | 状态 |
|---|---|---|
| OpenAI 官方指南 | 2026-07-18 | URL 已记录；当前命令行访问返回 HTTP 403，正文未依赖易变数值 |
| Anthropic Claude 官方指南 | 2026-07-18 | URL 与本地已复查资料一致；当前网络请求超时 |
| Google Gemini 官方指南 | 2026-07-18 | HTTP 200，可访问 |
| arXiv 研究论文 | 2026-07-18 | HTTP 200；结论需按实验条件使用 |
| 本地 `prompt-engineering/` 与 `llm-basic/` | 2026-07-18 | 已读取 |

## 相关笔记

- [[00-overview|上下文工程总览]]
- [[03-context-window-management|Context Window Management]]
- [[11-memory-engineering|Memory Engineering]]
- [[12-retrieval-engineering|Retrieval Engineering]]
- [[13-tool-context|Tool Context]]
- [[15-workspace-context|Workspace Context]]
