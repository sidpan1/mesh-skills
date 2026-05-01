# Section: Work context

You are extracting the user's CURRENT WORK CONTEXT for their MESH trajectory.

## What this section is

A factual statement of role, team, and what the user owns RIGHT NOW. Reads like the first paragraph of their LinkedIn-style positioning. No projects-in-flight (those go in "Top of mind"), no history (that goes in "Recent months" or "Long-term background"), no household/personal context (out of scope for this file).

## Output rules

- <= 50 words. Hard cap; longer output will be refused at validation.
- One short paragraph, no headings, no bullets.
- Plain text only.
- No internal codenames, partner/customer names, phone numbers, or addresses (the privacy lint and V8 stop-list will refuse these).
- If you cannot tell from the inputs what the user's current role is, say "Role and team unclear from recent sessions" and stop. Do NOT invent.

## Inputs

PROJECT SUMMARIES (one block per project the user has worked on, with bucket label CENTRAL/REGULAR/OCCASIONAL/ONE-OFF):

{{project_summaries}}

WHY SEED (one-line user-confirmed framing of why they're doing this work):

{{why_seed}}

PRIOR SECTION (the user's existing "Work context" from their last sync, or empty on first sync; for v1 migration this will be the user's full v1 body):

{{prior_section}}

## Now produce the section body

Output ONLY the section body text. No "## Work context" heading. No preamble. No code fences.
