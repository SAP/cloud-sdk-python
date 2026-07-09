#!/usr/bin/env bash
# check-concurrency.sh — placeholder: stub check emitting empty findings.
# TODO: implement rules from 01-PYTHON.md / 02-JAVA.md §3.concurrency
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

# CC-01: asyncio.Queue with no accompanying Lock/set — flag when queue+append pattern present
# FP-N-01: pre-filter — only lines mentioning asyncio.Queue can match.
echo "$diff_content" | awk '
  BEGIN { file=""; line=0 }
  /^diff --git a\// { file=$4; sub(/^b\//, "", file); line=0; next }
  /^@@/ { if (match($0, /\+[0-9]+/)) line=substr($0, RSTART+1, RLENGTH-1)+0; next }
  /^\+/ && !/^\+\+\+/ {
    c = substr($0, 2)
    if (c ~ /asyncio\.Queue\(/) { print file "\t" line "\t" c }
    line++
    next
  }
  /^ / { line++; next }
' | while IFS=$'\t' read -r file line_num content; do
  [ -z "$file" ] && continue
  if [ "$(is_skill_file "$file")" = "true" ]; then continue; fi
  if echo "$content" | grep -qE 'asyncio\.Queue\('; then
    # Check if same file has a Lock or set() nearby
    if [ -f "$REPO_ROOT/$file" ] && ! grep -qE 'asyncio\.Lock|set\(\)' "$REPO_ROOT/$file" 2>/dev/null; then
      emit_finding_if_touched "CC-01" "FLAG" "$file" "$line_num" \
        "asyncio.Queue without dedup — if items must be unique, add a set() + asyncio.Lock" "" >> "$findings"
    fi
  fi
done

status=$(status_from_findings < "$findings")
emit_report "concurrency" "$LANGUAGE" "$status" "$STARTED" < "$findings"
