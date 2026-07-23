#!/usr/bin/env bash
# check-constants.sh — placeholder: stub check emitting empty findings.
# TODO: implement rules from 01-PYTHON.md / 02-JAVA.md §3.constants
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/json-emit.sh"
source "$SCRIPT_DIR/lib/hunk-filter.sh"
source "$SCRIPT_DIR/lib/skill-self-skip.sh"

LANGUAGE="${LANGUAGE:-python}"
DIFF_FILE="${DIFF_FILE:-/dev/stdin}"
REPO_ROOT="${REPO_ROOT:-.}"

STARTED=$(now_iso)
findings=$(mktemp); trap 'rm -f "$findings"' EXIT
diff_content=$(cat "$DIFF_FILE" 2>/dev/null || echo "")

# CON-01 via AST on Python files
if [ "$LANGUAGE" = "python" ]; then
  changed=$(echo "$diff_content" | grep -oE '^\+\+\+ b/src/.*\.py' | sed 's|^+++ b/||' | sort -u)
  # Filter out skill files (self-review protection)
  filtered=""
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    if [ "$(is_skill_file "$f")" = "true" ]; then continue; fi
    filtered="$filtered $f"
  done <<< "$changed"
  if [ -n "$filtered" ]; then
    raw_con=$(mktemp); trap 'rm -f "$raw_con"' EXIT
    # shellcheck disable=SC2086
    python3 "$SCRIPT_DIR/lib/ast_python_checks.py" con-01 $filtered 2>/dev/null > "$raw_con" || true
    # FP-A-01: filter to touched lines only
    while IFS= read -r finding; do
      [ -z "$finding" ] && continue
      f=$(echo "$finding" | python3 -c "import json,sys;o=json.loads(sys.stdin.read());print(o.get('file',''))")
      ln=$(echo "$finding" | python3 -c "import json,sys;o=json.loads(sys.stdin.read());print(o.get('line',0))")
      [ -z "$f" ] && continue
      if is_line_touched "$f" "$ln"; then
        echo "$finding" >> "$findings"
      fi
    done < "$raw_con"
    rm -f "$raw_con"
  fi
fi

status=$(status_from_findings < "$findings")
emit_report "constants" "$LANGUAGE" "$status" "$STARTED" < "$findings"
