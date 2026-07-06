#!/usr/bin/env bash
# check-versioning.sh — SemVer bump + BREAKING family (BREAKING-01..04).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/json-emit.sh"
source "$SCRIPT_DIR/lib/predicates.sh"

LANGUAGE="${LANGUAGE:-python}"
REPO_ROOT="${REPO_ROOT:-.}"
DIFF_FILE="${DIFF_FILE:-/dev/stdin}"
PR_BODY_FILE="${PR_BODY_FILE:-}"
# Resolve BASE_SHA from the PR base ref rather than HEAD~10 (which fails on
# short branches). Only fall back to HEAD~10 when we can't reach a base ref.
if [ -z "${BASE_SHA:-}" ]; then
  base_ref="${GITHUB_BASE_REF:-main}"
  if git rev-parse --verify "origin/${base_ref}" >/dev/null 2>&1; then
    BASE_SHA=$(git merge-base HEAD "origin/${base_ref}" 2>/dev/null || echo "HEAD~10")
  elif git rev-parse --verify "$base_ref" >/dev/null 2>&1; then
    BASE_SHA=$(git merge-base HEAD "$base_ref" 2>/dev/null || echo "HEAD~10")
  else
    BASE_SHA="HEAD~10"
  fi
fi
HEAD_SHA="${HEAD_SHA:-HEAD}"
BREAKING_JSON="${BREAKING_JSON:-}"    # pre-computed via breaking-detector.py

STARTED=$(now_iso)
findings=$(mktemp); trap 'rm -f "$findings"' EXIT

diff_content=$(cat "$DIFF_FILE" 2>/dev/null || echo "")

# Detect version-bump line change
if [ "$LANGUAGE" = "python" ]; then
  version_bumped=$(echo "$diff_content" | grep -E '^\+version[[:space:]]*=' | head -1)
  version_removed=$(echo "$diff_content" | grep -E '^-version[[:space:]]*=' | head -1)
else
  version_bumped=$(echo "$diff_content" | grep -E '^\+[[:space:]]*<version>' | head -1)
  version_removed=$(echo "$diff_content" | grep -E '^-[[:space:]]*<version>' | head -1)
fi

# src/ changes present?
if [ "$LANGUAGE" = "python" ]; then
  src_changed=$(echo "$diff_content" | grep -qE 'diff --git a/src/sap_cloud_sdk/' && echo yes || echo no)
else
  src_changed=$(echo "$diff_content" | grep -qE 'diff --git a/src/main/java/' && echo yes || echo no)
fi

# commit types (BASE_SHA already resolved above; do not fall back to HEAD~10)
commit_types=$(has_commit_type "$BASE_SHA" "$HEAD_SHA" "feat,feat!,fix,fix!" 2>/dev/null || echo "false")

# BREAKING detector output
breaking_detected="false"
if [ -n "$BREAKING_JSON" ] && [ -f "$BREAKING_JSON" ]; then
  breaking_detected=$(jq -r '.breaking_detected' "$BREAKING_JSON" 2>/dev/null || echo "false")
fi

is_feat=$(has_commit_type "$BASE_SHA" "$HEAD_SHA" "feat,feat!" 2>/dev/null || echo "false")

# VER-01: src/ change without bump — only fires on feat OR breaking
if [ "$src_changed" = "yes" ] && [ -z "$version_bumped" ]; then
  if [ "$is_feat" = "true" ] || [ "$breaking_detected" = "true" ]; then
    emit_finding "VER-01" "BLOCK" "pyproject.toml" 1 \
      "Feature or breaking change detected but version not bumped" \
      "Bump MINOR version for feat/API change; MAJOR for breaking" >> "$findings"
  fi
fi

# BREAKING-01: if breaking, check PR body has proper declarations
if [ "$breaking_detected" = "true" ]; then
  # collect requirements
  has_bang=$(has_commit_type "$BASE_SHA" "$HEAD_SHA" "feat!,fix!" 2>/dev/null || echo "false")
  has_bump=$([ -n "$version_bumped" ] && echo "true" || echo "false")

  pr_body=""
  if [ -n "$PR_BODY_FILE" ] && [ -f "$PR_BODY_FILE" ]; then
    pr_body=$(cat "$PR_BODY_FILE")
  fi
  has_breaking_section="false"
  if echo "$pr_body" | grep -qE '^##[[:space:]]+Breaking Changes' ; then
    # section must have non-empty content (not "N/A" or "None" alone)
    # Use awk to extract from "## Breaking Changes" to next "## " heading, drop the header line itself
    section=$(echo "$pr_body" | awk '
      /^##[[:space:]]+Breaking Changes/ { flag=1; next }
      flag && /^##[[:space:]]+[A-Z]/ { exit }
      flag { print }
    ' | tr -d '[:space:]')
    if [ -n "$section" ] && ! echo "$section" | grep -qEi '^(N/A|None|none|--)*$'; then
      has_breaking_section="true"
    fi
  fi
  # Checkbox: accept -, *, +, or bullet with either ticked casing
  has_checkbox=$(echo "$pr_body" | grep -qE '^[[:space:]]*[-*+][[:space:]]*\[[xX]\][[:space:]]+([Bb]reaking change|BREAKING|Contains breaking)' && echo "true" || echo "false")

  # if ANY of the 4 requirements is missing → BLOCK
  missing=""
  [ "$has_bang" != "true" ] && missing="$missing commit-!:-prefix"
  [ "$has_bump" != "true" ] && missing="$missing version-bump"
  [ "$has_breaking_section" != "true" ] && missing="$missing PR-body-Breaking-Changes-section"
  [ "$has_checkbox" != "true" ] && missing="$missing PR-body-checkbox"

  if [ -n "$missing" ]; then
    emit_finding "BREAKING-01" "BLOCK" "PR_METADATA" 1 \
      "Breaking change detected — missing declarations:$missing" \
      "Add all 4: (a) feat!:/fix!: commit prefix (b) ## Breaking Changes section (c) checkbox ticked (d) version bump" >> "$findings"

    # BREAKING-02: partial declaration (some declared, others not)
    declared_count=0
    [ "$has_bang" = "true" ] && declared_count=$((declared_count+1))
    [ "$has_bump" = "true" ] && declared_count=$((declared_count+1))
    [ "$has_breaking_section" = "true" ] && declared_count=$((declared_count+1))
    [ "$has_checkbox" = "true" ] && declared_count=$((declared_count+1))
    if [ "$declared_count" -gt 0 ] && [ "$declared_count" -lt 4 ]; then
      emit_finding "BREAKING-02" "BLOCK" "PR_METADATA" 1 \
        "Breaking-change metadata is inconsistent ($declared_count/4 declared)" \
        "All 4 declarations must agree — reconcile or fully retract" >> "$findings"
    fi
  fi
fi

status=$(status_from_findings < "$findings")
emit_report "versioning" "$LANGUAGE" "$status" "$STARTED" < "$findings"
