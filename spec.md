# MESH V0 Specification

**AI-curated professional dinners for builders.**
*The dinner table is the original social network. We're giving it an algorithm.*

This document is the V0 contract: what we are building, why, and the decisions locked during brainstorming. Implementation details live in `plan.md`. Anything not specified here is out of scope for V0.

---

## Vision

Professional networking matches on **stated identity**: LinkedIn bios, job titles, conference badges. Result: 200-person mixers with zero follow-through, serendipity left to chance, the best builders shut out. The people who could change your career are three tables away. You'll never meet them because the event has no matching logic.

Claude Code conversations are the highest-fidelity signal of what a professional is *actually working on*. GitHub shows what you shipped. LinkedIn shows what you claim. Claude Code shows what you're **wrestling with right now**: the dead ends, the explorations, the 2am rabbit holes. No other platform has access to this signal.

MESH reads what you're building, not what you say you're building, and finds you 5 people who'd make your next week better. It then organizes an intimate dinner where every pairing has a reason. You show up at 8pm. The serendipity is engineered.

---

## V0 Goal

Run **dinner #1** in Bengaluru on **Saturday 2026-05-09 at 7pm** with 6 attendees algorithmically composed from a **30-person semi-public launch event** held the preceding **Friday 2026-05-01**.

Prove that engineered serendipity produces conversations real builders rate as valuable.

---

## Forcing Functions

The five constraints that everything else must respect.

```
[!] LAUNCH EVENT:    2026-05-01 (Friday)         30-person seed cohort
[!] FIRST DINNER:    2026-05-09 (Saturday) 7pm   Bengaluru, table of 6
[!] BUILD WINDOW:    7 days from 2026-04-25 to 2026-05-01
[!] RECURRING SLOT:  Saturday 7pm Bengaluru, fixed forever
[!] AI LAYER:        Claude Code only, no other API sprawl
[!] SHARED STORE:    Private GitHub repo, no DB, no cloud, no web app
```

---

## Decision Framework

Every choice below was made deliberately during brainstorming. Alternatives are listed for future reversibility.

| # | Decision | Chosen | Rejected alternatives | Why |
|---|---|---|---|---|
| D1 | **V0 form factor** | Trajectory engine + algorithmic dinner from kickoff event | Concierge MVP; brand-first dinner club; agent-API first | Trajectory engine is the moat; a real dinner anchors product to outcomes |
| D2 | **Match architecture** | Thin client extracts and summarizes; central matches | Fat client (math runs locally); hybrid hashed embeddings | Faster algo iteration; raw conversations still never leave device |
| D3 | **Density bootstrap** | Hand-curated 30-person semi-public launch event | Public waitlist; friends-and-family creep; community partnership | Solves density + acquisition + dogfooding in one event |
| D4 | **Verification scope** | Launch event itself is the V0 eval | Synthetic personas; shadow matching; trajectory-bend instrumentation | 7-day window precludes a real offline eval. Synthetic + GHArchive harness ships in V0.1 |
| D5 | **Plugin scope** | Clean module boundaries, no formal plugin API | Lightweight event bus; full plugin platform | YAGNI: extract a real plugin API after the 3rd plugin shows the right abstraction |
| D6 | **Event format** | Kickoff event week 1, first dinner week 2 Saturday | Event IS the dinner; hybrid huddle + later dinner | Cleanest test of the actual product loop |
| D7 | **Onboarding surface** | Paste-able prompt that asks minimal Q's + installs local skill | Form-only; manual conversation paste; GitHub-derived | Honest demo of the actual product, Claude-native from day 1 |
| D8 | **Central infra** | Founder's laptop + GitHub repo as DB (private by default; PUBLIC during the 2026-05-01 launch window, reverting to private after the launch event) | Cloud VM + Postgres; Google Sheet; Notion DB | Zero infra overhead; founder remains in the loop, desirable for first 3 dinners. Launch-window public state is a temporary operational choice disclosed to all onboarders. |
| D9 | **Matching mechanism** | **Claude is the matching engine** (single prompt over all summaries) | Embeddings + cosine similarity; hybrid Claude + embedding sanity check | Aligned with "Claude is the AI layer." Embeddings are V0.1 fast-filter when scale demands |
| D10 | **Invite delivery** | Pure Claude-native: `/mesh-trajectory check` slash command pulls from git | Email link; auto-notify hook | No external send infra. Founder WhatsApps the cohort to "run /mesh-trajectory check" |
| D11 | **Data schema** | Minimal 8-field document (see Data Schema) | Tags; opt-in highlights | Most defensible privacy posture. Tags revisit in V0.1 |
| D12 | **Hierarchical recursive summarization** | 3-layer: per-session -> per-project -> trajectory; bucket labels (CENTRAL/REGULAR/OCCASIONAL/ONE-OFF) provide texture without raw count weighting | Flat synthesis over per-session digests; flat synthesis over raw conversations | Plan 02 verification on the founder's real corpus (170 sessions across many logical projects) showed the flat synthesizer over-indexes on volume; one project with 80 sessions dominated the body at the expense of 25 other initiatives. The project layer ensures every project gets one slot in the synthesis input regardless of session count. |
| D13 | **LLM-as-judge interactive privacy lint** | Local Claude judges the candidate body, returns JSON-flagged spans by category/severity; user resolves each flag via AskUserQuestion (KEEP/REDACT/REPHRASE) before push | Schema-only validator (D11) alone; regex denylist; pre-push human-only review with no automation | The schema validator (D11) checks field shape, not content. Plan 02 surfaced a personally-sensitive sentence in a session digest that did not reach the body only because the founder made an editorial call; for non-founder users this gap is load-bearing. LLM-as-judge catches novel phrasings a regex list cannot; per-flag interactive resolution preserves user agency over the final body. |

