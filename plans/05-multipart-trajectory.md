# Plan 05: Multipart trajectory body (schema v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Before starting**, read in this order:
> 1. `CLAUDE.md` (hard constraints, especially #1 Claude is the AI layer, #3 privacy enforced by code, and #5 build only what's in the active plan).
> 2. `spec.md` (D9, D11, D13, the Privacy section).
> 3. **The approved design doc: `docs/superpowers/specs/2026-05-01-multipart-trajectory-design.md`.** This plan implements that doc; do NOT re-derive design decisions. If the doc and this plan disagree, the doc wins, stop and ask.
> 4. `plans/04-launch-readiness.md` (the slash command is `/mesh-trajectory`, single registered command, action-arg routing; the extract pipeline writes a manifest in one pass).
> 5. The most recent commits: `git log --oneline -15` to see what shipped after plan 04 (paste prompt, UX hardening, access request, launch-window override). The launch-window override is load-bearing for V8 below.

**Goal:** Replace the single 200-word trajectory body with four ordered H2 sections (`Work context`, `Top of mind`, `Recent months`, `Long-term background`), bump `schema_version` 1 -> 2, extend `validate.py` with rules V3-V8 (version gate + section structure + per-section/total word caps + PII stop-list), update the matcher prompt to weight sections, ship a v1->v2 lazy migration adapter on the orchestrator side, and dogfood the new flow on the founder's real corpus.

**Architecture:** No infra change. The schema gains one second locked artifact (`SECTION_FIELDS`) alongside `SCHEMA_FIELDS`. The validator pipeline grows from 4 rules to 8. The extractor produces 4 section bodies instead of 1 paragraph. The orchestrator continues to read the body as text; for v1 files it crudely treats the entire body as the `Recent months` section (per design doc Section 7).

**Tech stack:** Python 3.11 + pytest (unchanged). YAML for frontmatter. Markdown for body. No new dependencies.

---

## Why this iteration exists

Plan 04 shipped a clean extract -> digest -> per-project -> synthesize -> lint -> push pipeline that produces a single 200-word body. End-to-end verification on the founder's corpus confirmed the privacy gates hold and the body lands coherently. The single-body shape, however, conflates four temporally distinct signals (current role / near-term / recent months / long-term substrate) that the matcher needs to distinguish to detect the **Guide x Explorer** pattern (D9, spec.md "Matching: V0 vs V1 Vision"). The approved design doc decomposes the body into those four sections without expanding the privacy surface in line-item count (still one file per user, still 8 frontmatter fields), and adds V8 (PII stop-list) as a belt-and-braces guard while `mesh-data` is publicly readable during the launch window.

This plan is the implementation tracker for that doc. Section 12 of the doc lists the acceptance criteria; this plan turns each into TDD-ordered tasks.

## Architectural shift

```
   PLAN 04 (current shape)                        PLAN 05 (target)

   schema_version: 1                              schema_version: 2
   body: single 200-word paragraph                body: four H2 sections, total <=250 words
                                                    ## Work context           (<=50 words)
                                                    ## Top of mind            (<=75 words)
                                                    ## Recent months          (<=100 words)
                                                    ## Long-term background   (<=75 words)

   validate.py rules:                             validate.py rules:
     V1 frontmatter keys subset of SCHEMA_FIELDS    V1 (existing)
     V2 required fields present                     V2 (existing)
     V3 schema_version == 1                         V3 schema_version in {1,2} until 2026-06-01,
                                                       {2} only after the cutoff
     -- city Bengaluru                              V4 body has exactly SECTION_FIELDS H2s, in order
     -- body 50-300 words                           V5 no extra H2 headings in body
                                                    V6 each section <= SECTION_WORD_CAPS[section]
                                                    V7 total body <= TOTAL_BODY_WORD_CAP (250)
                                                    V8 PII stop-list pass over full body
                                                    (city + total-body cap stay; old single-body
                                                     50-300 word check is replaced by V6+V7)

   extract.py synthesizes one body              extract.py emits 4 sections in order
                                                  via 4 section-specific prompts under
                                                  prompts/sections/<section>.md

   compose.md ingests body as a paragraph       compose.md reads body as 4 named sections
                                                 with explicit weights (Top of mind 0.4,
                                                 Recent months 0.4, Long-term 0.2;
                                                 Work context as constraint, not score)

   orchestrator load_users.py treats body       v1 adapter: when frontmatter says
   as opaque text                                schema_version: 1, treat entire body as
                                                 the Recent months section, leave the other
                                                 three empty. Adapter is unit-tested with a
                                                 v1 fixture.
```

## What stays unchanged (do NOT touch)

- The 8 frontmatter fields (`SCHEMA_FIELDS` in `schema.py`) and their `REQUIRED_FIELDS` / `OPTIONAL_FIELDS` split.
- `push.py` (writes `users/<email>.md`; takes frontmatter + body, doesn't care about body shape).
- `lint_body.py` and `prompts/lint_body.md` (lint runs against the whole body string; sections do not change its surface).
- `parse_response.py` (founder-side JSON parser; design doc Section 6 is explicit that `{table_id, members[], why_this_table}` is unchanged).
- `write_invites.py`, `render_invite.py`.
- The hierarchical extract -> digest -> per-project pipeline shape (Tasks 1-4 of plan 04). The 4-section step replaces only step 13 of `SKILL.md` (synthesize) with a 4-pass loop; steps 5-12 stay.
- The per-session, per-project, summarize prompt files (`prompts/per_session.md`, `prompts/per_project.md`, `prompts/summarize.md`). The summarize.md prompt is reused as-is for each section pass with a section-name override variable.
- `/mesh-trajectory` slash command name + action-arg routing (plan 04).
- All three privacy-gate stages and their delete-after-downstream-step rule.
- Hard constraint #1 (no external LLM/embedding APIs), #2 (GitHub is the only datastore), #4 (raw conversations never leave device).

## Hard constraints (carry-overs from CLAUDE.md and the design doc)

1. **Claude is the AI layer.** No external LLM API calls. Section extraction runs through local Claude (the user's own session executing the skill).
2. **Privacy is enforced by code, not policy.** Validator V1-V8 are the gate. Never bypass. V8 (PII stop-list) is mandatory in V0 because `mesh-data` is currently public (launch-window override).
3. **The 8 frontmatter fields are frozen** (`SCHEMA_FIELDS`). Only the version number and the body shape change.
4. **`SECTION_FIELDS` is the second locked contract** (design doc Section 3.3). Adding/removing/renaming a section requires the same three-way commit pattern as adding a frontmatter field: `schema.py` + `spec.md` + a failing test in one commit.
5. **No V0.1 features** (design doc Section 10): no incremental per-section sync, no adjacent-bets section, no local-only memory file, no per-section embeddings, no automated migration tooling, no per-user PII stop-list UI.
6. **No em-dashes anywhere** (project rule).
7. **TDD discipline.** For every code task: write failing test -> run pytest, confirm RED -> implement minimally -> run pytest, confirm GREEN -> commit. One concern per commit (or one tightly coupled pair).
8. **Plans are append-only.** Do not edit this plan body after execution starts. Append an EXECUTION LOG appendix at the end of the iteration.

## Tech notes

- **Heading recognition rule** (design doc Section 4 "Heading recognition rule"): exact heading text after Unicode NFC normalization, case-sensitive, no typo tolerance. Match `^## <name>\s*$` with `name` taken verbatim from `SECTION_FIELDS`. The extractor produces canonical headings; if the user edits a heading, validation fails with a clear "rename heading X to Y" message.
- **Section parser shape.** Add a helper `parse_sections(body: str) -> dict[str, str]` to `validate.py`. It walks lines, splits on H2 headings (anything matching `^## `), returns an ordered dict of `{heading_text: section_body_text}` with whitespace normalized. The same helper is used by V4, V5, V6, V7, V8 and by the orchestrator v1 adapter (re-export).
- **Migration cutoff.** `MIGRATION_CUTOFF_DATE = date(2026, 6, 1)`. Lives in `schema.py`. V3 reads it and `date.today()` (or an injected `today` for tests).
- **PII stop-list file.** `skills/mesh_trajectory/pii_stoplist.txt`, one term per line, comments allowed via `#`. Per-user override at `~/.mesh/pii_extra.txt` (same format). Loader is unit-tested. Initial committed list contains generic partner/household terms (the design doc says "small hardcoded stop-list of common partner / household terms"; see Task 7 for the seed list).
- **PII regex set.** Phone (Indian + international), email-other-than-self, address-pattern. All implemented as plain `re` patterns in `validate.py`. V8 surfaces the FIRST offending substring in its error message; the user can rephrase and re-run.
- **v1->v2 orchestrator adapter.** Lives in `load_users.py`. When a user file's frontmatter has `schema_version == 1`, the loader populates `User.sections = {"Recent months": <full body>, "Work context": "", "Top of mind": "", "Long-term background": ""}`. For v2 files, `User.sections` is the parsed dict. `User.body` (the existing field) stays populated with the full original body string, so existing tests do not regress.
- **Extractor file layout.** Section prompts live at `skills/mesh_trajectory/prompts/sections/work_context.md`, `top_of_mind.md`, `recent_months.md`, `long_term_background.md`. Each prompt takes `{{project_summaries}}`, `{{why_seed}}`, and `{{prior_section}}` (empty string on first sync) and produces ONLY the section body text (no heading, the controller adds it).
- **Live reload caveat** (carried from plan 04 Task 3): SKILL.md edits may need a Claude Code session restart for the slash-command body to refresh. Document if hit; not a blocker.

---

## File structure (delta only)

```
mesh/
├── skills/
│   └── mesh_trajectory/
│       ├── schema.py                                     ← MODIFY: bump SCHEMA_VERSION,
│       │                                                          add SECTION_FIELDS,
│       │                                                          SECTION_WORD_CAPS,
│       │                                                          TOTAL_BODY_WORD_CAP,
│       │                                                          MIGRATION_CUTOFF_DATE
│       ├── pii_stoplist.txt                              ← CREATE: seed PII terms
│       ├── prompts/
│       │   └── sections/                                 ← CREATE: 4 section prompts
│       │       ├── work_context.md
│       │       ├── top_of_mind.md
│       │       ├── recent_months.md
│       │       └── long_term_background.md
│       ├── scripts/
│       │   └── validate.py                               ← MODIFY: rules V3-V8,
│       │                                                          parse_sections() helper,
│       │                                                          PII regex+stoplist loaders
│       └── SKILL.md                                      ← MODIFY: replace step 13 with
│                                                                  4-section synthesize loop;
│                                                                  update step 17 review framing;
│                                                                  add public-repo + v8 mention
│   └── mesh_orchestrator/
│       ├── prompts/
│       │   └── compose.md                                ← MODIFY: ingest sections + weights
│       └── scripts/
│           └── load_users.py                             ← MODIFY: v1 adapter, populate
│                                                                  User.sections
├── tests/
│   ├── test_schema.py                                    ← MODIFY: assert v2 + sections
│   ├── test_validate.py                                  ← MODIFY: V3-V8 tests + fixture
│   ├── fixtures/                                         ← CREATE
│   │   ├── user_v2_valid.md
│   │   └── user_v1_legacy.md
│   ├── test_load_users.py                                ← MODIFY: v1 adapter, v2 sections
│   └── test_extract.py                                   ← MODIFY: 4-section assembly test
├── spec.md                                               ← MODIFY: Data Schema section -> v2
└── plans/05-multipart-trajectory.md                      ← THIS FILE
```

The on-disk `~/.claude/skills/mesh -> .../skills/mesh_trajectory` symlink is unchanged.

---

# Tasks

## Task 1: Schema constants for v2 (`schema.py` + `test_schema.py`)

**Files:**
- Modify: `skills/mesh_trajectory/schema.py`
- Modify: `tests/test_schema.py`

Add `SCHEMA_VERSION = 2`, the new section constants, and a migration cutoff date. Lock them with tests.

- [ ] **Step 1: Write failing tests** in `tests/test_schema.py`. Replace the file body with:

```python
from datetime import date
from skills.mesh_trajectory.schema import (
    SCHEMA_FIELDS, SCHEMA_VERSION, REQUIRED_FIELDS,
    SECTION_FIELDS, SECTION_WORD_CAPS, TOTAL_BODY_WORD_CAP,
    MIGRATION_CUTOFF_DATE, ACCEPTED_SCHEMA_VERSIONS,
)


def test_schema_version_is_two():
    assert SCHEMA_VERSION == 2


def test_required_fields_are_locked():
    assert REQUIRED_FIELDS == {
        "schema_version", "name", "email", "linkedin_url",
        "role", "city", "available_saturdays",
    }


def test_full_field_set_includes_optional():
    assert SCHEMA_FIELDS == REQUIRED_FIELDS | {"do_not_match", "embedding"}


def test_section_fields_are_locked_and_ordered():
    # Tuple, not set: order is part of the contract.
    assert SECTION_FIELDS == (
        "Work context",
        "Top of mind",
        "Recent months",
        "Long-term background",
    )


def test_section_word_caps_match_design_doc():
    assert SECTION_WORD_CAPS == {
        "Work context":          50,
        "Top of mind":           75,
        "Recent months":        100,
        "Long-term background":  75,
    }


def test_section_word_caps_cover_every_section():
    assert set(SECTION_WORD_CAPS.keys()) == set(SECTION_FIELDS)


def test_total_body_word_cap_is_250():
    assert TOTAL_BODY_WORD_CAP == 250


def test_migration_cutoff_date_is_2026_06_01():
    assert MIGRATION_CUTOFF_DATE == date(2026, 6, 1)


def test_accepted_schema_versions_during_window():
    # During the migration window v1 and v2 are both accepted.
    # The validator gates by date; this constant is the static set.
    assert ACCEPTED_SCHEMA_VERSIONS == frozenset({1, 2})
```

- [ ] **Step 2: Run tests, confirm RED.**

```bash
.venv/bin/pytest tests/test_schema.py -v
```

Expected: ImportError or AssertionError on the new constants.

- [ ] **Step 3: Implement** the new constants in `schema.py`. Replace the file body with:

```python
"""Authoritative schema for MESH V0 user payload.

Two locked contracts in this module:
  1. SCHEMA_FIELDS  - the 8 frontmatter keys; never extend without updating
                      spec.md AND adding a failing test.
  2. SECTION_FIELDS - the 4 ordered H2 headings inside the body; never extend
                      or rename without updating spec.md AND adding a failing test.

Any field or section not declared here is forbidden; validate.py enforces both.
"""
from datetime import date

SCHEMA_VERSION = 2

# Versions the validator accepts. v1 is accepted for the migration window
# (until MIGRATION_CUTOFF_DATE). After that date, only SCHEMA_VERSION is
# accepted. See validate.py V3.
ACCEPTED_SCHEMA_VERSIONS = frozenset({1, 2})
MIGRATION_CUTOFF_DATE = date(2026, 6, 1)

REQUIRED_FIELDS = frozenset({
    "schema_version",
    "name",
    "email",
    "linkedin_url",
    "role",
    "city",
    "available_saturdays",
})

OPTIONAL_FIELDS = frozenset({
    "do_not_match",
    "embedding",
})

SCHEMA_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS

# Body shape: four ordered H2 sections.
# Order matters: validate.py V4 enforces this exact sequence.
SECTION_FIELDS = (
    "Work context",
    "Top of mind",
    "Recent months",
    "Long-term background",
)

SECTION_WORD_CAPS = {
    "Work context":          50,
    "Top of mind":           75,
    "Recent months":        100,
    "Long-term background":  75,
}

TOTAL_BODY_WORD_CAP = 250
```

- [ ] **Step 4: Run tests, confirm GREEN.**

```bash
.venv/bin/pytest tests/test_schema.py -v
```

Expected: 9 passing in `test_schema.py`. Other test files will FAIL (validate.py and load_users.py still pin to v1); that is expected and addressed in the subsequent tasks.

- [ ] **Step 5: Commit.**

```bash
git add skills/mesh_trajectory/schema.py tests/test_schema.py
git commit -m "feat(schema): bump to v2; add SECTION_FIELDS, word caps, migration cutoff"
```

---

## Task 2: Validator V3 - schema_version gate with migration window

**Files:**
- Modify: `skills/mesh_trajectory/scripts/validate.py`
- Modify: `tests/test_validate.py`

Replace the existing `schema_version == 1` check with the V3 rule: accept `{1, 2}` until `MIGRATION_CUTOFF_DATE`, then `{2}` only. Inject `today` so tests are deterministic. Keep the existing tests for valid v1 working until the rest of the validator (V4-V8) lands.

This task does NOT yet enforce 4-section body shape. The existing `BODY_MIN_WORDS / BODY_MAX_WORDS` 50-300-word check stays for now, so v1 fixtures continue to pass. V6+V7 (Task 5+6) will replace it.

- [ ] **Step 1: Write failing tests** in `tests/test_validate.py`. Replace the entire file body with this rewritten suite (it covers V1, V2, V3 in this commit; V4-V8 land in Tasks 3-7). Keep the legacy single-body 50-300 word check assertions for now (they will go away in Task 6):

```python
from datetime import date
import pytest
from skills.mesh_trajectory.scripts.validate import (
    validate_payload, parse_markdown, ValidationError,
)

VALID_V2 = {
    "schema_version": 2,
    "name": "Asha Rao",
    "email": "asha@example.com",
    "linkedin_url": "https://linkedin.com/in/asharao",
    "role": "Founding Engineer",
    "city": "Bengaluru",
    "available_saturdays": ["2026-05-09"],
}

VALID_V1 = VALID_V2 | {"schema_version": 1}

# Body that satisfies the OLD single-body 50-300 word check. Sections
# (V4-V8) are not enforced until Tasks 3-7.
LEGACY_BODY = "word " * 60


# --- V1: forbidden field rejection ---

def test_extra_field_is_refused():
    p = VALID_V2 | {"raw_conversation": "secret"}
    with pytest.raises(ValidationError, match="forbidden field"):
        validate_payload(p, body=LEGACY_BODY)


# --- V2: required field presence ---

def test_missing_required_field_is_refused():
    p = {k: v for k, v in VALID_V2.items() if k != "email"}
    with pytest.raises(ValidationError, match="missing required"):
        validate_payload(p, body=LEGACY_BODY)


# --- V3: schema_version gate with migration window ---

def test_v2_passes_during_window():
    # Should not raise on V3; later tasks add V4-V8 which need real sections.
    # We test V3 in isolation by passing the legacy body and asserting the
    # specific version rule is satisfied (other rules may still raise; we
    # only check V3 wasn't the failure).
    try:
        validate_payload(VALID_V2, body=LEGACY_BODY, today=date(2026, 5, 1))
    except ValidationError as e:
        assert "schema_version" not in str(e), f"V3 should pass v2: {e}"


def test_v1_passes_during_migration_window():
    # Pre-cutoff: v1 still acceptable.
    try:
        validate_payload(VALID_V1, body=LEGACY_BODY, today=date(2026, 5, 1))
    except ValidationError as e:
        assert "schema_version" not in str(e), f"V3 should accept v1 pre-cutoff: {e}"


def test_v1_refused_after_migration_cutoff():
    with pytest.raises(ValidationError, match="schema_version.*1.*after.*2026-06-01"):
        validate_payload(VALID_V1, body=LEGACY_BODY, today=date(2026, 6, 1))


def test_unknown_schema_version_is_refused():
    p = VALID_V2 | {"schema_version": 99}
    with pytest.raises(ValidationError, match="schema_version"):
        validate_payload(p, body=LEGACY_BODY, today=date(2026, 5, 1))


def test_v3_default_today_is_real_today():
    # When today is not injected, validate_payload uses date.today(). We can't
    # mock easily without freezegun; assert it doesn't crash on a v2 payload.
    try:
        validate_payload(VALID_V2, body=LEGACY_BODY)
    except ValidationError as e:
        assert "schema_version" not in str(e), f"V3 default-today path: {e}"


# --- city ---

def test_city_must_be_bengaluru_in_v0():
    p = VALID_V2 | {"city": "Mumbai"}
    with pytest.raises(ValidationError, match="city"):
        validate_payload(p, body=LEGACY_BODY)


# --- legacy body word check (will be replaced by V6+V7 in Tasks 5+6) ---

def test_body_too_short_is_refused_legacy():
    with pytest.raises(ValidationError, match="body"):
        validate_payload(VALID_V2, body="too short")


# --- parse_markdown framing (unchanged from plan 04) ---

def test_parse_markdown_refuses_missing_opening_fence(tmp_path):
    f = tmp_path / "u.md"
    f.write_text("name: Asha\n")
    with pytest.raises(ValidationError, match="begin with"):
        parse_markdown(f)


def test_parse_markdown_refuses_missing_closing_fence(tmp_path):
    f = tmp_path / "u.md"
    f.write_text("---\nname: Asha\n")
    with pytest.raises(ValidationError, match="closing"):
        parse_markdown(f)


def test_parse_markdown_refuses_empty_frontmatter(tmp_path):
    f = tmp_path / "u.md"
    f.write_text("---\n---\n\nbody")
    with pytest.raises(ValidationError, match="mapping"):
        parse_markdown(f)
```

- [ ] **Step 2: Run tests, confirm RED.**

```bash
.venv/bin/pytest tests/test_validate.py -v
```

Expected: failures on the V3-specific tests (`test_v1_passes_during_migration_window`, `test_v1_refused_after_migration_cutoff`, `test_v3_default_today_is_real_today`, etc.) because `validate_payload` does not yet accept a `today` kwarg and pins `schema_version == 1`.

- [ ] **Step 3: Implement V3** in `validate.py`. Replace the existing `schema_version` check with the version-gate logic and add the `today` kwarg. Patch only the relevant region; keep the rest of the file:

```python
"""Pre-push validator. Privacy gate. REFUSES any field not in SCHEMA_FIELDS.

Usage as CLI:
    python -m skills.mesh_trajectory.scripts.validate path/to/user.md
"""
import sys
from datetime import date
from pathlib import Path
import yaml
from skills.mesh_trajectory.schema import (
    SCHEMA_FIELDS, REQUIRED_FIELDS, SCHEMA_VERSION,
    ACCEPTED_SCHEMA_VERSIONS, MIGRATION_CUTOFF_DATE,
)

V0_ALLOWED_CITIES = frozenset({"Bengaluru"})
# Legacy single-body word check; V6+V7 supersede this in later tasks.
BODY_MIN_WORDS = 50
BODY_MAX_WORDS = 300


class ValidationError(Exception):
    pass


def validate_payload(frontmatter: dict, body: str, today: date | None = None) -> None:
    today = today or date.today()
    keys = set(frontmatter.keys())

    # V1: forbidden field rejection
    extra = keys - SCHEMA_FIELDS
    if extra:
        raise ValidationError(f"forbidden field(s) present: {sorted(extra)}")

    # V2: required fields present
    missing = REQUIRED_FIELDS - keys
    if missing:
        raise ValidationError(f"missing required field(s): {sorted(missing)}")

    # V3: schema_version gate with migration window
    sv = frontmatter["schema_version"]
    if sv not in ACCEPTED_SCHEMA_VERSIONS:
        raise ValidationError(
            f"schema_version must be one of {sorted(ACCEPTED_SCHEMA_VERSIONS)}, got {sv}"
        )
    if sv == 1 and today >= MIGRATION_CUTOFF_DATE:
        raise ValidationError(
            f"schema_version 1 not accepted after {MIGRATION_CUTOFF_DATE.isoformat()}; "
            f"re-run /mesh-trajectory sync to migrate to schema_version 2"
        )

    # city
    if frontmatter["city"] not in V0_ALLOWED_CITIES:
        raise ValidationError(
            f"city must be one of {sorted(V0_ALLOWED_CITIES)} in V0, got {frontmatter['city']}"
        )

    # Legacy body word check (replaced by V6+V7 in subsequent tasks)
    word_count = len(body.split())
    if word_count < BODY_MIN_WORDS or word_count > BODY_MAX_WORDS:
        raise ValidationError(
            f"body must be {BODY_MIN_WORDS}-{BODY_MAX_WORDS} words, got {word_count}"
        )


def parse_markdown(path: Path) -> tuple[dict, str]:
    text = path.read_text()
    if not text.startswith("---\n"):
        raise ValidationError("file must begin with YAML frontmatter '---'")
    parts = text.split("---\n", 2)
    if len(parts) != 3:
        raise ValidationError("file must end frontmatter with closing '---'")
    _, fm_text, body = parts
    fm = yaml.safe_load(fm_text)
    if not isinstance(fm, dict):
        raise ValidationError("frontmatter must be a YAML mapping")
    return fm, body.strip()


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate.py <path/to/user.md>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    try:
        fm, body = parse_markdown(path)
        validate_payload(fm, body)
    except ValidationError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests, confirm GREEN.**

```bash
.venv/bin/pytest tests/test_validate.py tests/test_schema.py -v
```

Expected: all tests in `test_schema.py` (9) and `test_validate.py` (~12) pass. Other test files (`test_load_users.py`) may still pass against v1 fixtures - they hardcode `schema_version: 1` and pre-cutoff `today` is the default.

- [ ] **Step 5: Commit.**

```bash
git add skills/mesh_trajectory/scripts/validate.py tests/test_validate.py
git commit -m "feat(validate): V3 schema_version gate with migration window to 2026-06-01"
```

---

## Task 3: Validator V4 - body has exactly SECTION_FIELDS H2 headings, in order

**Files:**
- Modify: `skills/mesh_trajectory/scripts/validate.py`
- Modify: `tests/test_validate.py`
- Create: `tests/fixtures/user_v2_valid.md`

Add a `parse_sections(body: str) -> dict[str, str]` helper used by V4 onward, then implement V4. The helper preserves order and lets V5 detect extras and V6/V7 word-count.

- [ ] **Step 1: Write the v2 fixture** at `tests/fixtures/user_v2_valid.md`. This is the "real shape" fixture (per CLAUDE.md "synthetic-test trap" warning); validator tests against fixtures must use the exact shape `extract.py` will produce.

```markdown
---
schema_version: 2
name: Asha Rao
email: asha@example.com
linkedin_url: https://linkedin.com/in/asharao
role: Founding Engineer
city: Bengaluru
available_saturdays:
  - "2026-05-09"
---

## Work context

Founding engineer at a 12-person fintech, owning the agent orchestration layer that routes customer queries across underwriting, KYC, and support. Reports to the CTO.

## Top of mind

Migrating an in-house agent harness onto a unified runtime so the team can ship multi-agent workflows without bespoke glue per use case. Wrestling with eval coverage and trajectory replay during the transition.

## Recent months

Shipped v2 of the underwriting agent stack with structured-output validation and per-tenant tool registries; cut hallucinated denials by half. Stood up an offline eval harness over six months of real cases that catches regressions before production.

## Long-term background

Eight years building backend systems at scale. Prior life in ranking infrastructure at a marketplace; wrote production search rankers and the eval pipelines that justified them. Comfortable in Python, Go, and prompt-engineering trade-off space.
```

- [ ] **Step 2: Write failing tests** in `tests/test_validate.py`. Append to the existing file (do not delete prior tests):

```python
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> tuple[dict, str]:
    return parse_markdown(FIXTURES / name)


def _v2_body(**overrides) -> str:
    """Build a v2 body from sections; override individual sections by name."""
    sections = {
        "Work context": "founding engineer at a 12 person fintech owning agent orchestration",
        "Top of mind": "migrating an in house agent harness onto a unified runtime this quarter",
        "Recent months": "shipped v2 of the underwriting agent stack and an offline eval harness",
        "Long-term background": "eight years backend systems plus prior ranking infrastructure work",
    }
    sections.update(overrides)
    parts = []
    for name in ("Work context", "Top of mind", "Recent months", "Long-term background"):
        parts.append(f"## {name}\n\n{sections[name]}")
    return "\n\n".join(parts)


# --- V4: exactly SECTION_FIELDS H2s, in order ---

def test_v2_fixture_passes_v4():
    fm, body = _fixture("user_v2_valid.md")
    # V4 should not raise; later rules might (V8 PII, etc.) but the fixture
    # is constructed to pass everything once V8 lands too.
    validate_payload(fm, body, today=date(2026, 5, 1))


def test_missing_section_is_refused_with_section_name():
    body = _v2_body()
    # Drop the "Top of mind" heading entirely.
    body = body.replace("## Top of mind\n\nmigrating an in house agent harness onto a unified runtime this quarter\n\n", "")
    with pytest.raises(ValidationError, match="Top of mind"):
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))


def test_sections_out_of_order_are_refused():
    # Swap "Top of mind" and "Recent months".
    body = (
        "## Work context\n\nfounding engineer\n\n"
        "## Recent months\n\nshipped v2 of the underwriting agent stack\n\n"
        "## Top of mind\n\nmigrating an in house agent harness this quarter\n\n"
        "## Long-term background\n\neight years backend systems\n"
    )
    with pytest.raises(ValidationError, match="order"):
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))


