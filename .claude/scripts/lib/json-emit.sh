#!/usr/bin/env bash
# lib/json-emit.sh — Shared JSON output helpers for check scripts.
# Every check-<X>.sh emits a JSON object matching the schema in 00-COMMON.md §3.
set -euo pipefail

# emit_finding writes a single finding object to stdout (one JSON line per call).
# Args: rule severity file line message [suggestion]
emit_finding() {
  local rule="$1" severity="$2" file="$3" line="$4" message="$5" suggestion="${6:-}"
  jq -cn \
    --arg rule "$rule" \
    --arg severity "$severity" \
    --arg file "$file" \
    --argjson line "$line" \
    --arg message "$message" \
    --arg suggestion "$suggestion" \
    '{rule:$rule, severity:$severity, file:$file, line:$line, message:$message, suggestion:$suggestion}'
}

# emit_report assembles the full JSON report from a set of findings (JSONL on stdin).
# Args: check_name language status started_at
emit_report() {
  local check="$1" language="$2" status="$3" started_at="$4"
  local tmp; tmp=$(mktemp)
  cat > "$tmp"
  local block_count flag_count
  block_count=$(jq -s '[.[] | select(.severity=="BLOCK")] | length' < "$tmp")
  flag_count=$(jq -s '[.[] | select(.severity=="FLAG")] | length' < "$tmp")
  # Build findings array from JSONL (jq -s reads each JSON object and produces one array)
  local findings; findings=$(jq -s '.' < "$tmp")

  jq -n \
    --arg check "$check" \
    --arg version "1.0.0" \
    --arg language "$language" \
    --arg status "$status" \
    --arg started_at "$started_at" \
    --argjson block_count "$block_count" \
    --argjson flag_count "$flag_count" \
    --argjson findings "$findings" \
    '{
      check: $check,
      version: $version,
      language: $language,
      status: $status,
      started_at: $started_at,
      duration_ms: 0,
      modules_analysed: [],
      findings: $findings,
      summary: {
        block_count: $block_count,
        flag_count: $flag_count,
        pass_criteria_met: [],
        pass_criteria_failed: []
      }
    }'
  rm -f "$tmp"
}

# status_from_findings derives PASS/FLAG/BLOCK from a JSONL of findings on stdin.
status_from_findings() {
  local input; input=$(cat)
  if [ -z "$input" ]; then echo "PASS"; return; fi
  if echo "$input" | jq -s -e 'any(.severity=="BLOCK")' > /dev/null 2>&1; then
    echo "BLOCK"
  elif echo "$input" | jq -s -e 'any(.severity=="FLAG")' > /dev/null 2>&1; then
    echo "FLAG"
  else
    echo "PASS"
  fi
}

# now_iso returns the current UTC time in ISO-8601 format.
now_iso() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}
