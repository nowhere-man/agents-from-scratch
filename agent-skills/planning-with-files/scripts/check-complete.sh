#!/usr/bin/env bash
# Report whether all phases in the active task_plan.md are complete.
#
# Plan-file resolution:
#   1. $1 (explicit path)
#   2. resolve-plan-dir.sh: $PLAN_ID env -> .planning/.active_plan -> newest mtime

[ "${PLANNING_DISABLED:-}" = "1" ] && exit 0

PLAN_FILE="${1:-}"
if [ -z "$PLAN_FILE" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd 2>/dev/null)" || SCRIPT_DIR="."
    RESOLVER="${SCRIPT_DIR}/resolve-plan-dir.sh"
    RESOLVED_DIR=""
    if [ -f "${RESOLVER}" ]; then
        RESOLVED_DIR="$(sh "${RESOLVER}" 2>/dev/null)"
    fi
    if [ -n "${RESOLVED_DIR}" ] && [ -f "${RESOLVED_DIR}/task_plan.md" ]; then
        PLAN_FILE="${RESOLVED_DIR}/task_plan.md"
    fi
fi

if [ ! -f "$PLAN_FILE" ]; then
    echo "[planning-with-files] No task_plan.md found — no active planning session."
    exit 0
fi

TOTAL=$(grep -cE '^### Phase [0-9]+[：:]' "$PLAN_FILE" || true)
COMPLETE=$(grep -cE '^- \*\*Status:\*\* complete[[:space:]]*$' "$PLAN_FILE" || true)
IN_PROGRESS=$(grep -cE '^- \*\*Status:\*\* in_progress[[:space:]]*$' "$PLAN_FILE" || true)
PENDING=$(grep -cE '^- \*\*Status:\*\* pending[[:space:]]*$' "$PLAN_FILE" || true)

# A file without phase headings is not a phase-structured plan.
if [ "$TOTAL" -eq 0 ]; then
    exit 0
fi

if [ $((COMPLETE + IN_PROGRESS + PENDING)) -ne "$TOTAL" ]; then
    echo "[planning-with-files] Invalid task_plan.md: each phase must have exactly one Status: pending, in_progress, or complete." >&2
    exit 1
fi

if [ "$COMPLETE" -eq "$TOTAL" ]; then
    echo "[planning-with-files] ALL PHASES COMPLETE ($COMPLETE/$TOTAL). If the user has additional work, add new phases to task_plan.md before starting."
else
    echo "[planning-with-files] Task in progress ($COMPLETE/$TOTAL phases complete). Update progress.md before stopping."
    if [ "$IN_PROGRESS" -gt 0 ]; then
        echo "[planning-with-files] $IN_PROGRESS phase(s) still in progress."
    fi
    if [ "$PENDING" -gt 0 ]; then
        echo "[planning-with-files] $PENDING phase(s) pending."
    fi
fi

exit 0
