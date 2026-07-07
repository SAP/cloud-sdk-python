#!/usr/bin/env bash
# check-errors-logging.sh — exception chaining, log level, sensitive-info in messages.
# Uses AST for chaining/swallow checks.
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

if [ "$LANGUAGE" = "python" ]; then
  changed=$(echo "$diff_content" | grep -oE '^\+\+\+ b/src/.*\.py' | sed 's|^+++ b/||' | sort -u)
  if [ -n "$changed" ]; then
    # AST-based chaining / swallow — only reports FLAGs when body ends non-Raise
    # FP-A-01: filter AST hits through hunk attribution
    raw_el=$(mktemp); trap 'rm -f "$raw_el"' EXIT
    # shellcheck disable=SC2086
    python3 "$SCRIPT_DIR/lib/ast_python_checks.py" el-01 $changed 2>/dev/null > "$raw_el" || true
    # shellcheck disable=SC2086
    python3 "$SCRIPT_DIR/lib/ast_python_checks.py" el-02 $changed 2>/dev/null >> "$raw_el" || true
    while IFS= read -r finding; do
      [ -z "$finding" ] && continue
      f=$(echo "$finding" | python3 -c "import json,sys;o=json.loads(sys.stdin.read());print(o.get('file',''))")
      ln=$(echo "$finding" | python3 -c "import json,sys;o=json.loads(sys.stdin.read());print(o.get('line',0))")
      [ -z "$f" ] && continue
      if is_line_touched "$f" "$ln"; then
        echo "$finding" >> "$findings"
      fi
    done < "$raw_el"
    rm -f "$raw_el"
  fi

  # EL-04: secret-like variable name in raise args (grep-based, added lines only)
  echo "$diff_content" | awk '
    BEGIN { file=""; line=0 }
    /^diff --git a\// { file=$4; sub(/^b\//, "", file); line=0; next }
    /^@@/ { if (match($0, /\+[0-9]+/)) line=substr($0, RSTART+1, RLENGTH-1)+0; next }
    /^\+/ && !/^\+\+\+/ { print file "\t" line "\t" substr($0, 2); line++; next }
    /^ / { line++; next }
  ' | while IFS=$'\t' read -r file line_num content; do
    [ -z "$file" ] && continue
  if [ "$(is_skill_file "$file")" = "true" ]; then continue; fi
    # match raise ...({...token|secret|password|api_key|client_secret...})
    if echo "$content" | grep -qE 'raise[[:space:]].*[fF]?"[^"]*\{[^}]*(token|secret|password|api_key|client_secret)[^}]*\}'; then
      emit_finding_if_touched "EL-04" "BLOCK" "$file" "$line_num" \
        "Exception message includes secret-like variable — leaks sensitive data" "" >> "$findings"
    fi
  done
fi

status=$(status_from_findings < "$findings")
emit_report "errors-logging" "$LANGUAGE" "$status" "$STARTED" < "$findings"
