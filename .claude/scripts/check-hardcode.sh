#!/usr/bin/env bash
# check-hardcode.sh — no hardcoded URLs, credentials, or magic values in impl code.
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
findings=$(mktemp)
trap 'rm -f "$findings"' EXIT

diff_content=$(cat "$DIFF_FILE" 2>/dev/null || echo "")

# Determine ignore patterns per language
# FP-B-01: HC-01 must not fire on XML/YAML/POM files where URL-like strings
# are namespace declarations (http://maven.apache.org/POM/4.0.0 etc.).
# FP-H-01: lockfiles are generated + full of package URLs; never scan them.
# FP-I-01: .env.example files carry placeholder URLs (your-…-here); templates.
LOCKFILE_PATTERNS='.*\.lock$|(.*/)?uv\.lock$|(.*/)?poetry\.lock$|(.*/)?Pipfile\.lock$|(.*/)?package-lock\.json$|(.*/)?yarn\.lock$|(.*/)?Cargo\.lock$|(.*/)?Gemfile\.lock$'
# .env, .env.X, .env_X, .env-X — any file whose basename starts with .env
ENV_EXAMPLE_PATTERNS='(.*/)?\.env(\..*|_.*|-.*)?$'
if [ "$LANGUAGE" = "python" ]; then
  ignore_files="^(tests?/|.*/tests?/|mocks?/|docs?/|.*/spec/|.*/constants\.py|.*/user-guide\.md|README\.md|.*\.md$|.*\.ya?ml$|.*\.xml$|.*\.properties$|.*pom\.xml$|${LOCKFILE_PATTERNS}|${ENV_EXAMPLE_PATTERNS})"
else
  # FP-O-01: multi-module Maven puts tests at <module>/src/test/java, not
  # src/test/. Match src/test/ at any depth. Same for mocks/constants.
  ignore_files="^(src/test/|.*/src/test/|mocks?/|docs?/|.*Constants\.java|.*/constants/|.*/user-guide\.md|README\.md|.*\.md$|.*\.ya?ml$|.*\.xml$|.*\.properties$|.*pom\.xml$|${LOCKFILE_PATTERNS}|${ENV_EXAMPLE_PATTERNS})"
fi

