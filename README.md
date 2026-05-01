# mesh-skills

MESH V0: AI-curated professional dinners for builders.

See `spec.md` for the product spec. See `plans/` for the iterative implementation history.

## Onboarding (paste this into Claude Code)

Open Claude Code in any folder and paste:

```
You are Claude. Onboard me into MESH.

Fetch https://raw.githubusercontent.com/sidpan1/mesh-skills/main/ONBOARD.md
and follow every step in order. Walk me through all 4 steps, confirm each
one out loud before moving on, and stop if any step fails.

Requires: Python 3.11+, git, a GitHub account that the founder has added
to the private mesh-data repo.
```

The referenced `ONBOARD.md` is a four-step guided flow:

1. **Install** the skill (idempotent, ~30s).
2. **Verify** GitHub access to mesh-data; if denied, hand the user a copy-paste request message to send the founder.
3. **Check** the user's last 4 weeks of Claude Code corpus has enough material; warn if sparse, stop if empty.
4. **Hand off** to a fresh Claude Code session for the trajectory flow (`/mesh-trajectory sync` or `/mesh-trajectory onboard`).

Latest version always served from `main`. To pin to a specific commit, replace `main` in the URL with a commit SHA.

## For the founder

After cloning, run:

    python3 -m venv .venv
    .venv/bin/pip install -e ".[dev]"
    .venv/bin/pytest

The `mesh-orchestrator` skill is in `skills/mesh_orchestrator/`. It runs on the founder laptop on Friday to compose tables for the Saturday dinner.

### Grant attendees access to mesh-data

`mesh-data` is private. Each attendee needs collaborator access on their GitHub handle before they can push their trajectory. The flow is fully Claude-driven on the attendee side: when their `git ls-remote` access check fails, the onboarding prompt offers to file an access-request issue on the public `mesh-skills` repo automatically (`gh issue create` under the hood). You receive a normal GitHub issue notification.

To grant pending requests in bulk (recommended for the launch event):

    scripts/grant_mesh_data_access.sh --pending             # grant all open access-request issues, comment + close

Or grant specific handles:

    scripts/grant_mesh_data_access.sh handle1 handle2 handle3
    scripts/grant_mesh_data_access.sh --file handles.txt   # one per line, # comments allowed
    scripts/grant_mesh_data_access.sh --dry-run --pending   # see what would happen

`--pending` reads open issues with title `Access request: ...` (filed by ONBOARD.md Step 2), grants the **issue author's** handle (not the title text) push access on `mesh-data`, then comments and closes the issue. Idempotent: re-granting an existing collaborator is a no-op. Uses your local `gh` CLI auth (no tokens stored in the repo).

## Privacy

Two-repo split: `mesh-skills` (this repo, public) holds the skill code and onboarding flow. `mesh-data` (private) holds individual user trajectories. Raw Claude Code conversations never leave the user's device; only the validated, lint-reviewed 8-field payload is uploaded. See `spec.md` for the privacy contract.
