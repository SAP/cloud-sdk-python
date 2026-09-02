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

# FP-J-01: if the repo itself doesn't consistently have SPDX headers, don't
# penalize new files for a missing header that no existing file has. Sample
# up to 20 existing source files of the target language. If < 20% carry an
# SPDX-License-Identifier header, we treat LIC-01/02 as SHADOW (report but
# do not block).
repo_has_spdx="unknown"
if [ "$reuse_present" != "true" ]; then
  if [ "$LANGUAGE" = "python" ]; then
    src_root="$REPO_ROOT/src"
    ext="py"
  else
    # Multi-module Maven: sources live under <module>/src/main/java, so scan
    # the whole repo for .java rather than a fixed src/main/java root.
    src_root="$REPO_ROOT"
    ext="java"
  fi
  if [ -d "$src_root" ]; then
    total=0; with_spdx=0
    # Sample up to 20 files. Read them into an array first so no pipe stays
    # open when we stop early (avoids SIGPIPE / exit 141 under pipefail).
    sample_files=$(find "$src_root" -type f -name "*.${ext}" 2>/dev/null | head -20 || true)
    while IFS= read -r f; do
      [ -z "$f" ] && continue
      total=$((total+1))
      if head -10 "$f" 2>/dev/null | grep -q "SPDX-License-Identifier"; then
        with_spdx=$((with_spdx+1))
      fi
    done <<< "$sample_files"
    if [ "$total" -gt 0 ]; then
      # Percent threshold: <20% adoption means the repo hasn't converged yet
      if [ $((with_spdx * 100 / total)) -lt 20 ]; then
        repo_has_spdx="no-consistent-adoption"
      else
        repo_has_spdx="yes"
      fi
    fi
  fi
fi

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

# FP-J-01: if the repo hasn't converged on SPDX headers, downgrade LIC-01/02
# emissions to a single summary FLAG (or skip entirely) rather than BLOCKing
# each new file for a debt the repo itself carries.
if [ "$repo_has_spdx" = "no-consistent-adoption" ]; then
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
        pass_criteria_met: ["Repo has no consistent SPDX adoption (<20% of existing files) — LIC-01/02 held until repo-wide migration"],
        pass_criteria_failed: []
      }
    }'
  exit 0
fi

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
