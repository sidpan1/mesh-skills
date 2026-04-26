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
   ~/.claude/skills/mesh-skills/.venv/bin/python -c "from skills.mesh_trajectory.scripts.extract import extract_per_session; import json; from pathlib import Path; sessions = extract_per_session(Path.home() / '.claude' / 'projects', weeks=4); print(json.dumps([{'id': s.session_id, 'last_seen': s.last_seen.isoformat(), 'corpus': s.corpus} for s in sessions]))" > /tmp/mesh_sessions.json
   ```
   Tell the user how many sessions were found. Default extractor caps at 40 most-recent sessions and drops sessions with <500 chars of substantive content.
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
15. Run `cd ~/.claude/skills/mesh-skills && ~/.claude/skills/mesh-skills/.venv/bin/python -m skills.mesh_trajectory.scripts.push $REPO_URL /tmp/mesh_fm.yaml /tmp/mesh_body.md` (cd matters: the push script clones mesh-data into a relative `~/.cache/mesh-data` and the import path resolves from the skill dir).
16. Delete the temp files: `rm -f /tmp/mesh_body.md /tmp/mesh_fm.yaml`.
17. On success, print: "MESH onboarding complete. You'll get an invite via /mesh-check on Friday evening."
18. On REFUSED output: explain what was rejected and why. Verify all temp files at `/tmp/mesh_*` are gone with `ls /tmp/mesh_*` returning No such file.

## /mesh-sync flow

1. Read `~/.config/mesh/profile.yaml` (written by `/mesh-onboard` step 14). If missing, redirect to `/mesh-onboard`.
2. Re-run the access check (step 4 of `/mesh-onboard`). If it fails, abort with the same "ping the founder" message — access may have been revoked.
3. Continue from `/mesh-onboard` step 5 onwards (extract → digests → why-seed → synthesize → review → push), using the loaded profile as the answers (do not re-ask name/email/etc.). All privacy-gate deletions (steps 7, 11, 16) and the profile re-persist (step 14, in case Saturdays changed) still apply.

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

- Two intermediate artifacts ever live on disk: `/tmp/mesh_sessions.json` (raw scrubbed per-session corpora, deleted in step 7) and `/tmp/mesh_digests.txt` + `/tmp/mesh_why.txt` (compressed signals, deleted in step 11). Both deletions happen IMMEDIATELY after their respective downstream step, before any further step that could fail.
- Only the validated payload reaches `mesh-data`. The validator REFUSES any non-schema field; never bypass.
- The user reviews BOTH the digest list (step 8) AND the final trajectory body (step 12) before push. No silent regeneration.
- The skill does NOT touch GitHub credentials. It uses whatever the user's local git is already configured with (gh CLI, credential helper, SSH key, etc.). If access is missing, the skill aborts with a clear message instead of trying to authenticate.
