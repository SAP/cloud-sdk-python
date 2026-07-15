#!/usr/bin/env bats
# test_fp_remediation.bats — regression tests for the 8 FP-* fixes catalogued
# in docs/plans 09-FP-REMEDIATION.md §2. Each test pins ONE fix so a future
# regression is caught immediately.
#
# Runs standalone (uses ADDED_LINES_FILE to feed the hunk filter). If a check
# script or lib helper isn't present in the current batch, the test is skipped.

setup() {
  SCRIPT_DIR="$BATS_TEST_DIRNAME/../../.claude/scripts"
  FIXTURES="$BATS_TEST_DIRNAME/fixtures"
  export LANGUAGE=python
  export REPO_ROOT="$BATS_TEST_DIRNAME/../.."
  export CONFIG_DIR="$REPO_ROOT/.claude/config"
}

# ------------------------------------------------------------
# FP-A-01 — hunk attribution enforced
# ------------------------------------------------------------

@test "FP-A-01: is_line_touched respects ADDED_LINES_FILE" {
  [ -f "$SCRIPT_DIR/lib/hunk-filter.sh" ] || skip "hunk-filter.sh not in this batch"
  tmpd=$(mktemp -d)
  cat > "$tmpd/added.txt" <<'EOF'
src/foo.py:5
src/foo.py:6
src/foo.py:7
src/foo.py:8
src/foo.py:9
src/foo.py:10
EOF
  # touched
  ADDED_LINES_FILE="$tmpd/added.txt" bash "$SCRIPT_DIR/lib/hunk-filter.sh" is_line_touched src/foo.py 7
  # not touched
  run env ADDED_LINES_FILE="$tmpd/added.txt" bash "$SCRIPT_DIR/lib/hunk-filter.sh" is_line_touched src/foo.py 100
  [ "$status" -ne 0 ]
  rm -rf "$tmpd"
}

@test "FP-A-01: is_meta_finding treats PR_BODY / COMMIT:* as metadata" {
  [ -f "$SCRIPT_DIR/lib/hunk-filter.sh" ] || skip "hunk-filter.sh not in this batch"
  bash "$SCRIPT_DIR/lib/hunk-filter.sh" is_meta_finding PR_BODY
  bash "$SCRIPT_DIR/lib/hunk-filter.sh" is_meta_finding COMMIT:abc123
  run bash "$SCRIPT_DIR/lib/hunk-filter.sh" is_meta_finding src/foo.py
  [ "$status" -ne 0 ]
}

# ------------------------------------------------------------
# FP-B-01 — HC-01 ignores POM/XML namespaces
# ------------------------------------------------------------

@test "FP-B-01: HC-01 does not fire on pom.xml POM namespace" {
  [ -f "$SCRIPT_DIR/check-hardcode.sh" ] || skip "check-hardcode.sh not in this batch"
  tmpd=$(mktemp -d)
  cat > "$tmpd/diff" <<'EOF'
diff --git a/pom.xml b/pom.xml
new file mode 100644
--- /dev/null
+++ b/pom.xml
@@ -0,0 +1,5 @@
+<?xml version="1.0"?>
+<project xmlns="http://maven.apache.org/POM/4.0.0"
+         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
+  <modelVersion>4.0.0</modelVersion>
+</project>
EOF
  bash "$SCRIPT_DIR/lib/diff-added-lines.sh" < "$tmpd/diff" > "$tmpd/added.txt"
  result=$(LANGUAGE=java ADDED_LINES_FILE="$tmpd/added.txt" DIFF_FILE="$tmpd/diff" bash "$SCRIPT_DIR/check-hardcode.sh")
  hc01_count=$(echo "$result" | jq '[.findings[] | select(.rule=="HC-01")] | length')
  [ "$hc01_count" = "0" ]
  rm -rf "$tmpd"
}

# ------------------------------------------------------------
# FP-B-02 — HTTP-01 ignores markdown code fences
# ------------------------------------------------------------

@test "FP-B-02: HTTP-01 does not fire on .md files" {
  [ -f "$SCRIPT_DIR/check-http-hygiene.sh" ] || skip "check-http-hygiene.sh not in this batch"
  tmpd=$(mktemp -d)
  cat > "$tmpd/diff" <<'EOF'
diff --git a/docs/user-guide.md b/docs/user-guide.md
new file mode 100644
--- /dev/null
+++ b/docs/user-guide.md
@@ -0,0 +1,4 @@
+# HTTP client usage
+```python
+client = httpx.Client()
+```
EOF
  bash "$SCRIPT_DIR/lib/diff-added-lines.sh" < "$tmpd/diff" > "$tmpd/added.txt"
  result=$(ADDED_LINES_FILE="$tmpd/added.txt" DIFF_FILE="$tmpd/diff" bash "$SCRIPT_DIR/check-http-hygiene.sh")
  http01_count=$(echo "$result" | jq '[.findings[] | select(.rule=="HTTP-01")] | length')
  [ "$http01_count" = "0" ]
  rm -rf "$tmpd"
}

