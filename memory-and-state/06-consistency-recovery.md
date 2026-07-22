---
title: 一致性、并发与崩溃恢复
aliases:
  - Agent Reliability and Recovery
  - Durable Agent Execution
tags:
  - agents
  - state
  - reliability
  - concurrency
  - recovery
status: active
created: 2026-07-23
last_reviewed: 2026-07-23
sources:
  - "[[memory-and-state/99-sources|资料与来源]]"
---

# 一致性、并发与崩溃恢复：让“再跑一次”不会闯祸

> [!abstract] 本篇学习终点
> 你将能解释 Agent 系统里的事务、乐观并发、幂等键、outbox、lease、重试、checkpoint、replay 和 durable execution；面对崩溃、超时、重复消息或两个 worker 同时更新时，能选择安全的恢复策略。

## 现实中的失败不是“调用失败”四个字

研究 Agent 发起“创建供应商报告并上传到共享盘”。进程在 HTTP 请求发出后立刻崩溃。重启时系统只知道调用超时，没有响应。

可能发生了三种现实：

1. 请求没到达，重试是安全的；
2. 请求已到达但响应丢失，重试会生成第二份报告；
3. 请求处理了一半，外部系统状态需要补偿或人工检查。

因此可靠性不是让模型“更有信心”，而是让每个边界有可验证的状态、身份和补偿路径。

## Exactly-once 通常是幻觉

网络和进程边界下，很难同时保证“动作只执行一次”和“结果一定被观察到”。工程上更常见的是：

- **at-least-once**：消息或动作可能重复；接收方必须幂等；
- **at-most-once**：可能丢失，但不重复；适合低价值通知；
- **effectively-once**：通过幂等键、唯一约束和状态核对，让业务结果看起来只发生一次。

把“模型只调用一次”当作 exactly-once 没有意义；模型重试、HTTP 重试、队列重投和 worker 恢复都可能重新执行。

## 事务：把逻辑状态变化绑在一起

一次本地 State 提交通常应在同一数据库事务内完成：

```text
BEGIN
  读取并锁定/验证 task version
  插入唯一 event（含 idempotency_key）
  更新 snapshot 和 state_version
  插入 outbox row（通知索引 worker 或下游）
COMMIT
```

如果中途失败，事件、snapshot 和 outbox 一起回滚；如果提交成功，异步 consumer 可以重试 outbox。不要先更新 snapshot、再发消息、最后写事件，否则任何中断都会留下无法解释的半状态。

## 乐观并发：用版本发现冲突

适合大多数 Agent State 的默认方案是 compare-and-set：

```sql
UPDATE agent_task
SET snapshot = :next_snapshot,
    state_version = state_version + 1
WHERE task_id = :task_id
  AND state_version = :expected_version;
```

若影响行数为 0：

1. 重新读取最新 snapshot；
2. 比较冲突字段和 evidence refs；
3. 重新生成 candidate 或按确定性 reducer 合并；
4. 超过预算时暂停并请求人工处理。

不要把 `last-write-wins` 当成通用冲突策略。对用户最新约束和已验证外部事实，简单覆盖可能造成数据丢失或越权。

## 悲观锁、Lease 与分布式协调

当同一 task 的副作用必须串行时，可用数据库行锁或短期 lease：

- 行锁适合一个数据库事务内的短操作；
- lease 适合跨多个网络调用的 worker ownership，但必须有 TTL（Time To Live，有效期）、续租、fencing token（随每次租约单调增加、用来拒绝旧 worker 写入的令牌）和过期后的安全行为；
- Redis lock 如果没有 fencing，旧 worker 可能在网络分区后继续写入。

锁只解决“谁现在可以尝试”，不解决“外部动作是否已经完成”。仍然需要幂等键和最终状态核对。

## 幂等键：把重复动作映射到同一业务意图

幂等键应稳定绑定逻辑动作，而不是绑定每次 HTTP 请求：

```text
<tenant>:<task_id>:<step_id>:<semantic-input-version>
acme:research-43:publish-report:v2
```

工具 adapter 保存：

- key 与请求参数 fingerprint；
- 第一次执行的外部 request ID；
- 已知结果或 unknown；
- 允许重试的条件和过期时间。

如果同一个 key 收到不同参数，应拒绝并报警；否则调用方可能误把两个意图合并。

## Outbox / Inbox：把数据库和消息队列接起来

### Transactional Outbox

State 事务同时写 `outbox` 表；publisher 以至少一次方式投递。consumer 处理后记录 inbox/dedup key：

```sql
CREATE TABLE agent_outbox (
    id              bigserial PRIMARY KEY,
    event_id        text UNIQUE NOT NULL,
    topic           text NOT NULL,
    payload         jsonb NOT NULL,
    published_at    timestamptz
);

CREATE TABLE agent_inbox (
    consumer_name   text NOT NULL,
    event_id        text NOT NULL,
    processed_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (consumer_name, event_id)
);
```

