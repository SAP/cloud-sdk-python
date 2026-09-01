#!/usr/bin/env bash
# check-telemetry.sh — verify telemetry instrumentation.
# Python: @record_metrics on public *Client methods + emission tests.
# Java: Telemetry.executeWithTelemetry(...) wrapping + tests.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/json-emit.sh
source "$SCRIPT_DIR/lib/json-emit.sh"
# shellcheck source=lib/hunk-filter.sh
source "$SCRIPT_DIR/lib/hunk-filter.sh"
# shellcheck source=lib/skill-self-skip.sh
source "$SCRIPT_DIR/lib/skill-self-skip.sh"

LANGUAGE="${LANGUAGE:-python}"
REPO_ROOT="${REPO_ROOT:-.}"
DIFF_FILE="${DIFF_FILE:-/dev/stdin}"

STARTED=$(now_iso)
findings=$(mktemp)
trap 'rm -f "$findings"' EXIT

diff_content=$(cat "$DIFF_FILE" 2>/dev/null || echo "")

# Get list of client files newly added or modified
if [ "$LANGUAGE" = "python" ]; then
  client_files=$(echo "$diff_content" | { grep -oE '^\+\+\+ b/src/sap_cloud_sdk/[a-z_]+/.*Client\.py|^\+\+\+ b/src/sap_cloud_sdk/[a-z_]+/client\.py' 2>/dev/null || true; } | sed 's|^+++ b/||' | sort -u)
else
  client_files=$(echo "$diff_content" | { grep -oE '^\+\+\+ b/src/main/java/com/sap/cloud/sdk/[a-z_]+/.*Client\.java' 2>/dev/null || true; } | sed 's|^+++ b/||' | sort -u)
fi

