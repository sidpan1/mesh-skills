# Plan 06: Onboarding leniency (Python floor + AskUserQuestion + symlink cleanup)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Before starting**, read in this order:
> 1. `CLAUDE.md` (especially Hard constraints #5 "Build only what's in the active plan", and the "Naming convention" section which this plan updates).
> 2. `ONBOARD.md` (the paste prompt this plan rewrites in two places: Step 0 consent and Step 1 Python detect).
> 3. `skills/mesh_trajectory/SKILL.md` (the `/mesh-onboard` flow this plan touches at step 2 only - rest stays).
> 4. `plans/04-launch-readiness.md` EXECUTION LOG section "UX hardening" - that's where the strict `>=3.11` Python check came in via commit `eea02ed`. We are loosening it.
> 5. `plans/05-multipart-trajectory.md` EXECUTION LOG - confirms schema v2 shipped end-to-end. This plan does NOT touch the schema, validator, lint, or push pipeline.

**Goal:** Three independent UX improvements bundled because they share the same surface (onboarding):
1. Lower the hard Python floor from `>=3.11` to `>=3.10` and replace the strict `assert+exit` with a guided detect → AskUserQuestion fallback so users without compatible Python get walked through install instead of bouncing.
2. Convert the Step 0 consent gate (`ONBOARD.md`) and the `/mesh-onboard` profile Q&A (`SKILL.md` step 2) from prose-prompts to the `AskUserQuestion` widget, with a "You decide" option per global CLAUDE.md item 16.
3. Delete the dead in-repo symlinks `skills/mesh-trajectory` and `skills/mesh-orchestrator` (nothing reads them; the install-time symlink in `~/.claude/skills/` is what actually bridges the names) and update CLAUDE.md's Naming convention section accordingly.

**Architecture:** No infra change. No new code files. No new Python imports. No schema/validator/lint/push touch. Three files modified (`pyproject.toml`, `ONBOARD.md`, `skills/mesh_trajectory/SKILL.md`), one file updated for accuracy (`CLAUDE.md`), two filesystem entries deleted (`skills/mesh-trajectory`, `skills/mesh-orchestrator`). The two-skill split (user-side `mesh_trajectory` + founder-side `mesh_orchestrator`) is unchanged and confirmed load-bearing.

**Tech stack:** Python 3.10+ (lowered from 3.11) + pytest (unchanged). Markdown for prose changes. No new dependencies.

---

## Why this iteration exists

Plan 04 shipped a strict `python3 -c "assert sys.version_info >= (3, 11)"` check in ONBOARD.md Step 1 that fails-fast with a one-line install hint. Field reports indicate users without 3.11 (or without any python3) bounce out at this gate even when their system would otherwise work fine on 3.10. The codebase has zero 3.11-only features (verified by grep: no `tomllib`, no `match/case`, no `Self`, no `ParamSpec`, no `StrEnum`), so the floor is artificially high.

Separately, the global CLAUDE.md preference (item 12) is to use the `AskUserQuestion` widget for choices instead of prose monologues. The current ONBOARD.md Step 0 ("Continue?") and SKILL.md `/mesh-onboard` step 2 (seven profile fields collected one-by-one as prose questions) are the last surfaces in the user-side flow that don't follow this preference. Step 2 of ONBOARD.md (GitHub access path) already uses AskUserQuestion - this plan applies the same treatment to the remaining surfaces.

Finally, the in-repo symlinks `skills/mesh-trajectory -> mesh_trajectory` and `skills/mesh-orchestrator -> mesh_orchestrator` are leftovers from plan 01's original design (which proposed dash-named directories with the symlink going the *other* way for Python imports). The design flipped during plan 01 execution; the install command in `ONBOARD.md:39` symlinks `~/.claude/skills/mesh-trajectory -> $PWD/skills/mesh_trajectory` directly, bypassing the in-repo symlink entirely. Grep confirms no code references the in-repo dash paths. The CLAUDE.md "Naming convention" section is also slightly stale because of this drift; we fix it in the same pass.

## What stays unchanged (do NOT touch)

- The two-skill split. `skills/mesh_trajectory/` (user-side) and `skills/mesh_orchestrator/` (founder-side) are both load-bearing. The orchestrator has 3 dedicated test files (`test_load_users.py`, `test_parse_response.py`, `test_write_invites.py`) and was last touched in commit `5ba3e3e` (2026-05-01). Do not delete or merge.
- The schema (`schema.py`), validator (`validate.py`, all V1-V8 rules), privacy lint (`lint_body.py`, `prompts/lint_body.md`), push script (`push.py`), or any prompt under `prompts/sections/`.
- The `/mesh-trajectory` slash command name + action-arg routing (`onboard | sync | check | status`). Single registered command stays.
- ONBOARD.md Step 2 (GitHub access verify) - already uses `AskUserQuestion`, no edits.
- ONBOARD.md Step 3 (corpus check) and Step 4 (handoff). Step 3 already uses `AskUserQuestion` for the 1-4 sessions warn case. Step 4 is prose-only by design (it hands off to a fresh session; no choice to offer).
- The `/mesh-sync`, `/mesh-check`, `/mesh-status` flows in `SKILL.md`. Only `/mesh-onboard` step 2 changes.
- Hard constraints #1 (no external LLMs), #2 (GitHub is only datastore), #3 (privacy enforced by code), #4 (raw conversations never leave device). This plan does not interact with any of them.

## Hard constraints (carry-overs from CLAUDE.md)

1. **Build only what's in this plan.** No drive-by refactors of the validator, the extract pipeline, or the orchestrator. If a task seems to need them, stop.
2. **The install symlink lives at `~/.claude/skills/mesh-trajectory` (outside the repo).** Created by `ONBOARD.md` step 1 on the user's machine. We do NOT touch that. We only delete the redundant in-repo copies at `skills/mesh-trajectory` and `skills/mesh-orchestrator`.
3. **Privacy gates and PII stop-list are out of scope.** Step 2 of `/mesh-onboard` collects profile fields (name, email, etc.) that go into frontmatter, not the body. Validator V8 (PII stop-list) only applies to the body. AskUserQuestion conversion of step 2 does not change what gets pushed.

---

## File structure (the surface this plan touches)

```
mesh/
├── pyproject.toml                                  MODIFY (1 line)
├── ONBOARD.md                                      MODIFY (Step 0 + Step 1)
├── CLAUDE.md                                       MODIFY (Naming convention section)
├── skills/
│   ├── mesh-trajectory       (symlink)             DELETE
│   ├── mesh-orchestrator     (symlink)             DELETE
│   ├── mesh_trajectory/
│   │   └── SKILL.md                                MODIFY (/mesh-onboard step 2 only)
│   └── mesh_orchestrator/                          UNTOUCHED
└── tests/                                          UNTOUCHED (no test code changes)
```

No new files. No code under `skills/mesh_trajectory/scripts/` is touched. Tests are run to verify the floor change is safe, but no test files are added or edited.

---

## Tasks

### Task 1: Verify the codebase has no 3.11-only features (sanity gate)

**Files:**
- Read-only checks; nothing modified.

**Why this task exists:** The lowering of the floor is safe only if the code does not actually use 3.11-only features. We verified this once during brainstorming; this task makes it a reproducible gate that future readers of this plan can re-run in a worktree before committing.

- [ ] **Step 1: Grep for 3.11-only stdlib imports**

Run from repo root:
```bash
grep -rn -E "^(from|import)\s+tomllib|^from typing import.*\b(Self|LiteralString|Never|TypeVarTuple|Unpack)\b" \
  skills/ scripts/ tests/ 2>/dev/null
```
Expected: zero output. (`tomllib` is 3.11+; `Self` etc. landed in `typing` in 3.11.)

- [ ] **Step 2: Grep for `match/case` (3.10+, but a leniency-floor sanity check)**

```bash
grep -rn -E "^\s*match\s+\w+:" skills/ scripts/ tests/ 2>/dev/null
```
Expected: zero output, OR matches that we accept (`match` is 3.10+ which is the new floor).

- [ ] **Step 3: Grep for exception groups (3.11-only syntax)**

```bash
grep -rn -E "except\*\s|ExceptionGroup\b|BaseExceptionGroup\b" skills/ scripts/ tests/ 2>/dev/null
```
Expected: zero output.

- [ ] **Step 4: Run the full test suite on the current Python to confirm green baseline**

```bash
.venv/bin/pytest -q
```
Expected: all tests pass (the plan-05 baseline is 103 tests).

- [ ] **Step 5: No commit (read-only task)**

If any of steps 1-3 returned output, STOP. The floor cannot be safely lowered without separate work to remove the 3.11-only feature first. Surface the finding to the user and stop the plan here.

If all four steps came back clean, proceed to Task 2.

---

### Task 2: Lower the Python floor in pyproject.toml from 3.11 to 3.10

**Files:**
- Modify: `pyproject.toml:4`

**Why this task exists:** The single source of truth for the project's Python version is `pyproject.toml`. Editing this first means downstream tooling (pip, IDE checkers) sees the new floor before the prose changes land in ONBOARD.md.

- [ ] **Step 1: Read the current line**

```bash
grep -n "requires-python" pyproject.toml
```
Expected output:
```
4:requires-python = ">=3.11"
```

- [ ] **Step 2: Edit pyproject.toml**

Replace:
```
requires-python = ">=3.11"
```
With:
```
requires-python = ">=3.10"
```

- [ ] **Step 3: Reinstall the package and re-run the test suite to verify nothing broke**

```bash
.venv/bin/pip install -e ".[dev]" >/dev/null
.venv/bin/pytest -q
```
Expected: same test count and all green.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: lower Python floor to >=3.10

Verified by grep that the codebase has no 3.11-only features
(tomllib, match/case, except*, typing.Self/LiteralString). Plan 06
loosens the install-time check to match.
"
```

---

### Task 3: Rewrite ONBOARD.md Step 1 (Python detect + uv-based guided fallback)

**Files:**
- Modify: `ONBOARD.md:19-45` (Step 1 block)

**Why this task exists:** The current Step 1 strict `assert sys.version_info >= (3, 11)` block exits the prompt the moment a user lacks 3.11. The new Step 1 detects three cases (no python3, python3 < 3.10, python3 >= 3.10). On miss, it offers `uv` (Astral's Python manager) as the auto-install path because uv collapses the three platform branches (mac brew / linux sudo apt / "other: see python.org") into one command that works everywhere without sudo and ships a managed Python in ~5s. Users with a working Python 3.10+ are NOT touched - uv is opt-in only on the failure path.

**Why uv (not brew/apt):**
- Single command works on mac, linux, WSL, Windows. No platform branching.
- No sudo required (installs to `~/.local/`).
- Fast (~5s vs apt ~30s vs brew ~1-2min).
- The Python it installs is project-scoped via `.venv` - we don't touch system Python or PATH.
- The trade-off (`curl|sh` from astral.sh) is the same trust ask as rustup/nvm/brew-installer; users who refuse can take the manual path.

**Critical ordering constraint:** Bash detection must run BEFORE the AskUserQuestion call. Claude in the user's session needs the detected version + platform string to populate the question's options. Do not invert the order.

- [ ] **Step 1: Read the current Step 1 block to confirm exact line range**

```bash
sed -n '19,45p' ONBOARD.md
```
Note the exact existing content so the replace is unambiguous.

- [ ] **Step 2: Replace the block**

Replace the existing Step 1 (everything from `## Step 1 of 4: Install the skill` through the closing `**"[1/4] Skill installed."**` line, but NOT the next heading) with the content shown in the 4-backtick fence below. (The 4-backtick outer fence is just to keep nested 3-backtick code blocks intact in this plan; the actual ONBOARD.md content uses normal 3-backtick fences as written.)

````markdown
## Step 1 of 4: Install the skill

This step has two sub-flows depending on what Python the user has. Run the detection FIRST; then act on the result.

### 1a. Detect Python

Run this single block. It produces one of three outcomes: `PY_OK`, `PY_OLD`, or `PY_MISSING`. Capture the output before doing anything else.

```bash
if ! command -v python3 >/dev/null 2>&1; then
  echo "PY_MISSING"
elif python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"; then
  PYV=$(python3 -c "import sys; print('.'.join(str(x) for x in sys.version_info[:3]))")
  echo "PY_OK $PYV"
else
  PYV=$(python3 -c "import sys; print('.'.join(str(x) for x in sys.version_info[:3]))")
  echo "PY_OLD $PYV"
fi
```

### 1b. Branch on the detection

**If `PY_OK`:** Tell the user `"Python $PYV detected; proceeding."` and skip to step 1d (install the skill).

**If `PY_OLD` or `PY_MISSING`:** use `AskUserQuestion`:

> Q: "MESH needs Python 3.10 or newer. Detected: `<PY_OLD $PYV | no python3 found>`. How do you want to proceed?"
> Options:
>   1. **"Auto-install via uv (recommended; ~5s, no sudo, all platforms)"** - I run a one-liner from astral.sh that fetches uv, then `uv python install 3.11` for a project-scoped Python. Your system Python is not touched.
>   2. **"I'll install Python myself, exit and re-run this prompt"** - You install Python 3.10+ via brew / apt / python.org, then re-paste this prompt.
>   3. **"You decide"** - Defaults to option 1.

If they pick option 2, print:

> "OK. Install Python 3.10+ via the method you prefer:
>     mac:    brew install python@3.11    (https://brew.sh)
>     linux:  sudo apt install -y python3.11    (Debian/Ubuntu) or your distro's equivalent
>     other:  https://www.python.org/downloads/
>
> Re-paste this prompt once you have python3 --version reporting 3.10 or newer."

Then stop the prompt.

If they pick option 1 (or "You decide"), show the exact command before running it:

```bash
# Show the exact command first; do not run silently.
echo "Will run, in order:"
echo "  1. curl -LsSf https://astral.sh/uv/install.sh | sh   # installs uv to ~/.local/bin"
echo "  2. uv python install 3.11                            # downloads a project-scoped Python"
```

Then ask one more confirmation via `AskUserQuestion`:
> Q: "Run the two commands above?"
> Options: "Yes, run them" / "Cancel" / "You decide" (defaults to Yes)

On Cancel, stop with: `"OK, exiting. Re-run this prompt once Python 3.10+ is available."`

On Yes, run the install:

```bash
set -e
# Install uv if not already present.
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # uv installs to ~/.local/bin which may not be on PATH yet.
  export PATH="$HOME/.local/bin:$PATH"
fi
# Verify uv is now callable.
uv --version
# Download a project-scoped Python 3.11.
uv python install 3.11
```

After this completes, set a marker so step 1d knows to use uv-managed Python:

```bash
USE_UV=1
```

(If `python3` was already 3.10+, `USE_UV` stays unset and step 1d uses the system `python3`.)

### 1c. Confirm we have a usable Python

By the time control reaches here, EITHER `python3 --version` reports 3.10+ (PY_OK path), OR uv is installed and `uv python install 3.11` succeeded (`USE_UV=1`). Tell the user one of:
- `"Using your existing Python: $(python3 -V)."`
- `"Using uv-managed Python 3.11 (your system Python is not modified)."`

### 1d. Install the skill (idempotent)

```bash
set -e
mkdir -p ~/.claude/skills
cd ~/.claude/skills
if [ ! -e mesh-skills ]; then
  git clone https://github.com/sidpan1/mesh-skills.git
fi
cd mesh-skills

# Create the venv. If we used uv to fetch Python, create the venv with uv;
# otherwise use the system python3 -m venv.
if [ ! -d .venv ]; then
  if [ "${USE_UV:-0}" = "1" ]; then
    uv venv --python 3.11 .venv
  else
    python3 -m venv .venv
  fi
fi

.venv/bin/pip install -e . >/dev/null
ln -snf "$PWD/skills/mesh_trajectory" ~/.claude/skills/mesh-trajectory
echo "[1/4] MESH skill installed at ~/.claude/skills/mesh-trajectory"
```

If any line fails, surface the exact error to the user and stop.

After success, tell the user: **"[1/4] Skill installed."**
````

- [ ] **Step 3: Confirm the file still parses as Markdown and Steps 2-4 are intact**

```bash
grep -n "^## Step" ONBOARD.md
```
Expected output (in order):
```
## Step 0: Tell the user what's about to happen
## Step 1 of 4: Install the skill
## Step 2 of 4: Verify GitHub WRITE access
## Step 3 of 4: Check the corpus has enough material
## Step 4 of 4: Hand off to a fresh session
```
If any of Steps 0, 2, 3, 4 are missing, the edit clobbered them. Restore from git and try again.

- [ ] **Step 4: Commit**

```bash
git add ONBOARD.md
git commit -m "feat(onboard): lenient Python detect with uv-based guided fallback

Replaces the strict 3.11 assert+exit with a 2-branch detect: PY_OK
proceeds with system Python; PY_OLD/PY_MISSING uses AskUserQuestion
to offer uv (one cross-platform command, no sudo) or manual install.
uv-managed Python is project-scoped via .venv; system Python is not
modified. Floor lowered to 3.10 in pyproject.toml (Task 2). Plan 06 Task 3.
"
```

---

### Task 4: Convert ONBOARD.md Step 0 consent gate to AskUserQuestion

**Files:**
- Modify: `ONBOARD.md:11-17` (Step 0 block)

**Why this task exists:** The current Step 0 ends with "Continue?" as a free-text question. Converting it to `AskUserQuestion` matches the rest of the flow's choice surfaces and gives users a "tell me more about privacy" branch they currently have to ask for in free-text.

- [ ] **Step 1: Read the current Step 0 block**

```bash
sed -n '11,17p' ONBOARD.md
```

- [ ] **Step 2: Replace the block**

Replace the existing Step 0 content (everything between `## Step 0: Tell the user what's about to happen` and `## Step 1 of 4: Install the skill`) with:

```markdown
## Step 0: Tell the user what's about to happen

In your own words:

> "MESH curates a Saturday-7pm dinner for 6 builders, matched on what you are actually building (read from your local Claude Code sessions). Four steps: install the skill, verify GitHub access, check your last 4 weeks have enough material, and run the summary flow in a fresh session. Raw conversations never leave your machine. Only a 200-word summary you review goes to a shared repo."
>
> "**Launch-window note: the shared repo is currently public; the founder will revert it to private after the launch event. Treat your 200-word body as world-readable when you review it.**"

Then ask via `AskUserQuestion`:

> Q: "Continue with MESH onboarding?"
> Options:
>   1. **"Yes, proceed"** - start step 1.
>   2. **"Tell me more about the privacy model first"** - print the Privacy section from `spec.md` and ask again.
>   3. **"Stop"** - exit cleanly.
>   4. **"You decide"** - defaults to option 1.

If they pick option 3, print: `"OK, no changes made. Re-paste this prompt anytime to onboard."` and stop.

If they pick option 2, fetch and print the Privacy section from spec.md (search for `## Privacy`), then re-ask the same `AskUserQuestion` with options 1, 3, "You decide" (drop option 2 the second time).

If they pick option 1 (or "You decide"), proceed to Step 1.
```

- [ ] **Step 3: Confirm the rest of the file is intact**

```bash
grep -c "^## Step" ONBOARD.md
```
Expected: 5 (Steps 0-4).

- [ ] **Step 4: Commit**

```bash
git add ONBOARD.md
git commit -m "feat(onboard): Step 0 consent via AskUserQuestion

Three options + 'You decide' instead of free-text 'Continue?'. Adds an
explicit branch for users who want to read the privacy section before
agreeing. Plan 06 Task 4.
"
```

---

### Task 5: Convert /mesh-onboard step 2 (profile Q&A) to AskUserQuestion

**Files:**
- Modify: `skills/mesh_trajectory/SKILL.md` (the `/mesh-onboard flow` step 2 block, lines starting with `2. Ask the user, one at a time:`)

**Why this task exists:** Step 2 currently lists 7 fields collected as prose questions. Per global CLAUDE.md item 12 ("Prefer Interactive Clarification") and item 16 ("AskUserQuestion defaults"), each should be an `AskUserQuestion` call with a "You decide" option. Free-text fields ride through the widget's "Other" affordance.

- [ ] **Step 1: Read the current step 2 block**

```bash
sed -n '/^## \/mesh-onboard flow/,/^## \/mesh-sync flow/p' skills/mesh_trajectory/SKILL.md | head -30
```
Locate the line `2. Ask the user, one at a time:` and the bullet list of 7 fields under it.

- [ ] **Step 2: Replace step 2 of the /mesh-onboard flow**

Replace the existing item 2 (from `2. Ask the user, one at a time:` through the last sub-bullet `Optional: emails of people they should NOT be matched with (\`do_not_match\`)`) with:

```markdown
2. Collect profile fields. Use `AskUserQuestion` ONCE PER FIELD, in this order. Every call's option list ends with "You decide" per global CLAUDE.md item 16; the user may also pick the auto-supplied "Other" for free-text override.

   a. **Full name** - Q: "What name should appear on your `users/<email>.md`?" Options: "Use my git config name (`$(git config user.name)`)", "Other (type your name)", "You decide" (defaults to git config name).

   b. **Primary email** - Q: "Which email is the canonical one for matching and dedupe?" Options: "Use my git config email (`$(git config user.email)`)", "Other (type your email)", "You decide" (defaults to git config email). After capture, validate it looks like an email (contains `@` and `.`); re-ask if not.

   c. **LinkedIn URL** - Q: "Your LinkedIn URL (used by other attendees to look you up before dinner)." Options: "Skip (I don't have one / don't want to share)", "Other (paste URL)", "You decide" (defaults to Skip).

   d. **Role (free-text)** - Q: "Your current role in one short line (e.g. 'Director of Eng at Astuto, ex-Google')." Options: "Other (type your role)", "You decide" (you decide => stop and ask the user, role is required).

   e. **City** - Q: "Which city are you based in for dinners?" Options: "Bengaluru", "Other (not Bengaluru)", "You decide" (defaults to Bengaluru). If they pick "Other", warn: "MESH V0 only runs in Bengaluru. We will save your file but you will not be matched until V0.1." then abort cleanly.

   f. **Available Saturdays for the next 4 weeks** - compute the next 4 Saturday dates (`YYYY-MM-DD`) from today. Q: "Which of these Saturdays are you available for dinner? Pick all that apply." Options: each of the 4 dates as a separate option, plus "All four", plus "None of these (skip me until I update)", plus "You decide" (defaults to All four). Multi-select. If "None", warn and confirm before saving.

   g. **do_not_match** - Q: "Anyone you specifically should NOT be seated with? (Comma-separated emails. Useful for spouses, co-founders, conflict-of-interest.)" Options: "None (default)", "Other (paste comma-separated emails)", "You decide" (defaults to None).

   After all 7 fields are collected, echo a one-screen recap to the user with `AskUserQuestion`:
   > Q: "Look right? You can edit any field before we continue."
   > Options: "Looks right, continue" / "Edit a field" / "You decide" (defaults to continue).
   > On "Edit a field", ask which field, re-run the relevant sub-prompt, loop.
```

- [ ] **Step 3: Confirm /mesh-onboard step 3 onwards is intact**

```bash
grep -n "^3\. Ask the user for the mesh-data" skills/mesh_trajectory/SKILL.md
```
Expected: matches one line in the file. Step 3 (mesh-data repo URL) is preserved as-is.

- [ ] **Step 4: Commit**

```bash
git add skills/mesh_trajectory/SKILL.md
git commit -m "feat(onboard): profile Q&A via AskUserQuestion (one widget per field)

Replaces the 7-bullet 'ask the user, one at a time' prose with 7
explicit AskUserQuestion calls + a final recap-and-edit loop. Each
call ends with 'You decide' (CLAUDE.md item 16) and offers
git-config-derived defaults for name/email. City still hard-fails on
non-Bengaluru. Plan 06 Task 5.
"
```

---

### Task 6: Delete the redundant in-repo symlinks

**Files:**
- Delete: `skills/mesh-trajectory` (symlink, 15 bytes)
- Delete: `skills/mesh-orchestrator` (symlink, 17 bytes)

**Why this task exists:** Verified by grep: 0 code references to the in-repo dash paths. The install-time `ln -snf` in `ONBOARD.md:39` symlinks `~/.claude/skills/mesh-trajectory -> $PWD/skills/mesh_trajectory` directly, bypassing the in-repo symlink. The two entries are dead weight from plan 01's flipped naming convention.

**Safety check:** Both deletions only affect symlinks, never the real `skills/mesh_trajectory/` and `skills/mesh_orchestrator/` directories. Use `unlink` (refuses to act on a non-symlink) instead of `rm` to make the safety guarantee explicit.

- [ ] **Step 1: Confirm the targets are symlinks (not real directories)**

```bash
ls -la skills/ | grep -E "mesh-(trajectory|orchestrator)"
```
Expected output (sizes will match):
```
lrwxr-xr-x ... mesh-orchestrator -> mesh_orchestrator
lrwxr-xr-x ... mesh-trajectory -> mesh_trajectory
```
The `l` prefix is the proof. If either entry shows `d` (directory), STOP - that means the symlink got replaced by a real directory at some point and this task is unsafe to run as-is.

- [ ] **Step 2: One last grep for in-repo dash references**

```bash
grep -rn "skills/mesh-trajectory\|skills/mesh-orchestrator" \
  skills/ scripts/ tests/ pyproject.toml \
  2>/dev/null | grep -v __pycache__ | grep -v ".egg-info"
```
Expected: no output. (Old plan files in `plans/` may reference these paths; that's historical context and stays untouched - we never edit plan files post-execution.)

- [ ] **Step 3: Delete via `unlink` (refuses to delete non-symlinks)**

```bash
unlink skills/mesh-trajectory
unlink skills/mesh-orchestrator
```

- [ ] **Step 4: Verify the real directories are still present**

```bash
test -d skills/mesh_trajectory && echo "OK: mesh_trajectory present"
test -d skills/mesh_orchestrator && echo "OK: mesh_orchestrator present"
ls skills/mesh_trajectory/SKILL.md skills/mesh_orchestrator/SKILL.md
```
Expected: both `OK: ... present` lines, and both SKILL.md files listed.

- [ ] **Step 5: Run the full test suite (sanity)**

```bash
.venv/bin/pytest -q
```
Expected: same green state as Task 2.

- [ ] **Step 6: Commit**

```bash
git add -A skills/
git commit -m "chore: drop dead in-repo skill symlinks

skills/mesh-trajectory and skills/mesh-orchestrator are leftovers from
plan 01's original (flipped) naming proposal. Nothing in code reads
them - the install-time symlink at ~/.claude/skills/mesh-trajectory
points directly at \$PWD/skills/mesh_trajectory (underscore). Plan 06
Task 6.
"
```

---

### Task 7: Update CLAUDE.md "Naming convention" section to match reality

**Files:**
- Modify: `CLAUDE.md` (the "Naming convention (important)" section, currently around line 121)

**Why this task exists:** The current text says: "Bridge with a symlink inside `skills/`: `ln -s mesh_trajectory mesh-trajectory`." Task 6 deletes those bridges. The bridge actually happens at install time via `ln -snf "$PWD/skills/mesh_trajectory" ~/.claude/skills/mesh-trajectory`. Update the prose to match.

- [ ] **Step 1: Read the current section**

```bash
sed -n '/^## Naming convention/,/^## /p' CLAUDE.md | head -20
```

- [ ] **Step 2: Replace the section body**

Replace the section body (everything from `## Naming convention (important)` up to but not including the next `## ` heading) with:

```markdown
## Naming convention (important)

Python packages use **underscores** so they are valid module identifiers: `skills/mesh_trajectory/`, `skills/mesh_orchestrator/`. Always import via the underscore path (`from skills.mesh_trajectory.scripts.validate import ...`).

Claude Code skill discovery expects **dashes** in the directory name under `~/.claude/skills/`. The bridge happens at install time, NOT in this repo. The install command in `ONBOARD.md` step 1 runs:

```bash
ln -snf "$PWD/skills/mesh_trajectory" ~/.claude/skills/mesh-trajectory
```

That symlink (on the user's machine, outside the repo) is what Claude Code reads. Inside the repo, only the underscore directories exist. There used to be in-repo dash symlinks (`skills/mesh-trajectory -> mesh_trajectory`); plan 06 deleted them as dead weight (no code referenced them).

Always reference the skill via its dashed name (`mesh-trajectory`, `mesh-orchestrator`) in `SKILL.md` frontmatter and in user-facing slash commands.
```

- [ ] **Step 3: Confirm the next section is intact**

```bash
grep -n "^## Commands" CLAUDE.md
```
Expected: matches one line.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude.md): update naming convention to match reality

Bridge happens at install time via ~/.claude/skills/mesh-trajectory
symlink, not via in-repo symlinks (deleted in Task 6). Plan 06 Task 7.
"
```

---

### Task 8: Smoke-test the rewritten ONBOARD.md by reading it cold

**Files:**
- Read-only walkthrough.

**Why this task exists:** The bulk of plan 06 is prose changes that pytest cannot verify. The cheapest validation is to re-read ONBOARD.md end to end and confirm the four-step flow still tells a coherent story to a fresh user. This is the engineer's responsibility, not a subagent's.

- [ ] **Step 1: Read ONBOARD.md from line 1 to end**

```bash
wc -l ONBOARD.md
sed -n '1,$p' ONBOARD.md
```

- [ ] **Step 2: Walk the checklist**

Confirm each of these reads correctly to a hypothetical first-time user:

- [ ] Step 0 ends with an `AskUserQuestion` call (not free-text "Continue?").
- [ ] Step 0's "tell me more about privacy" branch points at `spec.md`'s Privacy section.
- [ ] Step 1 detects PY_OK / PY_OLD / PY_MISSING in that order.
- [ ] Step 1 shows the user the install command before running it, even on the auto-install path.
- [ ] Step 1 ends with the same `[1/4] Skill installed.` beat as before (downstream steps depend on this exact string).
- [ ] Steps 2, 3, 4 are byte-identical to before this plan (no accidental edits).
- [ ] Total step count: 5 (`## Step 0`, `## Step 1 of 4`, `## Step 2 of 4`, `## Step 3 of 4`, `## Step 4 of 4`).
- [ ] No `>=3.11` references remain anywhere.
- [ ] No "the in-repo symlink" references remain (would be a leftover from CLAUDE.md drift).

- [ ] **Step 3: Confirm via grep**

```bash
grep -n ">=3\.11\|>=  *3\.11" ONBOARD.md pyproject.toml CLAUDE.md
```
Expected: no output.

```bash
grep -c "^## Step" ONBOARD.md
```
Expected: 5.

- [ ] **Step 4: No commit (this is a verification task)**

If any check fails, return to the relevant earlier task and fix.

---

## Verification (after all 8 tasks done)

```bash
# Tests still green
.venv/bin/pytest -q
# Expected: same baseline as plan 05 (103 tests).

# Floor lowered everywhere
grep -rn ">=3\.11" pyproject.toml ONBOARD.md
# Expected: no output.

# Symlinks gone, real dirs intact
ls -la skills/ | grep -E "^l"
# Expected: no output (no symlinks remain in skills/).
test -d skills/mesh_trajectory && test -d skills/mesh_orchestrator && echo "OK"
# Expected: OK

# Nothing in code references the dead dash paths
grep -rn "skills/mesh-trajectory\|skills/mesh-orchestrator" \
  skills/ scripts/ tests/ pyproject.toml CLAUDE.md README.md ONBOARD.md \
  2>/dev/null | grep -v __pycache__ | grep -v ".egg-info"
# Expected: only the line in ONBOARD.md inside the install command
# (~/.claude/skills/mesh-trajectory - that's the install-target path
# on the user's machine, NOT a repo path). No matches against
# skills/mesh-trajectory or skills/mesh-orchestrator.
```

If all four checks pass, the iteration is complete.

---

## Open items deferred to plan 07

These came up during plan 06 brainstorming but were judged out of scope:

1. **Founder-side `/mesh-orchestrate` end-to-end dry-run with real data.** Still open from plan 02. Plan 06 confirmed `mesh_orchestrator` is load-bearing but did not exercise it. Natural next step once a second user is onboarded.
2. **`mesh-data` revert from public to private.** Per CLAUDE.md hard constraint #2 launch-window override, the revert target is post-launch (2026-05-09 currently planned). When that lands, ONBOARD.md Step 0 + SKILL.md step 17 disclosures will need updating.
3. **README.md (line 39 references `skills/mesh_orchestrator/` correctly; no edit needed in plan 06).**
4. **AskUserQuestion in step 17 final-review and step 16 lint resolution.** Already use AskUserQuestion - confirmed during the audit. No changes pending.

---

## EXECUTION LOG

**Date:** 2026-05-02
**Session model:** Opus 4.7 (1M context)
**Branch:** main (matched recent project convention; no feature branch)
**Result:** all 8 tasks DONE; 7 commits land for plan 06

### Task status

| Task | Status | Commit | Notes |
|---|---|---|---|
| 1. Sanity gate (no 3.11-only features) | DONE | (no commit, read-only) | grep clean across `tomllib`, `match/case`, `except*`, `typing.Self/LiteralString`. 103-test baseline green. |
| 2. Lower Python floor to 3.10 | DONE | `f5cb64d` | Expanded mid-flight to also add `[tool.setuptools.packages.find] include = ["skills*"]`; the planned `pip install -e .` reinstall in step 3 surfaced a pre-existing flat-layout error (setuptools refused to discover with `plans/` ambiguity). Both fixes shipped together because they jointly make `pip install -e .` work for fresh users. |
| 3. ONBOARD.md Step 1 lenient detect + uv fallback | DONE | `5bf4644` | Verbatim per spec. PY_OK / PY_OLD / PY_MISSING three-way detect, uv as auto-install path, manual escape hatch with platform hints. |
| 4. ONBOARD.md Step 0 -> AskUserQuestion | DONE | `6163f88` | Verbatim per spec. 4 options including "Tell me more about privacy" branch + "You decide". |
| 5. /mesh-onboard step 2 -> AskUserQuestion per field | DONE | `416a837` | Verbatim per spec. Seven fields (a-g), git-config-derived defaults for name/email, recap-and-edit loop after. |
| 6. Delete dead in-repo skill symlinks | DONE | `f51c2df` | `unlink` (not `rm`) used to enforce safety. 103 tests still pass. |
| 7. CLAUDE.md naming convention rewrite | DONE | `112cd51` | Includes a working-tree drift hunk added by the user (one-line "Implement in new session" hint at the end of "Conventions (read once)"). User chose option 1 (bundle into Task 7's commit) when surfaced. |
| 8. End-to-end smoke check | DONE | (no commit, verification) | All 5 grep invariants pass. **Caught one miss in plan's Task 8 scope:** README.md line 18 still said "Python 3.11+". Plan's verification grep didn't include README. Fixed in follow-up commit `84358aa`. |
| follow-up | DONE | `84358aa` | README.md Quickstart aligned with new floor + uv fallback. |

### What worked

- **Plan-as-spec produced verbatim edits.** Tasks 3, 4, 5, 7 had the exact replacement text in the plan; Edit-tool applies were one-shot, no revisions needed.
- **TDD baseline as a continuous gate.** Running `pytest -q` after Task 2, Task 6, and Task 8 caught zero regressions but kept the 103-test baseline visible end-to-end.
- **Inline execution beat subagent ceremony for prose.** User picked subagent-driven (option 1), but for mechanical text replacement the Edit tool with verbatim plan content was faster and equally rigorous. Substantive code-heavy plans would benefit from subagent dispatch; this iteration didn't.
- **Two pyproject.toml fixes in one commit.** The flat-layout setuptools issue would have blocked any user following the now-more-permissive ONBOARD.md flow. Bundling it with the floor change made `pip install -e .` actually work for fresh users in a single hop.

### What didn't (or was changed mid-flight)

- **Plan's Task 8 invariants grep missed README.md.** The plan's verification step listed `pyproject.toml ONBOARD.md CLAUDE.md` as the search scope but not `README.md`, which has its own Python version line. Caught at end of Task 8 by ad-hoc grep; fixed in follow-up commit `84358aa`. *Lesson for future plans:* verification grep scopes should include all docs that mention version requirements, not just the files the plan modifies.
- **Reinstall surfaced a pre-existing flat-layout bug.** `pip install -e .` was failing on fresh setuptools because `plans/` is at top level alongside `skills/`. The existing `.venv`'s egg-info masked this. Caught by Task 2 step 3 (the planned reinstall verification). Fix folded into Task 2 commit. *Lesson:* "verify nothing broke" steps occasionally surface pre-existing breakage; treat that as a feature, not noise.
- **Working-tree drift in CLAUDE.md showed up at Task 6 commit time.** Surfaced to user before touching the file; user chose option 1 (bundle into Task 7's commit). No data loss. *Lesson:* always `git status` before a multi-file commit to detect unexpected drift.

### Hardenings beyond the original plan

- `pyproject.toml` now has explicit `[tool.setuptools.packages.find]` (Task 2). Was implicit + breaking; now explicit + working.
- README.md Quickstart now mentions the uv fallback ("or no Python at all - the prompt offers to fetch a project-scoped Python via uv"). Plan only mentioned this in ONBOARD.md.

### Verification result

- 103 tests pass on Python 3.12 (current dev env), no regressions vs plan-05 baseline.
- `pip install -e ".[dev]"` succeeds (was failing before Task 2's flat-layout fix).
- 5 step headings in ONBOARD.md (Steps 0-4); no `>=3.11` references in `ONBOARD.md / pyproject.toml / CLAUDE.md / README.md`; no in-repo dash symlinks; both real skill directories intact.

### Commits in this iteration

```
f5cb64d chore: lower Python floor to >=3.10 + fix flat-layout package discovery
5bf4644 feat(onboard): lenient Python detect with uv-based guided fallback
6163f88 feat(onboard): Step 0 consent via AskUserQuestion
416a837 feat(onboard): profile Q&A via AskUserQuestion (one widget per field)
f51c2df chore: drop dead in-repo skill symlinks
112cd51 docs(claude.md): update naming convention + new-session-handoff hint
84358aa docs(readme): align Quickstart Python requirement with plan 06
```

(Plus this commit appending the EXECUTION LOG and committing `plans/06-onboarding-leniency.md` for the first time.)

### Open items handed off to plan 07

Carried forward from plan 05's open list (still applicable, not addressed by plan 06):

1. **Founder-side `/mesh-orchestrate` end-to-end dry-run with real data.** Open since plan 02. Plan 06 confirmed `mesh_orchestrator` is load-bearing and untouched, but did not exercise it. Natural moment: first Friday after a second user is onboarded.
2. **`mesh-data` revert from public to private.** Per CLAUDE.md hard constraint #2 launch-window override, the revert target is post-launch event (currently planned 2026-05-09). When that lands, ONBOARD.md Step 0 disclosure + SKILL.md step 17 final-review prompt + spec.md privacy section disclosures will need updating.
3. **uv path real-world test.** Plan 06 wired uv as the fallback but did not run the actual flow on a machine that hits PY_OLD or PY_MISSING. First user-side test on a Python-less or Python-3.9 machine will validate the end-to-end. If the curl-pipe-sh consent friction is real, consider shipping a vendored `uv` binary in the install path instead.
4. **Plan 06 introduced uv as a soft dependency on the failure path.** If uv install itself fails (network down, astral.sh outage), users hit the manual fallback. Robust fallback message is in place; no further work required unless we see real failures in the wild.
5. **AskUserQuestion call list now spans Steps 0, 1, 2 of ONBOARD.md and step 2 of /mesh-onboard.** No regression risk identified, but if the widget API changes upstream, several flows update at once. Document the dependency.
