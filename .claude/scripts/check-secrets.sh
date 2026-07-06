#!/usr/bin/env bash
# check-secrets.sh — detect secrets (AWS keys, JWTs, GitHub tokens, private keys, etc.) in added lines.
# All SEC-* rules are BLOCK_LOCKED (cannot be suppressed).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/json-emit.sh
source "$SCRIPT_DIR/lib/json-emit.sh"
# shellcheck source=lib/skill-self-skip.sh
source "$SCRIPT_DIR/lib/skill-self-skip.sh"

LANGUAGE="${LANGUAGE:-python}"
DIFF_FILE="${DIFF_FILE:-/dev/stdin}"

STARTED=$(now_iso)

# Read diff (either from env-provided file or stdin) — extract added lines with file+line info
diff_content=$(cat "$DIFF_FILE" 2>/dev/null || echo "")

if [ -z "$diff_content" ]; then
  emit_report "secrets" "$LANGUAGE" "PASS" "$STARTED" <<< ""
  exit 0
fi

findings=$(mktemp)
trap 'rm -f "$findings"' EXIT

# Parse diff and scan each added line
echo "$diff_content" | awk '
  BEGIN { file=""; line=0 }
  /^diff --git a\// {
    file=$4
    sub(/^b\//, "", file)
    line=0
    next
  }
  /^@@/ {
    if (match($0, /\+[0-9]+/)) line=substr($0, RSTART+1, RLENGTH-1)+0
    next
  }
  /^\+/ && !/^\+\+\+/ {
    print file "\t" line "\t" substr($0, 2)
    line++
    next
  }
  /^ / { line++; next }
' | while IFS=$'\t' read -r file line_num content; do
  [ -z "$file" ] && continue
  # Self-review protection: skip skill files
  if [ "$(is_skill_file "$file")" = "true" ]; then continue; fi

  # SEC-01: AWS Access Key
  if echo "$content" | grep -qE 'AKIA[0-9A-Z]{16}'; then
    emit_finding "SEC-01" "BLOCK" "$file" "$line_num" "AWS Access Key detected — remove immediately and rotate the key" "" >> "$findings"
  fi
  # SEC-02: Google API Key
  if echo "$content" | grep -qE 'AIza[0-9A-Za-z_-]{35}'; then
    emit_finding "SEC-02" "BLOCK" "$file" "$line_num" "Google API Key detected — remove and rotate" "" >> "$findings"
  fi
  # SEC-03: GitHub PAT
  if echo "$content" | grep -qE 'gh[pousr]_[A-Za-z0-9_]{36,}'; then
    emit_finding "SEC-03" "BLOCK" "$file" "$line_num" "GitHub PAT detected — remove and rotate" "" >> "$findings"
  fi
  # SEC-04: OpenAI key
  if echo "$content" | grep -qE 'sk-[A-Za-z0-9]{20,}'; then
    emit_finding "SEC-04" "BLOCK" "$file" "$line_num" "OpenAI-like API key detected — remove and rotate" "" >> "$findings"
  fi
  # SEC-05: Slack bot token
  if echo "$content" | grep -qE 'xox[baprs]-[A-Za-z0-9-]+'; then
    emit_finding "SEC-05" "BLOCK" "$file" "$line_num" "Slack token detected — remove and rotate" "" >> "$findings"
  fi
  # SEC-06: JWT
  if echo "$content" | grep -qE 'eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'; then
    emit_finding "SEC-06" "BLOCK" "$file" "$line_num" "JWT token detected — remove and rotate" "" >> "$findings"
  fi
  # SEC-07: Private key header
  if echo "$content" | grep -qE 'BEGIN (RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY'; then
    emit_finding "SEC-07" "BLOCK" "$file" "$line_num" "Private key header detected — remove and rotate" "" >> "$findings"
  fi
  # SEC-08: BTP client_secret literal (heuristic: assignment with looks-like-secret value)
  # Match client_secret= or clientsecret= with quoted values that look like real secrets
  if echo "$content" | grep -qE '"clientsecret"\s*:\s*"[A-Za-z0-9+/=]{20,}"'; then
    emit_finding "SEC-08" "BLOCK" "$file" "$line_num" "BTP client_secret literal detected — use secret resolver" "" >> "$findings"
  fi
done

# SEC-10: .env files in diff (not .env.example, .env.test, .env.sample)
env_lines=$(echo "$diff_content" | grep -E '^\+\+\+ b/\.env(\..+)?$' || true)
while IFS= read -r line; do
  [ -z "$line" ] && continue
  # extract path from "+++ b/<path>"
  path="${line#+++ b/}"
  # skip allowed suffixes
  case "$path" in
    .env.example|.env.test|.env.sample|.env.template) continue ;;
    .env|.env.*) emit_finding "SEC-10" "BLOCK" "$path" 1 ".env file committed — never commit .env; use .env.example" "" >> "$findings" ;;
  esac
done <<< "$env_lines"

status=$(status_from_findings < "$findings")
emit_report "secrets" "$LANGUAGE" "$status" "$STARTED" < "$findings"
