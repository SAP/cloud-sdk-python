#!/usr/bin/env bats
# smoke tests for the SDK Module Review skill

setup() {
  SCRIPT_DIR="$BATS_TEST_DIRNAME/../../.claude/scripts"
  FIXTURES="$BATS_TEST_DIRNAME/fixtures"
  export LANGUAGE=python
  export REPO_ROOT="$BATS_TEST_DIRNAME/../.."
  export CONFIG_DIR="$REPO_ROOT/.claude/config"
}

# --- LIBS ---

@test "lib/json-emit.sh: emit_finding produces valid JSON" {
  source "$SCRIPT_DIR/lib/json-emit.sh"
  result=$(emit_finding "TEST-01" "BLOCK" "src/x.py" 42 "test message")
  echo "$result" | jq -e '.rule == "TEST-01"'
  echo "$result" | jq -e '.severity == "BLOCK"'
  echo "$result" | jq -e '.line == 42'
}

@test "lib/json-emit.sh: emit_report assembles findings correctly" {
  source "$SCRIPT_DIR/lib/json-emit.sh"
  result=$(printf '{"rule":"A","severity":"BLOCK","file":"f","line":1,"message":"m","suggestion":""}\n{"rule":"B","severity":"FLAG","file":"g","line":2,"message":"m","suggestion":""}\n' | emit_report "test" "python" "BLOCK" "2026-01-01T00:00:00Z")
  echo "$result" | jq -e '.check == "test"'
  echo "$result" | jq -e '.findings | length == 2'
  echo "$result" | jq -e '.summary.block_count == 1'
  echo "$result" | jq -e '.summary.flag_count == 1'
}

@test "lib/diff-added-lines.sh: extracts only added lines" {
  cat > /tmp/test.diff <<'EOF'
diff --git a/src/a.py b/src/a.py
--- a/src/a.py
+++ b/src/a.py
@@ -1,3 +1,4 @@
 context1
+added1
 context2
+added2
EOF
  result=$(bash "$SCRIPT_DIR/lib/diff-added-lines.sh" < /tmp/test.diff)
  echo "$result" | grep -q "src/a.py:2"
  echo "$result" | grep -q "src/a.py:4"
  ! echo "$result" | grep -q "context"
}

@test "lib/detect-language.sh: detects Python from pyproject.toml" {
  tmpd=$(mktemp -d)
  echo "[project]" > "$tmpd/pyproject.toml"
  mkdir -p "$tmpd/src/sap_cloud_sdk"
  result=$(bash "$SCRIPT_DIR/lib/detect-language.sh" "$tmpd")
  [ "$result" = "python" ]
  rm -rf "$tmpd"
}

@test "lib/predicates.sh: reuse_toml_aggregate_present returns true when REUSE.toml aggregate exists" {
  source "$SCRIPT_DIR/lib/predicates.sh"
  tmpd=$(mktemp -d)
  cat > "$tmpd/REUSE.toml" <<'EOF'
version = 1
[[annotations]]
path = "**"
SPDX-License-Identifier = "Apache-2.0"
EOF
  result=$(reuse_toml_aggregate_present "$tmpd")
  [ "$result" = "true" ]
  rm -rf "$tmpd"
}

@test "lib/predicates.sh: reuse_toml_aggregate_present false when no REUSE.toml" {
  source "$SCRIPT_DIR/lib/predicates.sh"
  tmpd=$(mktemp -d)
  result=$(reuse_toml_aggregate_present "$tmpd")
  [ "$result" = "false" ]
  rm -rf "$tmpd"
}

@test "lib/suppression.sh: parse_line detects ignore[hardcode]" {
  tmp=$(mktemp)
  cat > "$tmp" <<'EOF'
line1
timeout = 30  # sdk-review: ignore[hardcode]
line3
EOF
  result=$(bash "$SCRIPT_DIR/lib/suppression.sh" parse_line "$tmp")
  echo "$result" | grep -q ":2:hardcode"
  rm -f "$tmp"
}

@test "lib/suppression.sh: locked rules refuse suppression" {
  tmp=$(mktemp)
  echo "$tmp:1:SEC-01" > "$tmp.supp"
  result=$(bash "$SCRIPT_DIR/lib/suppression.sh" is_suppressed "SEC-01" "$tmp" 1 "$tmp.supp")
  [ "$result" = "false" ]
  rm -f "$tmp" "$tmp.supp"
}

