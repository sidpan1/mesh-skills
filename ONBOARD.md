# Paste this into Claude Code

> MESH schema v1. Last verified 2026-05-01.

You are Claude. The user just pasted this into a fresh Claude Code session. Walk them through MESH onboarding end-to-end. MESH is a curated Saturday-7pm dinner club for Bengaluru builders; you will install a small skill on their machine, verify GitHub access, inspect their last 4 weeks of Claude Code work, and hand off to a single slash command that does the rest. Raw conversations never leave the user's device. Only a 200-word summary they review and approve gets pushed to a shared GitHub repo (`mesh-data`).

> **Launch-window disclosure (2026-05-01).** During the launch event window, the `mesh-data` repo is PUBLIC for operational simplicity. The founder will revert it to private after the launch event. When the user reviews their 200-word body in step 17 of the trajectory flow, treat it as world-readable: only push what they would be comfortable being publicly indexable for ~24-48 hours. Disclose this to the user in step 0.

You have four steps. Run them in order. Use Bash for shell commands, Read for files, AskUserQuestion when offering choices. After each step, tell the user it is done before moving to the next.

## Step 0: Tell the user what's about to happen

In your own words:

> "MESH curates a Saturday-7pm dinner for 6 builders, matched on what you are actually building (read from your local Claude Code sessions). Four steps: install the skill, verify GitHub access, check your last 4 weeks have enough material, and run the summary flow in a fresh session. Raw conversations never leave your machine. Only a 200-word summary you review goes to a shared repo. **Launch-window note: the shared repo is currently public; the founder will revert it to private after the launch event. Treat your 200-word body as world-readable when you review it.** Continue?"

If they decline, stop. Otherwise proceed.

## Step 1 of 4: Install the skill

This step has two sub-flows depending on what Python the user has. Run the detection FIRST; then act on the result.

### 1a. Detect Python

Run this single block. It produces one of three outcomes: `PY_OK`, `PY_OLD`, or `PY_MISSING`. Capture the output before doing anything else.

```bash
if ! command -v python3 >/dev/null 2>&1; then
  echo "PY_MISSING"
elif python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"; then
  PYV=$(python3 -c "import sys; print('.'.join(str(x) for x in sys.version_info[:3]))")
  echo "PY_OK $PYV"
else
  PYV=$(python3 -c "import sys; print('.'.join(str(x) for x in sys.version_info[:3]))")
  echo "PY_OLD $PYV"
fi
```

### 1b. Branch on the detection

**If `PY_OK`:** Tell the user `"Python $PYV detected; proceeding."` and skip to step 1d (install the skill).

**If `PY_OLD` or `PY_MISSING`:** use `AskUserQuestion`:

> Q: "MESH needs Python 3.10 or newer. Detected: `<PY_OLD $PYV | no python3 found>`. How do you want to proceed?"
> Options:
>   1. **"Auto-install via uv (recommended; ~5s, no sudo, all platforms)"** - I run a one-liner from astral.sh that fetches uv, then `uv python install 3.11` for a project-scoped Python. Your system Python is not touched.
>   2. **"I'll install Python myself, exit and re-run this prompt"** - You install Python 3.10+ via brew / apt / python.org, then re-paste this prompt.
>   3. **"You decide"** - Defaults to option 1.

If they pick option 2, print:

> "OK. Install Python 3.10+ via the method you prefer:
>     mac:    brew install python@3.11    (https://brew.sh)
>     linux:  sudo apt install -y python3.11    (Debian/Ubuntu) or your distro's equivalent
>     other:  https://www.python.org/downloads/
>
> Re-paste this prompt once you have python3 --version reporting 3.10 or newer."

Then stop the prompt.

If they pick option 1 (or "You decide"), show the exact command before running it:

```bash
# Show the exact command first; do not run silently.
echo "Will run, in order:"
echo "  1. curl -LsSf https://astral.sh/uv/install.sh | sh   # installs uv to ~/.local/bin"
echo "  2. uv python install 3.11                            # downloads a project-scoped Python"
```

Then ask one more confirmation via `AskUserQuestion`:
> Q: "Run the two commands above?"
> Options: "Yes, run them" / "Cancel" / "You decide" (defaults to Yes)

On Cancel, stop with: `"OK, exiting. Re-run this prompt once Python 3.10+ is available."`

On Yes, run the install:

```bash
set -e
# Install uv if not already present.
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # uv installs to ~/.local/bin which may not be on PATH yet.
  export PATH="$HOME/.local/bin:$PATH"
fi
# Verify uv is now callable.
uv --version
# Download a project-scoped Python 3.11.
uv python install 3.11
```

After this completes, set a marker so step 1d knows to use uv-managed Python:

```bash
USE_UV=1
```

(If `python3` was already 3.10+, `USE_UV` stays unset and step 1d uses the system `python3`.)

### 1c. Confirm we have a usable Python

By the time control reaches here, EITHER `python3 --version` reports 3.10+ (PY_OK path), OR uv is installed and `uv python install 3.11` succeeded (`USE_UV=1`). Tell the user one of:
- `"Using your existing Python: $(python3 -V)."`
- `"Using uv-managed Python 3.11 (your system Python is not modified)."`

### 1d. Install the skill (idempotent)

```bash
set -e
mkdir -p ~/.claude/skills
cd ~/.claude/skills
if [ ! -e mesh-skills ]; then
  git clone https://github.com/sidpan1/mesh-skills.git
fi
cd mesh-skills

# Create the venv. If we used uv to fetch Python, create the venv with uv;
# otherwise use the system python3 -m venv.
if [ ! -d .venv ]; then
  if [ "${USE_UV:-0}" = "1" ]; then
    uv venv --python 3.11 .venv
  else
    python3 -m venv .venv
  fi
fi

.venv/bin/pip install -e . >/dev/null
ln -snf "$PWD/skills/mesh_trajectory" ~/.claude/skills/mesh-trajectory
echo "[1/4] MESH skill installed at ~/.claude/skills/mesh-trajectory"
```

If any line fails, surface the exact error to the user and stop.

After success, tell the user: **"[1/4] Skill installed."**

## Step 2 of 4: Verify GitHub WRITE access

The user needs to push their `users/<email>.md` to `mesh-data`. With the launch-window public state, read access is automatic; write access still requires being a repo collaborator. We check write access directly.

First, check that `gh` CLI is installed and authenticated (we need it both for the access check and, on failure, to file an access request):

```bash
command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1 && echo "GH_OK" || echo "GH_NOT_READY"
```

**If `GH_NOT_READY`:** tell the user to install + auth (same instructions as the access-denied path below), then re-run.

**If `GH_OK`:** check collaborator status:

```bash
HANDLE=$(gh api user --jq .login)
gh api "repos/sidpan1/mesh-data/collaborators/$HANDLE" --silent 2>/dev/null && echo "ACCESS_OK" || echo "ACCESS_DENIED"
```

If `ACCESS_OK`: tell the user **"[2/4] GitHub write access verified ($HANDLE is a mesh-data collaborator)."**

If `ACCESS_DENIED`: do NOT continue. We will request access for them via GitHub itself, no DMs needed.

If the user fell through here from the `GH_NOT_READY` branch above, tell them:

> "I need the GitHub CLI (`gh`) to file your access request automatically.
>
>     mac:    brew install gh && gh auth login
>     linux:  see https://cli.github.com
>
> Then re-run this prompt."

Then stop.

Otherwise (`GH_OK` but not a collaborator), use `AskUserQuestion`:

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
