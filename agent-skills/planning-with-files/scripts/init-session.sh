#!/usr/bin/env bash
# Initialize planning files for a new session.
#
# Usage:
#   ./init-session.sh "Backend Refactor"           # .planning/<date>-backend-refactor/
#   ./init-session.sh --template analytics "Report"
#
# Every run writes task_plan.md, findings.md, and progress.md under
# .planning/YYYY-MM-DD-<topic>/ and pins .planning/.active_plan.

set -e

TEMPLATE="default"
PROJECT_NAME=""

while [ $# -gt 0 ]; do
    case "$1" in
        --template|-t)
            if [ $# -lt 2 ]; then
                echo "Missing value for $1" >&2
                exit 2
            fi
            TEMPLATE="$2"
            shift 2
            ;;
        --*)
            echo "Unknown option: $1" >&2
            exit 2
            ;;
        *)
            if [ -z "$PROJECT_NAME" ]; then
                PROJECT_NAME="$1"
            else
                PROJECT_NAME="$PROJECT_NAME $1"
            fi
            shift
            ;;
    esac
done

DATE=$(date +%Y-%m-%d)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
TEMPLATE_DIR="$SKILL_ROOT/templates"

if [ "$TEMPLATE" != "default" ] && [ "$TEMPLATE" != "analytics" ]; then
    echo "Unknown template: $TEMPLATE (available: default, analytics). Using default."
    TEMPLATE="default"
fi

slugify() {
    # Lowercase, separators → '-', collapse repeats, trim leading/trailing '-'
    printf '%s' "$1" \
        | tr '[:upper:]' '[:lower:]' \
        | sed -E 's|[[:space:]_/]+|-|g; s/-+/-/g; s/^-//; s/-$//' \
        | cut -c1-40
}

create_files_in() {
    local target_dir="$1"
    local plan_path="$target_dir/task_plan.md"
    local findings_path="$target_dir/findings.md"
    local progress_path="$target_dir/progress.md"

    if [ ! -f "$plan_path" ]; then
        if [ "$TEMPLATE" = "analytics" ] && [ -f "$TEMPLATE_DIR/analytics_task_plan.md" ]; then
            cp "$TEMPLATE_DIR/analytics_task_plan.md" "$plan_path"
        else
            cp "$TEMPLATE_DIR/task_plan.md" "$plan_path"
        fi
        echo "Created $plan_path"
    else
        echo "$plan_path already exists, skipping"
    fi

    if [ ! -f "$findings_path" ]; then
        if [ "$TEMPLATE" = "analytics" ] && [ -f "$TEMPLATE_DIR/analytics_findings.md" ]; then
            cp "$TEMPLATE_DIR/analytics_findings.md" "$findings_path"
        else
            cp "$TEMPLATE_DIR/findings.md" "$findings_path"
        fi
        echo "Created $findings_path"
    else
        echo "$findings_path already exists, skipping"
    fi

    if [ ! -f "$progress_path" ]; then
        sed "s/\[日期\]/$DATE/g" "$TEMPLATE_DIR/progress.md" > "$progress_path"
        echo "Created $progress_path"
    else
        echo "$progress_path already exists, skipping"
    fi
}

SLUG="$(slugify "$PROJECT_NAME")"
if [ -z "$SLUG" ]; then
    if [ -n "$PROJECT_NAME" ]; then
        SLUG="topic-$(printf '%s' "$PROJECT_NAME" | cksum | awk '{print $1}')"
    else
        SLUG="untitled"
    fi
fi
BASE_ID="${DATE}-${SLUG}"
PLAN_ID="$BASE_ID"
PLAN_ROOT="${PWD}/.planning"
PLAN_DIR="${PLAN_ROOT}/${PLAN_ID}"
mkdir -p "$PLAN_DIR"

echo "Initializing planning files for: ${PROJECT_NAME:-untitled} (template: $TEMPLATE)"
echo "PLAN_ID=$PLAN_ID"
create_files_in "$PLAN_DIR"
printf "%s\n" "$PLAN_ID" > "${PLAN_ROOT}/.active_plan"
echo ""
echo "Active plan recorded: ${PLAN_ROOT}/.active_plan"
echo "Pin this terminal to the plan for parallel sessions:"
echo "  export PLAN_ID=$PLAN_ID"
