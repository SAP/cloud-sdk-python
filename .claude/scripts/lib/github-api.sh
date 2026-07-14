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

# delete_prior_bot_artifacts <pr> — idempotency: remove prior INLINE review
# comments before posting fresh ones. The summary comment is NOT deleted here;
# post_summary_comment updates it in place (avoids a delete→recreate race that
# produced duplicate summaries).
delete_prior_bot_artifacts() {
  local pr="$1"
  local owner_repo; owner_repo=$(detect_owner_repo)

  # review-comments (inline). Loop with a bounded retry: a single pass can miss
  # comments if pagination races with deletion, which is how duplicate/stale
  # comments accumulate. Re-list until none remain (max 5 passes).
  local pass ids
  for pass in 1 2 3 4 5; do
    ids=$(list_bot_review_comments "$pr" | awk -F'\t' '{print $1}' | grep -E '^[0-9]+$' || true)
    [ -z "$ids" ] && break
    while read -r id; do
      [ -n "$id" ] && gh_api -X DELETE "repos/${owner_repo}/pulls/comments/${id}" > /dev/null 2>&1 || true
    done <<< "$ids"
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
# On success: echoes the created comment's html_url (for linking from summary).
# On 422 (line not in diff): silent, echoes nothing (caller lists it in summary).
# Silently skips on fork PRs (no write access).
post_inline_comment() {
  local pr="$1" sha="$2" path="$3" line="$4" body="$5"
  local owner_repo; owner_repo=$(detect_owner_repo)
  local resp
  # Capture the JSON response; on success it contains .html_url.
  resp=$(gh_api "repos/${owner_repo}/pulls/${pr}/comments" \
    -F body="$body" \
    -F commit_id="$sha" \
    -F path="$path" \
    -F line="$line" \
    -F side="RIGHT" 2>/dev/null || true)
  local url
  url=$(echo "$resp" | jq -r '.html_url // empty' 2>/dev/null || echo "")
  if [ -n "$url" ]; then
    echo "$url"
  fi
  # If the post failed (no url), the caller still lists the finding in the
  # summary, so nothing is lost. We intentionally do NOT create a duplicate
  # issue-comment fallback here — the summary already carries every finding.
}

# post_summary_comment <pr> <body>
# Update-in-place: if a prior summary comment exists, PATCH it instead of
# creating a new one. This makes the summary idempotent even under concurrent
# runs (which is how duplicate summaries appeared). Only creates a new comment
# when none exists.
post_summary_comment() {
  local pr="$1" body="$2"
  local owner_repo; owner_repo=$(detect_owner_repo)
  local existing_id
  existing_id=$(list_bot_issue_comments "$pr" | grep -E '^[0-9]+$' | head -1 || true)
  if [ -n "$existing_id" ]; then
    gh_api -X PATCH "repos/${owner_repo}/issues/comments/${existing_id}" -F body="$body" > /dev/null 2>&1 || {
      echo "WARN: could not update summary comment (fork PR or missing pull-requests:write scope)" >&2
    }
    # Delete any extra duplicates beyond the one we just updated.
    list_bot_issue_comments "$pr" | grep -E '^[0-9]+$' | tail -n +2 | while read -r dup; do
      [ -n "$dup" ] && gh_api -X DELETE "repos/${owner_repo}/issues/comments/${dup}" > /dev/null 2>&1 || true
    done
  else
    gh_api "repos/${owner_repo}/issues/${pr}/comments" -F body="$body" > /dev/null 2>&1 || {
      echo "WARN: could not post summary comment (fork PR or missing pull-requests:write scope)" >&2
    }
  fi
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

  # Idempotent: read current labels first. If the target label is already
  # the ONLY sdk-review label, skip all GitHub API calls to avoid the noisy
  # "added X and removed X" churn in the PR timeline.
  local existing_labels
  existing_labels=$(gh pr view "$pr" --json labels -q '.labels[].name' 2>/dev/null || echo "")
  local current_sdk_labels
  current_sdk_labels=$(echo "$existing_labels" | grep '^sdk-review:' 2>/dev/null || true)
  if [ "$current_sdk_labels" = "$label" ]; then
    return 0  # already correct — nothing to do
  fi

  # remove any existing sdk-review labels that differ from target
  echo "$current_sdk_labels" | while read -r existing; do
    [ -n "$existing" ] && [ "$existing" != "$label" ] && \
      gh pr edit "$pr" --remove-label "$existing" > /dev/null 2>&1 || true
  done || true

  # add the target label only if not already present
  if ! echo "$current_sdk_labels" | grep -Fxq "$label" 2>/dev/null; then
    gh pr edit "$pr" --add-label "$label" > /dev/null 2>&1 || {
      echo "WARN: could not apply label (fork PR or missing pull-requests:write scope)" >&2
    }
  fi
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
