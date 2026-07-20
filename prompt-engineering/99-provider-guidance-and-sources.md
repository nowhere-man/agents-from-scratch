---
title: 官方指南
aliases:
  - Provider Guidance and Sources
  - OpenAI Gemini Anthropic Prompting 对照
tags:
  - prompt-engineering
status: active
created: 2026-07-16
last_reviewed: 2026-07-16
sources:
  - https://developers.openai.com/api/docs/guides/prompt-engineering
  - https://developers.openai.com/api/docs/guides/prompting
  - https://ai.google.dev/gemini-api/docs/prompting-strategies
  - https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview
---

# 官方指南

> [!important] 一句话核心
> 三家官方文档共同支持“清晰任务、相关上下文、必要示例、可验证迭代”，但消息层级、模型推理、参数和 API 能力属于供应商与版本特性，必须单独验证。

## 来源策略

本系列不是三家文档的翻译，而是：

1. 用本地资料建立工程问题框架。
2. 用三家官方资料交叉验证稳定原则。
3. 将当前 API、模型和参数建议隔离在本篇。
4. 当官方建议变化时，优先更新本篇的差异说明和 `last_reviewed`。

稳定正文不依赖具体模型名称、价格、context window 数字或 sampling 默认值。

## 跨供应商共识

| 共识 | 在本系列中的落点 |
|---|---|
| 指令应清晰、具体并定义输出要求 | [[01-task-contract]]、[[02-minimum-effective-prompt]] |
| 提供完成任务所需的相关上下文 | [[10-context-and-instruction-architecture]] |
| 示例可以定义格式、边界和风格 | [[02-minimum-effective-prompt]] |
| 复杂任务可以拆解或 chaining | [[13-decomposition-and-agent-workflows]] |
| Prompt 需要迭代和测试 | [[14-evaluation-and-iteration]] |
| 不同模型和版本需要重新验证 | [[15-production-lifecycle]] |
| 结构化输出和工具需要 API/程序配合 | [[11-structured-output-and-determinism]]、[[12-tools-state-and-authorization]] |

这些共同点是本系列主线的依据，但具体实现仍取决于目标 API 和模型。

## OpenAI

### 当前官方重点

- 使用不同消息角色或 `instructions` 表达不同优先级的指令。
- Prompt 行为会随模型类型和快照变化，生产应用需要测试和 eval。
- 使用 Markdown、XML 等结构分隔身份、指令、示例和上下文。
- Few-shot 用于展示输入输出映射和行为模式。
- 相关上下文可通过检索或文件工具提供。
- Structured Outputs、function calling 和 eval 是 prompt 之外的重要系统机制。
- 当前 Prompting 指南倾向把生产 prompt 作为代码模块管理，用类型化参数、Git、测试和部署流程维护。

### 需要隔离的易变内容

- 当前推荐模型及不同模型类型的 prompting 方法。
- Responses API 的具体字段和状态语义。
- Reusable prompt 对象等平台功能的生命周期。
- Structured Outputs 和 tool calling 的具体 schema 支持范围。

### 官方来源