# ------------------------------------------------------------
# FP-C-01 — BDD-01 accepts any *.feature file, not just <mod>.feature
# ------------------------------------------------------------

@test "FP-C-01: BDD-01 accepts scenarios.feature when module <mod>.feature is absent" {
  [ -f "$SCRIPT_DIR/check-bdd.sh" ] || skip "check-bdd.sh not in this batch"
  tmpd=$(mktemp -d)
  # Simulate a new module `foo` with source file and a feature file NOT
  # named foo.feature — BDD-01 must PASS (glob-based check).
  mkdir -p "$tmpd/src/sap_cloud_sdk/foo"
  echo "x = 1" > "$tmpd/src/sap_cloud_sdk/foo/client.py"
  mkdir -p "$tmpd/tests/foo/integration"
  echo "Feature: something else" > "$tmpd/tests/foo/integration/scenarios.feature"
  cat > "$tmpd/diff" <<'EOF'
diff --git a/src/sap_cloud_sdk/foo/client.py b/src/sap_cloud_sdk/foo/client.py
new file mode 100644
--- /dev/null
+++ b/src/sap_cloud_sdk/foo/client.py
@@ -0,0 +1,1 @@
+x = 1
EOF
  result=$(REPO_ROOT="$tmpd" DIFF_FILE="$tmpd/diff" LANGUAGE=python bash "$SCRIPT_DIR/check-bdd.sh")
  bdd01_count=$(echo "$result" | jq '[.findings[] | select(.rule=="BDD-01")] | length')
  [ "$bdd01_count" = "0" ]
  rm -rf "$tmpd"
}

# ------------------------------------------------------------
# FP-C-02 — PY-PT-04 accepts Exception subclass anywhere in module (AST)
# ------------------------------------------------------------

@test "FP-C-02: PY-PT-04 accepts Exception subclass in __init__.py (not exceptions.py)" {
  [ -f "$SCRIPT_DIR/lib/ast_python_checks.py" ] || skip "ast_python_checks.py not in this batch"
  tmpd=$(mktemp -d)
  mkdir -p "$tmpd/foo"
  cat > "$tmpd/foo/__init__.py" <<'EOF'
class FooError(Exception):
    pass
EOF
  # pt-04 helper returns exit 0 if module has any Exception subclass.
  python3 "$SCRIPT_DIR/lib/ast_python_checks.py" pt-04 "$tmpd/foo"
  # Negative: empty module → exit 1
  mkdir -p "$tmpd/bar"
  echo "x = 1" > "$tmpd/bar/__init__.py"
  run python3 "$SCRIPT_DIR/lib/ast_python_checks.py" pt-04 "$tmpd/bar"
  [ "$status" -ne 0 ]
  rm -rf "$tmpd"
}

# ------------------------------------------------------------
# FP-D-01 — PY-CON-01 skips generated model files + per-file cap
# ------------------------------------------------------------

@test "FP-D-01: PY-CON-01 skips _models.py files entirely" {
  [ -f "$SCRIPT_DIR/lib/ast_python_checks.py" ] || skip "ast_python_checks.py not in this batch"
  tmpd=$(mktemp -d)
  cat > "$tmpd/_models.py" <<'EOF'
class A: x = "value"; y = "value"; z = "value"; w = "value"
class B: x = "value"; y = "value"; z = "value"
EOF
  result=$(python3 "$SCRIPT_DIR/lib/ast_python_checks.py" con-01 "$tmpd/_models.py" 2>/dev/null)
  # Expect zero findings (file skipped)
  [ -z "$result" ]
  rm -rf "$tmpd"
}

@test "FP-D-01: PY-CON-01 caps at 3 findings per file" {
  [ -f "$SCRIPT_DIR/lib/ast_python_checks.py" ] || skip "ast_python_checks.py not in this batch"
  tmpd=$(mktemp -d)
  # Six different repeated literals (each ≥3× and ≥3 chars) — should be capped to 3.
  cat > "$tmpd/regular.py" <<'EOF'
a = "foo1234"; b = "foo1234"; c = "foo1234"
d = "bar1234"; e = "bar1234"; f = "bar1234"
g = "baz1234"; h = "baz1234"; i = "baz1234"
j = "qux1234"; k = "qux1234"; l = "qux1234"
m = "quux12"; n = "quux12"; o = "quux12"
p = "corge2"; q = "corge2"; r = "corge2"
EOF
  count=$(python3 "$SCRIPT_DIR/lib/ast_python_checks.py" con-01 "$tmpd/regular.py" 2>/dev/null | wc -l | tr -d ' ')
  [ "$count" -le 3 ]
  rm -rf "$tmpd"
}