def test_section_heading_typo_is_refused_with_rename_hint():
    body = _v2_body().replace("## Work context", "## Work Context")  # capital C
    with pytest.raises(ValidationError, match="rename.*Work Context.*Work context"):
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))
```

(Note the test relies on `_v2_body()` and `LEGACY_BODY` coexisting; the legacy body tests still use `LEGACY_BODY`. Once V6+V7 land in Tasks 5-6, the legacy single-body test gets deleted and replaced.)

- [ ] **Step 3: Run tests, confirm RED.**

```bash
.venv/bin/pytest tests/test_validate.py::test_v2_fixture_passes_v4 \
                 tests/test_validate.py::test_missing_section_is_refused_with_section_name \
                 tests/test_validate.py::test_sections_out_of_order_are_refused \
                 tests/test_validate.py::test_section_heading_typo_is_refused_with_rename_hint -v
```

Expected: failures because `validate_payload` does not yet check section structure.

- [ ] **Step 4: Implement V4** in `validate.py`. Add `parse_sections` and the V4 check. Insert the helper at module level and the rule into `validate_payload` AFTER the city check, BEFORE the legacy body word check. Use Unicode NFC normalization so heading comparison is stable across keyboard layouts:

```python
import re
import unicodedata
# ... existing imports ...
from skills.mesh_trajectory.schema import (
    SCHEMA_FIELDS, REQUIRED_FIELDS, SCHEMA_VERSION,
    ACCEPTED_SCHEMA_VERSIONS, MIGRATION_CUTOFF_DATE,
    SECTION_FIELDS, SECTION_WORD_CAPS, TOTAL_BODY_WORD_CAP,
)


