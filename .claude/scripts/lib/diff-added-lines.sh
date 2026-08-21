#!/usr/bin/env bash
# lib/diff-added-lines.sh — Emit file:line pairs that are in the added set (+) of a diff.
# Reads unified diff from stdin, outputs "path:linenumber" one per line (right-side lines only).
# Automatically excludes the skill's own files (self-review protection).
set -euo pipefail

awk '
  BEGIN { file=""; line=0; skip=0 }
  # Parse the "+++ b/<path>" header — this is authoritative and handles filenames
  # with spaces, unlike splitting the "diff --git a/... b/..." line on whitespace.
  /^\+\+\+ b\// {
    # Everything after "+++ b/" is the path (may contain spaces)
    file = substr($0, 7)
    line = 0
    # Self-review protection: skip skill files
    skip = 0
    if (file ~ /^\.claude\//) skip = 1
    if (file ~ /^tests\/sdk-review\//) skip = 1
    if (file ~ /^\.github\/workflows\/sdk-/) skip = 1
    if (file ~ /^docs\/PR-REVIEW\.md$/) skip = 1
    if (file ~ /^docs\/BRANCH-PROTECTION-SETUP\.md$/) skip = 1
    next
  }
  /^\+\+\+ \/dev\/null/ { file = ""; next }   # File being deleted
  /^--- / { next }
  /^diff --git/ { next }   # Ignored; +++ b/... below carries the real path
  /^@@/ {
    # hunk header: @@ -old,+new,newcount @@
    if (match($0, /\+[0-9]+/)) {
      line = substr($0, RSTART+1, RLENGTH-1) + 0
    }
    next
  }
  /^\+/ && !/^\+\+\+/ {
    if (!skip && file != "" && line > 0) print file ":" line
    line++
    next
  }
  /^-/ && !/^---/ {
    # deletion line — do not increment right-side counter
    next
  }
  /^ / {
    # context line — increment right-side counter but do not print
    line++
    next
  }
' "$@"
