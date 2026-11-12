#!/usr/bin/env bash
# lib/skill-self-skip.sh — return "true" if a file is part of the SDK review skill itself
# (used to prevent meta-review-loop where the skill's own files trigger findings).
set -euo pipefail

is_skill_file() {
  local file="$1"
  case "$file" in
    .claude/*)                             echo "true"; return ;;
    tests/sdk-review/*)                    echo "true"; return ;;  # legacy path pre-bug-8
    .github/workflows/sdk-*)               echo "true"; return ;;
    docs/PR-REVIEW.md|docs/BRANCH-PROTECTION-SETUP.md) echo "true"; return ;;
    *)                                     echo "false" ;;
  esac
}

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  is_skill_file "$@"
fi
