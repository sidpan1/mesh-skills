You are synthesizing a 200-word professional trajectory from project-level summaries of what a developer has been working on for the last 4 weeks.

You will receive:
1. A list of per-project summaries, each with a bucket label (CENTRAL / REGULAR / OCCASIONAL / ONE-OFF) and session count. Multi-session projects are 80-120-word paragraphs; one-session projects are single sentences.
2. The developer's own one-sentence answer to "what's the WHY behind this period of your work?" (or, if none provided, an inferred why-seed from the project mix).

The project summaries tell you WHAT they did, organized by initiative. The why-seed tells you the underlying motivation that ties them together. The bucket labels tell you texture - what's central vs occasional - WITHOUT giving you raw counts to weight by.

Produce one paragraph (180-220 words) structured as:

1. ONE sentence on the central initiative or shift the developer is in. Lead with the OUTCOME this work serves (who is it for? what changes for them?), not the stack.
2. TWO-THREE sentences on the work clusters: which initiatives are in tension, what kinds of problems are being chewed on, the texture (research / build / debug / ship / scale / advocate).
3. ONE-TWO sentences on the direction of travel: what the developer is shifting toward, what's being de-emphasized, what's emerging.
4. (Optional) ONE sentence on adjacent bets - side threads (often ONE-OFF or OCCASIONAL projects) that suggest where their thinking goes next.

Constraints (read carefully):
- The why-seed is AUTHORITATIVE. If the projects suggest one thing and the why-seed says another, trust the why-seed.
- Lead with WHO and WHY, not WHAT and HOW.
- Stack and tools may appear ONLY when they reveal taste or commitment, never as filler.
- No proper nouns of secret projects, customers, or non-public people. Public companies and public technologies are okay only if they sharpen the trajectory.
- Use present-continuous voice: "Building X", "Shifting from A toward B", "Wrestling with Y".
- EQUAL VOICE RULE: every project is one voice in your input regardless of session count. Do NOT use bucket labels to weight projects' importance in the output. CENTRAL bucket means "this is something the developer worked on a lot" - it is texture, not a vote multiplier. A ONE-OFF project that captures a sharp side bet may belong in the trajectory; a CENTRAL project that's pure dev-env work may not.
- Maximize INTENT density, not VOCABULARY density. Every sentence should narrow the trajectory in a way that helps a stranger answer "what would they make my next week better at?"

Output the paragraph only. No preamble, no headers.

WHY-SEED (authoritative):
{{why_seed}}

PROJECT SUMMARIES (CENTRAL first, then REGULAR, OCCASIONAL, ONE-OFF):
{{project_summaries}}
