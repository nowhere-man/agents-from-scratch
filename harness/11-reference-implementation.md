---
title: 最小可恢复 Agent Harness 参考实现
aliases:
  - Agent Harness Reference Implementation
  - Minimal Recoverable Harness
tags:
  - agents
  - harness
  - python
  - recovery
  - engineering
status: active
created: 2026-07-23
last_reviewed: 2026-07-23
sources:
  - "[[harness/99-sources|资料与来源]]"
---

# 最小可恢复 Agent Harness 参考实现

> [!abstract] 本篇学习终点
> 你将用一段无第三方依赖的 Python 代码串起 Run Contract、compare-and-set（CAS）State、bounded loop、tool policy、effect ledger、四态 Observation、crash、reconcile、resume、stop reason 与 trace。代码是可运行的教学骨架，不是完整生产框架。

## 本例要证明的五个不变量

研究 Agent 依次读取 Vendor A/B 的价格，生成报告并保存。保存操作会故意模拟“外部写入成功，但响应丢失并随后进程崩溃”。恢复后系统必须保证：

1. 模型输出只是候选，工具执行前检查 scope 与参数；
2. 每次模型/工具边界计入持久预算；
3. `started` 但无 terminal record 的副作用是 `unknown`；
4. 新 run 先 reconcile，不能盲目重复保存；
5. 只有 success criteria 满足后才写 `stop_reason=completed`。

## 完整代码

