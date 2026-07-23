---
title: Agent Harness 资料与来源
aliases:
  - Harness Sources
  - Agent Runtime References
tags:
  - agents
  - harness
  - sources
status: active
created: 2026-07-23
last_reviewed: 2026-07-23
---

# Agent Harness 资料与来源

> [!abstract] 证据范围
> 本系列在 2026-07-23 核对官方规范、官方框架文档、官方仓库与原始论文。正文把跨实现重复出现的语义写成工程原则；具体 API、默认值、preview、experimental、Development 或 public draft 状态只作为当前实现例子，使用前应重新核对链接。

## 怎样理解“截至当前的最佳实践”

这里的“最佳实践”不是把某一家框架的默认配置宣布为永久标准，而是按证据强度分三层：

1. **稳定工程不变量**：最小权限、结构化校验、幂等、unknown/reconcile、checkpoint、隔离、审计和故障测试；可从多个独立实现与安全规范交叉验证。
2. **当前共同模式**：Runner、graph、Plugin、Activity、effect ledger、trajectory eval 等；接口名不同，但 owner 与失败边界相近。
3. **版本敏感实现**：某个类名、装饰器、默认工具、trace 字段或 preview 功能；只在 [[harness/10-framework-map|框架地图]] 中映射，不当作定义。

## 仓库内前置资料

- [[llm-basics/31-llm-capabilities-boundaries-and-agents|LLM 能力边界与 Agent]]：模型提出候选、Runtime 掌握循环控制权。
- [[context-engineering/00-overview|Context Engineering]]：本轮可见信息的选择、预算与组装。
- [[context-engineering/13-tool-context|Tool Context]]：工具定义、结果压缩与不可信数据边界。
- [[context-engineering/14-planning-context|Planning Context]]：目标、计划、checkpoint 和完成审计。
- [[memory-and-state/00-overview|Memory 与 State 管理]]：Context、State、Memory、Artifact/Event 的权威边界。
- [[memory-and-state/04-turn-pipeline|一次 Agent Turn 的读写管线]]：read→assemble→act→commit。
- [[memory-and-state/06-consistency-recovery|一致性、并发与恢复]]：事务、CAS、幂等和未知副作用。
- [[memory-and-state/10-reference-implementation|Memory/State 参考实现]]：可恢复研究 Agent 的数据层骨架。
- [[prompt-engineering/00-overview|Prompt Engineering]]：任务契约、structured output、tool/state 与 eval 的分工。
- [[blogs/building-effective-agents|Building Effective Agents]]：先用最简单可评估方案，再按需要增加 workflow/agent；原始文章来源为 Anthropic Engineering。

## OpenAI Agents SDK：Runner、Tool、State 与 Trace 边界

官方仓库的 `.agents/references` 是本系列关于 Runner lifecycle 的主要当前依据：

