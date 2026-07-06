#!/usr/bin/env bash
# lib/apply-suppression.sh — filter findings against suppression comments in source.
# Called after a check produces its JSON report; reads suppression tuples and drops findings.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# collect_suppressions_for_files <file1> <file2> ...
# Emits "<file>:<line>:<rule>" tuples for all suppression comments found.
collect_suppressions_for_files() {
  for f in "$@"; do
    [ -f "$f" ] || continue
    bash "$SCRIPT_DIR/suppression.sh" parse_line "$f" 2>/dev/null || true
    bash "$SCRIPT_DIR/suppression.sh" parse_file "$f" 2>/dev/null || true
  done
}

# apply_to_report <report_json> <suppressions_file> → prints filtered report
apply_to_report() {
  local report="$1" supp_file="$2"
  local kept_count=0 suppressed_count=0
  local input; input=$(cat "$report")
  local n; n=$(echo "$input" | jq '.findings | length')
  if [ "$n" -eq 0 ]; then
    echo "$input"; return
  fi

  local kept=()
  local i=0
  while [ "$i" -lt "$n" ]; do
    local finding rule file line
    finding=$(echo "$input" | jq -c ".findings[$i]")
    rule=$(echo "$finding" | jq -r '.rule')
    file=$(echo "$finding" | jq -r '.file')
    line=$(echo "$finding" | jq -r '.line')

    local suppressed
    suppressed=$(bash "$SCRIPT_DIR/suppression.sh" is_suppressed "$rule" "$file" "$line" "$supp_file" 2>/dev/null || echo "false")

    if [ "$suppressed" = "true" ]; then
      suppressed_count=$((suppressed_count + 1))
    else
      kept+=("$finding")
      kept_count=$((kept_count + 1))
    fi
    i=$((i + 1))
  done

  local kept_json
  if [ ${#kept[@]} -eq 0 ]; then
    kept_json="[]"
  else
    kept_json=$(printf '%s\n' "${kept[@]}" | jq -s -c '.')
  fi

  echo "$input" | jq \
    --argjson kept "$kept_json" \
    --argjson suppressed "$suppressed_count" \
    '.findings = $kept | .summary.suppressed_count = $suppressed'
}

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  cmd="${1:-}"; shift || true
  case "$cmd" in
    collect)       collect_suppressions_for_files "$@" ;;
    apply)         apply_to_report "$@" ;;
    *) echo "Usage: apply-suppression.sh {collect|apply} args" >&2; exit 2 ;;
  esac
fi
