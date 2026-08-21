#!/usr/bin/env bash
# lib/apply-suppression.sh — filter findings against suppression comments in source.
# Called after a check produces its JSON report; reads suppression tuples and drops findings.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Source suppression.sh so we don't fork bash+jq per finding.
# shellcheck source=./suppression.sh
source "$SCRIPT_DIR/suppression.sh"

# collect_suppressions_for_files <file1> <file2> ...
# Emits "<file>:<line>:<rule>" tuples for all suppression comments found.
collect_suppressions_for_files() {
  for f in "$@"; do
    [ -f "$f" ] || continue
    parse_line_suppressions "$f" 2>/dev/null || true
    parse_file_suppressions "$f" 2>/dev/null || true
  done
}

# apply_to_report <report_json> <suppressions_file> → prints filtered report
apply_to_report() {
  local report="$1" supp_file="$2"
  local suppressed_count=0
  local input; input=$(cat "$report")
  local n; n=$(echo "$input" | jq '.findings | length')
  if [ "$n" -eq 0 ]; then
    echo "$input"; return
  fi

  # Extract all (rule, file, line) tuples in a single jq call — one fork total
  # instead of one per finding.
  local tuples; tuples=$(echo "$input" | jq -r '.findings[] | "\(.rule)|\(.file)|\(.line)"')

  local keep_flags=()
  local i=0
  while IFS='|' read -r rule file line; do
    if [ "$(is_suppressed "$rule" "$file" "$line" "$supp_file")" = "true" ]; then
      keep_flags+=("0")
      suppressed_count=$((suppressed_count + 1))
    else
      keep_flags+=("1")
    fi
    i=$((i + 1))
  done <<< "$tuples"

  # Build a JSON array of booleans and use jq to filter
  local keep_json
  if [ "${#keep_flags[@]}" -eq 0 ]; then
    keep_json="[]"
  else
    keep_json=$(printf '%s\n' "${keep_flags[@]}" | jq -s 'map(. == "1")')
  fi

  echo "$input" | jq \
    --argjson keep "$keep_json" \
    --argjson suppressed "$suppressed_count" \
    '.findings = [.findings[] as $f | ($f | . as $x | (input_line_number - 1) as $i | select($keep[$i]))] // .findings
     | .findings = [range(.findings | length) as $i | .findings[$i] | select($keep[$i])]
     | .summary.suppressed_count = $suppressed' 2>/dev/null || {
    # Fallback: simple length-preserving filter
    echo "$input" | jq \
      --argjson keep "$keep_json" \
      --argjson suppressed "$suppressed_count" \
      '(.findings | length) as $n
       | .findings = [range($n) | . as $i | (($keep[$i] // true) | if . then $i else null end) | select(. != null)] as $indices
       | .findings = [$indices[] as $i | .findings[$i]]
       | .summary.suppressed_count = $suppressed'
  }
}

# Simpler variant: build kept-list explicitly (safe fallback)
apply_to_report_v2() {
  local report="$1" supp_file="$2"
  local suppressed_count=0
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

    if [ "$(is_suppressed "$rule" "$file" "$line" "$supp_file")" = "true" ]; then
      suppressed_count=$((suppressed_count + 1))
    else
      kept+=("$finding")
    fi
    i=$((i + 1))
  done

  local kept_json
  if [ "${#kept[@]}" -eq 0 ]; then
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
    apply)         apply_to_report_v2 "$@" ;;   # simpler + safer
    *) echo "Usage: apply-suppression.sh {collect|apply} args" >&2; exit 2 ;;
  esac
fi
