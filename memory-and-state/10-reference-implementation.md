---
title: 最小可恢复 Research Agent 参考实现
aliases:
  - Agent Memory State Reference Implementation
  - 最小 Agent 状态实现
tags:
  - agents
  - memory
  - state
  - python
  - engineering
status: active
created: 2026-07-23
last_reviewed: 2026-07-23
sources:
  - "[[memory-and-state/99-sources|资料与来源]]"
---

# 最小可恢复 Research Agent 参考实现

> [!abstract] 本篇学习终点
> 你将看到一个不依赖特定 Agent 框架的最小实现：用结构化 State、append-only Event、Memory candidate、幂等工具和 CAS 提交串起一轮研究任务。代码是教学骨架，不是可直接上线的完整服务；关键是接口和验证顺序。

## 先定义不变量，再写循环

本例只做三件事：抓取供应商、比较价格、生成报告。它保证：

1. 只有成功 observation 才能完成 step；
2. State 版本必须匹配才能提交；
3. 外部抓取使用稳定幂等键；
4. timeout 进入 unknown，不自动判定失败或成功；
5. Memory 只接收带来源的 candidate，不直接写入控制面。

## 数据类型

```python
from dataclasses import dataclass, field
from typing import Any, Literal

Status = Literal["success", "retryable_error", "permanent_error", "unknown"]

@dataclass(frozen=True)
class Event:
    event_id: str
    task_id: str
    event_type: str
    payload: dict[str, Any]
    idempotency_key: str | None = None

@dataclass
class Snapshot:
    task_id: str
    version: int
    current_step: str
    completed: set[str] = field(default_factory=set)
    pending: set[str] = field(default_factory=set)
    unknowns: set[str] = field(default_factory=set)
    evidence_refs: list[str] = field(default_factory=list)
    authorization: dict[str, bool] = field(default_factory=dict)

@dataclass(frozen=True)
class Observation:
    status: Status
    operation_id: str
    artifact_ref: str | None = None
    error_code: str | None = None
```

真实项目中要增加 tenant、schema version、timestamps、actor、source version、sensitivity、trace ID 和序列号；这里先突出状态转换。

## 一个可幂等的工具适配器

```python
class VendorAPI:
    def __init__(self):
        self._results: dict[str, Observation] = {}

    async def fetch(self, vendor: str, *, idempotency_key: str) -> Observation:
        # 生产实现应先向 provider 查询这个 key 是否已有结果。
        if idempotency_key in self._results:
            return self._results[idempotency_key]

        try:
            response = await call_provider(vendor, idempotency_key=idempotency_key)
        except TemporaryTimeout:
            # 不能把 timeout 当成“没有数据”。
            return Observation("unknown", idempotency_key, error_code="UPSTREAM_TIMEOUT")

        artifact_ref = await save_artifact(response, scope={"vendor": vendor})
        result = Observation("success", idempotency_key, artifact_ref=artifact_ref)
        self._results[idempotency_key] = result
        return result
```

这里的内存字典只是演示；进程重启后会丢失，生产应由数据库/供应商幂等接口保存。关键是相同逻辑动作复用同一个 key，且参数变化时拒绝复用。

## 通过 reducer 更新 Snapshot

```python
def reduce_snapshot(old: Snapshot, event: Event) -> Snapshot:
    next_state = Snapshot(
        task_id=old.task_id,
        version=old.version + 1,
        current_step=old.current_step,
        completed=set(old.completed),
        pending=set(old.pending),
        unknowns=set(old.unknowns),
        evidence_refs=list(old.evidence_refs),
        authorization=dict(old.authorization),
    )

    if event.event_type in {"vendor_fetch_succeeded", "answer_succeeded"}:
        step = event.payload["step"]
        next_state.completed.add(step)
        next_state.pending.discard(step)
        next_state.unknowns.discard(step)
        ref = event.payload.get("artifact_ref")
        if ref:
            next_state.evidence_refs.append(ref)
    elif event.event_type in {"vendor_fetch_unknown", "answer_unknown"}:
        next_state.unknowns.add(event.payload["step"])
    else:
        raise ValueError(f"unsupported event: {event.event_type}")

    if next_state.completed & next_state.pending:
        raise AssertionError("a step cannot be completed and pending")
    return next_state
```

Reducer 必须尽量纯函数化：相同的旧状态和事件得到相同的新状态，才能测试、重放和定位错误。当前时间、随机数和外部读取要在 Event 中显式记录，而不是在 reducer 内部偷偷读取。

## State Store 的最小契约

```python
class StateStore:
    async def get(self, task_id: str) -> Snapshot: ...

    async def commit(
        self,
        *,
        expected_version: int,
        event: Event,
        next_snapshot: Snapshot,
    ) -> None:
        """原子写入 Event + Snapshot；版本不匹配则抛出 Conflict。

        重复 idempotency_key 返回 Duplicate，不再次推进 Snapshot。
        """
```

PostgreSQL 适配器应在一个事务中：

下面的提交路径只接收带非空 `idempotency_key` 的状态推进 Event；单纯审计事件应使用独立的 append-only 写入路径。