_H2_RE = re.compile(r"^##\s+(.+?)\s*$")


def parse_sections(body: str) -> dict[str, str]:
    """Walk markdown body, return ordered {h2_text: section_body} dict.

    Heading text is NFC-normalized and stripped of trailing whitespace.
    Section bodies preserve interior whitespace; leading/trailing newlines
    are stripped. The returned dict preserves insertion order (Python 3.7+).
    """
    sections: dict[str, str] = {}
    current_heading: str | None = None
    current_lines: list[str] = []
    for line in body.splitlines():
        m = _H2_RE.match(line)
        if m:
            if current_heading is not None:
                sections[current_heading] = "\n".join(current_lines).strip()
            current_heading = unicodedata.normalize("NFC", m.group(1))
            current_lines = []
        else:
            if current_heading is not None:
                current_lines.append(line)
            # Lines before the first H2 are ignored (no heading to attach to).
    if current_heading is not None:
        sections[current_heading] = "\n".join(current_lines).strip()
    return sections
```

Then, inside `validate_payload`, after the city check and before the legacy body check (we will REMOVE the legacy check in Task 6; for now both run), insert:

```python
    # V4: body has exactly SECTION_FIELDS H2 headings, in declared order.
    # Skip V4 entirely for v1 payloads (they have a single-paragraph body).
    if sv == 2:
        sections = parse_sections(body)
        actual = list(sections.keys())
        expected = list(SECTION_FIELDS)
        # Detect typos: a heading that NFC-normalizes case-insensitively
        # to an expected heading but is not exactly equal.
        for a in actual:
            for e in expected:
                if a != e and a.lower() == e.lower():
                    raise ValidationError(
                        f"section heading typo: rename '{a}' to '{e}'"
                    )
        missing = [e for e in expected if e not in actual]
        if missing:
            raise ValidationError(
                f"missing required section(s): {missing}"
            )
        if actual != expected:
            raise ValidationError(
                f"sections must appear in this order: {expected}; got: {actual}"
            )