```python
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Literal, Optional


Status = Literal["success", "retryable_error", "permanent_error", "unknown"]
CandidateKind = Literal["tool", "final"]


class StateConflict(RuntimeError):
    pass


class SimulatedCrash(RuntimeError):
    pass


@dataclass(frozen=True)
class RunContract:
    task_id: str
    run_id: str
    tenant_id: str
    user_id: str
    scopes: frozenset[str]
    allowed_vendors: frozenset[str]
    max_turns: int = 8
    max_model_requests: int = 8
    max_tool_calls: int = 8


@dataclass
class RunState:
    task_id: str
    version: int = 0
    turns: int = 0
    model_requests: int = 0
    tool_calls: int = 0
    evidence: dict[str, dict[str, Any]] = field(default_factory=dict)
    report_ref: str | None = None
    unknown_operations: set[str] = field(default_factory=set)
    errors: list[str] = field(default_factory=list)
    stop_reason: str | None = None
    final_answer: str | None = None


@dataclass(frozen=True)
class Candidate:
    kind: CandidateKind
    operation_id: str | None = None
    tool_name: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    text: str | None = None


@dataclass(frozen=True)
class Observation:
    status: Status
    operation_id: str
    tool_name: str
    result: dict[str, Any] | None = None
    error_code: str | None = None


@dataclass
class ToolEffect:
    operation_id: str
    tool_name: str
    arguments: dict[str, Any]
    idempotency_key: str
    status: Literal["started", "completed", "failed"] = "started"
    result: dict[str, Any] | None = None
    error_code: str | None = None


class InMemoryStore:
    """用内存模拟原子 State、append-only events 和 effect ledger。"""

    def __init__(self, initial: RunState) -> None:
        self._state = deepcopy(initial)
        self.events: list[dict[str, Any]] = []
        self.effects: dict[str, ToolEffect] = {}

    def load(self) -> RunState:
        return deepcopy(self._state)

    def commit(
        self,
        *,
        expected_version: int,
        next_state: RunState,
        run_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> RunState:
        if self._state.version != expected_version:
            raise StateConflict(
                f"expected version {expected_version}, "
                f"found {self._state.version}"
            )
        committed = deepcopy(next_state)
        committed.version = expected_version + 1
        self._state = committed
        self.events.append(
            {
                "run_id": run_id,
                "event_type": event_type,
                "state_version": committed.version,
                "payload": deepcopy(payload),
            }
        )
        return deepcopy(committed)

    def start_effect(
        self,
        *,
        operation_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        idempotency_key: str,
        run_id: str,
    ) -> ToolEffect:
        effect = ToolEffect(
            operation_id=operation_id,
            tool_name=tool_name,
            arguments=deepcopy(arguments),
            idempotency_key=idempotency_key,
        )
        self.effects[operation_id] = effect
        self.events.append(
            {
                "run_id": run_id,
                "event_type": "tool_effect_started",
                "payload": {
                    "operation_id": operation_id,
                    "tool_name": tool_name,
                },
            }
        )
        return deepcopy(effect)

    def complete_effect(
        self,
        operation_id: str,
        result: dict[str, Any],
        run_id: str,
    ) -> None:
        effect = self.effects[operation_id]
        effect.status = "completed"
        effect.result = deepcopy(result)
        self.events.append(
            {
                "run_id": run_id,
                "event_type": "tool_effect_completed",
                "payload": {"operation_id": operation_id},
            }
        )

    def fail_effect(self, operation_id: str, error_code: str, run_id: str) -> None:
        effect = self.effects[operation_id]
        effect.status = "failed"
        effect.error_code = error_code
        self.events.append(
            {
                "run_id": run_id,
                "event_type": "tool_effect_failed",
                "payload": {
                    "operation_id": operation_id,
                    "error_code": error_code,
                },
            }
        )


ToolHandler = Callable[[dict[str, Any], str], dict[str, Any]]
ToolValidator = Callable[[dict[str, Any], RunContract], None]
ToolReconciler = Callable[[str], Optional[dict[str, Any]]]


@dataclass(frozen=True)
class Tool:
    name: str
    required_scope: str
    validate: ToolValidator
    execute: ToolHandler
    reconcile: ToolReconciler


class ToolRegistry:
    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as error:
            raise ValueError(f"unknown tool: {name}") from error


class FakeVendorService:
    """外部系统 mock：同一 idempotency key 只保存一份报告。"""

    def __init__(self) -> None:
        self.prices = {
            "vendor-a": {"price": 99, "currency": "USD"},
            "vendor-b": {"price": 109, "currency": "USD"},
        }
        self.reports: dict[str, dict[str, Any]] = {}
        self._lost_response_once: set[str] = set()

    def fetch_price(self, args: dict[str, Any], _: str) -> dict[str, Any]:
        vendor = args["vendor"]
        price = self.prices[vendor]
        return {
            "vendor": vendor,
            **price,
            "artifact_ref": f"artifact://prices/{vendor}/2026-07-23",
        }

    def save_report(self, args: dict[str, Any], key: str) -> dict[str, Any]:
        result = self.reports.setdefault(
            key,
            {
                "report_ref": f"artifact://reports/{args['task_id']}.md",
                "content": args["content"],
            },
        )
        if key not in self._lost_response_once:
            self._lost_response_once.add(key)
            raise TimeoutError("response lost after the report was saved")
        return deepcopy(result)

    def reconcile_report(self, key: str) -> dict[str, Any] | None:
        result = self.reports.get(key)
        return deepcopy(result) if result else None


class ScriptedModel:
    """确定性 fake model；真实项目在这里接 ModelAdapter。"""

    def generate(self, contract: RunContract, state: RunState) -> Candidate:
        for vendor in sorted(contract.allowed_vendors):
            if vendor not in state.evidence:
                return Candidate(
                    kind="tool",
                    operation_id=f"{contract.task_id}:fetch:{vendor}:v1",
                    tool_name="fetch_price",
                    arguments={"vendor": vendor},
                )

        if state.report_ref is None:
            rows = [
                f"{vendor}: {item['price']} {item['currency']}"
                for vendor, item in sorted(state.evidence.items())
            ]
            return Candidate(
                kind="tool",
                operation_id=f"{contract.task_id}:save-report:v1",
                tool_name="save_report",
                arguments={
                    "task_id": contract.task_id,
                    "content": "\n".join(rows),
                },
            )

        return Candidate(
            kind="final",
            text=f"报告已保存：{state.report_ref}",
        )


class Harness:
    def __init__(
        self,
        *,
        store: InMemoryStore,
        model: ScriptedModel,
        tools: ToolRegistry,
        cancelled: Callable[[], bool] = lambda: False,
        crash_after_unknown: bool = False,
    ) -> None:
        self.store = store
        self.model = model
        self.tools = tools
        self.cancelled = cancelled
        self.crash_after_unknown = crash_after_unknown

    def run(self, contract: RunContract) -> RunState:
        state = self.store.load()
        if state.task_id != contract.task_id:
            raise ValueError("contract task_id does not match stored state")
        if state.stop_reason == "completed":
            return state

        state = self._reconcile_unknown(contract, state)
        if state.unknown_operations:
            return self._stop(contract, state, "unknown_external_state")

        while state.stop_reason is None:
            if self.cancelled():
                return self._stop(contract, state, "cancelled")
            if state.turns >= contract.max_turns:
                return self._stop(contract, state, "budget_exhausted")
            if state.model_requests >= contract.max_model_requests:
                return self._stop(contract, state, "budget_exhausted")

            state = self._increment(
                contract, state, "model_requests", "model_request_reserved"
            )
            candidate = self.model.generate(contract, state)
            state = self._increment(contract, state, "turns", "candidate_created")

            if candidate.kind == "final":
                if state.report_ref is None:
                    raise ValueError("final answer rejected: report is missing")
                return self._stop(
                    contract,
                    state,
                    "completed",
                    final_answer=candidate.text,
                )

            if state.tool_calls >= contract.max_tool_calls:
                return self._stop(contract, state, "budget_exhausted")
            state = self._increment(
                contract, state, "tool_calls", "tool_call_reserved"
            )
            observation = self._execute_tool(contract, candidate)
            state = self._commit_observation(contract, state, observation)

            if observation.status == "unknown" and self.crash_after_unknown:
                raise SimulatedCrash("crashed after an unknown external effect")

            state = self._reconcile_unknown(contract, state)
            if state.unknown_operations:
                return self._stop(contract, state, "unknown_external_state")

        return state

    def _increment(
        self,
        contract: RunContract,
        state: RunState,
        field_name: str,
        event_type: str,
    ) -> RunState:
        next_state = deepcopy(state)
        setattr(next_state, field_name, getattr(next_state, field_name) + 1)
        return self.store.commit(
            expected_version=state.version,
            next_state=next_state,
            run_id=contract.run_id,
            event_type=event_type,
            payload={field_name: getattr(next_state, field_name)},
        )

    def _execute_tool(
        self, contract: RunContract, candidate: Candidate
    ) -> Observation:
        assert candidate.tool_name and candidate.operation_id
        tool = self.tools.get(candidate.tool_name)
        if tool.required_scope not in contract.scopes:
            return Observation(
                status="permanent_error",
                operation_id=candidate.operation_id,
                tool_name=tool.name,
                error_code="scope_denied",
            )
        try:
            tool.validate(candidate.arguments, contract)
        except ValueError as error:
            return Observation(
                status="permanent_error",
                operation_id=candidate.operation_id,
                tool_name=tool.name,
                error_code=str(error),
            )

        existing = self.store.effects.get(candidate.operation_id)
        if existing and existing.status == "completed":
            return Observation(
                status="success",
                operation_id=existing.operation_id,
                tool_name=existing.tool_name,
                result=deepcopy(existing.result),
            )
        if existing and existing.status == "started":
            return Observation(
                status="unknown",
                operation_id=existing.operation_id,
                tool_name=existing.tool_name,
                error_code="unknown_after_crash",
            )

        self.store.start_effect(
            operation_id=candidate.operation_id,
            tool_name=tool.name,
            arguments=candidate.arguments,
            idempotency_key=candidate.operation_id,
            run_id=contract.run_id,
        )
        try:
            result = tool.execute(candidate.arguments, candidate.operation_id)
        except TimeoutError:
            return Observation(
                status="unknown",
                operation_id=candidate.operation_id,
                tool_name=tool.name,
                error_code="response_lost",
            )
        except Exception as error:
            self.store.fail_effect(
                candidate.operation_id, type(error).__name__, contract.run_id
            )
            return Observation(
                status="permanent_error",
                operation_id=candidate.operation_id,
                tool_name=tool.name,
                error_code=type(error).__name__,
            )

        self.store.complete_effect(candidate.operation_id, result, contract.run_id)
        return Observation(
            status="success",
            operation_id=candidate.operation_id,
            tool_name=tool.name,
            result=result,
        )

    def _reconcile_unknown(
        self, contract: RunContract, state: RunState
    ) -> RunState:
        current = state
        for operation_id in sorted(current.unknown_operations):
            effect = self.store.effects[operation_id]
            tool = self.tools.get(effect.tool_name)
            result = tool.reconcile(effect.idempotency_key)
            if result is None:
                continue
            self.store.complete_effect(operation_id, result, contract.run_id)
            current = self._commit_observation(
                contract,
                current,
                Observation(
                    status="success",
                    operation_id=operation_id,
                    tool_name=effect.tool_name,
                    result=result,
                ),
            )
        return current

    def _commit_observation(
        self,
        contract: RunContract,
        state: RunState,
        observation: Observation,
    ) -> RunState:
        next_state = deepcopy(state)
        if observation.status == "success":
            next_state.unknown_operations.discard(observation.operation_id)
            if observation.tool_name == "fetch_price" and observation.result:
                vendor = observation.result["vendor"]
                next_state.evidence[vendor] = deepcopy(observation.result)
            if observation.tool_name == "save_report" and observation.result:
                next_state.report_ref = observation.result["report_ref"]
        elif observation.status == "unknown":
            next_state.unknown_operations.add(observation.operation_id)
        else:
            next_state.errors.append(
                f"{observation.operation_id}:{observation.error_code}"
            )

        return self.store.commit(
            expected_version=state.version,
            next_state=next_state,
            run_id=contract.run_id,
            event_type="observation_committed",
            payload={
                "operation_id": observation.operation_id,
                "tool_name": observation.tool_name,
                "status": observation.status,
                "error_code": observation.error_code,
            },
        )

    def _stop(
        self,
        contract: RunContract,
        state: RunState,
        reason: str,
        final_answer: str | None = None,
    ) -> RunState:
        next_state = deepcopy(state)
        next_state.stop_reason = reason
        next_state.final_answer = final_answer
        return self.store.commit(
            expected_version=state.version,
            next_state=next_state,
            run_id=contract.run_id,
            event_type="run_stopped",
            payload={"stop_reason": reason},
        )


def validate_fetch(args: dict[str, Any], contract: RunContract) -> None:
    if set(args) != {"vendor"}:
        raise ValueError("invalid_fetch_schema")
    if args["vendor"] not in contract.allowed_vendors:
        raise ValueError("vendor_out_of_scope")


def validate_save(args: dict[str, Any], contract: RunContract) -> None:
    if set(args) != {"task_id", "content"}:
        raise ValueError("invalid_save_schema")
    if args["task_id"] != contract.task_id:
        raise ValueError("task_id_mismatch")
    if not isinstance(args["content"], str) or not args["content"].strip():
        raise ValueError("empty_report")


def main() -> None:
    service = FakeVendorService()
    store = InMemoryStore(RunState(task_id="vendor-report-43"))
    tools = ToolRegistry(
        [
            Tool(
                name="fetch_price",
                required_scope="vendor:read",
                validate=validate_fetch,
                execute=service.fetch_price,
                reconcile=lambda _: None,
            ),
            Tool(
                name="save_report",
                required_scope="artifact:write",
                validate=validate_save,
                execute=service.save_report,
                reconcile=service.reconcile_report,
            ),
        ]
    )
    first_run = RunContract(
        task_id="vendor-report-43",
        run_id="run-001",
        tenant_id="acme",
        user_id="user-123",
        scopes=frozenset({"vendor:read", "artifact:write"}),
        allowed_vendors=frozenset({"vendor-a", "vendor-b"}),
    )

    try:
        Harness(
            store=store,
            model=ScriptedModel(),
            tools=tools,
            crash_after_unknown=True,
        ).run(first_run)
    except SimulatedCrash as error:
        print(error)

    resumed_run = replace(first_run, run_id="run-002")
    final = Harness(
        store=store,
        model=ScriptedModel(),
        tools=tools,
    ).run(resumed_run)

    print(final.final_answer)
    print(f"stop_reason={final.stop_reason}")
    print(f"reports_saved={len(service.reports)}")
    print(f"unknown_operations={sorted(final.unknown_operations)}")

    assert final.stop_reason == "completed"
    assert len(service.reports) == 1
    assert not final.unknown_operations
    assert set(final.evidence) == {"vendor-a", "vendor-b"}


if __name__ == "__main__":
    main()
```

