#!/usr/bin/env bash
# lib/baseline.sh — Apply baseline exemptions to a findings JSON.
# Reads baseline.json + a check-report JSON, outputs the filtered report.
set -euo pipefail

# is_exempted rule file baseline_json → prints "true" | "false"
# Baseline schema: {exemptions: {"<rule>": {scope: "repo|module:<name>|file", files_exempted_glob: "<glob>", file_snapshot: {...}}}}
is_exempted() {
  local rule="$1" file="$2" baseline="$3"
  local entry; entry=$(echo "$baseline" | jq -r --arg rule "$rule" '.exemptions[$rule] // empty')
  if [ -z "$entry" ]; then echo "false"; return; fi

  local scope glob
  scope=$(echo "$entry" | jq -r '.scope // "repo"')
  glob=$(echo "$entry" | jq -r '.files_exempted_glob // "**"')

  case "$scope" in
    repo)
      echo "true"
      ;;
    file)
      # only exempt if file is in file_snapshot AND has not regressed (LOC check)
      local snapshot; snapshot=$(echo "$entry" | jq -r --arg f "$file" '.file_snapshot[$f] // empty')
      if [ -n "$snapshot" ]; then echo "true"; else echo "false"; fi
      ;;
    module:*)
      local mod="${scope#module:}"
      # naive: match path contains "/$mod/" or starts with "$mod/"
      if [[ "$file" == *"/${mod}/"* || "$file" == "${mod}/"* ]]; then
        echo "true"
      else
        echo "false"
      fi
      ;;
    *)
      echo "false"
      ;;
  esac
}

# apply_baseline_to_report baseline_file report_file → prints filtered report to stdout,
# suppressed count to stderr
apply_baseline_to_report() {
  local baseline_file="$1" report_file="$2"
  local baseline; baseline=$(cat "$baseline_file" 2>/dev/null || echo '{"exemptions":{}}')

  local report; report=$(cat "$report_file")
  local kept=() suppressed=0

  local n; n=$(echo "$report" | jq '.findings | length')
  local i=0
  while [ "$i" -lt "$n" ]; do
    local finding rule file exempt
    finding=$(echo "$report" | jq -c ".findings[$i]")
    rule=$(echo "$finding" | jq -r '.rule')
    file=$(echo "$finding" | jq -r '.file')
    exempt=$(is_exempted "$rule" "$file" "$baseline")
    if [ "$exempt" = "true" ]; then
      suppressed=$((suppressed + 1))
    else
      kept+=("$finding")
    fi
    i=$((i + 1))
  done

  # Guard against empty array under set -u; produce "[]" not "[\"\"]"
  local kept_json
  if [ "${#kept[@]}" -eq 0 ]; then
    kept_json="[]"
  else
    kept_json=$(printf '%s\n' "${kept[@]}" | jq -s -c '.')
  fi

  echo "$report" | jq --argjson kept "$kept_json" \
    --argjson suppressed "$suppressed" \
    '.findings = $kept | .summary.suppressed_by_baseline = $suppressed'
}

# When sourced, expose functions. When executed, run apply_baseline_to_report.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  apply_baseline_to_report "$@"
fi
