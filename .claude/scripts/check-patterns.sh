#!/usr/bin/env bash
# check-patterns.sh — idiomatic patterns (factory, exceptions, py.typed).
# Uses module_shape predicate to skip non-client modules.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/json-emit.sh"
source "$SCRIPT_DIR/lib/predicates.sh"
source "$SCRIPT_DIR/lib/hunk-filter.sh"
source "$SCRIPT_DIR/lib/baseline.sh"
source "$SCRIPT_DIR/lib/peer-consistency.sh"

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

  # PY-PT-01 / JV-PT-01: peer-consistency check (FP-G-01).
  # Previously: BLOCK if client module missing create_client()/ClientFactory.
  # Empirically wrong — only `destination` follows that shape. Now: FLAG only
  # when the module diverges from an element that ≥80% of peers adopt.
  # Tier: FLAG (never BLOCK).
  shape=$(module_shape "$mod_dir")
  if [ "$shape" = "client" ]; then
    for element in factory client config user-guide.md exceptions py.typed; do
      # py.typed only applies to Python
      if [ "$element" = "py.typed" ] && [ "$LANGUAGE" != "python" ]; then continue; fi
      # exceptions is checked separately below with AST for accuracy
      if [ "$element" = "exceptions" ]; then continue; fi
      if should_flag_peer_divergence "$mod_dir" "$element" "$LANGUAGE" "0.80"; then
        if [ "$LANGUAGE" = "python" ]; then
          rule_id="PY-PT-01"
          rel="src/sap_cloud_sdk/$mod/"
        else
          rule_id="JV-PT-01"
          rel="src/main/java/com/sap/cloud/sdk/$mod/"
        fi
        emit_finding "$rule_id" "FLAG" "$rel" 1 \
          "Module '$mod' diverges from peer convention: missing '$element' (≥80% of peer modules have it)" \
          "Consider adding $element for consistency with sibling modules" >> "$findings"
      fi
    done
  fi

  # PY-PT-03: py.typed marker
  if [ "$LANGUAGE" = "python" ]; then
    if [ ! -f "$mod_dir/py.typed" ] && [ ! -f "$REPO_ROOT/src/sap_cloud_sdk/py.typed" ]; then
      emit_finding "PY-PT-03" "FLAG" "src/sap_cloud_sdk/$mod/py.typed" 1 \
        "Module missing py.typed marker (PEP 561)" "" >> "$findings"
    fi
  fi

  # PY-PT-04 / JV-PT-05: module-specific exceptions
  # FP-C-02: pass if module has ANY class subclassing Exception (or *Error/*Exception),
  # regardless of whether it lives in exceptions.py or __init__.py or elsewhere.
  if [ "$LANGUAGE" = "python" ]; then
    if ! python3 "$SCRIPT_DIR/lib/ast_python_checks.py" pt-04 "$mod_dir" 2>/dev/null; then
      emit_finding "PY-PT-04" "FLAG" "src/sap_cloud_sdk/$mod/exceptions.py" 1 \
        "Module lacks Exception subclasses — define a module-specific exception hierarchy (in exceptions.py or __init__.py)" "" >> "$findings"
    fi
  else
    if [ ! -d "$mod_dir/exceptions" ]; then
      emit_finding "JV-PT-05" "FLAG" "src/main/java/com/sap/cloud/sdk/$mod/exceptions/" 1 \
        "Module lacks exceptions/ package" "" >> "$findings"
    fi
  fi

done <<< "$modules"

# PY-PT-08 via AST on changed Python files
# FP-A-01: filter by ADDED_LINES_FILE (only fire on functions declared on lines the PR touched)
# FP-E-01: consult line-level baseline for pre-existing PT-08 debt
if [ "$LANGUAGE" = "python" ]; then
  changed_py=$(echo "$diff_content" | grep -oE '^\+\+\+ b/src/sap_cloud_sdk/.*\.py' | sed 's|^+++ b/||' | grep -v '__pycache__' | sort -u)
  if [ -n "$changed_py" ]; then
    raw_pt08=$(mktemp); trap 'rm -f "$raw_pt08"' EXIT
    # shellcheck disable=SC2086
    python3 "$SCRIPT_DIR/lib/ast_python_checks.py" pt-08 $changed_py 2>/dev/null > "$raw_pt08" || true
    # Filter: keep only findings on lines touched by this PR AND not in baseline
    while IFS= read -r finding; do
      [ -z "$finding" ] && continue
      f=$(echo "$finding" | python3 -c "import json,sys;o=json.loads(sys.stdin.read());print(o.get('file',''))")
      ln=$(echo "$finding" | python3 -c "import json,sys;o=json.loads(sys.stdin.read());print(o.get('line',0))")
      [ -z "$f" ] && continue
      # Baseline check first (bypasses hunk filter — always suppressed)
      if is_in_line_baseline "PY-PT-08" "$f" "$ln"; then continue; fi
      # Hunk filter
      if is_line_touched "$f" "$ln"; then
        echo "$finding" >> "$findings"
      fi
    done < "$raw_pt08"
    rm -f "$raw_pt08"
  fi
fi

status=$(status_from_findings < "$findings")
emit_report "patterns" "$LANGUAGE" "$status" "$STARTED" < "$findings"