# Detect new decorator additions ONLY inside client files (scope predicate).
# Previously this counted @record_metrics from any added line — including tests,
# examples, and skill files — which produced false PY-TEL-06 findings.
if [ "$LANGUAGE" = "python" ]; then
  if [ -n "$client_files" ]; then
    # Build an awk-friendly set of client paths
    new_decorators=$(echo "$diff_content" | awk -v files="$client_files" '
      BEGIN {
        n = split(files, arr, "\n")
        for (i=1; i<=n; i++) if (arr[i] != "") set[arr[i]] = 1
        current = ""
      }
      /^\+\+\+ b\// { current = substr($0, 7); next }
      /^\+[[:space:]]*@record_metrics/ {
        if (current in set) count++
        next
      }
      END { print count+0 }
    ')
  else
    new_decorators=0
  fi
  # All SDK module-level Python files for PY-TEL-07 (wider than *Client.py)
  module_files=$(echo "$diff_content" | { grep -oE '^\+\+\+ b/src/sap_cloud_sdk/[a-z_/]+/[a-z_]+\.py' 2>/dev/null || true; } | sed 's|^+++ b/||' | sort -u)
else
  new_decorators=$(echo "$diff_content" | { grep -E '^\+.*Telemetry\.executeWithTelemetry' 2>/dev/null || true; } | wc -l | tr -d ' ')
fi

# PY-TEL-02: For each changed client file, run AST check
# FP-A-01: filter by hunk attribution — a client method predates the PR unless
# it lives on a line the PR added.
if [ "$LANGUAGE" = "python" ] && [ -n "$client_files" ]; then
  raw_tel=$(mktemp); trap 'rm -f "$raw_tel"' EXIT
  # shellcheck disable=SC2086
  python3 "$SCRIPT_DIR/lib/ast_python_checks.py" tel-02 $client_files 2>/dev/null > "$raw_tel" || true
  while IFS= read -r finding; do
    [ -z "$finding" ] && continue
    f=$(echo "$finding" | python3 -c "import json,sys;o=json.loads(sys.stdin.read());print(o.get('file',''))")
    ln=$(echo "$finding" | python3 -c "import json,sys;o=json.loads(sys.stdin.read());print(o.get('line',0))")
    [ -z "$f" ] && continue
    if is_line_touched "$f" "$ln"; then
      echo "$finding" >> "$findings"
    fi
  done < "$raw_tel"
  rm -f "$raw_tel"
fi


# PY-TEL-07: module-level public fns should have @record_metrics when siblings do
# Catches functions like watch_aicore_config / patch_litellm_for_credential_rotation
# that were flagged by Betina on PR #256.
if [ "$LANGUAGE" = "python" ] && [ -n "${module_files:-}" ]; then
  raw_tel07=$(mktemp); trap 'rm -f "$raw_tel07"' EXIT
  # shellcheck disable=SC2086
  python3 "$SCRIPT_DIR/lib/ast_python_checks.py" tel-07 $module_files 2>/dev/null > "$raw_tel07" || true
  while IFS= read -r finding; do
    [ -z "$finding" ] && continue
    f=$(echo "$finding" | python3 -c "import json,sys;o=json.loads(sys.stdin.read());print(o.get('file',''))")
    ln=$(echo "$finding" | python3 -c "import json,sys;o=json.loads(sys.stdin.read());print(o.get('line',0))")
    [ -z "$f" ] && continue
    if is_line_touched "$f" "$ln"; then
      echo "$finding" >> "$findings"
    fi
  done < "$raw_tel07"
  rm -f "$raw_tel07"
fi

# PY-TEL-08: new public SDK functions without a new Operation constant — Jean's suggestion
# When a PR adds new observable operations (non-private module-level fns), suggest adding
# a named Operation constant to operation.py for richer telemetry granularity.
if [ "$LANGUAGE" = "python" ] && [ -n "${module_files:-}" ]; then
  new_pub_fns=$(echo "$diff_content" |     { grep -oE '^\+[[:space:]]*(async def|def) [a-z][a-z_]+[(]' 2>/dev/null || true; } |     { grep -vE 'def _' 2>/dev/null || true; } | wc -l | tr -d ' ')
  op_changed=0
  if echo "$diff_content" | grep -q '^+++ b/src/sap_cloud_sdk/core/telemetry/operation\.py' 2>/dev/null; then
    op_changed=1
  fi
  if [ "${new_pub_fns:-0}" -gt 0 ] && [ "${op_changed:-0}" -eq 0 ]; then
    emit_finding "PY-TEL-08" "FLAG" "src/sap_cloud_sdk/core/telemetry/operation.py" 1       "${new_pub_fns} new public SDK function(s) added without a new Operation constant"       "Consider adding Operation.MODULE_FUNCNAME = 'func_name' to operation.py for each new observable operation" >> "$findings"
  fi
fi

# JV-TEL-02: For Java, grep-based check (executeWithTelemetry wrap around methods)
if [ "$LANGUAGE" = "java" ] && [ -n "$client_files" ]; then
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    full_path="$REPO_ROOT/$f"
    [ -f "$full_path" ] || continue
    # find public methods in the file
    while IFS= read -r match; do
      line_num="${match%%:*}"
      # check the following 20 lines for executeWithTelemetry
      end_line=$((line_num + 20))
      body=$(sed -n "${line_num},${end_line}p" "$full_path")
      if ! echo "$body" | grep -q "executeWithTelemetry"; then
        emit_finding_if_touched "JV-TEL-02" "BLOCK" "$f" "$line_num" \
          "Public method lacks Telemetry.executeWithTelemetry wrap" "" >> "$findings"
      fi
    done < <(grep -nE '^[[:space:]]*public [A-Za-z<>]+ [a-z][a-zA-Z0-9]+\(' "$full_path" 2>/dev/null | grep -v 'public class\|public interface\|public enum' || true)
  done <<< "$client_files"
fi

# PY-TEL-06 / JV-TEL-05: emission tests required when new decorator/wrapper added
if [ "$new_decorators" -gt 0 ]; then
  if [ "$LANGUAGE" = "python" ]; then
    # Find test files added/modified in same PR
    test_files=$(echo "$diff_content" | { grep -oE '^\+\+\+ b/tests/[a-z_]+/.*/test_.*\.py' 2>/dev/null || true; } | sed 's|^+++ b/||' | sort -u)
    has_metric_assert=false
    while IFS= read -r tf; do
      [ -z "$tf" ] && continue
      [ -f "$REPO_ROOT/$tf" ] || continue
      if grep -q 'record_request_metric\|record_error_metric' "$REPO_ROOT/$tf"; then
        has_metric_assert=true; break
      fi
    done <<< "$test_files"
    if [ "$has_metric_assert" = "false" ]; then
      emit_finding "PY-TEL-06" "BLOCK" "tests/" 1 \
        "New @record_metrics added ($new_decorators occurrences) but no test asserts record_request_metric was called" \
        "Add a test that mocks record_request_metric and asserts it was called with the expected Module/Operation" >> "$findings"
    fi
  fi
fi

status=$(status_from_findings < "$findings")
emit_report "telemetry" "$LANGUAGE" "$status" "$STARTED" < "$findings"