# --- CHECKS ---

@test "check-secrets: fires BLOCK on AWS access key" {
  DIFF_FILE="$FIXTURES/secrets-aws-key.diff" bash "$SCRIPT_DIR/check-secrets.sh" < "$FIXTURES/secrets-aws-key.diff" > /tmp/out.json
  jq -e '.status == "BLOCK"' /tmp/out.json
  jq -e '.findings[0].rule == "SEC-01"' /tmp/out.json
}

@test "check-secrets: fires BLOCK on JWT token" {
  DIFF_FILE="$FIXTURES/secrets-jwt.diff" bash "$SCRIPT_DIR/check-secrets.sh" < "$FIXTURES/secrets-jwt.diff" > /tmp/out.json
  jq -e '.status == "BLOCK"' /tmp/out.json
  jq -e '.findings | map(.rule) | any(. == "SEC-06")' /tmp/out.json
}

@test "check-secrets: PASS on clean diff" {
  DIFF_FILE="$FIXTURES/clean.diff" bash "$SCRIPT_DIR/check-secrets.sh" < "$FIXTURES/clean.diff" > /tmp/out.json
  jq -e '.status == "PASS"' /tmp/out.json
}

@test "check-hardcode: fires BLOCK on hardcoded URL" {
  DIFF_FILE="$FIXTURES/hardcode-url.diff" bash "$SCRIPT_DIR/check-hardcode.sh" < "$FIXTURES/hardcode-url.diff" > /tmp/out.json
  jq -e '.findings | length > 0' /tmp/out.json
  jq -e '.findings | map(.rule) | any(. == "HC-01")' /tmp/out.json
}

@test "check-disclosure: fires on SAP-internal URL (public profile)" {
  DISCLOSURE_PROFILE=public DIFF_FILE="$FIXTURES/disclosure-internal.diff" bash "$SCRIPT_DIR/check-disclosure.sh" < "$FIXTURES/disclosure-internal.diff" > /tmp/out.json
  jq -e '.findings | map(.rule) | any(. == "DIS-01")' /tmp/out.json
  jq -e '.findings[0].severity == "BLOCK"' /tmp/out.json
}

@test "check-disclosure: internal profile downgrades DIS-01 to FLAG" {
  DISCLOSURE_PROFILE=internal DIFF_FILE="$FIXTURES/disclosure-internal.diff" bash "$SCRIPT_DIR/check-disclosure.sh" < "$FIXTURES/disclosure-internal.diff" > /tmp/out.json
  jq -e '.findings[0].severity == "FLAG"' /tmp/out.json
}

@test "check-license-spdx: REUSE.toml aggregate exempts LIC-01" {
  tmpd=$(mktemp -d)
  cat > "$tmpd/REUSE.toml" <<'EOF'
version = 1
[[annotations]]
path = "**"
SPDX-License-Identifier = "Apache-2.0"
EOF
  REPO_ROOT="$tmpd" DIFF_FILE="$FIXTURES/secrets-aws-key.diff" bash "$SCRIPT_DIR/check-license-spdx.sh" < "$FIXTURES/secrets-aws-key.diff" > /tmp/out.json
  jq -e '.status == "PASS"' /tmp/out.json
  rm -rf "$tmpd"
}

@test "check-license-spdx: fires BLOCK on new .py without SPDX header (no REUSE.toml)" {
  cat > /tmp/no-spdx.diff <<'EOF'
diff --git a/src/new.py b/src/new.py
new file mode 100644
index 0000000..abc
--- /dev/null
+++ b/src/new.py
@@ -0,0 +1,2 @@
+def foo():
+    pass
EOF
  tmpd=$(mktemp -d)
  REPO_ROOT="$tmpd" DIFF_FILE=/tmp/no-spdx.diff bash "$SCRIPT_DIR/check-license-spdx.sh" < /tmp/no-spdx.diff > /tmp/out.json
  jq -e '.status == "BLOCK"' /tmp/out.json
  jq -e '.findings | map(.rule) | any(. == "LIC-01")' /tmp/out.json
  rm -rf "$tmpd"
}

