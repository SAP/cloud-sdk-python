#!/usr/bin/env bash
# lib/detect-modules.sh — extract module names from a diff.
# Usage: detect-modules.sh <language> [diff-file]
#   Reads diff from stdin if no diff-file argument.
set -euo pipefail

lang="${1:-python}"
diff_source="${2:-/dev/stdin}"

if [ "$lang" = "python" ]; then
  grep -oE '(src/sap_cloud_sdk|src/)[a-z_][a-z_0-9]*/' "$diff_source" 2>/dev/null | \
    sed -E 's|src/sap_cloud_sdk/||; s|src/||; s|/$||' | \
    grep -v '^core$' | grep -v '^[[:space:]]*$' | sort -u
elif [ "$lang" = "java" ]; then
  grep -oE 'src/main/java/com/sap/cloud/sdk/[a-z_][a-z_0-9]*/' "$diff_source" 2>/dev/null | \
    sed 's|src/main/java/com/sap/cloud/sdk/||; s|/$||' | \
    grep -v '^core$' | sort -u
else
  echo "ERROR: unknown language $lang" >&2; exit 2
fi