- [Prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering)
- [Prompting](https://developers.openai.com/api/docs/guides/prompting)
- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [Evals](https://developers.openai.com/api/docs/guides/evals)

## Google Gemini

### 当前官方重点

- 明确输入类型、约束和 response format。
- 使用具体且多样的 few-shot 示例，并保持示例结构一致。
- 提供模型解决问题所需的上下文。
- 复杂任务可以拆为独立指令、顺序链或并行聚合。
- Prompt design 是迭代过程，需要根据实际模型响应实验。
- 长上下文中，当前指南建议先提供材料，再在末尾给出具体问题，并用清晰过渡语锚定任务。
- 当前 Gemini 指南还包含多模态、thinking、sampling parameters 和 agentic workflow 的专属建议。

### 需要隔离的易变内容

- Gemini 特定系列的参数默认值和 thinking 行为。
- “总是加入 few-shot”等面向当前 Gemini 的强建议。
- 当前模型的长上下文、知识截止时间和 grounding 提示模板。
- Structured output 与 function calling 的具体支持范围。

> [!warning] Gemini 专属建议不是跨模型通则
> Google 当前指南对 few-shot 给出较强建议；本系列保留为 Gemini 专属实践。跨供应商方法仍从直接 baseline 开始，通过 eval 决定是否需要示例。

### 官方来源

- [Prompt design strategies](https://ai.google.dev/gemini-api/docs/prompting-strategies)
- [Structured output](https://ai.google.dev/gemini-api/docs/structured-output)
- [Function calling](https://ai.google.dev/gemini-api/docs/function-calling)

## Anthropic Claude

### 当前官方重点

- Prompt engineering 前先定义成功标准、建立可测试方法并准备 baseline。
- 并非所有失败都应由 prompt 修复；成本和延迟可能更适合通过模型选择解决。
- 通用技巧包括清晰直接、解释约束背景、使用示例、XML 标签和角色。
- 当前最佳实践还覆盖长上下文、输出格式、tool use、thinking、agentic state、安全和复杂任务 chaining。
- Tool use 和 eval 有独立的官方指南，不应只从 prompt 文案理解。

### 需要隔离的易变内容

- 不同 Claude 型号的专属 prompting 和迁移建议。
- Thinking、prefill、tool use 和长上下文行为。
- Claude Console 中 prompt generator、improver 等平台工具。

### 官方来源

- [Prompt engineering overview](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview)
- [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
- [Define success criteria and build evaluations](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests)
- [Tool use overview](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)

## 差异如何处理

### 消息角色不同

不同 API 对 system、developer、user 或 system parameter 的支持和优先级不同。正文使用“高优先级稳定规则”和“当前请求”的抽象职责；实现时查目标供应商当前 API。

### 推理提示不同

部分模型自动进行内部推理，部分模型更依赖显式步骤说明。不要要求输出私有思维过程；需要可检查性时，要求依据、假设、阶段产物、来源或程序验证。

### Few-shot 强度不同

示例对分类、格式和边界任务通常有效，但上下文成本和模型行为不同。本系列不规定通用数量，也不把 few-shot 设为所有任务默认项。

### 长上下文顺序不同

供应商对材料和问题的推荐顺序可能随模型演进。采用“有来源的材料 + 明确的最终任务”作为 baseline，再用目标模型和真实长输入比较顺序。

### Schema 和 Tool API 不同

支持的 JSON Schema 子集、严格模式、并行调用、结果消息和错误处理各不相同。正文只定义系统原则，代码实现必须查当前 API reference。

## 本地资料

### 仓库 Skill

- [[agent-skills/prompt-engineering/SKILL.md|Prompt Engineering Skill]]
- [[agent-skills/prompt-engineering/references/patterns.md|Prompt Patterns]]
- [[agent-skills/prompt-engineering/references/long-context.md|Long Context 与消息分层]]
- [[agent-skills/prompt-engineering/references/runtime.md|Runtime：Retrieval、State 与 Tool Calling]]
- [[agent-skills/prompt-engineering/references/evaluation.md|Prompt Evaluation]]

## 复查协议

复查本篇时：

1. 访问全部官方链接并确认规范 URL。
2. 检查当前模型、API 和弃用信息是否变化。
3. 只把跨供应商长期一致的结论提升到核心正文。
4. 将模型专属建议留在本篇，并写明供应商和日期。
5. 更新 `last_reviewed`，不伪造未实际核验的状态。

## 来源状态

| 来源                                | 最后核验       | 状态  |
| --------------------------------- | ---------- | --- |
| OpenAI 官方指南                       | 2026-07-16 | 可访问 |
| Google Gemini 官方指南                | 2026-07-16 | 可访问 |
| Anthropic Claude 官方指南             | 2026-07-16 | 可访问 |
| `agent-skills/prompt-engineering` | 2026-07-16 | 已读取 |

## 相关笔记

- [[prompt-engineering/00-overview|提示词工程总览]]
- [[10-context-and-instruction-architecture|上下文与指令架构]]
- [[11-structured-output-and-determinism|结构化输出与确定性保证]]
- [[14-evaluation-and-iteration|Prompt 评估与迭代]]
- [[15-production-lifecycle|Prompt 的生产生命周期]]
