# Plan 04: Launch readiness - real slash command + single-extract refactor + me-private slug fix

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. **Before starting**, read `plans/03-hierarchical-summarization.md` (especially the EXECUTION LOG appendix at the bottom). The hierarchical pipeline is shipped and verified end-to-end; this plan hardens the launch surface so 30 attendees on 2026-05-01 don't stumble on the issues plan 03's verification surfaced.

## Why this iteration exists

Plan 03's end-to-end verification (commit `ebceb499` to mesh-data) shipped the founder's body successfully, but exposed three issues that bite at the launch event 2026-05-01:

1. **The four documented sub-commands are fiction.** `/mesh-onboard`, `/mesh-sync`, `/mesh-check`, `/mesh-status` are conceptual flows routed by argument, not registered slash commands. Only `/mesh-trajectory` is real. ONBOARD.md (the paste-able prompt for 30 attendees) tells users to run `/mesh-onboard`. They will get "command not found." This is the most visible launch-day failure mode.
2. **The hierarchical pipeline calls `extract_per_session()` twice** (SKILL.md step 5 for sessions, step 8 for groups). On a live corpus the two calls return slightly different session sets - in plan 03's verification, one ktichenaid session was lost and one extra software-farms-poc session appeared. Net effect was small (166/167 correctly attributed), but the same race condition could lose a session whose body fragment is privacy-sensitive: that fragment then never reaches the founder's review or the lint pass. This is a privacy-contract gap, not just a data-quality gap.
3. **Slug normalization splits `me-private-projects-hermes-admin` from `hermes-admin`.** Both reach the same logical project; today they get separate slots in the synthesis input. Cosmetic for the founder (the hermes-admin work made it through), but a 2nd user with their own private path encoding may see worse fragmentation.

Plan 03's open-items list captured all three. Plan 04 ships the fixes in a single tight iteration so the founder can dogfood the corrected flow on a friend's machine before the launch event. Items not picked up here (digest cache, `/mesh-orchestrate` end-to-end dry-run, `subagents` filter generalization) defer to plan 05.

## Architectural shift

Two contained changes on top of plan 03's pipeline.

```
   PLAN 03 (current)                              PLAN 04 (proposed)

   step 5: extract_per_session -> JSON dump       step 5: extract_per_session_to_disk
           (holds 167 corpora in one 1MB JSON)            (writes per-session .txt files +
                                                          manifest.json with project +
                                                          bucket assignments in ONE pass)
   step 6: digest pass reads JSON                 step 6: digest pass reads per-session files
   step 7: rm sessions.json                       step 7: rm per-session corpora
                                                          (manifest stays; carries metadata,
                                                          not corpus content)
   step 8: extract_per_session AGAIN ----┐        step 8: read manifest.json (already classified)
           -> groups.json                |                no second extract -> no race
                                         |
                                         v
                                  (race window: corpus
                                   changes between calls)
```

```
   /mesh-trajectory  (registered, only real cmd)  /mesh  (registered, only real cmd)
        +                                              +
   /mesh-onboard, /mesh-sync, /mesh-check,         args: onboard | sync | check | status
   /mesh-status (NOT registered, doc fiction)      controller routes by arg
```

**Key property (single extract):** the manifest written in step 5 is the source of truth for the rest of the flow. No subsequent extract call. Race window closes; UUID accountability becomes deterministic.

**Key property (slash command):** ONBOARD.md, SKILL.md, spec.md all converge on a single registered command name. Users type `/mesh sync` and the skill's flow dispatcher reads the arg.

## What stays unchanged

- 8-field schema (`schema.py` untouched)
- Validator (`validate.py` untouched)
- Push script (`push.py` untouched)
- Privacy lint (`lint_body.py`, `lint_body.md` untouched)
- Per-session digest prompt (`per_session.md`)
- Per-project digest prompt (`per_project.md`)
- Synthesis prompt (`summarize.md`)
- Founder-side orchestrator and invite renderer (untouched; plan 05 picks them up)
- The three privacy-gate stages and their delete-after-downstream-step rule
- The interactive `AskUserQuestion` lint resolution loop

## Hard constraints (carry-overs from CLAUDE.md and plans 01-03)

1. Claude is the AI layer. No external LLM API calls.
2. The 8-field schema is frozen. Don't touch `schema.py`.
3. The pre-push validator must keep refusing non-schema fields.
4. Privacy contract: per-session corpora live in `/tmp` and are deleted before the next stage.
5. Build only what's in this plan. Don't pull plan 05 ideas (digest cache, founder-side, etc.).
6. No em-dashes anywhere (project rule).
7. TDD discipline: write failing test first, run pytest to confirm RED, implement minimally, run pytest to confirm GREEN, commit. One task = one commit (plus optional tiny fix commits if the spec misjudged the real corpus, as plan 03 did).

## Tech notes

- **Manifest shape.** `manifest.json` is an ordered list:
  ```json
  [
    {
      "session_id": "<uuid>",
      "project_slug_raw": "<dir-name-from-disk>",
      "project_slug_normalized": "<after-normalize_slug>",
      "last_seen": "<iso-ts>",
      "corpus_path": "/tmp/mesh_sess/<NNN>_<uuid>.txt"
    },
    ...
  ]
  ```
  Project + bucket grouping is computed on demand from the manifest (one `group_by_project` call inside the SKILL.md flow), not stored in the manifest itself. The manifest captures only what changes if the corpus changes; bucket thresholds live in code and may change in plan 05.