预期输出的关键部分是：

```text
crashed after an unknown external effect
报告已保存：artifact://reports/vendor-report-43.md
stop_reason=completed
reports_saved=1
unknown_operations=[]
```

`reports_saved=1` 证明恢复没有把外部写重复执行。

## 沿一次失败追踪数据流

第一次 `save_report` 的顺序是：

```text
tool_call_reserved 持久化预算
→ tool_effect_started
→ 外部 service 以 operation_id 保存报告
→ response_lost
→ Observation(status=unknown)
→ State.unknown_operations 加入 operation_id
→ 模拟进程崩溃
```

第二个 run 先读取 unknown operation：

```text
effect ledger 找到 started
→ reconcile_report(operation_id)
→ 外部系统返回已保存报告
→ effect 补写 completed
→ success Observation 提交 State
→ 模型只生成最终回答，不再次 save_report
```

## 每个类对应哪条 Harness seam

| 示例类 | 生产替换 |
|---|---|
| `ScriptedModel` | provider-specific `ModelAdapter` |
| `Tool` / `ToolRegistry` | typed tool registry、MCP adapter、policy metadata |
| `InMemoryStore` | 事务数据库、event store、checkpoint backend |
| `FakeVendorService` | HTTP/DB/File adapter + identity + timeout |
| `Harness` | Runner、graph node runtime 或 durable activity |

