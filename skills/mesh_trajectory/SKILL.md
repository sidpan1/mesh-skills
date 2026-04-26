---
name: mesh-trajectory
description: MESH user-side skill. Onboards user, syncs trajectory weekly, displays dinner invites. Slash commands /mesh-onboard, /mesh-sync, /mesh-check, /mesh-status.
allowed_tools:
  - Bash
  - Read
  - Write
  - Edit
---

# mesh-trajectory

User-side skill for MESH V0. Reads local Claude Code sessions, summarizes via local Claude, and pushes a 200-word trajectory to the private `mesh-data` repo. Pulls and renders dinner invites.

## Slash commands

| Command | What it does |
|---|---|
| `/mesh-onboard` | First-time setup: collect Q&A, install env, run first sync. |
| `/mesh-sync` | Re-extract sessions, regenerate trajectory, push update. |
| `/mesh-check` | Pull mesh-data and show pending dinner invite, if any. |
| `/mesh-status` | Show current user file + last sync time + next Saturday status. |

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
4. **Pre-flight access check.** Run `git ls-remote --exit-code <repo_url> HEAD`. If it fails, stop and tell the user: "Your local git can't read mesh-data. Ping the founder to get added, then run `/mesh-onboard` again. Verify your GitHub auth with `gh auth status`."
5. **Extract per-session corpora.** Run:
   ```bash
   ~/.claude/skills/mesh-skills/.venv/bin/python -c "from skills.mesh_trajectory.scripts.extract import extract_per_session; import json; from pathlib import Path; sessions = extract_per_session(Path.home() / '.claude' / 'projects', weeks=4); print(json.dumps([{'id': s.session_id, 'project_slug': s.project_slug, 'last_seen': s.last_seen.isoformat(), 'corpus': s.corpus} for s in sessions]))" > /tmp/mesh_sessions.json
   ```
   Tell the user how many sessions were found. Default extractor caps at 200 most-recent sessions and drops sessions with <500 chars of substantive content.
6. **Per-session digests.** For each session in `/tmp/mesh_sessions.json`, read `prompts/per_session.md`, substitute `{{session_corpus}}`, and produce one digest sentence. Append all digests to `/tmp/mesh_digests.txt`, ordered most-recent-first. Each line is `<session_id> <YYYY-MM-DD> <digest>`. (You, Claude, run this loop in your response - parallel subagents are appropriate when there are >50 sessions.)
7. **Privacy gate (sessions).** Delete `/tmp/mesh_sessions.json` now. Raw corpus snippets must not linger past the digest pass.
   ```bash
   rm -f /tmp/mesh_sessions.json
   ```
8. **Group by project + classify buckets.**
   ```bash
   ~/.claude/skills/mesh-skills/.venv/bin/python -c "
   from skills.mesh_trajectory.scripts.extract import extract_per_session, group_by_project, classify_bucket
   from pathlib import Path
   import json
   sessions = extract_per_session(Path.home() / '.claude' / 'projects', weeks=4)
   groups = group_by_project(sessions)
   out = []
   for proj, sess in sorted(groups.items(), key=lambda x: -len(x[1])):
       out.append({
           'project': proj,
           'session_count': len(sess),
           'bucket': classify_bucket(len(sess)),
           'session_ids': [s.session_id for s in sess],
       })
   print(json.dumps(out, indent=2))
   " > /tmp/mesh_groups.json
   ```
   Tell the user how many logical projects emerged after slug normalization and which got which bucket label.
9. **Per-project summaries.** For each project in `/tmp/mesh_groups.json`, append a block to `/tmp/mesh_project_summaries.txt`:
   - If `session_count == 1`: pull the matching session digest from `/tmp/mesh_digests.txt`. Wrap as `Project: <project> (1 session, ONE-OFF)\n<digest>`.
   - If `session_count >= 2`: gather the matching session digests, read `prompts/per_project.md`, substitute `{{project_name}}`, `{{session_count}}`, `{{bucket}}`, and `{{digests}}` (the matching digests joined with newlines). Generate the 80-120 word INITIATIVE-level paragraph in your response. Wrap as `Project: <project> ({n} sessions, {BUCKET})\n<paragraph>`.
   (You, Claude, run this loop in your response - you ARE the LLM in the loop.)
10. **Privacy gate (groups + digests).** Delete intermediate artifacts now:
    ```bash
    rm -f /tmp/mesh_groups.json /tmp/mesh_digests.txt
    ```
11. **Show the user the project summaries.** Print `/tmp/mesh_project_summaries.txt`. Ask: "Do these project summaries cover what you've actually been doing? Any project you want to drop, or any summary that mis-frames what you did?" Loop until approved.
12. **Why-seed.** Default to inferring the why-seed from the project mix; print the inferred sentence and offer the user a one-line override before synthesis. Save the chosen sentence to `/tmp/mesh_why.txt`.
13. **Synthesize.** Read `prompts/summarize.md`, substitute `{{why_seed}}` (from `/tmp/mesh_why.txt`) and `{{project_summaries}}` (from `/tmp/mesh_project_summaries.txt`). Generate the 200-word trajectory paragraph in your response. Write it to `/tmp/mesh_body.md`.
14. **Privacy gate (intermediate).** Delete the project summaries + why-seed:
    ```bash
    rm -f /tmp/mesh_project_summaries.txt /tmp/mesh_why.txt
    ```
