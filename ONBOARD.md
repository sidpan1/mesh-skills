# Paste this into Claude Code

> **Pre-launch note (founder reminder):** Before distributing this file to attendees, push `mesh-skills` to `https://github.com/sidpan1/mesh-skills` as a public repo. Until then the `git clone` in Step 1 will 404. Remove this note before sending.

You are about to onboard into MESH, a curated dinner-club for Bengaluru builders.

## Step 0: Confirm context

Tell the user:

> "MESH curates a Saturday-7pm dinner for 6 builders, matched on what you're actually
>  building (read from your local Claude Code sessions). I'll install a small skill,
>  ask you a few questions, summarize your trajectory locally, and push only that summary
>  to a private repo. Raw conversations never leave your machine. Continue?"

If they decline: stop. Otherwise proceed.

## Step 1: Install the skill

Run these bash commands (show them to the user first):

```bash
mkdir -p ~/.claude/skills
cd ~/.claude/skills
if [ ! -d mesh-skills ]; then
  git clone https://github.com/sidpan1/mesh-skills.git
fi
cd mesh-skills
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
ln -snf "$PWD/skills/mesh_trajectory" ~/.claude/skills/mesh-trajectory
```

## Step 2: Verify GitHub access

The skill uses the user's existing local git auth (gh CLI, credential helper, SSH). No new tokens to generate. Run:

```bash
git ls-remote --exit-code https://github.com/sidpan1/mesh-data HEAD
```

If it succeeds (prints a SHA), the user is good. Continue to Step 3.

If it fails with auth error: tell the user "Your GitHub auth doesn't have access to mesh-data yet. Ping the founder with your GitHub handle and they will grant you access. Re-run this step after they confirm." Then stop.

## Step 3: Run /mesh-onboard

Tell the user to run `/mesh-onboard`. The skill takes over from here.

## Step 4 (founder, post-event):

Once onboarded, the user will get an invite via `/mesh-check` on Friday evening.
The dinner is the following Saturday at 7pm in Bengaluru.
