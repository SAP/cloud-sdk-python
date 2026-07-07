#!/usr/bin/env bash
# check-binding-shape.sh — placeholder: stub check emitting empty findings.
# TODO: implement rules from 01-PYTHON.md / 02-JAVA.md §3.binding-shape
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/json-emit.sh"
source "$SCRIPT_DIR/lib/skill-self-skip.sh"

LANGUAGE="${LANGUAGE:-python}"
DIFF_FILE="${DIFF_FILE:-/dev/stdin}"
REPO_ROOT="${REPO_ROOT:-.}"

STARTED=$(now_iso)
findings=$(mktemp); trap 'rm -f "$findings"' EXIT
diff_content=$(cat "$DIFF_FILE" 2>/dev/null || echo "")

# BND-02 (LOCKED): token URL via string concat + "/oauth/token"
echo "$diff_content" | awk '
  BEGIN { file=""; line=0 }
  /^diff --git a\// { file=$4; sub(/^b\//, "", file); line=0; next }
  /^@@/ { if (match($0, /\+[0-9]+/)) line=substr($0, RSTART+1, RLENGTH-1)+0; next }
  /^\+/ && !/^\+\+\+/ { print file "\t" line "\t" substr($0, 2); line++; next }
  /^ / { line++; next }
' | while IFS=$'\t' read -r file line_num content; do
  [ -z "$file" ] && continue
  # Self-review protection: skip skill files
  if [ "$(is_skill_file "$file")" = "true" ]; then continue; fi
  if echo "$content" | grep -qE 'rstrip\("/"\)[[:space:]]*\+[[:space:]]*"/oauth/token"|\.replaceAll\("/\+\$", ""\)[[:space:]]*\+[[:space:]]*"/oauth/token"'; then
    emit_finding "BND-02" "BLOCK" "$file" "$line_num" \
      "BTP token URL built via string concat — different services expose different fields" \
      "Use HttpUrl.parse().newBuilder() or honour a 'token_url' field if present" >> "$findings"
  fi
  if echo "$content" | grep -qE '\+[[:space:]]*"/oauth/token"'; then
    emit_finding "BND-02" "BLOCK" "$file" "$line_num" \
      "Hardcoded /oauth/token path — BTP services vary" "" >> "$findings"
  fi
done

status=$(status_from_findings < "$findings")
emit_report "binding-shape" "$LANGUAGE" "$status" "$STARTED" < "$findings"
