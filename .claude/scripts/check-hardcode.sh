#!/usr/bin/env bash
# check-hardcode.sh — no hardcoded URLs, credentials, or magic values in impl code.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/json-emit.sh
source "$SCRIPT_DIR/lib/json-emit.sh"
# shellcheck source=lib/skill-self-skip.sh
source "$SCRIPT_DIR/lib/skill-self-skip.sh"

LANGUAGE="${LANGUAGE:-python}"
DIFF_FILE="${DIFF_FILE:-/dev/stdin}"

STARTED=$(now_iso)
findings=$(mktemp)
trap 'rm -f "$findings"' EXIT

diff_content=$(cat "$DIFF_FILE" 2>/dev/null || echo "")

# Determine ignore patterns per language
if [ "$LANGUAGE" = "python" ]; then
  ignore_files='^(tests?/|mocks?/|docs?/|.*/spec/|.*/constants\.py|.*/user-guide\.md|README\.md)'
else
  ignore_files='^(src/test/|mocks?/|docs?/|.*Constants\.java|.*/constants/|.*/user-guide\.md|README\.md)'
fi

echo "$diff_content" | awk '
  BEGIN { file=""; line=0 }
  /^diff --git a\// { file=$4; sub(/^b\//, "", file); line=0; next }
  /^@@/ { if (match($0, /\+[0-9]+/)) line=substr($0, RSTART+1, RLENGTH-1)+0; next }
  /^\+/ && !/^\+\+\+/ { print file "\t" line "\t" substr($0, 2); line++; next }
  /^ / { line++; next }
' | while IFS=$'\t' read -r file line_num content; do
  [ -z "$file" ] && continue
  if [ "$(is_skill_file "$file")" = "true" ]; then continue; fi
  # Filter out test/mock/docs/constants files
  if echo "$file" | grep -qE "$ignore_files"; then continue; fi

  # HC-01: hardcoded URL
  if echo "$content" | grep -qE 'https?://[a-zA-Z0-9]'; then
    # exempt localhost / example.com / example.org (test-safe)
    if ! echo "$content" | grep -qE 'https?://(localhost|127\.0\.0\.1|example\.(com|org|net)|reserved\.)'; then
      emit_finding "HC-01" "BLOCK" "$file" "$line_num" "Hardcoded URL in implementation — externalize to config" "" >> "$findings"
    fi
  fi
  # HC-02: Authorization Bearer
  if echo "$content" | grep -qE 'Authorization[[:space:]]*:[[:space:]]*Bearer[[:space:]]+[A-Za-z0-9]'; then
    emit_finding "HC-02" "BLOCK" "$file" "$line_num" "Hardcoded Authorization header value" "" >> "$findings"
  fi
  # HC-04: direct os.environ / System.getenv
  if [ "$LANGUAGE" = "python" ]; then
    if echo "$content" | grep -qE 'os\.environ\["[A-Z]'; then
      emit_finding "HC-04" "FLAG" "$file" "$line_num" "Direct os.environ access — prefer secret_resolver / config layer" "" >> "$findings"
    fi
  else
    if echo "$content" | grep -qE 'System\.getenv\('; then
      emit_finding "HC-04" "FLAG" "$file" "$line_num" "Direct System.getenv() — prefer SecretResolver" "" >> "$findings"
    fi
  fi
  # HC-06: hardcoded timeout numeric literal
  if echo "$content" | grep -qiE '(timeout|retries|max_retries)[[:space:]]*=[[:space:]]*[0-9]+'; then
    emit_finding "HC-06" "FLAG" "$file" "$line_num" "Hardcoded timeout/retry number — externalize to config" "" >> "$findings"
  fi
done

status=$(status_from_findings < "$findings")
emit_report "hardcode" "$LANGUAGE" "$status" "$STARTED" < "$findings"
