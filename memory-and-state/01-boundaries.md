---
title: Memory 与 State 的边界：先把“记住”拆开
aliases:
  - Memory State Boundaries
  - 状态与记忆边界
tags:
  - agents
  - memory
  - state
  - concepts
status: active
created: 2026-07-23
last_reviewed: 2026-07-23
sources:
  - "[[memory-and-state/99-sources|资料与来源]]"
---

# Memory 与 State 的边界：先把“记住”拆开

> [!abstract] 本篇学习终点
> 你将能用同一套术语解释一个 Agent 的 context、memory、state、event、snapshot、thread、session、run、checkpoint、artifact、storage、index 和 cache；面对一条新数据，也能判断它应该由谁拥有、保存多久、能否改变系统行为。

## 先看一个冲突

研究 Agent 昨天保存了：

```text
用户喜欢用表格；当前任务正在抓取供应商 A；上次看到的汇率是 7.21；任务 ID 是 research-42；完整 API 响应在 artifact://resp-991。
```

今天用户说：“这次请用要点，不要表格；任务换成 research-43；汇率以央行接口当前值为准。”

这些文字都可能出现在同一条 prompt 里，但它们的处理方式不同：最新用户指令覆盖本次表达格式；research-42 不能成为 research-43 的 pending list；7.21 只能是历史观察；artifact 是可回查原文；用户长期偏好如果仍有价值，可以保留为低优先级 memory，但不能覆盖本次明确要求。

所以“记忆”不是一个数据库表，而是一组**不同所有者、不同生命周期、不同写入权限的数据契约**。

## Context：这一次模型看到了什么

Context 是某一次模型调用实际可见的输入。它可能包含系统规则、用户消息、当前 State 的投影、检索到的 Memory、工具结果摘要和当前动作。

Context 有两个特点：

1. 它是一次性的视图，不是永久存储；
2. 它的内容经过选择和变换，不能反过来证明原始事实已经改变。

一个 memory 只有被检索、通过 scope/权限/新鲜度检查并组装进本轮请求后，才成为 Context。反过来，一段进入 prompt 的文字也不一定有权修改 State。

## State：现在什么为真

State 是系统为了继续执行当前任务而维护的、可验证的当前视图。它回答：

- 任务目标和成功标准是什么？
- 当前处于哪个 phase/step？
- 哪些步骤已经由真实 observation 证明完成？
- 哪些决定、未知项、授权和预算仍然有效？
- 当前 State 的版本是多少，谁能提交下一版？

State 不是“模型想法的 JSON 化”。它必须能绑定来源、版本和不变量。例如：

```yaml
task_id: research-43
version: 12
current_step: compare_vendor_prices
completed_steps:
  - collect_vendor_a
unknowns:
  - exchange_rate_at_2026-07-23T10:00Z
authorization:
  send_email: false
evidence_refs:
  - artifact://vendor-a-response-17
```

`completed_steps` 只能在对应 artifact/test/observation 通过验证后更新。模型说“已经完成”只是 candidate，不是事实。

## Memory：未来可能有用，但不一定永远正确

Memory 是跨 turn、跨 session 或跨 task 保存、未来可被选择性检索的信息。它通常比 State 稀疏，允许：

- 语义检索、关键词检索或图关系检索；
- 摘要、合并、降权、过期和删除；
- user/project/organization scope；
- 不确定性、来源和确认时间。

“用户长期偏好简体中文”可能是 semantic memory；“上周供应商 A 报价 100 美元”更像 episodic memory 或 artifact reference；“调用供应商 API 前先刷新 token”可能是 procedural memory。它们都不能直接当作当前任务 State。

## Event、Snapshot、Checkpoint 和 Artifact

这四个词经常被混为“存档”，但它们承担不同职责。

| 对象 | 记录什么 | 是否可直接作为当前状态 |
|---|---|---|
| **Event** | 某个时间发生了什么，如用户修正、工具返回、状态提交 | 不能；需要按顺序解释或投影 |
| **Snapshot / Current View** | 根据事件物化出的当前字段和值 | 可以，是快速读取的当前视图 |
| **Checkpoint** | 可以从中断处继续所需的最小恢复接口 | 可以作为恢复起点，但仍需重验证外部环境 |
| **Artifact** | 大型原文或可回查产物，如 JSON、日志、报告、diff | 不是状态；通过引用支持状态和证据 |

