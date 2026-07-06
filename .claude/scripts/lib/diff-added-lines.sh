#!/usr/bin/env bash
# lib/diff-added-lines.sh — Emit file:line pairs that are in the added set (+) of a diff.
# Reads unified diff from stdin, outputs "path:linenumber" one per line (right-side lines only).
# Automatically excludes the skill's own files (self-review protection).
set -euo pipefail

awk '
  BEGIN { file=""; line=0; skip=0 }
  /^diff --git a\// {
    # Field 4 is "b/<path>" — take it directly (regex was buggy with paths containing "b/")
    file = $4
    sub(/^b\//, "", file)
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
  /^\+\+\+ / { next }
  /^--- / { next }
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
