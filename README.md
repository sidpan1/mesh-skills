# mesh-skills

MESH V0: AI-curated professional dinners for builders.

See `spec.md` for the product spec. See `plan.md` for the implementation plan.

## For users (attendees)

Paste the contents of `ONBOARD.md` into Claude Code on your machine.

## For the founder

After cloning, run:

    pip install -e ".[dev]"
    pytest

The `mesh-orchestrator` skill is in `skills/mesh-orchestrator/`. It runs on the founder laptop on Friday to compose tables for the Saturday dinner.
