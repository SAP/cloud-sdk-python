#!/usr/bin/env bash
# check-disclosure.sh — open-source disclosure hygiene.
# Detects SAP-internal URLs, ORD IDs, internal Jira, unfilled PR body templates.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/json-emit.sh
source "$SCRIPT_DIR/lib/json-emit.sh"
# shellcheck source=lib/skill-self-skip.sh
source "$SCRIPT_DIR/lib/skill-self-skip.sh"

LANGUAGE="${LANGUAGE:-python}"
PROFILE="${DISCLOSURE_PROFILE:-public}"   # "public" or "internal"
DIFF_FILE="${DIFF_FILE:-/dev/stdin}"
PR_BODY_FILE="${PR_BODY_FILE:-}"

STARTED=$(now_iso)
findings=$(mktemp)
trap 'rm -f "$findings"' EXIT

diff_content=$(cat "$DIFF_FILE" 2>/dev/null || echo "")

# Determine severity based on profile
sev_public() { if [ "$PROFILE" = "public" ]; then echo "BLOCK"; else echo "FLAG"; fi; }
sev_internal_ok() { if [ "$PROFILE" = "public" ]; then echo "BLOCK"; else echo "PASS"; fi; }

# Scan added lines only
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

  # DIS-01: SAP-internal hostnames
  if echo "$content" | grep -qEi '(int\.repositories\.cloud\.sap|\.tools\.sap|\.wdf\.sap\.corp|\.mo\.sap\.corp|jira\.tools\.sap)'; then
    emit_finding "DIS-01" "$(sev_public)" "$file" "$line_num" "SAP-internal hostname detected in code" "" >> "$findings"
  fi
  # DIS-02: Internal Jira URL
  if echo "$content" | grep -qEi 'jira\.tools\.sap|jira\.wdf\.sap\.corp'; then
    emit_finding "DIS-02" "$(sev_public)" "$file" "$line_num" "Internal Jira URL — remove or move to internal-only docs" "" >> "$findings"
  fi
  # DIS-06: Internal artifactory index-url
  if echo "$content" | grep -qEi '\-\-index-url\s+https?://int\.repositories\.cloud\.sap'; then
    emit_finding "DIS-06" "BLOCK" "$file" "$line_num" "Internal artifactory --index-url — must not appear in public/shared configs" "" >> "$findings"
  fi
done

# DIS-07/08: PR body
if [ -n "$PR_BODY_FILE" ] && [ -f "$PR_BODY_FILE" ]; then
  body=$(cat "$PR_BODY_FILE")
  # DIS-07: unfilled Closes #<issue_number> placeholder
  if echo "$body" | grep -qE 'Closes #<issue_number>'; then
    emit_finding "DIS-07" "BLOCK" "PR_BODY" 1 "PR body contains unfilled 'Closes #<issue_number>' placeholder" "" >> "$findings"
  fi
  # DIS-08 (SHADOW): internal URLs / Jira in PR body
  if echo "$body" | grep -qEi '\.tools\.sap|\.wdf\.sap\.corp|jira\.tools\.sap'; then
    emit_finding "DIS-08" "FLAG" "PR_BODY" 1 "PR body references SAP-internal URLs/Jira — remove from public-visible artifacts" "" >> "$findings"
  fi
fi

status=$(status_from_findings < "$findings")
emit_report "disclosure" "$LANGUAGE" "$status" "$STARTED" < "$findings"
