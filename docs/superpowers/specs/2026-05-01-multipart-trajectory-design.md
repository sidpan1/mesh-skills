---
title: Multipart trajectory body (schema v2)
date: 2026-05-01
status: design-approved (pending writing-plans handoff)
authors: Sidhant Panda + Claude
related:
  - spec.md (D9, D11, Privacy section)
  - skills/mesh_trajectory/schema.py
  - skills/mesh_trajectory/scripts/validate.py
  - skills/mesh_orchestrator/prompts/compose.md
---

# Multipart trajectory body (schema v2)

## 1. Context

Today, every user's `mesh-data/users/<email>.md` has 8 frontmatter fields plus a single ~200-word free-text body that summarizes the user's last few weeks of Claude Code work. The founder's local Claude reads these bodies and composes dinner tables.

A reference memory format (Claude web "Memory") was reviewed alongside this design. It uses six layered sections (Work / Personal / Top of mind / Brief history / Long-term background / Other instructions). It is richer and more reviewable than a single para. We want the temporal layering for matching quality, but we do not want the privacy and review-cost expansion that comes with adopting the format wholesale.

## 2. Goals and non-goals

**Goals**

- Replace the single 200-word body with **four named sections** that expose temporal layering: `Work context`, `Top of mind`, `Recent months`, `Long-term background`.
- Preserve MESH's existing privacy contract (locked schema, code-enforced validator, raw conversations never leave the device).
- Keep total review time under ~60 seconds.
- Give the founder's matcher a clean signal for the highest-value pairing pattern (Guide x Explorer): same substrate, different velocities.
- Lazy migration: no backfill script; existing users re-sync at their own pace.

**Non-goals (V0)**

- No personal / household / operational sections in the shared file. Those stay on-device or in a separate local artifact (out of scope for this spec).
- No per-section embeddings. Claude continues to be the AI layer (Hard Constraint 1, D9).
- No incremental per-section sync UX in V0. The schema and extractor must not block it for V0.1, but V0 ships full re-extract on every `sync`.
- No automated backfill of existing schema_v1 files.

## 3. Schema v2 contract

### 3.1 Frontmatter (unchanged except version bump)

```yaml
---
schema_version: 2          # was 1
name: string
email: string
linkedin_url: string
role: string
city: string               # hard-filtered to "Bengaluru"
available_saturdays:
  - "YYYY-MM-DD"
do_not_match: []           # optional
embedding: null            # reserved; null in V0
---
```

The 8-field set is unchanged. `SCHEMA_FIELDS` in `schema.py` still refuses any other key. Only the version number and the body shape change.

### 3.2 Body: four ordered sections

The body MUST contain exactly these H2 headings, in this order, with no other H2 headings anywhere in the body.

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

Total body word cap: **250 words**. Per-section caps act as soft signal-shaping (preventing the user from dumping everything into one section) and the total cap acts as the hard review-time guarantee.

### 3.3 Constants in `schema.py`