- **Per-session file format.** Same as plan 03's verification used (header lines + `---CORPUS-BEGIN---`/`---CORPUS-END---` delimiters). The injection-guard delimiters in `per_session.md` already match.
- **Slug normalization for me-private.** The `-me-private-projects-` prefix appears after the user-home strip. Algorithm: after stripping `Users-<name>-(workspaces-root-workspace-|projects-)`, also strip a leading `me-private-projects-` if present. The resulting leaf project name then runs through the existing `--`-collapse and leaf-extraction steps. Real corpus lock-in: `me-private-projects-hermes-admin` collapses to `hermes-admin`.
- **Slash-command rename.** Symlink at `~/.claude/skills/mesh-trajectory` becomes `~/.claude/skills/mesh`. SKILL.md frontmatter `name: mesh-trajectory` becomes `name: mesh`. The Python package stays `skills.mesh_trajectory` (per CLAUDE.md naming convention: underscore for python, dashed for Claude Code skill discovery). ONBOARD.md install instructions update accordingly.
- **Live reload caveat.** Per Claude Code skill docs, skill changes under `~/.claude/skills/` reload within the current session - but plan 03's verification observed a stale slash-command body in one case. Plan 04 includes a smoke step where the founder runs `/mesh sync` after the SKILL.md change in a fresh session to confirm the cache is honored. If the cache is sticky, document the session-restart requirement and move on (not a blocker).

---

## File structure (delta only)

```
mesh/
├── skills/
│   └── mesh_trajectory/
│       ├── SKILL.md                           ← MODIFY: name -> mesh, single-extract step ordering
│       └── scripts/
│           └── extract.py                     ← MODIFY: add extract_per_session_to_disk(),
│                                                       add normalize_slug me-private handling
├── tests/
│   └── test_extract.py                        ← MODIFY: add tests for to_disk + me-private slug
├── ONBOARD.md                                 ← MODIFY: symlink name + invocation strings
├── spec.md                                    ← MODIFY: any /mesh-trajectory references -> /mesh
└── plans/04-launch-readiness.md               ← THIS FILE
```

The on-disk symlink at `~/.claude/skills/mesh-trajectory` is a one-time rename, not tracked in repo.

---

# Tasks

## Task 1: `extract_per_session_to_disk()` + per-session file writing

**Files:**
- Modify: `skills/mesh_trajectory/scripts/extract.py`
- Modify: `tests/test_extract.py`

Add a new function that wraps `extract_per_session()`, writes per-session text files + a manifest, and returns the manifest path. Existing `extract_per_session` stays untouched (other callers still depend on it).

- [ ] **Step 1: Write failing tests** in `tests/test_extract.py`. At minimum:

```python
def test_extract_per_session_to_disk_writes_files_and_manifest(tmp_path):
    # Create a synthetic projects-root layout
    proj_root = tmp_path / "projects"
    _make_jsonl(proj_root / "proj-a" / "uuid-aaa.jsonl", [
        _msg("user", "x" * 600, "2026-04-22T10:00:00Z"),
    ])
    _make_jsonl(proj_root / "proj-b" / "uuid-bbb.jsonl", [
        _msg("user", "y" * 600, "2026-04-23T10:00:00Z"),
    ])
    out_dir = tmp_path / "out"
    manifest_path = extract_per_session_to_disk(
        out_dir=out_dir,
        projects_root=proj_root,
        weeks=4,
        now="2026-04-25T00:00:00Z",
        min_corpus_chars=0,
    )
    # Manifest at the expected path
    assert manifest_path == out_dir / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())
    # Two sessions, ordered most-recent-first
    assert len(manifest) == 2
    assert manifest[0]["session_id"] == "uuid-bbb"
    assert manifest[1]["session_id"] == "uuid-aaa"
    # Each manifest entry has the expected fields
    for entry in manifest:
        assert "session_id" in entry
        assert "project_slug_raw" in entry
        assert "project_slug_normalized" in entry
        assert "last_seen" in entry
        assert "corpus_path" in entry
        assert Path(entry["corpus_path"]).exists()
        # Corpus file contains scrubbed content with delimiters
        body = Path(entry["corpus_path"]).read_text()
        assert "---CORPUS-BEGIN---" in body
        assert "---CORPUS-END---" in body
        assert f"SESSION_ID: {entry['session_id']}" in body


def test_extract_per_session_to_disk_normalizes_slug_in_manifest(tmp_path):
    proj_root = tmp_path / "projects"
    _make_jsonl(proj_root / "-Users-x-workspaces-root-workspace-mesh" / "uuid-aaa.jsonl", [
        _msg("user", "x" * 600, "2026-04-22T10:00:00Z"),
    ])
    out_dir = tmp_path / "out"
    extract_per_session_to_disk(
        out_dir=out_dir, projects_root=proj_root, weeks=4,
        now="2026-04-25T00:00:00Z", min_corpus_chars=0,
    )
    manifest = json.loads((out_dir / "manifest.json").read_text())
    assert manifest[0]["project_slug_raw"] == "-Users-x-workspaces-root-workspace-mesh"
    assert manifest[0]["project_slug_normalized"] == "mesh"


def test_extract_per_session_to_disk_creates_out_dir(tmp_path):
    proj_root = tmp_path / "projects"
    _make_jsonl(proj_root / "p" / "u.jsonl", [
        _msg("user", "x" * 600, "2026-04-22T10:00:00Z"),
    ])
    out_dir = tmp_path / "out" / "nested"  # parent does not exist
    extract_per_session_to_disk(
        out_dir=out_dir, projects_root=proj_root, weeks=4,
        now="2026-04-25T00:00:00Z", min_corpus_chars=0,
    )
    assert out_dir.exists()
    assert (out_dir / "manifest.json").exists()
```

- [ ] **Step 2: Run tests, confirm RED.**

- [ ] **Step 3: Implement** `extract_per_session_to_disk` in `extract.py`:

