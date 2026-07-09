#!/usr/bin/env bash
# lib/github-api.sh — gh CLI wrapper for review posting.
set -euo pipefail

# Use plain vars (not readonly) so the file can be sourced multiple times
# without hitting "readonly variable" under set -e.
#
# SDK_REVIEW_MARKER_PREFIX is intentionally an UNCLOSED HTML-comment fragment.
# It is NEVER emitted verbatim as a comment body; it is used only as a prefix
# substring matched via jq `contains($m)` in list_bot_review_comments() so we
# can identify all bot-posted comments regardless of their kind qualifier.
# Every real emitted marker (see orchestrate.sh) is a fully-closed HTML comment,
# e.g. "<!-- sdk-review:v1 kind=summary -->" or
#      "<!-- sdk-review:v1 check=SEC-01 id=SEC-01-3 -->".
# Do not "close" this prefix or the substring match will miss all qualified forms.
SDK_REVIEW_MARKER_PREFIX="${SDK_REVIEW_MARKER_PREFIX:-<!-- sdk-review:v1}"
SUMMARY_MARKER="${SUMMARY_MARKER:-<!-- sdk-review:v1 kind=summary -->}"

# check_gh_auth <hostname> → exit 0 if authed, exit 2 with message otherwise
check_gh_auth() {
  local hostname="${1:-github.com}"
  if ! gh auth status --hostname "$hostname" > /dev/null 2>&1; then
    echo "ERROR: gh CLI not authenticated for $hostname. Run: gh auth login --hostname $hostname" >&2
    exit 2
  fi
}

# detect_hostname → prints "github.com" or "github.tools.sap" from git remote
detect_hostname() {
  local remote_url
  remote_url=$(git remote get-url origin 2>/dev/null || echo "")
  case "$remote_url" in
    *github.tools.sap*) echo "github.tools.sap" ;;
    *github.com*)       echo "github.com" ;;
    *)                  echo "github.com" ;;
  esac
}

# gh_api — wrapper that pins --hostname so `gh_api repos/OWNER/REPO/…` hits the
# correct GitHub instance. Without this, gh defaults to github.com and every
# call against the internal github.tools.sap repo 404s.
gh_api() {
  gh api --hostname "$(detect_hostname)" "$@"
}

# detect_owner_repo → prints "owner/repo" from git remote
# Handles all remote formats:
#   https://github.com/OWNER/REPO.git
#   https://user@github.com/OWNER/REPO.git
#   https://token@github.tools.sap/OWNER/REPO.git
#   git@github.com:OWNER/REPO.git
#   ssh://git@github.com/OWNER/REPO.git
detect_owner_repo() {
  local remote_url
  remote_url=$(git remote get-url origin 2>/dev/null || echo "")
  [ -z "$remote_url" ] && { echo ""; return; }

  # Strip trailing .git if present
  remote_url="${remote_url%.git}"

  # SSH format: git@host:owner/repo
  if [[ "$remote_url" == *"@"*":"* && "$remote_url" != *"://"* ]]; then
    # cut everything up to and including ':'
    remote_url="${remote_url#*:}"
    echo "$remote_url"
    return
  fi

  # HTTP(S)/SSH-with-protocol: strip up to first '/' after host
  # First strip the protocol
  remote_url="${remote_url#*://}"
  # Strip optional user@ prefix
  remote_url="${remote_url#*@}"
  # Now format is: host/owner/repo — strip first component (host)
  remote_url="${remote_url#*/}"
  echo "$remote_url"
}

# get_pr_head_sha <pr_number> → prints the head SHA
get_pr_head_sha() {
  local pr="$1"
  gh pr view "$pr" --json headRefOid -q .headRefOid
}

# list_bot_review_comments <pr> → outputs "id\tbody_marker" for each review-comment we've posted
list_bot_review_comments() {
  local pr="$1"
  local owner_repo; owner_repo=$(detect_owner_repo)
  gh_api "repos/${owner_repo}/pulls/${pr}/comments" --paginate 2>/dev/null | \
    jq -r --arg m "$SDK_REVIEW_MARKER_PREFIX" '.[] | select(.body | contains($m)) | "\(.id)\t\(.body[0:120])"' || true
}

# list_bot_issue_comments <pr> → outputs "id" for each issue-comment (summary) we've posted
list_bot_issue_comments() {
  local pr="$1"
  local owner_repo; owner_repo=$(detect_owner_repo)
  gh_api "repos/${owner_repo}/issues/${pr}/comments" --paginate 2>/dev/null | \
    jq -r --arg m "$SUMMARY_MARKER" '.[] | select(.body | contains($m)) | .id' || true
}

# delete_prior_bot_artifacts <pr> — idempotency: remove all sdk-review:v1 comments before posting new
delete_prior_bot_artifacts() {
  local pr="$1"
  local owner_repo; owner_repo=$(detect_owner_repo)

  # review-comments (inline)
  list_bot_review_comments "$pr" | awk -F'\t' '{print $1}' | while read -r id; do
    [ -n "$id" ] && gh_api -X DELETE "repos/${owner_repo}/pulls/comments/${id}" > /dev/null 2>&1 || true
  done

  # issue-comments (summary)
  list_bot_issue_comments "$pr" | while read -r id; do
    [ -n "$id" ] && gh_api -X DELETE "repos/${owner_repo}/issues/comments/${id}" > /dev/null 2>&1 || true
  done
}

