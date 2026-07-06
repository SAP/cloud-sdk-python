#!/usr/bin/env bash
# check-deletion-hygiene.sh — placeholder: stub check emitting empty findings.
# TODO: implement rules from 01-PYTHON.md / 02-JAVA.md §3.deletion-hygiene
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/json-emit.sh"

LANGUAGE="${LANGUAGE:-python}"
DIFF_FILE="${DIFF_FILE:-/dev/stdin}"
REPO_ROOT="${REPO_ROOT:-.}"

STARTED=$(now_iso)
findings=$(mktemp); trap 'rm -f "$findings"' EXIT
diff_content=$(cat "$DIFF_FILE" 2>/dev/null || echo "")

# DEL-01: symbol removed from __all__ but references remain in codebase
if [ "$LANGUAGE" = "python" ]; then
  # Extract removed __all__ entries
  removed_symbols=$(echo "$diff_content" | awk '
    /\+\+\+ b\/.*__init__\.py$/ { in_init=1; next }
    /^diff --git/ { in_init=0 }
    in_init && /^-[[:space:]]*"[A-Za-z_][A-Za-z0-9_]*"/ {
      match($0, /"[^"]+"/); print substr($0, RSTART+1, RLENGTH-2)
    }
  ')
  while IFS= read -r sym; do
    [ -z "$sym" ] && continue
    # search codebase (excluding the file where it was removed)
    hits=$(grep -rEIln "\b${sym}\b" "$REPO_ROOT/src" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$hits" -gt 0 ]; then
      emit_finding "DEL-01" "BLOCK" "src/" 1 \
        "Symbol '$sym' removed from __all__ but still referenced in $hits files" "" >> "$findings"
    fi
  done <<< "$removed_symbols"
fi

status=$(status_from_findings < "$findings")
emit_report "deletion-hygiene" "$LANGUAGE" "$status" "$STARTED" < "$findings"
