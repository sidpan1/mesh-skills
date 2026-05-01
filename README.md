# mesh-skills

MESH V0: AI-curated professional dinners for builders.

See `spec.md` for the product spec. See `plans/` for the iterative implementation history.

## Onboarding (paste this into Claude Code)

Open Claude Code in any folder and paste:

```
You are Claude. Onboard me into MESH.

Fetch https://raw.githubusercontent.com/sidpan1/mesh-skills/main/ONBOARD.md
and follow every step in order. Do not skip the install, the access check,
or the profile-existence test.

After the slash command in step 3 finishes (or fails), stop and report.

Note: if /mesh-trajectory is not recognized after install, tell me to start
a fresh Claude Code session and paste this prompt again.

Requires: Python 3.10+, git, a GitHub account that the founder has added
to the private mesh-data repo.
```

The referenced `ONBOARD.md` walks Claude through install, access verification, and either `/mesh-trajectory onboard` (new users) or `/mesh-trajectory sync` (existing users) end-to-end.

Latest version always served from `main`. To pin to a specific commit, replace `main` in the URL with a commit SHA.

## For the founder

After cloning, run:

    python3 -m venv .venv
    .venv/bin/pip install -e ".[dev]"
    .venv/bin/pytest

The `mesh-orchestrator` skill is in `skills/mesh_orchestrator/`. It runs on the founder laptop on Friday to compose tables for the Saturday dinner.

## Privacy

Two-repo split: `mesh-skills` (this repo, public) holds the skill code and onboarding flow. `mesh-data` (private) holds individual user trajectories. Raw Claude Code conversations never leave the user's device; only the validated, lint-reviewed 8-field payload is uploaded. See `spec.md` for the privacy contract.
