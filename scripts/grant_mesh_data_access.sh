#!/usr/bin/env bash
# Bulk-add GitHub handles as collaborators on the private mesh-data repo.
# Founder-only utility. Uses your local `gh` CLI auth (no token in this file).
#
# Usage:
#   scripts/grant_mesh_data_access.sh <handle1> [<handle2> ...]
#   scripts/grant_mesh_data_access.sh --file handles.txt
#   scripts/grant_mesh_data_access.sh --pending             # grant all open access-request issues
#   scripts/grant_mesh_data_access.sh --dry-run <handle>
#   scripts/grant_mesh_data_access.sh --dry-run --pending
#
# --pending mode reads open issues on sidpan1/mesh-skills with title
# "Access request: ..." (filed by ONBOARD.md Step 2), grants the issue
# author push access on mesh-data, then comments + closes the issue.
#
# Idempotent: re-granting an existing collaborator is a no-op (gh API returns 204).
# Permission level: push (collaborators can commit their own users/<email>.md).

set -euo pipefail

REPO="sidpan1/mesh-data"
ISSUE_REPO="sidpan1/mesh-skills"
PERMISSION="push"
DRY_RUN=0
PENDING_MODE=0
HANDLES=()
# Map handles back to issue numbers in --pending mode so we can close them.
declare -a PENDING_ISSUES=()

usage() {
  sed -n '2,11p' "$0" | sed 's/^# \?//'
  exit "${1:-0}"
}

# Parse args.
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage 0
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --pending)
      PENDING_MODE=1
      shift
      ;;
    --file)
      [[ $# -ge 2 ]] || { echo "--file needs a path" >&2; exit 2; }
      while IFS= read -r line; do
        # Skip blank and comment lines.
        line="${line%%#*}"
        line="$(echo "$line" | tr -d '[:space:]')"
        [[ -n "$line" ]] && HANDLES+=("$line")
      done < "$2"
      shift 2
      ;;
    --)
      shift
      while [[ $# -gt 0 ]]; do HANDLES+=("$1"); shift; done
      ;;
    -*)
      echo "Unknown flag: $1" >&2
      usage 2
      ;;
    *)
      HANDLES+=("$1")
      shift
      ;;
  esac
done

# Sanity check: gh is installed and authed.
command -v gh >/dev/null 2>&1 || { echo "gh CLI not found. brew install gh" >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh CLI not authenticated. Run: gh auth login" >&2; exit 1; }

# Confirm we own the repo before granting access.
gh repo view "$REPO" --json visibility -q .visibility >/dev/null 2>&1 || {
  echo "Cannot read $REPO. Are you authenticated as the repo owner?" >&2
  exit 1
}

# Pending mode: pull handles from open access-request issues on the public repo.
if [[ "$PENDING_MODE" -eq 1 ]]; then
  echo "Reading open access-request issues from $ISSUE_REPO..."
  issues_json=$(gh issue list -R "$ISSUE_REPO" --state open --search "Access request: in:title" --json number,author,title --limit 100)
  count=$(echo "$issues_json" | jq length)
  if [[ "$count" -eq 0 ]]; then
    echo "No pending access-request issues."
    exit 0
  fi
  echo "Found $count pending request(s)."
  while IFS=$'\t' read -r num login title; do
    [[ -n "$num" ]] || continue
    HANDLES+=("$login")
    PENDING_ISSUES+=("$num")
  done < <(echo "$issues_json" | jq -r '.[] | [.number, .author.login, .title] | @tsv')
fi

[[ ${#HANDLES[@]} -gt 0 ]] || { echo "No handles given." >&2; usage 2; }

OK_COUNT=0
FAIL_COUNT=0

for i in "${!HANDLES[@]}"; do
  handle="${HANDLES[$i]}"
  # Strip leading @ if present.
  handle="${handle#@}"
  issue_num="${PENDING_ISSUES[$i]:-}"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    if [[ -n "$issue_num" ]]; then
      echo "[dry-run] would PUT repos/$REPO/collaborators/$handle (permission=$PERMISSION) and close issue #$issue_num"
    else
      echo "[dry-run] would PUT repos/$REPO/collaborators/$handle (permission=$PERMISSION)"
    fi
    continue
  fi

  if gh api -X PUT "repos/$REPO/collaborators/$handle" -f "permission=$PERMISSION" --silent 2>/tmp/mesh_grant_err; then
    echo "[ok]  $handle"
    OK_COUNT=$((OK_COUNT+1))

    # In --pending mode, comment + close the originating issue.
    if [[ -n "$issue_num" ]]; then
      gh issue comment "$issue_num" -R "$ISSUE_REPO" -b "Access granted on \`$REPO\`. Re-run the onboarding prompt in a fresh Claude Code session and Step 2 will pass." >/dev/null 2>&1 || true
      gh issue close "$issue_num" -R "$ISSUE_REPO" >/dev/null 2>&1 || true
      echo "      closed issue #$issue_num"
    fi
  else
    err="$(cat /tmp/mesh_grant_err 2>/dev/null || true)"
    echo "[err] $handle: $err"
    FAIL_COUNT=$((FAIL_COUNT+1))
  fi
done

rm -f /tmp/mesh_grant_err

if [[ "$DRY_RUN" -eq 0 ]]; then
  echo ""
  echo "Granted: $OK_COUNT  Failed: $FAIL_COUNT  Repo: $REPO  Permission: $PERMISSION"
fi
