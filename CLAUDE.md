# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

MESH V0: AI-curated professional dinners for builders in Bengaluru. The product reads what a user is building (from their local Claude Code session history), summarizes it into a 200-word trajectory, and matches them with 5 other builders for a Saturday-7pm dinner.

Anchor docs:
- `spec.md`: the V0 contract (vision, decision framework D1-D11, architecture, data schema, failure modes, verification, success criteria). The architectural rationale.
- `plans/`: numbered iterations, each one self-contained — see "Iterative plans workflow" below. Always work from the latest unexecuted plan.

Read `spec.md` first to understand the product. Then read the latest plan in `plans/` and the EXECUTION LOG appendices on prior plans to understand what's already been built and what hasn't worked. Every architectural decision is justified in the Decision Framework table in `spec.md`; if you find yourself wanting to revisit a choice, find it in D1-D11 first to see what alternatives were rejected and why.

## Hard constraints (these override defaults)

1. **Claude is the AI layer.** No external LLM APIs (no OpenAI, no embedding APIs, no third-party model providers). The user's local Claude does summarization. The founder's local Claude does matching. If a task seems to need an API call to anything other than GitHub, you have misunderstood the design. See D9 in `spec.md`.

2. **GitHub is the only datastore.** Two repos: this one (`mesh-skills`, public, contains code + docs + the paste-able onboarding prompt) and `mesh-data` (private, contains `users/<email>.md` and `networking-dinners/dinner-YYYY-MM-DD/table-N.md`). No Postgres, no Redis, no S3, no web app, no API server. See D8.

3. **Privacy is enforced by code, not policy.** The pre-push validator (`skills/mesh_trajectory/scripts/validate.py`) MUST refuse any field outside the locked 8-field schema. Never bypass it. Never add fields without updating `SCHEMA_FIELDS` in `schema.py` AND the schema section in `spec.md` AND a corresponding test that fails before the field is allowed. See D11 + the Privacy section in `spec.md`.

4. **Raw Claude Code conversations never leave the user's device.** Only the validated 8-field payload (which includes a 200-word trajectory body the user reviewed and edited) is uploaded. The extractor (`extract.py`) writes to `/tmp/mesh_corpus.txt` and that file must be deleted before the skill exits.

5. **Build only what's in the active plan.** Each iteration has its own plan in `plans/NN-*.md`. Don't pull V0.1+ ideas into the current iteration. If a task requires something out of scope, stop and ask — that's a signal to either close out the current plan or start the next one.

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

## Iterative plans workflow

We work iteration by iteration. Each iteration has its own plan file under `plans/`, numbered `01-`, `02-`, … The number is the order of authoring; once a plan is started it is **append-only** (do not rewrite history — append an EXECUTION LOG instead).

**Conventions:**

- **One plan per iteration.** A plan is "ready to execute in a single fresh Claude Code session". When scope grows beyond that, split into the next plan.
- **Latest unexecuted plan = your starting point.** When you open this repo, find the plan with no EXECUTION LOG appendix at the bottom. That is the active plan. If all plans have execution logs, ask the user before starting a new one.
- **Each plan is self-contained.** It must brief a fresh Claude that has never seen prior conversations. Reference earlier plans by filename when needed; do not assume the reader has the context.
- **Append, don't rewrite.** When an iteration completes (or stops), add an `# EXECUTION LOG (appended YYYY-MM-DD)` section at the bottom of that plan. Cover: task status (DONE / NOT DONE / SKIPPED + commit SHA), what worked, what didn't, hardenings beyond the original plan, mid-flight architectural changes, verification result, and open items handed off to the next plan.
- **Author the next plan only after the current one's execution log is written.** The next plan should reference what didn't work in the previous one and what's being deferred.

**Workflow at the start of a session:**

1. Read `CLAUDE.md` (this file) and `spec.md`.
2. `ls plans/` to see all iterations. Read each plan's first ~30 lines to get the gist; read the EXECUTION LOG of the most recent completed plan in full.
3. Pick the latest plan with no EXECUTION LOG. That's your work.
4. Use `superpowers:subagent-driven-development` (or inline execution if scope is small) to walk the plan task by task.
5. When done (or when stopping), append the EXECUTION LOG to the plan you executed, then optionally author the next plan.

