#!/usr/bin/env bats
# Extended test suite — tier gating, suppression, integration flows, edge cases.

setup() {
  SCRIPT_DIR="$BATS_TEST_DIRNAME/../../.claude/scripts"
  FIXTURES="$BATS_TEST_DIRNAME/fixtures"
  export LANGUAGE=python
  export REPO_ROOT="$BATS_TEST_DIRNAME/../.."
  export CONFIG_DIR="$REPO_ROOT/.claude/config"
}

# ============================================================
# TIER GATING (aggregate.sh applies rules.yaml tiers)
# ============================================================

@test "aggregate: SHADOW rule findings moved to shadow_findings, not posted" {
  tmpd=$(mktemp -d)
  cat > "$tmpd/report-test.json" <<'EOF'
{
  "check": "test",
  "version": "1.0.0",
  "language": "python",
  "status": "FLAG",
  "started_at": "2026-01-01T00:00:00Z",
  "duration_ms": 0,
  "modules_analysed": [],
  "findings": [
    {"rule": "PR-SIZE-01", "severity": "FLAG", "file": ".", "line": 1, "message": "big", "suggestion": ""},
    {"rule": "SEC-01", "severity": "BLOCK", "file": "x", "line": 1, "message": "aws", "suggestion": ""}
  ],
  "summary": {"block_count": 1, "flag_count": 1}
}
EOF
  result=$(RULES_YAML="$CONFIG_DIR/rules.yaml" bash "$SCRIPT_DIR/aggregate.sh" "$tmpd")
  # PR-SIZE-01 is SHADOW → goes to shadow_findings
  echo "$result" | jq -e '.shadow_findings | length == 1'
  echo "$result" | jq -e '.shadow_findings[0].rule == "PR-SIZE-01"'
  # SEC-01 is BLOCK_LOCKED → stays in findings with locked=true
  echo "$result" | jq -e '.findings | length == 1'
  echo "$result" | jq -e '.findings[0].locked == true'
  echo "$result" | jq -e '.summary.block_count == 1'
  echo "$result" | jq -e '.summary.shadow_count == 1'
  echo "$result" | jq -e '.summary.locked_count == 1'
  rm -rf "$tmpd"
}

@test "aggregate: unknown rule defaults to FLAG tier" {
  tmpd=$(mktemp -d)
  cat > "$tmpd/report-test.json" <<'EOF'
{
  "check": "test", "version": "1.0.0", "language": "python", "status": "FLAG",
  "started_at": "2026-01-01T00:00:00Z", "duration_ms": 0, "modules_analysed": [],
  "findings": [
    {"rule": "UNKNOWN-99", "severity": "BLOCK", "file": "x", "line": 1, "message": "m", "suggestion": ""}
  ],
  "summary": {"block_count": 1, "flag_count": 0}
}
EOF
  result=$(RULES_YAML="$CONFIG_DIR/rules.yaml" bash "$SCRIPT_DIR/aggregate.sh" "$tmpd")
  echo "$result" | jq -e '.findings[0].severity == "FLAG"'
  rm -rf "$tmpd"
}

@test "aggregate: BLOCK_LOCKED rules cannot be softened" {
  tmpd=$(mktemp -d)
  cat > "$tmpd/report-test.json" <<'EOF'
{
  "check": "test", "version": "1.0.0", "language": "python", "status": "FLAG",
  "started_at": "2026-01-01T00:00:00Z", "duration_ms": 0, "modules_analysed": [],
  "findings": [
    {"rule": "BND-02", "severity": "FLAG", "file": "x", "line": 1, "message": "token concat", "suggestion": ""}
  ],
  "summary": {"block_count": 0, "flag_count": 1}
}
EOF
  result=$(RULES_YAML="$CONFIG_DIR/rules.yaml" bash "$SCRIPT_DIR/aggregate.sh" "$tmpd")
  echo "$result" | jq -e '.findings[0].severity == "BLOCK"'
  echo "$result" | jq -e '.findings[0].tier == "BLOCK_LOCKED"'
  echo "$result" | jq -e '.findings[0].locked == true'
  rm -rf "$tmpd"
}

# ============================================================
# SUPPRESSION (apply-suppression.sh)
# ============================================================

@test "suppression: parse_line detects multiple checks in ignore[a,b]" {
  tmp=$(mktemp)
  echo 'x = 1  # sdk-review: ignore[hardcode,patterns]' > "$tmp"
  result=$(bash "$SCRIPT_DIR/lib/suppression.sh" parse_line "$tmp")
  echo "$result" | grep -q ":1:hardcode"
  echo "$result" | grep -q ":1:patterns"
  rm -f "$tmp"
}

