# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

MESH V0: AI-curated professional dinners for builders in Bengaluru. The product reads what a user is building (from their local Claude Code session history), summarizes it into a 200-word trajectory, and matches them with 5 other builders for a Saturday-7pm dinner.

This repo (`mesh-skills`) is currently **pre-code**. The artifacts that exist are:
- `spec.md`: the V0 contract (vision, decision framework D1-D11, architecture, data schema, failure modes, verification, success criteria).
- `plan.md`: the bite-sized TDD implementation plan (tasks T0-T13) for a 7-day sprint ending in a 30-person launch event on 2026-05-01 and dinner #1 on Saturday 2026-05-09.

Read `spec.md` first, then `plan.md`. Every architectural decision is justified in the Decision Framework table in `spec.md`; if you find yourself wanting to revisit a choice, find it in D1-D11 first to see what alternatives were rejected and why.

## Hard constraints (these override defaults)

1. **Claude is the AI layer.** No external LLM APIs (no OpenAI, no embedding APIs, no third-party model providers). The user's local Claude does summarization. The founder's local Claude does matching. If a task seems to need an API call to anything other than GitHub, you have misunderstood the design. See D9 in `spec.md`.

2. **GitHub is the only datastore.** Two repos: this one (`mesh-skills`, public, contains code + docs + the paste-able onboarding prompt) and `mesh-data` (private, contains `users/<email>.md` and `networking-dinners/dinner-YYYY-MM-DD/table-N.md`). No Postgres, no Redis, no S3, no web app, no API server. See D8.

3. **Privacy is enforced by code, not policy.** The pre-push validator (`skills/mesh_trajectory/scripts/validate.py`) MUST refuse any field outside the locked 8-field schema. Never bypass it. Never add fields without updating `SCHEMA_FIELDS` in `schema.py` AND the schema section in `spec.md` AND a corresponding test that fails before the field is allowed. See D11 + the Privacy section in `spec.md`.

4. **Raw Claude Code conversations never leave the user's device.** Only the validated 8-field payload (which includes a 200-word trajectory body the user reviewed and edited) is uploaded. The extractor (`extract.py`) writes to `/tmp/mesh_corpus.txt` and that file must be deleted before the skill exits.

5. **Build only what's in the plan.** The spec lists what is out of scope for V0 (embeddings, velocity matching, hosts marketplace, agent API, web app, plugin platform, payments, multi-city, recursive memory consolidation). Do not build any of these in V0. If a task requires one, stop and ask.

## Architecture in one diagram

Two Claude agents communicating through a single git repo:

```
USER MACHINE                            CENTRAL                  DINNER
mesh-trajectory skill   --git push-->   mesh-data repo  <--push-- mesh-orchestrator skill
  /mesh-onboard                         users/*.md                  /mesh-orchestrate
  /mesh-sync                            networking-dinners/*.md     (founder laptop, Friday)
  /mesh-check (renders invite)
```

The user-side skill extracts -> summarizes (via local Claude) -> validates -> pushes. The founder-side skill loads -> asks Claude to compose tables -> validates JSON -> writes invites -> pushes. The user-side skill's `/mesh-check` pulls and renders.

## Code layout (planned, see plan.md File Structure for the full tree)

- `skills/mesh_trajectory/` (underscore for Python import; dashed name `mesh-trajectory` is a symlink for Claude Code skill discovery)
- `skills/mesh_orchestrator/` (same naming convention)
- `tests/` (pytest, mirrors `skills/`)
- `ONBOARD.md` (the paste-able prompt users run in their Claude Code)
- `schema.py` lives at `skills/mesh_trajectory/schema.py` and is the single source of truth for the 8 fields

## Naming convention (important)

Python packages use **underscores**: `skills/mesh_trajectory/`, `skills/mesh_orchestrator/`. Claude Code skill discovery expects **dashes**: `mesh-trajectory`, `mesh-orchestrator`. Bridge with a symlink inside `skills/`: `ln -s mesh_trajectory mesh-trajectory`. Always import via the underscore path; always reference the skill via the dashed name in `SKILL.md` frontmatter and in user-facing slash commands.

## Commands

The repo has no code yet. Once Task T0 from `plan.md` is complete:

```bash
# setup
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# run all tests
pytest

# run one test file
pytest tests/test_validate.py -v

# run one test
pytest tests/test_validate.py::test_extra_field_is_refused -v
```

Skill invocation (after install per `ONBOARD.md`):
- User-side: `/mesh-onboard`, `/mesh-sync`, `/mesh-check`, `/mesh-status`
- Founder-side: `/mesh-orchestrate <YYYY-MM-DD>` (defaults to next Saturday)

## How to extend safely

- **Adding a field to the schema**: update `SCHEMA_FIELDS` in `schema.py`, update the schema section in `spec.md`, add a failing test in `tests/test_validate.py`, then make it pass. Never edit one without the other two.
- **Changing the matching prompt**: edit `skills/mesh_orchestrator/prompts/compose.md`. The JSON output contract in `parse_response.py` is the contract; if you change the JSON shape, update `parse_response.py` AND its tests in the same commit.
- **Adding a slash command**: register it in the relevant `SKILL.md` and document it in this file's Commands section. Keep flows in `SKILL.md` (instructions for Claude); keep deterministic logic in `scripts/` (Python with pytest coverage).
- **Touching the failure-mode list in spec.md**: every failure mode must have a mitigation that is either implemented in V0 code or explicitly deferred to V0.1. Don't add a failure mode without saying which.

## TDD discipline (per plan.md)

Every task in `plan.md` follows: write failing test -> run, see it fail -> implement minimally -> run, see pass -> commit. Do not skip steps. Do not batch. The plan is structured so each task produces a green test suite and a single commit.

## Out of scope reminders

- No web app, no React, no frontend framework. The product surface is Claude Code slash commands.
- No email send, no SMS, no WhatsApp API. The founder messages the cohort manually via WhatsApp; users see invites via `/mesh-check`.
- No embeddings in V0. Claude reads the raw 200-word summaries and reasons over them. The `embedding` field is reserved in the schema but always `null` in V0.
- No multi-city. `city` is hard-filtered to "Bengaluru" in `validate.py`.
- No host marketplace, no payments, no agent-native API. All deferred to V0.1+.

## Current status (as of 2026-04-25)

Pre-code. Next action is Task T0 in `plan.md`: initialize git, write `pyproject.toml`, create the private `mesh-data` repo. The 7-day build window ends on Friday 2026-05-01 with the launch event; dinner #1 is Saturday 2026-05-09.
