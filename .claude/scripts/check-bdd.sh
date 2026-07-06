#!/usr/bin/env bash
# check-bdd.sh — feature file existence + cross-language parity via alias map.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/json-emit.sh"

LANGUAGE="${LANGUAGE:-python}"
REPO_ROOT="${REPO_ROOT:-.}"
DIFF_FILE="${DIFF_FILE:-/dev/stdin}"
SDK_SIBLING_PATH="${SDK_SIBLING_PATH:-}"
CONFIG_DIR="${CONFIG_DIR:-$REPO_ROOT/.claude/config}"

STARTED=$(now_iso)
findings=$(mktemp); trap 'rm -f "$findings"' EXIT

diff_content=$(cat "$DIFF_FILE" 2>/dev/null || echo "")

# Extract new/modified modules from diff
if [ "$LANGUAGE" = "python" ]; then
  modules=$(echo "$diff_content" | grep -oE 'src/sap_cloud_sdk/[a-z_]+/' 2>/dev/null | sed 's|src/sap_cloud_sdk/||; s|/$||' | grep -v '^core$' | sort -u || true)
else
  modules=$(echo "$diff_content" | grep -oE 'src/main/java/com/sap/cloud/sdk/[a-z_]+/' 2>/dev/null | sed 's|src/main/java/com/sap/cloud/sdk/||; s|/$||' | grep -v '^core$' | sort -u || true)
fi

# resolve alias mapping (python name → java name and vice versa)
# The YAML is a simple list of pairs:
#   aliases:
#     - python: dms
#       java: documentmanagement
# awk on `$NF` (last field) extracts the value cleanly even when the key
# column varies. We only pair a python: line with the very next java: line.
resolve_sibling_name() {
  local mod="$1" dir="$LANGUAGE"
  local aliases="$CONFIG_DIR/module-aliases.yaml"
  if [ ! -f "$aliases" ]; then echo "$mod"; return; fi
  if [ "$dir" = "python" ]; then
    awk -v mod="$mod" '
      /^[[:space:]]*-?[[:space:]]*python:[[:space:]]*/ {
        sub(/^[^:]*:[[:space:]]*/, ""); p_name=$0; next
      }
      /^[[:space:]]*java:[[:space:]]*/ {
        sub(/^[^:]*:[[:space:]]*/, ""); j_name=$0
        if (p_name == mod) { print j_name; exit }
        p_name=""
      }
    ' "$aliases"
    return
  else
    awk -v mod="$mod" '
      /^[[:space:]]*-?[[:space:]]*python:[[:space:]]*/ {
        sub(/^[^:]*:[[:space:]]*/, ""); p_name=$0; next
      }
      /^[[:space:]]*java:[[:space:]]*/ {
        sub(/^[^:]*:[[:space:]]*/, ""); j_name=$0
        if (j_name == mod) { print p_name; exit }
        p_name=""
      }
    ' "$aliases"
    return
  fi
}

while IFS= read -r mod; do
  [ -z "$mod" ] && continue

  # Path for THIS repo's feature file
  if [ "$LANGUAGE" = "python" ]; then
    feature_path="$REPO_ROOT/tests/$mod/integration/$mod.feature"
    mod_dir="$REPO_ROOT/src/sap_cloud_sdk/$mod"
  else
    feature_path="$REPO_ROOT/src/test/resources/com/sap/applicationfoundation/$mod/integration/$mod.feature"
    mod_dir="$REPO_ROOT/src/main/java/com/sap/cloud/sdk/$mod"
  fi

  # BDD-01: feature file exists (only fire if module has any source files)
  if [ ! -f "$feature_path" ] && [ -d "$mod_dir" ]; then
    # Detect if this PR creates any new file INSIDE the module.
    # `new file mode` is on its own line before the `+++ b/<path>` header,
    # so we scan block-by-block to link them.
    is_new_module=$(echo "$diff_content" | awk -v mod="$mod" -v lang="$LANGUAGE" '
      BEGIN {
        if (lang == "python") pat = "src/sap_cloud_sdk/" mod "/"
        else                  pat = "src/main/java/com/sap/cloud/sdk/" mod "/"
      }
      /^diff --git/ { is_new = 0; next }
      /^new file mode/ { is_new = 1; next }
      /^\+\+\+ b\// {
        if (is_new && index($0, pat) > 0) { print "true"; exit }
      }
    ')
    if [ "$is_new_module" = "true" ]; then
      emit_finding "BDD-01" "BLOCK" "tests/$mod/integration/$mod.feature" 1 \
        "New module '$mod' has no BDD feature file" \
        "Create $feature_path with cross-language-consistent scenarios" >> "$findings"
    fi
  fi

  # BDD-02: sibling repo parity
  sibling_name=$(resolve_sibling_name "$mod")
  [ -z "$sibling_name" ] && sibling_name="$mod"

  if [ -n "$SDK_SIBLING_PATH" ] && [ -d "$SDK_SIBLING_PATH" ]; then
    if [ "$LANGUAGE" = "python" ]; then
      # Python repo — sibling is Java
      sibling_feature="$SDK_SIBLING_PATH/src/test/resources/com/sap/applicationfoundation/$sibling_name/integration/$sibling_name.feature"
      sibling_module_dir="$SDK_SIBLING_PATH/src/main/java/com/sap/cloud/sdk/$sibling_name"
    else
      sibling_feature="$SDK_SIBLING_PATH/tests/$sibling_name/integration/$sibling_name.feature"
      sibling_module_dir="$SDK_SIBLING_PATH/src/sap_cloud_sdk/$sibling_name"
    fi
    # If the sibling module dir exists, and sibling has no feature but we do (or vice versa)
    if [ -d "$sibling_module_dir" ] && [ ! -f "$sibling_feature" ] && [ -f "$feature_path" ]; then
      emit_finding "BDD-02" "FLAG" "$feature_path" 1 \
        "Sibling SDK ($sibling_name) has module but no BDD feature — parity broken" "" >> "$findings"
    fi
    if [ -d "$sibling_module_dir" ] && [ -f "$sibling_feature" ] && [ ! -f "$feature_path" ] && [ -d "$mod_dir" ]; then
      emit_finding "BDD-02" "BLOCK" "tests/.../$mod.feature" 1 \
        "Module '$mod' exists in sibling SDK ($sibling_name) with BDD feature — this repo must have equivalent" "" >> "$findings"
    fi
  fi
done <<< "$modules"

status=$(status_from_findings < "$findings")
emit_report "bdd" "$LANGUAGE" "$status" "$STARTED" < "$findings"
