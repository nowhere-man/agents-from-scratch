"""A minimal, provider-free Agent Loop used by the Loop Engineering notes.

The model and tools are deterministic fakes. The point is to make control
ownership visible: the model proposes; the harness validates, executes,
records observations, commits state, and decides when to stop.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict, dataclass, field, replace
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Mapping, Protocol


class ResultStatus(str, Enum):
    SUCCESS = "success"
    RETRYABLE_ERROR = "retryable_error"
    PERMANENT_ERROR = "permanent_error"
    UNKNOWN = "unknown"


class RunStatus(str, Enum):
    RUNNING = "running"
    RETRYING = "retrying"
    RECONCILING = "reconciling"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class StopReason(str, Enum):
    COMPLETED_SUCCESS_CRITERIA = "completed_success_criteria"
    PAUSED_FOR_HUMAN = "paused_for_human"
    PAUSED_UNKNOWN_SIDE_EFFECT = "paused_unknown_side_effect"
    STOPPED_BUDGET_EXCEEDED = "stopped_budget_exceeded"
    FAILED_POLICY_REJECTION = "failed_policy_rejection"
    FAILED_PERMANENT_TOOL_ERROR = "failed_permanent_tool_error"
    FAILED_RETRY_EXHAUSTED = "failed_retry_exhausted"
    FAILED_PREMATURE_FINISH = "failed_premature_finish"


class ProposalKind(str, Enum):
    TOOL_CALL = "tool_call"
    FINISH = "finish"


@dataclass(frozen=True)
class RunContract:
    allowed_tools: tuple[str, ...]
    allowed_paths: tuple[str, ...] = ("payments/",)
    approval_required_for: tuple[str, ...] = ("apply_patch",)
    max_steps: int = 24
    max_model_calls: int = 16
    max_tool_calls: int = 40
    max_retries_per_action: int = 2
    required_regression_runs: int = 20


@dataclass(frozen=True)
class ActionProposal:
    kind: ProposalKind
    action_id: str
    state_version: int
    reason: str
    tool: str | None = None
    arguments: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResult:
    status: ResultStatus
    output: Mapping[str, Any] = field(default_factory=dict)
    error: str | None = None
    replayed: bool = False


@dataclass(frozen=True)
class Observation:
    observation_id: str
    action_id: str
    tool: str
    status: ResultStatus
    output: Mapping[str, Any]
    error: str | None
    attempt: int
    idempotency_key: str
    replayed: bool


@dataclass
class RunState:
    run_id: str
    version: int = 0
    status: RunStatus = RunStatus.RUNNING
    current_step: str = "reproduce"
    steps_used: int = 0
    model_calls: int = 0
    tool_calls: int = 0
    completed_steps: list[str] = field(default_factory=list)
    findings: dict[str, Any] = field(default_factory=dict)
    changed_paths: list[str] = field(default_factory=list)
    observations: list[Observation] = field(default_factory=list)
    retry_counts: dict[str, int] = field(default_factory=dict)
    pending_approval: str | None = None
    stop_reason: StopReason | None = None

    @property
    def terminal(self) -> bool:
        return self.status in {
            RunStatus.PAUSED,
            RunStatus.COMPLETED,
            RunStatus.FAILED,
            RunStatus.STOPPED,
        }

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class TraceEvent:
    kind: str
    run_id: str
    state_version: int
    details: Mapping[str, Any]


class ModelAdapter(Protocol):
    def propose(self, state: RunState, contract: RunContract) -> ActionProposal:
        """Return a candidate action. It has no authority to execute it."""


class Tool(Protocol):
    name: str

    def execute(
        self, arguments: Mapping[str, Any], idempotency_key: str
    ) -> ToolResult:
        """Execute one authorized invocation and report its result category."""


class CheckpointStore(Protocol):
    def load(self, run_id: str) -> RunState:
        """Return a detached copy of the latest committed state."""

    def compare_and_commit(
        self, expected_version: int, new_state: RunState
    ) -> RunState:
        """Commit only when the current version still matches."""


class VersionConflict(RuntimeError):
    pass


class PolicyViolation(RuntimeError):
    pass


class ApprovalRequired(RuntimeError):
    def __init__(self, tool: str) -> None:
        super().__init__(f"human approval required for {tool}")
        self.tool = tool


class InMemoryCheckpointStore:
    """Teaching store with compare-and-swap semantics and full history."""

    def __init__(self, initial_state: RunState) -> None:
        self._states = {initial_state.run_id: copy.deepcopy(initial_state)}
        self.history = [copy.deepcopy(initial_state)]

    def load(self, run_id: str) -> RunState:
        return copy.deepcopy(self._states[run_id])

    def compare_and_commit(
        self, expected_version: int, new_state: RunState
    ) -> RunState:
        current = self._states[new_state.run_id]
        if current.version != expected_version:
            raise VersionConflict(
                f"expected version {expected_version}, found {current.version}"
            )
        committed = copy.deepcopy(new_state)
        committed.version = expected_version + 1
        self._states[new_state.run_id] = committed
        self.history.append(copy.deepcopy(committed))
        return copy.deepcopy(committed)


class ScriptedTool:
    """A deterministic fake tool whose responses can include injected faults."""

    def __init__(
        self,
        name: str,
        default_result: ToolResult,
        scripted_results: list[ToolResult] | None = None,
    ) -> None:
        self.name = name
        self.default_result = default_result
        self.scripted_results = list(scripted_results or [])
        self.execution_count = 0

    def execute(
        self, arguments: Mapping[str, Any], idempotency_key: str
    ) -> ToolResult:
        del arguments, idempotency_key
        self.execution_count += 1
        if self.scripted_results:
            return self.scripted_results.pop(0)
        return self.default_result


class ToolRuntime:
    """Executes registered tools and deduplicates committed logical actions."""

    def __init__(self, tools: Mapping[str, Tool]) -> None:
        self.tools = dict(tools)
        self.ledger: dict[str, ToolResult] = {}

    def execute(self, proposal: ActionProposal, idempotency_key: str) -> ToolResult:
        if idempotency_key in self.ledger:
            return replace(self.ledger[idempotency_key], replayed=True)

        if proposal.tool is None or proposal.tool not in self.tools:
            return ToolResult(
                status=ResultStatus.PERMANENT_ERROR,
                error=f"unknown tool: {proposal.tool}",
            )

        result = self.tools[proposal.tool].execute(
            proposal.arguments, idempotency_key
        )
        # A retryable failure is not cached: the tool says no durable action was
        # committed. Success and unknown results are cached so a CAS retry or
        # process restart cannot blindly repeat a logical side effect.
        if result.status in {ResultStatus.SUCCESS, ResultStatus.UNKNOWN}:
            self.ledger[idempotency_key] = result
        return result


class FlakyTestModel:
    """A fake planner/executor that follows a deterministic diagnostic plan."""

    def propose(self, state: RunState, contract: RunContract) -> ActionProposal:
        del contract
        if "reproduce" not in state.completed_steps:
            return ActionProposal(
                kind=ProposalKind.TOOL_CALL,
                action_id="reproduce-baseline",
                state_version=state.version,
                tool="run_baseline",
                arguments={"command_id": "payments_flaky_baseline", "runs": 20},
                reason="Measure the baseline failure distribution before editing.",
            )
        if "inspect" not in state.completed_steps:
            return ActionProposal(
                kind=ProposalKind.TOOL_CALL,
                action_id="inspect-fixture",
                state_version=state.version,
                tool="inspect_fixture",
                arguments={"path": "payments/test_retry.py"},
                reason="Inspect fixture lifetime after the baseline implicates shared state.",
            )
        if "patch" not in state.completed_steps:
            return ActionProposal(
                kind=ProposalKind.TOOL_CALL,
                action_id="apply-minimal-patch",
                state_version=state.version,
                tool="apply_patch",
                arguments={"paths": ["payments/retry.py"]},
                reason="Apply the smallest patch supported by the observations.",
            )
        if "verify" not in state.completed_steps:
            return ActionProposal(
                kind=ProposalKind.TOOL_CALL,
                action_id="verify-regression",
                state_version=state.version,
                tool="run_regression",
                arguments={"command_id": "payments_flaky_regression", "runs": 20},
                reason="Verify the patch repeatedly against the run contract.",
            )
        return ActionProposal(
            kind=ProposalKind.FINISH,
            action_id="finish-run",
            state_version=state.version,
            reason="All planned steps have observations; request completion audit.",
        )


def default_contract(**overrides: Any) -> RunContract:
    values: dict[str, Any] = {
        "allowed_tools": (
            "run_baseline",
            "inspect_fixture",
            "apply_patch",
            "run_regression",
        )
    }
    values.update(overrides)
    return RunContract(**values)


def default_tools(
    overrides: Mapping[str, ScriptedTool] | None = None,
) -> dict[str, ScriptedTool]:
    tools = {
        "run_baseline": ScriptedTool(
            "run_baseline",
            ToolResult(
                ResultStatus.SUCCESS,
                {"runs": 20, "failures": 3, "signal": "shared_fake_clock"},
            ),
        ),
        "inspect_fixture": ScriptedTool(
            "inspect_fixture",
            ToolResult(
                ResultStatus.SUCCESS,
                {"scope": "session", "teardown_resets_clock": False},
            ),
        ),
        "apply_patch": ScriptedTool(
            "apply_patch",
            ToolResult(
                ResultStatus.SUCCESS,
                {
                    "patch_id": "diff-003",
                    "changed_paths": ["payments/retry.py"],
                },
            ),
        ),
        "run_regression": ScriptedTool(
            "run_regression",
            ToolResult(ResultStatus.SUCCESS, {"runs": 20, "failures": 0}),
        ),
    }
    tools.update(overrides or {})
    return tools


class Harness:
    """Owns the loop, policy, tool execution, state commit, and stop decision."""

    def __init__(
        self,
        *,
        contract: RunContract,
        store: CheckpointStore,
        model: ModelAdapter,
        runtime: ToolRuntime,
        approved_tools: set[str] | None = None,
    ) -> None:
        self.contract = contract
        self.store = store
        self.model = model
        self.runtime = runtime
        self.approved_tools = set(approved_tools or set())
        self.trace: list[TraceEvent] = []

    def run(self, run_id: str) -> RunState:
        while True:
            state = self.store.load(run_id)
            if state.terminal:
                return state
            try:
                state = self.step(run_id)
            except VersionConflict as exc:
                self._trace(
                    "version_conflict",
                    state,
                    {"error": str(exc), "action": "reload_and_replan"},
                )
                continue
            if state.terminal:
                return state

    def step(self, run_id: str) -> RunState:
        state = self.store.load(run_id)
        if state.terminal:
            return state

        budget_stop = self._budget_stop(state)
        if budget_stop is not None:
            return self._commit_terminal(
                state, RunStatus.STOPPED, budget_stop, "budget_stop"
            )

        proposal = self.model.propose(copy.deepcopy(state), self.contract)
        next_state = copy.deepcopy(state)
        next_state.steps_used += 1
        next_state.model_calls += 1
        self._trace("proposal", state, _jsonable(asdict(proposal)))

        try:
            self._validate(proposal, state)
        except ApprovalRequired as exc:
            next_state.status = RunStatus.PAUSED
            next_state.pending_approval = exc.tool
            next_state.stop_reason = StopReason.PAUSED_FOR_HUMAN
            self._trace("approval_required", state, {"tool": exc.tool})
            return self.store.compare_and_commit(state.version, next_state)
        except PolicyViolation as exc:
            next_state.status = RunStatus.FAILED
            next_state.stop_reason = StopReason.FAILED_POLICY_REJECTION
            self._trace("policy_rejection", state, {"error": str(exc)})
            return self.store.compare_and_commit(state.version, next_state)

        if proposal.kind is ProposalKind.FINISH:
            if self._success_criteria_met(state):
                next_state.status = RunStatus.COMPLETED
                next_state.stop_reason = StopReason.COMPLETED_SUCCESS_CRITERIA
                self._trace("completion_audit", state, {"passed": True})
            else:
                next_state.status = RunStatus.FAILED
                next_state.stop_reason = StopReason.FAILED_PREMATURE_FINISH
                self._trace("completion_audit", state, {"passed": False})
            return self.store.compare_and_commit(state.version, next_state)

        assert proposal.tool is not None
        action_attempt = next_state.retry_counts.get(proposal.action_id, 0) + 1
        idempotency_key = self._idempotency_key(proposal)
        result = self.runtime.execute(proposal, idempotency_key)
        next_state.tool_calls += 1
        observation = Observation(
            observation_id=f"obs-{next_state.tool_calls:03d}-v{state.version}",
            action_id=proposal.action_id,
            tool=proposal.tool,
            status=result.status,
            output=dict(result.output),
            error=result.error,
            attempt=action_attempt,
            idempotency_key=idempotency_key,
            replayed=result.replayed,
        )
        next_state.observations.append(observation)
        self._trace("observation", state, _jsonable(asdict(observation)))
        self._reduce(next_state, proposal, observation)
        return self.store.compare_and_commit(state.version, next_state)

    def _validate(self, proposal: ActionProposal, state: RunState) -> None:
        if proposal.state_version != state.version:
            raise PolicyViolation(
                f"stale proposal version {proposal.state_version}; current {state.version}"
            )
        if proposal.kind is ProposalKind.FINISH:
            return
        if proposal.tool is None:
            raise PolicyViolation("tool_call proposal is missing a tool")
        if proposal.tool not in self.contract.allowed_tools:
            raise PolicyViolation(f"tool is outside run scope: {proposal.tool}")
        if proposal.tool not in self.runtime.tools:
            raise PolicyViolation(f"tool is not registered: {proposal.tool}")
        if proposal.tool in self.contract.approval_required_for:
            if proposal.tool not in self.approved_tools:
                raise ApprovalRequired(proposal.tool)
        for path in _proposal_paths(proposal):
            if not _path_allowed(path, self.contract.allowed_paths):
                raise PolicyViolation(f"path is outside allowed scope: {path}")

    def _reduce(
        self,
        state: RunState,
        proposal: ActionProposal,
        observation: Observation,
    ) -> None:
        if observation.status is ResultStatus.RETRYABLE_ERROR:
            retries = state.retry_counts.get(proposal.action_id, 0) + 1
            state.retry_counts[proposal.action_id] = retries
            if retries > self.contract.max_retries_per_action:
                state.status = RunStatus.FAILED
                state.stop_reason = StopReason.FAILED_RETRY_EXHAUSTED
            else:
                state.status = RunStatus.RETRYING
            return

        if observation.status is ResultStatus.PERMANENT_ERROR:
            state.status = RunStatus.FAILED
            state.stop_reason = StopReason.FAILED_PERMANENT_TOOL_ERROR
            return

        if observation.status is ResultStatus.UNKNOWN:
            state.status = RunStatus.PAUSED
            state.stop_reason = StopReason.PAUSED_UNKNOWN_SIDE_EFFECT
            state.current_step = "reconcile_unknown_result"
            return

        state.status = RunStatus.RUNNING
        state.retry_counts.pop(proposal.action_id, None)
        output = observation.output
        if proposal.tool == "run_baseline":
            state.findings["baseline_runs"] = output.get("runs")
            state.findings["baseline_failures"] = output.get("failures")
            state.findings["baseline_signal"] = output.get("signal")
            _complete(state, "reproduce", "inspect")
        elif proposal.tool == "inspect_fixture":
            state.findings["fixture_scope"] = output.get("scope")
            state.findings["teardown_resets_clock"] = output.get(
                "teardown_resets_clock"
            )
            _complete(state, "inspect", "patch")
        elif proposal.tool == "apply_patch":
            changed_paths = list(output.get("changed_paths", []))
            if not all(
                _path_allowed(path, self.contract.allowed_paths)
                for path in changed_paths
            ):
                state.status = RunStatus.FAILED
                state.stop_reason = StopReason.FAILED_POLICY_REJECTION
                return
            state.changed_paths = changed_paths
            state.findings["patch_id"] = output.get("patch_id")
            _complete(state, "patch", "verify")
        elif proposal.tool == "run_regression":
            state.findings["regression_runs"] = output.get("runs")
            state.findings["regression_failures"] = output.get("failures")
            _complete(state, "verify", "completion_audit")

    def _success_criteria_met(self, state: RunState) -> bool:
        return all(
            (
                state.findings.get("baseline_failures", 0) > 0,
                state.findings.get("fixture_scope") == "session",
                bool(state.findings.get("patch_id")),
                state.findings.get("regression_runs", 0)
                >= self.contract.required_regression_runs,
                state.findings.get("regression_failures") == 0,
                bool(state.changed_paths),
                all(
                    _path_allowed(path, self.contract.allowed_paths)
                    for path in state.changed_paths
                ),
            )
        )

    def _budget_stop(self, state: RunState) -> StopReason | None:
        if state.steps_used >= self.contract.max_steps:
            return StopReason.STOPPED_BUDGET_EXCEEDED
        if state.model_calls >= self.contract.max_model_calls:
            return StopReason.STOPPED_BUDGET_EXCEEDED
        if state.tool_calls >= self.contract.max_tool_calls:
            return StopReason.STOPPED_BUDGET_EXCEEDED
        return None

    def _commit_terminal(
        self,
        state: RunState,
        status: RunStatus,
        reason: StopReason,
        trace_kind: str,
    ) -> RunState:
        next_state = copy.deepcopy(state)
        next_state.status = status
        next_state.stop_reason = reason
        self._trace(trace_kind, state, {"stop_reason": reason.value})
        return self.store.compare_and_commit(state.version, next_state)

    def _idempotency_key(self, proposal: ActionProposal) -> str:
        normalized = json.dumps(
            proposal.arguments, sort_keys=True, separators=(",", ":")
        )
        raw = f"{proposal.action_id}|{proposal.tool}|{normalized}".encode()
        digest = hashlib.sha256(raw).hexdigest()[:16]
        return f"{proposal.action_id}:{digest}"

    def _trace(
        self, kind: str, state: RunState, details: Mapping[str, Any]
    ) -> None:
        self.trace.append(
            TraceEvent(
                kind=kind,
                run_id=state.run_id,
                state_version=state.version,
                details=dict(details),
            )
        )


def _proposal_paths(proposal: ActionProposal) -> list[str]:
    paths: list[str] = []
    if "path" in proposal.arguments:
        paths.append(str(proposal.arguments["path"]))
    paths.extend(str(path) for path in proposal.arguments.get("paths", []))
    return paths


def _path_allowed(path: str, allowed_prefixes: tuple[str, ...]) -> bool:
    candidate = PurePosixPath(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return False
    normalized = candidate.as_posix()
    return any(
        normalized == prefix.rstrip("/")
        or normalized.startswith(prefix.rstrip("/") + "/")
        for prefix in allowed_prefixes
    )


def _complete(state: RunState, completed: str, next_step: str) -> None:
    if completed not in state.completed_steps:
        state.completed_steps.append(completed)
    state.current_step = next_step


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def demo() -> None:
    initial = RunState(run_id="flaky-payments-42")
    store = InMemoryCheckpointStore(initial)
    tools = default_tools()
    runtime = ToolRuntime(tools)
    harness = Harness(
        contract=default_contract(),
        store=store,
        model=FlakyTestModel(),
        runtime=runtime,
        approved_tools={"apply_patch"},
    )
    final_state = harness.run(initial.run_id)
    print(json.dumps(final_state.to_dict(), ensure_ascii=False, indent=2))
    print("\nTRACE")
    for event in harness.trace:
        print(json.dumps(_jsonable(asdict(event)), ensure_ascii=False))


if __name__ == "__main__":
    demo()