```

- [ ] **Step 5: Run tests, confirm GREEN.**

```bash
.venv/bin/pytest tests/test_validate.py tests/test_schema.py -v
```

Expected: all V4 tests now pass. Legacy single-body tests still pass (we kept the BODY_MIN/MAX check).

- [ ] **Step 6: Commit.**

```bash
git add skills/mesh_trajectory/scripts/validate.py tests/test_validate.py tests/fixtures/user_v2_valid.md
git commit -m "feat(validate): V4 body has exactly SECTION_FIELDS H2 headings in order"
```

---

## Task 4: Validator V5 - no extra H2 headings outside SECTION_FIELDS

**Files:**
- Modify: `skills/mesh_trajectory/scripts/validate.py`
- Modify: `tests/test_validate.py`

V4 catches missing/typo'd/out-of-order. V5 catches extras (e.g., user adds `## Personal context`).

- [ ] **Step 1: Write failing test** in `tests/test_validate.py` (append):

```python
def test_extra_h2_heading_in_body_is_refused():
    body = _v2_body() + "\n\n## Personal context\n\nfamily of 4 in indiranagar"
    with pytest.raises(ValidationError, match="unexpected section.*Personal context"):
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))


def test_extra_h2_at_top_of_body_is_refused():
    body = "## Bonus\n\nfree text\n\n" + _v2_body()
    with pytest.raises(ValidationError, match="unexpected section.*Bonus"):
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))
```

- [ ] **Step 2: Run tests, confirm RED.**

```bash
.venv/bin/pytest tests/test_validate.py::test_extra_h2_heading_in_body_is_refused tests/test_validate.py::test_extra_h2_at_top_of_body_is_refused -v
```

- [ ] **Step 3: Implement V5** in `validate.py`. Insert this check inside the `if sv == 2:` block, AFTER the V4 missing/order checks but BEFORE V6 (next task):

```python
        # V5: no H2 headings outside SECTION_FIELDS.
        unexpected = [a for a in actual if a not in expected]
        if unexpected:
            raise ValidationError(
                f"unexpected section heading(s) in body: {unexpected}; "
                f"only {list(SECTION_FIELDS)} are allowed"
            )
```

Note: the order matters. V4's "missing" check raises if any `SECTION_FIELDS` heading is absent; V5 raises only if extras are present beyond the expected set. With the V4 + V5 ordering above, a body with `Bonus` + the 4 expected sections will hit V4's "out of order" path first because `actual = [Bonus, Work context, ...]` does not equal `[Work context, Top of mind, ...]`. To keep the V5 error message precise, move the "extras" check BEFORE the "out of order" check. Adjust V4 implementation:

Replace the V4 block with:

```python
    if sv == 2:
        sections = parse_sections(body)
        actual = list(sections.keys())
        expected = list(SECTION_FIELDS)

        # Typo detection
        for a in actual:
            for e in expected:
                if a != e and a.lower() == e.lower():
                    raise ValidationError(
                        f"section heading typo: rename '{a}' to '{e}'"
                    )

        # V5: extras
        unexpected = [a for a in actual if a not in expected]
        if unexpected:
            raise ValidationError(
                f"unexpected section heading(s) in body: {unexpected}; "
                f"only {list(SECTION_FIELDS)} are allowed"
            )

        # V4 (continued): missing
        missing = [e for e in expected if e not in actual]
        if missing:
            raise ValidationError(f"missing required section(s): {missing}")

        # V4 (continued): order
        if actual != expected:
            raise ValidationError(
                f"sections must appear in this order: {expected}; got: {actual}"
            )
```

- [ ] **Step 4: Run tests, confirm GREEN.**

```bash
.venv/bin/pytest tests/test_validate.py tests/test_schema.py -v
```

- [ ] **Step 5: Commit.**

```bash
git add skills/mesh_trajectory/scripts/validate.py tests/test_validate.py
git commit -m "feat(validate): V5 refuse H2 headings outside SECTION_FIELDS"
```

---

## Task 5: Validator V6 - per-section word caps

**Files:**
- Modify: `skills/mesh_trajectory/scripts/validate.py`
- Modify: `tests/test_validate.py`

Each section must respect `SECTION_WORD_CAPS[section]`. Word counting matches `len(text.split())` (whitespace tokens) for consistency with the legacy body check; this is an order-of-magnitude tool, not linguistic precision.

- [ ] **Step 1: Write failing tests** in `tests/test_validate.py` (append):

```python
def test_section_over_its_word_cap_is_refused_with_actual_count():
    # "Work context" cap is 50; produce 51 words.
    long_section = " ".join(["word"] * 51)
    body = _v2_body(**{"Work context": long_section})
    with pytest.raises(ValidationError, match=r"Work context.*51.*50"):
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))


def test_each_section_has_its_own_cap():
    # "Recent months" cap is 100; produce 101 words.
    long_section = " ".join(["word"] * 101)
    body = _v2_body(**{"Recent months": long_section})
    with pytest.raises(ValidationError, match=r"Recent months.*101.*100"):
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))


def test_section_at_exact_cap_passes():
    exact = " ".join(["word"] * 50)
    body = _v2_body(**{"Work context": exact})
    # Should not raise on V6 (other rules may still raise but not V6).
    try:
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))
    except ValidationError as e:
        assert "Work context" not in str(e), f"V6 should pass at exact cap: {e}"
```

- [ ] **Step 2: Run tests, confirm RED.**

```bash
.venv/bin/pytest tests/test_validate.py -k "section_over_its_word_cap or each_section or section_at_exact" -v
```

- [ ] **Step 3: Implement V6** in `validate.py`. Append inside the `if sv == 2:` block, AFTER the V4 order check:

```python
        # V6: each section <= SECTION_WORD_CAPS[section]
        for name in SECTION_FIELDS:
            wc = len(sections[name].split())
            cap = SECTION_WORD_CAPS[name]
            if wc > cap:
                raise ValidationError(
                    f"section '{name}' has {wc} words; cap is {cap}"
                )
```

- [ ] **Step 4: Run tests, confirm GREEN.**

```bash
.venv/bin/pytest tests/test_validate.py tests/test_schema.py -v
```

- [ ] **Step 5: Commit.**

```bash
git add skills/mesh_trajectory/scripts/validate.py tests/test_validate.py
git commit -m "feat(validate): V6 enforce per-section word caps"
```

---

## Task 6: Validator V7 - total body word cap + retire legacy single-body check

**Files:**
- Modify: `skills/mesh_trajectory/scripts/validate.py`
- Modify: `tests/test_validate.py`

V7 caps the total body at `TOTAL_BODY_WORD_CAP` (250). For v2 payloads V7 supersedes the legacy `BODY_MIN_WORDS / BODY_MAX_WORDS` check. For v1 payloads (migration window) the legacy check still applies. Once the cutoff passes (2026-06-01), V3 already refuses v1, so the legacy check effectively retires.

- [ ] **Step 1: Write failing tests** in `tests/test_validate.py` (append). Also DELETE `test_body_too_short_is_refused_legacy` and `test_body_too_long_is_refused` if they exist as standalone v2-pinned tests (they target the legacy check; v2 has its own path now).

```python
def test_total_body_over_cap_is_refused_even_when_each_section_under_its_cap():
    # Set every section to within-cap words but engineer the total to exceed 250.
    # 50 + 75 + 100 + 75 = 300 max if every cap is hit; cap-then-trim to >250 but each within.
    sections = {
        "Work context":          " ".join(["w"] * 50),   # 50
        "Top of mind":           " ".join(["w"] * 70),   # 70
        "Recent months":         " ".join(["w"] * 80),   # 80
        "Long-term background":  " ".join(["w"] * 51),   # 51 -> total 251
    }
    body = _v2_body(**sections)
    with pytest.raises(ValidationError, match=r"total body.*251.*250"):
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))


def test_total_body_at_exact_cap_passes():
    sections = {
        "Work context":          " ".join(["w"] * 50),
        "Top of mind":           " ".join(["w"] * 75),
        "Recent months":         " ".join(["w"] * 75),
        "Long-term background":  " ".join(["w"] * 50),
    }  # total 250
    body = _v2_body(**sections)
    try:
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))
    except ValidationError as e:
        assert "total body" not in str(e), f"V7 should pass at exact cap: {e}"


def test_v1_body_word_check_still_runs_during_migration_window():
    # v1 uses the legacy 50-300 word check; too-short body is refused.
    with pytest.raises(ValidationError, match="body must be"):
        validate_payload(VALID_V1, body="too short", today=date(2026, 5, 1))


def test_v2_body_below_50_words_is_NOT_refused_by_legacy_check():
    # v2 path skips the legacy word check; only V7 (total cap) applies on the
    # high end. Each section having a cap implicitly bounds the low end via V4.
    sections = {
        "Work context":          "one",
        "Top of mind":           "two",
        "Recent months":         "three",
        "Long-term background":  "four",
    }
    body = _v2_body(**sections)
    # Should not raise on the legacy "body too short" rule.
    try:
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))
    except ValidationError as e:
        assert "body must be" not in str(e), f"v2 should not hit legacy word check: {e}"
```

- [ ] **Step 2: Run tests, confirm RED.**

- [ ] **Step 3: Implement V7 + branch the legacy check** in `validate.py`. The new shape:

```python
        # V6: per-section caps (existing from Task 5)
        for name in SECTION_FIELDS:
            wc = len(sections[name].split())
            cap = SECTION_WORD_CAPS[name]
            if wc > cap:
                raise ValidationError(
                    f"section '{name}' has {wc} words; cap is {cap}"
                )

        # V7: total body cap
        total = sum(len(sections[name].split()) for name in SECTION_FIELDS)
        if total > TOTAL_BODY_WORD_CAP:
            raise ValidationError(
                f"total body has {total} words; cap is {TOTAL_BODY_WORD_CAP}"
            )

    else:
        # v1 only: legacy single-body word check (50-300).
        word_count = len(body.split())
        if word_count < BODY_MIN_WORDS or word_count > BODY_MAX_WORDS:
            raise ValidationError(
                f"body must be {BODY_MIN_WORDS}-{BODY_MAX_WORDS} words, got {word_count}"
            )
```

Important: REMOVE the now-unconditional legacy word check at the bottom of `validate_payload`. The new shape has the legacy check ONLY in the `else` branch (sv == 1). Move the legacy check into the else; do not leave it running for v2.

- [ ] **Step 4: Run tests, confirm GREEN.**

```bash
.venv/bin/pytest tests/test_validate.py tests/test_schema.py -v
```

- [ ] **Step 5: Commit.**