事件回答“发生过什么”，snapshot 回答“现在是什么”，checkpoint 回答“从哪里继续”，artifact 回答“证据原文在哪里”。

## Thread、Session、Run、Step：时间和范围的四个切片

不同框架命名略有差异，但可以先用下面的通用含义：

- **Thread**：一个连续对话或任务上下文的逻辑容器。
- **Session**：某个框架对 thread 的运行时封装，通常包含消息/事件和临时 state。
- **Run**：一次从输入到输出的执行尝试，可能产生多个 tool call 和事件。
- **Step**：run 内可验证的局部动作，例如 `fetch_vendor_a` 或 `validate_quote`。

一个 thread 可以有多个 run（失败后重试、人工批准后恢复），一个 run 可以有多个 step。跨 thread 的偏好通常才进入长期 memory；当前 run 的 token、重试次数和临时结果不应自动跨任务传播。

## Storage、Index、Cache：放在哪里不等于它是什么

| 组件 | 作用 | 典型内容 | 失败时的含义 |
|---|---|---|---|
| **Storage** | 保存可恢复的原始或结构化数据 | PostgreSQL、对象存储、事件表 | 丢失可能破坏恢复/审计 |
| **Index** | 加速查找候选 | BM25、向量索引、图索引 | 可重建；索引命中不等于事实正确 |
| **Cache** | 短时间减少延迟和成本 | Redis、模型响应 cache | 可失效、不可作为唯一真相 |

例如一条 Memory 的事实和 metadata 可以在 PostgreSQL 保存，embedding 在向量索引保存，最近检索结果在 Redis 缓存。删除 Memory 时三处都要处理；重建向量索引时不能丢失 PostgreSQL 的 source of truth。

## 哪些数据绝不能只放在 prompt 或向量库

以下数据需要受控的权威 owner：

- 付款、余额、权限、审批和生产写入授权；
- 当前任务的完成状态、重试次数和副作用幂等记录；
- 用户删除请求、租户边界和合规保留标记；
- 外部 API 是否真正成功，以及 unknown outcome 的处理结果；
- 版本、时间、来源和撤销关系。

Prompt 可以展示它们的投影；向量库可以帮助找到相关说明；但最终判断要回到数据库、授权服务、工作区或真实外部系统。

## 一个可操作的判断顺序

收到任何候选信息时，依次问：

1. 它描述的是现在、过去，还是未来可能复用的经验？
2. 谁是 source of truth，谁有权修改？
3. 需要精确读取、相似检索，还是只需按 ID 回查？
4. 它只属于哪一个 user/project/tenant/task？
5. 过期、冲突、删除和恢复怎样处理？
6. 如果写入失败或重复写入，系统能否保持不变量？

这组问题比“要不要加一个 memory 字段”更重要。

> [!warning] 常见误区
> **把 Session 叫 Memory**：Session 常常只是当前 thread 的历史容器；它不自动提供跨用户检索、事实冲突解决或长期删除策略。\
> **把 checkpoint 叫长期记忆**：checkpoint 让一次任务恢复，不代表未来任务应该读到其中的全部内容。\
> **把 embedding 当数据库**：embedding 只是一种检索表示，无法单独表达权限、版本、撤销和事务。

## 与已有笔记的接口

[[context-engineering/00-overview|Context Engineering]] 讲“哪些信息进入这次调用”；[[context-engineering/11-memory-engineering|Memory Engineering]] 讲“什么值得跨任务留下”；[[context-engineering/14-planning-context|Planning Context]] 讲“长任务如何继续”。本系列接下来把三者落成可查询、可提交、可恢复的数据结构。

> [!success] 自测
> 进程崩溃前，工具返回 `timeout`，但外部系统可能已经完成写入。这个结果应先记录为 Event/unknown observation，还是直接把 State 标为成功？为什么？如果你选择前者，并能说明需要幂等查询或状态核对，说明边界已经建立。

下一篇从 State 内部展开：[[memory-and-state/02-state-model|State 数据模型：Event Log、Snapshot 与 Checkpoint]]。