```python
SCHEMA_VERSION = 2

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

`SECTION_FIELDS` is the second locked contract alongside `SCHEMA_FIELDS`. Adding, removing, or renaming a section requires the same three-way commit pattern as adding a frontmatter field: `schema.py` + `spec.md` + a failing test in one commit.

## 4. Validator rules (`validate.py`)

The validator pipeline becomes:

| # | Rule | Status | On failure |
|---|---|---|---|
| V1 | Frontmatter keys subset of `SCHEMA_FIELDS` | existing | refuse |
| V2 | All `REQUIRED_FIELDS` present | existing | refuse |
| V3 | `schema_version` in `{1, 2}` during migration window (until 2026-06-01); `{2}` only after cutoff | new | refuse with version + cutoff date |
| V4 | Body contains exactly `SECTION_FIELDS` H2 headings, in order | new | refuse, name missing/extra heading |
| V5 | No H2 headings in body outside `SECTION_FIELDS` | new | refuse, name offending heading |
| V6 | Each section <= `SECTION_WORD_CAPS[section]` | new | refuse with section name + actual count |
| V7 | Total body <= `TOTAL_BODY_WORD_CAP` | new | refuse with actual count |
| V8 | PII stop-list pass over full body | new | refuse with offending substring |

**V8 PII stop-list (initial):** phone-number regex (Indian + international formats), email regex matching anything other than the user's own `email` frontmatter field, address-pattern regex (e.g., `\b\d+[A-Z]?-?\d+\b` for unit numbers, common Bengaluru area suffixes), and a small hardcoded stop-list of common partner / household terms loaded from `skills/mesh_trajectory/pii_stoplist.txt`. Stop-list is per-user-overridable via a local `~/.mesh/pii_extra.txt` for terms only that user knows are sensitive.

V8 is intentionally cheap and conservative: it costs a few regex passes; it blocks the obvious leaks even if the user pastes carelessly. It is not a substitute for V4-V7.

### Heading recognition rule

Sections are matched by **exact heading text after normalizing whitespace**. Case-sensitive. Unicode normalization (NFC). No tolerance for typos. The extractor produces canonical headings; if the user edits them, validation fails with a clear "rename heading X to Y" message.

## 5. Sync flow (`extract.py` + `SKILL.md`)

```
/mesh-trajectory sync
  |
  +-- 1. Pull last N weeks of Claude Code session JSONL into /tmp/mesh_corpus.txt
  |      (existing extract logic; N defaults to 6 weeks, configurable)
  |
  +-- 2. For each section in SECTION_FIELDS, call local Claude with:
  |        - the corpus
  |        - the section name + its word cap + a section-specific prompt
  |        - prior context, depending on the user's current state:
  |            * first-ever sync         -> no prior context
  |            * existing v2 file        -> prior section text for continuity
  |            * existing v1 file        -> the full 200-word v1 body, used
  |                                         as additional input to all 4
  |                                         sections (migration case)
  |      Render the proposed section to the user.
  |
  +-- 3. User reviews and edits each section in turn. Skipping a section
  |      is not allowed (validation will fail). User can edit inline before
  |      moving to the next.
  |
  +-- 4. Assemble full file (frontmatter + 4 sections), run validate.py
  |      with V1-V8. On any failure, surface and re-loop into the failing
  |      step (heading -> step 2/3, word cap -> step 3, PII -> step 3).
  |
  +-- 5. Delete /tmp/mesh_corpus.txt (Hard Constraint 4).
  |
  +-- 6. git commit + push to mesh-data.
```

**V0.1 hook (designed-for, not built):** `sync --section "Top of mind"` re-runs steps 2-6 for one section only. The section-addressable schema makes this a small change later. V0 always runs the full flow.

### Section-specific extraction prompts (sketch)

- **Work context** prompt: "From the corpus, extract the user's role, team, and what they own. Output <=50 words. No personal context, no household, no projects in flight."
- **Top of mind** prompt: "From the corpus, identify what the user is actively working on or thinking about in the last ~4 weeks. Output <=75 words."
- **Recent months** prompt: "From the corpus, summarize what the user has shipped or shifted in the last 3-6 months. Output <=100 words."
- **Long-term background** prompt: "From the corpus and prior summaries, summarize the user's durable expertise (1+ year horizon). Output <=75 words. Stable across syncs."

The full prompts live in `skills/mesh_trajectory/prompts/sections/<section>.md` and are themselves committed; they are part of the contract because they shape what users see and approve.

## 6. Matching prompt change (`compose.md`, founder-side)

The compose prompt is updated to read sections explicitly and weight them:

- **Work context** -> role-diversity / no-same-company filter (constraint, not score).
- **Top of mind** -> near-term compatibility, weight 0.4.
- **Recent months** -> trajectory similarity, weight 0.4.
- **Long-term background** -> substrate fit, weight 0.2.

Guide x Explorer detection: high overlap on `Long-term background` + low overlap on `Top of mind` => different velocities on shared substrate. The prompt biases each composed table toward at least one such pair where the candidate pool allows.

`parse_response.py` JSON output contract is **unchanged**: still `{table_id, members[], why_this_table}`. Only the input shape changes.

## 7. Migration: lazy, no backfill

```
schema_version: 1 file  -- accepted by orchestrator with a deprecation warning
                            until 2026-06-01, then refused.
schema_version: 2 file  -- accepted from this PR forward.

User upgrades by running /mesh-trajectory sync once after the new
extractor ships. The new extractor reads the existing v1 200-word
body as additional context, decomposes into 4 sections, user reviews,
push.