---

## Architecture

```
USER MACHINE                                          CENTRAL                       FIRST DINNER
+-----------------------------------------+           +------------------+          +-------------+
| paste prompt -> Claude                  |   git     | founder's laptop |   git    | Sat 7pm     |
|   |- asks: name/LI/role/city/sat-avail  |   push    | runs             |   push   | Bengaluru   |
|   |- installs mesh skill                | --------> | /mesh-orchestrate| -------> | table of 6  |
|   |- skill reads ~/.claude/projects     |           |   (Friday wk 2)  |          | venue:      |
|   |                                     |           | * reads users/   |  invite  | pre-booked  |
|   v hierarchical summarization          |           | * Claude-as-     |   md     |             |
|   per-session digests                   |           |   matcher in one |          |             |
|        |                                |           |   prompt         |          |             |
|        v group by normalized project    |           | * writes invite  |          |             |
|   per-project summaries (with bucket    |           |   md per table   |          |             |
|     labels: CENTRAL/REGULAR/OCCASIONAL/ |           +------------------+          +-------------+
|     ONE-OFF; equal voice across)        |                   |                           ^
|        |                                |                   v                           |
|        v synthesize over project        |           mesh-data repo                      |
|   200-word trajectory body              |           networking-dinners/                 |
|        |                                |           dinner-2026-05-09/                  |
|        v privacy lint (LLM-as-judge)    |           table-1.md ----------------------+
|   AskUserQuestion per flag (KEEP/       |
|     REDACT/REPHRASE)                    |
|        |                                |
|        v user reviews + commits         |
|   to mesh-data repo                     |
|   /mesh-trajectory check shows invite |
+-----------------------------------------+
```

**Key property**: two Claude agents communicating through a single git repo. No web app, no API server, no database. The user-side pipeline summarizes hierarchically (session -> project -> trajectory) so volume bias does not dominate the body, and an interactive privacy lint reviews the body before push. The privacy contract is enforced by both a pre-push schema validator and the user's per-flag KEEP/REDACT/REPHRASE decisions.

---

## Components

| Unit | Owns | Reads | Writes | V0 |
|---|---|---|---|---|
| **1. Onboarding prompt** | The user-facing first 3 minutes | nothing | delegates to skill installer | yes |
| **2. mesh-trajectory skill** (local) | Extraction, summarization, sync, invite display | `~/.claude/projects/`, `mesh-data` repo | `users/<email>.md`; renders invites | yes |
| **3. mesh-data repo** (private GitHub) | Shared store + audit trail | passive | passive | yes |
| **4. mesh-orchestrator skill** (founder laptop) | Matching + table composition + invite generation | `users/*.md` | `networking-dinners/*.md` | yes |
| **5. mesh-feedback** | Post-dinner ratings, weight tuning | `networking-dinners/*` + survey | scoring artifacts | V0.1 |
| **6. mesh-eval** | Synthetic personas + GHArchive offline harness | benchmark fixtures | precision@K scores | V0.1 |

### Interface contracts

- **Skill -> repo**: writes `users/<email>.md` with YAML frontmatter matching the *Data Schema* exactly. Pre-push validator REFUSES the push if any non-schema key is present.
- **Orchestrator -> repo**: writes `networking-dinners/dinner-YYYY-MM-DD/table-N.md` with attendee list, venue, time, and a Claude-generated "why this table" narrative.
- **Skill <- repo**: `/mesh-trajectory check` reads any `dinner-*` file mentioning the user's email and renders it.