# ------------------------------------------------------------
# FP-E-01 — PY-PT-08 baseline suppresses pre-existing lines
# ------------------------------------------------------------

@test "FP-E-01: is_in_line_baseline matches (rule,file,line) triple" {
  [ -f "$SCRIPT_DIR/lib/baseline.sh" ] || skip "baseline.sh not in this batch"
  # Skip if this batch's baseline.sh lacks the new function.
  grep -q "is_in_line_baseline" "$SCRIPT_DIR/lib/baseline.sh" || skip "baseline.sh lacks is_in_line_baseline"
  tmpd=$(mktemp -d)
  cat > "$tmpd/baseline.json" <<'EOF'
{
  "line_baseline": [
    {"rule": "PY-PT-08", "file": "src/foo/__init__.py", "line": 81},
    {"rule": "PY-PT-08", "file": "src/foo/__init__.py", "line": 127}
  ]
}
EOF
  BASELINE_FILE="$tmpd/baseline.json" bash "$SCRIPT_DIR/lib/baseline.sh" is_in_line_baseline PY-PT-08 src/foo/__init__.py 81
  BASELINE_FILE="$tmpd/baseline.json" bash "$SCRIPT_DIR/lib/baseline.sh" is_in_line_baseline PY-PT-08 src/foo/__init__.py 127
  # Not baselined
  run env BASELINE_FILE="$tmpd/baseline.json" bash "$SCRIPT_DIR/lib/baseline.sh" is_in_line_baseline PY-PT-08 src/foo/__init__.py 999
  [ "$status" -ne 0 ]
  # Prefix-guard: 81 must NOT match 812
  cat > "$tmpd/baseline.json" <<'EOF'
{"line_baseline": [{"rule":"PY-PT-08","file":"src/foo.py","line":81}]}
EOF
  run env BASELINE_FILE="$tmpd/baseline.json" bash "$SCRIPT_DIR/lib/baseline.sh" is_in_line_baseline PY-PT-08 src/foo.py 812
  [ "$status" -ne 0 ]
  rm -rf "$tmpd"
}

# ------------------------------------------------------------
# DEL-01 guardrail — synthetic path is not filtered out
# ------------------------------------------------------------

@test "DEL-01: guardrail — synthetic src/ path is treated as metadata by hunk filter" {
  [ -f "$SCRIPT_DIR/lib/hunk-filter.sh" ] || skip "hunk-filter.sh not in this batch"
  # is_meta_finding returns 0 for special paths. src/ is a real path so we test
  # the emit_finding_if_touched path — DEL-01's src/:1 emission bypasses the
  # filter because the calling script does NOT wrap it (verified via grep).
  ! grep -q "emit_finding_if_touched \"DEL-01\"" "$SCRIPT_DIR/check-deletion-hygiene.sh"
  # DEL-01 is called via plain emit_finding — the fix is deliberate.
}

# ------------------------------------------------------------
# FP-G-01 — peer-consistency for PT-01 (no more "factory required" law)
# ------------------------------------------------------------

@test "FP-G-01: peer_element_fraction returns adopted/total/fraction" {
  [ -f "$SCRIPT_DIR/lib/peer-consistency.sh" ] || skip "peer-consistency.sh not in this batch"
  tmpd=$(mktemp -d)
  mkdir -p "$tmpd/src/sap_cloud_sdk/a" "$tmpd/src/sap_cloud_sdk/b" "$tmpd/src/sap_cloud_sdk/c"
  # a and b have user-guide.md; c doesn't
  touch "$tmpd/src/sap_cloud_sdk/a/user-guide.md" "$tmpd/src/sap_cloud_sdk/b/user-guide.md"
  result=$(bash "$SCRIPT_DIR/lib/peer-consistency.sh" peer_element_fraction "$tmpd" python user-guide.md)
  adopted=$(echo "$result" | awk '{print $1}')
  total=$(echo "$result" | awk '{print $2}')
  [ "$adopted" = "2" ]
  [ "$total" = "3" ]
  rm -rf "$tmpd"
}

