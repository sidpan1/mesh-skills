---
name: mesh-trajectory
description: MESH user-side skill. Single registered command /mesh-trajectory with action arg (onboard | sync | check | status). Onboards user, syncs trajectory weekly, displays dinner invites.
allowed_tools:
  - Bash
  - Read
  - Write
  - Edit
---

# mesh-trajectory

User-side skill for MESH V0. Reads local Claude Code sessions, summarizes via local Claude, and pushes a 200-word trajectory to the private `mesh-data` repo. Pulls and renders dinner invites.

## Invocation

The skill registers ONE slash command, `/mesh-trajectory`. Sub-flows are selected by the first argument:

| Invocation | Flow |
|---|---|
| `/mesh-trajectory onboard` | First-time setup: collect Q&A, install env, run first sync. |
| `/mesh-trajectory sync` | Re-extract sessions, regenerate trajectory, push update. |
| `/mesh-trajectory check` | Pull mesh-data and show pending dinner invite, if any. |
| `/mesh-trajectory status` | Show current user file + last sync time + next Saturday status. |
| `/mesh-trajectory` (no arg, or unknown arg) | Print this invocation table and exit. |

When `/mesh-trajectory` is invoked, parse the first non-empty token of the user's message after the command. Match against the actions above; on no match or no token, print the table and exit. Free-text variants ("do a sync", "run onboarding", "check my invite") map to the obvious action.

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
4. **Pre-flight access check.** Run `git ls-remote --exit-code <repo_url> HEAD`. If it fails, stop and tell the user: "Your local git can't read mesh-data. Ping the founder to get added, then run `/mesh-trajectory onboard` again. Verify your GitHub auth with `gh auth status`."
5. **Extract per-session corpora + manifest (single pass).** Run:
   ```bash
   ~/.claude/skills/mesh-skills/.venv/bin/python -m skills.mesh_trajectory.scripts.extract --to-dir /tmp/mesh_sess
   COUNT=$(jq length /tmp/mesh_sess/manifest.json)
   echo "Sessions found: $COUNT"
   ```
   This writes one file per session at `/tmp/mesh_sess/<NNN>_<uuid>.txt` plus a manifest at `/tmp/mesh_sess/manifest.json`. Each manifest entry carries `session_id`, `project_slug_raw`, `project_slug_normalized`, `last_seen`, and `corpus_path`. Default extractor caps at 200 most-recent sessions and drops sessions with <500 chars of substantive content.

   **Sparse-corpus guard:** if `COUNT` is 0, abort: tell the user "MESH reads your last 4 weeks of Claude Code session history; you have none. Use Claude Code on a real project for at least a week, then re-run." Delete `/tmp/mesh_sess` and stop. If `COUNT` is 1 to 4, use AskUserQuestion: "Only $COUNT sessions in the last 4 weeks. The trajectory will be short. Proceed, or stop and try later?" with options Proceed / Stop. If `COUNT >= 5`, continue without prompting.
6. **Per-session digests.** For each entry in `/tmp/mesh_sess/manifest.json`, read the corpus file at `entry.corpus_path`, apply `prompts/per_session.md` (substitute `{{session_corpus}}`), and produce one digest sentence. Append all digests to `/tmp/mesh_digests.txt`, ordered most-recent-first. Each line is `<session_id> <YYYY-MM-DD> <digest>`. Use parallel subagents when there are >50 sessions; instruct each subagent to read manifest entries by index range and write a batch file (e.g. `/tmp/mesh_digests_batch_NN.txt`), then concatenate them into `/tmp/mesh_digests.txt`.
7. **Privacy gate (corpora).** Delete the per-session corpus files now. The manifest stays - it carries metadata only (no corpus content).
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
9. **Per-project summaries.** For each project in `/tmp/mesh_groups.json`, append a block to `/tmp/mesh_project_summaries.txt`:
   - If `session_count == 1`: pull the matching session digest from `/tmp/mesh_digests.txt`. Wrap as `Project: <project> (1 session, ONE-OFF)\n<digest>`.
   - If `session_count >= 2`: gather the matching session digests, read `prompts/per_project.md`, substitute `{{project_name}}`, `{{session_count}}`, `{{bucket}}`, and `{{digests}}` (the matching digests joined with newlines). Generate the 80-120 word INITIATIVE-level paragraph in your response. Wrap as `Project: <project> ({n} sessions, {BUCKET})\n<paragraph>`.
   Use parallel summarizer subagents when there are 5+ multi-session projects (each subagent owns 3-6 projects, writes to `/tmp/mesh_proj_summaries/<project>.txt`); the controller then concatenates into `/tmp/mesh_project_summaries.txt`.
10. **Privacy gate (manifest + groups + digests).** Delete the manifest, groups, digests, and any per-project intermediate now:
    ```bash
    rm -rf /tmp/mesh_sess /tmp/mesh_proj_summaries
    rm -f /tmp/mesh_groups.json /tmp/mesh_digests.txt
    ```