---

## Data Schema

The complete, exhaustive payload that leaves the user's device. Any field not listed here MUST NOT be uploaded. The validator enforces this.

```yaml
---
# users/<email>.md frontmatter
schema_version: 1
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

# Body of the file: 200-word trajectory summary written by the user's
# local Claude after reading their last 4 weeks of Claude Code sessions.
# User reviews and edits before commit. This is the only free-text field.
```

**Notes**
- `do_not_match` was added during failure-mode review. Optional, costs nothing if empty.
- `embedding` is reserved so V0.1 can populate without a schema migration. V0 matching uses Claude reading the summary text directly.
- The 200-word body is the only field that contains derived content from the user's sessions. The user reviews and edits before any push.

---

## Matching: V0 vs V1 Vision

### V0: Claude Is the Matching Engine

The orchestrator dumps all available trajectory summaries into a single Claude prompt and asks it to compose tables of 6. Constraints (no same-company pairs, respect `do_not_match`, single city) are part of the prompt. Claude returns structured JSON with table assignments and a "why this table" narrative.

This works cleanly up to ~150 users (context budget). The V1 two-pass system below is a strict superset.

### V1+ Two-Pass Matching (post-V0)

**Pass 1 (find the neighborhood)**: rolling summary embedded into a vector. Similarity finds professionals working in nearby problem spaces. A complementarity filter ensures role diversity.

**Pass 2 (rank by direction)**: within the candidate set, rank by who is moving in the same direction. Direction is derived from how the rolling summary has shifted over recent weeks.

**Velocity** creates distinct match archetypes:

| | Same Direction | Different Direction |
|---|---|---|
| **Similar Velocity** | Fellow Explorers: shared questions, exciting energy | Standard similarity match |
| **Different Velocity** | **Guide x Explorer**: highest value match | Low signal |

The Guide x Explorer pairing is where MESH creates the most value: someone three months deep in agent evaluation meets someone who just started exploring it from a product angle. V1 hard-codes this preference; V0 surfaces it via Claude's natural reasoning over the summary text.

---

## 14-Day Timeline

```
WEEK 1: BUILD                              WEEK 2: RUN
-------------                              -----------
Day 1 (today)  spec + plan + repos         Day 8       quiet
Day 2          mesh-data scaffold + schema Day 9       quiet
Day 3          extractor + validator       Day 10      quiet
Day 4          summarization flow          Day 11      quiet
Day 5          orchestrator + invite gen   Day 12      reminder ping
Day 6          dogfood with 5 friends      Day 13      RSVP cutoff
Day 7 (Fri)    LAUNCH EVENT (30 people)    Day 14 (Fri) /mesh-orchestrate run
                                            Day 15 (Sat) DINNER #1 - 7pm
                                            Days 16-17  debrief + V0.1 input
```

---

## Privacy (load-bearing)

Privacy is not a "solve later" problem. It is the thing that kills adoption at the first serious user.