```sql
BEGIN;
WITH inserted_event AS (
    INSERT INTO agent_event(event_id, task_id, sequence_no, event_type,
                            payload, idempotency_key)
    VALUES (:event_id, :task_id, :next_sequence, :type, :payload, :key)
    ON CONFLICT (task_id, idempotency_key) DO NOTHING
    RETURNING task_id
)
UPDATE agent_task AS task
SET snapshot = :snapshot,
    state_version = task.state_version + 1
FROM inserted_event
WHERE task.task_id = :task_id
  AND task.state_version = :expected_version;
-- inserted_event 为空（重复 key）时 UPDATE 不执行，返回 Duplicate/no-op。
-- 新 Event 但 UPDATE 影响 0 行时 ROLLBACK 并返回 Conflict。
-- 若已有 Event 而 Snapshot 落后，走独立 reconcile/replay，不要重放同一提交。
-- 先校验已存在 Event 的参数 fingerprint（规范化参数摘要）；同 key 不同参数应返回 IdempotencyConflict。
-- 适配器应读取两个 row count：
--   重复 key       → COMMIT（无状态变化）并返回 Duplicate
--   新 Event + 冲突 → ROLLBACK 并返回 Conflict
--   新 Event + 成功 → COMMIT
```

真实实现还要处理“事件已存在但 snapshot 尚未推进”的修复/对账情况，并用唯一约束防止 sequence 或 idempotency key 重复。

## 一轮执行骨架

```python
async def research_turn(task_id: str, user_text: str, actor):
    snapshot = await state_store.get(task_id)
    if snapshot.authorization.get("send_email") is not False:
        raise PermissionError("send_email must be explicitly disabled for this task")

    memories = await memory_store.search(
        query=user_text,
        scope={"tenant": actor.tenant, "user_id": actor.user_id,
               "project": "research-agent"},
        filters={"status": "active", "valid_at": now()},
        limit=5,
    )
    packet = build_packet(snapshot=snapshot, memories=memories,
                          user_text=user_text)

    decision = await model.decide(packet)
    validate_schema(decision)
    validate_tool_authorization(decision, actor, snapshot)

    # decision schema 要求每个动作都有稳定的 step/input_version。
    key = f"{task_id}:{decision.tool}:{decision.step}:{decision.input_version}"
    if decision.tool == "vendor_fetch":
        observation = await vendor_api.fetch(decision.vendor,
                                             idempotency_key=key)
    else:
        observation = Observation("success", f"answer:{task_id}")

    if observation.status == "unknown":
        event = Event(
            event_id=new_id(), task_id=task_id,
            event_type=("vendor_fetch_unknown"
                        if decision.tool == "vendor_fetch"
                        else "answer_unknown"),
            payload={"step": decision.step,
                     "error_code": observation.error_code},
            idempotency_key=key,
        )
    elif observation.status == "success":
        event = Event(
            event_id=new_id(), task_id=task_id,
            event_type=("vendor_fetch_succeeded"
                        if decision.tool == "vendor_fetch"
                        else "answer_succeeded"),
            payload={"step": decision.step,
                     "artifact_ref": observation.artifact_ref},
            idempotency_key=key,
        )
    else:
        raise RetryableStepError(observation.error_code)

    next_snapshot = reduce_snapshot(snapshot, event)
    await state_store.commit(
        expected_version=snapshot.version,
        event=event,
        next_snapshot=next_snapshot,
    )

    # 只排队 candidate；长期记忆 policy worker 再决定是否写入。
    for candidate in extract_candidates(user_text, decision, event):
        await memory_queue.enqueue(candidate, dedupe_key=candidate.key)

    return render_observation(observation, next_snapshot)
```

注意 `memory_queue.enqueue` 不在 State 事务中强行等待。若当前任务必须立即使用一条用户确认偏好，可以把该偏好作为明确的同步 State/Memory 提交，但仍需独立的 policy 和审计。

## 崩溃测试：证明恢复而不是讲故事

```python
async def test_timeout_does_not_mark_step_complete():
    fake_provider.fail_after_receiving = True
    result = await research_turn("research-43", "抓取供应商 A", actor)

    state = await state_store.get("research-43")
    assert "fetch_vendor_a" not in state.completed
    assert "fetch_vendor_a" in state.unknowns

    # 模拟进程重启：从持久 store 重新创建 harness。
    fake_provider.fail_after_receiving = False
    await reconcile_external_state("research-43", "fetch_vendor_a")
    resumed = await research_turn("research-43", "继续", actor)
    assert resumed.status in {"success", "awaiting_review"}
```

测试不应只断言最终文本，而要断言 State 不变量、外部调用次数和事件序列。对真实 provider，使用 sandbox、测试租户或可查询的幂等接口。

## 从这个骨架升级到生产

| 骨架部分 | 生产替换 |
|---|---|
| `StateStore` | PostgreSQL/数据库事务 + schema migration |
| `_results` | provider idempotency API + operation table |
| `memory_queue` | transactional outbox + durable queue |
| `build_packet` | 带 token budget、敏感性和 trace 的 Context Builder |
| `model.decide` | 结构化输出、模型路由、超时和预算 |
| `save_artifact` | 对象存储、checksum、保留和访问审计 |
| 进程内 retry | worker lease、退避、dead-letter 和人工升级 |
| 单机日志 | OpenTelemetry/Langfuse/LangSmith 等 trace + 业务指标 |

不要一开始复制框架内部所有功能；先让这条最小契约在测试中成立，再按吞吐、恢复时长、审计和团队能力选框架。

> [!warning] 代码示例的边界
> 上面的 `call_provider`、`save_artifact`、`model` 和 `memory_store` 都是接口占位。它展示的是所有权、验证和提交顺序，不是可直接用于生产的供应商 SDK 代码。

下一篇把实现放进上线路线：[[memory-and-state/11-production-playbook|生产落地手册]]。