- [References 目录](https://github.com/openai/openai-agents-python/tree/main/.agents/references)
- [Runner lifecycle](https://github.com/openai/openai-agents-python/blob/main/.agents/references/runner-lifecycle.md)：turn、NextStep、guardrail、stream/non-stream、取消和清理。
- [Tool execution lifecycle](https://github.com/openai/openai-agents-python/blob/main/.agents/references/tool-execution-lifecycle.md)：discovery、approval partition、invocation、并发与恢复。
- [Function and output schema](https://github.com/openai/openai-agents-python/blob/main/.agents/references/function-and-output-schema.md)：provider schema、参数重建、strictness 与 output validation。
- [RunState schema](https://github.com/openai/openai-agents-python/blob/main/.agents/references/runstate-schema.md)：版本、稳定 identity、resume boundary 与 secret 处理。
- [Session persistence](https://github.com/openai/openai-agents-python/blob/main/.agents/references/session-persistence.md)：model view、持久候选、完整 history、原子 append 与 compaction。
- [Tracing lifecycle](https://github.com/openai/openai-agents-python/blob/main/.agents/references/tracing-lifecycle.md)：run/model/tool/session/error trace 与 exporter 隔离。
- [Sandbox runtime boundary](https://github.com/openai/openai-agents-python/blob/main/.agents/references/sandbox-runtime-boundary.md)：Runner/session owner、workspace snapshot、路径、mount、credential 与 cleanup。

这些文档描述 SDK 当前实现契约，正文提取其稳定语义，不保证未来 API 名称不变。

## LangGraph：Graph persistence 与 interrupt

- [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)：thread-scoped checkpointer 与 cross-thread Store 的分工。
- [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)：稳定 `thread_id`、pause/resume，以及恢复从 node 起点重新执行的副作用要求。
- [Durable execution](https://docs.langchain.com/oss/python/langgraph/durable-execution)：graph 任务的持久执行与 replay 约束。

## Google ADK：Runner Plugin、Workflow、安全与 Eval

- [Plugins](https://adk.dev/plugins/)：Runner 级 agent/model/tool callbacks，适合全局 policy、trace、metrics 和 caching。
- [Template agent workflows](https://adk.dev/agents/workflow-agents/)：deterministic sequential、parallel、loop；文档同时指向 Python/Go 2.0 graph/dynamic workflow。
- [Safety and Security for AI Agents](https://adk.dev/safety/)：identity/authorization、tool guardrail、sandbox、trace/eval、network perimeter 与 UI escaping。
- [Evaluate Agents](https://adk.dev/evaluate/)：trajectory/tool use 与 final response 的双层评测。
- [Sessions](https://adk.dev/sessions/)：session、state 与 memory 的官方边界。

## Pydantic AI Harness：2026 年直接使用 Harness 命名的实现

总索引：[Pydantic AI `llms.txt`](https://pydantic.dev/docs/ai/llms.txt)。相关页面均明确提示 API 可能跨版本变化：

- [Step Persistence](https://pydantic.dev/docs/ai/harness/step-persistence/)：append-only events、provider-valid snapshots、tool-effect ledger、`unknown_after_crash`。
- [Guardrails](https://pydantic.dev/docs/ai/harness/guardrails/)：allow/block/replace/retry，以及 streaming 无法事后撤回。
- [FileSystem](https://pydantic.dev/docs/ai/harness/filesystem/)：固定 root、symlink-safe containment、protected patterns 与 optimistic concurrency。
- [Shell](https://pydantic.dev/docs/ai/harness/shell/)：command policy、环境清理、timeout、输出截断和后台进程；文档明确 denylist 不是硬安全边界。
- [Overflowing Tool Output](https://pydantic.dev/docs/ai/harness/overflowing-tool-output/)：truncate、spill 与 summarize。
- [Compaction](https://pydantic.dev/docs/ai/harness/compaction/)：clear、dedupe、trim、summarize 等上下文策略。
- [Subagents](https://pydantic.dev/docs/ai/harness/subagents/)：命名 delegate、独立 budget 与 failure handling。
- [Dynamic Workflow](https://pydantic.dev/docs/ai/harness/dynamic-workflow/)：sandboxed orchestration script、`max_agent_calls`、token/resource budgets。

## Microsoft Agent Framework、AutoGen 与 CrewAI

### Microsoft Agent Framework

- [Overview](https://learn.microsoft.com/en-us/agent-framework/overview/)（页面日期 2026-07-08）：明确区分 Agents、Harness、Workflows。
- [Agent Harnesses](https://learn.microsoft.com/en-us/agent-framework/agents/harness)：function loop、per-service-call history、compaction、todo/mode、file/memory、approval、OpenTelemetry 与可选 background agents/Shell。
- [Workflows](https://learn.microsoft.com/en-us/agent-framework/workflows/)：type-safe graph、checkpoint、HITL、functional 与 graph API。

官方文档将 Agent Framework 描述为 AutoGen 与 Semantic Kernel 的后继整合方向；Go 和部分工作流能力存在语言差异或 preview，应按当前页面核对。

### AutoGen

- [AutoGen Core User Guide](https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/index.html)：Actor model、异步消息、agent identity/lifecycle、local/distributed runtime 与 trace。

### CrewAI

- [Agents](https://docs.crewai.com/en/concepts/agents)：role、goal、tools 和执行配置。
- [Tasks](https://docs.crewai.com/en/concepts/tasks)：任务依赖、输出与 human input。
- [Flows](https://docs.crewai.com/en/concepts/flows)：event-driven state、条件、循环、分支和跨 Crew 编排。
- [Checkpointing](https://docs.crewai.com/en/concepts/checkpointing)：crew/flow/agent 恢复的当前实现。

## Durable Workflow：Temporal

- [Temporal Workflows](https://docs.temporal.io/workflows)：Event History、deterministic replay，以及 LLM/API/DB/File I/O 放入 Activity 的原则。
- [Temporal Activities](https://docs.temporal.io/activities)：外部活动、timeout、retry 与幂等要求。

Temporal 是通用 durable execution engine，不替代 Agent 的 model/tool/policy layer；它适合作为长时 Harness 的外层控制面。

## MCP 与 Agent Skills

### Model Context Protocol

- [Tools — Specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)：tool discovery/call、JSON Schema、output schema、task support、人审提示与不可信 annotations。
- [Authorization — Specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)：OAuth 2.1、resource/auth server discovery、scope 与 client registration。
- [Security Best Practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices)：confused deputy、token passthrough、SSRF、session hijacking、consent、redirect URI 和 OAuth state。

MCP 规范本身不拥有应用的 loop、真实授权、sandbox 或 State commit；这些仍由 Host/Harness 实现。

### Agent Skills

- [Agent Skills Specification](https://agentskills.io/specification)：`SKILL.md`、必填 metadata、scripts/references/assets 与 progressive disclosure；`allowed-tools` 当前标记为 experimental。
- [Anthropic Skills repository](https://github.com/anthropics/skills)：官方示例能力包；仓库明确示例主要用于教育/演示，不能当作产品行为保证。

## Observability

- [OpenTelemetry GenAI Semantic Conventions repository](https://github.com/open-telemetry/semantic-conventions-genai)：GenAI conventions 已从主 semantic-conventions 仓库迁移到此处。
- [GenAI agent spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md)：`create_agent`、`invoke_agent`、`invoke_workflow`、`plan`、`execute_tool`；当前状态为 Development。

System instructions、input/output messages、tool definitions/arguments/results 等内容字段具有 opt-in 或敏感属性；实现仍需单独审计 exception、log 和 traceback。

## Security 与治理

- [OWASP Agentic AI Threats and Mitigations](https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/)：Agentic Security Initiative 的威胁入口。
- [OWASP Agentic Top 10 — 1st Public Draft](https://github.com/GenAI-Security-Project/GenAI-Agent-Security-Initiative/tree/main/agentic-top-10/Sprint%201-first-public-draft-expanded)：behaviour hijack、tool misuse、identity/privilege、supply chain、RCE、memory/context poisoning、inter-agent communication、cascading failures、human trust、rogue agents。它是 public draft，且部分展开页仍为占位内容，只用于威胁覆盖检查。
- [NIST AI RMF Generative AI Profile, NIST AI 600-1](https://doi.org/10.6028/NIST.AI.600-1)：Generative AI 风险画像与 AI RMF 配套资源。
- [NIST AI RMF Playbook](https://airc.nist.gov/airmf-resources/playbook/)：Govern、Map、Measure、Manage 的建议；官方明确它不是需要完整执行的 checklist。

## Agent 设计与推理模式的原始资料

- [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)：workflow 与 autonomous agent 的简化优先原则；本轮官方页面直连超时，仓库已有 [[blogs/building-effective-agents|本地保存笔记]] 可核对正文。
- [ReAct](https://arxiv.org/abs/2210.03629)：reasoning 与 action 交错，使用环境 Observation 更新下一步。
- [Plan-and-Solve Prompting](https://arxiv.org/abs/2305.04091)：先规划子任务，再执行。
- [Reflexion](https://arxiv.org/abs/2303.11366)：以语言反馈和 episodic memory 改进后续尝试，不更新模型权重。
- [Tree of Thoughts](https://arxiv.org/abs/2305.10601)、[Graph of Thoughts](https://arxiv.org/abs/2308.09687)、[LATS](https://arxiv.org/abs/2310.04406)：候选 thought/trajectory 的搜索、评估、合并与回溯。

这些论文支持 [[harness/06-orchestration-patterns|编排与搜索策略]] 的概念来源；论文实验收益不能直接外推为生产收益，仍需在自己的任务、模型、工具和预算下评测。

## 最后一次版本检查

正式采用某个框架前，至少重新核对：

- 页面/包版本与发布日期；
- stable、preview、experimental、Development 或 public draft 状态；
- Python/.NET/Go/TypeScript 等语言能力是否一致；
- 默认 tool、approval、trace content、sandbox 和 retry 行为；
- checkpoint 是否真的覆盖 workspace/provider session/tool effects；
- breaking change、migration 与数据兼容策略。

本系列的稳定结论不依赖某个类名：模型提出候选，Harness 执行 Contract；外部副作用必须可确认，恢复必须从安全边界开始，权限必须由真实系统强制执行。
