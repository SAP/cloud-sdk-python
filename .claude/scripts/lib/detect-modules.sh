#!/usr/bin/env bash
# lib/detect-modules.sh — extract module names from a diff.
set -euo pipefail

# Usage: detect-modules.sh <language> < diff.patch
lang="${1:-python}"
if [ "$lang" = "python" ]; then
  grep -oE '(src/sap_cloud_sdk|src/)[a-z_][a-z_0-9]*/' 2>/dev/null | \
    sed -E 's|src/sap_cloud_sdk/||; s|src/||; s|/$||' | \
    grep -v '^core$' | grep -v '^\s*$' | sort -u
elif [ "$lang" = "java" ]; then
  grep -oE 'src/main/java/com/sap/cloud/sdk/[a-z_][a-z_0-9]*/' 2>/dev/null | \
    sed 's|src/main/java/com/sap/cloud/sdk/||; s|/$||' | \
    grep -v '^core$' | sort -u
else
  echo "ERROR: unknown language $lang" >&2; exit 2
fi
