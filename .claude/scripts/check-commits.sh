#!/usr/bin/env bash
# check-commits.sh — Conventional Commits enforcement.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/json-emit.sh"

LANGUAGE="${LANGUAGE:-python}"
# Resolve BASE_SHA from GITHUB_BASE_REF merge-base when not explicitly set —
# HEAD~10 is a poor fallback (only reachable when the PR has ≥10 commits).
if [ -z "${BASE_SHA:-}" ]; then
  base_ref="${GITHUB_BASE_REF:-main}"
  # Try origin/<ref>, then <ref>, then finally HEAD~10 as last resort
  if git rev-parse --verify "origin/${base_ref}" >/dev/null 2>&1; then
    BASE_SHA=$(git merge-base HEAD "origin/${base_ref}" 2>/dev/null || echo "HEAD~10")
  elif git rev-parse --verify "$base_ref" >/dev/null 2>&1; then
    BASE_SHA=$(git merge-base HEAD "$base_ref" 2>/dev/null || echo "HEAD~10")
  else
    BASE_SHA="HEAD~10"
  fi
fi
HEAD_SHA="${HEAD_SHA:-HEAD}"

STARTED=$(now_iso)
findings=$(mktemp); trap 'rm -f "$findings"' EXIT

# List commit subjects
commits=$(git log "${BASE_SHA}..${HEAD_SHA}" --format='%H %s' 2>/dev/null || echo "")
prefix_regex='^(feat|fix|refactor|chore|docs|test|ci|build|perf|style|revert)(\([a-z0-9_/-]+\))?!?:[[:space:]]+.+'

echo "$commits" | while IFS= read -r line; do
  [ -z "$line" ] && continue
  sha=$(echo "$line" | cut -d' ' -f1)
  subject=$(echo "$line" | cut -d' ' -f2-)
  # Skip merge commits (identified by 2+ parents, robust regardless of message shape)
  parents=$(git rev-list --parents -n 1 "$sha" 2>/dev/null | awk '{print NF-1}')
  if [ "${parents:-0}" -gt 1 ]; then continue; fi
  # Also skip legacy "Merge branch/pull/etc" defaults
  if echo "$subject" | grep -qiE '^Merge '; then continue; fi
  if ! echo "$subject" | grep -qE "$prefix_regex"; then
    emit_finding "COM-01" "FLAG" "COMMIT:$sha" 1 \
      "Commit '$subject' does not follow Conventional Commits" \
      "Prefix with feat:/fix:/chore:/docs:/test:/refactor:/ci:/build:/perf:/style:/revert:" >> "$findings"
  fi
done

status=$(status_from_findings < "$findings")
emit_report "commits" "$LANGUAGE" "$status" "$STARTED" < "$findings"