```python
def extract_per_session_to_disk(
    out_dir: Path,
    projects_root: Path = DEFAULT_PROJECTS_ROOT,
    weeks: int = DEFAULT_WEEKS,
    now: str | None = None,
    max_chars_per_session: int = 8_000,
    min_corpus_chars: int = 500,
    max_sessions: int = 200,
    exclude_projects: frozenset[str] | set[str] | None = None,
) -> Path:
    """Extract sessions, write per-session corpus files + manifest. Return manifest path.
    Each corpus file: <out_dir>/<NNN>_<uuid>.txt with header + delimited corpus.
    Manifest: <out_dir>/manifest.json - ordered list of session metadata.
    """
    sessions = extract_per_session(
        projects_root=projects_root, weeks=weeks, now=now,
        max_chars_per_session=max_chars_per_session,
        min_corpus_chars=min_corpus_chars,
        max_sessions=max_sessions,
        exclude_projects=exclude_projects,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for i, s in enumerate(sessions):
        corpus_path = out_dir / f"{i:03d}_{s.session_id}.txt"
        corpus_path.write_text(
            f"SESSION_ID: {s.session_id}\n"
            f"PROJECT_SLUG: {s.project_slug}\n"
            f"LAST_SEEN: {s.last_seen.isoformat()}\n"
            f"---CORPUS-BEGIN---\n{s.corpus}\n---CORPUS-END---\n"
        )
        manifest.append({
            "session_id": s.session_id,
            "project_slug_raw": s.project_slug,
            "project_slug_normalized": normalize_slug(s.project_slug),
            "last_seen": s.last_seen.isoformat(),
            "corpus_path": str(corpus_path),
        })
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest_path
```

- [ ] **Step 4: Add `__main__` flag** so the SKILL.md flow can call it as a one-liner. Replace the current `main()` body or add a sibling:

```python
def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--to-dir", type=Path, default=None,
                        help="If set, write per-session files + manifest here and exit.")
    args = parser.parse_args()
    if args.to_dir is not None:
        manifest_path = extract_per_session_to_disk(out_dir=args.to_dir)
        print(manifest_path)
        return 0
    print(extract_corpus())
    return 0
```

- [ ] **Step 5: Run tests, confirm GREEN.** Target: 69 + 3 = 72 tests passing.

- [ ] **Step 6: Smoke test** against real corpus:

```bash
.venv/bin/python -m skills.mesh_trajectory.scripts.extract --to-dir /tmp/mesh_smoke
ls /tmp/mesh_smoke/ | head -5
~/.claude/skills/mesh-skills/.venv/bin/python -c "
import json
m = json.load(open('/tmp/mesh_smoke/manifest.json'))
print(f'{len(m)} sessions in manifest')
print(f'First entry: {m[0]}')
"
rm -rf /tmp/mesh_smoke
```

Expected: ~167 sessions, manifest entries each pointing to a real per-session file. Cleanup `/tmp/mesh_smoke` after smoke.

- [ ] **Step 7: Commit** `feat(extract): single-pass extract_per_session_to_disk with manifest`.

---

## Task 2: Slug normalization handles `me-private-projects-` prefix

**Files:**
- Modify: `skills/mesh_trajectory/scripts/extract.py`
- Modify: `tests/test_extract.py`

Real corpus produced two distinct buckets for the same logical project (`me-private-projects-hermes-admin` and `hermes-admin`). The fix: after stripping the user-home prefix, also strip `me-private-projects-` if present.

- [ ] **Step 1: Write failing tests** in `tests/test_extract.py`:

```python
def test_normalize_slug_strips_me_private_projects_prefix():
    """me-private-projects-<X> and <X> should collapse to the same logical project."""
    assert normalize_slug(
        "-Users-sidhant-panda-workspaces-root-workspace-me-private-projects-hermes-admin"
    ) == "hermes-admin"
    # Should also work with the worktree-suffix variant from plan 03
    assert normalize_slug(
        "-Users-sidhant-panda-workspaces-root-workspace-me-private-projects-hermes-admin--claude-worktrees-strange-archimedes-d871d7"
    ) == "hermes-admin"


def test_normalize_slug_me_private_does_not_eat_unrelated_projects():
    """The me-private prefix must only strip when the slug actually starts with it after user-home."""
    # A project literally named "me-private-projects-something-else" still strips to the leaf
    assert normalize_slug(
        "-Users-x-workspaces-root-workspace-me-private-projects-foo"
    ) == "foo"
    # An unrelated project stays as-is
    assert normalize_slug(
        "-Users-x-workspaces-root-workspace-mesh"
    ) == "mesh"
```

- [ ] **Step 2: Run tests, confirm RED.**

- [ ] **Step 3: Update** `normalize_slug` to add the prefix-strip step. Order: user-home -> me-private -> worktree-suffix-collapse -> leaf-extraction.

```python
# After existing user-home strip, before the existing -- collapse:
if s.startswith("me-private-projects-"):
    s = s[len("me-private-projects-"):]
```

- [ ] **Step 4: Run tests, confirm GREEN.** Target: 72 + 2 = 74 tests passing.

- [ ] **Step 5: Smoke test** against real corpus:

```bash
.venv/bin/python -c "
from skills.mesh_trajectory.scripts.extract import extract_per_session, group_by_project
from pathlib import Path
sessions = extract_per_session(Path.home() / '.claude' / 'projects', weeks=4)
groups = group_by_project(sessions)
hermes = [k for k in groups if 'hermes' in k]
print(f'hermes-related buckets: {hermes}')
# Expect: only one bucket named 'hermes-admin'
"
```

Expected: only `hermes-admin` (the `me-private-projects-` variants collapsed).

- [ ] **Step 6: Commit** `fix(extract): collapse me-private-projects-* slug variants to leaf project`.

---

## Task 3: Slash-command rename - `/mesh-trajectory` to `/mesh`

**Files:**
- Modify: `skills/mesh_trajectory/SKILL.md` (frontmatter `name`, intro, slash-command table)
- Modify: `ONBOARD.md` (install instructions + invocation strings)
- Modify: `spec.md` (anywhere it references the old command)
- Modify: `CLAUDE.md` (if it references the old command)
- The on-disk symlink `~/.claude/skills/mesh-trajectory -> ...` becomes `~/.claude/skills/mesh -> ...` (one-shot, not tracked in repo)

This is a documentation + frontmatter change. The Python package stays `skills.mesh_trajectory` per the CLAUDE.md naming convention.

- [ ] **Step 1: Update `SKILL.md` frontmatter:**

```yaml
---
name: mesh
description: MESH user-side skill. Single command /mesh with action arg (onboard | sync | check | status). Onboards user, syncs trajectory weekly, displays dinner invites.
allowed_tools:
  - Bash
  - Read
  - Write
  - Edit
---
```

