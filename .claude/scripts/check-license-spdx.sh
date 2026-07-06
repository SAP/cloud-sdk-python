#!/usr/bin/env bash
# check-license-spdx.sh — verify new source files have SPDX headers.
# REUSE.toml aggregate → rule PASSES (baseline exemption).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/json-emit.sh
source "$SCRIPT_DIR/lib/json-emit.sh"
# shellcheck source=lib/predicates.sh
source "$SCRIPT_DIR/lib/predicates.sh"

LANGUAGE="${LANGUAGE:-python}"
REPO_ROOT="${REPO_ROOT:-.}"
DIFF_FILE="${DIFF_FILE:-/dev/stdin}"

STARTED=$(now_iso)
findings=$(mktemp)
trap 'rm -f "$findings"' EXIT

# Predicate: REUSE.toml aggregate present?
reuse_present=$(reuse_toml_aggregate_present "$REPO_ROOT")

diff_content=$(cat "$DIFF_FILE" 2>/dev/null || echo "")

if [ "$reuse_present" = "true" ]; then
  # Baseline exemption: rule OFF for this repo. Emit a valid report matching
  # the JSON contract in 00-COMMON.md §3 (aggregators expect these fields).
  jq -n --arg check "license-spdx" --arg lang "$LANGUAGE" --arg started "$STARTED" \
    '{
      check: $check,
      version: "1.0.0",
      language: $lang,
      status: "PASS",
      started_at: $started,
      duration_ms: 0,
      modules_analysed: [],
      findings: [],
      summary: {
        block_count: 0,
        flag_count: 0,
        suppressed_by_baseline: 0,
        pass_criteria_met: ["REUSE.toml aggregate present — LIC-01/02 exempted"],
        pass_criteria_failed: []
      }
    }'
  exit 0
fi

# Find newly added files (starts with "diff --git a/... b/..." followed by "new file mode")
# We match on "+++ b/<path>" lines that appear right after "new file mode"
added_files=$(echo "$diff_content" | awk '
  /^diff --git/ { in_block=1; is_new=0; path=""; next }
  in_block && /^new file mode/ { is_new=1; next }
  in_block && /^\+\+\+ b\// { if (is_new) print substr($0, 7); in_block=0 }
')

# REUSE-IgnoreStart
if [ "$LANGUAGE" = "python" ]; then
  ext_match='\.py$'
  spdx_line='# SPDX-License-Identifier: Apache-2.0'
  cprt_line='# SPDX-FileCopyrightText:'
else
  ext_match='\.java$'
  spdx_line='// SPDX-License-Identifier: Apache-2.0'
  cprt_line='// SPDX-FileCopyrightText:'
fi
# REUSE-IgnoreEnd

while IFS= read -r f; do
  [ -z "$f" ] && continue
  if ! echo "$f" | grep -qE "$ext_match"; then continue; fi
  # Read first 10 lines from the diff for that file to check headers
  header=$(echo "$diff_content" | awk -v file="$f" '
    $0 == "+++ b/" file { flag=1; count=0; next }
    flag && /^\+/ && !/^\+\+\+/ { print substr($0, 2); count++; if (count>=10) exit }
    flag && /^diff --git/ { exit }
  ')
  if ! echo "$header" | grep -qF "$spdx_line"; then
    emit_finding "LIC-01" "BLOCK" "$f" 1 "New source file missing SPDX-License-Identifier header" "" >> "$findings"
  fi
  if ! echo "$header" | grep -qF "$cprt_line"; then
    emit_finding "LIC-02" "BLOCK" "$f" 1 "New source file missing SPDX-FileCopyrightText header" "" >> "$findings"
  fi
done <<< "$added_files"

status=$(status_from_findings < "$findings")
emit_report "license-spdx" "$LANGUAGE" "$status" "$STARTED" < "$findings"
