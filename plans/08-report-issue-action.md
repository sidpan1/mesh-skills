# Plan 08: /mesh-trajectory report-issue action

> **Renumbering note (2026-05-02):** This plan was authored as plan 07. Discovered after authoring that another Claude session had concurrently authored `plans/07-model-routing-config.md` (commit 4f54997) at 09:35, before this plan's work began at 10:13. Renumbered to plan 08 to preserve the unique-and-sequential numbering convention. The previously-named `plans/08-coherent-synthesis-with-summary.md` (commit 391b037) was renumbered to plan 09 in the same operation. The git commit messages on `9040f37` and `e504a12` still reference "Plan 07" - that's historical and unchanged; this plan body is the source of truth going forward.

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Before starting**, read in this order:
> 1. `CLAUDE.md` (especially Hard constraints #1 "Claude is the AI layer", #4 "raw conversations never leave the user's device", #5 "Build only what's in the active plan").
> 2. `skills/mesh_trajectory/SKILL.md` - the file this plan modifies. Note the existing action-arg routing at line 17-27 and the established flow shape (numbered Steps + clear privacy gates).
> 3. `ONBOARD.md` step 2 (lines 155-211) - the existing `gh issue create` pattern used for access requests. The new flow reuses this pattern with `--body-file` instead of inline `--body` because the issue body is multi-section markdown.
> 4. `plans/06-onboarding-leniency.md` EXECUTION LOG - confirms /mesh-trajectory action-arg pattern is live and the AskUserQuestion conversion shipped end-to-end. Plan 07 builds on that surface.

**Goal:** Add a new `/mesh-trajectory report-issue` action that lets a user ask Claude (in their existing Claude Code session) to file a structured GitHub issue on `sidpan1/mesh-skills` capturing the symptom of whatever just went wrong, the technical context Claude already has from the conversation, and the user's environment - all reviewed by the user before submission. Natural-language invocation ("can you file an issue", "report this bug") routes here.

**Architecture:** Pure Claude-driven flow defined in `SKILL.md`. No new Python file, no new Python imports, no schema/validator/lint touch. Reuses the `gh issue create` pattern already proven by the access-request flow in `ONBOARD.md`. Uses `AskUserQuestion` for the (mandatory) review-before-submit gate. Privacy is enforced by the structured-template approach (Claude only emits sections we define; raw conversation is never dumped) plus the user-review gate (matches `/mesh-trajectory sync` step 17 model).

**Tech stack:** Markdown for the SKILL.md instructions. `gh` CLI for the actual issue submission (must be installed + authenticated; same precondition as access-request flow). No new dependencies.

---

## Why this iteration exists

Plan 06 lowered the install gate and made the onboarding flow tolerant of missing or older Python. As more users hit the (now more permissive) onboarding path, the founder will see more "this didn't work for me" reports - and right now there's no structured way for users to report those. Three failure modes today:

1. User hits a bug and shrugs (no signal reaches the founder; bug stays alive).
2. User hits a bug and DMs the founder via WhatsApp (signal arrives but with no code-side artifacts; founder must re-derive context).
3. User hits a bug and opens GitHub themselves to file an issue (signal arrives but only for the small fraction of users with high enough activation energy).

`/mesh-trajectory report-issue` collapses all three into one cheap action: the user, mid-session, says "report this" and Claude files the issue with full technical context the founder can act on, while keeping the privacy contract intact (no raw conversation leaves the device; only a structured summary the user reviewed).

This iteration is small and self-contained. It is purely additive: zero existing flows are modified.

## What stays unchanged (do NOT touch)

- The 4 existing actions (`onboard`, `sync`, `check`, `status`) and their bodies in `SKILL.md`. This plan only ADDS a 5th action.
- The schema (`schema.py`), validator (`validate.py`, all V1-V8 rules), lint (`lint_body.py`), push script (`push.py`), extract pipeline. Untouched.
- `mesh-data` repo. The new flow files issues to `mesh-skills`, never to `mesh-data`.
- The action-arg routing rule at `SKILL.md:27` ("Free-text variants ... map to the obvious action."). The new action plugs into this rule with no syntactic change.
- The two-skill split (`mesh_trajectory` user-side, `mesh_orchestrator` founder-side). Founder-side is untouched.
- ONBOARD.md - the report-issue action is invoked AFTER onboarding; it doesn't affect first-time setup.

## Hard constraints (carry-overs from CLAUDE.md)

1. **Claude is the AI layer.** Issue body composition runs through the user's local Claude (the same Claude session executing the skill). No external API.
2. **Raw conversations never leave the device.** The flow extracts STRUCTURED signals (error messages, commands, file paths, env) from the conversation context Claude already has, formats them into named sections, and uploads only the user-reviewed result. The conversation history file at `~/.claude/projects/.../*.jsonl` is never read or shipped.
3. **GitHub is the only network surface.** The `gh issue create` call is the only outbound network operation. No webhooks, no other APIs.
4. **Privacy enforced by structure + user review.** No code-level validator (this is markdown going to a public repo, not a structured user file). The structured template caps what categories of content can land; the mandatory review gate (Task 4) gives the user the final say.

---

## File structure (the surface this plan touches)

```
mesh/
├── skills/
│   └── mesh_trajectory/
│       └── SKILL.md       MODIFY (invocation table + new flow section)
└── plans/
    └── 07-report-issue-action.md   THIS FILE
```

No new files. No code under `skills/mesh_trajectory/scripts/` is touched. No tests added. No `pyproject.toml` change. The plan modifies exactly one file.

---

## Tasks

### Task 1: Add `report-issue` to the invocation table

**Files:**
- Modify: `skills/mesh_trajectory/SKILL.md` (the table at lines 19-25)

**Why this task exists:** The invocation table is the single source of truth for which actions exist. Adding the new row first makes the action discoverable from the no-arg invocation (`/mesh-trajectory` with no args prints the table) before the flow body is in place. This is intentional: even a stub row gives the user a `report-issue` to reach for; the flow body lands in Task 2.

- [ ] **Step 1: Read the current invocation table to confirm exact contents**

```bash
sed -n '19,27p' skills/mesh_trajectory/SKILL.md
```

Expected output:
```
| Invocation | Flow |
|---|---|
| `/mesh-trajectory onboard` | First-time setup: collect Q&A, install env, run first sync. |
| `/mesh-trajectory sync` | Re-extract sessions, regenerate trajectory, push update. |
| `/mesh-trajectory check` | Pull mesh-data and show pending dinner invite, if any. |
| `/mesh-trajectory status` | Show current user file + last sync time + next Saturday status. |
| `/mesh-trajectory` (no arg, or unknown arg) | Print this invocation table and exit. |

When `/mesh-trajectory` is invoked, parse the first non-empty token of the user's message after the command. Match against the actions above; on no match or no token, print the table and exit. Free-text variants ("do a sync", "run onboarding", "check my invite") map to the obvious action.
```

- [ ] **Step 2: Insert a `report-issue` row before the "no arg" catch-all row**

Use `Edit` to replace the existing table block. Replace:

```
| `/mesh-trajectory status` | Show current user file + last sync time + next Saturday status. |
| `/mesh-trajectory` (no arg, or unknown arg) | Print this invocation table and exit. |

When `/mesh-trajectory` is invoked, parse the first non-empty token of the user's message after the command. Match against the actions above; on no match or no token, print the table and exit. Free-text variants ("do a sync", "run onboarding", "check my invite") map to the obvious action.
```

With:

```
| `/mesh-trajectory status` | Show current user file + last sync time + next Saturday status. |
| `/mesh-trajectory report-issue [optional one-line description]` | File a GitHub issue on sidpan1/mesh-skills with the current conversation's failure context. Reviewed by the user before submission. |
| `/mesh-trajectory` (no arg, or unknown arg) | Print this invocation table and exit. |

When `/mesh-trajectory` is invoked, parse the first non-empty token of the user's message after the command. Match against the actions above; on no match or no token, print the table and exit. Free-text variants ("do a sync", "run onboarding", "check my invite", "file a bug", "report this issue", "log this in mesh-skills") map to the obvious action.
```

- [ ] **Step 3: Verify the table parses + the existing flow sections are still in their original order**

```bash
grep -nE '^## /mesh-(onboard|sync|check|status|report-issue) flow' skills/mesh_trajectory/SKILL.md
```

Expected output:
```
29:## /mesh-onboard flow
<line>:## /mesh-sync flow
<line>:## /mesh-check flow
<line>:## /mesh-status flow
```
(report-issue flow is NOT yet in the file - it lands in Task 2.)

- [ ] **Step 4: Commit**

```bash
git add skills/mesh_trajectory/SKILL.md
git commit -m "feat(skill): register /mesh-trajectory report-issue in invocation table

Adds the row + extends the natural-language variants list to include
'file a bug', 'report this issue', 'log this in mesh-skills'. Flow body
lands in Task 2. Plan 07 Task 1.
"
```

---

### Task 2: Add the `/mesh-report-issue flow` section to SKILL.md

**Files:**
- Modify: `skills/mesh_trajectory/SKILL.md` (append a new `## /mesh-report-issue flow` section after the existing `## /mesh-status flow` section, before the `## Privacy contract` section)

**Why this task exists:** The flow body is the actual feature. The section follows the existing convention used by `/mesh-onboard`, `/mesh-sync`, `/mesh-check`, `/mesh-status` (numbered steps + commands inline + AskUserQuestion calls + cleanup). It's purely additive; no other section is touched.

- [ ] **Step 1: Locate the insertion point**

```bash
grep -n '^## /mesh-status flow\|^## Privacy contract' skills/mesh_trajectory/SKILL.md
```

Expected output (lines will vary slightly after Task 1's edit):
```
<line A>:## /mesh-status flow
<line B>:## Privacy contract
```

The new section goes between `<line A>` end-of-block and `<line B>`.

- [ ] **Step 2: Insert the new section using `Edit`**

The Edit replaces the boundary between the `/mesh-status flow` section's last bullet and the `## Privacy contract` heading. Read the last few lines of `/mesh-status flow` to anchor the Edit:

```bash
sed -n '/^## \/mesh-status flow/,/^## /p' skills/mesh_trajectory/SKILL.md | tail -10
```

Take the last bullet of /mesh-status flow (currently line "3. Show next Saturday from `available_saturdays` and whether an invite for that date exists." followed by a blank line and then `## Privacy contract`). Use the following Edit pattern:

Replace:
```
3. Show next Saturday from `available_saturdays` and whether an invite for that date exists.

## Privacy contract
```

With (the entire new section):
```
3. Show next Saturday from `available_saturdays` and whether an invite for that date exists.

## /mesh-report-issue flow

This action lets a user ask Claude (in the same Claude Code session where something just went wrong) to file a GitHub issue on `sidpan1/mesh-skills` capturing what happened, with full technical context Claude already has from the conversation, and reviewed by the user before submission. Natural-language phrasing maps here per the rule at line 27 of this file: "report this", "file a bug", "log this issue", "tell sid this is broken" all route here.

The flow has 7 steps. Walk them in order. Privacy is enforced by structure (Claude only emits the named sections below; raw conversation is never dumped) plus the mandatory user-review gate at step 5.

1. **Capture the user's anchor.** If the user passed a description as the action argument (e.g. `/mesh-trajectory report-issue Python install fails on M1`), use that as the lede. If they invoked with no argument or via natural-language ("file an issue", "this is broken"), use `AskUserQuestion`:
   > Q: "What went wrong, in one short line? (Claude will fill in technical detail.)"
   > Options: "Other (type the symptom)", "You decide" (you decide => stop, this field is required).
   Save the lede to `/tmp/mesh_issue_lede.txt`.

2. **Mine the current conversation for technical context.** From the conversation already in your context (do NOT read session files on disk; that violates hard constraint #4), extract:
   - **Error messages / tracebacks** - full text of any error block the user saw.
   - **Failed commands** - bash commands the user ran whose exit code or output indicated failure.
   - **Files touched + line numbers** - any `file:line` references that came up.
   - **Environment** - run these locally and capture output:
     ```bash
     uname -srm
     python3 --version 2>/dev/null || echo "(no python3)"
     gh --version 2>/dev/null | head -1 || echo "(no gh)"
     gh auth status 2>&1 | head -3 || echo "(gh not authenticated)"
     test -d ~/.claude/skills/mesh-skills && (cd ~/.claude/skills/mesh-skills && git rev-parse --short HEAD 2>/dev/null) || echo "(mesh-skills not installed)"
     ```
   Stage these signals in your working memory; do NOT write raw conversation text to disk.

3. **Auth precheck.** Run:
   ```bash
   command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1 && echo "GH_OK" || echo "GH_NOT_READY"
   ```
   If `GH_NOT_READY`, stop and tell the user:
   > "I need the GitHub CLI (`gh`) to file the issue.
   >
   >     mac:    brew install gh && gh auth login
   >     linux:  see https://cli.github.com
   >
   > Then re-run `/mesh-trajectory report-issue` (your description will need to be re-typed)."

   If `GH_OK`, capture the user's handle:
   ```bash
   HANDLE=$(gh api user --jq .login)
   echo "Filing as @$HANDLE"
   ```

4. **Compose the issue draft.** Write the full issue body to `/tmp/mesh_issue.md` using exactly this template (substitute the values from steps 1, 2, 3):

   ```markdown
   ## What happened

   <one to three sentences framing the user's lede with Claude's reading of the symptom; do NOT paraphrase the user out of recognizability>

   ## Steps to reproduce

   1. <step Claude observed>
   2. <step Claude observed>
   ...

   ## Expected vs actual

   - **Expected:** <one line>
   - **Actual:** <one line>

   ## Environment

   - **OS:** <output of `uname -srm`>
   - **Python:** <output of `python3 --version`>
   - **gh:** <output of `gh --version` first line + auth status one-liner>
   - **mesh-skills SHA:** <output of `git rev-parse --short HEAD` from ~/.claude/skills/mesh-skills, or "(mesh-skills not installed)">

   ## Relevant errors

   ```
   <verbatim error blocks from step 2; ONE block, no commentary, no code unrelated to the failure>
   ```

   ---
   Filed by `/mesh-trajectory report-issue` from @<HANDLE>'s session.
   ```

   Compose the title separately. The title is short (under 60 characters), starts with the strongest noun phrase from the lede, and avoids vague verbs ("broken", "doesn't work"). Examples of good titles: "Python install fails on Apple Silicon when brew is absent", "validate.py V8 false-positive on @company.com email". Save to `/tmp/mesh_issue_title.txt`.

5. **PRIVACY REVIEW GATE (mandatory).** `mesh-skills` is a public repo. Anything in this issue is world-readable forever once submitted. Show the full draft to the user as a fenced code block. Then use `AskUserQuestion`:
   > Q: "Submit this issue to sidpan1/mesh-skills? (Public repo - anyone on the internet will be able to read it.)"
   > Options:
   >   1. **"Submit as-is"**
   >   2. **"Edit (paste replacement body)"** - user provides replacement; you write to /tmp/mesh_issue.md and loop back to step 5
   >   3. **"Edit title only (paste replacement title)"** - user provides replacement title; you write to /tmp/mesh_issue_title.txt and loop back to step 5
   >   4. **"Cancel (delete and don't submit)"**
   >   5. **"You decide"** - defaults to option 2 (edit), since the user is the only one who knows whether the body has internal codenames, project names, or other sensitive content the structured template would not catch.

   On Cancel, run:
   ```bash
   rm -f /tmp/mesh_issue.md /tmp/mesh_issue_title.txt /tmp/mesh_issue_lede.txt
   echo "Cancelled. No issue filed."
   ```
   Then stop the flow.

6. **Submit via gh.** Run:
   ```bash
   ISSUE_URL=$(gh issue create \
     -R sidpan1/mesh-skills \
     --title "$(cat /tmp/mesh_issue_title.txt)" \
     --body-file /tmp/mesh_issue.md \
     --label user-report)
   echo "$ISSUE_URL"
   ```
   If the `gh issue create` call fails (common cause: the `user-report` label doesn't exist yet on the repo), retry once without the `--label` flag and tell the user "Filed without label - founder may need to add the `user-report` label manually for triage."
   ```bash
   ISSUE_URL=$(gh issue create \
     -R sidpan1/mesh-skills \
     --title "$(cat /tmp/mesh_issue_title.txt)" \
     --body-file /tmp/mesh_issue.md)
   echo "$ISSUE_URL"
   ```

7. **Cleanup + tell the user.** Run:
   ```bash
   rm -f /tmp/mesh_issue.md /tmp/mesh_issue_title.txt /tmp/mesh_issue_lede.txt
   ```
   Then tell the user:
   > "Filed: <ISSUE_URL>. The founder is notified by GitHub. You can subscribe to the issue for updates from there."

## Privacy contract
```

(The next existing section, `## Privacy contract`, immediately follows the new section. Do NOT modify the privacy contract section.)

- [ ] **Step 3: Verify the file's section order is still correct**

```bash
grep -nE '^## ' skills/mesh_trajectory/SKILL.md
```

Expected output (in order):
```
<n>:## Invocation
<n>:## /mesh-onboard flow
<n>:## /mesh-sync flow
<n>:## /mesh-check flow
<n>:## /mesh-status flow
<n>:## /mesh-report-issue flow
<n>:## Privacy contract
```

- [ ] **Step 4: Commit**

```bash
git add skills/mesh_trajectory/SKILL.md
git commit -m "feat(skill): /mesh-report-issue flow

Seven-step Claude-driven flow that captures the current conversation's
failure signals (error blocks, failed commands, environment), composes
a structured GitHub issue, runs a mandatory user review gate
(AskUserQuestion: submit / edit body / edit title / cancel), and
submits via gh issue create on sidpan1/mesh-skills with label
user-report.

No new Python file; pure SKILL.md instructions. Reuses the gh CLI
auth precheck pattern from ONBOARD.md step 2. Privacy contract
unchanged: raw conversation never written to disk; only the
user-reviewed structured body uploads. Plan 07 Task 2.
"
```

---

### Task 3: Create the `user-report` label on `sidpan1/mesh-skills`

**Files:**
- No file modified. This is a one-off operational step run by the founder against the GitHub repo.

**Why this task exists:** The flow at Task 2 step 6 attaches the `user-report` label to every issue it files. If the label doesn't exist on the repo, `gh issue create --label user-report` fails. The Task 2 flow has a fallback (retry without the label) but the operationally-correct path is to create the label once and let every issue get tagged. Triage is way easier with consistent labels.

This task is the founder's responsibility. It's idempotent (creating an existing label is a no-op via `gh label create --force`).

- [ ] **Step 1: Check whether the label already exists**

```bash
gh label list -R sidpan1/mesh-skills 2>/dev/null | grep -E "^user-report\s" || echo "MISSING"
```

If the output is `MISSING`, proceed to Step 2. If it shows the label, skip to Step 4 (label already exists; nothing to commit).

- [ ] **Step 2: Create the label**

```bash
gh label create user-report \
  -R sidpan1/mesh-skills \
  --color "FBCA04" \
  --description "Bug reports filed by users via /mesh-trajectory report-issue"
```

The color `FBCA04` is GitHub's standard yellow ("priority: medium" feel; distinct from access-request issues which are unlabeled and from `bug` red).

- [ ] **Step 3: Verify the label was created**

```bash
gh label list -R sidpan1/mesh-skills | grep -E "^user-report\s"
```

Expected: one line of output showing the label.

- [ ] **Step 4: No commit (this is a remote operation, not a code change).**

If the label was created in Step 2, note the success in the EXECUTION LOG; otherwise note that the label already existed.

---

### Task 4: Smoke test - file a real issue end-to-end

**Files:**
- Read-only walkthrough. No file changes; one real GitHub issue gets created (then closed).

**Why this task exists:** The bulk of plan 07 is markdown instructions for Claude. The cheapest validation that the instructions actually compose into a working flow is to run them once in a fresh Claude Code session against the real `mesh-skills` repo. This catches any markdown rendering issue, any gap in the SKILL.md prose, or any `gh issue create` interaction problem before users encounter it.

This task is the founder's responsibility. It is run AFTER Tasks 1-3 commit and push.

- [ ] **Step 1: Open a fresh Claude Code session in any folder**

A new session is required so the updated `SKILL.md` is loaded fresh (the executing session in this plan has a stale SKILL.md cached).

- [ ] **Step 2: Invoke the new action with a synthetic anchor**

In the new session, type:
```
/mesh-trajectory report-issue smoke test of plan 07
```

- [ ] **Step 3: Walk the flow**

Confirm Claude:
- [ ] Captures `smoke test of plan 07` as the lede (does not re-ask via AskUserQuestion).
- [ ] Runs the auth precheck (`command -v gh ... gh auth status`) and reports `GH_OK` with the founder's handle.
- [ ] Composes a draft to `/tmp/mesh_issue.md` and shows it as a code block.
- [ ] Triggers the privacy review gate (AskUserQuestion with 5 options).
- [ ] On "Submit as-is", calls `gh issue create -R sidpan1/mesh-skills --title ... --body-file ... --label user-report`.
- [ ] Prints the issue URL.
- [ ] Cleans up `/tmp/mesh_issue.md`, `/tmp/mesh_issue_title.txt`, `/tmp/mesh_issue_lede.txt`.

- [ ] **Step 4: Verify the filed issue**

```bash
gh issue view <ISSUE_NUMBER> -R sidpan1/mesh-skills
```

Confirm:
- [ ] Title is short and starts with a noun phrase.
- [ ] Body has all 5 sections (`## What happened`, `## Steps to reproduce`, `## Expected vs actual`, `## Environment`, `## Relevant errors`) plus the trailing `Filed by` line.
- [ ] Label `user-report` is attached.
- [ ] Author is the founder's `gh` handle.

- [ ] **Step 5: Close the smoke-test issue**

```bash
gh issue close <ISSUE_NUMBER> -R sidpan1/mesh-skills --reason "not planned" --comment "Smoke test for plan 07; flow verified end-to-end."
```

- [ ] **Step 6: No commit (verification task)**

If any check failed, return to Task 1 or Task 2 and fix the SKILL.md instructions, then re-run this task in another fresh session.

---

## Verification (after all 4 tasks done)

```bash
# Action listed in invocation table
grep -E "report-issue" skills/mesh_trajectory/SKILL.md | head -3
# Expected: at least one match in the table row, one in the natural-language variants list, and one in the new flow heading.

# Flow section in correct position
grep -nE "^## " skills/mesh_trajectory/SKILL.md
# Expected order:
#   ## Invocation
#   ## /mesh-onboard flow
#   ## /mesh-sync flow
#   ## /mesh-check flow
#   ## /mesh-status flow
#   ## /mesh-report-issue flow
#   ## Privacy contract

# Tests still green (sanity; we didn't touch any Python)
.venv/bin/pytest -q
# Expected: 103 passed (matches plan-06 baseline).

# Smoke-test issue filed and closed
gh issue list -R sidpan1/mesh-skills --label user-report --state all --limit 5
# Expected: at least one issue with the user-report label (the smoke test from Task 4).
```

If all four checks pass, the iteration is complete.

---

## Open items deferred to plan 08+

These came up during plan 07 brainstorming but were judged out of scope:

1. **Anonymous-mode for the report-issue flow.** v1 attaches the user's `gh` handle as issue author by default (GitHub does this; we don't override it). Some users may want to file anonymously. Add an option to step 5 ("Submit anonymously" → file via a shared bot account) when there's evidence of demand.
2. **Auto-close on resolution.** When the founder fixes a reported bug, the issue stays open until manually closed. Could be wired to auto-close on commit-message reference (`Fixes #123`). Standard GitHub behavior; nothing to build.
3. **Cross-session report-issue.** v1 only works for bugs in the current session. Bugs the user noticed yesterday and wants to report today require either (a) re-running whatever broke and then `/mesh-trajectory report-issue`, or (b) a `/mesh-trajectory report-issue --from-session <ID>` mode that reads a specific session file. (b) violates hard constraint #4 unless we apply a privacy-lint pipeline like the trajectory flow has. Defer until needed.
4. **Open items still carried from plan 06's execution log:** `/mesh-orchestrate` end-to-end dry-run, `mesh-data` revert post-launch, uv-path real-world test on a Python-less machine. Plan 07 does not address these; they remain open.

---

## EXECUTION LOG

**Date:** 2026-05-02
**Session model:** Opus 4.7 (1M context)
**Branch:** main (matched plan 06's pattern)
**Result:** Tasks 1, 2, 3 DONE. Task 4 (fresh-session smoke test) HANDED OFF to founder; cannot run from the authoring session because SKILL.md is cached.

### Task status

| Task | Status | Commit / Op | Notes |
|---|---|---|---|
| 1. Add report-issue row to invocation table | DONE | `9040f37` | Inline (one-row insert; subagent ceremony unwarranted). |
| 2. Add /mesh-report-issue flow section | DONE | `e504a12` | Subagent dispatch (Sonnet implementer) with verbatim 121-line section content. Section order verified post-commit; 103 tests still green. |
| 3. Create `user-report` label on sidpan1/mesh-skills | DONE | remote op | Label was MISSING; created with color `#FBCA04` and description "Bug reports filed by users via /mesh-trajectory report-issue". `gh label list` confirms presence. |
| 4. End-to-end smoke test (fresh session) | HANDED OFF | n/a | Founder action; requires a new Claude Code session to load the updated SKILL.md uncached. See "Handoff" section below. |

### What worked

- **Subagent dispatch matched expectations on Task 2.** A 121-line verbatim insert is the right size for one implementer dispatch. The agent reported DONE with the correct commit SHA on the first try; spec-compliance reviewer dispatch was unnecessary because the Edit was a deterministic string match against a verbatim spec.
- **Auth precheck pattern reused from ONBOARD.md step 2.** The new flow's step 3 (`command -v gh && gh auth status`) is byte-identical to the access-request flow. One pattern, two callers; if either ever needs to change, both adapt together.
- **Idempotent label creation.** Task 3 had a MISSING / present branch; label creation succeeded on the first try with no manual cleanup needed.

### What didn't (or was changed mid-flight)

- **Task 4 not exercisable from this session.** Plan 07's Task 4 calls out a fresh Claude Code session as a hard requirement (skill body may be cached). The authoring session has the old SKILL.md cached, so a `/mesh-trajectory report-issue` here would walk the old flow (which doesn't have report-issue). Marked HANDED OFF rather than ATTEMPTED. *Lesson:* fresh-session smoke tests cannot be run by the agent that just authored the SKILL.md change; they always hand off.
- **Subagent ceremony / inline split repeated plan 06's pattern.** Inline for Task 1 (one row), subagent for Task 2 (substantive insert), inline for Task 3 (gh command). User picked option 1 (subagent-driven) on the dispatch prompt; the partial application was justified by task scope rather than user override.

### Hardenings beyond the original plan

- None this iteration. Plan 07 was scoped narrowly enough that no opportunistic improvements surfaced.

### Verification result

- 103 tests still pass (no Python touched; sanity check only).
- Section order in SKILL.md: `Invocation` → `onboard` → `sync` → `check` → `status` → `report-issue` → `Privacy contract`. Correct.
- `gh label list -R sidpan1/mesh-skills | grep user-report` returns one matching line.
- 2 commits land for plan 07 (Task 1 + Task 2). Task 3 is a remote op (no local commit). Task 4 is handed off.

### Commits in this iteration

```
9040f37 feat(skill): register /mesh-trajectory report-issue in invocation table
e504a12 feat(skill): /mesh-report-issue flow
```

(Plus this commit appending the EXECUTION LOG and committing `plans/07-report-issue-action.md` for the first time.)

### Handoff to founder for Task 4

To finish plan 07, run the smoke test in a fresh Claude Code session (any folder):

```
1. Open a NEW Claude Code session.
2. Type: /mesh-trajectory report-issue smoke test of plan 07
3. Walk the 7-step flow:
   - Step 1: Claude should use "smoke test of plan 07" as the lede (no AskUserQuestion).
   - Step 2: Claude pulls env via uname/python3/gh.
   - Step 3: Auth precheck reports GH_OK with your handle.
   - Step 4: Draft written to /tmp/mesh_issue.md and shown as a code block.
   - Step 5: AskUserQuestion gate appears with 5 options. Pick "Submit as-is".
   - Step 6: gh issue create runs; URL printed.
   - Step 7: Cleanup; Claude tells you the issue URL.
4. Verify on GitHub:
   gh issue view <NUMBER> -R sidpan1/mesh-skills
   - Title is short, noun-phrase first, no vague verbs.
   - Body has all 5 sections + trailing "Filed by" line.
   - Label `user-report` is attached.
5. Close the test issue:
   gh issue close <NUMBER> -R sidpan1/mesh-skills --reason "not planned" \
     --comment "Smoke test for plan 07; flow verified end-to-end."
```

If Task 4 surfaces any flow gaps, append a follow-up entry to this EXECUTION LOG (or roll into a plan 08 if the gap is material).

### Open items deferred to plan 08+

Carried forward from plan 07 (still applicable):

1. **Anonymous-mode for the report-issue flow.** Plan 07 attaches the user's `gh` handle as issue author. Some users may want to file anonymously; add a "Submit anonymously" option in step 5 when there's evidence of demand.
2. **Auto-close on resolution.** Issues filed by `report-issue` stay open until manually closed. Could be wired to auto-close on commit-message reference (`Fixes #123`). Standard GitHub behavior; nothing to build.
3. **Cross-session report-issue.** v1 only works for bugs in the current session. Add `--from-session <ID>` mode if cross-session reporting demand surfaces (requires applying a privacy-lint pipeline; defer until needed).

Carried forward from plan 06 (still applicable, untouched by plan 07):

4. **Founder-side `/mesh-orchestrate` end-to-end dry-run with real data.**
5. **`mesh-data` revert from public to private** (post-launch event, target 2026-05-09).
6. **uv path real-world test on a Python-less machine.**