# FP-N-01: performance. A per-line shell loop over the full added-line set
# forks 5-6 subprocesses per line; on a 13k-line diff that is ~80k forks and
# blows past the orchestrate timeout. Pre-filter in awk so ONLY lines that
# could match some HC-* rule reach the shell loop. The awk stage also does
# the file-level ignore so we never even emit lines from ignored files.
#
# Interesting-line heuristic (broad — real rule regexes still run in-loop):
#   - contains http:// or https://           (HC-01)
#   - contains "Authorization" or "Bearer"    (HC-02)
#   - contains os.environ[ or System.getenv(  (HC-04)
#   - contains timeout/retries/max_retries =  (HC-06)
echo "$diff_content" | awk -v ignore="$ignore_files" '
  BEGIN { file=""; line=0 }
  /^diff --git a\// { file=$4; sub(/^b\//, "", file); line=0; next }
  /^@@/ { if (match($0, /\+[0-9]+/)) line=substr($0, RSTART+1, RLENGTH-1)+0; next }
  /^\+/ && !/^\+\+\+/ {
    c = substr($0, 2)
    # File-level ignore (awk regex; mirrors the shell ignore_files pattern)
    if (file ~ ignore) { line++; next }
    # Interesting-line pre-filter
    if (c ~ /https?:\/\// || \
        c ~ /Authorization|Bearer/ || \
        c ~ /os\.environ\[|System\.getenv\(/ || \
        c ~ /(timeout|retries|max_retries)[ \t]*=[ \t]*[0-9]/) {
      print file "\t" line "\t" c
    }
    line++
    next
  }
  /^ / { line++; next }
' | while IFS=$'\t' read -r file line_num content; do
  [ -z "$file" ] && continue
  if [ "$(is_skill_file "$file")" = "true" ]; then continue; fi

  # FP-R-01: skip URLs that live inside a Python docstring (documentation
  # examples, not runtime code). Compute the docstring line set once per file.
  if [ "$LANGUAGE" = "python" ] && echo "$file" | grep -q '\.py$'; then
    if [ "${_docstring_file:-}" != "$file" ]; then
      _docstring_file="$file"
      _docstring_lines=""
      if [ -f "$REPO_ROOT/$file" ]; then
        _docstring_lines=$(python3 "$SCRIPT_DIR/lib/ast_python_checks.py" docstring-lines "$REPO_ROOT/$file" 2>/dev/null || echo "")
      fi
    fi
    if [ -n "$_docstring_lines" ] && echo "$_docstring_lines" | grep -qx "$line_num"; then
      continue
    fi
  fi

  # HC-01: hardcoded URL. Extract each URL and check individually so a line
  # with both example.com (allowed) and api.com (real) still fires on the real one.
  # Use word boundary via (^|[^A-Za-z0-9]) so we don't match tokens inside identifiers.
  while IFS= read -r url; do
    [ -z "$url" ] && continue
    # allow-list: only IANA-reserved test/example TLDs and localhost
    # `.example` must be the terminal label (RFC 2606) — anchor at path/port/end.
    # FP-B-01: also allowlist standard XML/POM/W3C namespace URLs which appear
    # as identifiers in build files, not as network endpoints.
    if echo "$url" | grep -qE '^https?://(localhost|127\.0\.0\.1|example\.(com|org|net)|[^/]+\.example(/|:|$)|reserved\.)'; then
      continue
    fi
    if echo "$url" | grep -qE '^https?://(maven\.apache\.org/POM/|www\.w3\.org/[0-9]+/XMLSchema|schemas\.xmlsoap\.org/)'; then
      continue
    fi
    emit_finding_if_touched "HC-01" "BLOCK" "$file" "$line_num" "Hardcoded URL '$url' in implementation — externalize to config" "" >> "$findings"
    break  # only one finding per line to avoid duplicate reports
  done < <(echo "$content" | grep -oE 'https?://[A-Za-z0-9][A-Za-z0-9._~:/?#@!$&*+,;=%-]*' || true)
  # HC-02: Authorization Bearer
  if echo "$content" | grep -qE 'Authorization[[:space:]]*:[[:space:]]*Bearer[[:space:]]+[A-Za-z0-9]'; then
    emit_finding_if_touched "HC-02" "BLOCK" "$file" "$line_num" "Hardcoded Authorization header value" "" >> "$findings"
  fi
  # HC-04: direct os.environ / System.getenv
  if [ "$LANGUAGE" = "python" ]; then
    if echo "$content" | grep -qE 'os\.environ\["[A-Z]'; then
      emit_finding_if_touched "HC-04" "FLAG" "$file" "$line_num" "Direct os.environ access — prefer secret_resolver / config layer" "" >> "$findings"
    fi
  else
    if echo "$content" | grep -qE 'System\.getenv\('; then
      emit_finding_if_touched "HC-04" "FLAG" "$file" "$line_num" "Direct System.getenv() — prefer SecretResolver" "" >> "$findings"
    fi
  fi
  # HC-06: hardcoded timeout numeric literal
  # Use word boundary via (^|[^A-Za-z0-9_]) so 'default_timeout' or 'my_timeout' don't match
  if echo "$content" | grep -qiE '(^|[^A-Za-z0-9_])(timeout|retries|max_retries)[[:space:]]*=[[:space:]]*[0-9]+'; then
    emit_finding_if_touched "HC-06" "FLAG" "$file" "$line_num" "Hardcoded timeout/retry number — externalize to config" "" >> "$findings"
  fi
done

status=$(status_from_findings < "$findings")
emit_report "hardcode" "$LANGUAGE" "$status" "$STARTED" < "$findings"
