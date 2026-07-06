#!/usr/bin/env bash
# check-constants.sh — placeholder: stub check emitting empty findings.
# TODO: implement rules from 01-PYTHON.md / 02-JAVA.md §3.constants
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/json-emit.sh"

LANGUAGE="${LANGUAGE:-python}"
DIFF_FILE="${DIFF_FILE:-/dev/stdin}"
REPO_ROOT="${REPO_ROOT:-.}"

STARTED=$(now_iso)
findings=$(mktemp); trap 'rm -f "$findings"' EXIT
diff_content=$(cat "$DIFF_FILE" 2>/dev/null || echo "")

# CON-01 via AST on Python files
if [ "$LANGUAGE" = "python" ]; then
  changed=$(echo "$diff_content" | grep -oE '^\+\+\+ b/src/.*\.py' | sed 's|^+++ b/||' | sort -u)
  if [ -n "$changed" ]; then
    # shellcheck disable=SC2086
    python3 "$SCRIPT_DIR/lib/ast_python_checks.py" con-01 $changed 2>/dev/null >> "$findings" || true
  fi
fi

status=$(status_from_findings < "$findings")
emit_report "constants" "$LANGUAGE" "$status" "$STARTED" < "$findings"
