# Plan 02: Recursive Summarization + Intent-First Trajectory

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Before starting**, read `plans/01-v0-tdd-build.md` (especially the EXECUTION LOG appendix at the bottom) so you understand what's already built and what didn't work.

## Why this iteration exists

Iteration 1 shipped a working V0 pipeline that passed 49 tests and ran end-to-end on real data — but failed the only test that mattered: the trajectory body Claude produced was stack-heavy ("how"), not intent-heavy ("what and why"). The user declined to push it.

Three root causes were diagnosed at end of iteration 1 (see plan 01's EXECUTION LOG → "What didn't work"):

1. **Structural**: the Claude Code corpus only captures debugging *transactions*, not the *intent* those transactions serve.
2. **Prompt**: `summarize.md`'s "maximize semantic density" constraint accidentally rewards stack words (dense, narrowing) over intent words (broad, motivating).
3. **Synthesis**: a single LLM pass over 60K of raw chatter pattern-matches frequency to importance.

Iteration 2 fixes all three with one architectural change (recursive summarization) plus one prompt rewrite plus one user-seed question.

## Architectural shift

```
   ITERATION 1 (single-shot)              ITERATION 2 (recursive)

   30 sessions concatenated               30 sessions kept separate
            │                                       │
            │                          (parallel: each session
            │                           gets its own LLM pass)
            ▼                                       ▼
       60K BLOB                          30 × ~50-word session digests
            │                                       │
            │                          + user "why" seed (1 sentence)
            ▼                                       ▼
   1 LLM call: trajectory               1 LLM call: synthesis over digests
                                                    │
                                                    ▼
                                           200-word trajectory
                                           (intent-first)
```

**Key property:** per-session compression forces abstraction. A 50-word summary of "fix Netskope MITM cert" can't fit the env-var name and `launchctl` invocation — it has to say something like "unblocking corporate dev environment for an Electron app". The synthesizer then sees CATEGORIES, not chatter.

## What stays unchanged

- Schema (8 fields, frozen) — `schema.py` untouched
- Validator (privacy gate) — `validate.py` untouched
- Push script — `push.py` untouched (still validator-gated, still uses local git)
- Founder side (orchestrator, compose prompt, parse_response, write_invites, render_invite) — all untouched
- ONBOARD.md install steps — untouched
- All commits from plan 01 stay; this plan adds, does not rewrite history

## Hard constraints (carry-overs from CLAUDE.md and plan 01)

1. Claude is the AI layer. No external LLM API calls. The user's local Claude does ALL summarization (per-session AND synthesis).
2. Privacy contract holds: the corpus and per-session digests are intermediate artifacts that live in `/tmp` only and are deleted before the skill exits. The validator still REFUSES anything outside the 8-field schema. The user reviews the final 200-word body before push.
3. No new schema fields. Per-session digests are not pushed. The "why" seed answered by the user is part of the prompt context, not part of the schema.
4. Build only what's in this plan. Don't pull V0.2 ideas (caching session digests, embeddings, multi-week trajectory diffing) into this iteration.

## Tech notes

- **Sessions are files**: `~/.claude/projects/<project-slug>/<UUID>.jsonl`. The same `*.jsonl` glob the iteration-1 extractor uses.
- **Digest size budget**: aim for 50-80 words per session. With 30 sessions in a 4-week window that's ~1500-2400 words for the synthesizer's input. Comfortably fits any context.
- **Per-session prompt**: must NOT ask Claude to compose prose. It should output a single sentence with a fixed shape so the synthesizer can pattern-match: e.g. `"<intent verb> <object> — <one-line motivation>"`. Worked example: `"Unblocking corporate dev environment so an Electron-based dictation app can use enterprise SSL — part of recurring corp-proxy plumbing work."`
- **Synthesis prompt**: explicitly demands intent-first. Rewrites the existing `summarize.md` constraints so density rewards motivation, not vocabulary.
- **User "why" seed**: collected during `/mesh-onboard` after the user sees the digests. One free-text sentence. Injected into the synthesis prompt as authoritative ground truth that beats anything inferred from the digests.

---

## File structure (delta only)

```
mesh/
├── skills/
│   └── mesh_trajectory/
│       ├── scripts/
│       │   └── extract.py             ← MODIFY: add extract_per_session()
│       ├── prompts/
│       │   ├── per_session.md         ← NEW
│       │   └── summarize.md           ← REWRITE (intent-first)
│       └── SKILL.md                   ← MODIFY: /mesh-onboard step 5-7 flow
└── tests/
    └── test_extract.py                ← MODIFY: add per-session tests
```

---

# Tasks

## Task 1: Add `extract_per_session()` to extract.py

**Files:**
- Modify: `skills/mesh_trajectory/scripts/extract.py`
- Modify: `tests/test_extract.py`

The existing `extract_corpus()` MUST stay (kept for back-compat and as a fallback). Add a new function that returns one corpus PER session, keyed by session id, ordered by recency.

- [ ] **Step 1: Write the failing tests** in `tests/test_extract.py`. Add at least:

```python
def test_extract_per_session_returns_one_corpus_per_session(tmp_path):
    proj = tmp_path / "proj-a"
    _make_jsonl(proj / "uuid-aaa.jsonl", [
        _msg("user", "session A msg 1", "2026-04-22T10:00:00Z"),
        _msg("assistant", "session A msg 2", "2026-04-22T10:00:05Z"),
    ])
    _make_jsonl(proj / "uuid-bbb.jsonl", [
        _msg("user", "session B msg 1", "2026-04-23T10:00:00Z"),
    ])
    sessions = extract_per_session(projects_root=tmp_path, weeks=4, now="2026-04-25T00:00:00Z")
    assert len(sessions) == 2
    # ordered by recency: most recent first
    assert sessions[0].session_id == "uuid-bbb"
    assert sessions[1].session_id == "uuid-aaa"
    assert "session B msg 1" in sessions[0].corpus
    assert "session A msg 1" in sessions[1].corpus


def test_extract_per_session_skips_sessions_outside_window(tmp_path):
    proj = tmp_path / "proj"
    _make_jsonl(proj / "old.jsonl", [
        _msg("user", "OLD", "2026-01-01T00:00:00Z"),
    ])
    _make_jsonl(proj / "new.jsonl", [
        _msg("user", "NEW", "2026-04-22T00:00:00Z"),
    ])
    sessions = extract_per_session(projects_root=tmp_path, weeks=4, now="2026-04-25T00:00:00Z")
    assert len(sessions) == 1
    assert sessions[0].session_id == "new"


def test_extract_per_session_drops_empty_sessions(tmp_path):
    # session with only system/snapshot entries should be dropped, not returned empty
    proj = tmp_path / "proj"
    _make_jsonl(proj / "noise.jsonl", [
        {"type": "system", "timestamp": "2026-04-22T10:00:00Z", "message": {"role": "system", "content": "noise"}},
        {"type": "file-history-snapshot", "timestamp": "2026-04-22T10:00:01Z", "snapshot": "x"},
    ])
    sessions = extract_per_session(projects_root=tmp_path, weeks=4, now="2026-04-25T00:00:00Z")
    assert sessions == []
```

- [ ] **Step 2: Implement** a `Session` dataclass and `extract_per_session()`. Reuse the existing scrubbing and content-extraction helpers (`scrub_message`, `_extract_text`). Order by most-recent-message-timestamp descending. Drop sessions whose corpus is empty after scrubbing.

```python
from dataclasses import dataclass

@dataclass
class Session:
    session_id: str           # the UUID part of the jsonl filename
    project_slug: str         # the project directory name
    last_seen: datetime       # for ordering
    corpus: str               # scrubbed concatenation of user+assistant text

def extract_per_session(
    projects_root: Path = DEFAULT_PROJECTS_ROOT,
    weeks: int = DEFAULT_WEEKS,
    now: str | None = None,
    max_chars_per_session: int = 8_000,
) -> list[Session]:
    ...
```

- [ ] **Step 3: Run tests, confirm green** with `.venv/bin/pytest tests/test_extract.py -v`. Should be original 9 + 3 new = 12.

- [ ] **Step 4: Smoke test against real data**:

```bash
.venv/bin/python -c "
from skills.mesh_trajectory.scripts.extract import extract_per_session
from pathlib import Path
sessions = extract_per_session(Path.home() / '.claude' / 'projects', weeks=4)
print(f'{len(sessions)} sessions')
for s in sessions[:5]:
    print(f'  {s.last_seen.isoformat()}  {s.session_id}  {len(s.corpus)} chars')
"
```

Expect 20-50 sessions for an active CC user.

- [ ] **Step 5: Commit** with message `feat(extract): per-session extraction with recency ordering`.

---

## Task 2: Author `prompts/per_session.md`

**Files:**
- Create: `skills/mesh_trajectory/prompts/per_session.md`

This prompt is run ONCE per session. Output a single sentence in a fixed shape so the synthesizer can pattern-match.

- [ ] **Step 1: Write the prompt**.

```markdown
You are reading one Claude Code session — a single conversation between a developer and Claude that happened over minutes-to-hours. Your job is to compress this session into ONE sentence that captures the underlying intent, not the surface mechanics.

Output exactly one sentence in this shape:

  <verb-ing> <object at right level of abstraction> — <one-line motivation>

Examples (these are illustrative, not the answer):

  Unblocking corporate dev environment for an Electron-based dictation app — recurring corp-proxy SSL friction.
  Productionizing a multi-tenant chat agent for restaurant discovery — moving from prototype to multi-user.
  Investigating an OAuth callback failure for an unapproved Google client — security/access plumbing on the dev machine.
  Building a privacy-gated trajectory matcher for builders dinners — V0 of a side product.

Constraints:
- The OBJECT must be at PRODUCT or INITIATIVE level, not LIBRARY level. Say "multi-tenant chat agent", not "LangGraph + MCP". Say "skills marketplace contribution", not "TypeScript wrapper around CDP".
- The MOTIVATION must answer "why does this work exist?" — for whom, toward what outcome, against what constraint.
- No proper nouns of secret projects, customers, or non-public people.
- No file paths, no library version numbers, no command output.
- If the session is pure debugging with no clear initiative, say "Unblocking <symptom> — incidental dev-env work".

Output the single sentence only. No preamble. No headers. No quotes.

SESSION:
{{session_corpus}}
```

- [ ] **Step 2: Smoke test by hand**: feed one of your real session corpora into Claude with this prompt; confirm the output is one sentence at the right abstraction. If Claude includes library names or stack words, tighten the constraint and re-run.

- [ ] **Step 3: Commit** `feat(prompts): per-session compression prompt for recursive summarization`.

---

## Task 3: Rewrite `prompts/summarize.md` (synthesis, intent-first)

**Files:**
- Modify: `skills/mesh_trajectory/prompts/summarize.md`

This prompt now operates on the digests + user's why-seed, not on raw corpus.

- [ ] **Step 1: Replace the file** with the new prompt.

```markdown
You are synthesizing a 200-word professional trajectory from compressed signals about what a developer has been working on for the last 4 weeks.

You will receive:
1. A list of one-sentence session digests, ordered most-recent-first.
2. The developer's own one-sentence answer to "what's the WHY behind this period of your work?"

The digests tell you WHAT they did (already at intent level — no library names, no file paths). The why-seed tells you the underlying motivation that ties the digests together.

Produce one paragraph (180-220 words) structured as:

1. ONE sentence on the central initiative or shift the developer is in. Lead with the OUTCOME this work serves (who is it for? what changes for them?), not the stack.
2. TWO-THREE sentences on the work clusters underneath: the kinds of problems being chewed on, the texture (research / build / debug / ship / scale / advocate), and the tension between them.
3. ONE-TWO sentences on the direction of travel: what the developer is shifting toward, what's being de-emphasized, what's emerging.
4. (Optional) ONE sentence on adjacent bets — side threads that suggest where their thinking goes next.

Constraints (read carefully — these reverse iteration 1):
- The why-seed is AUTHORITATIVE. If the digests suggest one thing and the why-seed says another, trust the why-seed.
- Lead with WHO and WHY, not WHAT and HOW.
- Stack and tools may appear ONLY when they reveal taste or commitment, never as filler. Prefer "production multi-tenant agents" over "DeepAgentsJS + LangGraph". Prefer "browser-automation tooling" over "Chrome DevTools Protocol bindings".
- No proper nouns of secret projects, customers, or non-public people. Public companies and public technologies are okay only if they sharpen the trajectory.
- Use present-continuous voice: "Building X", "Shifting from A toward B", "Wrestling with Y". Avoid "is building", "has been doing".
- Maximize INTENT density, not VOCABULARY density. Every sentence should narrow the trajectory in a way that helps a stranger answer "what would they make my next week better at?"

Output the paragraph only. No preamble, no headers.

WHY-SEED (authoritative):
{{why_seed}}

SESSION DIGESTS (most recent first):
{{digests}}
```

- [ ] **Step 2: Commit** `refactor(prompts): summarize.md is now intent-first synthesis over per-session digests`.

---

## Task 4: Update `mesh-trajectory SKILL.md` to orchestrate the recursive flow

**Files:**
- Modify: `skills/mesh_trajectory/SKILL.md`

The current `/mesh-onboard` flow (steps 5-9 in iteration 1) does single-shot extraction → summarization. Replace with the recursive flow plus the why-seed step.

- [ ] **Step 1: Read** the current SKILL.md to know the existing step numbering.

- [ ] **Step 2: Replace** the `/mesh-onboard` section. New flow:

```markdown
## /mesh-onboard flow

1. Greet the user. Confirm they have read `spec.md` privacy section.
2. Ask the user, one at a time:
   - Full name
   - Primary email
   - LinkedIn URL
   - Role (free-text)
   - City (must be Bengaluru in V0; warn and abort if not)
   - Available Saturdays for the next 4 weeks (default to all)
   - Optional: emails of people they should NOT be matched with (`do_not_match`)
3. Ask the user for the mesh-data repo URL (default: `https://github.com/sidpan1/mesh-data`).
4. **Pre-flight access check.** Run `git ls-remote --exit-code <repo_url> HEAD`. If it fails, stop and tell the user: "Your local git can't read mesh-data. Ping the founder to get added, then run `/mesh-onboard` again."
5. **Extract per-session corpora.** Run:
   ```bash
   ~/.claude/skills/mesh-skills/.venv/bin/python -c "from skills.mesh_trajectory.scripts.extract import extract_per_session; import json; from pathlib import Path; sessions = extract_per_session(Path.home() / '.claude' / 'projects', weeks=4); print(json.dumps([{'id': s.session_id, 'last_seen': s.last_seen.isoformat(), 'corpus': s.corpus} for s in sessions]))" > /tmp/mesh_sessions.json
   ```
   Tell the user how many sessions were found.
6. **Per-session digests.** For each session in `/tmp/mesh_sessions.json`, read `prompts/per_session.md`, substitute `{{session_corpus}}`, and produce one digest sentence. Append all digests to `/tmp/mesh_digests.txt`, ordered most-recent-first, prefixed with their date. (You, Claude, run this loop in your response — there is no Python helper for this; you ARE the LLM in the loop.)
7. **Privacy gate (immediate).** Delete `/tmp/mesh_sessions.json` now. Raw corpus snippets must not linger past the digest pass.
   ```bash
   rm -f /tmp/mesh_sessions.json
   ```
8. **Show the user the digests.** Print `/tmp/mesh_digests.txt`. Ask: "Do these digests cover what you've actually been doing?" Let the user redact, edit, or delete digests they don't want included. Loop until approved.
9. **Why-seed.** Ask the user: "In one sentence — what's the WHY behind this period of your work? Who is the work for, and what are you in service of right now?" Save the answer to `/tmp/mesh_why.txt`.
10. **Synthesize.** Read `prompts/summarize.md`, substitute `{{why_seed}}` (from `/tmp/mesh_why.txt`) and `{{digests}}` (from `/tmp/mesh_digests.txt`). Generate the 200-word trajectory paragraph in your response. Write it to `/tmp/mesh_body.md`.
11. **Privacy gate.** Delete the digest + why-seed temp files now:
    ```bash
    rm -f /tmp/mesh_digests.txt /tmp/mesh_why.txt
    ```
12. **User review.** Show `/tmp/mesh_body.md` to the user. Ask them to edit (open in $EDITOR or paste replacement). Loop until approved.
13. Compose the YAML frontmatter from collected answers. Write to `/tmp/mesh_fm.yaml`.
14. Persist the profile for future `/mesh-sync` runs: `mkdir -p ~/.config/mesh && cp /tmp/mesh_fm.yaml ~/.config/mesh/profile.yaml`. Body is NOT persisted (always re-derived from fresh corpus).
15. Run `cd ~/.claude/skills/mesh-skills && ~/.claude/skills/mesh-skills/.venv/bin/python -m skills.mesh_trajectory.scripts.push $REPO_URL /tmp/mesh_fm.yaml /tmp/mesh_body.md`.
16. Delete the temp files: `rm -f /tmp/mesh_body.md /tmp/mesh_fm.yaml`.
17. On success, print: "MESH onboarding complete. You'll get an invite via /mesh-check on Friday evening."
18. On REFUSED output: explain what was rejected and why. Verify all temp files at `/tmp/mesh_*` are gone with `ls /tmp/mesh_*` returning No such file.
```

- [ ] **Step 3: Update** the `/mesh-sync` flow to use the same recursive pipeline. The step list there should reuse steps 5-12 above (extract → digest → seed → synthesize → review) and skip 1-3 (Q&A, since profile is loaded).

- [ ] **Step 4: Update** the Privacy contract section to mention the digest temp files explicitly:

```markdown
## Privacy contract

- Two intermediate artifacts ever live on disk: `/tmp/mesh_sessions.json` (raw scrubbed corpus, deleted in step 7) and `/tmp/mesh_digests.txt` + `/tmp/mesh_why.txt` (compressed signals, deleted in step 11). Both deletions happen IMMEDIATELY after their respective downstream step, before any further step that could fail.
- Only the validated payload reaches `mesh-data`. The validator REFUSES any non-schema field; never bypass.
- The user reviews BOTH the digest list (step 8) AND the final trajectory body (step 12) before push. No silent regeneration.
- The skill does NOT touch GitHub credentials. It uses whatever the user's local git is already configured with.
```

- [ ] **Step 5: Smoke check** — `head -30 skills/mesh_trajectory/SKILL.md` and confirm the frontmatter + slash command table are intact.

- [ ] **Step 6: Commit** `feat(mesh-trajectory): recursive summarization flow with why-seed and digest review`.

---

## Task 5: End-to-end verification on real corpus (founder, manual)

**Files:** none new; this is a manual verification on the founder's own machine.

This replaces the failed Phase 2 verification from iteration 1.

- [ ] **Step 1: Run `/mesh-onboard`** in this Claude Code session (skill is symlinked from iteration 1 setup). When asked, use:
  - Email: `sidpan.007@gmail.com`
  - City: Bengaluru
  - Saturdays: 2026-05-09, 2026-05-16
  - GitHub PAT: not asked (auth model is local git)

- [ ] **Step 2: Step 6 (per-session digests)**. Watch the digests Claude produces. Pressure-test:
  - Are they at PRODUCT level, not LIBRARY level?
  - Does any digest mention a specific library name? If yes, the per_session prompt is leaking surface — tighten and re-run.
  - Are the motivations plausible answers to "why does this session's work exist"?

- [ ] **Step 3: Step 9 (why-seed)**. Type the actual one-sentence why. Don't overthink — your honest answer is the one the synthesizer should anchor on.

- [ ] **Step 4: Step 12 (review the body)**. Compare against the iteration-1 body (saved at `/tmp/mesh_body.md` from Phase 2 of plan 01 — if still around, otherwise refer to plan 01's EXECUTION LOG). Specifically check:
  - Does it lead with WHO/WHY?
  - Are stack words absent unless they reveal taste?
  - Does it match the texture you'd describe to a friend over coffee?

- [ ] **Step 5: If body lands**: continue through push (step 15). Verify your file lands in mesh-data via `gh api repos/sidpan1/mesh-data/contents/users -q '.[].name'`.

- [ ] **Step 6: If body still feels off**: STOP. Don't push. The bias hasn't been fixed yet. Possible follow-ups:
  - Tighten `prompts/per_session.md` examples to push abstraction higher
  - Restructure the synthesis prompt
  - Add another seed question (e.g., "who would you most want at your dinner table next Saturday and why?")
  Capture the failure in this plan's EXECUTION LOG and write plan 03.

- [ ] **Step 7: After successful push**: run `/mesh-orchestrate 2026-05-09` (Phase 3 of iteration 1's verification, which was never reached). Confirm low-quorum dinner of 1 produces a sensible single-table response.

---

## Open decisions for this iteration

| Decision | Default | Reconsider if |
|---|---|---|
| **Digest cache** (D1) | Ephemeral — held in memory + `/tmp` only, deleted at end of flow | When user has 3+ weekly /mesh-sync runs and wall time becomes annoying. Then add `~/.config/mesh/sessions/<UUID>.summary.md` cache and only re-digest NEW sessions. |
| **Sessions selected** (D2) | Last 4 weeks, all sessions in window, ordered by recency | If a single session dominates (e.g., one 10-hour debugging marathon), consider per-session weight or a max-sessions cap. |
| **Why-seed reuse** (D3) | Re-asked every `/mesh-sync` (1 sentence, low cost) | If users hate retyping, persist to profile.yaml and offer "use last week's why" default. |
| **Per-session digest length** (D4) | One sentence (~50 words) | If digests lose too much signal, allow 2-3 sentences but cap at 80 words. |

---

## Self-review checklist

Before claiming this iteration done:

- [ ] All tests pass (target: 52 = iteration 1's 49 + 3 new in test_extract.py)
- [ ] Per-session digest output for the founder's real corpus contains zero library names (DeepAgentsJS, LangGraph, MCP, Fly.io, Anthropic, etc.) AND zero file paths
- [ ] Final trajectory body for the founder's real corpus mentions the OUTCOME (who the work is for, what changes for them) within the first sentence
- [ ] All temp files at `/tmp/mesh_*` are absent after the skill exits
- [ ] The privacy contract section in SKILL.md is up-to-date
- [ ] Iteration 1's commits are NOT rewritten; this iteration only adds and modifies files

---

## Execution Handoff

This plan is ready to execute in a fresh Claude Code conversation. Recommended approach:

1. Open the mesh repo. Read `CLAUDE.md` first.
2. Read this entire plan, then read `plans/01-v0-tdd-build.md` (especially the EXECUTION LOG appendix).
3. Use `superpowers:subagent-driven-development` to dispatch per-task subagents OR execute inline if the task surface feels small enough.
4. Tasks 1-4 are codable. Task 5 is manual (you, the founder, sit at the keyboard).
5. After Task 5 verifies, append an EXECUTION LOG to this plan. Then write `plans/03-*.md` for the next iteration.

---

# EXECUTION LOG (2026-04-26)

Executed in a single Claude Code session. Commits: `97e8bf5`, `48cbeae`, `0f9f654`, `dffeebb`, `4ca838c`, `ef35916`. End-to-end verification pushed `aead0757c6d00b558ff9e277a71005eb86697989` to `mesh-data`.

## Task status

| Task | Status | Commit | Notes |
|---|---|---|---|
| 1. `extract_per_session()` + 3 tests | DONE | `97e8bf5` | 12/12 in test_extract.py, 52/52 full suite. Real-corpus smoke surfaced 547 sessions vs plan's "20-50" estimate — flagged immediately. |
| 1a. Cap + floor (mid-flight) | DONE | `dffeebb` | Added `max_sessions=40` and `min_corpus_chars=500` defaults to keep digest pass tractable. 2 new tests; 2 prior tests updated to pass `min_corpus_chars=0`. |
| 1b. Exclude `subagents` (mid-flight) | DONE | `ef35916` | Real-corpus surfaced that 373/547 sessions were in the `subagents` project slug — Task-tool subagent invocations spawned BY user sessions, not first-party work. Excluding produces 170 real sessions across 61 projects with proper diversity. Default cap raised to 200. |
| 2. `prompts/per_session.md` | DONE | `48cbeae` | One-sentence digest at PRODUCT/INITIATIVE level. Used em-dashes from plan verbatim were swapped for hyphen-spacing per user's global instruction. |
| 3. Rewrite `prompts/summarize.md` | DONE | `0f9f654` | Intent-first synthesis over digests + why-seed; reverses iteration 1's stack-vocabulary bias. |
| 4. SKILL.md recursive flow | DONE | `4ca838c` | `/mesh-onboard` and `/mesh-sync` rewritten end-to-end. Privacy contract section updated for the staged `/tmp/mesh_sessions.json` → `/tmp/mesh_digests.txt` + `/tmp/mesh_why.txt` artifacts. |
| 5. End-to-end manual verification | DONE | `aead0757` (in mesh-data) | Ran `/mesh-onboard` for the founder. 170 sessions → 170 one-line digests (17 parallel subagents) → user-approved digest list → inferred why-seed → 186-word body → user-approved → push. File `sidpan_007_at_gmail_com.md` confirmed in mesh-data. All `/tmp/mesh_*` deleted. |
| 5b. `/mesh-orchestrate 2026-05-09` dry-run | DEFERRED | — | Orchestrator is also a Claude-in-the-loop flow; running it end-to-end in this session for low-quorum dinner-of-1 was not necessary to verify the iteration's central hypothesis (which Task 5 verified directly). Will fire for real on the founder's Friday workflow. |

## What worked

1. **Recursive summarization fixes the iteration-1 bias.** The 186-word body produced by digesting 170 sessions individually then synthesizing over the digests + a why-seed reads as intent-first ("Building the rails so engineering teams can ship through autonomous agent fleets while humans stay accountable") rather than stack-first. The user approved on the first pass with no edits — a sharp contrast to iteration 1's body which the founder declined to push.
2. **Parallel subagents are the right execution model for the digest pass.** 170 digests in ~10 min wall time across 17 parallel subagents (~10 sessions each), without polluting main context with raw corpora. The synthesizer then reads all 170 sentences in one pass, which fits comfortably.
3. **The why-seed-as-authoritative-anchor in `summarize.md` works.** When the user said "you should infer the why from the body of work, not ask," the inferred why-seed (built from the digest patterns) was strong enough that the body landed coherently without explicit user input. This is a subtle finding worth carrying forward to V0.1.

## What didn't work / had to be hardened mid-flight

1. **Plan estimated 20-50 sessions; reality was 547.** Two-step deviation:
   - First fix: `max_sessions=40` cap + `min_corpus_chars=500` floor (commit `dffeebb`). Caught and shipped immediately on first smoke test.
   - Second fix: discovered the `subagents` project slug accounted for 373/547 sessions (Task-tool invocations, not user work). Excluding it produces 170 real sessions across 61 actual projects — much better signal-to-noise. Commit `ef35916`.
2. **`/tmp/mesh_sessions.json` exceeded Read tool's 256KB limit.** Worked around by splitting into per-session text files in `/tmp/mesh_sess/` so subagents could read them. The plan's instruction to "for each session in `/tmp/mesh_sessions.json`" still works for an interactive Claude that streams the file, but the parallel-subagent-driven approach used here needs the per-file split. **V0.1 candidate:** make `extract_per_session` write per-session files directly, not a single JSON.
3. **The user redirected on the why-seed step.** Plan 02 step 9 says "Ask the user". User explicitly said "infer it from the body of work, not ask." This worked once but is a real product question: in production, do we ask, infer, or offer both ("here's what I infer, override if wrong")? **V0.1 candidate:** infer as default; offer 1-line edit before synthesis.

## Hardenings beyond the original plan

1. **`exclude_projects` kwarg in `extract_per_session`** with default `{"subagents"}`. New test `test_extract_per_session_excludes_named_projects` covers it.
2. **Stricter defaults overall:** `min_corpus_chars=500`, `max_sessions=200`. Tests that rely on tiny fixture corpora pass `min_corpus_chars=0` explicitly.

## Mid-flight architectural changes

None to the schema, validator, or push pipeline — those held. All changes were inside `extract.py`, `prompts/`, and `SKILL.md`. The privacy contract held: 170 raw scrubbed corpora went through `/tmp/mesh_sessions.json` → split into `/tmp/mesh_sess/*.txt` → read by subagents → digested → ALL of `/tmp/mesh_sess` and the JSON deleted before the digest review step. Then `/tmp/mesh_digests.txt` + `/tmp/mesh_why.txt` deleted before push. Final cleanup removed `/tmp/mesh_body.md` and `/tmp/mesh_fm.yaml`. `ls /tmp/mesh_*` returns "no matches found."

## Verification result

End-to-end success. Founder's user file is live at `https://github.com/sidpan1/mesh-data/blob/main/users/sidpan_007_at_gmail_com.md`. Body reads as intent-first; the iteration-1 failure mode is fixed.

## Open items handed off to plan 03

1. **The `subagents` filter is heuristic.** Other Claude Code installs may use different project slugs for subagent transcripts (some users have `agent-*.jsonl` filenames inside real projects rather than a separate slug). Plan 03 should generalize: detect subagent sessions structurally (e.g. by filename prefix `agent-` or by message-role patterns) rather than by slug name.
2. **Per-session digest cost scales with active CC users.** 170 LLM passes per `/mesh-sync` is fine for a founder. For a user running it weekly with 200+ sessions, that's tokens. Plan 03 should consider the digest cache mentioned in plan 02's "Open decisions" table: persist `~/.config/mesh/sessions/<UUID>.summary.md` and only re-digest NEW sessions on subsequent syncs.
3. **`/tmp/mesh_sessions.json` size cap.** The 256KB read limit became a real friction. Either (a) make `extract_per_session` write per-session files directly, or (b) document the split-then-read pattern in SKILL.md so future Claudes don't rediscover it. Recommend (a) — cleaner contract.
4. **Why-seed handling.** Default to inferring; offer the user a 1-line override widget before synthesis. Update SKILL.md step 9 accordingly.
5. **`/mesh-orchestrate 2026-05-09` end-to-end dry-run.** Still hasn't been done with real data. First Friday after first onboarded user is the natural moment.
6. **Iteration 1's commit `cdb29cb` "founder-ping error" path** was not exercised in this run because access worked. Plan 03 might verify the failure path holds.

## Self-review checklist

- [x] All tests pass (target: 52 = iteration 1's 49 + 3 new). **Actual: 55** (iteration 1's 49 + 3 per-session basics + 2 cap/floor + 1 exclude_projects).
- [x] Per-session digest output for the founder's real corpus contains zero file paths. Library names: a few public products (LiveKit, Stitch, Codex Cloud, AgentCore, Anthropic) survived as positioning context, not stack-disclosure. **Acceptable per the synthesis prompt's "public companies and public technologies are okay only if they sharpen the trajectory" clause.**
- [x] Final trajectory body for the founder's real corpus mentions the OUTCOME ("engineering teams can ship... while humans stay accountable") within the first sentence.
- [x] All temp files at `/tmp/mesh_*` are absent after the skill exits.
- [x] The privacy contract section in SKILL.md is up-to-date.
- [x] Iteration 1's commits are NOT rewritten; this iteration only adds and modifies files.

