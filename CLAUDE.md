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
USER MACHINE                              CENTRAL                  DINNER
mesh-trajectory skill   --git push-->     mesh-data repo  <--push-- mesh-orchestrator skill
  /mesh-trajectory onboard                users/*.md                  /mesh-orchestrate
  /mesh-trajectory sync                   networking-dinners/*.md     (founder laptop, Friday)
  /mesh-trajectory check (renders invite)
```

The user-side skill extracts -> summarizes (via local Claude) -> validates -> pushes. The founder-side skill loads -> asks Claude to compose tables -> validates JSON -> writes invites -> pushes. The user-side skill's `/mesh-trajectory check` pulls and renders.

## Iterative plans workflow

We work iteration by iteration. Each iteration has its own plan file under `plans/`, numbered `01-`, `02-`, … The number is the order of authoring; once a plan is started it is **append-only** (do not rewrite history — append an EXECUTION LOG instead).

### START-OF-SESSION DECISION TREE (do this FIRST, every session)

```
                    NEW CONVERSATION OPENS
                              │
                              ▼
              Read CLAUDE.md + spec.md  (you are here)
                              │
                              ▼
                       `ls plans/`
                              │
                              ▼
              Look at the HIGHEST-NUMBERED plan
                              │
              ┌───────────────┴───────────────┐
              │                               │
       Has EXECUTION LOG                Has NO EXECUTION LOG
       at the bottom?                   at the bottom?
              │                               │
        ✓ COMPLETE                       ⏳ INCOMPLETE
              │                               │
              ▼                               ▼
   ┌────────────────────────┐    ┌─────────────────────────┐
   │ Surface to the user:    │    │ Read this plan IN FULL  │
   │  - what shipped         │    │ + read the EXECUTION    │
   │  - what's open          │    │ LOG of the previous     │
   │  - propose next plan    │    │ plan (if any).          │
   │  OR ask "what next?"    │    │                         │
   │                         │    │ This plan IS your work. │
   │ Do NOT start coding     │    │ Walk it task by task.   │
   │ until the user picks    │    │                         │
   │ a direction.            │    │ When done, append the   │
   └────────────────────────┘    │ EXECUTION LOG. Then      │
                                  │ ask user about next.    │
                                  └─────────────────────────┘
```

**The two paths in plain words:**

**Path A — latest plan is COMPLETE (has EXECUTION LOG appendix):**
  → No active work. Read the EXECUTION LOG to know what shipped and what's open.
  → Surface a one-paragraph summary to the user + propose 1-3 candidate next plans (informed by the "Open items handed off" section of the most recent log).
  → ASK before authoring a new plan or starting code. Do not assume.

**Path B — latest plan is INCOMPLETE (no EXECUTION LOG appendix):**
  → That plan IS your work. No question to ask the user; just go.
  → Read the plan in full + the EXECUTION LOG of the previous plan (if any) for context on prior decisions and pitfalls.
  → Use `superpowers:subagent-driven-development` (or inline if small) to walk the tasks.
  → When the iteration ends — whether you finished, partially finished, or hit a blocker — append an EXECUTION LOG to this plan covering: task status (DONE / PARTIAL / BLOCKED + commit SHA), what worked, what didn't, hardenings beyond the original plan, mid-flight architectural changes, verification result, and open items handed off to the next plan.
  → Then ask the user whether to author the next plan now.

### END-OF-SESSION CHECKLIST

1. The active plan has an EXECUTION LOG appendix that reflects everything that happened in this session.
2. If the iteration produced learnings that need a follow-on plan, `plans/NN+1-*.md` is written while the context is fresh.
3. Both files are committed in one commit.

### Conventions (read once)

- **One plan per iteration.** A plan is "ready to execute in a single fresh Claude Code session". When scope grows beyond that, split into the next plan.
- **Each plan is self-contained.** It must brief a fresh Claude that has never seen prior conversations. Reference earlier plans by filename when needed; do not assume the reader has the context.
- **Append, don't rewrite.** EXECUTION LOG is the only structured way to record what happened. Never edit a plan's body after execution starts.
- **Author the next plan only after the current one's execution log is written.** The next plan should reference what didn't work in the previous one and what's being deferred.

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
- User-side: `/mesh-trajectory onboard`, `/mesh-trajectory sync`, `/mesh-trajectory check`, `/mesh-trajectory status` (single registered command, action arg routes to flow)
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
- No email send, no SMS, no WhatsApp API. The founder messages the cohort manually via WhatsApp; users see invites via `/mesh-trajectory check`.
- No embeddings in V0. Claude reads the raw 200-word summaries and reasons over them. The `embedding` field is reserved in the schema but always `null` in V0.
- No multi-city. `city` is hard-filtered to "Bengaluru" in `validate.py`.
- No host marketplace, no payments, no agent-native API. All deferred to V0.1+.

## Current status

Always check `plans/` for the latest iteration. As of the most recent commit, iteration 1 (`plans/01-v0-tdd-build.md`) is complete and has an EXECUTION LOG documenting what shipped + what blocked. The active plan is the most recent one without an EXECUTION LOG appendix.

Build window references in older plans are anchored to specific dates (launch event 2026-05-01, dinner #1 on 2026-05-09); treat those as targets that may have shifted — read the EXECUTION LOG appendices to confirm current dates.
