#!/usr/bin/env bash
# check-deps-supply.sh — placeholder: stub check emitting empty findings.
# TODO: implement rules from 01-PYTHON.md / 02-JAVA.md §3.deps-supply
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/json-emit.sh"

LANGUAGE="${LANGUAGE:-python}"
DIFF_FILE="${DIFF_FILE:-/dev/stdin}"
REPO_ROOT="${REPO_ROOT:-.}"

STARTED=$(now_iso)
findings=$(mktemp); trap 'rm -f "$findings"' EXIT
diff_content=$(cat "$DIFF_FILE" 2>/dev/null || echo "")

# DEP-04: internal artifactory index URL
if echo "$diff_content" | grep -qE '\+.*(index-url|extra-index-url).*int\.repositories\.cloud\.sap'; then
  emit_finding "DEP-04" "BLOCK" "config" 1 \
    "Internal artifactory --index-url reference in public artifact" "" >> "$findings"
fi
# DEP-03: pyproject.toml deps changed but uv.lock not
if [ "$LANGUAGE" = "python" ]; then
  pyproject_deps_changed=$(echo "$diff_content" | grep -cE '^\+.*"[a-z][a-z0-9_-]*[><=~!]+' || echo 0)
  uv_lock_changed=$(echo "$diff_content" | grep -c '^\+\+\+ b/uv\.lock' || echo 0)
  if [ "$pyproject_deps_changed" -gt 0 ] && [ "$uv_lock_changed" -eq 0 ]; then
    # only fire if pyproject.toml dep table (not [project] version) changed
    if echo "$diff_content" | grep -qE '^\+.*\[project\.(dependencies|optional-dependencies)\]|^\+[[:space:]]+"[a-z][a-z0-9_-]*[><=~!].*"'; then
      emit_finding "DEP-03" "FLAG" "pyproject.toml" 1 \
        "pyproject.toml dependencies changed but uv.lock not updated" "" >> "$findings"
    fi
  fi
fi

status=$(status_from_findings < "$findings")
emit_report "deps-supply" "$LANGUAGE" "$status" "$STARTED" < "$findings"
