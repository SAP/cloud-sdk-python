#!/usr/bin/env bash
# check-commits.sh — Conventional Commits enforcement.
#
# The repos squash-merge PRs, so ONLY the final squashed subject (which
# defaults to the PR title) becomes a commit on main. Checking every
# intermediate commit floods the review with findings for messages that
# will be discarded. We therefore check a single subject:
#   1. PR_TITLE  (env, set by orchestrate from the PR metadata) if available
#   2. else the most recent non-merge commit subject (HEAD)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/json-emit.sh"

LANGUAGE="${LANGUAGE:-python}"
HEAD_SHA="${HEAD_SHA:-HEAD}"
PR_TITLE="${PR_TITLE:-}"

STARTED=$(now_iso)
findings=$(mktemp); trap 'rm -f "$findings"' EXIT

prefix_regex='^(feat|fix|refactor|chore|docs|test|ci|build|perf|style|revert)(\([a-z0-9_/,.-]+\))?!?:[[:space:]]+.+'

# Pick the single subject that will land on main after squash-merge.
if [ -n "$PR_TITLE" ]; then
  subject="$PR_TITLE"
  location="PR_TITLE"
else
  # Most recent non-merge commit subject.
  subject=$({ git log "$HEAD_SHA" --no-merges -1 --format='%s' 2>/dev/null || true; })
  location="COMMIT:$({ git rev-parse "$HEAD_SHA" 2>/dev/null || echo HEAD; })"
fi

if [ -n "$subject" ] && ! echo "$subject" | grep -qiE '^Merge '; then
  if ! echo "$subject" | grep -qE "$prefix_regex"; then
    emit_finding "COM-01" "FLAG" "$location" 1 \
      "Squash-merge subject '$subject' does not follow Conventional Commits" \
      "The PR title becomes the squashed commit — prefix with feat:/fix:/chore:/docs:/test:/refactor:/ci:/build:/perf:/style:/revert:" >> "$findings"
  fi
fi

status=$(status_from_findings < "$findings")
emit_report "commits" "$LANGUAGE" "$status" "$STARTED" < "$findings"