@test "FP-G-01: PT-01 fires FLAG when new module lacks a >=80% adopted element" {
  [ -f "$SCRIPT_DIR/check-patterns.sh" ] || skip "check-patterns.sh not in this batch"
  tmpd=$(mktemp -d)
  # Peers a, b, c all have user-guide.md (100%). New module `foo` doesn't.
  mkdir -p "$tmpd/src/sap_cloud_sdk/"{a,b,c,foo}
  for m in a b c; do
    touch "$tmpd/src/sap_cloud_sdk/$m/user-guide.md"
    touch "$tmpd/src/sap_cloud_sdk/$m/client.py"
    echo "def create_${m}_client(): pass" > "$tmpd/src/sap_cloud_sdk/$m/client.py"
  done
  # foo has client.py but no user-guide.md → should FLAG
  echo "class FooClient: pass" > "$tmpd/src/sap_cloud_sdk/foo/client.py"
  # Diff creates foo — client shape
  cat > "$tmpd/diff" <<'EOF'
diff --git a/src/sap_cloud_sdk/foo/client.py b/src/sap_cloud_sdk/foo/client.py
new file mode 100644
--- /dev/null
+++ b/src/sap_cloud_sdk/foo/client.py
@@ -0,0 +1,1 @@
+class FooClient: pass
EOF
  result=$(REPO_ROOT="$tmpd" DIFF_FILE="$tmpd/diff" LANGUAGE=python bash "$SCRIPT_DIR/check-patterns.sh" 2>/dev/null)
  # PY-PT-01 should fire FLAG (not BLOCK) mentioning user-guide.md
  pt01_flag=$(echo "$result" | jq '[.findings[] | select(.rule=="PY-PT-01" and .severity=="FLAG")] | length')
  [ "$pt01_flag" -ge 1 ]
  pt01_block=$(echo "$result" | jq '[.findings[] | select(.rule=="PY-PT-01" and .severity=="BLOCK")] | length')
  [ "$pt01_block" = "0" ]
  rm -rf "$tmpd"
}

@test "FP-G-01: PT-01 does NOT fire when peers <80% adopt the element (factory case)" {
  [ -f "$SCRIPT_DIR/check-patterns.sh" ] || skip "check-patterns.sh not in this batch"
  tmpd=$(mktemp -d)
  # 3 peers: only 1 has create_*_client → 33% adoption of factory element.
  mkdir -p "$tmpd/src/sap_cloud_sdk/"{a,b,c,foo}
  echo "def create_a_client(): pass" > "$tmpd/src/sap_cloud_sdk/a/client.py"
  echo "class BClient: pass" > "$tmpd/src/sap_cloud_sdk/b/client.py"
  echo "class CClient: pass" > "$tmpd/src/sap_cloud_sdk/c/client.py"
  echo "class FooClient: pass" > "$tmpd/src/sap_cloud_sdk/foo/client.py"
  cat > "$tmpd/diff" <<'EOF'
diff --git a/src/sap_cloud_sdk/foo/client.py b/src/sap_cloud_sdk/foo/client.py
new file mode 100644
--- /dev/null
+++ b/src/sap_cloud_sdk/foo/client.py
@@ -0,0 +1,1 @@
+class FooClient: pass
EOF
  result=$(REPO_ROOT="$tmpd" DIFF_FILE="$tmpd/diff" LANGUAGE=python bash "$SCRIPT_DIR/check-patterns.sh" 2>/dev/null)
  # No factory-related PT-01 finding
  factory_flag=$(echo "$result" | jq '[.findings[] | select(.rule=="PY-PT-01" and (.message | contains("factory")))] | length')
  [ "$factory_flag" = "0" ]
  rm -rf "$tmpd"
}

@test "FP-G-01: PT-01 emits zero findings when module has every universal element" {
  [ -f "$SCRIPT_DIR/check-patterns.sh" ] || skip "check-patterns.sh not in this batch"
  tmpd=$(mktemp -d)
  # 3 peers with user-guide.md; foo also has it and everything else uncommon.
  mkdir -p "$tmpd/src/sap_cloud_sdk/"{a,b,c,foo}
  for m in a b c foo; do
    touch "$tmpd/src/sap_cloud_sdk/$m/user-guide.md"
    echo "class ${m^}Client: pass" > "$tmpd/src/sap_cloud_sdk/$m/client.py"
  done
  cat > "$tmpd/diff" <<'EOF'
diff --git a/src/sap_cloud_sdk/foo/client.py b/src/sap_cloud_sdk/foo/client.py
new file mode 100644
--- /dev/null
+++ b/src/sap_cloud_sdk/foo/client.py
@@ -0,0 +1,1 @@
+class FooClient: pass
EOF
  result=$(REPO_ROOT="$tmpd" DIFF_FILE="$tmpd/diff" LANGUAGE=python bash "$SCRIPT_DIR/check-patterns.sh" 2>/dev/null)
  pt01_count=$(echo "$result" | jq '[.findings[] | select(.rule=="PY-PT-01")] | length')
  [ "$pt01_count" = "0" ]
  rm -rf "$tmpd"
}

