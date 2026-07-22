---
title: Memory 与 State 的评测、可观测性和排障
aliases:
  - Agent Memory State Evaluation
  - Agent Observability
tags:
  - agents
  - memory
  - state
  - evaluation
  - observability
status: active
created: 2026-07-23
last_reviewed: 2026-07-23
sources:
  - "[[memory-and-state/99-sources|资料与来源]]"
---

# Memory 与 State 的评测、可观测性和排障

> [!abstract] 本篇学习终点
> 你将能把“Agent 好像更懂用户了”拆成可测量的写入质量、检索收益、状态正确性、恢复成功率、泄漏率、成本和延迟，并设计一条从 trace 到根因的排障路径。

## 只看最终答案会漏掉什么

研究 Agent 最终生成了一份正确报告，但可能是碰巧猜中：

- 关键 Memory 没被召回，只是模型参数里知道类似事实；
- State 已经被错误标为完成，下一次恢复会跳过步骤；
- 向量索引召回了另一租户的数据，但答案没有引用它；
- 工具实际上重复发送了报告，只是用户尚未发现。

因此评测要同时看**结果、轨迹、状态不变量和数据边界**。

## Memory 指标

### 写入质量

- **Write precision**：写入候选中真正值得长期保留的比例；
- **Unsupported memory rate**：没有可靠来源或只是模型猜测的比例；
- **Scope accuracy**：user/project/tenant scope 正确的比例；
- **Duplicate rate**：同一事实被重复保存的比例；
- **Sensitive-write rate**：不应持久化的秘密/PII 被写入的比例。

### 读取质量

- **Retrieval usefulness**：使用 Memory 与 baseline 相比，任务成功率或人工评分提升多少；
- **Stale-use rate**：已过期/被 supersede 的 memory 被用于当前决策的比例；
- **Contradiction rate**：memory 与当前明确输入或 source of truth 冲突的比例；
- **Provenance coverage**：被引用 memory 能否回到 event/artifact；
- **Leakage rate**：跨 tenant/user/project 的内容进入 Context 的比例；
- **Forgetting completeness**：删除后所有派生副本不再召回的比例。

“命中率高”不能替代这些指标。命中大量错误旧 memory，仍然是失败。

## State 指标

- **State invariant violation**：不变量被破坏的次数；
- **Version conflict rate**：CAS 冲突比例，过高可能说明任务粒度或并发设计不合适；
- **Duplicate side-effect rate**：同一幂等意图产生多个外部副作用的比例；
- **Unknown resolution time**：外部结果未知到最终核对的时间；
- **Recovery success**：进程中断后从正确步骤恢复并完成的比例；
- **Recovery skip rate**：恢复时跳过未经验证步骤的比例；
- **Completion claim accuracy**：声明完成时真正满足 success criteria 的比例；
- **Checkpoint staleness**：恢复包与当前 workspace/权限/版本不一致的比例。

## 成本、延迟和质量的三角

每次增加检索、摘要或检查都会付出 token、网络和延迟成本。至少按 run 记录：

```yaml
run_metrics:
  run_id: run-7
  state_reads: 1
  memory_searches: 2
  memory_candidates: 8
  memory_selected: 3
  model_calls: 4
  tool_calls: 5
  input_tokens: 18320
  output_tokens: 2140
  latency_ms: 12600
  retries: 1
  recovery: false
  final_status: completed
```

不要只看平均值；P95/P99（分别表示 95%/99% 请求不超过该值的延迟分位数）、长历史 token、失败重试和人工升级往往决定真实体验和成本。

## Eval Set：把“长期”变成可重复实验

建立一组带标签的多轮任务，每条至少有：

- 初始目标、后续修正和任务边界；
- 应被写入/不应写入的 Memory candidates；
- 必须保留的 State 约束和步骤；
- 过期、冲突、跨租户和删除样例；
- 工具成功、超时、unknown、重复投递和崩溃点；
- 预期 evidence refs、完成标准和允许的工具。