@test "check-binding-shape: fires BLOCK_LOCKED on /oauth/token concat" {
  LANGUAGE=java DIFF_FILE="$FIXTURES/binding-token-concat.diff" bash "$SCRIPT_DIR/check-binding-shape.sh" < "$FIXTURES/binding-token-concat.diff" > /tmp/out.json
  jq -e '.status == "BLOCK"' /tmp/out.json
  jq -e '.findings | map(.rule) | any(. == "BND-02")' /tmp/out.json
}

# --- AST checks ---

@test "ast-python-checks: EL-01 fires on raising different exception without from e" {
  cat > /tmp/bad.py <<'EOF'
def x():
    try:
        pass
    except ValueError as e:
        raise KeyError("nope")
EOF
  result=$(python3 "$SCRIPT_DIR/lib/ast_python_checks.py" el-01 /tmp/bad.py)
  echo "$result" | jq -e '.rule == "PY-EL-01"'
  rm -f /tmp/bad.py
}

@test "ast-python-checks: EL-01 PASSES on bare raise" {
  cat > /tmp/good.py <<'EOF'
def x():
    try:
        pass
    except ValueError:
        raise
EOF
  result=$(python3 "$SCRIPT_DIR/lib/ast_python_checks.py" el-01 /tmp/good.py)
  [ -z "$result" ]
  rm -f /tmp/good.py
}

@test "ast-python-checks: EL-01 PASSES on raise X from e" {
  cat > /tmp/good.py <<'EOF'
def x():
    try:
        pass
    except ValueError as e:
        raise KeyError("wrapped") from e
EOF
  result=$(python3 "$SCRIPT_DIR/lib/ast_python_checks.py" el-01 /tmp/good.py)
  [ -z "$result" ]
  rm -f /tmp/good.py
}

@test "ast-python-checks: TEL-02 fires on public *Client method without @record_metrics" {
  cat > /tmp/client.py <<'EOF'
class MyClient:
    def do_thing(self):
        pass
EOF
  result=$(python3 "$SCRIPT_DIR/lib/ast_python_checks.py" tel-02 /tmp/client.py)
  echo "$result" | jq -e '.rule == "PY-TEL-02"'
  rm -f /tmp/client.py
}

@test "ast-python-checks: TEL-02 PASSES when @record_metrics present" {
  cat > /tmp/client.py <<'EOF'
class MyClient:
    @record_metrics(Module.X, Operation.Y)
    def do_thing(self):
        pass
EOF
  result=$(python3 "$SCRIPT_DIR/lib/ast_python_checks.py" tel-02 /tmp/client.py)
  [ -z "$result" ]
  rm -f /tmp/client.py
}

@test "ast-python-checks: CON-01 fires on 3× repeated string" {
  cat > /tmp/const.py <<'EOF'
def x():
    a = "com.sap.adm.DocumentService"
    b = "com.sap.adm.DocumentService"
    c = "com.sap.adm.DocumentService"
EOF
  result=$(python3 "$SCRIPT_DIR/lib/ast_python_checks.py" con-01 /tmp/const.py)
  echo "$result" | jq -e '.rule == "PY-CON-01"'
  rm -f /tmp/const.py
}

# --- Full orchestrator dry-run ---

@test "orchestrate.sh: dry-run against secrets fixture exits 1 (BLOCK)" {
  tmpd=$(mktemp -d)
  cp -r "$REPO_ROOT/.claude" "$tmpd/"
  cd "$tmpd"
  echo "[project]" > pyproject.toml
  mkdir -p src/sap_cloud_sdk
  set +e
  DRY_RUN=true LOCAL_DIFF="$FIXTURES/secrets-aws-key.diff" REPO_ROOT="$tmpd" \
    bash .claude/scripts/orchestrate.sh 999 --dry-run > /dev/null 2>&1
  status=$?
  set -e
  [ "$status" -eq 1 ]
  rm -rf "$tmpd"
}

@test "orchestrate.sh: dry-run against clean fixture exits 0" {
  tmpd=$(mktemp -d)
  cp -r "$REPO_ROOT/.claude" "$tmpd/"
  cd "$tmpd"
  echo "[project]" > pyproject.toml
  mkdir -p src/sap_cloud_sdk
  DRY_RUN=true LOCAL_DIFF="$FIXTURES/clean.diff" REPO_ROOT="$tmpd" \
    bash .claude/scripts/orchestrate.sh 999 --dry-run
  rm -rf "$tmpd"
}