@test "FP-H-01: HC-01 does not fire on uv.lock" {
  [ -f "$SCRIPT_DIR/check-hardcode.sh" ] || skip "check-hardcode.sh not in this batch"
  tmpd=$(mktemp -d)
  cat > "$tmpd/diff" <<'DIFF'
diff --git a/uv.lock b/uv.lock
new file mode 100644
--- /dev/null
+++ b/uv.lock
@@ -0,0 +1,3 @@
+url = "https://files.pythonhosted.org/packages/aa/bb/foo-1.0.tar.gz"
+url = "https://files.pythonhosted.org/packages/cc/dd/bar-2.0.tar.gz"
+other = "value"
DIFF
  result=$(DIFF_FILE="$tmpd/diff" LANGUAGE=python bash "$SCRIPT_DIR/check-hardcode.sh" 2>/dev/null)
  hc01_count=$(echo "$result" | jq '[.findings[] | select(.rule=="HC-01")] | length')
  [ "$hc01_count" = "0" ]
  rm -rf "$tmpd"
}

@test "FP-H-01: HC-01 does not fire on poetry.lock / package-lock.json" {
  [ -f "$SCRIPT_DIR/check-hardcode.sh" ] || skip "check-hardcode.sh not in this batch"
  tmpd=$(mktemp -d)
  cat > "$tmpd/diff" <<'DIFF'
diff --git a/poetry.lock b/poetry.lock
new file mode 100644
--- /dev/null
+++ b/poetry.lock
@@ -0,0 +1,1 @@
+url = "https://files.pythonhosted.org/packages/foo.tar.gz"
diff --git a/package-lock.json b/package-lock.json
new file mode 100644
--- /dev/null
+++ b/package-lock.json
@@ -0,0 +1,1 @@
+"resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz"
DIFF
  result=$(DIFF_FILE="$tmpd/diff" LANGUAGE=python bash "$SCRIPT_DIR/check-hardcode.sh" 2>/dev/null)
  hc01_count=$(echo "$result" | jq '[.findings[] | select(.rule=="HC-01")] | length')
  [ "$hc01_count" = "0" ]
  rm -rf "$tmpd"
}

@test "FP-I-01: HC-01 does not fire on .env.example templates" {
  [ -f "$SCRIPT_DIR/check-hardcode.sh" ] || skip "check-hardcode.sh not in this batch"
  tmpd=$(mktemp -d)
  cat > "$tmpd/diff" <<'DIFF'
diff --git a/.env_integration_tests.example b/.env_integration_tests.example
new file mode 100644
--- /dev/null
+++ b/.env_integration_tests.example
@@ -0,0 +1,3 @@
+API_URL=https://your-api-url-here.com
+AUTH_URL=https://your-auth-url.example.com
+OTHER=value
DIFF
  result=$(DIFF_FILE="$tmpd/diff" LANGUAGE=python bash "$SCRIPT_DIR/check-hardcode.sh" 2>/dev/null)
  hc01_count=$(echo "$result" | jq '[.findings[] | select(.rule=="HC-01")] | length')
  [ "$hc01_count" = "0" ]
  rm -rf "$tmpd"
}

@test "FP-J-01: LIC-01/02 skips when repo lacks SPDX in existing files" {
  [ -f "$SCRIPT_DIR/check-license-spdx.sh" ] || skip "check-license-spdx.sh not in this batch"
  tmpd=$(mktemp -d)
  mkdir -p "$tmpd/src/main/java/com/sap"
  # Create 5 existing java files, none with SPDX
  for i in 1 2 3 4 5; do
    echo "package com.sap;" > "$tmpd/src/main/java/com/sap/Foo${i}.java"
    echo "public class Foo${i} {}" >> "$tmpd/src/main/java/com/sap/Foo${i}.java"
  done
  cat > "$tmpd/diff" <<'DIFF'
diff --git a/src/main/java/com/sap/NewClient.java b/src/main/java/com/sap/NewClient.java
new file mode 100644
--- /dev/null
+++ b/src/main/java/com/sap/NewClient.java
@@ -0,0 +1,2 @@
+package com.sap;
+public class NewClient {}
DIFF
  result=$(REPO_ROOT="$tmpd" DIFF_FILE="$tmpd/diff" LANGUAGE=java bash "$SCRIPT_DIR/check-license-spdx.sh" 2>/dev/null)
  lic_count=$(echo "$result" | jq '[.findings[] | select(.rule | startswith("LIC-"))] | length')
  [ "$lic_count" = "0" ]
  # Should have a pass_criteria_met entry mentioning no consistent adoption
  no_adoption=$(echo "$result" | jq '.summary.pass_criteria_met | any(contains("no consistent SPDX adoption"))')
  [ "$no_adoption" = "true" ]
  rm -rf "$tmpd"
}