- [ ] **Step 2: Update SKILL.md slash-command table:**

```markdown
## Invocation

The skill registers ONE slash command, `/mesh`. Sub-flows are selected by argument:

| Invocation | Flow |
|---|---|
| `/mesh onboard` | First-time setup: collect Q&A, run first sync. |
| `/mesh sync` | Re-extract sessions, regenerate trajectory, push update. |
| `/mesh check` | Pull mesh-data and show pending dinner invite. |
| `/mesh status` | Show current user file + last sync time + next Saturday status. |
| `/mesh` (no arg) | Print this command list and exit. |

If the user invokes `/mesh` without an arg, OR with an unrecognized arg, print the table above and exit without executing any flow.
```

(Section heading changes from "Slash commands" to "Invocation" for clarity; flow heading naming below stays "## /mesh-onboard flow" etc. for searchability against existing docs and the EXECUTION LOG references.)

- [ ] **Step 3: Update `ONBOARD.md`** install + invocation:

```markdown
## Install (one time)

```bash
git clone https://github.com/sidpan1/mesh-skills ~/.claude/skills/mesh-skills
ln -s ~/.claude/skills/mesh-skills/skills/mesh_trajectory ~/.claude/skills/mesh
cd ~/.claude/skills/mesh-skills && python3 -m venv .venv && .venv/bin/pip install -e .
```

## Run

In a fresh Claude Code session, run `/mesh onboard`. The skill will walk you through:
- Collecting your name, role, LinkedIn, available Saturdays
- Reading your last 4 weeks of Claude Code session history (locally; never leaves your device)
- Reviewing project summaries and the final 200-word trajectory before publish
- Privacy lint: confirming or redacting any sensitive spans
- Pushing to the private mesh-data repo

Subsequent weekly use: `/mesh sync` (skips the Q&A; uses your saved profile).

To check for an invite: `/mesh check`.
```

- [ ] **Step 4: `grep` for old references** and update:

```bash
grep -rn "/mesh-trajectory\|mesh-trajectory" --include="*.md" /Users/sidhant.panda/workspaces/root-workspace/mesh/
grep -rn "/mesh-onboard\|/mesh-sync\|/mesh-check\|/mesh-status" --include="*.md" /Users/sidhant.panda/workspaces/root-workspace/mesh/
```

For each match: if the file is a plan EXECUTION LOG (plans/01, plans/02, plans/03), LEAVE IT - those are append-only history. If the file is `spec.md`, `ONBOARD.md`, `SKILL.md`, `CLAUDE.md`, or `README.md`, update the reference to `/mesh <action>`.

- [ ] **Step 5: Rename the on-disk symlink** (one-shot, manual):

```bash
ls -la ~/.claude/skills/ | grep mesh
# Should show:
#   mesh-skills -> /Users/sidhant.panda/workspaces/root-workspace/mesh
#   mesh-trajectory -> ~/.claude/skills/mesh-skills/skills/mesh_trajectory
rm ~/.claude/skills/mesh-trajectory
ln -s ~/.claude/skills/mesh-skills/skills/mesh_trajectory ~/.claude/skills/mesh
ls -la ~/.claude/skills/ | grep mesh
# New state:
#   mesh -> ~/.claude/skills/mesh-skills/skills/mesh_trajectory
#   mesh-skills -> /Users/sidhant.panda/workspaces/root-workspace/mesh
```

