---
title: 主流 Agent 框架与 Memory 产品映射
aliases:
  - Agent Framework Comparison
  - Memory Frameworks
tags:
  - agents
  - frameworks
  - memory
  - state
status: active
created: 2026-07-23
last_reviewed: 2026-07-23
sources:
  - "[[memory-and-state/99-sources|资料与来源]]"
---

# 主流 Agent 框架与 Memory 产品映射

> [!abstract] 本篇学习终点
> 你将不再用“哪个框架有 memory”来选型，而是先列出需要的原语，再看 LangGraph、OpenAI Agents SDK、Google ADK、Microsoft Agent Framework、Mem0、Zep、Letta 和 Temporal 分别提供了什么、没有提供什么，以及如何组合。

## 先建立共同接口

不管产品叫什么，一个可恢复 Agent 通常需要以下接口：

```text
TaskStateStore
  get(task_id, version?)
  commit(candidate, expected_version)
  append_event(event)
  checkpoint(task_id)

MemoryStore
  put(candidate)
  search(query, scope, filters, limit)
  supersede/delete(memory_id)

ArtifactStore
  put(bytes, metadata) -> artifact_ref
  get(artifact_ref, span?)

ExecutionRuntime
  run(step)
  retry/reconcile(idempotency_key)
  pause/resume(interruption_id)
```

框架的价值在于减少实现这些接口的成本、提供 tracing、HITL（Human-in-the-Loop，人工在环）、部署和生态；它不会自动替你定义业务事实、租户边界、删除策略或副作用幂等。

## LangGraph：图状态 + Checkpointer + Store

LangGraph 官方把持久化分成两套：

- **Checkpointer** 按 `thread_id` 保存 graph state checkpoints，支持对话连续性、HITL、time travel 和故障恢复；
- **Store** 保存 graph state 之外的 key-value data，跨 thread 访问用户偏好、事实和共享知识。

它对应本系列的：

```text
thread_id → Task/Thread State + Checkpoint
Store namespace → Long-term Memory
PostgresSaver/Store → 持久化 owner
```

`InMemorySaver`/`InMemoryStore` 适合开发；生产应使用持久后端，并处理 checkpoint retention、subgraph namespace 和跨 graph 共享。LangGraph 很适合显式状态图、条件分支、interrupt/resume 和可检查节点；如果只是简单聊天，直接用 SDK session 可能更轻。

## OpenAI Agents SDK：选择唯一的 Conversation State Owner

Agents SDK 的 Session 会在每次 run 前读取历史、拼接新输入，run 后保存新 item；可用 `SessionSettings` 限制历史，使用 callback 裁剪/重排，并有 SQLite、Redis、SQLAlchemy、MongoDB、Dapr 等实现。

它还支持 OpenAI Conversations API 的 `conversation_id` 或 Responses 的 `previous_response_id` 链。关键不是哪一种“更先进”，而是**一轮 conversation 只选择一个 owner**：

```text
应用 replay / SDK Session / server conversation chain
三选一；RunState resume 另用于恢复中断的同一次 run。
```

SDK Session 解决对话历史，不自动解决跨用户 semantic memory、业务审批 State 或外部副作用。可以把它和 Mem0/自建 MemoryStore 组合，但要避免两个 history writer 重复保存相同 item。

## Google ADK：Session、State、MemoryService 三件套

Google ADK 的概念划分很清晰：

- `Session` 保存单一 conversation 的 Events；
- `session.state` 保存当前会话 scratchpad；
- `MemoryService` 提供跨 session 的可搜索长期知识。

State key prefix 还能表达 scope：无前缀是 session，`user:` 跨用户 sessions，`app:` 跨应用，`temp:` 仅当前 invocation。官方建议通过 Context state 并随 event append 更新，避免直接修改从服务取出的 Session 对象绕过 event tracking。

ADK 适合需要多语言 SDK、Gemini/Vertex 生态和显式 session/memory service 的团队；仍需自己定义业务 State schema、权限、事件保留和高风险动作的幂等。

## Microsoft Agent Framework：Session + Context Provider + Workflow

Microsoft 当前的 Agent Framework 将 agent 调用、`AgentSession`、context providers 和 workflows 组合起来。可以把它映射为：

- Session：对话/运行时上下文容器；
- Context provider：从 State/Memory 选择并注入个性化信息；
- Workflow：有类型接口的多步骤编排和执行边界。

由于 API 和版本仍在快速演进，教程只依赖这一层语义，不把某个 preview 方法名当作长期契约。Azure/.NET 团队可用它减少平台集成工作；跨云或需要精细 durable replay 时，仍应把业务 State 和 workflow owner 明确留在自己的数据模型中。

## 其他常见编排框架放在哪一层

下面这些框架也常出现在生产选型中，但它们的核心价值更多是编排、工具和数据接入，不会自动替你完成 Memory/State 治理：

| 框架 | 更擅长的层 | 记忆/状态要自己确认的部分 |
|---|---|---|
| **AutoGen** | 多 Agent 对话、team/group-chat、事件/图式协作 | 线程历史、团队状态和副作用恢复是否由当前版本/后端持久化；不要把聊天记录当业务 State |
| **CrewAI** | Role-based agents、Crews 与 Flows，快速验证协作流程 | Flow state、任务重试和长期 Memory 的 owner；高风险动作仍需外部授权与幂等 |
| **LlamaIndex Workflows** | 事件驱动工作流、RAG/数据密集管线 | 文档检索不是当前 task State；跨进程恢复、checkpoint 和删除策略需要单独设计 |
| **PydanticAI** | 类型安全的依赖注入、结构化输出和工具契约 | 类型校验不等于持久化/授权；需接入自己的 StateStore、MemoryStore 和 durable runtime |
| **Semantic Kernel** | .NET/Python 的 plugins、planner 和企业服务集成 | memory connector 的语义、版本和权限随后端变化；业务事实仍由领域系统拥有 |

