from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from reference_loop import (
    FlakyTestModel,
    Harness,
    InMemoryCheckpointStore,
    ResultStatus,
    RunState,
    RunStatus,
    ScriptedTool,
    StopReason,
    ToolResult,
    ToolRuntime,
    VersionConflict,
    default_contract,
    default_tools,
)


def build_harness(
    *,
    contract=None,
    tools=None,
    approved=True,
    store=None,
):
    initial = RunState(run_id="test-run")
    checkpoint_store = store or InMemoryCheckpointStore(initial)
    tool_map = tools or default_tools()
    runtime = ToolRuntime(tool_map)
    harness = Harness(
        contract=contract or default_contract(),
        store=checkpoint_store,
        model=FlakyTestModel(),
        runtime=runtime,
        approved_tools={"apply_patch"} if approved else set(),
    )
    return harness, checkpoint_store, tool_map, runtime


class ConflictOnceStore(InMemoryCheckpointStore):
    def __init__(self, initial_state: RunState) -> None:
        super().__init__(initial_state)
        self.did_conflict = False

    def compare_and_commit(self, expected_version, new_state):
        if not self.did_conflict:
            current = self.load(new_state.run_id)
            current.version += 1
            self._states[new_state.run_id] = copy.deepcopy(current)
            self.history.append(copy.deepcopy(current))
            self.did_conflict = True
            raise VersionConflict("injected concurrent commit")
        return super().compare_and_commit(expected_version, new_state)


class ReferenceLoopTests(unittest.TestCase):
    def test_happy_path_completes_only_after_verified_regression(self):
        harness, _, tools, _ = build_harness()

        final = harness.run("test-run")

        self.assertEqual(final.status, RunStatus.COMPLETED)
        self.assertEqual(
            final.stop_reason, StopReason.COMPLETED_SUCCESS_CRITERIA
        )
        self.assertEqual(final.findings["baseline_failures"], 3)
        self.assertEqual(final.findings["regression_failures"], 0)
        self.assertEqual(final.changed_paths, ["payments/retry.py"])
        self.assertEqual(tools["apply_patch"].execution_count, 1)

    def test_missing_approval_pauses_before_write_tool_executes(self):
        harness, _, tools, _ = build_harness(approved=False)

        final = harness.run("test-run")

        self.assertEqual(final.status, RunStatus.PAUSED)
        self.assertEqual(final.stop_reason, StopReason.PAUSED_FOR_HUMAN)
        self.assertEqual(final.pending_approval, "apply_patch")
        self.assertEqual(tools["apply_patch"].execution_count, 0)

    def test_retryable_failure_retries_then_completes(self):
        flaky_baseline = ScriptedTool(
            "run_baseline",
            ToolResult(
                ResultStatus.SUCCESS,
                {"runs": 20, "failures": 3, "signal": "shared_fake_clock"},
            ),
            scripted_results=[
                ToolResult(ResultStatus.RETRYABLE_ERROR, error="runner busy")
            ],
        )
        tools = default_tools({"run_baseline": flaky_baseline})
        harness, _, _, _ = build_harness(tools=tools)

        final = harness.run("test-run")

        self.assertEqual(final.status, RunStatus.COMPLETED)
        self.assertEqual(flaky_baseline.execution_count, 2)
        statuses = [observation.status for observation in final.observations]
        self.assertIn(ResultStatus.RETRYABLE_ERROR, statuses)

    def test_unknown_side_effect_pauses_for_reconciliation(self):
        unknown_patch = ScriptedTool(
            "apply_patch",
            ToolResult(ResultStatus.UNKNOWN, error="connection lost after write"),
        )
        tools = default_tools({"apply_patch": unknown_patch})
        harness, _, _, _ = build_harness(tools=tools)

        final = harness.run("test-run")

        self.assertEqual(final.status, RunStatus.PAUSED)
        self.assertEqual(
            final.stop_reason, StopReason.PAUSED_UNKNOWN_SIDE_EFFECT
        )
        self.assertEqual(final.current_step, "reconcile_unknown_result")
        self.assertEqual(tools["run_regression"].execution_count, 0)

    def test_budget_exhaustion_is_not_reported_as_success(self):
        harness, _, _, _ = build_harness(
            contract=default_contract(max_steps=2)
        )

        final = harness.run("test-run")

        self.assertEqual(final.status, RunStatus.STOPPED)
        self.assertEqual(
            final.stop_reason, StopReason.STOPPED_BUDGET_EXCEEDED
        )
        self.assertNotIn("patch", final.completed_steps)

    def test_new_harness_continues_from_committed_checkpoint(self):
        harness, store, tools, runtime = build_harness()
        first = harness.step("test-run")
        second = harness.step("test-run")
        self.assertGreater(second.version, first.version)

        restarted = Harness(
            contract=default_contract(),
            store=store,
            model=FlakyTestModel(),
            runtime=runtime,
            approved_tools={"apply_patch"},
        )
        final = restarted.run("test-run")

        self.assertEqual(final.status, RunStatus.COMPLETED)
        self.assertEqual(tools["run_baseline"].execution_count, 1)
        self.assertEqual(tools["inspect_fixture"].execution_count, 1)

    def test_cas_conflict_reuses_idempotent_tool_result(self):
        store = ConflictOnceStore(RunState(run_id="test-run"))
        harness, _, tools, _ = build_harness(store=store)

        final = harness.run("test-run")

        self.assertEqual(final.status, RunStatus.COMPLETED)
        self.assertEqual(tools["run_baseline"].execution_count, 1)
        replayed = [
            event
            for event in harness.trace
            if event.kind == "observation"
            and event.details.get("replayed") is True
        ]
        self.assertTrue(replayed)


if __name__ == "__main__":
    unittest.main()