15. **Privacy LINT pass.** Read `prompts/lint_body.md`, substitute `{{body}}` from `/tmp/mesh_body.md`. Generate the JSON flag list in your response. Validate it:
    ```bash
    ~/.claude/skills/mesh-skills/.venv/bin/python -c "
    import json, sys
    from skills.mesh_trajectory.scripts.lint_body import parse_lint_response
    raw = sys.stdin.read()
    flags = parse_lint_response(raw)
    print(json.dumps([{'span': f.span, 'category': f.category, 'severity': f.severity, 'reason': f.reason} for f in flags]))
    " <<EOF
    <paste-the-JSON-from-your-response-here>
    EOF
    ```
    If validation raises `LintParseError`, regenerate the lint output ONCE with a stricter "valid JSON only, no code fences, no preamble" reminder. If it fails twice, abort with: "Privacy lint pipeline failed twice. Body is at /tmp/mesh_body.md. Review manually before re-running /mesh-onboard or /mesh-sync."
16. **Interactive flag resolution.** For each flag returned by the lint, use `AskUserQuestion` with three options:
    - **KEEP**: leave the span as-is (user judges it acceptable).
    - **REDACT**: delete the span from `/tmp/mesh_body.md`.
    - **REPHRASE**: ask the user for replacement text and substitute the span.
    Apply each user decision to `/tmp/mesh_body.md` immediately. After all flags are resolved, if the redactions broke sentence flow, offer to re-synthesize from the original project summaries (which means returning to step 13 - in that case re-create `/tmp/mesh_project_summaries.txt` and `/tmp/mesh_why.txt` from your conversation context, since they were deleted at step 14).
17. **User review.** Show updated `/tmp/mesh_body.md`. Ask for any final edits (open in $EDITOR or paste replacement). Loop until approved.
18. Compose the YAML frontmatter from collected answers. Write to `/tmp/mesh_fm.yaml`.
19. Persist the profile for future `/mesh-sync` runs: `mkdir -p ~/.config/mesh && cp /tmp/mesh_fm.yaml ~/.config/mesh/profile.yaml`. Body is NOT persisted (always re-derived from fresh corpus).
20. Run `cd ~/.claude/skills/mesh-skills && ~/.claude/skills/mesh-skills/.venv/bin/python -m skills.mesh_trajectory.scripts.push $REPO_URL /tmp/mesh_fm.yaml /tmp/mesh_body.md` (cd matters: the push script clones mesh-data into a relative `~/.cache/mesh-data` and the import path resolves from the skill dir).
21. Delete the temp files: `rm -f /tmp/mesh_body.md /tmp/mesh_fm.yaml`.
22. On success, print: "MESH onboarding complete. You'll get an invite via /mesh-check on Friday evening."
23. On REFUSED output: explain what was rejected and why. Verify all temp files at `/tmp/mesh_*` are gone with `ls /tmp/mesh_*` returning No such file.

## /mesh-sync flow

1. Read `~/.config/mesh/profile.yaml` (written by `/mesh-onboard` step 19). If missing, redirect to `/mesh-onboard`.
2. Re-run the access check (`/mesh-onboard` step 4). If it fails, abort with the same "ping the founder" message - access may have been revoked.
3. Continue from `/mesh-onboard` step 5 onwards (extract -> digests -> group -> per-project summaries -> why-seed -> synthesize -> lint -> interactive resolution -> review -> push), using the loaded profile as the answers (do not re-ask name/email/etc.). All three privacy-gate deletions (steps 7, 10, 14) and the profile re-persist (step 19, in case Saturdays changed) still apply.

## /mesh-check flow

1. `git -C ~/.cache/mesh-data pull --rebase`
2. Find `networking-dinners/dinner-*/table-*.md` files containing the user's email.
3. For the most recent matching file, run `~/.claude/skills/mesh-skills/.venv/bin/python -m skills.mesh_trajectory.scripts.render_invite <path>` and show the formatted output.
4. If none, print: "No invite yet. Founder runs the orchestrator on Fridays."

## /mesh-status flow

1. Show `users/<slugified-email>.md` from local mesh-data clone.
2. Show last commit timestamp on that file.
3. Show next Saturday from `available_saturdays` and whether an invite for that date exists.

## Privacy contract

- Three intermediate artifact stages ever live on disk, each gated by an immediate-delete step:
  1. `/tmp/mesh_sessions.json` (raw scrubbed per-session corpora) - deleted in step 7.
  2. `/tmp/mesh_digests.txt` + `/tmp/mesh_groups.json` (compressed per-session signals + grouping metadata) - deleted in step 10.
  3. `/tmp/mesh_project_summaries.txt` + `/tmp/mesh_why.txt` (project-level intermediate) - deleted in step 14.
- Only the validated, lint-reviewed payload reaches `mesh-data`. The schema validator REFUSES non-schema fields; the privacy lint asks the user about suspect content; never bypass either.
- The user reviews TWO checkpoints before push: project summaries (step 11) and the final lint-reviewed body (step 17).
- The skill does NOT touch GitHub credentials. It uses whatever the user's local git is already configured with (gh CLI, credential helper, SSH key, etc.). If access is missing, the skill aborts with a clear message instead of trying to authenticate.
