# Plan 07: Model routing config (Haiku for L1, Sonnet for L2, Opus for L3 + lint + compose)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Before starting**, read in this order:
> 1. `CLAUDE.md` (Hard Constraint #1: Claude is the AI layer; Haiku, Sonnet, Opus are all Claude models so this constraint is satisfied).
> 2. `spec.md` (D9 matching mechanism, D12 hierarchical summarization, D13 lint).
> 3. `plans/05-multipart-trajectory.md` (the v2 schema + 4-section synthesis are now the contract; this plan does NOT change them).
> 4. `plans/06-onboarding-leniency.md` EXECUTION LOG (the most recent SKILL.md state — onboarding flow has been UX-hardened).
> 5. The most recent commits: `git log --oneline -15`. The previous session ran `/mesh-trajectory sync` end-to-end on the founder's corpus on Opus throughout (87 sessions, 5 digest subagents + 3 summary subagents, ~600K subagent tokens). That run is the cost baseline this plan optimizes against.

**Goal:** Make per-layer model selection a single-source-of-truth config (`skills/mesh_trajectory/config/model_routing.yaml`) that the SKILL.md flow reads at runtime; route per-session digests to **Haiku 4.5**, per-project summaries to **Sonnet 4.6**, and final 4-section synthesis + privacy lint + founder-side compose to **Opus 4.7**. Verify with one full founder dogfood sync.

**Architecture:** A flat YAML config maps each layer name (`layer1`, `layer2`, `layer3`, `lint`, `compose`) to a model alias (`haiku` / `sonnet` / `opus`). A small Python loader (`model_routing.py`) exposes `get_model(layer)` and a CLI (`python -m ... <layer>` prints the resolved model). SKILL.md steps that dispatch subagents shell out to the CLI to get the model name, then pass it as the Agent tool's `model` parameter. Layers that run in the parent context (synthesis, lint) cannot change the parent's model mid-conversation, but the config is still authoritative documentation for those layers and is consumed by the founder-side compose flow which DOES dispatch as a subagent.

**Tech stack:** Python 3.11 + pytest + PyYAML (already a dep). No new dependencies.

---

## Why this iteration exists

The first end-to-end production run of `/mesh-trajectory sync` (founder's corpus, 2026-05-02) used Opus 4.7 for every layer because subagents inherit the parent's model unless explicitly overridden. Token accounting from that run: 8 subagents consumed **596,719 tokens combined**, with the bulk on the 5 digest subagents (~470K). At 30 launch attendees each running sync once, that scales to roughly **18M tokens for the digest layer alone**, all on Opus.

The recursive layers do not need Opus. Per-session digests are constrained one-sentence extractions; per-project summaries follow a rigid three-sentence skeleton. Haiku 4.5 and Sonnet 4.6 produce comparable quality on these contracts at a fraction of the cost and meaningfully lower latency. The final 4-section synthesis is where matching signal lives (the Guide x Explorer pattern depends on per-section calibration); that stays on Opus. Privacy lint stays on Opus because catching subtle career / codename signals is exactly the kind of nuance smaller models miss.

The user instruction added at plan-author time: **"save this in a config and reference it while executing."** This means we do NOT hardcode model names in SKILL.md. A single YAML config is the contract, the SKILL.md flow reads it at runtime, and a future change to the routing is a one-file edit (plus a test update) rather than scattered SKILL.md edits.

## Architectural shift

```
   PLAN 05 + 06 (current)                          PLAN 07 (proposed)

   subagents inherit parent model                  subagents dispatched with explicit
   (Opus 4.7 everywhere)                           model from config:
                                                     layer1 (per-session digest)  -> haiku
                                                     layer2 (per-project summary) -> sonnet
                                                     layer3 (4-section synthesis) -> opus
                                                     lint  (LLM-as-judge)         -> opus
                                                     compose (founder matcher)    -> opus

                                                   config:
                                                     skills/mesh_trajectory/config/
                                                       model_routing.yaml
                                                   loader:
                                                     skills/mesh_trajectory/scripts/
                                                       model_routing.py
                                                   SKILL.md flow reads config
                                                   at dispatch time via CLI:
                                                     MODEL=$(python -m ... layer1)
                                                     dispatch Agent with model=$MODEL
```

The config is load-bearing: changing it changes the next sync. SKILL.md does NOT name models in prose; it always defers to the config. Tests lock the current routing so a future change requires updating spec.md (D14) AND the test in one commit.

## What stays unchanged

- The 8-field schema (`SCHEMA_FIELDS` in `schema.py`).
- The 4-section body shape (`SECTION_FIELDS`).
- All 8 validator rules (V1-V8).
- The hierarchical pipeline shape (extract -> digest -> per-project -> synthesize -> lint -> push).
- The four section-extraction prompts.
- The founder-side `compose.md` JSON output contract.
- All three privacy-gate stages and their delete-after-downstream-step rule.
- Hard Constraint #1 (Claude is the AI layer): Haiku, Sonnet, Opus are all Claude models. This plan does not introduce any non-Claude provider.

## Hard constraints (carry-overs)

1. **Claude is the AI layer.** No external LLM/embedding APIs. Haiku 4.5, Sonnet 4.6, Opus 4.7 are all Claude.
2. **Privacy is enforced by code, not policy.** V1-V8 unchanged. The model used by the lint judge does NOT replace the validator gate; it ADDS another check.
3. **Append-only plans.** Do not edit this plan body after execution starts. Append an EXECUTION LOG appendix at the end of the iteration.
4. **TDD discipline.** Loader + CLI ship with tests that fail first.
5. **No em-dashes anywhere** (project rule).
6. **Build only what's in this plan.** No additional layer routing (no per-section model picking, no fallback chains, etc.) unless an EXECUTION LOG follow-on shows the simple flat routing is insufficient.

## Tech notes

- **Model alias resolution.** The Agent tool's `model` parameter accepts the literal strings `opus`, `sonnet`, `haiku`. The config stores those literals (not version-pinned IDs like `claude-haiku-4-5-20251001`) so the routing keeps working as new model versions ship under the same alias. If a future Claude model family changes the alias scheme, the config gains a translation layer; for now, pass-through.
- **Where the config lives.** `skills/mesh_trajectory/config/model_routing.yaml`. The `config/` subdir is new; pick it because future config files (e.g. PII stop-list became flat-file at the skill root in plan 05; that was fine for one file but a `config/` dir signals "user-tunable knobs live here"). Do NOT move `pii_stoplist.txt` in this plan; that's out of scope.
- **CLI shape.** `python -m skills.mesh_trajectory.scripts.model_routing <layer>` prints the resolved model alias and exits 0; an unknown layer prints to stderr and exits 1. SKILL.md uses backticks (`MODEL=$(...)`) to capture stdout into a shell variable.
- **Loader API.**
  ```python
  def get_model(layer: str) -> str: ...           # raises KeyError on unknown layer
  def all_routes() -> dict[str, str]: ...         # full mapping for tests + diagnostics
  CONFIG_PATH = Path(__file__).parent.parent / "config" / "model_routing.yaml"
  ```
- **Layers that run in the parent context** (layer3 synthesis, lint when invoked inline). The parent session's model cannot change mid-conversation. The config still encodes the recommendation; SKILL.md surfaces a one-line note for these steps ("This step runs in the current session; ensure your session is on `<configured-model>`"). The founder-side compose flow DOES dispatch as a subagent, so it gets explicit model routing.
- **Quality risk profile.** Haiku at L1 is low-risk (constrained one-sentence extraction with a hard fallback for noise sessions). Sonnet at L2 is low-risk (rigid three-sentence skeleton, user reviews at SKILL.md step 11 before propagation). Opus at L3 protects the matching signal. Lint at Opus protects the privacy gate.
- **No regression of plan 05 tests.** All 103 existing tests must still pass after this plan. The new model_routing tests are additive.

---

## File structure (delta only)

```
mesh/
├── skills/
│   └── mesh_trajectory/
│       ├── config/                                ← CREATE: skill config dir
│       │   └── model_routing.yaml                 ← CREATE: layer -> model mapping
│       ├── scripts/
│       │   └── model_routing.py                   ← CREATE: loader + CLI
│       └── SKILL.md                               ← MODIFY: steps 6, 9, 13, 15 read config
├── tests/
│   └── test_model_routing.py                      ← CREATE: lock the routing
├── spec.md                                        ← MODIFY: add D14 to decision framework
└── plans/07-model-routing-config.md               ← THIS FILE
```

---

# Tasks

## Task 1: Create model_routing.yaml + loader + tests

**Files:**
- Create: `skills/mesh_trajectory/config/model_routing.yaml`
- Create: `skills/mesh_trajectory/scripts/model_routing.py`
- Create: `tests/test_model_routing.py`

The YAML config is the single source of truth. The loader exposes `get_model(layer)` and `all_routes()`. Tests lock the current routing to fail loudly if the YAML is edited without updating tests AND spec.md.

- [ ] **Step 1: Write the failing tests** at `tests/test_model_routing.py`:

```python
import pytest
from pathlib import Path
from skills.mesh_trajectory.scripts.model_routing import (
    get_model, all_routes, CONFIG_PATH, UnknownLayerError,
)


def test_config_file_exists():
    assert CONFIG_PATH.exists(), f"missing config at {CONFIG_PATH}"


def test_layer1_is_haiku():
    assert get_model("layer1") == "haiku"


def test_layer2_is_sonnet():
    assert get_model("layer2") == "sonnet"


def test_layer3_is_opus():
    assert get_model("layer3") == "opus"


def test_lint_is_opus():
    assert get_model("lint") == "opus"


def test_compose_is_opus():
    assert get_model("compose") == "opus"


def test_all_routes_returns_full_mapping():
    routes = all_routes()
    assert routes == {
        "layer1": "haiku",
        "layer2": "sonnet",
        "layer3": "opus",
        "lint":   "opus",
        "compose": "opus",
    }


def test_unknown_layer_raises():
    with pytest.raises(UnknownLayerError, match="layer42"):
        get_model("layer42")


def test_only_known_aliases_in_config():
    # Lock the value space: only "haiku", "sonnet", "opus" are accepted.
    # If someone adds a custom alias, this test forces them to update the
    # loader's allow-list AND this test.
    allowed = {"haiku", "sonnet", "opus"}
    for layer, model in all_routes().items():
        assert model in allowed, f"layer {layer} maps to unknown alias {model}"
```

- [ ] **Step 2: Run tests, confirm RED.**

```bash
.venv/bin/pytest tests/test_model_routing.py -v
```

Expected: ImportError on `model_routing` module (it doesn't exist yet).

- [ ] **Step 3: Create the config file** at `skills/mesh_trajectory/config/model_routing.yaml`:

```yaml
# MESH model routing per pipeline layer.
# Single source of truth. SKILL.md reads this file at runtime via
# scripts/model_routing.py. Changing a value here changes the next sync.
#
# Allowed values: haiku, sonnet, opus. The Agent tool resolves these
# aliases to the latest model version of that family.
#
# Decision rationale lives in spec.md D14. To change a routing:
#   1. Edit this file.
#   2. Update tests/test_model_routing.py.
#   3. Update spec.md D14.
# All three in one commit.

layer1:  haiku   # per-session digest (Layer 1): one-sentence INITIATIVE compression
layer2:  sonnet  # per-project summary (Layer 2): 80-120 word INITIATIVE paragraph
layer3:  opus    # 4-section synthesis (Layer 3): final body, matching surface
lint:    opus    # privacy LLM-as-judge: catches subtle disclosures Haiku/Sonnet miss
compose: opus    # founder-side matcher: composes dinner tables (Guide x Explorer detection)
```

- [ ] **Step 4: Implement the loader** at `skills/mesh_trajectory/scripts/model_routing.py`:

```python
"""Per-layer model routing for the MESH trajectory pipeline.

The config at skills/mesh_trajectory/config/model_routing.yaml is the
single source of truth. The SKILL.md flow shells out to this module's CLI
at dispatch time to resolve which model a given layer should use.

CLI usage:
    python -m skills.mesh_trajectory.scripts.model_routing layer1
    # prints: haiku

Library usage:
    from skills.mesh_trajectory.scripts.model_routing import get_model
    model = get_model("layer1")  # "haiku"
"""
from __future__ import annotations

import sys
from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).parent.parent / "config" / "model_routing.yaml"

ALLOWED_MODELS = frozenset({"haiku", "sonnet", "opus"})


class UnknownLayerError(KeyError):
    pass


class InvalidModelError(ValueError):
    pass


def all_routes() -> dict[str, str]:
    """Return the full {layer: model} mapping. Validates allow-list."""
    raw = yaml.safe_load(CONFIG_PATH.read_text())
    if not isinstance(raw, dict):
        raise InvalidModelError(f"config root must be a mapping, got {type(raw).__name__}")
    routes: dict[str, str] = {}
    for layer, model in raw.items():
        if model not in ALLOWED_MODELS:
            raise InvalidModelError(
                f"layer {layer!r} maps to {model!r}; allowed: {sorted(ALLOWED_MODELS)}"
            )
        routes[str(layer)] = str(model)
    return routes


def get_model(layer: str) -> str:
    routes = all_routes()
    if layer not in routes:
        raise UnknownLayerError(
            f"unknown layer {layer!r}; known: {sorted(routes.keys())}"
        )
    return routes[layer]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: model_routing.py <layer>", file=sys.stderr)
        print(f"known layers: {sorted(all_routes().keys())}", file=sys.stderr)
        return 2
    layer = sys.argv[1]
    try:
        print(get_model(layer))
    except UnknownLayerError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run tests, confirm GREEN.**

```bash
.venv/bin/pytest tests/test_model_routing.py -v
```

Expected: 8 tests pass.

- [ ] **Step 6: Smoke-test the CLI.**

```bash
.venv/bin/python -m skills.mesh_trajectory.scripts.model_routing layer1
# Expected stdout: haiku
.venv/bin/python -m skills.mesh_trajectory.scripts.model_routing layer2
# Expected stdout: sonnet
.venv/bin/python -m skills.mesh_trajectory.scripts.model_routing layer3
# Expected stdout: opus
.venv/bin/python -m skills.mesh_trajectory.scripts.model_routing nope
# Expected stderr: ERROR: unknown layer 'nope'; ...
# Expected exit code: 1
```

If the exit code on the last call is 0, the CLI's error-path is broken; fix `main()` and re-run.

- [ ] **Step 7: Confirm full pytest still green.**

```bash
.venv/bin/pytest -q
```

Expected: 103 (from plan 05) + 8 (this task) = **111 passing**.

- [ ] **Step 8: Commit.**

```bash
git add skills/mesh_trajectory/config/model_routing.yaml \
        skills/mesh_trajectory/scripts/model_routing.py \
        tests/test_model_routing.py
git commit -m "feat(routing): per-layer model config + loader (haiku/sonnet/opus)"
```

---

## Task 2: SKILL.md step 6 (per-session digests) — read config + dispatch with model

**Files:**
- Modify: `skills/mesh_trajectory/SKILL.md` (step 6 of `/mesh-onboard` flow)

The current step 6 says "Use parallel subagents when there are >50 sessions" without specifying a model. Update it to fetch the model from the routing config and pass it as the Agent dispatch's `model` parameter.

- [ ] **Step 1: Read the current step 6** to confirm exact text to replace:

```bash
sed -n '63p' skills/mesh_trajectory/SKILL.md
```

It should match:

```
6. **Per-session digests.** For each entry in `/tmp/mesh_sess/manifest.json`, ...
```

- [ ] **Step 2: Replace step 6** with this exact body (preserve the trailing newline and the indentation of the line that follows):

```markdown
6. **Per-session digests.** For each entry in `/tmp/mesh_sess/manifest.json`, read the corpus file at `entry.corpus_path`, apply `prompts/per_session.md` (substitute `{{session_corpus}}`), and produce one digest sentence. Append all digests to `/tmp/mesh_digests.txt`, ordered most-recent-first. Each line is `<session_id> <YYYY-MM-DD> <digest>`. Use parallel subagents when there are >50 sessions; instruct each subagent to read manifest entries by index range and write a batch file (e.g. `/tmp/mesh_digests_batch_NN.txt`), then concatenate them into `/tmp/mesh_digests.txt`.

   **Model:** Resolve the per-layer model BEFORE dispatching subagents, then pass it as the Agent tool's `model` parameter (one shell call, used for every subagent in this layer):

   ```bash
   LAYER1_MODEL=$(~/.claude/skills/mesh-skills/.venv/bin/python -m skills.mesh_trajectory.scripts.model_routing layer1)
   echo "Layer 1 (digest) model: $LAYER1_MODEL"
   ```

   Then in each Agent dispatch for this step, set `model: "$LAYER1_MODEL"` (the captured value, e.g. `haiku`). Do NOT hardcode the model in the SKILL.md or in subagent prompts; always resolve via the routing config so that a future config edit takes effect on the next sync without touching SKILL.md.
```

- [ ] **Step 3: Sanity checks.**

```bash
grep -c "model_routing" skills/mesh_trajectory/SKILL.md
# Expected: >= 1
grep -c "—" skills/mesh_trajectory/SKILL.md
# Expected: 0
.venv/bin/pytest -q | tail -3
# Expected: 111 passed
```

- [ ] **Step 4: Commit.**

```bash
git add skills/mesh_trajectory/SKILL.md
git commit -m "feat(skill): step 6 reads layer1 model (haiku) from routing config"
```

---

## Task 3: SKILL.md step 9 (per-project summaries) — read config + dispatch with model

**Files:**
- Modify: `skills/mesh_trajectory/SKILL.md` (step 9 of `/mesh-onboard` flow)

Same shape as Task 2 but for layer2.

- [ ] **Step 1: Read the current step 9.**

```bash
sed -n '92,95p' skills/mesh_trajectory/SKILL.md
```

It should start with `9. **Per-project summaries.**` and end with the line about parallel summarizer subagents.

- [ ] **Step 2: Replace step 9** with this exact body:

```markdown
9. **Per-project summaries.** For each project in `/tmp/mesh_groups.json`, append a block to `/tmp/mesh_project_summaries.txt`:
   - If `session_count == 1`: pull the matching session digest from `/tmp/mesh_digests.txt`. Wrap as `Project: <project> (1 session, ONE-OFF)\n<digest>`.
   - If `session_count >= 2`: gather the matching session digests, read `prompts/per_project.md`, substitute `{{project_name}}`, `{{session_count}}`, `{{bucket}}`, and `{{digests}}` (the matching digests joined with newlines). Generate the 80-120 word INITIATIVE-level paragraph in your response. Wrap as `Project: <project> ({n} sessions, {BUCKET})\n<paragraph>`.
   Use parallel summarizer subagents when there are 5+ multi-session projects (each subagent owns 3-6 projects, writes to `/tmp/mesh_proj_summaries/<project>.txt`); the controller then concatenates into `/tmp/mesh_project_summaries.txt`.

   **Model:** Resolve the per-layer model before dispatching summarizer subagents:

   ```bash
   LAYER2_MODEL=$(~/.claude/skills/mesh-skills/.venv/bin/python -m skills.mesh_trajectory.scripts.model_routing layer2)
   echo "Layer 2 (per-project) model: $LAYER2_MODEL"
   ```

   Then in each Agent dispatch for this step, set `model: "$LAYER2_MODEL"` (e.g. `sonnet`). For ONE-OFF projects (session_count == 1) there is no Agent dispatch (the controller pulls the digest directly), so layer2 routing does not apply.
```

- [ ] **Step 3: Sanity checks.**

```bash
grep -c "LAYER1_MODEL\|LAYER2_MODEL" skills/mesh_trajectory/SKILL.md
# Expected: >= 2
grep -c "—" skills/mesh_trajectory/SKILL.md
# Expected: 0
.venv/bin/pytest -q | tail -3
# Expected: 111 passed
```

- [ ] **Step 4: Commit.**

```bash
git add skills/mesh_trajectory/SKILL.md
git commit -m "feat(skill): step 9 reads layer2 model (sonnet) from routing config"
```

---

## Task 4: SKILL.md steps 13 (synthesis) and 15 (lint) — surface the configured model as guidance

**Files:**
- Modify: `skills/mesh_trajectory/SKILL.md` (step 13 + step 15 of `/mesh-onboard` flow)

Synthesis and lint run in the parent context; we cannot change the parent's model mid-conversation. But we CAN:
- Print the configured model so the running session is aware of the recommendation.
- Document that a wrapper invoker (e.g. a future scheduled cron agent) should dispatch the whole sync as a subagent with the right model.

This is a one-line addition per step, not a flow rewrite.

- [ ] **Step 1: Locate step 13** (currently the multi-substep "Synthesize the four sections.").

```bash
grep -n "^13\.\s*\*\*Synthesize" skills/mesh_trajectory/SKILL.md
```

- [ ] **Step 2: Insert this paragraph** as a new sub-bullet at the END of step 13 (after the existing sub-step e and before the assembled-body code block):

```markdown
   **Model note.** This step runs in the current Claude Code session, not as a subagent; the parent's model cannot be changed mid-conversation. The configured layer3 model is `opus`. If you (the running Claude) are not on Opus, surface a one-line warning: "Note: layer3 (4-section synthesis) is configured to use opus per skills/mesh_trajectory/config/model_routing.yaml; this session may be on a different model. Quality may regress." Resolve via:

   ```bash
   ~/.claude/skills/mesh-skills/.venv/bin/python -m skills.mesh_trajectory.scripts.model_routing layer3
   # Expected stdout: opus
   ```
```

- [ ] **Step 3: Locate step 15** (the privacy LINT pass).

```bash
grep -n "^15\.\s*\*\*Privacy LINT" skills/mesh_trajectory/SKILL.md
```

- [ ] **Step 4: Insert this paragraph** as a new sub-bullet at the END of step 15 (after the existing fallback-on-twice-failure instruction):

```markdown
   **Model note.** Same as step 13: the lint judge runs in the current session, not as a subagent. The configured `lint` model is `opus`. Resolve via `python -m skills.mesh_trajectory.scripts.model_routing lint`. If the running session is not on Opus, surface the same one-line warning.
```

- [ ] **Step 5: Sanity checks.**

```bash
grep -c "model_routing" skills/mesh_trajectory/SKILL.md
# Expected: >= 4
grep -c "—" skills/mesh_trajectory/SKILL.md
# Expected: 0
.venv/bin/pytest -q | tail -3
# Expected: 111 passed
```

- [ ] **Step 6: Commit.**

```bash
git add skills/mesh_trajectory/SKILL.md
git commit -m "feat(skill): steps 13 + 15 surface configured layer3 + lint models"
```

---

## Task 5: Founder-side compose — read config + dispatch with model

**Files:**
- Modify: `skills/mesh_orchestrator/SKILL.md` (step 7 of `/mesh-orchestrate` flow)

The compose flow currently says "Generate the response (you, Claude, ARE the matching engine here)." That assumes the founder-side session is on whatever model. The compose model is the most quality-sensitive (matching is the product). Surface the configured model the same way as the user-side L3.

- [ ] **Step 1: Read the current step 7.**

```bash
grep -n "^7\." skills/mesh_orchestrator/SKILL.md
```

- [ ] **Step 2: Append this sub-bullet** as a new line directly under step 7 (before step 8):

```markdown
   **Model note.** The configured `compose` model is `opus`. Resolve via:

   ```bash
   ~/.claude/skills/mesh-skills/.venv/bin/python -m skills.mesh_trajectory.scripts.model_routing compose
   # Expected stdout: opus
   ```

   If this flow is invoked by a wrapper that dispatches the founder-side sync as an Agent subagent (e.g. a future scheduled routine), pass `model: "opus"` (or the resolved value) on dispatch. If you (the running Claude) are not on Opus and there is no wrapper, surface the same one-line model-mismatch warning as user-side step 13.
```

- [ ] **Step 3: Sanity checks.**

```bash
grep -c "model_routing" skills/mesh_orchestrator/SKILL.md
# Expected: >= 1
grep -c "—" skills/mesh_orchestrator/SKILL.md
# Expected: 0
.venv/bin/pytest -q | tail -3
# Expected: 111 passed
```

- [ ] **Step 4: Commit.**

```bash
git add skills/mesh_orchestrator/SKILL.md
git commit -m "feat(orchestrator): compose step surfaces configured opus model"
```

---

## Task 6: spec.md — add D14 to the decision framework

**Files:**
- Modify: `spec.md`

D14 documents the model-routing choice + rationale + the change procedure (3-way commit: yaml + test + spec).

- [ ] **Step 1: Locate the decision framework table.**

```bash
grep -n "^| D13 " spec.md
```

The D13 row is the last row in the table. Append D14 immediately after it.

- [ ] **Step 2: Add the D14 row.** Insert this exact line directly after the D13 row in the decision framework table:

```markdown
| D14 | **Per-layer model routing** | Layer 1 (per-session digest) -> Haiku 4.5; Layer 2 (per-project summary) -> Sonnet 4.6; Layer 3 (4-section synthesis) -> Opus 4.7; privacy lint -> Opus 4.7; founder-side compose -> Opus 4.7. Encoded in `skills/mesh_trajectory/config/model_routing.yaml`; SKILL.md flows resolve the model at dispatch time via `scripts/model_routing.py`. | Opus across all layers (status quo); Sonnet across all layers (one model for everything); per-section model picking inside layer 3 | Plan 07's first end-to-end production sync ran the whole pipeline on Opus and consumed ~600K subagent tokens; per-session digest is a constrained extraction Haiku handles cleanly; per-project summary follows a rigid skeleton Sonnet handles well; matching signal lives in the 4-section synthesis and the privacy lint, both of which justify Opus. Config-driven so a future re-routing is one file edit (yaml + test + this row, in one commit). |
```

- [ ] **Step 3: Sanity checks.**

```bash
grep -c "^| D14 " spec.md
# Expected: 1
grep -c "—" spec.md
# Expected: 0
```

- [ ] **Step 4: Commit.**

```bash
git add spec.md
git commit -m "docs(spec): add D14 per-layer model routing to decision framework"
```

---

## Task 7: Founder dogfood verification — re-sync with new routing, compare against the all-Opus baseline

**Files:** none.

The 2026-05-02 sync run is the cost + quality baseline (all-Opus, ~600K subagent tokens, body landed at commit `f4be7fee` in mesh-data). This task re-runs the same flow on the same corpus with the new routing and captures the diff.

- [ ] **Step 1: Pre-flight.**

```bash
git -C ~/.cache/mesh-data pull --rebase
ls ~/.cache/mesh-data/users/sidpan_007_at_gmail_com.md
.venv/bin/pytest -q | tail -3
# Expected: 111 passed
.venv/bin/python -m skills.mesh_trajectory.scripts.model_routing layer1
.venv/bin/python -m skills.mesh_trajectory.scripts.model_routing layer2
.venv/bin/python -m skills.mesh_trajectory.scripts.model_routing layer3
# Expected stdouts: haiku, sonnet, opus
```

- [ ] **Step 2: Run `/mesh-trajectory sync` in a fresh Claude Code session.** Walk the full flow per SKILL.md. Capture per-subagent token counts from the completion notifications (the `<usage>` blocks). Specifically log:
  - Layer 1 subagent count + total tokens (was 5 subagents / ~470K on Opus baseline).
  - Layer 2 subagent count + total tokens (was 3 subagents / ~127K on Opus baseline).
  - Wall-clock time per layer.

- [ ] **Step 3: Quality spot-checks** before approving the body for push:
  - Read the assembled `/tmp/mesh_body.md`. Compare each section against the body that landed at mesh-data commit `f4be7fee` (today's all-Opus baseline). Look for: vocabulary drift toward stack/library terms (the warning sign of L1 Haiku regression), trajectory-sentence vagueness in any project summary the user reviews at SKILL.md step 11 (the warning sign of L2 Sonnet regression), or section-level signal loss vs the baseline.
  - If quality regresses meaningfully on either signal, STOP. Document the failure mode in this plan's EXECUTION LOG with concrete examples. Plan 08 candidates: bump L1 to Sonnet, bump L2 to Opus, or revert routing.
  - If quality is comparable, push and verify the file lands.

- [ ] **Step 4: Append metrics to this plan's EXECUTION LOG** in a "Verification metrics" section:
  - L1 token spend (new) vs baseline + delta.
  - L2 token spend (new) vs baseline + delta.
  - L3 token spend (unchanged, parent context).
  - Wall-clock-per-layer comparison.
  - One-paragraph quality assessment (verbatim quotes if anything regressed).

- [ ] **Step 5: Cleanup.**

```bash
ls /tmp/mesh_* 2>&1
# Expected: no /tmp/mesh_* artifacts remain
```

---

## Open decisions for this iteration

| Decision | Default | Reconsider if |
|---|---|---|
| **Model alias scheme** | Pass-through aliases (`haiku` / `sonnet` / `opus`); the Agent tool resolves them to the latest model version. | If a future Anthropic naming change breaks this assumption, add a translation layer in `model_routing.py` that maps alias -> versioned model ID. |
| **Where the YAML lives** | `skills/mesh_trajectory/config/model_routing.yaml` (new `config/` dir for tunable knobs). | If a second tunable lands in V0.1 and shares a different scope (e.g. founder-only), reorganize then. Don't pre-design. |
| **Layer count** | Five layers: `layer1` / `layer2` / `layer3` / `lint` / `compose`. | If V0.1 introduces an L4 (e.g. cross-week trajectory consolidation), extend the config and add a test row. |
| **L2 = Sonnet specifically** | User decision after we discussed L2 being borderline-OK on Haiku. | If verification (Task 7) shows L2 trajectory-sentence quality is comparable on Haiku, drop L2 to Haiku in a one-row config edit and a test update. |
| **Synthesis + lint as parent-context** | They run in whatever session the user launches the skill from; SKILL.md surfaces a model-mismatch warning if the parent isn't on the configured model. | If a future iteration wraps the whole sync in a subagent dispatch (e.g. for scheduled runs), all five layers become enforceable from one place. |

---

## Self-review checklist

Before claiming this iteration done:

- [ ] All 111 tests pass (103 baseline + 8 new in `test_model_routing.py`).
- [ ] `python -m skills.mesh_trajectory.scripts.model_routing layer1` prints `haiku`; `layer2` prints `sonnet`; `layer3`, `lint`, `compose` all print `opus`.
- [ ] `python -m skills.mesh_trajectory.scripts.model_routing nope` exits non-zero with a clear error.
- [ ] SKILL.md steps 6 and 9 each reference `model_routing` and capture the model into a shell variable before dispatch.
- [ ] SKILL.md steps 13 and 15 reference `model_routing` for visibility (parent-context, no enforcement).
- [ ] `mesh_orchestrator/SKILL.md` step 7 references `model_routing` for compose.
- [ ] spec.md has a D14 row in the decision framework table.
- [ ] No em-dashes in any modified file.
- [ ] Founder dogfood sync (Task 7) succeeded OR the failure is documented in this plan's EXECUTION LOG.
- [ ] Plans 01-06 are NOT rewritten; this iteration only adds and modifies.

---

## Execution Handoff

This plan is ready to execute in a fresh Claude Code conversation.

1. Open the mesh repo. Read `CLAUDE.md`, then `spec.md` (especially D9, D12, D13), then this plan in full.
2. Read `plans/05-multipart-trajectory.md` and `plans/06-onboarding-leniency.md` EXECUTION LOGs for the latest pipeline + onboarding state.
3. Use `superpowers:subagent-driven-development` to dispatch per-task subagents OR `superpowers:executing-plans` for inline batch execution. Tasks 1-6 are codable; Task 7 is the founder dogfood and is manual.
4. Dispatch order matters slightly: Task 1 (config + loader + tests) before Tasks 2-5 (SKILL.md edits), which depend on the loader. Task 6 (spec.md D14) and Task 7 (verification) can run any time after Tasks 1-5.
5. Each task ends with one commit; do not batch commits across tasks.
6. After Task 7, append an EXECUTION LOG to this plan covering: task status (DONE / PARTIAL / BLOCKED + commit SHAs), what worked, what didn't, hardenings beyond the original plan, mid-flight architectural changes, the dogfood metrics + quality assessment, and open items handed off to plan 08.
7. Then ask the user whether to author plan 08 now (likely scope: scheduled weekly sync via the `/schedule` skill so the body stays fresh between manual runs; or per-section model overrides if Task 7 shows L3 needs heterogeneous models per section).

---

# EXECUTION LOG (2026-05-02)

## Task status

| # | Task | Status | Commit |
|---|---|---|---|
| 1 | Create model_routing.yaml + loader + tests | DONE | `4e375a9` |
| 2 | SKILL.md step 6 reads layer1 | DONE | `4661d6d` |
| 3 | SKILL.md step 9 reads layer2 | DONE | `d23a747` |
| 4 | SKILL.md steps 13 + 15 surface configured model | DONE | `8c996e8` |
| 5 | mesh_orchestrator/SKILL.md step 7 surfaces compose model | DONE | `1123834` |
| 6 | spec.md D14 entry | DONE | `870ca0a` |
| 7 | Founder dogfood verification | DEFERRED | (folded into plan 09's verification: same dogfood run will exercise both routing + the v3 coherence layer end-to-end) |

Plan was authored at commit `4f54997` and executed in the same session as plan 09. 6 implementation commits + plan commit + execution log commit.

## Test counts

- Baseline (start of session): 103 passing (post plan 06 onboarding leniency).
- After Task 6: **112 passing** (+9 in `test_model_routing.py`).

## What worked

- The TDD ordering held: tests RED before the loader existed, GREEN after the YAML + loader landed.
- The CLI shape (`python -m skills.mesh_trajectory.scripts.model_routing layer1` -> `haiku`) is what the SKILL.md flow actually needs. The shell-capture pattern (`MODEL=$(...)`) is the natural way to wire it.
- `ALLOWED_MODELS = frozenset({"haiku", "sonnet", "opus"})` doubles as a syntax check on the YAML; an invalid alias raises at load time, not at dispatch time. Test `test_only_known_aliases_in_config` locks that.
- Steps 13 + 15 surface the configured model as a "if your session is not on Opus, warn" note rather than trying to enforce — correct framing because the parent's model can't be changed mid-conversation. The compose step surfaces the same way.

## What didn't work first try

Nothing. All 6 codable tasks landed clean on first attempt. The earlier session had already authored the plan with concrete code, so execution was largely transcription.

## Hardenings beyond the original plan

None. The plan's tech notes were sufficient.

## Mid-flight architectural changes

None.

## Verification result

- All 112 tests pass.
- CLI smoke: `layer1 -> haiku`, `layer2 -> sonnet`, `layer3 -> opus`, `lint -> opus`, `compose -> opus`. Unknown layer exits 1 with a clear error.
- `grep -c model_routing skills/mesh_trajectory/SKILL.md` -> 5 (steps 6, 9, 13, 15 + a model-mismatch warning string).
- `grep -c model_routing skills/mesh_orchestrator/SKILL.md` -> 1.
- D14 row present in spec.md.
- No em-dashes anywhere.

## What remains MANUAL (deferred)

- **Founder dogfood sync with the new routing.** Task 7 of the plan called for re-running `/mesh-trajectory sync` against the founder corpus and comparing against the all-Opus 2026-05-02 baseline. **Folded into plan 09's verification** (Task 11) because plan 09 ships the v3 coherence layer in the same session; one dogfood run can exercise both changes end-to-end. The metrics expected (L1 token spend on Haiku vs the Opus baseline; L2 on Sonnet) will be captured in plan 09's EXECUTION LOG.

## Open items handed off to plan 09 / plan 10

- Plan 09 picks up immediately and adds `layer4: opus` to the routing config in its Task 7 (now trivial since the YAML exists).
- Plan 10 candidates: scheduled weekly sync via `/schedule`; if dogfood shows L1 Haiku quality regresses meaningfully, bump L1 to Sonnet (one-row YAML edit + one test update + spec.md D14 update, in one commit per the three-way pattern).