@test "suppression: parse_line ignore without brackets = wildcard" {
  tmp=$(mktemp)
  echo 'x = 1  # sdk-review: ignore' > "$tmp"
  result=$(bash "$SCRIPT_DIR/lib/suppression.sh" parse_line "$tmp")
  echo "$result" | grep -q ":1:\*"
  rm -f "$tmp"
}

@test "suppression: is_suppressed returns true when rule matches line" {
  supp_file=$(mktemp)
  echo "src/x.py:42:HC-01" > "$supp_file"
  result=$(bash "$SCRIPT_DIR/lib/suppression.sh" is_suppressed "HC-01" "src/x.py" "42" "$supp_file")
  [ "$result" = "true" ]
  rm -f "$supp_file"
}

@test "suppression: is_suppressed returns true when wildcard on line" {
  supp_file=$(mktemp)
  echo "src/x.py:42:*" > "$supp_file"
  result=$(bash "$SCRIPT_DIR/lib/suppression.sh" is_suppressed "ANY-RULE" "src/x.py" "42" "$supp_file")
  [ "$result" = "true" ]
  rm -f "$supp_file"
}

@test "suppression: is_suppressed false on locked rule (SEC-01)" {
  supp_file=$(mktemp)
  echo "src/x.py:42:SEC-01" > "$supp_file"
  result=$(bash "$SCRIPT_DIR/lib/suppression.sh" is_suppressed "SEC-01" "src/x.py" "42" "$supp_file")
  [ "$result" = "false" ]
  rm -f "$supp_file"
}

@test "suppression: is_suppressed false on locked rule (BND-02)" {
  supp_file=$(mktemp)
  echo "src/x.py:42:BND-02" > "$supp_file"
  result=$(bash "$SCRIPT_DIR/lib/suppression.sh" is_suppressed "BND-02" "src/x.py" "42" "$supp_file")
  [ "$result" = "false" ]
  rm -f "$supp_file"
}

@test "suppression: file-level suppression matches any line" {
  supp_file=$(mktemp)
  echo "src/x.py:*:hardcode" > "$supp_file"
  result=$(bash "$SCRIPT_DIR/lib/suppression.sh" is_suppressed "hardcode" "src/x.py" "999" "$supp_file")
  [ "$result" = "true" ]
  rm -f "$supp_file"
}

@test "apply-suppression: filters findings correctly" {
  supp_file=$(mktemp)
  echo "src/x.py:10:HC-01" > "$supp_file"

  report=$(mktemp)
  cat > "$report" <<'EOF'
{
  "check": "hardcode", "version": "1.0.0", "language": "python", "status": "BLOCK",
  "started_at": "2026-01-01T00:00:00Z", "duration_ms": 0, "modules_analysed": [],
  "findings": [
    {"rule": "HC-01", "severity": "BLOCK", "file": "src/x.py", "line": 10, "message": "url", "suggestion": ""},
    {"rule": "HC-01", "severity": "BLOCK", "file": "src/y.py", "line": 5, "message": "url", "suggestion": ""}
  ],
  "summary": {"block_count": 2, "flag_count": 0}
}
EOF
  result=$(bash "$SCRIPT_DIR/lib/apply-suppression.sh" apply "$report" "$supp_file")
  # x.py:10 suppressed, y.py:5 kept
  echo "$result" | jq -e '.findings | length == 1'
  echo "$result" | jq -e '.findings[0].file == "src/y.py"'
  echo "$result" | jq -e '.summary.suppressed_count == 1'
  rm -f "$supp_file" "$report"
}

# ============================================================
# JSON CONTRACT
# ============================================================

@test "json-emit: emit_report handles empty findings" {
  source "$SCRIPT_DIR/lib/json-emit.sh"
  result=$(echo -n "" | emit_report "test" "python" "PASS" "2026-01-01T00:00:00Z")
  echo "$result" | jq -e '.findings | length == 0'
  echo "$result" | jq -e '.summary.block_count == 0'
  echo "$result" | jq -e '.summary.flag_count == 0'
}

@test "json-emit: status_from_findings returns BLOCK when any BLOCK finding" {
  source "$SCRIPT_DIR/lib/json-emit.sh"
  result=$(printf '{"severity":"FLAG"}\n{"severity":"BLOCK"}\n' | status_from_findings)
  [ "$result" = "BLOCK" ]
}

@test "json-emit: status_from_findings returns PASS when empty" {
  source "$SCRIPT_DIR/lib/json-emit.sh"
  result=$(echo -n "" | status_from_findings)
  [ "$result" = "PASS" ]
}

# ============================================================
# DIFF ATTRIBUTION EDGE CASES
# ============================================================