这样索引 worker 即使收到重复事件，也能安全跳过；如果发布成功但 `published_at` 更新失败，重复发布由 consumer 去重。

### 不要把异步完成当同步成功

Outbox row 已提交只证明“通知待发送”，不证明向量已更新、用户已收到消息或外部报告已发布。每一层都要有自己的 observation/status。

## Retry：每次重试都必须改变至少一个边界

重试策略应按错误分类：

| 错误 | 是否可重试 | 必须改变什么 |
|---|---|---|
| 网络暂时不可用 | 通常可 | 退避、次数/时间预算；幂等键不变 |
| 429 限流 | 可 | `Retry-After`、并发度或队列优先级 |
| 参数 schema 错误 | 不重试同一输入 | 修复参数或回到模型校验 |
| 权限拒绝 | 不盲重试 | 请求授权或停止 |
| 外部状态 unknown | 先查询 | 查询状态或进入人工复核 |
| 同一 CAS 冲突 | 可有限重试 | 重新读取并重建 candidate |

重复相同 command 不是 progress。每次失败记录 error code、尝试次数、策略变化和剩余预算。

## Checkpoint 与 Replay

Checkpoint 保存恢复所需的最小 State；Replay 使用 Event Log 或 workflow history 重建当前状态。二者的区别：

- checkpoint 是快速恢复的物化入口；
- replay 是从可验证事件重新计算；
- checkpoint 损坏或版本不兼容时可以从较早 checkpoint/event 重建；
- replay 需要 deterministic reducer，不能依赖当前时间、随机数或不可记录的外部读取。

Temporal 的 durable workflow 把 Command 映射成持久 Event，worker 崩溃后 replay history 恢复 workflow state；这是长任务的成熟实现。LangGraph checkpointer 更偏图状态快照，适合 thread-level continuation。两者可以互补，但不是同一个产品层。

## 外部副作用的两阶段思路

对于发送邮件、付款、发布报告等动作，可把步骤拆成：

1. **Intent**：在 State 中提交“准备执行”的意图和幂等键；
2. **Execute**：带幂等键调用外部服务；
3. **Reconcile**：查询外部状态并记录 `succeeded/failed/unknown`；
4. **Advance**：只有核对后才把 workflow step 标为完成。

不能把模型返回的 tool call 当作 Execute 成功，也不能用“请求已发送”代替外部系统确认。

## 人工暂停与恢复

HITL（Human-in-the-Loop）不是把对话暂停在内存里。暂停时应保存：

- task/run/state version；
- 待批准动作、参数摘要和风险；
- 证据引用和当前授权；
- 恢复 token 或 interruption ID；
- 过期时间和批准者身份。

批准后重新读取最新 State，确认没有 scope/版本冲突，再执行。用户批准旧版本动作时，若资源已变化，应重新请求批准而不是自动沿用。

## 并发 worker 的三种合并方式

### 独立事件 + 父级 reducer

适合并行只读检索。每个 child 只写自己的事件，父级按稳定顺序合并 evidence refs。

### 字段级 CAS

适合不同 worker 修改互不重叠字段。冲突字段重新计算，避免整份 JSON 覆盖。

### 单一 owner 串行化

适合同一账户、库存或发布队列。牺牲吞吐换确定性，通常比复杂的自动合并更安全。

不要根据“多数 worker 说对”决定业务事实；汇总模型可以提出冲突解释，但 source of truth 仍由外部系统或人工确认。

## 故障注入测试

可靠性不能只靠 happy path 测试。至少注入：

- tool 发出后 kill worker；
- event 写成功、snapshot 写失败；
- outbox 重复投递；
- 两个 worker 读取同一版本后同时提交；
- checkpoint 之后用户修改目标；
- Memory index 延迟或返回已删除候选；
- 恢复时权限被撤销。

每个测试都应检查不变量：没有重复副作用、没有越租户读取、State 版本单调、unknown 不被误标成功、恢复后不会跳过未验证步骤。

> [!warning] “重试三次”不是可靠性设计
> 没有幂等键、状态核对和策略变化，三次重试只是把副作用放大三倍。重试预算应与动作风险、成本和恢复接口一起定义。

> [!success] 自测
> 如果一个 LangGraph node 在写外部数据库后进程崩溃，下一次 checkpoint 恢复如何判断是否重写？请同时说出 checkpoint、idempotency key、外部查询和 CAS 的角色。

下一篇把这些原语映射到主流框架和产品：[[memory-and-state/07-framework-map|主流框架与 Memory 产品映射]]。
