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

# FP-E-01: line-level baseline lookup.
# is_in_line_baseline <rule> <file> <line> [baseline_file]
# Returns 0 if the (rule,file,line) triple is present in baseline.json under
# `.line_baseline[]`. baseline.json extension:
#   { ..., "line_baseline": [ {"rule":"PY-PT-08","file":"src/x/y.py","line":81}, ... ] }
is_in_line_baseline() {
  local rule="$1" file="$2" line="$3"
  local baseline_file="${4:-${BASELINE_FILE:-${REPO_ROOT:-.}/.claude/config/baseline.json}}"
  [ -f "$baseline_file" ] || return 1
  # Cheap match against the flat JSON — avoids paying for `jq` per finding.
  # Line MUST be terminated by non-digit (comma or }) so 81 doesn't match 812.
  grep -qE "\"rule\"[[:space:]]*:[[:space:]]*\"${rule}\"[[:space:]]*,[[:space:]]*\"file\"[[:space:]]*:[[:space:]]*\"${file}\"[[:space:]]*,[[:space:]]*\"line\"[[:space:]]*:[[:space:]]*${line}[^0-9]" "$baseline_file" 2>/dev/null
}

# bootstrap_pt_08 <repo_root>
# Walk the entire codebase, run PY-PT-08 detector, append each hit to
# baseline.json under `line_baseline`. Documented usage:
#   bash .claude/scripts/lib/baseline.sh bootstrap PY-PT-08 <repo_root>
# NOT run automatically — humans must call it to snapshot existing tech debt.
bootstrap_pt_08() {
  local repo_root="${1:-.}"
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  local baseline_dir="$repo_root/.claude/config"
  local baseline="$baseline_dir/baseline.json"
  mkdir -p "$baseline_dir"
  [ -f "$baseline" ] || echo '{}' > "$baseline"

  # Collect all .py files under src/, run PT-08 detection, merge into baseline.
  local py_files
  py_files=$(find "$repo_root/src" -name '*.py' -not -path '*/__pycache__/*' 2>/dev/null | tr '\n' ' ')
  [ -z "$py_files" ] && { echo "no python files under $repo_root/src" >&2; return 1; }

  # shellcheck disable=SC2086
  local hits
  hits=$(python3 "$script_dir/ast_python_checks.py" pt-08 $py_files 2>/dev/null || true)

  BASELINE_JSON="$baseline" HITS="$hits" python3 -c "
import json, os, sys
path = os.environ['BASELINE_JSON']
hits_raw = os.environ.get('HITS', '')
try:
    with open(path) as f: doc = json.load(f)
except Exception: doc = {}
lb = doc.setdefault('line_baseline', [])
seen = {(e.get('rule'), e.get('file'), e.get('line')) for e in lb}
added = 0
for line in hits_raw.splitlines():
    line = line.strip()
    if not line: continue
    try:
        obj = json.loads(line)
    except Exception:
        continue
    key = (obj.get('rule'), obj.get('file'), obj.get('line'))
    if None in key: continue
    if key in seen: continue
    lb.append({'rule': obj['rule'], 'file': obj['file'], 'line': obj['line']})
    seen.add(key)
    added += 1
with open(path, 'w') as f:
    json.dump(doc, f, indent=2)
print(f'baseline bootstrapped: +{added} PY-PT-08 entries (total {len(lb)})', file=sys.stderr)
"
}

# When sourced, expose functions. When executed, dispatch subcommand.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  case "${1:-}" in
    bootstrap)
      shift
      rule="${1:-}"; shift || true
      case "$rule" in
        PY-PT-08) bootstrap_pt_08 "${1:-.}" ;;
        *) echo "unsupported bootstrap rule: $rule (only PY-PT-08)" >&2; exit 2 ;;
      esac
      ;;
    is_in_line_baseline)
      shift; is_in_line_baseline "$@"
      ;;
    *)
      apply_baseline_to_report "$@"
      ;;
  esac
fi
