#!/usr/bin/env bash
# check-patterns.sh — idiomatic patterns (factory, exceptions, py.typed).
# Uses module_shape predicate to skip non-client modules.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/json-emit.sh"
source "$SCRIPT_DIR/lib/predicates.sh"

LANGUAGE="${LANGUAGE:-python}"
REPO_ROOT="${REPO_ROOT:-.}"
DIFF_FILE="${DIFF_FILE:-/dev/stdin}"

STARTED=$(now_iso)
findings=$(mktemp); trap 'rm -f "$findings"' EXIT

diff_content=$(cat "$DIFF_FILE" 2>/dev/null || echo "")

# Detect module dirs touched
if [ "$LANGUAGE" = "python" ]; then
  modules=$(echo "$diff_content" | grep -oE 'src/sap_cloud_sdk/[a-z_]+/' | sed 's|src/sap_cloud_sdk/||; s|/$||' | grep -v '^core$' | sort -u)
else
  modules=$(echo "$diff_content" | grep -oE 'src/main/java/com/sap/cloud/sdk/[a-z_]+/' | sed 's|src/main/java/com/sap/cloud/sdk/||; s|/$||' | grep -v '^core$' | sort -u)
fi

while IFS= read -r mod; do
  [ -z "$mod" ] && continue

  if [ "$LANGUAGE" = "python" ]; then
    mod_dir="$REPO_ROOT/src/sap_cloud_sdk/$mod"
  else
    mod_dir="$REPO_ROOT/src/main/java/com/sap/cloud/sdk/$mod"
  fi

  [ -d "$mod_dir" ] || continue

  # PY-PT-01 / JV-PT-01: factory exists — only fire on client modules
  shape=$(module_shape "$mod_dir")
  if [ "$shape" = "client" ]; then
    if [ "$LANGUAGE" = "python" ]; then
      if ! grep -rqE '^def create_[a-z_]*client\(' "$mod_dir" 2>/dev/null; then
        emit_finding "PY-PT-01" "BLOCK" "src/sap_cloud_sdk/$mod/" 1 \
          "Client module '$mod' missing create_client() factory function" "" >> "$findings"
      fi
    else
      if ! grep -rqE 'class [A-Z][A-Za-z]*ClientFactory' "$mod_dir" 2>/dev/null; then
        emit_finding "JV-PT-01" "BLOCK" "src/main/java/com/sap/cloud/sdk/$mod/" 1 \
          "Client module '$mod' missing ClientFactory class" "" >> "$findings"
      fi
    fi
  fi

  # PY-PT-03: py.typed marker
  if [ "$LANGUAGE" = "python" ]; then
    if [ ! -f "$mod_dir/py.typed" ] && [ ! -f "$REPO_ROOT/src/sap_cloud_sdk/py.typed" ]; then
      emit_finding "PY-PT-03" "FLAG" "src/sap_cloud_sdk/$mod/py.typed" 1 \
        "Module missing py.typed marker (PEP 561)" "" >> "$findings"
    fi
  fi

  # PY-PT-04 / JV-PT-05: module-specific exceptions
  if [ "$LANGUAGE" = "python" ]; then
    if [ ! -f "$mod_dir/exceptions.py" ]; then
      emit_finding "PY-PT-04" "FLAG" "src/sap_cloud_sdk/$mod/exceptions.py" 1 \
        "Module lacks exceptions.py — module-specific exception hierarchy recommended" "" >> "$findings"
    fi
  else
    if [ ! -d "$mod_dir/exceptions" ]; then
      emit_finding "JV-PT-05" "FLAG" "src/main/java/com/sap/cloud/sdk/$mod/exceptions/" 1 \
        "Module lacks exceptions/ package" "" >> "$findings"
    fi
  fi

done <<< "$modules"

# PY-PT-08 via AST on changed Python files
if [ "$LANGUAGE" = "python" ]; then
  changed_py=$(echo "$diff_content" | grep -oE '^\+\+\+ b/src/sap_cloud_sdk/.*\.py' | sed 's|^+++ b/||' | grep -v '__pycache__' | sort -u)
  if [ -n "$changed_py" ]; then
    # shellcheck disable=SC2086
    python3 "$SCRIPT_DIR/lib/ast_python_checks.py" pt-08 $changed_py 2>/dev/null >> "$findings" || true
  fi
fi

status=$(status_from_findings < "$findings")
emit_report "patterns" "$LANGUAGE" "$status" "$STARTED" < "$findings"
