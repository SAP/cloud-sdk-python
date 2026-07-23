#!/usr/bin/env bats
# test_signals.bats — regression tests for the PR-signal invariants that broke
# during live posting (see conversation 2026-07-09). Each test pins ONE
# reported problem so it can't silently return:
#
#   1. per_check_summary table count MUST reconcile with posted findings
#      (bug-T-01: table showed 6 while only 3 findings posted).
#   2. findings that survive tier-gating carry their originating check name.
#   3. shadow/OFF-tier findings are NOT counted in the table.
#   4. aggregate output is always valid JSON with the required keys.

setup() {
  SCRIPT_DIR="$BATS_TEST_DIRNAME/../.."
  AGG="$SCRIPT_DIR/.claude/scripts/aggregate.sh"
  RULES="$SCRIPT_DIR/.claude/config/rules.yaml"
}

# Build a throwaway TMPDIR_RUN with synthetic report-*.json files.
_mk_reports() {
  local d="$1"
  mkdir -p "$d"
  # hardcode: 2 FLAG findings (HC-04) — should post
  cat > "$d/report-hardcode.json" <<'JSON'
{"check":"hardcode","version":"1.0.0","language":"java","status":"FLAG","started_at":"t","duration_ms":0,"modules_analysed":[],
 "findings":[
   {"rule":"HC-04","severity":"FLAG","file":"a/Foo.java","line":10,"message":"getenv","suggestion":""},
   {"rule":"HC-04","severity":"FLAG","file":"a/Foo.java","line":12,"message":"getenv","suggestion":""}
 ],
 "summary":{"block_count":0,"flag_count":2}}
JSON
  # pr-size: 2 findings but rule is SHADOW tier → must be filtered out of count
  cat > "$d/report-pr-size.json" <<'JSON'
{"check":"pr-size","version":"1.0.0","language":"java","status":"FLAG","started_at":"t","duration_ms":0,"modules_analysed":[],
 "findings":[
   {"rule":"PR-SIZE-01","severity":"FLAG","file":".","line":1,"message":"big","suggestion":""},
   {"rule":"PR-SIZE-02","severity":"FLAG","file":".","line":1,"message":"many files","suggestion":""}
 ],
 "summary":{"block_count":0,"flag_count":2}}
JSON
  # a clean check with zero findings — must still appear as PASS/0
  cat > "$d/report-secrets.json" <<'JSON'
{"check":"secrets","version":"1.0.0","language":"java","status":"PASS","started_at":"t","duration_ms":0,"modules_analysed":[],
 "findings":[],"summary":{"block_count":0,"flag_count":0}}
JSON
}

@test "signals: aggregate output is valid JSON with required keys" {
  [ -f "$AGG" ] || skip "aggregate.sh not in this batch"
  tmpd=$(mktemp -d); _mk_reports "$tmpd"
  out=$(RULES_YAML="$RULES" bash "$AGG" "$tmpd")
  echo "$out" | jq -e '.findings and .per_check_summary and .summary' >/dev/null
  rm -rf "$tmpd"
}

@test "signals: table count reconciles with posted findings (bug-T-01)" {
  [ -f "$AGG" ] || skip "aggregate.sh not in this batch"
  tmpd=$(mktemp -d); _mk_reports "$tmpd"
  out=$(RULES_YAML="$RULES" bash "$AGG" "$tmpd")
  total=$(echo "$out" | jq '.findings | length')
  table_sum=$(echo "$out" | jq '[.per_check_summary[].count] | add')
  # The sum of per-check counts MUST equal the number of posted findings.
  [ "$total" = "$table_sum" ]
  rm -rf "$tmpd"
}

@test "signals: SHADOW-tier findings are excluded from the table count" {
  [ -f "$AGG" ] || skip "aggregate.sh not in this batch"
  [ -f "$RULES" ] || skip "rules.yaml not in this batch"
  # Only assert if PR-SIZE-01 is actually SHADOW in rules.yaml (its configured tier).
  tier=$(grep -oE 'PR-SIZE-01:[[:space:]]*\{[^}]*tier:[[:space:]]*[A-Z_]+' "$RULES" | grep -oE 'tier:[[:space:]]*[A-Z_]+' | grep -oE '[A-Z_]+$' || echo "")
  if [ "$tier" != "SHADOW" ]; then skip "PR-SIZE-01 not SHADOW tier (is '$tier')"; fi
  tmpd=$(mktemp -d); _mk_reports "$tmpd"
  out=$(RULES_YAML="$RULES" bash "$AGG" "$tmpd")
  prsize_count=$(echo "$out" | jq '.per_check_summary["pr-size"].count')
  [ "$prsize_count" = "0" ]
  rm -rf "$tmpd"
}

@test "signals: clean check still appears as PASS with 0 count" {
  [ -f "$AGG" ] || skip "aggregate.sh not in this batch"
  tmpd=$(mktemp -d); _mk_reports "$tmpd"
  out=$(RULES_YAML="$RULES" bash "$AGG" "$tmpd")
  status=$(echo "$out" | jq -r '.per_check_summary["secrets"].status')
  count=$(echo "$out" | jq -r '.per_check_summary["secrets"].count')
  [ "$status" = "PASS" ]
  [ "$count" = "0" ]
  rm -rf "$tmpd"
}

@test "signals: posted findings carry their originating check name" {
  [ -f "$AGG" ] || skip "aggregate.sh not in this batch"
  tmpd=$(mktemp -d); _mk_reports "$tmpd"
  out=$(RULES_YAML="$RULES" bash "$AGG" "$tmpd")
  # Every posted finding must have a non-null .check (needed for the table).
  missing=$(echo "$out" | jq '[.findings[] | select(.check == null)] | length')
  [ "$missing" = "0" ]
  rm -rf "$tmpd"
}
