#!/usr/bin/env bats
# Contract test: every rule ID in baseline.json.exemptions must exist in rules.yaml.
# Guards against the drift Bohn caught in code review (PY-LIC-01 vs LIC-01).

setup() {
  REPO_ROOT="$BATS_TEST_DIRNAME/../.."
  BASELINE="$REPO_ROOT/.claude/config/baseline.json"
  RULES="$REPO_ROOT/.claude/config/rules.yaml"
}

@test "baseline.json is valid JSON" {
  [ -f "$BASELINE" ] || skip "baseline.json not in this batch"
  jq empty "$BASELINE"
}

@test "every baseline rule ID appears in rules.yaml" {
  [ -f "$BASELINE" ] || skip "baseline.json not in this batch"
  [ -f "$RULES" ] || skip "rules.yaml not in this batch"

  # Extract rule keys from baseline (excluding _documentation etc.)
  baseline_rules=$(jq -r '.exemptions | keys[]' "$BASELINE")
  # Extract rule keys from rules.yaml (any line matching /^  [A-Z][A-Z0-9_-]*:/)
  rules_yaml_rules=$(grep -oE '^  [A-Z][A-Z0-9_-]*:' "$RULES" | tr -d ' :' | sort -u)

  for br in $baseline_rules; do
    if ! echo "$rules_yaml_rules" | grep -Fxq "$br"; then
      echo "FAIL: baseline rule '$br' not found in rules.yaml" >&2
      return 1
    fi
  done
}

@test "baseline.json has non-placeholder at_commit" {
  [ -f "$BASELINE" ] || skip "baseline.json not in this batch"
  at_commit=$(jq -r '.at_commit' "$BASELINE")
  # Must be a 40-char hex SHA (or "PENDING_ORIGIN_MAIN" temporarily allowed)
  if [[ "$at_commit" == "TBD" ]]; then
    echo "FAIL: at_commit is placeholder 'TBD'" >&2
    return 1
  fi
  # Real SHA is 40 hex chars
  if ! echo "$at_commit" | grep -qE '^[0-9a-f]{40}$'; then
    echo "FAIL: at_commit is not a git SHA: $at_commit" >&2
    return 1
  fi
}
