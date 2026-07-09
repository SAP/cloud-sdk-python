#!/usr/bin/env bash
# check-http-hygiene.sh — placeholder: stub check emitting empty findings.
# TODO: implement rules from 01-PYTHON.md / 02-JAVA.md §3.http-hygiene
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

# HTTP-PY-01: Session per invocation (only fire on newly added lines)
# FP-N-01: pre-filter — only lines that create a session/client can match,
# and skip test/mock/doc/example/markdown files right in awk.
echo "$diff_content" | awk '
  BEGIN { file=""; line=0; skip=0 }
  /^diff --git a\// {
    file=$4; sub(/^b\//, "", file); line=0
    # File-level skip: tests/mocks/docs/examples (any depth) + md/rst/txt
    skip = (file ~ /(^|\/)(tests?|mocks?|docs?|examples?)\// || file ~ /\.(md|rst|txt)$/) ? 1 : 0
    next
  }
  /^@@/ { if (match($0, /\+[0-9]+/)) line=substr($0, RSTART+1, RLENGTH-1)+0; next }
  /^\+/ && !/^\+\+\+/ {
    c = substr($0, 2)
    if (!skip && c ~ /(requests|httpx)\.(Session|AsyncClient)\(\)/) {
      print file "\t" line "\t" c
    }
    line++
    next
  }
  /^ / { line++; next }
' | while IFS=$'\t' read -r file line_num content; do
  [ -z "$file" ] && continue
  if [ "$(is_skill_file "$file")" = "true" ]; then continue; fi
  if echo "$content" | grep -qE '(requests|httpx)\.(Session|AsyncClient)\(\)'; then
    emit_finding_if_touched "HTTP-01" "FLAG" "$file" "$line_num" \
      "HTTP session created per invocation — prefer single instance in __init__" "" >> "$findings"
  fi
done

status=$(status_from_findings < "$findings")
emit_report "http-hygiene" "$LANGUAGE" "$status" "$STARTED" < "$findings"