- All session reading runs locally on the user's machine. Raw conversations never leave the device.
- The user-side pipeline holds intermediate artifacts in three staged temp files at `/tmp/mesh_*`, each deleted IMMEDIATELY after the next downstream step:
  1. `/tmp/mesh_sessions.json` (raw scrubbed per-session corpora) - deleted after the per-session digest pass.
  2. `/tmp/mesh_digests.txt` + `/tmp/mesh_groups.json` (compressed signals + grouping metadata) - deleted after the per-project summarization pass.
  3. `/tmp/mesh_project_summaries.txt` + `/tmp/mesh_why.txt` (project-level intermediate + the user's why-seed) - deleted after synthesis.
- Only the 8 schema fields above are uploaded. The pre-push validator REFUSES pushes that contain anything else.
- An interactive privacy lint runs on the candidate body BEFORE push: local Claude flags suspect spans by category (career, family-health, internal-codename, customer-partner, other) and severity, and the user resolves each flag via `AskUserQuestion` with KEEP / REDACT / REPHRASE options. The user reviews the per-project summaries (one checkpoint) and the lint-reviewed body (second checkpoint) before any commit.
- The mesh-data repo is private by default; **launch-window override (2026-05-01)**: temporarily PUBLIC during the launch event window for operational simplicity. ONBOARD.md Step 0 and SKILL.md Step 17 disclose this so onboarders treat their 200-word body as world-readable for the duration. The founder reverts to private after the launch event.
- Users can inspect, edit, or delete their `users/<email>.md` at any time via `/mesh-trajectory sync`.

---

## Failure Modes

| Failure | V0 mitigation |
|---|---|
| Too few opt-ins (<12) | Cancel that week's dinner; defer to next Saturday |
| Odd opt-ins (13, 19, 25) | Orchestrator prompt asks Claude to choose: drop last-confirmed, or one table of 7 |
| Skill install fails on attendee's machine | Fallback Google Form collects same 8 fields; trajectory comes from free-text answer. Disclosed as "partial mode" |
| Local Claude can't read sessions | Skill prompts user to paste a representative conversation; local Claude summarizes from that |
| Bad match (co-workers, exes) | `do_not_match` field + orchestrator prompt enforces "no same-company pairs" hard constraint |
| Concurrent git pushes (30 users at the launch event) | One file per user (`users/<email>.md`), no shared file = no merge conflicts |
| Privacy leak via accidental field | Pre-push validator REFUSES push when non-schema fields are present |
| No-show on dinner night | V0: empty seat acceptable. Track for repeat-offender list. V0.1: refundable deposit |
| Wrong city | `city` is a hard filter; V0 only matches `city=Bengaluru` |
| Orchestrator (Claude) returns garbage | Structured JSON output enforced in prompt; on parse failure, re-run with adjusted prompt; manual table composition fallback |

---

## Verification Strategy

| Layer | V0 (week 1) | V0.1 (post-launch) |
|---|---|---|
| **Algorithm correctness** | None automated; founder spot-checks Claude's reasoning before push | Synthetic personas: 50 LLM-generated trajectories seeded by real GitHub profiles, hand-labeled "should match" pairs; GHArchive + arXiv co-author corpus for ground-truth edges |
| **Privacy guarantee** | Manual review of validator code + dogfood with 5 friends + `git diff` audit | Unit tests on the validator that fail if any non-schema field passes |
| **Match quality** | Dinner #1 is the eval; founder sits at table, observes whether conversations land | Post-dinner NPS + pairwise "would you meet this person again" rating |
| **Skill install reliability** | Dogfood with 5 friends across Mac Intel, Mac M-series, Linux. Document failures | CI install test against a clean Claude Code container |
| **End-to-end flow** | One dry-run dogfood dinner with 5 friends in week 1 (day 6) | n/a |

**Honest take**: the launch event IS the V0 eval. The synthetic + GHArchive offline harness ships in V0.1 sprint 1, after the first dinner provides ground truth to validate offline scores against. Public dataset research (see brainstorming transcript) found no perfect public corpus that matches MESH's actual input distribution (Claude Code session histories).

---

## Out of Scope (deferred to V0.1+)

| Item | Defer reason |
|---|---|
| Embeddings + vector search | Claude as matcher works for <150 users; add when context budget is tight |
| Velocity / direction matching | Requires multi-week trajectory history; impossible until users have history |
| Tags and structured topics | Optional schema additions once Claude-as-matcher hits accuracy ceiling |
| Hosts marketplace | Founder is the host for first 3-5 dinners |
| Agent-native API | No external agent demand until consumer side has density |
| Web app / mobile app | Claude-native is the V0 surface; web only when non-Claude-Code users matter |
| Plugin platform | Clean module boundaries are sufficient until 3rd plugin emerges |
| Payments / deposits | Friction on a free product is wrong before product-market fit |
| Trajectory-bend long-game metric | Requires multiple dinners per user over months |
| Multi-city | Bengaluru only |
| Recursive memory consolidation | V0 takes a single 4-week snapshot; weekly re-summarize comes when users have multi-week trajectories worth folding |

---

## Success Criteria for V0

- [ ] 30 people complete onboarding at the launch event with no privacy regret
- [ ] At least 12 opt in for the Saturday slot
- [ ] Orchestrator produces a table of 6 in under 5 minutes
- [ ] Dinner #1 happens with 5+ attendees showing up
- [ ] Median attendee NPS (informal hand-collected) >= 8/10
- [ ] At least 2 attendees report a follow-up conversation in the week after

---

## What Success Looks Like (V1)

- **Match acceptance**: invitations that convert to attendance.
- **Table NPS**: post-dinner satisfaction.
- **Follow-up rate**: attendee pairs who connect after.
- **Trajectory bend**: embedding shift attributable to a MESH connection.
- **Repeat rate**: users who attend 3+ dinners.

---

*MESH: the meatspace layer for professional serendipity.*