选型时把它们放回前面定义的四层：编排框架负责 loop/工具/路由，StateStore 负责当前真值，MemoryStore 负责跨任务候选，Workflow Engine 负责长时恢复。这样即使框架更名、合并或替换，核心设计仍然成立。

## Mem0：抽取式 Memory Layer

Mem0 典型调用是：

```text
add(messages, scope) → 抽取/去重/写入事实和索引
search(query, scope) → semantic + keyword + temporal/entity 候选
```

它适合快速加入 user/project memory，支持 managed Platform 或 self-hosted OSS（Open Source Software，开源自托管）形态。官方文档把 SQL facts/metadata 作为 source of truth，把 vector/entity store 当检索层；默认 additive 写入，纠正和删除使用显式操作。

不要让 Mem0 代替订单、权限或 workflow State。它适合作为 `MemoryStore` 实现，仍需由你的 harness 负责当前任务约束、授权和 memory candidate policy。

## Zep / Graphiti：时间知识图谱型 Memory

Zep 将用户、线程、事实、实体和关系组织成 temporal Context Graph，并生成带有效/失效时间的 Context Block。它适合：

- “某个事实在什么时候成立？”；
- 实体关系和多跳查询；
- 需要保留历史但不让旧事实冒充当前值。

代价是图摄取、schema 和查询语义更复杂；简单偏好列表或严格事务状态不必使用图。

## Letta：可读、版本化、Agent-owned Memory

Letta 的核心假设是 agent identity 跨 conversation 持续存在，长期记忆放在 git-backed MemFS：

- `system/` 文件作为每轮热上下文；
- 其他目录按需加载，形成冷存档；
- 每次编辑提交 git，可回滚、审计、合并；
- dreaming/memory doctor 异步整理和反思。

它非常适合个人助理、coding agent 的身份/项目约定和程序性知识。它不是高吞吐、强事务的业务 State 库；若 agent 需要发付款或维护订单，仍需外部 authoritative store。

## Temporal：把长任务交给 Durable Execution

Temporal 不是 Memory 产品，而是 durable workflow runtime：Event History 保存命令产生的事件，worker 崩溃后 replay 恢复 workflow state，Activity 承担外部副作用。

适合：长时间等待、定时器、人工审批、重试、跨服务编排和需要明确恢复语义的任务。不要因为 Agent 有多轮对话就自动上 Temporal；短对话可由数据库 session/checkpointer 解决。使用 Temporal 时仍需把业务事实、用户 memory 和 artifact 放在合适的 store，不能把 workflow Memo 当关键执行状态。

## 一张选型表

| 首要问题 | 优先考虑 | 仍需自己补上的边界 |
|---|---|---|
| 图式工作流、interrupt、checkpoint | LangGraph | 业务 schema、memory policy、外部副作用幂等 |
| OpenAI 模型上的轻量多轮工具 Agent | OpenAI Agents SDK Session | 长期 memory、任务 State owner、授权 |
| Gemini/Vertex、多语言 session/memory | Google ADK | 生产数据库、删除传播、workflow durability |
| Azure/.NET 的 agent + workflow | Microsoft Agent Framework | 稳定业务 State 与版本锁定 |
| 快速 user/project facts | Mem0 | 事实权威、scope、冲突、删除和高风险状态 |
| 时间关系、多跳用户上下文 | Zep/Graphiti | 事务 State、成本和图 schema |
| 可读、可版本化的 agent identity/memory | Letta/MemFS | 业务系统权威状态和并发事务 |
| 跨小时/天的可靠编排 | Temporal | memory/retrieval、领域数据模型和 UI |

## 组合范式：不要让产品互相抢 owner

一个合理的组合可能是：

```text
LangGraph / Agents SDK / ADK 负责单次 Agent Loop
→ PostgreSQL 负责 Task State、事件和 Memory metadata
→ Mem0 或自建检索层负责长期 Memory retrieval
→ Object Storage 负责 artifacts
→ Temporal（必要时）负责长时 workflow 和副作用恢复
```

组合时写下“谁是 owner”：

- conversation history 由哪个 session/replay 机制拥有？
- current task State 由哪个数据库/graph checkpoint 拥有？
- long-term Memory 的事实由哪个 store 拥有，索引如何重建？
- external side effect 的最终状态由哪个业务系统拥有？

如果一个字段有两个 writer，却没有 reconciliation 规则，系统迟早会出现重复、丢失或互相覆盖。

## 迁移和版本策略

框架 API 会变，业务数据不能绑死在框架内部序列化格式。建议：

1. 在应用边界定义自己的 Task/Memory/Artifact Contract；
2. 编写 adapter，把框架 checkpoint/session 映射到 Contract；
3. 保存 `schema_version` 和 `framework_version`；
4. 迁移时先双写/回放验证，再切换读取 owner；
5. 保留原始事件和 artifact，避免只能依赖旧 SDK 解码。

> [!warning] 产品名不是架构
> “用了 LangGraph”不代表任务一定可恢复；“接了 Mem0”不代表 memory 一定可靠；“用了 Temporal”也不代表用户偏好有正确 scope。可靠性来自 owner、schema、证据、版本和测试，而不是依赖列表。

> [!success] 自测
> 一个团队同时使用 OpenAI SDK Session、Redis chat history 和 OpenAI `conversation_id`，为什么容易重复上下文？请指出应保留哪个 owner，以及另外两个如何降级为 cache/迁移工具或被移除。

下一篇进入不可回避的边界：[[memory-and-state/08-security-governance|安全、隐私与治理]]。