@test "diff-added-lines: handles multiple hunks in one file" {
  cat > /tmp/multi.diff <<'EOF'
diff --git a/src/a.py b/src/a.py
--- a/src/a.py
+++ b/src/a.py
@@ -1,3 +1,4 @@
 line1
+added_first
 line2
@@ -10,3 +11,4 @@
 line10
+added_second
 line11
EOF
  result=$(bash "$SCRIPT_DIR/lib/diff-added-lines.sh" < /tmp/multi.diff)
  echo "$result" | grep -q "src/a.py:2"
  echo "$result" | grep -q "src/a.py:12"
  rm -f /tmp/multi.diff
}

@test "diff-added-lines: multiple files" {
  cat > /tmp/multi-file.diff <<'EOF'
diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,1 +1,2 @@
 x
+new_in_a
diff --git a/b.py b/b.py
--- a/b.py
+++ b/b.py
@@ -1,1 +1,2 @@
 y
+new_in_b
EOF
  result=$(bash "$SCRIPT_DIR/lib/diff-added-lines.sh" < /tmp/multi-file.diff)
  echo "$result" | grep -q "a.py:2"
  echo "$result" | grep -q "b.py:2"
  rm -f /tmp/multi-file.diff
}

# ============================================================
# PREDICATES EDGE CASES
# ============================================================

@test "predicates: module_shape returns 'client' for module with client.py" {
  source "$SCRIPT_DIR/lib/predicates.sh"
  tmpd=$(mktemp -d)
  touch "$tmpd/client.py"
  result=$(module_shape "$tmpd")
  [ "$result" = "client" ]
  rm -rf "$tmpd"
}

@test "predicates: module_shape returns 'patch' for module with _patch.py only" {
  source "$SCRIPT_DIR/lib/predicates.sh"
  tmpd=$(mktemp -d)
  touch "$tmpd/_patch.py"
  result=$(module_shape "$tmpd")
  [ "$result" = "patch" ]
  rm -rf "$tmpd"
}

@test "predicates: module_shape returns 'other' for empty dir" {
  source "$SCRIPT_DIR/lib/predicates.sh"
  tmpd=$(mktemp -d)
  result=$(module_shape "$tmpd")
  [ "$result" = "other" ]
  rm -rf "$tmpd"
}

# ============================================================
# AST EDGE CASES
# ============================================================

@test "ast: EL-02 accepts except: ...; return e" {
  cat > /tmp/ok.py <<'EOF'
def f():
    try:
        pass
    except Exception as e:
        return e
EOF
  result=$(python3 "$SCRIPT_DIR/lib/ast_python_checks.py" el-02 /tmp/ok.py)
  [ -z "$result" ]
  rm -f /tmp/ok.py
}

@test "ast: EL-02 flags except: pass" {
  cat > /tmp/bad.py <<'EOF'
def f():
    try:
        do_work()
    except Exception:
        pass
EOF
  result=$(python3 "$SCRIPT_DIR/lib/ast_python_checks.py" el-02 /tmp/bad.py)
  echo "$result" | jq -e '.rule == "PY-EL-02"'
  rm -f /tmp/bad.py
}

@test "ast: TEL-02 skips private methods" {
  cat > /tmp/client.py <<'EOF'
class MyClient:
    def _internal(self):
        pass
EOF
  result=$(python3 "$SCRIPT_DIR/lib/ast_python_checks.py" tel-02 /tmp/client.py)
  [ -z "$result" ]
  rm -f /tmp/client.py
}

@test "ast: TEL-02 skips non-Client classes" {
  cat > /tmp/model.py <<'EOF'
class DataModel:
    def get_value(self):
        pass
EOF
  result=$(python3 "$SCRIPT_DIR/lib/ast_python_checks.py" tel-02 /tmp/model.py)
  [ -z "$result" ]
  rm -f /tmp/model.py
}

@test "ast: CON-01 does not flag URLs" {
  cat > /tmp/const.py <<'EOF'
a = "https://api.example.com"
b = "https://api.example.com"
c = "https://api.example.com"
EOF
  result=$(python3 "$SCRIPT_DIR/lib/ast_python_checks.py" con-01 /tmp/const.py)
  [ -z "$result" ]
  rm -f /tmp/const.py
}

# ============================================================
# BASELINE
# ============================================================

@test "baseline: repo-scope exempts all files" {
  baseline='{"exemptions":{"PY-LIC-01":{"scope":"repo"}}}'
  source "$SCRIPT_DIR/lib/baseline.sh"
  result=$(is_exempted "PY-LIC-01" "src/anything.py" "$baseline")
  [ "$result" = "true" ]
}