一个最小评测集可以包含：

1. 用户偏好确认后跨新 thread 检索；
2. 当前请求覆盖旧偏好；
3. 旧版本事实不能覆盖新版本；
4. 删除后向量/全文索引不再命中；
5. tool timeout 后恢复不重复副作用；
6. 两个 worker 产生 CAS 冲突；
7. 外部文档尝试污染 Memory；
8. 中断后从 checkpoint 正确继续。

## Trace：让一次错误可以定位

建议每次 turn 记录结构化 trace（原文按敏感级别脱敏）：

```yaml
trace:
  trace_id: tr-88
  task_id: research-43
  state:
    read_version: 12
    committed_version: 13
  context:
    selected_memory_ids: [pref-report-format-v2]
    rejected_memory_ids: [old-currency-v1]
    evidence_ids: [artifact://vendor-a-response-17]
    token_breakdown: {control: 320, state: 480, memory: 210, evidence: 940}
  model:
    provider: example
    model: example-model
    prompt_version: research-v4
  actions:
    - kind: tool_call
      name: vendor_read
      idempotency_key: research-43:vendor-a:v2
      status: unknown
  writes:
    - kind: state_event
      event_id: evt-99
      status: committed
    - kind: memory_candidate
      status: queued
  stop_reason: awaiting_reconciliation
```

Trace 需要同时记录 Selected、Rejected、Uncertain 的对象和原因，否则你只能看到最终 prompt，无法知道为什么某条旧记忆没有被过滤。

## 一条分层排障路径

当答案或行为错误时，按层定位：

```text
1. Source：原始事实是否存在、版本是否正确？
2. Ingestion：事件/Memory 是否写入、去重和 scope 正确？
3. Index：向量/全文/图索引是否新鲜、过滤正确？
4. Selection：为什么选中/拒绝某条候选？
5. Assembly：Context 是否丢了单位、否定、时间或授权？
6. Model：输出是否符合 schema，是否产生越权候选？
7. Execution：工具是否真实成功、是否重复或 unknown？
8. Commit：CAS、事务和不变量是否通过？
9. Recovery：重启/重试是否沿正确 checkpoint 继续？
```

不要一看到答案错就先改 prompt；如果根因是旧索引或错误写回，扩写 prompt 只会掩盖问题。

## LLM-as-Judge（让模型充当评审）的边界

模型评审可以帮助判断摘要是否有用、报告是否符合风格，但不适合独立证明：

- 权限是否正确；
- State 版本是否一致；
- 外部副作用是否只发生一次；
- 删除是否完整；
- evidence 是否真的支持数字。

这些需要数据库断言、来源对照、工具状态查询和人工抽样。对主观质量使用 rubric（评分标准）、pairwise comparison（成对比较）和校准集；报告 judge 模型、版本和提示变化。

## 故障注入与回归门

每次升级模型、框架、prompt、embedding 或 Memory policy，都跑：

- 正常多轮任务；
- 长历史压缩；
- 新 thread 跨任务检索；
- 版本冲突和用户修正；
- timeout/429/unknown；
- 进程 kill、重复消息、CAS 冲突；
- 删除、越权和 prompt injection。

回归门不应只比较最终文本相似度，而要比较：状态不变量、工具序列、evidence 引用、Memory 选择和成本预算。

> [!tip] 先建立 baseline
> 先实现“不使用长期 Memory”的单 Agent baseline（基线），再测加 Memory 后的 personalization lift 和 contradiction/leakage 变化。没有 baseline，就无法知道 Memory 到底带来了收益还是只是增加了 token。

> [!success] 自测
> 如果一次回答错用了旧汇率，你会先查哪三条 trace？理想答案应包括：selected memory 的 valid/supersedes 信息、当前 State/用户输入的优先级、最终 Context packet 和 source-of-truth 查询。

下一篇把这些接口串成可运行的最小示例：[[memory-and-state/10-reference-implementation|最小参考实现]]。