(The `mesh-skills` symlink stays - it's the python-import-path bridge, separate from skill discovery.)

- [ ] **Step 6: Live-reload smoke test.** In the SAME session, type `/mesh` (with no arg). Confirm Claude Code recognizes it. If it does NOT (cache stuck): document a session restart requirement in SKILL.md and CLAUDE.md and move on.

- [ ] **Step 7: Commit** `feat(mesh-trajectory): rename slash command to /mesh with action-arg routing`.

---

## Task 4: SKILL.md flow update - single-extract from manifest

**Files:**
- Modify: `skills/mesh_trajectory/SKILL.md` (steps 5-10 of `/mesh-onboard` flow)

Plan 03's flow extracts twice (step 5 sessions, step 8 groups). Plan 04 collapses to one extract that emits the manifest, and step 8 reads the manifest instead of re-extracting.

- [ ] **Step 1: Update the `## /mesh-onboard flow` section.** Replace step 5 through step 10 with this revised body. Steps 1-4 (greet/Q&A/access check) and steps 11-23 (project review onward) stay unchanged.

```markdown
5. **Extract per-session corpora + manifest (single pass).** Run:
   ```bash
   ~/.claude/skills/mesh-skills/.venv/bin/python -m skills.mesh_trajectory.scripts.extract --to-dir /tmp/mesh_sess
   ```
   This writes one file per session at `/tmp/mesh_sess/<NNN>_<uuid>.txt` plus a manifest at `/tmp/mesh_sess/manifest.json`. Tell the user how many sessions were found (`jq length /tmp/mesh_sess/manifest.json`). Default extractor caps at 200 most-recent and drops sessions with <500 chars of substantive content.

6. **Per-session digests.** For each entry in `/tmp/mesh_sess/manifest.json`, read the corpus file at `entry.corpus_path`, apply `prompts/per_session.md`, and produce one digest sentence. Append all digests to `/tmp/mesh_digests.txt`, ordered most-recent-first. Each line is `<session_id> <YYYY-MM-DD> <digest>`. Use parallel subagents when there are >50 sessions; instruct them to read manifest entries by index range and write batch files (e.g. `/tmp/mesh_digests_batch_NN.txt`) which the controller concatenates into `/tmp/mesh_digests.txt`.

7. **Privacy gate (corpora).** Delete the per-session corpus files. The manifest stays - it carries metadata only (no corpus content).
   ```bash
   find /tmp/mesh_sess -name '[0-9]*_*.txt' -delete
   ls /tmp/mesh_sess/
   # Should show only manifest.json
   ```

8. **Group by project + classify buckets** (read from manifest, no re-extract):
   ```bash
   ~/.claude/skills/mesh-skills/.venv/bin/python -c "
   import json
   from collections import defaultdict
   from skills.mesh_trajectory.scripts.extract import classify_bucket
   manifest = json.load(open('/tmp/mesh_sess/manifest.json'))
   groups = defaultdict(list)
   for entry in manifest:
       groups[entry['project_slug_normalized']].append(entry['session_id'])
   out = []
   for proj, sids in sorted(groups.items(), key=lambda x: -len(x[1])):
       out.append({
           'project': proj,
           'session_count': len(sids),
           'bucket': classify_bucket(len(sids)),
           'session_ids': sids,
       })
   print(json.dumps(out, indent=2))
   " > /tmp/mesh_groups.json
   ```
   Tell the user how many logical projects emerged after slug normalization and which got which bucket label.

9. **Per-project summaries.** (Same as plan 03's step 9; no changes other than reading session_ids from `/tmp/mesh_groups.json`.) For each project:
   - If `session_count == 1`: pull the matching session digest from `/tmp/mesh_digests.txt`. Wrap as `Project: <project> (1 session, ONE-OFF)\n<digest>`.
   - If `session_count >= 2`: gather the matching session digests, read `prompts/per_project.md`, substitute `{{project_name}}`, `{{session_count}}`, `{{bucket}}`, and `{{digests}}`. Generate the 80-120 word INITIATIVE-level paragraph. Wrap as `Project: <project> ({n} sessions, {BUCKET})\n<paragraph>`.
   Use parallel summarizer subagents when there are 5+ multi-session projects (each subagent owns 3-6 projects, writes to `/tmp/mesh_proj_summaries/<project>.txt`); the controller then concatenates into `/tmp/mesh_project_summaries.txt`.

10. **Privacy gate (manifest + groups + digests).** Delete the manifest, groups, and digest intermediate now:
    ```bash
    rm -rf /tmp/mesh_sess
    rm -f /tmp/mesh_groups.json /tmp/mesh_digests.txt
    rm -rf /tmp/mesh_proj_summaries
    ```
```

Steps 11 through 23 stay as in plan 03 (project review, why-seed, synthesize, lint, interactive resolution, push, cleanup). Verify the step numbering still flows.

- [ ] **Step 2: Update the Privacy contract section.** Adjust the "three intermediate artifact stages" wording:

```markdown
## Privacy contract

- Three intermediate artifact stages ever live on disk, each gated by an immediate-delete step:
  1. `/tmp/mesh_sess/<NNN>_<uuid>.txt` (raw scrubbed per-session corpora) - deleted in step 7. The manifest at `/tmp/mesh_sess/manifest.json` continues until step 10 (it carries only metadata: session id, project slug, timestamp, file paths).
  2. `/tmp/mesh_digests.txt` + `/tmp/mesh_groups.json` (compressed per-session signals + grouping metadata) + the (now-empty-of-corpora) `/tmp/mesh_sess/` directory - deleted in step 10.
  3. `/tmp/mesh_project_summaries.txt` + `/tmp/mesh_why.txt` (project-level intermediate) - deleted in step 14.
- Only the validated, lint-reviewed payload reaches `mesh-data`. The schema validator REFUSES non-schema fields; the privacy lint asks the user about suspect content; never bypass either.
- The user reviews TWO checkpoints before push: project summaries (step 11) and the final lint-reviewed body (step 17).
- The skill does NOT touch GitHub credentials. It uses whatever the user's local git is already configured with (gh CLI, credential helper, SSH key, etc.). If access is missing, the skill aborts with a clear message instead of trying to authenticate.
```

- [ ] **Step 3: Sanity checks:**

```bash
grep -c "—" skills/mesh_trajectory/SKILL.md   # 0
grep -c "/tmp/mesh_sess/manifest.json" skills/mesh_trajectory/SKILL.md  # >= 2
grep -c "extract_per_session_to_disk\|--to-dir" skills/mesh_trajectory/SKILL.md  # >= 1
grep -c "/tmp/mesh_sessions.json" skills/mesh_trajectory/SKILL.md  # 0 (old artifact removed)
grep -c "extract_per_session AGAIN\|step 8.*extract_per_session" skills/mesh_trajectory/SKILL.md  # 0
.venv/bin/pytest -q | tail -3   # 74 passing
```

- [ ] **Step 4: Commit** `feat(mesh-trajectory): single-extract flow reads manifest instead of re-extracting`.

---

## Task 5: Manual end-to-end dogfood on a friend's machine

**Files:** none.

The single most important launch-readiness verification: someone other than the founder runs the flow end-to-end. Plan 03 verified on the founder; plan 04 verifies on a 2nd user. Discovers the install-friction failures that ONLY surface on a fresh machine.

- [ ] **Step 1: Founder coordinates with one trusted person** (a friend who already uses Claude Code daily). Ideal candidate has:
  - macOS or Linux on a real laptop (not a corporate VM)
  - At least 4 weeks of recent Claude Code session history
  - A GitHub account that the founder can add to mesh-data as a collaborator
  - 30-45 minutes available

- [ ] **Step 2: Add the friend as a mesh-data collaborator:**

```bash
gh api -X PUT repos/sidpan1/mesh-data/collaborators/<friend-github-username> -f permission=push
```

- [ ] **Step 3: Friend follows ONBOARD.md** as written. Founder watches over their shoulder (or screen-shares). Note every friction point with file:line references:
  - Install command failures (clone, symlink, venv, pip install)
  - First `/mesh onboard` invocation: does the slash command appear? Does Claude execute the flow?
  - Q&A round: any awkward phrasing?
  - Extraction: does the friend's corpus produce a sane session count? Are there projects the friend wants to drop entirely?
  - Per-project summaries: do they read at INITIATIVE level? Any volume bias still visible?
  - Why-seed: does the inferred sentence land, or does the friend override?
  - Synthesis: does the body land coherently? Word count in 180-220?
  - Privacy lint: does it flag at least one item? Are the AskUserQuestion widgets clear? Does REPHRASE produce a coherent body?
  - Push: does it succeed? Does the friend's user file appear in mesh-data?
  - Cleanup: are all `/tmp/mesh_*` deleted?

- [ ] **Step 4: If body OR lint feels off**: STOP. Document the failure in this plan's EXECUTION LOG with the friend's permission to share details (or generic descriptions if not). Plan 05 picks up the fix.

- [ ] **Step 5: If e2e succeeds**: append the session metrics to this plan's EXECUTION LOG (count of projects, lint flags, total wall time, friction points) and confirm to the founder that the flow is launch-ready.

---

## Open decisions for this iteration

| Decision | Default | Reconsider if |
|---|---|---|
| **Manifest format** | `corpus_path` is absolute and points into `/tmp/mesh_sess/`. | If the founder wants to run the flow with a different temp dir (e.g. `/tmp/mesh.<pid>`), the manifest's absolute paths break re-running with a different dir. Keep absolute for V0 simplicity. |
| **Slash-command rename strategy** | Hard rename (delete `~/.claude/skills/mesh-trajectory`, add `~/.claude/skills/mesh`). | If the founder has muscle memory and wants both to work for a transition window, keep both symlinks pointing to the same target with two SKILL.md frontmatter `name`s. Adds complexity; skip unless asked. |
| **Friend-machine eval scope** | Single user, full flow. | If multiple friends are willing, run 2-3 in parallel for cross-user signal. The founder coordinates schedule. |
| **What the friend sees in the project summaries** | The friend reviews their own; no founder watches the contents. | Privacy: the friend's project summaries may contain sensitive personal context (the lint hasn't run yet). Founder co-screen is friction; ideal is the friend runs solo and reports back on the experience. |
| **Lint sensitivity threshold for 2nd user** | Same as plan 03 (low/medium/high all surfaced). | If lint flags >10 items, the 4-round resolution UX feels heavy. Plan 05 candidate: collapse low-severity flags into a single "review batch" prompt. |