核心数据类型 `RunContract`、`Candidate`、`Observation` 和 `ToolEffect` 应尽量保持框架无关。

## 这个教学实现刻意省略了什么

- 真正的 JSON Schema/Pydantic validation；
- async model/tool streaming 与 in-flight cancellation；
- 持久数据库事务和跨 worker 锁；
- approval request、deadline、rate limit 和退避；
- Artifact Store、workspace sandbox 与 credential broker；
- 内容脱敏、OpenTelemetry exporter 和 eval runner。

这些应作为独立 adapter 或中间件增加，不要塞进一个巨型 `run()` 函数。

## 建议追加的故障测试

1. 删除 `artifact:write` scope，断言工具没有进入 `started`；
2. 让模型返回越界 vendor，断言 `permanent_error`；
3. 在 State commit 前注入 version 变化，断言 CAS 冲突不会覆盖；
4. 让 reconcile 返回 `None`，断言 stop reason 为 `unknown_external_state`；
5. 把 `cancelled()` 改为在第二轮返回 `True`，断言不创建新工具调用；
6. 将 budget 设为 1，断言 `budget_exhausted` 且已完成 Observation 保留；
7. 模拟并发 siblings，验证一个失败不删除另一个成功结果。

下一篇把这些原语按成熟度排成上线顺序：[[harness/12-production-playbook|Harness 生产落地手册]]。
