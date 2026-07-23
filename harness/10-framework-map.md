---
title: Agent Harness 框架地图
aliases:
  - Agent Framework Map
  - Harness Runtime Comparison
tags:
  - agents
  - harness
  - frameworks
  - runtime
status: active
created: 2026-07-23
last_reviewed: 2026-07-23
sources:
  - "[[harness/99-sources|资料与来源]]"
---

# 框架地图：把产品 API 映射回稳定的 Harness Contract

> [!abstract] 本篇学习终点
> 你将能判断各框架主要解决 loop、session、graph、message runtime、durability、tool protocol 还是 capability packaging；能按项目压力选层，而不是按功能列表选“最全框架”。以下状态核对截至 2026-07-23，preview/development API 必须再次查阅官方文档。

## 先确定比较坐标

我们不比较“谁最好”，只问每个方案拥有哪一部分控制权：

1. Run/turn loop；
2. typed schema 与 tool lifecycle；
3. session/checkpoint/resume；
4. graph、handoff 和多 Agent；
5. durable replay 与外部 activity；
6. sandbox/workspace；
7. policy、approval、trace/eval；
8. 协议或能力包，而非 runtime。

## 当前方案映射

| 方案 | 主要形态 | 最强原语 | 关键边界/注意 |
|---|---|---|---|
| OpenAI Agents SDK | SDK Runner / session runtime | Agent、tools、guardrails、handoff、sessions、tracing、Runner state machine | discovery/approval/invocation、stream/non-stream、cancel/resume identity 要作为同一 contract；具体 API 随版本核对 |
| LangGraph | stateful graph runtime | graph、checkpointer、interrupt、thread、Store | resume 会从 node 起点重跑；checkpointer 是 thread state，Store 是跨 thread 数据 |
| Google ADK | Agent + graph/workflow + Runner plugins | workflow、callbacks/plugins、session/state/memory、eval | 全局 policy 更适合 Runner Plugin；routing/dynamic 能力需看当前语言与实验状态 |
| Pydantic AI Harness | typed capability/harness layer | guardrails、filesystem/shell、compaction、step persistence、subagents/dynamic workflow | Harness API 多处明确可能变化；command denylist 不是 sandbox，step persistence 不是完整 graph checkpoint |
| Microsoft Agent Framework | Agent + opinionated Harness + graph workflow | batteries-included Harness、middleware、session、type-safe workflow、checkpoint/HITL | 2026-07 文档直接区分 Agent/Harness/Workflow；部分语言/功能仍 preview，应用仍自负安全与可靠性 |
| AutoGen Core | actor/message runtime | async messages、agent identity/lifecycle、local→distributed runtime | 适合事件驱动多 Agent；消息、权限、背压和分布式状态成本较高；Microsoft 将 Agent Framework 定位为其后继方向 |
| CrewAI | role-based Crews + event-driven Flows | Agents/Tasks、Crews、Flow state/branch/HITL | Role/Task 是能力声明，Flow 才是控制面；避免让 role 描述替代真实 policy |
| Temporal | durable workflow engine | Event History、deterministic replay、Activity、timeout/retry | LLM/API/DB/File I/O 应作为 Activity；它不是 Agent prompt/tool SDK，需要与 Agent runtime 组合 |
| MCP | tool/resource/prompt protocol | Host–Client–Server 互操作、capability discovery | 不拥有你的 run loop、授权或 sandbox；必须处理 consent、scope、token、SSRF 与 session 安全 |
| Agent Skills | filesystem capability package/spec | `SKILL.md` + scripts/references/assets，progressive disclosure | Skill 描述“如何做”，不拥有真实权限、State commit 或 loop；`allowed-tools` 当前仍 experimental |

## OpenAI Agents SDK：Runner contract 的参考

其公开 Runner/Tool/RunState/Sandbox/Tracing/Session 参考强调：

- turn 计数、NextStep、guardrail、streaming 与 cancellation 是一个生命周期；
- tool discovery、approval partition 与 invocation 分开；
- resume 保留 agent/tool/call/approval identity，不重复已完成动作；
- strict schema、参数重建与 output validation 属于同一兼容边界；
- serialized state 有 schema version，secret 不进入 State/trace；
- session persistence 区分 model view、持久候选和完整 history。

这些原则可迁移到任何自建 Harness，不要求使用同一个 SDK。

