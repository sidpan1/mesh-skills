---
name: mesh-orchestrator
description: MESH founder-side skill. Reads users from mesh-data, asks Claude to compose tables, writes invites. Slash command /mesh-orchestrate.
allowed_tools:
  - Bash
  - Read
  - Write
  - Edit
---

# mesh-orchestrator

Founder-side skill, run on the founder's laptop on Friday morning to compose tables for the upcoming Saturday dinner.

## Slash command

`/mesh-orchestrate <dinner_date>` (default: next Saturday)

## Flow

1. Compute `dinner_date` (default: next Saturday in YYYY-MM-DD).
2. Ask the user (founder) for the venue if not previously set this week. Save in `~/.config/mesh/orchestrator.yaml`.
3. `git -C ~/.cache/mesh-data pull --rebase` (clone first if missing: `git clone https://github.com/sidpan1/mesh-data ~/.cache/mesh-data`).
4. Load available users via (run from the skill dir so imports resolve):
   ```bash
   cd ~/.claude/skills/mesh-skills && ~/.claude/skills/mesh-skills/.venv/bin/python -c "from skills.mesh_orchestrator.scripts.load_users import load_users_for_date; import json; from pathlib import Path; print(json.dumps([u.__dict__ for u in load_users_for_date(Path('~/.cache/mesh-data').expanduser(), '<dinner_date>')]))"
   ```
   Capture the JSON list. Save it to `/tmp/mesh_users.json`.
5. If fewer than 6 users available: print the list, ask founder whether to proceed (low-quorum dinner) or cancel. If proceed, set `low_quorum: true` for the prompt.
6. Read `prompts/compose.md`. Substitute `{{dinner_date}}`, `{{venue}}`, `{{users_json}}` (from `/tmp/mesh_users.json`).
7. Generate the response (you, Claude, ARE the matching engine here). Output the strict JSON per the prompt to `/tmp/mesh_response.json`.
8. Validate the JSON (run from the skill dir):
   ```bash
   cd ~/.claude/skills/mesh-skills && ~/.claude/skills/mesh-skills/.venv/bin/python -c "from skills.mesh_orchestrator.scripts.parse_response import parse_response; import sys, json; print(json.dumps(parse_response(sys.stdin.read())))" < /tmp/mesh_response.json
   ```
   On ParseError, regenerate with the error in your context. Loop up to 3 times before falling back to manual.
9. Show the founder the parsed response. Founder approves or asks for changes (in which case re-prompt with feedback).
10. Write invites (run from the skill dir):
    ```bash
    cd ~/.claude/skills/mesh-skills && ~/.claude/skills/mesh-skills/.venv/bin/python -c "from skills.mesh_orchestrator.scripts.write_invites import write_invites; import json, pathlib; write_invites(pathlib.Path('~/.cache/mesh-data').expanduser(), json.load(open('/tmp/mesh_response.json')), time='19:00')"
    ```
11. Commit + push (uses founder's local git auth — no token injection):
    ```bash
    git -C ~/.cache/mesh-data add networking-dinners
    git -C ~/.cache/mesh-data commit -m "dinner: <dinner_date> tables composed"
    git -C ~/.cache/mesh-data push
    ```
    The founder owns mesh-data so push works with whatever GitHub auth their local git is configured with (gh CLI, credential helper, SSH).
12. Delete the temp files: `rm -f /tmp/mesh_users.json /tmp/mesh_response.json`.
13. Print: "Invites pushed. Now WhatsApp the cohort: 'invites live, run /mesh-check'."

## Failure handling

- If load_users returns empty: cancel dinner, push a `dinner-<date>/cancelled.md` with reason.
- If parse_response keeps failing after 3 attempts: print the raw Claude output, fall back to manual table composition by editing markdown directly.
- If git push fails: do not retry blindly; show founder the error, let them resolve auth/conflicts. Do NOT skip the temp-file cleanup (step 12) on failure.

## Privacy

- Never log full user bodies in the terminal beyond what the founder needs to spot-check.
- The mesh-data clone is already private; do not copy it elsewhere.
- The skill does NOT manage GitHub credentials. It assumes the founder's local git is already authorized to push to mesh-data.
- Temp files at `/tmp/mesh_users.json` and `/tmp/mesh_response.json` MUST be deleted at the end of the flow (step 12), even on partial failure.