@test "FP-J-01: LIC-01/02 still fires when repo has SPDX in existing files" {
  [ -f "$SCRIPT_DIR/check-license-spdx.sh" ] || skip "check-license-spdx.sh not in this batch"
  tmpd=$(mktemp -d)
  mkdir -p "$tmpd/src/main/java/com/sap"
  # Create 5 existing files, all with SPDX
  for i in 1 2 3 4 5; do
    cat > "$tmpd/src/main/java/com/sap/Foo${i}.java" <<HDR
// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 SAP SE
package com.sap;
public class Foo${i} {}
HDR
  done
  cat > "$tmpd/diff" <<'DIFF'
diff --git a/src/main/java/com/sap/NewClient.java b/src/main/java/com/sap/NewClient.java
new file mode 100644
--- /dev/null
+++ b/src/main/java/com/sap/NewClient.java
@@ -0,0 +1,2 @@
+package com.sap;
+public class NewClient {}
DIFF
  result=$(REPO_ROOT="$tmpd" DIFF_FILE="$tmpd/diff" LANGUAGE=java bash "$SCRIPT_DIR/check-license-spdx.sh" 2>/dev/null)
  lic01=$(echo "$result" | jq '[.findings[] | select(.rule=="LIC-01")] | length')
  [ "$lic01" = "1" ]
  rm -rf "$tmpd"
}

@test "FP-K-01: PY-CON-01 does not count occurrences outside PR added-lines set" {
  [ -f "$SCRIPT_DIR/lib/ast_python_checks.py" ] || skip "ast_python_checks.py not present"
  tmpd=$(mktemp -d)

  # File with 5 occurrences of a repeated string; PR only touches unrelated lines
  cat > "$tmpd/module.py" <<'PY'
"""module."""
CONST_A = "value-1"

def a():
    logger.info("customer credentials at path")   # line 5

def b():
    logger.info("customer credentials at path")   # line 8

def c():
    logger.info("customer credentials at path")   # line 11

def d():
    logger.info("customer credentials at path")   # line 14

def e():
    logger.info("customer credentials at path")   # line 17
PY

  # Added-lines set says PR only touched lines 1 and 2 (unrelated docstring/const)
  cat > "$tmpd/added-lines.txt" <<'ADDED'
$tmpd/module.py:1
$tmpd/module.py:2
ADDED
  # Substitute the actual tmp path into the added-lines file
  sed -i '' "s|\$tmpd|$tmpd|g" "$tmpd/added-lines.txt"

  ADDED_LINES_FILE="$tmpd/added-lines.txt" \
    python3 "$SCRIPT_DIR/lib/ast_python_checks.py" con-01 "$tmpd/module.py" > "$tmpd/out.jsonl"

  count=$(wc -l < "$tmpd/out.jsonl" | tr -d ' ')
  # Should be 0 because none of the 5 occurrences are on added lines
  [ "$count" = "0" ]
  rm -rf "$tmpd"
}

@test "FP-K-01: PY-CON-01 fires when at least one occurrence is on an added line" {
  [ -f "$SCRIPT_DIR/lib/ast_python_checks.py" ] || skip "ast_python_checks.py not present"
  tmpd=$(mktemp -d)

  cat > "$tmpd/module.py" <<'PY'
"""module."""

def a():
    logger.info("customer credentials at path")   # line 4

def b():
    logger.info("customer credentials at path")   # line 7

def c():
    logger.info("customer credentials at path")   # line 10
PY

  # PR touches line 4 (one of the occurrences)
  cat > "$tmpd/added-lines.txt" <<ADDED
$tmpd/module.py:4
ADDED

  ADDED_LINES_FILE="$tmpd/added-lines.txt" \
    python3 "$SCRIPT_DIR/lib/ast_python_checks.py" con-01 "$tmpd/module.py" > "$tmpd/out.jsonl"

  count=$(wc -l < "$tmpd/out.jsonl" | tr -d ' ')
  [ "$count" = "1" ]
  # Anchor line should be the added-line occurrence (4), not the first overall
  anchor=$(jq -r '.line' "$tmpd/out.jsonl")
  [ "$anchor" = "4" ]
  rm -rf "$tmpd"
}

@test "FP-U-01: TD-checkbox PASS when tests are in multi-module Maven path (sdk-adms/src/test/)" {
  [ -f "$SCRIPT_DIR/check-testing-depth.sh" ] || skip "check-testing-depth.sh not present"
  tmpd=$(mktemp -d)
  cat > "$tmpd/diff" <<'DIFF'
diff --git a/sdk-adms/src/test/java/com/sap/cloud/sdk/adms/AdmsHttpCallsTest.java b/sdk-adms/src/test/java/com/sap/cloud/sdk/adms/AdmsHttpCallsTest.java
new file mode 100644
--- /dev/null
+++ b/sdk-adms/src/test/java/com/sap/cloud/sdk/adms/AdmsHttpCallsTest.java
@@ -0,0 +1,1 @@
+public class AdmsHttpCallsTest {}
DIFF
  cat > "$tmpd/body" <<'BODY'
- [x] I have added/updated automated tests to cover my changes
BODY
  result=$(DIFF_FILE="$tmpd/diff" PR_BODY_FILE="$tmpd/body" LANGUAGE=java \
    bash "$SCRIPT_DIR/check-testing-depth.sh" 2>/dev/null)
  status=$(echo "$result" | jq -r '.status')
  [ "$status" = "PASS" ]
  rm -rf "$tmpd"
}

