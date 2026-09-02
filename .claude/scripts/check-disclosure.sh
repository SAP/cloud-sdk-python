#!/usr/bin/env bash
# check-disclosure.sh — open-source disclosure hygiene.
# Detects SAP-internal URLs, ORD IDs, internal Jira, unfilled PR body templates.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/json-emit.sh
source "$SCRIPT_DIR/lib/json-emit.sh"
# shellcheck source=lib/hunk-filter.sh
source "$SCRIPT_DIR/lib/hunk-filter.sh"
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

# Scan added lines only.
# FP-N-01: pre-filter in awk. All DIS-* rules key off SAP-internal hostnames
# or --index-url. Only lines containing 'sap' (case-insensitive) or
# 'index-url' can match — everything else is skipped before the shell loop.
echo "$diff_content" | awk '
  BEGIN { file=""; line=0 }
  /^diff --git a\// { file=$4; sub(/^b\//, "", file); line=0; next }
  /^@@/ { if (match($0, /\+[0-9]+/)) line=substr($0, RSTART+1, RLENGTH-1)+0; next }
  /^\+/ && !/^\+\+\+/ {
    c = substr($0, 2)
    if (c ~ /[Ss][Aa][Pp]|index-url/) { print file "\t" line "\t" c }
    line++
    next
  }
  /^ / { line++; next }
' | while IFS=$'\t' read -r file line_num content; do
  [ -z "$file" ] && continue
  # Self-review protection: skip skill files
  if [ "$(is_skill_file "$file")" = "true" ]; then continue; fi

  # DIS-02: Internal Jira URL (checked first — more specific)
  dis02_fired=false
  if echo "$content" | grep -qEi 'jira\.tools\.sap|jira\.wdf\.sap\.corp'; then
    emit_finding_if_touched "DIS-02" "$(sev_public)" "$file" "$line_num" "Internal Jira URL — remove or move to internal-only docs" "" >> "$findings"
    dis02_fired=true
  fi
  # DIS-01: SAP-internal hostnames (skip if DIS-02 already covers the same line)
  if [ "$dis02_fired" = "false" ] && echo "$content" | grep -qEi '(int\.repositories\.cloud\.sap|\.tools\.sap|\.wdf\.sap\.corp|\.mo\.sap\.corp)'; then
    emit_finding_if_touched "DIS-01" "$(sev_public)" "$file" "$line_num" "SAP-internal hostname detected in code" "" >> "$findings"
  fi
  # DIS-06: Internal artifactory index-url
  if echo "$content" | grep -qEi '\-\-index-url[[:space:]]+https?://int\.repositories\.cloud\.sap'; then
    emit_finding_if_touched "DIS-06" "BLOCK" "$file" "$line_num" "Internal artifactory --index-url — must not appear in public/shared configs" "" >> "$findings"
  fi
done

# DIS-07/08: PR body
if [ -n "$PR_BODY_FILE" ] && [ -f "$PR_BODY_FILE" ]; then
  body=$(cat "$PR_BODY_FILE")
  # DIS-07: unfilled Closes #<issue_number> placeholder.
  # Severity: BLOCK for PRs that change source code (they should be tracked by an
  # issue); downgrade to FLAG for docs-only / chore PRs where no issue is required.
  if echo "$body" | grep -qE 'Closes #<issue_number>'; then
    _src_changed=false
    if [ -f "${DIFF_FILE:-/nonexistent}" ] && grep -qE 'diff --git a/src/' "${DIFF_FILE}" 2>/dev/null; then
      _src_changed=true
    elif echo "${diff_content:-}" | grep -qE 'diff --git a/src/'; then
      _src_changed=true
    fi
    _dis07_sev="FLAG"
    [ "$_src_changed" = "true" ] && _dis07_sev="BLOCK"
    emit_finding "DIS-07" "$_dis07_sev" "PR_BODY" 1 "PR body contains unfilled 'Closes #<issue_number>' placeholder" "" >> "$findings"
  fi
  # DIS-08 (SHADOW): internal URLs / Jira in PR body
  if echo "$body" | grep -qEi '\.tools\.sap|\.wdf\.sap\.corp|jira\.tools\.sap'; then
    emit_finding "DIS-08" "FLAG" "PR_BODY" 1 "PR body references SAP-internal URLs/Jira — remove from public-visible artifacts" "" >> "$findings"
  fi
fi

status=$(status_from_findings < "$findings")
emit_report "disclosure" "$LANGUAGE" "$status" "$STARTED" < "$findings"
