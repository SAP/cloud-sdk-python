#!/usr/bin/env bash
# lib/suppression.sh — Parse # sdk-review: ignore[<check>] comments.
# Outputs "<file>:<line>:<check>" tuples of suppressions found in a diff.
set -euo pipefail

# Line-level: any occurrence of "sdk-review: ignore[X,Y]" or "sdk-review: ignore" on same line
# File-level: "sdk-review-ignore-file: X,Y" within first 20 lines of file

# parse_line_suppressions <file>
# Scans the file and emits <file>:<line>:<check> for each suppression on that line.
# Anchor to a comment context to avoid false positives in string literals or docstrings.
parse_line_suppressions() {
  local file="$1"
  [ -f "$file" ] || return 0
  awk -v file="$file" '
    # Require the marker to be preceded by a comment character (# or //) so we
    # do not match "sdk-review: ignore" inside a docstring or string literal.
    match($0, /(#|\/\/)[[:space:]]*sdk-review:[[:space:]]*ignore(\[[^]]*\])?/) {
      m = substr($0, RSTART, RLENGTH)
      # extract [checks] if present
      if (match(m, /\[[^]]*\]/)) {
        checks = substr(m, RSTART+1, RLENGTH-2)
        n = split(checks, arr, ",")
        for (j=1; j<=n; j++) {
          gsub(/^ +| +$/, "", arr[j])
          print file ":" NR ":" arr[j]
        }
      } else {
        print file ":" NR ":*"
      }
    }
  ' "$file"
}

# parse_file_suppressions <file>
# Emits <file>:*:<check> when a file-level suppression header is present in first 20 lines.
parse_file_suppressions() {
  local file="$1"
  [ -f "$file" ] || return 0
  head -20 "$file" 2>/dev/null | awk -v file="$file" '
    # Require comment prefix
    match($0, /(#|\/\/)[[:space:]]*sdk-review-ignore-file:[[:space:]]*[a-zA-Z0-9_,-]+/) {
      m = substr($0, RSTART, RLENGTH)
      sub(/^(#|\/\/)[[:space:]]*sdk-review-ignore-file:[[:space:]]*/, "", m)
      n = split(m, arr, ",")
      for (j=1; j<=n; j++) {
        gsub(/^ +| +$/, "", arr[j])
        print file ":*:" arr[j]
      }
    }
  '
}

# is_suppressed <rule> <file> <line> <suppressions_file>
# Locked rules (SEC-*, HC-03, DIS-06, LIC-01/02, BND-02, BND-05, BREAKING-*) NEVER suppressed.
# Uses fixed-string matching so paths with regex metachars (dots, brackets) work.
is_suppressed() {
  local rule="$1" file="$2" line="$3" supp_file="$4"

  case "$rule" in
    SEC-*|HC-03|DIS-06|LIC-01|LIC-02|BND-02|BND-05|BREAKING-*)
      echo "false"; return
      ;;
  esac

  [ -f "$supp_file" ] || { echo "false"; return; }

  # Use grep -Fx (fixed-string, whole-line) to safely handle regex metachars in path.
  if grep -Fxq "${file}:${line}:${rule}" "$supp_file"; then echo "true"; return; fi
  if grep -Fxq "${file}:${line}:*" "$supp_file"; then echo "true"; return; fi
  if grep -Fxq "${file}:*:${rule}" "$supp_file"; then echo "true"; return; fi

  echo "false"
}

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  cmd="${1:-}"; shift || true
  case "$cmd" in
    parse_line)  parse_line_suppressions "$@" ;;
    parse_file)  parse_file_suppressions "$@" ;;
    is_suppressed) is_suppressed "$@" ;;
    *) echo "Usage: suppression.sh {parse_line|parse_file|is_suppressed} args" >&2; exit 2 ;;
  esac
fi