**Workflow at the end of a session:**

1. Update the EXECUTION LOG of the active plan with everything that happened.
2. If the iteration produced learnings that change the next plan, write `plans/NN+1-*.md` now while the context is fresh.
3. Commit both files in one commit.

## Code layout (planned, see plans/01-v0-tdd-build.md File Structure for the full tree)

- `skills/mesh_trajectory/` (underscore for Python import; dashed name `mesh-trajectory` is a symlink for Claude Code skill discovery)
- `skills/mesh_orchestrator/` (same naming convention)
- `tests/` (pytest, mirrors `skills/`)
- `ONBOARD.md` (the paste-able prompt users run in their Claude Code)
- `schema.py` lives at `skills/mesh_trajectory/schema.py` and is the single source of truth for the 8 fields

## Naming convention (important)

Python packages use **underscores**: `skills/mesh_trajectory/`, `skills/mesh_orchestrator/`. Claude Code skill discovery expects **dashes**: `mesh-trajectory`, `mesh-orchestrator`. Bridge with a symlink inside `skills/`: `ln -s mesh_trajectory mesh-trajectory`. Always import via the underscore path; always reference the skill via the dashed name in `SKILL.md` frontmatter and in user-facing slash commands.

## Commands

```bash
# setup (one-time)
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# run all tests
.venv/bin/pytest

# run one test file
.venv/bin/pytest tests/test_validate.py -v

# run one test
.venv/bin/pytest tests/test_validate.py::test_extra_field_is_refused -v
```

Skill invocation (after install per `ONBOARD.md`):
- User-side: `/mesh-onboard`, `/mesh-sync`, `/mesh-check`, `/mesh-status`
- Founder-side: `/mesh-orchestrate <YYYY-MM-DD>` (defaults to next Saturday)

## How to extend safely

- **Adding a field to the schema**: update `SCHEMA_FIELDS` in `schema.py`, update the schema section in `spec.md`, add a failing test in `tests/test_validate.py`, then make it pass. Never edit one without the other two.
- **Changing the matching prompt**: edit `skills/mesh_orchestrator/prompts/compose.md`. The JSON output contract in `parse_response.py` is the contract; if you change the JSON shape, update `parse_response.py` AND its tests in the same commit.
- **Adding a slash command**: register it in the relevant `SKILL.md` and document it in this file's Commands section. Keep flows in `SKILL.md` (instructions for Claude); keep deterministic logic in `scripts/` (Python with pytest coverage).
- **Touching the failure-mode list in spec.md**: every failure mode must have a mitigation that is either implemented in V0 code or explicitly deferred to V0.1. Don't add a failure mode without saying which.

## TDD discipline

Every task in every plan follows: write failing test -> run, see it fail -> implement minimally -> run, see pass -> commit. Do not skip steps. Do not batch. Plans are structured so each task produces a green test suite and a single commit. The synthetic-test trap from iteration 1 (passing tests against fake data shape that didn't match real Claude Code session files) is the cautionary tale: when reading user-machine data, write at least one test that runs against a real fixture.

## Out of scope reminders

- No web app, no React, no frontend framework. The product surface is Claude Code slash commands.
- No email send, no SMS, no WhatsApp API. The founder messages the cohort manually via WhatsApp; users see invites via `/mesh-check`.
- No embeddings in V0. Claude reads the raw 200-word summaries and reasons over them. The `embedding` field is reserved in the schema but always `null` in V0.
- No multi-city. `city` is hard-filtered to "Bengaluru" in `validate.py`.
- No host marketplace, no payments, no agent-native API. All deferred to V0.1+.

## Current status

Always check `plans/` for the latest iteration. As of the most recent commit, iteration 1 (`plans/01-v0-tdd-build.md`) is complete and has an EXECUTION LOG documenting what shipped + what blocked. The active plan is the most recent one without an EXECUTION LOG appendix.

Build window references in older plans are anchored to specific dates (launch event 2026-05-01, dinner #1 on 2026-05-09); treat those as targets that may have shifted — read the EXECUTION LOG appendices to confirm current dates.
