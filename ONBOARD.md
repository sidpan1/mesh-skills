# Paste this into Claude Code

You are Claude. The user just pasted this into a fresh Claude Code session. Walk them through onboarding into MESH end-to-end. MESH is a curated Saturday-7pm dinner club for Bengaluru builders; you will install a small skill on their machine, ask a few questions, summarize their last 4 weeks of Claude Code work into a 200-word trajectory, and push only that summary to a private GitHub repo. Raw conversations never leave their device.

Do all of the steps below in order. Do not skip ahead. Use Bash for shell commands, Read for files, AskUserQuestion when offering choices.

## Step 0: Confirm context

Tell the user, in your own words:

> "MESH curates a Saturday-7pm dinner for 6 builders, matched on what you are actually building (read from your local Claude Code sessions). I will install a small skill, ask you a few questions, summarize your trajectory locally, and push only that summary to a private repo. Raw conversations never leave your machine. Continue?"

If they decline, stop. Otherwise proceed.

## Step 1: Install (idempotent)

Run this single bash block. It is safe to re-run; existing installs are reused.

```bash
set -e
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
echo "MESH skill installed at ~/.claude/skills/mesh-trajectory"
```

If any step fails, surface the error to the user and stop.

## Step 2: Verify GitHub access

```bash
git ls-remote --exit-code https://github.com/sidpan1/mesh-data HEAD
```

If it succeeds (prints a SHA), continue.

If it fails with auth error, tell the user: "Your GitHub auth does not have access to mesh-data yet. Ping the founder with your GitHub handle and they will grant you access. Re-run this prompt after they confirm." Then stop.

## Step 3: Run the trajectory flow

Check whether the user already has a saved profile:

```bash
test -f ~/.config/mesh/profile.yaml && echo HAS_PROFILE || echo NO_PROFILE
```

- If HAS_PROFILE: tell the user to run `/mesh-trajectory sync`. The skill will reuse their saved name / email / LinkedIn / role / Saturdays, re-extract their last 4 weeks of sessions, regenerate the trajectory body, run the privacy lint with interactive flag resolution, and push the updated `users/<email>.md` to mesh-data.
- If NO_PROFILE: tell the user to run `/mesh-trajectory onboard`. The skill will collect profile fields (name, email, LinkedIn, role, available Saturdays, optional do-not-match list), then run the same extract → digest → group → summarize → review → lint → push pipeline.

Either way, after the slash command finishes, the user's trajectory is live in mesh-data and they will receive a `/mesh-trajectory check` invite on Friday evening.

## Step 4: Confirm and hand off

After the slash command completes successfully, tell the user:

> "MESH onboarding complete. Run `/mesh-trajectory check` on Friday evening to see your dinner invite. The dinner is the following Saturday at 7pm in Bengaluru."

If the slash command fails, surface the error and stop. Do not retry silently.
