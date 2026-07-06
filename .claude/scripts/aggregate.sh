#!/usr/bin/env bash
# aggregate.sh — merge N check reports into a single summary, applying rule tiers.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMPDIR_RUN="$1"
RULES_YAML="${RULES_YAML:-$SCRIPT_DIR/../config/rules.yaml}"

# get_tier <rule> — reads rules.yaml, returns tier or empty
get_tier() {
  local rule="$1"
  # rules.yaml format: "  RULE-ID: { tier: X, ... }"
  awk -v rule="$rule" '
    match($0, "^  " rule ":") {
      if (match($0, /tier:[[:space:]]*[A-Z_]+/)) {
        t = substr($0, RSTART, RLENGTH)
        sub(/^tier:[[:space:]]*/, "", t)
        print t
        exit
      }
    }
  ' "$RULES_YAML" 2>/dev/null
}

# Collect all report-*.json files. Skip files that are not valid JSON
# (e.g. a check that timed out or crashed producing partial stdout) so a
# single bad report can't take the whole aggregation down.
raw_reports=$(ls "$TMPDIR_RUN"/report-*.json 2>/dev/null | sort)
reports=""
for r in $raw_reports; do
  if jq -e '.' "$r" >/dev/null 2>&1; then
    reports="$reports $r"
  else
    echo "WARN: skipping invalid JSON report: $r" >&2
  fi
done
if [ -z "$reports" ]; then
  echo '{"findings":[],"shadow_findings":[],"summary":{"block_count":0,"flag_count":0,"shadow_count":0,"locked_count":0},"per_check_summary":{}}'
  exit 0
fi

# Merge raw findings, then re-classify each finding by tier from rules.yaml
merged=$(mktemp)
# shellcheck disable=SC2086
jq -s '.' $reports > "$merged"

# For each finding, look up its rule tier and adjust
retagged_findings="[]"
retagged_shadow="[]"
locked_count=0

n=$(jq '[.[] | .findings // [] | length] | add // 0' "$merged")
if [ "$n" -gt 0 ]; then
  all_findings=$(jq '[.[] | .findings // []] | flatten' "$merged")
  rule_ids=$(echo "$all_findings" | jq -r '.[] | .rule' | sort -u)

  # Build lookup: rule -> tier
  tier_map='{}'
  while IFS= read -r rule; do
    [ -z "$rule" ] && continue
    tier=$(get_tier "$rule")
    [ -z "$tier" ] && tier="FLAG"   # default
    tier_map=$(echo "$tier_map" | jq --arg r "$rule" --arg t "$tier" '. + {($r): $t}')
  done <<< "$rule_ids"

  # Split findings into posted vs shadow based on tier
  retagged_findings=$(echo "$all_findings" | jq --argjson tiers "$tier_map" '
    map(
      . as $f
      | ($tiers[$f.rule] // "FLAG") as $tier
      | if $tier == "SHADOW" then empty
        elif $tier == "BLOCK_LOCKED" then . + {severity: "BLOCK", tier: "BLOCK_LOCKED", locked: true}
        elif $tier == "BLOCK" then . + {severity: "BLOCK", tier: "BLOCK"}
        elif $tier == "FLAG" then . + {severity: "FLAG", tier: "FLAG"}
        else . + {tier: $tier} end
    )
  ')
  retagged_shadow=$(echo "$all_findings" | jq --argjson tiers "$tier_map" '
    map(
      . as $f
      | ($tiers[$f.rule] // "FLAG") as $tier
      | if $tier == "SHADOW" then . + {tier: "SHADOW"} else empty end
    )
  ')
  locked_count=$(echo "$retagged_findings" | jq '[.[] | select(.locked == true)] | length')
fi

block_count=$(echo "$retagged_findings" | jq '[.[] | select(.severity == "BLOCK")] | length')
flag_count=$(echo "$retagged_findings" | jq '[.[] | select(.severity == "FLAG")] | length')
shadow_count=$(echo "$retagged_shadow" | jq 'length')
per_check=$(jq '[.[] | {(.check): {status: .status, count: ((.findings // []) | length)}}] | add' "$merged")

jq -n \
  --argjson findings "$retagged_findings" \
  --argjson shadow "$retagged_shadow" \
  --argjson block "$block_count" \
  --argjson flag "$flag_count" \
  --argjson shadow_c "$shadow_count" \
  --argjson locked "$locked_count" \
  --argjson per_check "$per_check" \
  '{
    version: "1.0.0",
    findings: $findings,
    shadow_findings: $shadow,
    summary: {
      block_count: $block,
      flag_count: $flag,
      shadow_count: $shadow_c,
      locked_count: $locked
    },
    per_check_summary: $per_check
  }'

rm -f "$merged"
