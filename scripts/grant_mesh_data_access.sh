#!/usr/bin/env bash
# Bulk-add GitHub handles as collaborators on the private mesh-data repo.
# Founder-only utility. Uses your local `gh` CLI auth (no token in this file).
#
# Usage:
#   scripts/grant_mesh_data_access.sh <handle1> [<handle2> ...]
#   scripts/grant_mesh_data_access.sh --file handles.txt
#   scripts/grant_mesh_data_access.sh --dry-run <handle>
#
# Idempotent: re-granting an existing collaborator is a no-op (gh API returns 204).
# Permission level: push (collaborators can commit their own users/<email>.md).

set -euo pipefail

REPO="sidpan1/mesh-data"
PERMISSION="push"
DRY_RUN=0
HANDLES=()

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

[[ ${#HANDLES[@]} -gt 0 ]] || { echo "No handles given." >&2; usage 2; }

# Sanity check: gh is installed and authed.
command -v gh >/dev/null 2>&1 || { echo "gh CLI not found. brew install gh" >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "gh CLI not authenticated. Run: gh auth login" >&2; exit 1; }

# Confirm we own the repo before granting access.
gh repo view "$REPO" --json visibility -q .visibility >/dev/null 2>&1 || {
  echo "Cannot read $REPO. Are you authenticated as the repo owner?" >&2
  exit 1
}

OK_COUNT=0
FAIL_COUNT=0

for handle in "${HANDLES[@]}"; do
  # Strip leading @ if present.
  handle="${handle#@}"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] would PUT repos/$REPO/collaborators/$handle (permission=$PERMISSION)"
    continue
  fi

  if gh api -X PUT "repos/$REPO/collaborators/$handle" -f "permission=$PERMISSION" --silent 2>/tmp/mesh_grant_err; then
    echo "[ok]  $handle"
    OK_COUNT=$((OK_COUNT+1))
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