No bulk migration script. No automated rewrite. Each user re-syncs
at their own pace inside the 30-day window.
```

The orchestrator gains a small adapter: when reading a v1 file, treat the entire 200-word body as `Recent months` for matching purposes and leave the other three sections empty. This is intentionally crude; the whole point is to push users to re-sync.

## 8. Testing strategy

New tests under `tests/test_validate.py` and `tests/test_extract.py`:

- Valid v2 file passes V1-V8.
- Missing one of the 4 sections -> V4 refuses with section name.
- Extra H2 heading (e.g., `## Personal context`) -> V5 refuses with heading name.
- Section over its word cap by 1 word -> V6 refuses with cap and actual count.
- Total over 250 words even with each section under its cap -> V7 refuses.
- Phone number in body -> V8 refuses.
- Email other than user's own in body -> V8 refuses.
- Address-pattern in body -> V8 refuses.
- v1 file passes V1-V3 with deprecation warning until cutoff, then V3 refuses.

**TDD discipline (per CLAUDE.md):** every test is written failing first, then implementation makes it pass, one commit per test (or one commit per tightly-coupled pair). The synthetic-test trap from iteration 1 applies: at least one validate test must run against a real fixture file shaped exactly like what `extract.py` will produce.

## 9. Privacy considerations

The launch-window override in CLAUDE.md hard constraint #2 makes `mesh-data` temporarily **public** through (target) 2026-05-09. This sharpens the stakes for this design:

- Any leak now leaks to a public GitHub repo, not a private one.
- V8 (PII stop-list) is therefore not optional in V0; it is the belt-and-braces guard against careless paste.
- ONBOARD.md, `SKILL.md` final-review step, and any new section-review UX must surface "this is a public repo right now" before each push, until the repo is reverted to private.
- After private revert, V8 stays in place; the threat model just relaxes.

What the new schema does **not** change: raw Claude Code conversations still never leave the device, `/tmp/mesh_corpus.txt` still gets deleted on exit, the validator is still the only gate.

What the new schema **does** add to the privacy surface: 4 free-text sections instead of 1. V4-V7 cap that surface in word count; V8 caps it in content shape.

## 10. Out of scope (deferred to V0.1+)

- Incremental per-section sync (`sync --section`). Designed-for only.
- Adjacent-bets / side-projects section. Re-evaluate after dinner #1.
- Local-only memory file (`~/.mesh/memory.md`) with personal/operational sections. Separate spec when needed.
- Per-section embeddings. Stays out of V0 per D9.
- Automated migration tooling. Lazy is fine for the user count we have.
- Per-user PII stop-list UI. V0 only supports manual edit of `~/.mesh/pii_extra.txt`.

## 11. Risks and open questions

| # | Risk | Mitigation |
|---|---|---|
| R1 | Users push back on 4-section review feeling heavier than 1-para review | Hard cap of 250 words enforces ~50s review. We measure on dogfood (5 friends) before launch event. |
| R2 | Section-specific prompts produce lower-quality output than a single holistic prompt | Side-by-side eval on 5 dogfood users; if quality regresses, fall back to a single prompt that emits a sectioned output |
| R3 | V8 stop-list false-positives block legitimate content | Stop-list is intentionally conservative; per-user override file `~/.mesh/pii_extra.txt`; failure messages name the offending substring so the user can rephrase |
| R4 | v1 + v2 coexistence period bugs the orchestrator | The crude v1-as-Recent-months adapter is one branch and is unit-tested with a v1 fixture |
| R5 | Migration cutoff (2026-06-01) is too aggressive given launch on 2026-05-09 | Cutoff is editable; revisit after launch when re-sync rate is observable |

## 12. Acceptance criteria

This design ships when:

1. `schema.py` exposes `SCHEMA_VERSION = 2`, `SECTION_FIELDS`, `SECTION_WORD_CAPS`, `TOTAL_BODY_WORD_CAP` and tests cover their immutability.
2. `validate.py` implements V1-V8; all V4-V8 tests pass with TDD-style commits.
3. `extract.py` produces 4-section output and the user-review UX in `SKILL.md` walks through them in order.
4. `compose.md` is updated and `parse_response.py` tests still pass against unchanged JSON output.
5. spec.md `## Data Schema` section is updated to v2.
6. CLAUDE.md hard constraints are unchanged; only the schema-extension procedure (#3) gains the section-set as a second locked artifact.
7. Founder-side dogfood with 5 users produces a clean composed dinner table from v2 trajectories.

---

**Implementation tracker:** to be authored as `plans/NN-multipart-trajectory.md` via the writing-plans skill, with task ordering driven by Section 8 testing strategy.