```bash
git add skills/mesh_trajectory/scripts/validate.py tests/test_validate.py
git commit -m "feat(validate): V7 total body cap; scope legacy word check to v1 only"
```

---

## Task 7: Validator V8 - PII stop-list pass

**Files:**
- Create: `skills/mesh_trajectory/pii_stoplist.txt`
- Modify: `skills/mesh_trajectory/scripts/validate.py`
- Modify: `tests/test_validate.py`

V8 catches obvious leaks: a phone number, an email other than the user's own, an address-like pattern, or a hardcoded stop-list term (partner / household). Conservative; failure messages name the offending substring so the user can rephrase. The stop-list lives at `skills/mesh_trajectory/pii_stoplist.txt`. Per-user override at `~/.mesh/pii_extra.txt`.

- [ ] **Step 1: Create the stop-list file** at `skills/mesh_trajectory/pii_stoplist.txt`:

```
# MESH PII stop-list (V0).
# One term per line. Lines starting with # are comments.
# Matched as case-insensitive whole-word substring against the body.
# Per-user override: add a line to ~/.mesh/pii_extra.txt (same format).
# Conservative seed; expand as we learn from dogfood.

# Common partner / household relationship terms (intentionally generic).
my wife
my husband
my partner
my fiance
my fiancee
my girlfriend
my boyfriend
my mom
my dad
my mother
my father
my son
my daughter
my child
my kids
my children
home address
home phone
landlord
landlady
```

- [ ] **Step 2: Write failing tests** in `tests/test_validate.py` (append):

```python
def test_phone_number_in_body_is_refused():
    body = _v2_body(**{"Top of mind": "call me on +91 98765 43210 to chat"})
    with pytest.raises(ValidationError, match=r"PII.*phone.*98765"):
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))


def test_email_other_than_self_in_body_is_refused():
    body = _v2_body(**{"Top of mind": "ping ravi@otherco.com about the eval harness"})
    with pytest.raises(ValidationError, match=r"PII.*email.*ravi@otherco.com"):
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))


def test_users_own_email_in_body_is_allowed():
    body = _v2_body(**{"Top of mind": "you can also reach me at asha@example.com"})
    # asha@example.com is VALID_V2["email"]; V8 should not refuse.
    try:
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))
    except ValidationError as e:
        assert "PII" not in str(e), f"own email should be allowed: {e}"


def test_address_pattern_in_body_is_refused():
    body = _v2_body(**{"Work context": "office at #4-21B HSR Layout, Bengaluru"})
    with pytest.raises(ValidationError, match=r"PII.*address"):
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))


def test_stoplist_term_in_body_is_refused():
    body = _v2_body(**{"Top of mind": "balancing this with my wife starting a new role"})
    with pytest.raises(ValidationError, match=r"PII.*stoplist.*my wife"):
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))


def test_per_user_override_extends_stoplist(tmp_path, monkeypatch):
    # Point the loader at a user override containing a custom term.
    override = tmp_path / "pii_extra.txt"
    override.write_text("# my override\nproject helios\n")
    monkeypatch.setenv("MESH_PII_EXTRA_PATH", str(override))
    body = _v2_body(**{"Top of mind": "main thrust this month is project helios"})
    with pytest.raises(ValidationError, match=r"PII.*stoplist.*project helios"):
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))
```

- [ ] **Step 3: Run tests, confirm RED.**

- [ ] **Step 4: Implement V8 + stop-list loader** in `validate.py`. Add at module level:

```python
import os

_PHONE_RE = re.compile(
    # Indian mobile (+91 98765 43210, 98765 43210, 9876543210)
    # and generic international/US (+1 415 555 0123, 415-555-0123, etc.)
    r"(?:(?:\+\d{1,3}[\s\-]?)?\d{3,5}[\s\-]?\d{3,4}[\s\-]?\d{3,4})"
)

_EMAIL_RE = re.compile(r"[\w\.\-+]+@[\w\.\-]+\.[A-Za-z]{2,}")

_ADDRESS_RE = re.compile(
    # Unit-like patterns: #4-21B, 4/21, A-21, plus common Bengaluru area suffixes.
    # Conservative; false-positives are acceptable, user can rephrase.
    r"(?:#\s*\d+[A-Z]?[-/]?\d*[A-Z]?"
    r"|\b\d+[A-Z]?[-/]\d+[A-Z]?\b"
    r"|\b(?:HSR Layout|Indiranagar|Koramangala|Whitefield|Marathahalli|Jayanagar|Bellandur)\b)",
    re.IGNORECASE,
)


def _load_stoplist() -> list[str]:
    """Load the committed stop-list plus the per-user override (if present).

    Override path: env $MESH_PII_EXTRA_PATH, else ~/.mesh/pii_extra.txt.
    """
    base = Path(__file__).parent.parent / "pii_stoplist.txt"
    terms: list[str] = []
    for path in (base, Path(os.environ.get("MESH_PII_EXTRA_PATH") or Path.home() / ".mesh" / "pii_extra.txt")):
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            terms.append(line)
    return terms
```

Then, inside `validate_payload`, add the V8 block at the END of the `if sv == 2:` branch (after V7):

```python
        # V8: PII stop-list pass.
        own_email = frontmatter["email"].lower()
        body_lower = body.lower()

        # Phone
        m = _PHONE_RE.search(body)
        if m:
            raise ValidationError(f"PII (phone) in body: '{m.group(0)}'")
        # Email other than self
        for em in _EMAIL_RE.findall(body):
            if em.lower() != own_email:
                raise ValidationError(f"PII (email) in body: '{em}'")
        # Address pattern
        m = _ADDRESS_RE.search(body)
        if m:
            raise ValidationError(f"PII (address) in body: '{m.group(0)}'")
        # Stop-list (case-insensitive, whole-word boundary)
        for term in _load_stoplist():
            pattern = r"\b" + re.escape(term.lower()) + r"\b"
            if re.search(pattern, body_lower):
                raise ValidationError(f"PII (stoplist) in body: '{term}'")
```

A subtle interaction: the phone regex is greedy and may match something inside a date or version string. If V8 false-positives on legitimate content during dogfood (Task 13), tighten the regex in a follow-on commit; do NOT relax tests, ADD new fixture tests for the false-positive shape and adjust the regex.

- [ ] **Step 5: Run tests, confirm GREEN.**

```bash
.venv/bin/pytest tests/test_validate.py tests/test_schema.py -v
```

- [ ] **Step 6: Sanity check** the v2 fixture still passes the WHOLE pipeline:

```bash
.venv/bin/python -c "
from datetime import date
from skills.mesh_trajectory.scripts.validate import validate_payload, parse_markdown
from pathlib import Path
fm, body = parse_markdown(Path('tests/fixtures/user_v2_valid.md'))
validate_payload(fm, body, today=date(2026, 5, 1))
print('OK')
"
```

Expected: `OK`. If V8 false-positives on the fixture (e.g., the "8 years" string trips phone), edit the fixture to use a less-ambiguous phrasing rather than relaxing V8.

- [ ] **Step 7: Commit.**

```bash
git add skills/mesh_trajectory/pii_stoplist.txt skills/mesh_trajectory/scripts/validate.py tests/test_validate.py
git commit -m "feat(validate): V8 PII stop-list (phone, email, address, term list)"
```

---

## Task 8: Section-extraction prompts

**Files:**
- Create: `skills/mesh_trajectory/prompts/sections/work_context.md`
- Create: `skills/mesh_trajectory/prompts/sections/top_of_mind.md`
- Create: `skills/mesh_trajectory/prompts/sections/recent_months.md`
- Create: `skills/mesh_trajectory/prompts/sections/long_term_background.md`

Each prompt takes the project summaries, the why-seed, and (optionally) the prior section text from the user's existing file (for continuity across syncs and for the v1->v2 migration case where prior is the entire v1 body). Each emits ONLY the section body text (no heading, no preamble); the controller in `SKILL.md` adds `## <Section>` and assembles.

- [ ] **Step 1: Write `work_context.md`:**

```markdown
# Section: Work context

You are extracting the user's CURRENT WORK CONTEXT for their MESH trajectory.

## What this section is

A factual statement of role, team, and what the user owns RIGHT NOW. Reads like the first paragraph of their LinkedIn-style positioning. No projects-in-flight (those go in "Top of mind"), no history (that goes in "Recent months" or "Long-term background"), no household/personal context (out of scope for this file).

## Output rules

- <= 50 words. Hard cap; longer output will be refused at validation.
- One short paragraph, no headings, no bullets.
- Plain text only.
- No internal codenames, partner/customer names, phone numbers, or addresses (the privacy lint and V8 stop-list will refuse these).
- If you cannot tell from the inputs what the user's current role is, say "Role and team unclear from recent sessions" and stop. Do NOT invent.

## Inputs

PROJECT SUMMARIES (one block per project the user has worked on, with bucket label CENTRAL/REGULAR/OCCASIONAL/ONE-OFF):

{{project_summaries}}

WHY SEED (one-line user-confirmed framing of why they're doing this work):

{{why_seed}}

PRIOR SECTION (the user's existing "Work context" from their last sync, or empty on first sync; for v1 migration this will be the user's full v1 body):

{{prior_section}}

## Now produce the section body

Output ONLY the section body text. No "## Work context" heading. No preamble. No code fences.
```

- [ ] **Step 2: Write `top_of_mind.md`:**

```markdown
# Section: Top of mind

You are extracting the user's TOP OF MIND for their MESH trajectory: what they are actively working on or thinking about RIGHT NOW (this and next ~4 weeks).

## What this section is

The active threads. The thing that comes out when someone asks "what are you up to lately?" Captures direction and tension - what they are wrestling with, not just what is on the calendar. Look for the CENTRAL and REGULAR project buckets in the inputs; weight ONE-OFFs only if they are the most recent.

## Output rules

- <= 75 words. Hard cap.
- One paragraph, no headings, no bullets.
- Specific over generic. "Migrating an in-house agent harness onto a unified runtime" beats "working on agent infrastructure."
- No internal codenames, partner/customer names, phone numbers, addresses.
- If recent activity is sparse, say so honestly. Do NOT invent activity.

## Inputs

PROJECT SUMMARIES:

{{project_summaries}}

WHY SEED:

{{why_seed}}

PRIOR SECTION (existing "Top of mind", or empty / v1 body):

{{prior_section}}

## Now produce the section body

Output ONLY the section body text. No heading. No preamble. No code fences.
```

- [ ] **Step 3: Write `recent_months.md`:**

