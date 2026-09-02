#!/usr/bin/env bash
# check-docs.sh — documentation completeness including BTP deps and regional availability.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/json-emit.sh"

LANGUAGE="${LANGUAGE:-python}"
REPO_ROOT="${REPO_ROOT:-.}"
DIFF_FILE="${DIFF_FILE:-/dev/stdin}"

STARTED=$(now_iso)
findings=$(mktemp); trap 'rm -f "$findings"' EXIT

diff_content=$(cat "$DIFF_FILE" 2>/dev/null || echo "")

# Detect new module directories (module has new files at top-level)
# FP-M-01: multi-module Maven nests sources under <module>/src/main/java.
# Match the module segment after .../com/sap/cloud/sdk/ at any prefix depth.
if [ "$LANGUAGE" = "python" ]; then
  new_modules=$(echo "$diff_content" | { grep -oE '^\+\+\+ b/src/sap_cloud_sdk/[a-z_]+/[^/]+\.py' 2>/dev/null || true; } | sed 's|^+++ b/src/sap_cloud_sdk/||; s|/[^/]*\.py$||' | sort -u)
else
  new_modules=$(echo "$diff_content" | { grep -oE '^\+\+\+ b/.*src/main/java/com/sap/cloud/sdk/[a-z_]+/[^/]+\.java' 2>/dev/null || true; } | sed -E 's|^.*com/sap/cloud/sdk/||; s|/[^/]*\.java$||' | sort -u)
fi

while IFS= read -r mod; do
  [ -z "$mod" ] && continue
  [ "$mod" = "core" ] && continue

  if [ "$LANGUAGE" = "python" ]; then
    user_guide="$REPO_ROOT/src/sap_cloud_sdk/$mod/user-guide.md"
    mod_dir="$REPO_ROOT/src/sap_cloud_sdk/$mod"
  else
    user_guide="$REPO_ROOT/src/main/java/com/sap/cloud/sdk/$mod/user-guide.md"
    mod_dir="$REPO_ROOT/src/main/java/com/sap/cloud/sdk/$mod"
  fi

  # DC-01: user-guide.md exists
  if [ ! -f "$user_guide" ]; then
    # Only fire if module dir exists (module is new-ish)
    if [ -d "$mod_dir" ]; then
      emit_finding "DC-01" "BLOCK" "src/.../$mod/user-guide.md" 1 \
        "Module '$mod' missing user-guide.md" \
        "Create $user_guide with sections: ## Installation, ## Quick Start, ## Configuration" >> "$findings"
    fi
    continue
  fi

  # DC-02: required sections
  # Report the repo-relative path (strip $REPO_ROOT/ prefix) so findings don't
  # leak the reviewer's local absolute path into the PR comment.
  guide_rel="${user_guide#"$REPO_ROOT"/}"
  guide_content=$(cat "$user_guide" 2>/dev/null || echo "")
  if ! echo "$guide_content" | grep -qE '^##[[:space:]]+(Installation|Import)'; then
    emit_finding "DC-02" "FLAG" "$guide_rel" 1 "user-guide.md missing ## Installation section" "" >> "$findings"
  fi
  if ! echo "$guide_content" | grep -qE '^##[[:space:]]+Quick Start'; then
    emit_finding "DC-02" "BLOCK" "$guide_rel" 1 "user-guide.md missing ## Quick Start section" "" >> "$findings"
  fi

  # DC-11..DC-14 (BTP deps + regional)
  # Detect module imports/usages. Use word boundaries and prefer explicit
  # SAP-namespaced references to avoid false positives on DocumentFragment,
  # AWSRegion, region_id inside docstrings, etc.
  if [ "$LANGUAGE" = "python" ]; then
    has_dest=$(grep -rq "from sap_cloud_sdk\.destination" "$mod_dir" 2>/dev/null && echo yes || echo no)
    # Fragment/Certificate: require the SDK-provided client class specifically,
    # or an import from the SDK's fragments/certificates subpackage.
    has_frag=$(grep -rqE "\bFragmentClient\b|from[[:space:]]+sap_cloud_sdk\.fragments" "$mod_dir" 2>/dev/null && echo yes || echo no)
    has_cert=$(grep -rqE "\bCertificateClient\b|from[[:space:]]+sap_cloud_sdk\.certificates" "$mod_dir" 2>/dev/null && echo yes || echo no)
    # Region: constant naming or SDK-provided helper only — plain 'region_id'
    # in docstrings should not fire.
    has_region=$(grep -rqE "\bSUPPORTED_REGIONS\b|\bSupportedRegion\b|\bavailable_regions\b|from[[:space:]]+sap_cloud_sdk\.regions" "$mod_dir" 2>/dev/null && echo yes || echo no)
  else
    has_dest=$(grep -rq "com\.sap\.cloud\.sdk\.destination" "$mod_dir" 2>/dev/null && echo yes || echo no)
    has_frag=$(grep -rqE "\bFragmentClient\b|com\.sap\.cloud\.sdk\.fragments" "$mod_dir" 2>/dev/null && echo yes || echo no)
    has_cert=$(grep -rqE "\bCertificateClient\b|com\.sap\.cloud\.sdk\.certificates" "$mod_dir" 2>/dev/null && echo yes || echo no)
    # Java word-boundary: require SAP SDK Region type; avoid AWSRegion etc.
    has_region=$(grep -rqE "\bSupportedRegion\b|com\.sap\.cloud\.sdk\.regions|\bREGIONAL_AVAILABILITY\b" "$mod_dir" 2>/dev/null && echo yes || echo no)
  fi

  # DC-11: destination dep must be documented
  if [ "$has_dest" = "yes" ]; then
    if ! echo "$guide_content" | grep -qEi 'destination service|## Dependencies|## Prerequisites'; then
      emit_finding "DC-11" "BLOCK" "$guide_rel" 1 \
        "Module imports destination service — must document in ## Dependencies section" \
        "Add: ## Dependencies\\n- SAP BTP Destination Service instance" >> "$findings"
    fi
  fi
  # DC-12: fragments
  if [ "$has_frag" = "yes" ]; then
    if ! echo "$guide_content" | grep -qEi 'fragments'; then
      emit_finding "DC-12" "BLOCK" "$guide_rel" 1 \
        "Module uses Fragments — must document Fragments prerequisite" "" >> "$findings"
    fi
  fi
  # DC-13: certificates
  if [ "$has_cert" = "yes" ]; then
    if ! echo "$guide_content" | grep -qEi 'certificate'; then
      emit_finding "DC-13" "BLOCK" "$guide_rel" 1 \
        "Module uses Certificates — must document Certificate prerequisite" "" >> "$findings"
    fi
  fi
  # DC-14: regional
  if [ "$has_region" = "yes" ]; then
    if ! echo "$guide_content" | grep -qEi 'Regional Availability|## Limitations|available in|supported region'; then
      emit_finding "DC-14" "BLOCK" "$guide_rel" 1 \
        "Module has region-specific constants — must document ## Regional Availability" "" >> "$findings"
    fi
  fi

done <<< "$new_modules"

status=$(status_from_findings < "$findings")
emit_report "docs" "$LANGUAGE" "$status" "$STARTED" < "$findings"