## LangGraph：显式 State graph

当任务需要固定节点、条件边、并行、interrupt 和 checkpoint 时，LangGraph 比隐藏 loop 更容易观察。要特别记住：

- 使用稳定 `thread_id` 恢复；
- checkpointer 保存 thread-scoped execution state；
- Store 保存跨 thread 的长期数据；
- interrupt 后 node 从头执行，因此副作用要可重试或拆出安全边界。

## Google ADK：Runner 级横切能力

ADK 的 Agent callbacks 适合局部组件，Plugin 注册一次后覆盖 Runner 管理的 agent/model/tool 生命周期，适合：

- policy enforcement；
- tracing/metrics；
- caching；
- request/response modification。

Workflow 方面，模板 sequential/parallel/loop 是确定性编排；Python/Go 2.0 文档已引导到更灵活的 graph/dynamic workflow。Eval 同时看 trajectory/tool use 与 final response。

## Pydantic AI 与 Microsoft：直接使用 Harness 命名

Pydantic AI Harness 当前把 filesystem、shell、guardrails、overflow handling、step persistence、subagents 与 dynamic workflow 组织为 capabilities。它很适合观察“横切能力如何插入 typed Agent”，但官方明确 API 仍可能变化。

Microsoft Agent Framework 2026-07 文档把三层直接列为：

- Agent：模型、工具与响应；
- Harness：function loop、每次 service call history、compaction、todo/mode、file memory/access、approval、OpenTelemetry、可选 skills/background agents/shell/loop；
- Workflow：type-safe graph、checkpoint 与 HITL。

这与本系列的边界高度一致，但具体内置默认值仍需按版本审计，尤其是自动审批、Shell 与第三方系统数据边界。

## AutoGen 与 CrewAI：不同的多 Agent 抽象

AutoGen Core 以 actor/message runtime 为中心，适合异步、分布式 Agent 网络。CrewAI 则区分 role-based Crews 与 event-driven Flows；Flow 提供状态、条件、循环和分支。

两者都不能消除多 Agent 的成本：每个 Agent 仍需要最小 Context、独立 identity、tool policy、budget、failure isolation 和 trace lineage。

## Temporal：给 Agent 加 durable 外壳

当 run 跨天、需等待外部事件或协调多个不可靠服务时，可把确定性流程放 Temporal Workflow，把 LLM/tool/API 调用放 Activity：

```text
Temporal Workflow
├─ Activity: 调用 Research Agent 一步
├─ Activity: 抓取供应商 API
├─ wait signal: 人工审批
└─ Activity: 生成并保存报告
```

Workflow replay 不重做已记录 Activity result。Activity 自身仍要幂等并设置 timeout/retry；关键执行状态放 Event History/State，不放 Memo 充当真值。

## MCP 与 Skills：不要把协议/包误认成 Runtime

- MCP 解决 N 个 Host 与 M 个服务之间的标准连接，但 Host/Harness 仍拥有授权与执行控制。
- Skill 解决能力如何被发现、按需加载并携带 instructions/scripts/resources，但激活 Skill 不等于授予系统权限。

它们都可以被多个 Harness 使用，正因为它们没有取代 Harness。

## 选择路径

```text
能用普通函数完成？
├─ 是 → 写函数
└─ 否，需要模型做开放判断？
   ├─ 单 Agent + 少量工具 → 手写 loop 或轻量 SDK Runner
   ├─ 固定分支/并行/HITL → Graph/Flow runtime
   ├─ 分布式消息型多 Agent → Actor/message runtime
   ├─ 跨进程/跨天/可靠重放 → Durable workflow + Agent Activity
   └─ 多租户文件/Shell/浏览器 → 再增加平台 sandbox/policy/observability
```

## 保持可替换的四个 seam

为了避免锁死框架，内部至少保留：

```python
ModelAdapter.generate(context) -> Candidate
ToolAdapter.execute(request, actor) -> Observation
StateStore.load/commit/checkpoint(...)
PolicyEngine.evaluate(stage, subject, context) -> Verdict
```

Graph、SDK、MCP 或 durable engine 都通过 adapter 接入。先固定内部 Contract，再映射外部 API，升级时才不必重写业务真值与安全策略。

下一篇用标准库写出这些 seam：[[harness/11-reference-implementation|最小可恢复 Harness 参考实现]]。