```markdown
# Section: Recent months

You are extracting the user's RECENT MONTHS for their MESH trajectory: what they have shipped or shifted in the last 3-6 months.

## What this section is

Past-tense. Outcomes, not activity. Reads like the highlights paragraph of a quarterly review. Look across all project buckets; CENTRAL and REGULAR carry more weight than ONE-OFFs.

## Output rules

- <= 100 words. Hard cap.
- One paragraph, no headings, no bullets.
- Concrete over vague. "Shipped v2 of the underwriting agent stack" beats "improved customer experience."
- Quantify when the inputs quantify (latency cuts, accuracy lifts, throughput).
- No internal codenames, partner/customer names, phone numbers, addresses.

## Inputs

PROJECT SUMMARIES:

{{project_summaries}}

WHY SEED:

{{why_seed}}

PRIOR SECTION (existing "Recent months", or empty / v1 body):

{{prior_section}}

## Now produce the section body

Output ONLY the section body text. No heading. No preamble. No code fences.
```

- [ ] **Step 4: Write `long_term_background.md`:**

```markdown
# Section: Long-term background

You are extracting the user's LONG-TERM BACKGROUND for their MESH trajectory: durable expertise on a 1+ year horizon.

## What this section is

The substrate. What you would describe to someone asking "who is this person, professionally?" beyond the current job. Years of experience, prior domains, languages and tools they are at home in. Stable across syncs - this section should not change much week to week.

## Output rules

- <= 75 words. Hard cap.
- One paragraph, no headings, no bullets.
- Past-and-present tense. "Eight years building backend systems" plus current "comfortable in Python, Go."
- No internal codenames, partner/customer names, phone numbers, addresses.

## Inputs

PROJECT SUMMARIES:

{{project_summaries}}

WHY SEED:

{{why_seed}}

PRIOR SECTION (existing "Long-term background", or empty / v1 body):

{{prior_section}}

## Now produce the section body

Output ONLY the section body text. No heading. No preamble. No code fences.
```

- [ ] **Step 5: Verify the prompts are loadable** (no test, just a smoke):

```bash
ls skills/mesh_trajectory/prompts/sections/
# Expected: 4 files
for f in skills/mesh_trajectory/prompts/sections/*.md; do
  grep -c "{{project_summaries}}" "$f"  # 1
  grep -c "{{why_seed}}" "$f"           # 1
  grep -c "{{prior_section}}" "$f"      # 1
done
```

Each file should report `1 1 1`.

- [ ] **Step 6: Commit.**

```bash
git add skills/mesh_trajectory/prompts/sections/
git commit -m "feat(prompts): four section-specific extraction prompts"
```

---

## Task 9: SKILL.md - replace single-body synthesize with 4-section loop

**Files:**
- Modify: `skills/mesh_trajectory/SKILL.md`

Replace step 13 (single synthesize) with a 4-pass section loop. Update step 17 (final review) framing to walk the user through all four sections in turn. Keep steps 1-12 (greet/Q&A/extract/digests/groups/per-project/why-seed) unchanged. Keep steps 14-16 (intermediate cleanup, lint, interactive resolution) unchanged in shape; lint runs against the assembled body. Update the privacy contract section to mention the new section-aware shape. Update the launch-window disclosure in step 17 to also reference V8.

- [ ] **Step 1: Replace step 13** in `skills/mesh_trajectory/SKILL.md`. Find the current step 13 and replace its body with this exact text:

```markdown
13. **Synthesize the four sections.** For each `<section>` in this exact order: `Work context`, `Top of mind`, `Recent months`, `Long-term background`:
    a. Read `prompts/sections/<snake_case>.md` (e.g., `work_context.md`, `top_of_mind.md`, `recent_months.md`, `long_term_background.md`).
    b. Substitute `{{project_summaries}}` (from `/tmp/mesh_project_summaries.txt`), `{{why_seed}}` (from `/tmp/mesh_why.txt`), and `{{prior_section}}` (the existing same-named section from the user's current `users/<email>.md` in the local mesh-data clone, parsed via `parse_sections`; empty string on first sync; for a v1 file the entire body string).
    c. Generate the section body in your response. The model output MUST be plain text under the per-section word cap (50 / 75 / 100 / 75 words for the four sections respectively). If your output exceeds the cap, regenerate with a "tighter, drop the least-essential clause" instruction.
    d. Append `## <Section>\n\n<section_body>\n\n` to `/tmp/mesh_body.md` in the canonical order. Use `>> /tmp/mesh_body.md` from the controller; create the file fresh at the start of step 13a (`: > /tmp/mesh_body.md`).
    e. Show the user the section just written and ask: "Does this section land? Edit, regenerate, or accept?" Loop on Edit/Regenerate before moving to the next section.

    After all four sections are written, the assembled `/tmp/mesh_body.md` will look like:
    ```
    ## Work context

    <50 words max>

    ## Top of mind

    <75 words max>

    ## Recent months

    <100 words max>

    ## Long-term background

    <75 words max>
    ```

    The pre-push validator (V4-V7) refuses any deviation from this shape; V8 refuses obvious PII (phone, foreign email, address, stop-list terms).
```

- [ ] **Step 2: Update step 17** (FINAL REVIEW). Find the current step 17 and replace its body with this exact text:

```markdown
17. **FINAL REVIEW (load-bearing privacy gate).** This is the LAST point at which the user can prevent content from leaving their machine. Show the user the COMPLETE updated `/tmp/mesh_body.md` in a code block, exactly as it will appear in mesh-data. Then for EACH of the four sections in turn, ask one focused question via `AskUserQuestion`:

    > **Section: <Work context | Top of mind | Recent months | Long-term background>**
    > <render this section's body, exactly>
    >
    > **Launch-window note (2026-05-01):** mesh-data is currently PUBLIC. Anyone on the internet can read this section until the founder reverts the repo to private after the launch event. The PII stop-list (V8) caught the obvious leaks; this is your last chance to catch what it missed.
    >
    > Things to look for in this section:
    > - Internal codenames, partner names, customer names the lint missed
    > - Phrasing that reveals more than you'd say in a public LinkedIn post
    > - Wording you'd regret if a future hiring manager read it

    Options for each section: "Keep section as-is", "Edit (paste replacement)", "Regenerate from project summaries", "You decide".

    On "Edit": accept the user's replacement text, write it back into `/tmp/mesh_body.md` between the section's `## <name>` heading and the next `##`, loop back to this step for the same section.

    On "Regenerate": loop back to step 13 for THIS section only (re-read the prompt, re-substitute, append). The other sections are not touched.

    After all four sections are reviewed and accepted, ask once more: "Push the entire body to mesh-data, or abort?" with options "Push", "Abort (delete everything)", "You decide". On "Abort": delete all `/tmp/mesh_*` and stop, no push.
```

- [ ] **Step 3: Update the Privacy contract section** at the bottom of SKILL.md. Append this paragraph to the existing list:

```markdown
- The body is now four ordered H2 sections (`Work context`, `Top of mind`, `Recent months`, `Long-term background`). The pre-push validator refuses any deviation from this shape (V4 missing/order, V5 extras, V6 per-section caps, V7 total cap 250 words, V8 PII stop-list). The schema version is bumped to 2; v1 files are accepted by the orchestrator until 2026-06-01 via a crude adapter (the entire v1 body is treated as the `Recent months` section).
```

- [ ] **Step 4: Sanity checks:**

```bash
grep -c "—" skills/mesh_trajectory/SKILL.md   # 0 (no em-dashes)
grep -c "Work context" skills/mesh_trajectory/SKILL.md   # >= 3
grep -c "prompts/sections/" skills/mesh_trajectory/SKILL.md   # >= 1
grep -c "schema_version 2\|schema_version: 2\|schema_version is bumped to 2" skills/mesh_trajectory/SKILL.md   # >= 1
.venv/bin/pytest -q | tail -3   # all tests still passing
```

- [ ] **Step 5: Commit.**

```bash
git add skills/mesh_trajectory/SKILL.md
git commit -m "feat(skill): 4-section synthesize loop and per-section final review"
```

---

## Task 10: Matching prompt - read sections + weights (`compose.md`)

**Files:**
- Modify: `skills/mesh_orchestrator/prompts/compose.md`

The matcher's input shape now includes a `sections` field per user (added by the load_users update in Task 11). The prompt explains how to read it, weights each section, and biases for Guide x Explorer pairs. The output JSON contract is unchanged.

- [ ] **Step 1: Replace `compose.md`** with this body:

```markdown
# Composition prompt for MESH dinner tables

You are MESH's matching engine. You read every available user's trajectory and compose tables of 6 for an in-person dinner this Saturday in Bengaluru.

## Inputs you have

- Dinner date: {{dinner_date}}
- Venue: {{venue}}
- Available users (each as a JSON object below). Fields:
  - `name`, `email`, `role`, `do_not_match`
  - `sections`: an object with four keys, in this order:
    - `Work context` (<= 50 words): factual current role + team + what they own
    - `Top of mind` (<= 75 words): active threads, this/next 4 weeks
    - `Recent months` (<= 100 words): what shipped and shifted in the last 3-6 months
    - `Long-term background` (<= 75 words): durable expertise, 1+ year horizon
  - `body`: the assembled markdown body (kept for backward compatibility; prefer `sections`)

  For users on schema_version 1 (legacy), the `sections` object will have only `Recent months` populated with the full original body; the other three section strings will be empty. Treat such users as having unknown role/horizon detail; rely on `Recent months` for matching.

## What to optimize

Compose tables that maximize the chance of a "this changed my career" conversation. The signal you're looking for, in priority order:

1. **Guide x Explorer (highest value):** high overlap on `Long-term background` (same substrate) + low overlap on `Top of mind` (different velocities on that substrate). One person three months deep on a topic the other is just exploring. These are the dinners that bend trajectories.
2. **Fellow Explorers:** high overlap on `Top of mind` + similar `Recent months` shape. Shared open question, similar velocity. Good energy.
3. **Adjacent problem spaces:** overlap on `Long-term background` substrate, different vantage point in `Work context` (infra vs product vs research).

When weighing similarity across sections, treat:

- `Top of mind`            weight ~0.4 (near-term compatibility)
- `Recent months`          weight ~0.4 (trajectory similarity)
- `Long-term background`   weight ~0.2 (substrate fit)
- `Work context`           constraint, not score: drives no-same-company filter and role-diversity preference

For each composed table, ensure at least one Guide x Explorer pair where the candidate pool allows. State the pair explicitly in `why_this_table` ("X is three months into agent eval; Y just started exploring the same from a product angle").

## Hard constraints (NEVER violate)

- Each table has exactly 6 attendees, unless total available is 13/19/25 etc., in which case last table is 7. If total < 12, output one table only with whatever is available and flag low-quorum.
- No two attendees from the same company (infer from role and email domain).
- Respect every user's `do_not_match` list.
- A given user appears in exactly one table.

## Output format (strict JSON)

```json
{
  "dinner_date": "{{dinner_date}}",
  "venue": "{{venue}}",
  "low_quorum": false,
  "tables": [
    {
      "table": 1,
      "attendees": [
        {
          "email": "asha@example.com",
          "name": "Asha Rao",
          "role": "Founding Engineer",
          "trajectory_one_liner": "Building agent harness unification across runtimes"
        }
      ],
      "why_this_table": "One paragraph explaining the trajectory intersections that make this table interesting. Reference specific people by first name. Call out the Guide x Explorer pairs and which sections drove the pairing."
    }
  ]
}
```