---

## Self-review checklist

Before claiming this iteration done:

- [ ] All tests pass (target: 74 = 69 baseline from plan 03 + 3 to-disk tests + 2 me-private slug tests).
- [ ] `extract_per_session_to_disk` writes per-session files + manifest in one call; manifest has `project_slug_normalized` populated.
- [ ] `normalize_slug("-Users-x-workspaces-root-workspace-me-private-projects-hermes-admin")` returns `hermes-admin`.
- [ ] On founder's real corpus, `me-private-projects-hermes-admin` no longer appears as a separate bucket - it merges into `hermes-admin`.
- [ ] `~/.claude/skills/mesh` exists; `~/.claude/skills/mesh-trajectory` does not.
- [ ] SKILL.md frontmatter `name: mesh`.
- [ ] ONBOARD.md install instructions reference `/mesh onboard` not `/mesh-onboard`.
- [ ] No `/tmp/mesh_sessions.json` references remain in SKILL.md or any markdown under `skills/`.
- [ ] SKILL.md flow has no second `extract_per_session` call.
- [ ] One friend's machine successfully ran `/mesh onboard` end-to-end and pushed to mesh-data, OR the failure mode is documented in this plan's EXECUTION LOG.
- [ ] Plans 01-03 commits and EXECUTION LOGs are NOT rewritten; this iteration only adds and modifies.

---

## Execution Handoff

This plan is ready to execute in a fresh Claude Code conversation.

1. Open the mesh repo. Read `CLAUDE.md` first.
2. Read this entire plan, then read `plans/03-hierarchical-summarization.md` (especially the EXECUTION LOG appendix - the leaf-project semantic correction and the slash-command-cache observation are important context).
3. Use `superpowers:subagent-driven-development` to dispatch per-task subagents OR execute inline. Tasks 1-4 are codable; Task 5 is manual (the founder + a friend).
4. After Task 5 verifies (or fails informatively), append an EXECUTION LOG to this plan covering: task status (DONE / PARTIAL / BLOCKED + commit SHAs), what worked, what didn't, hardenings beyond the original plan, mid-flight architectural changes, the friend's verification outcome, and open items handed off to plan 05.
5. Then ask the user whether to author plan 05 now (likely scope: digest cache, `/mesh-orchestrate` end-to-end dry-run, AskUserQuestion lint grouping refinements).

---

# EXECUTION LOG (2026-05-01)

Executed in a single Claude Code session via inline TDD + UX hardening. Code commits on this repo: `fd79aa0`, `dbd0394`, `2be0095`, `35b65ba`, `3553a0f`, `eea02ed`, `ef0f067`, `1f08200`, `523875f`. No new pushes to `mesh-data` in this iteration; the founder's plan 03 push at `ebceb499` remains the only user file. mesh-data was flipped to PUBLIC mid-iteration as a launch-window operational override (reverts post-launch).

## Task status

