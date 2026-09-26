#!/usr/bin/env bash
# lib/tier-manager.sh — apply rule tiers (SHADOW/FLAG/BLOCK/BLOCK_LOCKED) to a report.
# Reads rules.yaml, filters/reclassifies findings based on rule tier.
set -euo pipefail

# get_tier <rule> <rules_yaml_file> → prints tier (empty if not configured)
# Supports BOTH:
#   block form:   RULE-ID:
#                    tier: X
#   flow form:    RULE-ID: { tier: X }
#   flow form:    RULE-ID: { tier: X, predicates: {...} }
get_tier() {
  local rule="$1" cfg="$2"
  [ -f "$cfg" ] || { echo ""; return; }

  awk -v rule="$rule" '
    # Escape regex-special chars in rule id for safe matching
    BEGIN {
      # Just anchor at start of key line, requiring `<rule>:` at column 3
      pattern = "^  " rule "[[:space:]]*:"
    }

    # Match rule header
    $0 ~ pattern {
      # Try inline flow form first: RULE: { tier: X, ...  } or { tier: "X" }
      if (match($0, /tier[[:space:]]*:[[:space:]]*[A-Z_]+/)) {
        t = substr($0, RSTART, RLENGTH)
        sub(/^tier[[:space:]]*:[[:space:]]*/, "", t)
        print t
        exit
      }
      # Fall through to block form
      in_rule = 1
      next
    }
    # Block form: look for next rule id or dedent
    in_rule && /^  [A-Z][A-Z0-9_-]*[[:space:]]*:/ { in_rule = 0 }
    in_rule && /^[^ ]/ { in_rule = 0 }
    in_rule && /tier[[:space:]]*:/ {
      match($0, /tier[[:space:]]*:[[:space:]]*[A-Z_]+/)
      if (RSTART > 0) {
        t = substr($0, RSTART, RLENGTH)
        sub(/^tier[[:space:]]*:[[:space:]]*/, "", t)
        print t
        exit
      }
    }
  ' "$cfg"
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
    severity=$(echo "$f" | jq -r '.severity')
    # Fall back to finding's original severity when rule not configured
    [ -z "$tier" ] && tier="$severity"

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
      OFF)
        # explicit off → skip entirely (neither posted nor shadowed)
        ;;
      *)
        kept+=("$(echo "$f" | jq -c ". + {tier: \"$tier\"}")")
        ;;
    esac
    i=$((i + 1))
  done

  # Empty arrays under set -u: guard explicitly to avoid jq input errors
  local kept_json shadow_json
  if [ "${#kept[@]}" -eq 0 ]; then
    kept_json="[]"
  else
    kept_json=$(printf '%s\n' "${kept[@]}" | jq -s -c '.')
  fi
  if [ "${#shadow[@]}" -eq 0 ]; then
    shadow_json="[]"
  else
    shadow_json=$(printf '%s\n' "${shadow[@]}" | jq -s -c '.')
  fi

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