Output ONLY the JSON. No preamble. No code fences. Just the raw JSON object.

## Users

{{users_json}}
```

- [ ] **Step 2: Sanity checks:**

```bash
grep -c "—" skills/mesh_orchestrator/prompts/compose.md   # 0
grep -c "Work context\|Top of mind\|Recent months\|Long-term background" skills/mesh_orchestrator/prompts/compose.md   # >= 4
grep -c "Guide x Explorer" skills/mesh_orchestrator/prompts/compose.md   # >= 2
grep -c '"trajectory_one_liner"' skills/mesh_orchestrator/prompts/compose.md   # 1 (output contract unchanged)
.venv/bin/pytest tests/test_parse_response.py -v   # parse_response tests still pass
```

- [ ] **Step 3: Commit.**

```bash
git add skills/mesh_orchestrator/prompts/compose.md
git commit -m "feat(orchestrator): compose.md reads sections with weights; output JSON unchanged"
```

---

## Task 11: Orchestrator v1 adapter - populate `User.sections`

**Files:**
- Create: `tests/fixtures/user_v1_legacy.md`
- Modify: `skills/mesh_orchestrator/scripts/load_users.py`
- Modify: `tests/test_load_users.py`

`load_users_for_date` gains a `sections: dict[str, str]` field on the `User` dataclass. For v2 files it parses sections via `parse_sections` (re-exported from `validate.py`). For v1 files, the entire body becomes `Recent months`; the other three sections are empty strings. The existing `body` field stays populated with the raw body text so existing callers do not break.

- [ ] **Step 1: Create the v1 fixture** at `tests/fixtures/user_v1_legacy.md`:

```markdown
---
schema_version: 1
name: Legacy User
email: legacy@example.com
linkedin_url: https://linkedin.com/in/legacyuser
role: Senior Engineer
city: Bengaluru
available_saturdays:
  - "2026-05-09"
---

This is the original single-paragraph body from a schema_version 1 user file. It contains a mix of role, recent work, and substrate that the v2 schema would have decomposed into four sections. The orchestrator's v1 adapter treats this entire paragraph as the Recent months section so the matcher can still reason about this user during the migration window. Word count here is comfortably inside the legacy 50-300 range so V3 accepts it pre-cutoff.
```

- [ ] **Step 2: Write failing tests** in `tests/test_load_users.py`. Append to the existing tests:

```python
from skills.mesh_trajectory.schema import SECTION_FIELDS

FIXTURES = Path(__file__).parent / "fixtures"


def test_v2_user_exposes_parsed_sections(tmp_path):
    # Copy the v2 fixture into a tmp users/ dir.
    (tmp_path / "users").mkdir()
    (tmp_path / "users" / "asha_at_example_com.md").write_text(
        (FIXTURES / "user_v2_valid.md").read_text()
    )
    users = load_users_for_date(tmp_path, "2026-05-09")
    assert len(users) == 1
    u = users[0]
    assert set(u.sections.keys()) == set(SECTION_FIELDS)
    assert "founding engineer" in u.sections["Work context"].lower()
    assert "agent harness" in u.sections["Top of mind"].lower()


def test_v1_user_has_only_recent_months_populated(tmp_path):
    (tmp_path / "users").mkdir()
    (tmp_path / "users" / "legacy_at_example_com.md").write_text(
        (FIXTURES / "user_v1_legacy.md").read_text()
    )
    users = load_users_for_date(tmp_path, "2026-05-09")
    assert len(users) == 1
    u = users[0]
    assert set(u.sections.keys()) == set(SECTION_FIELDS)
    assert u.sections["Work context"] == ""
    assert u.sections["Top of mind"] == ""
    assert u.sections["Long-term background"] == ""
    assert "schema_version 1" in u.sections["Recent months"].lower()
    # Legacy body field still populated for any caller that looks at it.
    assert u.body == u.sections["Recent months"]


def test_user_sections_is_ordered_dict(tmp_path):
    (tmp_path / "users").mkdir()
    (tmp_path / "users" / "asha_at_example_com.md").write_text(
        (FIXTURES / "user_v2_valid.md").read_text()
    )
    users = load_users_for_date(tmp_path, "2026-05-09")
    assert list(users[0].sections.keys()) == list(SECTION_FIELDS)
```

- [ ] **Step 3: Run tests, confirm RED.**

```bash
.venv/bin/pytest tests/test_load_users.py -v
```

Expected: failures because `User` has no `sections` attribute.

- [ ] **Step 4: Implement** in `skills/mesh_orchestrator/scripts/load_users.py`. Replace the file with:

```python
"""Load users/*.md from a mesh-data clone, filter by available_saturday + city.

For schema_version 2 files, parse the body's four H2 sections and expose them
as User.sections. For schema_version 1 files (migration window only), populate
sections["Recent months"] with the entire body and leave the other three empty
so the matcher can still reason about the user. The User.body field stays
populated with the raw body string for any caller that does not yet read
sections.
"""
from dataclasses import dataclass, field
from pathlib import Path
import yaml

from skills.mesh_trajectory.scripts.validate import parse_sections
from skills.mesh_trajectory.schema import SECTION_FIELDS


@dataclass
class User:
    email: str
    name: str
    linkedin_url: str
    role: str
    city: str
    available_saturdays: list[str]
    do_not_match: list[str]
    body: str
    sections: dict[str, str] = field(default_factory=dict)


def _build_sections(schema_version: int, body: str) -> dict[str, str]:
    """Return an ordered {section_name: text} dict over SECTION_FIELDS."""
    if schema_version == 2:
        parsed = parse_sections(body)
        # Preserve canonical order; missing keys (shouldn't happen for a
        # validator-clean v2 file) become empty strings.
        return {name: parsed.get(name, "") for name in SECTION_FIELDS}
    # v1: dump full body into Recent months; other three empty.
    return {
        "Work context": "",
        "Top of mind": "",
        "Recent months": body,
        "Long-term background": "",
    }


def _parse(path: Path) -> User | None:
    text = path.read_text()
    if not text.startswith("---\n"):
        return None
    _, fm_text, body = text.split("---\n", 2)
    fm = yaml.safe_load(fm_text)
    body = body.strip()
    sats = [str(s) for s in fm["available_saturdays"]]
    return User(
        email=fm["email"],
        name=fm["name"],
        linkedin_url=fm["linkedin_url"],
        role=fm["role"],
        city=fm["city"],
        available_saturdays=sats,
        do_not_match=fm.get("do_not_match", []) or [],
        body=body,
        sections=_build_sections(int(fm["schema_version"]), body),
    )


def load_users_for_date(
    mesh_data_root: Path,
    target_date: str,
    city: str = "Bengaluru",
) -> list[User]:
    users: list[User] = []
    users_dir = mesh_data_root / "users"
    if not users_dir.exists():
        return users
    for f in sorted(users_dir.glob("*.md")):
        try:
            u = _parse(f)
        except Exception:
            continue
        if u is None:
            continue
        if u.city != city:
            continue
        if target_date not in u.available_saturdays:
            continue
        users.append(u)
    return users
```

- [ ] **Step 5: Run tests, confirm GREEN.**

```bash
.venv/bin/pytest tests/test_load_users.py tests/test_validate.py tests/test_schema.py -v
```

Expected: all passing. Existing `test_loads_only_users_available_on_target_date`, `test_user_has_body_attribute`, `test_handles_unquoted_iso_dates`, `test_skips_users_in_wrong_city` still pass (they ignore the new field).

- [ ] **Step 6: Update the orchestrator's load_users CLI snippet** in `skills/mesh_orchestrator/SKILL.md`. The current snippet at step 4 emits `u.__dict__`; that already includes the new `sections` field, so no edit needed. Verify by reading the file:

```bash
grep -n "u.__dict__" skills/mesh_orchestrator/SKILL.md
```

Just confirm the line still reads `print(json.dumps([u.__dict__ for u in load_users_for_date(...)]))`. If it does, no change. If it does not, update it to dump the User dataclass including `sections`.

- [ ] **Step 7: Commit.**

```bash
git add tests/fixtures/user_v1_legacy.md skills/mesh_orchestrator/scripts/load_users.py tests/test_load_users.py
git commit -m "feat(orchestrator): User.sections via parse_sections; v1 adapter -> Recent months"
```

---

## Task 12: spec.md - update Data Schema section to v2

**Files:**
- Modify: `spec.md`

The Data Schema section pins `schema_version: 1` and a single 200-word body. Bring it up to date with v2 and the four sections. Do NOT touch other sections of spec.md (decision framework, architecture diagram, privacy section already disclose what they need to in plan 04 and the launch-window override).

- [ ] **Step 1: Edit spec.md `## Data Schema` section.** Find the YAML block and the trailing notes; replace them with:

```markdown
## Data Schema

The complete, exhaustive payload that leaves the user's device. Any field not listed here MUST NOT be uploaded. The validator enforces this.

### Frontmatter (8 fields, frozen)

```yaml
---
# users/<email>.md frontmatter
schema_version: 2            # v2 since 2026-05-01; v1 accepted until 2026-06-01
name: string                 # full name, e.g., "Asha Rao"
email: string                # primary email, used as filename and dedup key
linkedin_url: string         # full URL
role: string                 # free-text, e.g., "Founding Engineer", "PM"
city: string                 # V0 hard-filtered to "Bengaluru"
available_saturdays:         # ISO dates the user is available
  - "2026-05-09"
  - "2026-05-16"
do_not_match:                # emails to never seat at same table (optional)
  - "ex.colleague@example.com"
embedding: null              # reserved for V0.1; always null in V0
---
```

### Body (4 ordered H2 sections, total <= 250 words)

```
## Work context
[<= 50 words: role, team, what you own]

## Top of mind
[<= 75 words: active threads, this/next 4 weeks]

## Recent months
[<= 100 words: last 3-6 months, what shipped and shifted]

## Long-term background
[<= 75 words: durable expertise, 1+ year horizon]
```

The body is the only free-text content that contains derived material from the user's sessions. The user reviews each section and the assembled whole before push. The pre-push validator (`skills/mesh_trajectory/scripts/validate.py`) refuses any deviation from this shape (V4 missing/order, V5 extras, V6 per-section caps, V7 total 250-word cap, V8 PII stop-list).

### Locked artifacts

`SCHEMA_FIELDS` and `SECTION_FIELDS` in `skills/mesh_trajectory/schema.py` are the single source of truth for the frontmatter keys and the body section names respectively. Adding, removing, or renaming either requires the same three-way commit pattern: `schema.py` + this section in `spec.md` + a failing test in `tests/test_schema.py` and `tests/test_validate.py`.

### Migration

`schema_version: 1` (single 200-word body) is accepted by both the validator and the orchestrator until `MIGRATION_CUTOFF_DATE = 2026-06-01`. Existing v1 users re-sync at their own pace via `/mesh-trajectory sync`. The orchestrator treats a v1 body as the entire `Recent months` section and leaves the other three empty (a deliberately crude adapter; the point is to push users to re-sync).

### Notes

- `do_not_match` was added during failure-mode review. Optional, costs nothing if empty.
- `embedding` is reserved so V0.1 can populate without a schema migration. V0 matching uses Claude reading the section text directly.
```

