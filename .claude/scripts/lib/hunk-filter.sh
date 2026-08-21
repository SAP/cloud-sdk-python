#!/usr/bin/env bash
# lib/hunk-filter.sh — restrict findings to lines actually touched by the PR diff.
#
# The rule engine's contract (per 05-VALIDATION-V2.md §T-4) is that findings
# only fire on lines in the PR's added-lines set. Without this filter every
# check emits noise for pre-existing code. See docs/plans 09-FP-REMEDIATION
# §Pattern A for the empirical justification (84% FP rate reduced to <15%).
#
# The added-lines file is produced by orchestrate.sh from
# `lib/diff-added-lines.sh` and exported as $ADDED_LINES_FILE. Format:
#   path/to/file.py:42
#   path/to/file.py:43
#   ...
#
# is_line_touched <file> <line> -> exit 0 if touched, 1 if not
# is_range_touched <file> <start> <end> -> exit 0 if any line in range touched
#
# Both helpers return 0 (permissive) when $ADDED_LINES_FILE is unset or empty
# so the checks continue to work when invoked standalone (e.g., bats tests).

set -uo pipefail

is_line_touched() {
  local file="$1" line="$2"
  # Backward-compat: without the added-lines context, allow everything.
  [ -n "${ADDED_LINES_FILE:-}" ] || return 0
  [ -f "${ADDED_LINES_FILE:-}" ] || return 0
  [ -s "${ADDED_LINES_FILE:-}" ] || return 0
  grep -Fxq "${file}:${line}" "${ADDED_LINES_FILE}"
}

is_range_touched() {
  local file="$1" start="$2" end="$3"
  [ -n "${ADDED_LINES_FILE:-}" ] || return 0
  [ -f "${ADDED_LINES_FILE:-}" ] || return 0
  [ -s "${ADDED_LINES_FILE:-}" ] || return 0
  # Cheap path: grep any line in [start, end] for the file
  local ln
  for ln in $(seq "$start" "$end"); do
    if grep -Fxq "${file}:${ln}" "${ADDED_LINES_FILE}"; then
      return 0
    fi
  done
  return 1
}

# is_meta_finding <file> -> exit 0 if this is a PR-metadata finding (PR_BODY,
# COMMIT:*, or ".") that should bypass hunk attribution entirely.
is_meta_finding() {
  local file="$1"
  case "$file" in
    PR_BODY|.|""|COMMIT:*|PR_METADATA) return 0 ;;
    *) return 1 ;;
  esac
}

# Convenience wrapper: emit only if the finding is either metadata or touched.
# Signature matches emit_finding but adds hunk filtering.
#   emit_finding_if_touched <rule> <severity> <file> <line> <message> <suggestion>
emit_finding_if_touched() {
  local rule="$1" sev="$2" file="$3" line="$4" msg="$5" sugg="$6"
  if is_meta_finding "$file"; then
    emit_finding "$rule" "$sev" "$file" "$line" "$msg" "$sugg"
    return
  fi
  if is_line_touched "$file" "$line"; then
    emit_finding "$rule" "$sev" "$file" "$line" "$msg" "$sugg"
  fi
}

# CLI entry point (used by bats tests)
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  case "${1:-}" in
    is_line_touched)   shift; is_line_touched "$@" ;;
    is_range_touched)  shift; is_range_touched "$@" ;;
    is_meta_finding)   shift; is_meta_finding "$@" ;;
    *) echo "Usage: hunk-filter.sh {is_line_touched|is_range_touched|is_meta_finding} args" >&2; exit 2 ;;
  esac
fi