@test "FP-U-01: TD-checkbox still fires when no tests at all in multi-module repo" {
  [ -f "$SCRIPT_DIR/check-testing-depth.sh" ] || skip "check-testing-depth.sh not present"
  tmpd=$(mktemp -d)
  cat > "$tmpd/diff" <<'DIFF'
diff --git a/sdk-adms/src/main/java/com/sap/cloud/sdk/adms/AdmsClient.java b/sdk-adms/src/main/java/com/sap/cloud/sdk/adms/AdmsClient.java
new file mode 100644
--- /dev/null
+++ b/sdk-adms/src/main/java/com/sap/cloud/sdk/adms/AdmsClient.java
@@ -0,0 +1,1 @@
+public class AdmsClient {}
DIFF
  cat > "$tmpd/body" <<'BODY'
- [x] I have added/updated automated tests to cover my changes
BODY
  result=$(DIFF_FILE="$tmpd/diff" PR_BODY_FILE="$tmpd/body" LANGUAGE=java \
    bash "$SCRIPT_DIR/check-testing-depth.sh" 2>/dev/null)
  count=$(echo "$result" | jq '[.findings[] | select(.rule=="TD-checkbox")] | length')
  [ "$count" = "1" ]
  rm -rf "$tmpd"
}

# ── Corpus-2026-07-15 batch ─────────────────────────────────────────────────

@test "FP-P: SEC-07 does not fire on PEM stub in tests/ directory" {
  [ -f "$SCRIPT_DIR/check-secrets.sh" ] || skip "check-secrets.sh not present"
  tmpd=$(mktemp -d)
  cat > "$tmpd/diff" <<'DIFF'
diff --git a/tests/unit/test_auth.py b/tests/unit/test_auth.py
new file mode 100644
--- /dev/null
+++ b/tests/unit/test_auth.py
@@ -0,0 +1,1 @@
+FAKE = "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----"
DIFF
  result=$(DIFF_FILE="$tmpd/diff" LANGUAGE=python bash "$SCRIPT_DIR/check-secrets.sh" 2>/dev/null)
  count=$(echo "$result" | jq '[.findings[] | select(.rule=="SEC-07")] | length')
  [ "$count" = "0" ]
  rm -rf "$tmpd"
}

@test "FP-P: SEC-07 still fires on PEM in src/ (not a test file)" {
  [ -f "$SCRIPT_DIR/check-secrets.sh" ] || skip "check-secrets.sh not present"
  tmpd=$(mktemp -d)
  cat > "$tmpd/diff" <<'DIFF'
diff --git a/src/sap_cloud_sdk/module/client.py b/src/sap_cloud_sdk/module/client.py
new file mode 100644
--- /dev/null
+++ b/src/sap_cloud_sdk/module/client.py
@@ -0,0 +1,1 @@
+REAL = "-----BEGIN EC PRIVATE KEY-----\nrealkeycontent\n-----END EC PRIVATE KEY-----"
DIFF
  result=$(DIFF_FILE="$tmpd/diff" LANGUAGE=python bash "$SCRIPT_DIR/check-secrets.sh" 2>/dev/null)
  count=$(echo "$result" | jq '[.findings[] | select(.rule=="SEC-07")] | length')
  [ "$count" = "1" ]
  rm -rf "$tmpd"
}

@test "FP-Q: TD-10 does not fire for existing module touched but not newly created" {
  [ -f "$SCRIPT_DIR/check-testing-depth.sh" ] || skip "check-testing-depth.sh not present"
  tmpd=$(mktemp -d)
  # Diff touches agentgateway but no new __init__.py
  cat > "$tmpd/diff" <<'DIFF'
diff --git a/src/sap_cloud_sdk/agentgateway/agw_client.py b/src/sap_cloud_sdk/agentgateway/agw_client.py
--- a/src/sap_cloud_sdk/agentgateway/agw_client.py
+++ b/src/sap_cloud_sdk/agentgateway/agw_client.py
@@ -1,1 +1,2 @@
 existing_line = 1
+new_line = 2
DIFF
  result=$(DIFF_FILE="$tmpd/diff" LANGUAGE=python bash "$SCRIPT_DIR/check-testing-depth.sh" 2>/dev/null)
  count=$(echo "$result" | jq '[.findings[] | select(.rule=="TD-10")] | length')
  [ "$count" = "0" ]
  rm -rf "$tmpd"
}

