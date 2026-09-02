#!/usr/bin/env bash
# check-quality-gate-parity.sh — placeholder: stub check emitting empty findings.
# TODO: implement rules from 01-PYTHON.md / 02-JAVA.md §3.quality-gate-parity
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/json-emit.sh"

LANGUAGE="${LANGUAGE:-python}"
DIFF_FILE="${DIFF_FILE:-/dev/stdin}"
REPO_ROOT="${REPO_ROOT:-.}"

STARTED=$(now_iso)
findings=$(mktemp); trap 'rm -f "$findings"' EXIT
diff_content=$(cat "$DIFF_FILE" 2>/dev/null || echo "")

# QG-01: workflow with `ruff check` but no `ruff format --check` or `ty check`
if echo "$diff_content" | grep -qE '^\+\+\+ b/\.github/workflows/'; then
  wf_content=$(echo "$diff_content" | awk '/^\+\+\+ b\/\.github\/workflows\// { flag=1; next } /^diff --git/ { flag=0 } flag && /^\+/ && !/^\+\+\+/ { print }')
  if echo "$wf_content" | grep -q 'ruff check'; then
    if ! echo "$wf_content" | grep -q 'ruff format'; then
      emit_finding "QG-01" "FLAG" ".github/workflows/" 1 \
        "Workflow runs 'ruff check' but not 'ruff format --check' — mismatch with dev gate" "" >> "$findings"
    fi
    if ! echo "$wf_content" | grep -q 'ty check'; then
      emit_finding "QG-02" "FLAG" ".github/workflows/" 1 \
        "Workflow runs 'ruff check' but not 'ty check' — incomplete type gate" "" >> "$findings"
    fi
  fi
fi

status=$(status_from_findings < "$findings")
emit_report "quality-gate-parity" "$LANGUAGE" "$status" "$STARTED" < "$findings"