- [ ] **Step 2: Sanity checks:**

```bash
grep -c "schema_version: 2" spec.md   # >= 1
grep -c "Work context\|Top of mind\|Recent months\|Long-term background" spec.md   # >= 4
grep -c "—" spec.md   # 0 (no em-dashes)
grep -c "200-word" spec.md   # may still be > 0 in non-Data-Schema sections (architecture
                              # diagram still says "200-word trajectory body"); LEAVE
                              # those in the diagram unless the diagram itself is fully
                              # redrawn. We are NOT redrawing the architecture diagram in
                              # this iteration; spec.md sections outside Data Schema are
                              # historical at the time of v2 cutover and may be revisited
                              # in a later plan.
```

If the architecture diagram in spec.md still says "200-word trajectory body", it is acceptable for this iteration to leave it; the Data Schema section is the load-bearing contract.

- [ ] **Step 3: Commit.**

```bash
git add spec.md
git commit -m "docs(spec): Data Schema section to v2 with 4 ordered sections + migration"
```

---

## Task 13: Dogfood verification on the founder's real corpus

**Files:** none (this is a verification + log task).

End-to-end verification that the new flow produces a clean, useful, validator-passing v2 file from the founder's actual Claude Code session history. Same shape as plan 03/04 verification: run the flow, watch the failure modes, document.

- [ ] **Step 1: Pre-flight.** Pull the latest mesh-data, confirm the founder's existing v1 user file is present, confirm the local skill symlink resolves:

```bash
git -C ~/.cache/mesh-data pull --rebase
ls ~/.cache/mesh-data/users/ | head -5
ls -la ~/.claude/skills/mesh
.venv/bin/pytest -q | tail -3   # all tests pass before dogfood
```

- [ ] **Step 2: Run `/mesh-trajectory sync`** in a fresh Claude Code session. Walk the four-section synthesize loop. Note for each section:
  - Did the section land coherently on first generation, or did regeneration help?
  - Was the per-section word cap hit naturally, or did the model overshoot and need a tighter retry?
  - Did the per-section AskUserQuestion review feel proportionate (vs. heavy)?
  - For the v1 -> v2 migration, was the prior v1 body useful as `{{prior_section}}` for any of the four prompts?

- [ ] **Step 3: After all four sections are accepted**, before the lint pass, manually sanity-check `/tmp/mesh_body.md`:

```bash
cat /tmp/mesh_body.md
.venv/bin/python -c "
from skills.mesh_trajectory.scripts.validate import parse_sections
from pathlib import Path
sections = parse_sections(Path('/tmp/mesh_body.md').read_text())
for name, body in sections.items():
    wc = len(body.split())
    print(f'  {name}: {wc} words')
total = sum(len(b.split()) for b in sections.values())
print(f'  TOTAL: {total} words')
"
```

Expected: 4 sections, each under cap, total under 250.

- [ ] **Step 4: Run the lint pass + final review** (steps 15-17 of `SKILL.md`). Note:
  - How many flags did the lint raise? (Plan 03 saw a small number on the same corpus; expect similar.)
  - Did V8 false-positive on anything? If yes, capture the substring and the section it fired in for the EXECUTION LOG; do NOT relax V8 to ship the dogfood.
  - In the per-section final review, was anything caught by the user that the lint and V8 missed? That is the primary quality signal for whether the new shape is paying for itself.

- [ ] **Step 5: Push** and verify the file lands in mesh-data:

```bash
git -C ~/.cache/mesh-data pull --rebase
cat ~/.cache/mesh-data/users/<founder-email-slug>.md | head -40
.venv/bin/python -m skills.mesh_trajectory.scripts.validate ~/.cache/mesh-data/users/<founder-email-slug>.md
# Expected: OK
```

- [ ] **Step 6: Run the orchestrator end-to-end on a synthetic 6-user pool.** Build a small fixture set in a scratch dir to confirm the founder-side adapter works for a mixed v1/v2 pool:

```bash
mkdir -p /tmp/mesh_dogfood/users
# Mix: 1 v1 fixture, 1 v2 fixture, plus 4 copies with email/name swapped to make 6.
cp tests/fixtures/user_v1_legacy.md /tmp/mesh_dogfood/users/legacy_at_example_com.md
cp tests/fixtures/user_v2_valid.md /tmp/mesh_dogfood/users/asha_at_example_com.md
# (manually copy + sed-edit 4 more variants with distinct emails and matching available_saturdays)
.venv/bin/python -c "
from skills.mesh_orchestrator.scripts.load_users import load_users_for_date
from pathlib import Path
us = load_users_for_date(Path('/tmp/mesh_dogfood'), '2026-05-09')
for u in us:
    populated = [k for k, v in u.sections.items() if v]
    print(f'{u.email}: schema-derived sections populated = {populated}')
"
rm -rf /tmp/mesh_dogfood
```

Expected: legacy user reports `['Recent months']` only; v2 users report all 4. Confirms the adapter is wired through.

- [ ] **Step 7: If anything in steps 2-6 produced an unrecoverable failure, STOP.** Document the failure in this plan's EXECUTION LOG and write plan 06 to address. Do not push a broken body.

- [ ] **Step 8: If the flow ran clean**, append the EXECUTION LOG to this plan (next section) covering: task status (DONE/PARTIAL/BLOCKED + commit SHAs), what worked, what didn't, hardenings beyond the original plan, mid-flight architectural changes, dogfood metrics (per-section word counts, lint flag count, V8 false-positives), and open items handed off to plan 06.

---

## Open decisions for this iteration

| Decision | Default | Reconsider if |
|---|---|---|
| **Heading match strictness** | Exact NFC-normalized text, case-sensitive, no typo tolerance (with a typo-detection ASSIST that suggests the canonical name on a case-only mismatch). | If dogfood shows users editing headings cosmetically (e.g., bolding, trailing punctuation), tighten or relax. |
| **V8 phone regex aggressiveness** | Greedy (Indian + international shapes); may false-positive on date-like or version-like substrings. | If dogfood (Task 13) hits a false-positive on real content, ADD a fixture test for the false-positive shape and tighten the regex; do not relax V8 to ship. |
| **PII stop-list seed terms** | Generic partner / household phrases (see Task 7 file). | If dogfood reveals a category we missed (e.g., common prescription names, neighborhood nicknames), add to the seed list with a comment explaining why. |
| **Migration cutoff** | `2026-06-01` per design doc. | After dinner #1 (2026-05-09), reassess re-sync rate; the date is editable in `schema.py`. |
| **Per-section review UX** | One AskUserQuestion per section in step 17, then one final "Push or abort". | If dogfood shows the per-section review feels heavy and users want a single bulk review, fold to one review on the assembled body. |
| **`prior_section` source for v1 migration** | All four section prompts receive the entire v1 body as `{{prior_section}}`. | If sections turn out to over-fit to the v1 body (i.e., regenerate the v1 body verbatim), strip `{{prior_section}}` for sections other than `Recent months` on the migration path. |

---

## Self-review checklist

Before claiming this iteration done:

- [ ] All tests pass. New tests added in Tasks 1-7 and 11 are GREEN; no existing test was deleted unless explicitly noted (Task 6 retires the legacy single-body word check for v2 only).
- [ ] `schema.py` exposes `SCHEMA_VERSION = 2`, `SECTION_FIELDS`, `SECTION_WORD_CAPS`, `TOTAL_BODY_WORD_CAP`, `MIGRATION_CUTOFF_DATE`, `ACCEPTED_SCHEMA_VERSIONS`. Tests in `test_schema.py` lock all six.
- [ ] `validate.py` implements V1-V8. The V3 test for the post-cutoff date (`today=date(2026, 6, 1)`) refuses v1.
- [ ] Validator V4-V8 each have at least one passing AND one failing test (refusal path).
- [ ] `tests/fixtures/user_v2_valid.md` and `tests/fixtures/user_v1_legacy.md` both exist and parse cleanly via `parse_markdown`.
- [ ] `extract.py` SKILL.md flow synthesizes the four sections in declared order; `prompts/sections/*.md` exist and each contains the three required substitution variables.
- [ ] `compose.md` reads `sections` and weights them; the JSON output contract is unchanged (parse_response tests still pass).
- [ ] `load_users.py` populates `User.sections` for both v1 and v2 files; v1 dumps full body into `Recent months`.
- [ ] `spec.md` `## Data Schema` section reflects v2 with 4 sections + migration note.
- [ ] No em-dashes anywhere in modified files.
- [ ] Plans 01-04 are NOT rewritten; this iteration only adds and modifies.
- [ ] Founder dogfood (Task 13) succeeded OR the failure mode is documented in this plan's EXECUTION LOG.

---

## Execution Handoff

This plan is ready to execute in a fresh Claude Code conversation.

1. Open the mesh repo. Read `CLAUDE.md`, then `spec.md` (D9, D11, D13, Privacy section), then this plan in full.
2. Read the design doc at `docs/superpowers/specs/2026-05-01-multipart-trajectory-design.md` so design rationale is in context. If the doc and this plan disagree, the doc wins; stop and ask.
3. Use `superpowers:subagent-driven-development` to dispatch per-task subagents, OR `superpowers:executing-plans` for inline batch execution. Tasks 1-12 are codable; Task 13 is the founder dogfood and is manual.
4. Dispatch order matters: Task 1 (schema constants) before Task 2 (validator V3) before Tasks 3-7 (V4-V8). Task 8 (section prompts) and Task 9 (SKILL.md flow) depend on the new SKILL.md flow text - keep them in order. Task 10 (compose.md) and Task 11 (load_users.py) are independent of each other and can run in parallel after Task 7. Task 12 (spec.md) is independent and can run any time after Task 1. Task 13 runs last.
5. Each task ends with one commit; do not batch commits across tasks.
6. After Task 13, append an EXECUTION LOG to this plan covering: task status (DONE / PARTIAL / BLOCKED + commit SHAs), what worked, what didn't, hardenings beyond the original plan, mid-flight architectural changes, dogfood result, and open items handed off to plan 06.
7. Then ask the user whether to author plan 06 now (likely scope: incremental per-section sync `sync --section "Top of mind"`, adjacent-bets / side-projects section, founder-side `/mesh-orchestrate` dry-run with a v1+v2 mixed pool, lint grouping refinements).
