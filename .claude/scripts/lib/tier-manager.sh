#!/usr/bin/env bash
# lib/tier-manager.sh — apply rule tiers (SHADOW/FLAG/BLOCK/BLOCK_LOCKED) to a report.
# Reads rules.yaml, filters/reclassifies findings based on rule tier.
set -euo pipefail

# get_tier <rule> <rules_yaml_file> → prints tier
get_tier() {
  local rule="$1" cfg="$2"
  # Grep for tier under rule id (simple YAML parsing — no yq dep required)
  # Format expected:
  #   <RULE-ID>:
  #     tier: SHADOW|FLAG|BLOCK|BLOCK_LOCKED
  awk -v rule="$rule" '
    $0 ~ ("^  " rule ":$") { in_rule=1; next }
    in_rule && /^  [A-Z]/ { in_rule=0 }
    in_rule && /tier:/ {
      gsub(/^[[:space:]]*tier:[[:space:]]*/, "")
      print
      exit
    }
  ' "$cfg" 2>/dev/null || echo ""
}

# apply_tiers_to_report <report> <rules_yaml> → prints filtered report
# SHADOW findings are stripped from .findings and moved to .shadow_findings
# BLOCK_LOCKED findings get a locked=true flag
apply_tiers_to_report() {
  local report="$1" cfg="$2"

  local kept=() shadow=()
  local n; n=$(jq '.findings | length' "$report")
  local i=0
  while [ "$i" -lt "$n" ]; do
    local f rule tier severity
    f=$(jq -c ".findings[$i]" "$report")
    rule=$(echo "$f" | jq -r '.rule')
    tier=$(get_tier "$rule" "$cfg")
    [ -z "$tier" ] && tier=$(echo "$f" | jq -r '.severity')  # fall back to severity
    severity=$(echo "$f" | jq -r '.severity')

    case "$tier" in
      SHADOW)
        shadow+=("$(echo "$f" | jq -c '. + {tier: "SHADOW"}')")
        ;;
      FLAG)
        kept+=("$(echo "$f" | jq -c '.severity = "FLAG" | .tier = "FLAG"')")
        ;;
      BLOCK)
        kept+=("$(echo "$f" | jq -c '.severity = "BLOCK" | .tier = "BLOCK"')")
        ;;
      BLOCK_LOCKED)
        kept+=("$(echo "$f" | jq -c '.severity = "BLOCK" | .tier = "BLOCK_LOCKED" | .locked = true')")
        ;;
      *)
        kept+=("$(echo "$f" | jq -c ". + {tier: \"$severity\"}")")
        ;;
    esac
    i=$((i + 1))
  done

  local kept_json shadow_json
  kept_json=$(printf '%s\n' "${kept[@]:-}" | jq -s -c '.')
  shadow_json=$(printf '%s\n' "${shadow[@]:-}" | jq -s -c '.')

  jq --argjson kept "$kept_json" --argjson shadow "$shadow_json" \
    '.findings = $kept | .shadow_findings = $shadow' "$report"
}

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  cmd="${1:-}"; shift || true
  case "$cmd" in
    get_tier)               get_tier "$@" ;;
    apply_tiers_to_report)  apply_tiers_to_report "$@" ;;
    *) echo "Usage: tier-manager.sh {get_tier|apply_tiers_to_report} args" >&2; exit 2 ;;
  esac
fi