11. **Show the user the project summaries.** Print `/tmp/mesh_project_summaries.txt`. Ask: "Do these project summaries cover what you've actually been doing? Any project you want to drop, or any summary that mis-frames what you did?" Loop until approved.
12. **Why-seed.** Default to inferring the why-seed from the project mix; print the inferred sentence and offer the user a one-line override before synthesis. Save the chosen sentence to `/tmp/mesh_why.txt`.
13. **Synthesize the four sections.** For each `<section>` in this exact order: `Work context`, `Top of mind`, `Recent months`, `Long-term background`:
    a. Read `prompts/sections/<snake_case>.md` (i.e. `work_context.md`, `top_of_mind.md`, `recent_months.md`, `long_term_background.md`).
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
    If validation raises `LintParseError`, regenerate the lint output ONCE with a stricter "valid JSON only, no code fences, no preamble" reminder. If it fails twice, abort with: "Privacy lint pipeline failed twice. Body is at /tmp/mesh_body.md. Review manually before re-running /mesh-trajectory onboard or /mesh-trajectory sync."
16. **Interactive flag resolution.** For each flag returned by the lint, use `AskUserQuestion` with three options:
    - **KEEP**: leave the span as-is (user judges it acceptable).
    - **REDACT**: delete the span from `/tmp/mesh_body.md`.
    - **REPHRASE**: ask the user for replacement text and substitute the span.
    Apply each user decision to `/tmp/mesh_body.md` immediately. After all flags are resolved, if the redactions broke sentence flow, offer to re-synthesize from the original project summaries (which means returning to step 13 - in that case re-create `/tmp/mesh_project_summaries.txt` and `/tmp/mesh_why.txt` from your conversation context, since they were deleted at step 14).
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
18. Compose the YAML frontmatter from collected answers. Write to `/tmp/mesh_fm.yaml`.
19. Persist the profile for future `/mesh-sync` runs: `mkdir -p ~/.config/mesh && cp /tmp/mesh_fm.yaml ~/.config/mesh/profile.yaml`. Body is NOT persisted (always re-derived from fresh corpus).
20. Run `cd ~/.claude/skills/mesh-skills && ~/.claude/skills/mesh-skills/.venv/bin/python -m skills.mesh_trajectory.scripts.push $REPO_URL /tmp/mesh_fm.yaml /tmp/mesh_body.md` (cd matters: the push script clones mesh-data into a relative `~/.cache/mesh-data` and the import path resolves from the skill dir).
21. Delete the temp files: `rm -f /tmp/mesh_body.md /tmp/mesh_fm.yaml`.
22. On success, print: "MESH onboarding complete. You'll get an invite via /mesh-trajectory check on Friday evening."
23. On REFUSED output: explain what was rejected and why. Verify all temp files at `/tmp/mesh_*` are gone with `ls /tmp/mesh_*` returning No such file.

## /mesh-sync flow

1. Read `~/.config/mesh/profile.yaml` (written by the `/mesh-onboard` flow step 19). If missing, tell the user to run `/mesh-trajectory onboard`.
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
  1. `/tmp/mesh_sess/<NNN>_<uuid>.txt` (raw scrubbed per-session corpora) - deleted in step 7. The manifest at `/tmp/mesh_sess/manifest.json` continues until step 10 (it carries only metadata: session id, raw and normalized slugs, timestamp, file paths - no corpus content).
  2. `/tmp/mesh_digests.txt` + `/tmp/mesh_groups.json` (compressed per-session signals + grouping metadata) + the now-empty `/tmp/mesh_sess/` directory + `/tmp/mesh_proj_summaries/` (per-project subagent outputs) - deleted in step 10.
  3. `/tmp/mesh_project_summaries.txt` + `/tmp/mesh_why.txt` (project-level intermediate) - deleted in step 14.
- A single `extract_per_session_to_disk` call in step 5 is the source of truth for the rest of the flow; step 8 reads the manifest, no second extract. This closes the race window where a privacy-sensitive session could appear in one extract pass but not the other.
- Only the validated, lint-reviewed payload reaches `mesh-data`. The schema validator REFUSES non-schema fields; the privacy lint asks the user about suspect content; never bypass either.
- The user reviews TWO checkpoints before push: project summaries (step 11) and the final lint-reviewed body (step 17).
- The skill does NOT touch GitHub credentials. It uses whatever the user's local git is already configured with (gh CLI, credential helper, SSH key, etc.). If access is missing, the skill aborts with a clear message instead of trying to authenticate.
- The body is now four ordered H2 sections (`Work context`, `Top of mind`, `Recent months`, `Long-term background`). The pre-push validator refuses any deviation from this shape (V4 missing/order, V5 extras, V6 per-section caps, V7 total cap 250 words, V8 PII stop-list). The schema version is bumped to 2; v1 files are accepted by the orchestrator until 2026-06-01 via a crude adapter (the entire v1 body is treated as the `Recent months` section).