@test "FP-Q: TD-10 fires when __init__.py is added as new file mode" {
  [ -f "$SCRIPT_DIR/check-testing-depth.sh" ] || skip "check-testing-depth.sh not present"
  tmpd=$(mktemp -d)
  cat > "$tmpd/diff" <<'DIFF'
diff --git a/src/sap_cloud_sdk/newmod/__init__.py b/src/sap_cloud_sdk/newmod/__init__.py
new file mode 100644
--- /dev/null
+++ b/src/sap_cloud_sdk/newmod/__init__.py
@@ -0,0 +1,1 @@
+"""New module."""
DIFF
  result=$(DIFF_FILE="$tmpd/diff" LANGUAGE=python bash "$SCRIPT_DIR/check-testing-depth.sh" 2>/dev/null)
  count=$(echo "$result" | jq '[.findings[] | select(.rule=="TD-10")] | length')
  [ "$count" = "1" ]
  rm -rf "$tmpd"
}

@test "FP-N: HC-01 does not fire on *.example.com subdomain" {
  [ -f "$SCRIPT_DIR/check-hardcode.sh" ] || skip "check-hardcode.sh not present"
  tmpd=$(mktemp -d)
  cat > "$tmpd/diff" <<'DIFF'
diff --git a/src/sap_cloud_sdk/module/_models.py b/src/sap_cloud_sdk/module/_models.py
new file mode 100644
--- /dev/null
+++ b/src/sap_cloud_sdk/module/_models.py
@@ -0,0 +1,1 @@
+    url: str = "https://storage.example.com/documents/file.pdf"
DIFF
  result=$(DIFF_FILE="$tmpd/diff" LANGUAGE=python bash "$SCRIPT_DIR/check-hardcode.sh" 2>/dev/null)
  count=$(echo "$result" | jq '[.findings[] | select(.rule=="HC-01")] | length')
  [ "$count" = "0" ]
  rm -rf "$tmpd"
}

@test "FP-O: HC-01 does not fire on URL with <placeholder> token" {
  [ -f "$SCRIPT_DIR/check-hardcode.sh" ] || skip "check-hardcode.sh not present"
  tmpd=$(mktemp -d)
  cat > "$tmpd/diff" <<'DIFF'
diff --git a/src/sap_cloud_sdk/module/config.py b/src/sap_cloud_sdk/module/config.py
new file mode 100644
--- /dev/null
+++ b/src/sap_cloud_sdk/module/config.py
@@ -0,0 +1,1 @@
+    url: str = "https://api.<region>.ngdpi.dpp.cloud.sap/v1"
DIFF
  result=$(DIFF_FILE="$tmpd/diff" LANGUAGE=python bash "$SCRIPT_DIR/check-hardcode.sh" 2>/dev/null)
  count=$(echo "$result" | jq '[.findings[] | select(.rule=="HC-01")] | length')
  [ "$count" = "0" ]
  rm -rf "$tmpd"
}

@test "DIS-07 is FLAG (not BLOCK) for docs-only PR" {
  [ -f "$SCRIPT_DIR/check-disclosure.sh" ] || skip "check-disclosure.sh not present"
  tmpd=$(mktemp -d)
  # Diff only touches docs/ — no src/
  cat > "$tmpd/diff" <<'DIFF'
diff --git a/docs/README.md b/docs/README.md
--- a/docs/README.md
+++ b/docs/README.md
@@ -1,1 +1,2 @@
+# Updated
DIFF
  cat > "$tmpd/body" <<'BODY'
Closes #<issue_number>
BODY
  result=$(DIFF_FILE="$tmpd/diff" PR_BODY_FILE="$tmpd/body" LANGUAGE=python bash "$SCRIPT_DIR/check-disclosure.sh" 2>/dev/null)
  severity=$(echo "$result" | jq -r '.findings[] | select(.rule=="DIS-07") | .severity')
  [ "$severity" = "FLAG" ]
  rm -rf "$tmpd"
}

@test "DIS-07 is BLOCK for PR that changes src/" {
  [ -f "$SCRIPT_DIR/check-disclosure.sh" ] || skip "check-disclosure.sh not present"
  tmpd=$(mktemp -d)
  cat > "$tmpd/diff" <<'DIFF'
diff --git a/src/sap_cloud_sdk/module/client.py b/src/sap_cloud_sdk/module/client.py
--- a/src/sap_cloud_sdk/module/client.py
+++ b/src/sap_cloud_sdk/module/client.py
@@ -1,1 +1,2 @@
+new_feature = True
DIFF
  cat > "$tmpd/body" <<'BODY'
Closes #<issue_number>
BODY
  result=$(DIFF_FILE="$tmpd/diff" PR_BODY_FILE="$tmpd/body" LANGUAGE=python bash "$SCRIPT_DIR/check-disclosure.sh" 2>/dev/null)
  severity=$(echo "$result" | jq -r '.findings[] | select(.rule=="DIS-07") | .severity')
  [ "$severity" = "BLOCK" ]
  rm -rf "$tmpd"
}
