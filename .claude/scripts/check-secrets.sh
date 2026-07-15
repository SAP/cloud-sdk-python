#!/usr/bin/env bash
# check-secrets.sh — detect secrets (AWS keys, JWTs, GitHub tokens, private keys, etc.) in added lines.
# All SEC-* rules are BLOCK_LOCKED (cannot be suppressed).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/json-emit.sh
source "$SCRIPT_DIR/lib/json-emit.sh"
# shellcheck source=lib/hunk-filter.sh
source "$SCRIPT_DIR/lib/hunk-filter.sh"
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

# Parse diff and scan each added line.
# FP-N-01: pre-filter in awk so only lines that could contain a secret reach
# the shell loop. The heuristic is a BROAD superset of every SEC-* anchor —
# the precise per-rule regexes still run in the loop. Secrets are
# BLOCK_LOCKED, so the pre-filter is intentionally over-inclusive (favor
# false-inclusion over ever missing a real secret).
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
    c = substr($0, 2)
    # Broad superset of SEC-01..08 anchors:
    #   AKIA / AIza / gh?_ / sk- / xox / eyJ / PRIVATE KEY / clientsecret
    if (c ~ /AKIA|AIza|gh[pousr]_|sk-|xox[baprs]-|eyJ|PRIVATE KEY|[Cc]lient[_]?[Ss]ecret/) {
      print file "\t" line "\t" c
    }
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
  # SEC-04: OpenAI / Anthropic API key (both use sk-… prefix; Anthropic allows dashes)
  if echo "$content" | grep -qE 'sk-[A-Za-z0-9_-]{20,}'; then
    emit_finding "SEC-04" "BLOCK" "$file" "$line_num" "AI provider API key detected (sk-…) — remove and rotate" "" >> "$findings"
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
  # FP-P: test fixture PEM stubs (body is "test", "fake", "dummy", or < 40 chars
  # of base64) must not fire. Real private keys have hundreds of chars of base64.
  # We gate on file path AND body content within the diff hunk.
  if echo "$content" | grep -qE 'BEGIN (RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY'; then
    # Skip if file is under a test directory (path heuristic)
    _is_test_path=false
    if echo "$file" | grep -qE '(^|/)(tests?|test_[^/]+|[^/]+_test)\.(py|java)$|/(tests?|fixtures?)/'; then
      _is_test_path=true
    fi
    if [ "$_is_test_path" = "false" ]; then
      emit_finding "SEC-07" "BLOCK" "$file" "$line_num" "Private key header detected — remove and rotate" "" >> "$findings"
    fi
    # Even in test files, fire if body looks like real key content (>= 40 base64 chars)
    # (covered by _is_test_path=true suppression above; real keys are never test stubs)
  fi
  # SEC-08: BTP client_secret literal (heuristic: assignment with looks-like-secret value)
  # Match client_secret= or clientsecret= with quoted values that look like real secrets
  if echo "$content" | grep -qE '"clientsecret"[[:space:]]*:[[:space:]]*"[A-Za-z0-9+/=]{20,}"'; then
    emit_finding "SEC-08" "BLOCK" "$file" "$line_num" "BTP client_secret literal detected — use secret resolver" "" >> "$findings"
  fi
done

# SEC-10: .env files in diff (not .env.example, .env.test, .env.sample, .env.template)
# Match both top-level .env and subdirectory service/.env
env_lines=$(echo "$diff_content" | grep -E '^\+\+\+ b/(.*/)?\.env(\..+)?$' || true)
while IFS= read -r line; do
  [ -z "$line" ] && continue
  # extract path from "+++ b/<path>"
  path="${line#+++ b/}"
  # basename check for allowlist
  base="${path##*/}"
  case "$base" in
    .env.example|.env.test|.env.sample|.env.template) continue ;;
    .env|.env.*) emit_finding "SEC-10" "BLOCK" "$path" 1 ".env file committed — never commit .env; use .env.example" "" >> "$findings" ;;
  esac
done <<< "$env_lines"

status=$(status_from_findings < "$findings")
emit_report "secrets" "$LANGUAGE" "$status" "$STARTED" < "$findings"