@test "baseline: module scope exempts only matching module" {
  baseline='{"exemptions":{"TEL-06":{"scope":"module:adms"}}}'
  source "$SCRIPT_DIR/lib/baseline.sh"
  in_module=$(is_exempted "TEL-06" "src/sap_cloud_sdk/adms/foo.py" "$baseline")
  [ "$in_module" = "true" ]
  other=$(is_exempted "TEL-06" "src/sap_cloud_sdk/destination/foo.py" "$baseline")
  [ "$other" = "false" ]
}

@test "baseline: unknown rule not exempted" {
  baseline='{"exemptions":{"OTHER":{"scope":"repo"}}}'
  source "$SCRIPT_DIR/lib/baseline.sh"
  result=$(is_exempted "HC-01" "src/x.py" "$baseline")
  [ "$result" = "false" ]
}

# ============================================================
# INTEGRATION FLOWS
# ============================================================

@test "orchestrate: empty diff produces summary with 0 findings" {
  tmpd=$(mktemp -d)
  cp -r "$REPO_ROOT/.claude" "$tmpd/"
  cd "$tmpd"
  echo "[project]" > pyproject.toml
  mkdir -p src/sap_cloud_sdk
  echo "" > /tmp/empty.diff

  set +e
  DRY_RUN=true LOCAL_DIFF=/tmp/empty.diff REPO_ROOT="$tmpd" \
    bash .claude/scripts/orchestrate.sh 999 --dry-run > /tmp/out.txt 2>&1
  status=$?
  set -e
  [ "$status" -eq 0 ]
  grep -q "BLOCK: 0" /tmp/out.txt
  rm -rf "$tmpd" /tmp/empty.diff /tmp/out.txt
}

@test "orchestrate: dry-run generates valid summary.json" {
  tmpd=$(mktemp -d)
  cp -r "$REPO_ROOT/.claude" "$tmpd/"
  cd "$tmpd"
  echo "[project]" > pyproject.toml
  mkdir -p src/sap_cloud_sdk

  KEEP_TMP=1 DRY_RUN=true LOCAL_DIFF="$FIXTURES/clean.diff" REPO_ROOT="$tmpd" TMPDIR_RUN=/tmp/orch-test \
    bash .claude/scripts/orchestrate.sh 999 --dry-run > /dev/null 2>&1 || true
  [ -f /tmp/orch-test/summary.json ]
  jq -e '.summary.block_count != null' /tmp/orch-test/summary.json
  jq -e '.per_check_summary' /tmp/orch-test/summary.json
  rm -rf "$tmpd" /tmp/orch-test
}

# ============================================================
# SPECIFIC CHECK EDGE CASES
# ============================================================

@test "check-secrets: does not fire on placeholder-looking test fixtures" {
  # test data that looks like a key but is a test placeholder
  cat > /tmp/test-fixture.diff <<'EOF'
diff --git a/tests/fixtures/token.txt b/tests/fixtures/token.txt
new file mode 100644
index 0000000..abc
--- /dev/null
+++ b/tests/fixtures/token.txt
@@ -0,0 +1 @@
+test-token-placeholder
EOF
  DIFF_FILE=/tmp/test-fixture.diff bash "$SCRIPT_DIR/check-secrets.sh" < /tmp/test-fixture.diff > /tmp/out.json
  # Should not fire on obvious placeholder
  jq -e '.status == "PASS"' /tmp/out.json
  rm -f /tmp/test-fixture.diff /tmp/out.json
}

@test "check-hardcode: exempts localhost and example.com" {
  cat > /tmp/local.diff <<'EOF'
diff --git a/src/sap_cloud_sdk/mymod/client.py b/src/sap_cloud_sdk/mymod/client.py
index 111..222
--- a/src/sap_cloud_sdk/mymod/client.py
+++ b/src/sap_cloud_sdk/mymod/client.py
@@ -1,1 +1,2 @@
 x
+URL = "https://localhost:8080/api"
EOF
  DIFF_FILE=/tmp/local.diff bash "$SCRIPT_DIR/check-hardcode.sh" < /tmp/local.diff > /tmp/out.json
  # localhost is allowlisted
  jq -e '[.findings[] | select(.rule == "HC-01")] | length == 0' /tmp/out.json
  rm -f /tmp/local.diff /tmp/out.json
}

@test "check-disclosure: PR body Closes #<issue_number> triggers DIS-07" {
  pr_body=$(mktemp)
  echo "Closes #<issue_number>" > "$pr_body"
  cat > /tmp/empty.diff <<'EOF'
EOF
  DIFF_FILE=/tmp/empty.diff PR_BODY_FILE="$pr_body" bash "$SCRIPT_DIR/check-disclosure.sh" < /tmp/empty.diff > /tmp/out.json
  jq -e '.findings | map(.rule) | any(. == "DIS-07")' /tmp/out.json
  rm -f "$pr_body" /tmp/empty.diff /tmp/out.json
}
