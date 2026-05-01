# Paste this into Claude Code

> MESH schema v1. Last verified 2026-05-01.

You are Claude. The user just pasted this into a fresh Claude Code session. Walk them through MESH onboarding end-to-end. MESH is a curated Saturday-7pm dinner club for Bengaluru builders; you will install a small skill on their machine, verify GitHub access, inspect their last 4 weeks of Claude Code work, and hand off to a single slash command that does the rest. Raw conversations never leave the user's device. Only a 200-word summary they review and approve gets pushed to a private repo.

You have four steps. Run them in order. Use Bash for shell commands, Read for files, AskUserQuestion when offering choices. After each step, tell the user it is done before moving to the next.

## Step 0: Tell the user what's about to happen

In your own words:

> "MESH curates a Saturday-7pm dinner for 6 builders, matched on what you are actually building (read from your local Claude Code sessions). Four steps: install the skill, verify GitHub access, check your last 4 weeks have enough material, and run the summary flow in a fresh session. Raw conversations never leave your machine. Only a 200-word summary you review goes to a private repo. Continue?"

If they decline, stop. Otherwise proceed.

## Step 1 of 4: Install the skill

Run this single bash block. Safe to re-run on an already-installed machine.

```bash
set -e
python3 -c "import sys; assert sys.version_info >= (3, 11), f'MESH needs Python 3.11+, found {sys.version.split()[0]}'" || {
  echo "Install Python 3.11 or newer first. brew install python@3.11 (mac) or apt install python3.11 (linux)."
  exit 1
}
mkdir -p ~/.claude/skills
cd ~/.claude/skills
if [ ! -e mesh-skills ]; then
  git clone https://github.com/sidpan1/mesh-skills.git
fi
cd mesh-skills
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -e . >/dev/null
ln -snf "$PWD/skills/mesh_trajectory" ~/.claude/skills/mesh-trajectory
echo "[1/4] MESH skill installed at ~/.claude/skills/mesh-trajectory"
```

If any line fails, surface the exact error to the user and stop. Common case: `python3` resolves to 3.10 or older; tell them to install 3.11.

After success, tell the user: **"[1/4] Skill installed."**

## Step 2 of 4: Verify GitHub access

```bash
git ls-remote --exit-code https://github.com/sidpan1/mesh-data HEAD >/dev/null 2>&1 && echo "ACCESS_OK" || echo "ACCESS_DENIED"
```

If `ACCESS_OK`: tell the user **"[2/4] GitHub access verified."**

If `ACCESS_DENIED`: do NOT continue. We will request access for them via GitHub itself, no DMs needed.

First, check that `gh` CLI is installed and authenticated:

```bash
command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1 && echo "GH_OK" || echo "GH_NOT_READY"
```

**If `GH_NOT_READY`:** tell the user to install + auth:

> "I need the GitHub CLI (`gh`) to file your access request automatically.
>
>     mac:    brew install gh && gh auth login
>     linux:  see https://cli.github.com
>
> Then re-run this prompt."

Then stop.

**If `GH_OK`:** detect the user's handle and offer to file the request:

```bash
HANDLE=$(gh api user --jq .login)
echo "Detected GitHub handle: $HANDLE"
```

Use `AskUserQuestion`:

- Question: "Your GitHub handle is `$HANDLE`. Open an access-request issue on sidpan1/mesh-skills? The founder gets notified by GitHub and grants access; this prompt picks up where it left off when you re-run."
- Options:
  1. "Yes, file the request now (Recommended)"
  2. "I will message the founder directly"
  3. "You decide"

If they pick "Yes" (or "You decide"), run:

```bash
gh issue create \
  -R sidpan1/mesh-skills \
  --title "Access request: $HANDLE" \
  --body "Filed automatically by /mesh-trajectory onboarding.

Please add \`@$HANDLE\` as a collaborator (push permission) to \`sidpan1/mesh-data\` so I can complete MESH setup.

Founder: run \`scripts/grant_mesh_data_access.sh --pending\` to grant all open access requests at once, or \`scripts/grant_mesh_data_access.sh $HANDLE\` for just this one."
```

Capture the URL `gh issue create` prints. Tell the user:

> "[2/4] Access request filed: <ISSUE_URL>. The founder is notified. Once they grant access (the issue will be closed automatically), re-run this prompt and Step 2 will pass."

Then stop.

If they pick option 2 ("I will message the founder directly"), give them:

> "Tell the founder via WhatsApp / DM:
>
>     'Add @$HANDLE to mesh-data, please.'
>
> Re-run this prompt once they confirm."

Then stop.

## Step 3 of 4: Check the corpus has enough material

This step prevents the most common silent failure: a thin corpus produces a thin trajectory.

```bash
~/.claude/skills/mesh-skills/.venv/bin/python -m skills.mesh_trajectory.scripts.extract --to-dir /tmp/mesh_check
COUNT=$(jq length /tmp/mesh_check/manifest.json)
PROJECTS=$(jq -r '[.[].project_slug_normalized] | unique | length' /tmp/mesh_check/manifest.json)
rm -rf /tmp/mesh_check
echo "$COUNT sessions across $PROJECTS projects in the last 4 weeks."
```

Decide based on `COUNT`:
- **0 sessions**: stop. Tell the user: "MESH reads your Claude Code session history; you have none in the last 4 weeks. Use Claude Code on a real project for at least a week, then re-run this prompt."
- **1 to 4 sessions**: warn but allow continue. Use AskUserQuestion: "Only N sessions found. Your trajectory will be short and may not reflect your full work. Proceed anyway, or come back later with more sessions?" Options: "Proceed anyway", "Stop and try later", "You decide".
- **5 or more**: tell the user **"[3/4] Found N sessions across P projects. Plenty to work with."**

## Step 4 of 4: Hand off to a fresh session

Detect whether the user has a saved profile from a previous run:

```bash
test -f ~/.config/mesh/profile.yaml && echo HAS_PROFILE || echo NO_PROFILE
```

If `HAS_PROFILE`, the next command is `/mesh-trajectory sync`. If `NO_PROFILE`, it is `/mesh-trajectory onboard`.

Now give the user this exact hand-off (substitute the right command):

> "[4/4] Setup done. Last step needs a fresh Claude Code session so the new skill is loaded clean.
>
>     1. Open a NEW Claude Code session in any folder.
>     2. Type:  /mesh-trajectory <onboard|sync>
>
> The skill will take over: ask any missing profile fields, summarize your last 4 weeks of work into a 200-word trajectory, run a privacy lint with you in the loop, and push to mesh-data. You'll review the body before push. Total time: 5 to 10 minutes.
>
> When it's done, you'll get a dinner invite via `/mesh-trajectory check` on Friday evening."

Then stop. Do NOT run /mesh-trajectory in this session. The skill body may be cached from before install; a fresh session guarantees the right flow runs.