| Task | Status | Commit(s) | Notes |
|---|---|---|---|
| 1. `extract_per_session_to_disk` + manifest | DONE | `fd79aa0` | TDD: 3 RED tests, then GREEN. 69 → 72. CLI gains `--to-dir`; existing callers untouched. |
| 2. me-private slug normalization | DONE | `dbd0394` | TDD: 2 new tests + 1 updated (plan-03's worktree-suffix test now expects further collapse to `hermes-admin`). 72 → 74. Real-corpus smoke confirmed only `hermes-admin` in the hermes/me-private space (was 2 buckets in plan 03). |
| 3. `/mesh-trajectory` rename to `/mesh` | SKIPPED | — | User decision mid-session ("3 is not needed - skip it"). Slash command stays `/mesh-trajectory`. The fictional-sub-commands fix moved into Task 4 as args-routing without rename. |
| 4. SKILL.md single-extract flow + args-routing | DONE | `2be0095` | Bundled the args-routing (formerly Task 3's functional half) with the single-extract pipeline rewrite. Section headers (`## /mesh-onboard flow` etc.) preserved for searchability against plans 01-03 EXECUTION LOGs. ONBOARD.md, spec.md, CLAUDE.md user-facing references switched to `/mesh-trajectory <action>`. |
| 5. Friend-machine end-to-end dogfood | DEFERRED | — | Not exercised in this iteration. Handed to plan 05 as the highest-priority remaining verification. |

Beyond the plan-04 scope, the iteration also shipped seven UX hardenings that were not in the original task list:

| Beyond-scope work | Status | Commit | Notes |
|---|---|---|---|
| Self-contained paste-and-go ONBOARD.md | DONE | `35b65ba` | Removed founder pre-launch reminder block; idempotent install; profile-existence-aware routing. |
| Public mesh-skills repo on GitHub | DONE | (gh repo create) | `gh repo create sidpan1/mesh-skills --public --source=. --remote=origin --push`. mesh-data remained PRIVATE at this point. |
| README referenced paste prompt + privacy split | DONE | `3553a0f` | Quick-start section that fetches ONBOARD.md from `main` instead of pasting the long form. |
| Top-to-bottom UX hardening (9 fixes) | DONE | `eea02ed` | 4-step framing, Python 3.11+ assertion, sparse-corpus guard mirrored in SKILL.md, final-review elevated to load-bearing privacy gate, schema version banner, progress beats `[N/4]`, plain-English Step 0, verb consistency. Founder script `scripts/grant_mesh_data_access.sh` (handles, --file, --dry-run, idempotent). |
| Claude-driven access request via gh issue | DONE | `ef0f067` | Step 2 ACCESS_DENIED branch: detects user's GH handle, AskUserQuestion to file an `Access request: <handle>` issue on the public mesh-skills repo. Founder script gains `--pending` mode that grants the issue **author's** handle (not the title text - spoofing protection) and closes the issue. |
| Fix gh search indexing latency | DONE | `1f08200` | Found via end-to-end test: `gh issue list --search "... in:title"` returned `[]` for an issue created seconds before. Switched to list-then-jq-filter. Re-verified round-trip with a real test issue. |
| Launch-window mesh-data public + disclosures | DONE | `523875f` | User-directed override of D8/HC#2: `mesh-data` flipped PUBLIC for launch window, reverts post-launch. Step 2 access check redesigned from `git ls-remote` (read, always passes on public) to `gh api .../collaborators/$HANDLE` (write, real failure mode). Disclosures added to ONBOARD Step 0, SKILL step 17, spec D8 + Privacy, CLAUDE HC #2, README Privacy. |

## What worked

1. **TDD discipline held.** Tasks 1 and 2 each cycled RED → implement → GREEN → commit cleanly. The me-private fix even forced an honest update of plan-03's worktree-suffix test (it now expects the further collapse), which kept the test suite consistent rather than shadowing the change.
2. **Args-routing collapses the launch-blocker without ceremony.** Plan 04 originally bundled rename + routing in Task 3. Splitting them mid-session let us ship the routing (the actual launch fix) without the symlink dance and without breaking founder muscle memory.
3. **Single-extract closes the privacy-contract race.** Plan 03's smoke had lost 1/167 sessions silently across two extract calls. The new flow extracts once, writes a manifest, and step 8 reads metadata-only from it. Step 7's `find ... -delete` keeps the privacy gate timing intact (corpus deleted; manifest survives one more step).
4. **End-to-end testing caught the gh search latency bug.** Without the "test it out once" pass, the founder would have run `--pending` on launch night, seen "no pending" while real issues piled up, and panicked. Catching this with a synthetic test issue + cleanup was clean.
5. **Public-flip + access-check fix bundled.** When mesh-data went public, `git ls-remote` started passing for everyone (read access is implicit on public repos), which would have let non-collaborators sail through Step 2 and fail confusingly at push time. The fix to use the collaborator API for a true write-access check was a real bug surfaced by the visibility change, not a UX nice-to-have.
6. **Documentation honesty as a first-class deliverable.** Five files (`ONBOARD.md`, `SKILL.md`, `spec.md`, `CLAUDE.md`, `README.md`) now disclose the launch-window public state with a specific revert target. If we'd flipped silently, the onboarding prompt would tell every attendee "private repo" while pushing to a public one.

## What didn't work / had to be hardened mid-flight

1. **gh issue search has indexing latency** (caught at end-to-end test, fixed in `1f08200`). New issues are not visible to `--search "... in:title"` for up to several minutes; the same issues are immediately visible via plain `--json` list. Replaced with list-then-jq-filter. Deterministic, no wait. Worth canonicalizing for any future gh-API-driven control plane.
2. **Step 2's read-vs-write semantics changed under us when mesh-data went public.** `git ls-remote` was sufficient when both read and write tracked together (private repo, collaborator-only). Once public, read divorced from write; the original check became a silent permissive false-positive. Redesigned to `gh api .../collaborators/$HANDLE`, which checks the actual auth boundary attendees care about. Side benefit: the access-request flow remains useful even with public mesh-data (write still gated).
3. **Plan 03's `me-private-projects-hermes-admin` worktree test had to be flipped, not added to.** Task 2 expected a clean "add new tests" path; reality required updating one existing assertion that previously asserted the un-collapsed form. This meant editing test data committed in plan 03. Captured here so plan-history readers don't think a regression slipped in.
4. **Mid-iteration scope expansion.** The iteration was authored as 5 tasks; it shipped 11 commits with deep UX work past task 4. The expansion was user-driven ("solve all the concerns from the UX pov", "test it out once", "make the mesh data repo public for now") and stayed inside the launch-readiness theme, but the original plan body undercounts what landed. Future iterations should either (a) plan with a "plus UX" appendix slot, or (b) split a clear "core fixes" iteration from "UX polish + launch ops" iteration.

## Hardenings beyond the original plan

1. **`scripts/grant_mesh_data_access.sh`** with `--file`, `--dry-run`, `--pending`, idempotent, `gh`-CLI-only (no tokens in repo). `--pending` round-trip (read open issues, grant authors, comment, close) is the launch-night ergonomics win.
2. **Sparse-corpus guard** mirrored in BOTH places. ONBOARD.md Step 3 catches it before slash-command runs; SKILL.md step 5 catches it for direct `/mesh-trajectory onboard` invocations that bypass ONBOARD. Either path can stop at 0, AskUserQuestion-warn at 1-4, proceed at 5+.
3. **Final review elevated to load-bearing privacy gate.** SKILL.md step 17 is now an explicit AskUserQuestion with four options (Push as-is / Edit / Re-run lint stricter / Abort) that frames the body as world-readable. Especially important during the launch-window public state.
4. **Python 3.11+ assertion at install time.** Earlier silent-fail-at-import is now loud-fail-with-instructions: `brew install python@3.11` (mac) or `apt install python3.11` (linux). pyproject already pinned 3.11; the README now matches.

## Mid-flight architectural changes

1. **`/mesh-trajectory` stays the registered slash command.** Plan 04 originally ranked the rename to `/mesh` as a Task 3 scope item; user skipped it. The args-routing piece - the actual launch-bug fix - moved into Task 4. Net effect: section headers in SKILL.md continue to read `## /mesh-onboard flow` etc., user types `/mesh-trajectory onboard` etc.
2. **`mesh-data` temporarily PUBLIC.** D8 + the Privacy section + CLAUDE.md HC #2 all carry an explicit launch-window override with a revert target. This is the largest deviation from plan 04's "what stays unchanged" list. Documented end-to-end so the revert is a one-command + one-doc-flip-commit operation.
3. **Access check semantic switched from read to write.** Forced by (2); see "What didn't work" item 2.

## Verification result

End-to-end success against the founder's machine.

- **Tests:** 74/74 pass on every Task commit.
- **Real-corpus smoke:** 91-92 sessions across 15 logical projects (was 18 in plan 03; the corpus has shifted in 5 days, and the me-private collapse merged 2 buckets into 1). Only `hermes-admin` in the hermes/me-private space.
- **ONBOARD.md walked step-by-step:** Step 0 (URL fetchable) HTTP 200; Step 1 (Python 3.11+, idempotent install) PYTHON_OK + symlink intact; Step 2 (write access via collaborator API) ACCESS_OK for the founder, ACCESS_DENIED for `octocat` (correct); Step 3 (corpus check) 92 / 15 / proceed; Step 4 (profile detection) HAS_PROFILE → sync route.
- **Founder script:** all four modes verified (`--help`, `--dry-run` handles, `--dry-run --pending` empty, `--dry-run --pending` with real test issue). Spoofing protection verified: title `octocat`, author `sidpan1`, script attributed to `sidpan1`. Test issue cleaned up.
- **Public mesh-data live:** `curl -sI` returns HTTP 200 for the founder's user file with no auth.
- **Privacy disclosures:** all 5 docs updated to match runtime state.

The end-to-end trajectory flow itself was NOT re-run in this iteration (no new push to mesh-data) - plan 03 verified that pipeline; plan 04 hardens the surface around it. The next push will happen when the founder runs `/mesh-trajectory sync` in a fresh session.

## Open items handed off to plan 05

1. **Revert mesh-data to private after launch event** (target: 2026-05-09 post-dinner). One command + one doc-flip commit.
2. **Friend-machine end-to-end dogfood** (plan 04 Task 5, never done). Highest-priority remaining verification: a non-founder run on a fresh laptop. Discovers install-friction that only surfaces outside the founder's environment.
3. **`/mesh-orchestrate` end-to-end dry-run with real data.** Open since plan 02; never exercised. First Friday after second onboarded user is the natural moment.
4. **Per-project digest cache.** At 92 sessions × ~3 min digest pass × 30 attendees, the weekly sync cost is non-trivial. Cache `~/.config/mesh/sessions/<UUID>.summary.md` and only re-digest NEW sessions on subsequent syncs.
5. **`subagents`-filter generalization.** Plan 02 deferred; plan 03 didn't pick it up; plan 04 didn't either. Detect subagent sessions structurally (filename prefix, message-role patterns) rather than by slug name.
6. **AskUserQuestion lint-flag grouping canonicalization** in SKILL.md step 16. Plan 03's verification grouped 4 adjacent-clause flags into one round; plan 04 didn't formalize this. Step 16 still says "one round per flag".
7. **Digest UUID off-by-one reconciliation.** Plan 03 lost 1/167 silently; plan 04 didn't address. Reconcile each digest line's UUID against the manifest's session_id allowlist; flag or re-attribute strays.
8. **Slash-command session-start cache** documented and worked around via the two-session UX dance (install in current session, run /mesh-trajectory in fresh session). If Claude Code platform fixes the cache, this dance can collapse.
9. **mesh-data architectural split** (option C from the visibility decision): consider splitting `mesh-data` (private user trajectories) and `mesh-invites` (public dinner invites) for V0.1. Architecturally cleaner than a flag flip.
10. **Plan 04's mid-iteration scope expansion** suggests a structural change to the iterate workflow itself: a "plus UX appendix" slot in plan templates so launch-readiness iterations can budget for the work that always emerges between "core fixes" and "ship".

## Self-review checklist

- [x] All tests pass (target: 74). Actual: 74.
- [x] `extract_per_session_to_disk` writes per-session files + manifest in one call; manifest has `project_slug_normalized` populated.
- [x] `normalize_slug("-Users-x-workspaces-root-workspace-me-private-projects-hermes-admin")` returns `hermes-admin`.
- [x] On founder's real corpus, `me-private-projects-hermes-admin` no longer appears as a separate bucket; merged into `hermes-admin`.
- [SKIPPED by user] `~/.claude/skills/mesh` exists; `~/.claude/skills/mesh-trajectory` does not. Task 3 skipped; mesh-trajectory stays the registered name.
- [SKIPPED by user] SKILL.md frontmatter `name: mesh`. Stayed `name: mesh-trajectory`.
- [x] ONBOARD.md install instructions reference `/mesh-trajectory <action>` not `/mesh-onboard`.
- [x] No `/tmp/mesh_sessions.json` references remain in SKILL.md.
- [x] SKILL.md flow has no second `extract_per_session` call.
- [DEFERRED] One friend's machine successfully ran `/mesh onboard` end-to-end. Open in handoff item 2.
- [x] Plans 01-03 commits and EXECUTION LOGs are NOT rewritten; this iteration only adds and modifies.