# is_fork_pr <pr> → prints "true" or "false"
# Fork PRs receive a read-only GITHUB_TOKEN in CI regardless of workflow permissions.
is_fork_pr() {
  local pr="$1"
  local head_repo
  head_repo=$(gh pr view "$pr" --json headRepositoryOwner,isCrossRepository -q '.isCrossRepository' 2>/dev/null || echo "false")
  echo "$head_repo"
}

# post_inline_comment <pr> <sha> <path> <line> <body>
# Silently skips on fork PRs (no write access).
post_inline_comment() {
  local pr="$1" sha="$2" path="$3" line="$4" body="$5"
  local owner_repo; owner_repo=$(detect_owner_repo)
  # HTTP 422 means "line not in diff" — retry as issue comment.
  # Any other failure (403 fork PR, network) is silent.
  local http_code
  http_code=$(gh_api "repos/${owner_repo}/pulls/${pr}/comments" \
    -F body="$body" \
    -F commit_id="$sha" \
    -F path="$path" \
    -F line="$line" \
    -F side="RIGHT" --include 2>&1 | head -1 | awk '{print $2}' || echo "500")

  if [ "$http_code" = "422" ]; then
    # Line not in diff — fall back to PR-level comment with citation
    gh_api "repos/${owner_repo}/issues/${pr}/comments" \
      -F body="$body

_(originally intended as inline on \`$path:$line\` but that line is not in the diff)_" > /dev/null 2>&1 || true
  fi
}

# post_summary_comment <pr> <body>
post_summary_comment() {
  local pr="$1" body="$2"
  local owner_repo; owner_repo=$(detect_owner_repo)
  gh_api "repos/${owner_repo}/issues/${pr}/comments" -F body="$body" > /dev/null 2>&1 || {
    echo "WARN: could not post summary comment (fork PR or missing pull-requests:write scope)" >&2
  }
}

# post_or_update_check_run <sha> <conclusion> <title> <summary>
post_or_update_check_run() {
  local sha="$1" conclusion="$2" title="$3" summary="$4"
  local owner_repo; owner_repo=$(detect_owner_repo)
  local check_name="sdk-module-review"
  local external_id="sdk-review-v1-${sha}"

  # try to find existing run for same SHA + name
  local existing
  existing=$(gh_api "repos/${owner_repo}/commits/${sha}/check-runs?check_name=${check_name}" 2>/dev/null | \
    jq -r '.check_runs[0].id // empty' 2>/dev/null || echo "")

  if [ -n "$existing" ]; then
    gh_api -X PATCH "repos/${owner_repo}/check-runs/${existing}" \
      -F status="completed" \
      -F conclusion="$conclusion" \
      -F "output[title]=$title" \
      -F "output[summary]=$summary" > /dev/null 2>&1 || {
        echo "WARN: could not update check-run (fork PR or missing checks:write scope)" >&2
      }
  else
    gh_api "repos/${owner_repo}/check-runs" \
      -F name="$check_name" \
      -F head_sha="$sha" \
      -F external_id="$external_id" \
      -F status="completed" \
      -F conclusion="$conclusion" \
      -F "output[title]=$title" \
      -F "output[summary]=$summary" > /dev/null 2>&1 || {
        echo "WARN: could not create check-run (fork PR or missing checks:write scope)" >&2
      }
  fi
}

# apply_label <pr> <label> — creates label if missing, adds to PR, removes other sdk-review labels
apply_label() {
  local pr="$1" label="$2"
  local owner_repo; owner_repo=$(detect_owner_repo)

  # ensure labels exist (silent on failure — fork PR or no permission)
  for l in "sdk-review: ✅ passed:0e8a16" "sdk-review: ❌ blocked:b60205" \
           "sdk-review: ⚠️ flagged:e4e669" "sdk-review: skipped:cccccc"; do
    local name color
    name="${l%:*}"; color="${l##*:}"
    gh_api "repos/${owner_repo}/labels" -F name="$name" -F color="$color" > /dev/null 2>&1 || true
  done

  # remove any existing sdk-review labels first
  # Guard: `grep` returns 1 on no-match, which combined with `set -o pipefail`
  # aborts the caller. Use `|| true` to swallow that.
  local existing_labels
  existing_labels=$(gh pr view "$pr" --json labels -q '.labels[].name' 2>/dev/null || echo "")
  echo "$existing_labels" | grep '^sdk-review:' 2>/dev/null | while read -r existing; do
    [ -n "$existing" ] && gh pr edit "$pr" --remove-label "$existing" > /dev/null 2>&1 || true
  done || true

  # add the target label
  gh pr edit "$pr" --add-label "$label" > /dev/null 2>&1 || {
    echo "WARN: could not apply label (fork PR or missing pull-requests:write scope)" >&2
  }
}

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  cmd="${1:-}"; shift || true
  case "$cmd" in
    check_gh_auth)          check_gh_auth "$@" ;;
    detect_hostname)        detect_hostname "$@" ;;
    detect_owner_repo)      detect_owner_repo "$@" ;;
    get_pr_head_sha)        get_pr_head_sha "$@" ;;
    is_fork_pr)             is_fork_pr "$@" ;;
    delete_prior_bot_artifacts) delete_prior_bot_artifacts "$@" ;;
    post_inline_comment)    post_inline_comment "$@" ;;
    post_summary_comment)   post_summary_comment "$@" ;;
    post_or_update_check_run) post_or_update_check_run "$@" ;;
    apply_label)            apply_label "$@" ;;
    *) echo "Usage: github-api.sh <command> args" >&2; exit 2 ;;
  esac
fi
