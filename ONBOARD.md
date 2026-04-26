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

## Step 2: Collect the user's GitHub PAT

Tell the user:

> "I need a GitHub Personal Access Token with `repo` scope on the `mesh-data`
>  repository. Visit https://github.com/settings/tokens, create a fine-grained
>  token scoped to `mesh-data` only, and paste it here."

Set in env: `export MESH_GH_TOKEN=<token>` and persist to `~/.config/mesh/env`.

## Step 3: Run /mesh-onboard

Tell the user to run `/mesh-onboard`. The skill takes over from here.

## Step 4 (founder, post-event):

Once onboarded, the user will get an invite via `/mesh-check` on Friday evening.
The dinner is the following Saturday at 7pm in Bengaluru.
