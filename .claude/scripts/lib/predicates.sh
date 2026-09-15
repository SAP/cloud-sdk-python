#!/usr/bin/env bash
# lib/predicates.sh — Evaluate scope predicates for rules.
# Called by orchestrate.sh before each check runs.
# Outputs comma-separated rule IDs to SKIP because predicates are false.
set -euo pipefail

# has_commit_type <base_sha> <head_sha> <type1,type2,...> → prints "true" or "false"
has_commit_type() {
  local base="$1" head="$2" types="$3"
  local pattern
  pattern=$(echo "$types" | tr ',' '|')
  if git log "${base}..${head}" --format=%s 2>/dev/null | grep -qE "^(${pattern})(\(.*\))?!?: "; then
    echo "true"
  else
    echo "false"
  fi
}

# module_shape <module_dir> → prints "client" | "patch" | "config" | "other"
module_shape() {
  local dir="$1"
  if [ -f "$dir/client.py" ] || [ -f "$dir/_http.py" ] || compgen -G "$dir/*Client.java" > /dev/null 2>&1; then
    echo "client"
  elif [ -f "$dir/_patch.py" ] || compgen -G "$dir/patch*.py" > /dev/null 2>&1; then
    echo "patch"
  elif [ -f "$dir/config.py" ] && [ ! -f "$dir/client.py" ]; then
    echo "config"
  else
    echo "other"
  fi
}

# reuse_toml_aggregate_present <repo_root> → prints "true" or "false"
# BSD-safe: uses [[:space:]] instead of \s.
reuse_toml_aggregate_present() {
  local root="${1:-.}"
  local reuse="$root/REUSE.toml"
  if [ ! -f "$reuse" ]; then echo "false"; return; fi
  if grep -qE 'path[[:space:]]*=[[:space:]]*"\*\*?"' "$reuse" 2>/dev/null; then
    echo "true"
  else
    echo "false"
  fi
}

# file_in_added_set <file> <added_lines_file> → prints "true" or "false"
# Uses grep -F for fixed-string matching (safe with paths containing regex metachars).
file_in_added_set() {
  local file="$1" added_lines_file="$2"
  [ -f "$added_lines_file" ] || { echo "false"; return; }
  if grep -Fq "${file}:" "$added_lines_file"; then
    echo "true"
  else
    echo "false"
  fi
}

# line_in_added_set <file> <line> <added_lines_file> → prints "true" or "false"
line_in_added_set() {
  local file="$1" line="$2" added_lines_file="$3"
  [ -f "$added_lines_file" ] || { echo "false"; return; }
  # Use grep -Fx (fixed, whole-line) to avoid regex metachars in path
  if grep -Fxq "${file}:${line}" "$added_lines_file"; then
    echo "true"
  else
    echo "false"
  fi
}

# filter_findings_by_hunk <report_file> <added_lines_file> → prints filtered report
# Fix: build the added-lines set as a proper JSON array (not slurped strings).
filter_findings_by_hunk() {
  local report="$1" added="$2"
  local added_json
  if [ ! -f "$added" ] || [ ! -s "$added" ]; then
    added_json="[]"
  else
    added_json=$(sort -u "$added" | jq -R . | jq -s '.')
  fi
  jq --argjson added "$added_json" '
    .findings |= map(
      select($added | index(.file + ":" + (.line|tostring)) != null)
    )
  ' "$report"
}

# When executed directly, dispatch to subcommand
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  cmd="${1:-}"; shift || true
  case "$cmd" in
    has_commit_type)          has_commit_type "$@" ;;
    module_shape)             module_shape "$@" ;;
    reuse_toml_aggregate_present) reuse_toml_aggregate_present "$@" ;;
    file_in_added_set)        file_in_added_set "$@" ;;
    line_in_added_set)        line_in_added_set "$@" ;;
    filter_findings_by_hunk)  filter_findings_by_hunk "$@" ;;
    *) echo "Usage: predicates.sh <command> [args]" >&2; exit 2 ;;
  esac
fi
