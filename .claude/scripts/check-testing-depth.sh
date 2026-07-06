#!/usr/bin/env bash
# check-testing-depth.sh — test names, tests-added checkbox truthfulness, integration test present.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/json-emit.sh"

LANGUAGE="${LANGUAGE:-python}"
DIFF_FILE="${DIFF_FILE:-/dev/stdin}"
PR_BODY_FILE="${PR_BODY_FILE:-}"

STARTED=$(now_iso)
findings=$(mktemp); trap 'rm -f "$findings"' EXIT

diff_content=$(cat "$DIFF_FILE" 2>/dev/null || echo "")

# TD-01: If PR title is fix: AND src/ changed AND no test file changed → FLAG
if [ "$LANGUAGE" = "python" ]; then
  fix_commit=$(git log HEAD --format=%s -n 1 2>/dev/null | grep -qE '^fix' && echo yes || echo no)
  src_changed=$(echo "$diff_content" | grep -qE 'src/sap_cloud_sdk/' && echo yes || echo no)
  test_changed=$(echo "$diff_content" | grep -qE 'tests?/.*/test_' && echo yes || echo no)
  if [ "$fix_commit" = "yes" ] && [ "$src_changed" = "yes" ] && [ "$test_changed" = "no" ]; then
    emit_finding "TD-01" "FLAG" "tests/" 1 \
      "Bug-fix PR touches src/ but no test files changed" \
      "Add a focused unit test that reproduces the bug and asserts the fix" >> "$findings"
  fi

  # TD-10: New module → integration test required
  new_modules=$(echo "$diff_content" | awk '/^diff --git/ { flag=0 } /^new file mode/ { flag=1 } flag && /^\+\+\+ b\/src\/sap_cloud_sdk\/[a-z_]+\/[^/]+\.py/ { print }' | grep -oE 'src/sap_cloud_sdk/[a-z_]+/' | sed 's|src/sap_cloud_sdk/||; s|/$||' | sort -u)
  while IFS= read -r mod; do
    # Both conditions should skip the loop iteration. The previous
    # A || B && continue form parses as (A || B) && continue, which is
    # correct — but the `&& continue` under `set -e` short-circuits the
    # loop body's exit status and hides errors. Explicit if is safer.
    if [ -z "$mod" ] || [ "$mod" = "core" ]; then
      continue
    fi
    has_integration=$(echo "$diff_content" | grep -qE "tests/$mod/integration/" && echo yes || echo no)
    if [ "$has_integration" = "no" ]; then
      emit_finding "TD-10" "BLOCK" "tests/$mod/integration/" 1 \
        "New module '$mod' has no integration test" "" >> "$findings"
    fi
  done <<< "$new_modules"
fi

# TD-checkbox: PR body says "tests added" but no test files touched
if [ -n "$PR_BODY_FILE" ] && [ -f "$PR_BODY_FILE" ]; then
  body=$(cat "$PR_BODY_FILE")
  if echo "$body" | grep -qE '\-[[:space:]]*\[[xX]\][[:space:]].*(added|updated).*tests'; then
    if ! echo "$diff_content" | grep -qE 'diff --git a/(tests?/|src/test/)'; then
      emit_finding "TD-checkbox" "FLAG" "PR_BODY" 1 \
        "PR body ticks 'added tests' checkbox but no test files changed" "" >> "$findings"
    fi
  fi
fi

status=$(status_from_findings < "$findings")
emit_report "testing-depth" "$LANGUAGE" "$status" "$STARTED" < "$findings"
