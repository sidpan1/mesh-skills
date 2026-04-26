You are synthesizing a 200-word professional trajectory from compressed signals about what a developer has been working on for the last 4 weeks.

You will receive:
1. A list of one-sentence session digests, ordered most-recent-first.
2. The developer's own one-sentence answer to "what's the WHY behind this period of your work?"

The digests tell you WHAT they did (already at intent level - no library names, no file paths). The why-seed tells you the underlying motivation that ties the digests together.

Produce one paragraph (180-220 words) structured as:

1. ONE sentence on the central initiative or shift the developer is in. Lead with the OUTCOME this work serves (who is it for? what changes for them?), not the stack.
2. TWO-THREE sentences on the work clusters underneath: the kinds of problems being chewed on, the texture (research / build / debug / ship / scale / advocate), and the tension between them.
3. ONE-TWO sentences on the direction of travel: what the developer is shifting toward, what's being de-emphasized, what's emerging.
4. (Optional) ONE sentence on adjacent bets - side threads that suggest where their thinking goes next.

Constraints (read carefully - these reverse iteration 1):
- The why-seed is AUTHORITATIVE. If the digests suggest one thing and the why-seed says another, trust the why-seed.
- Lead with WHO and WHY, not WHAT and HOW.
- Stack and tools may appear ONLY when they reveal taste or commitment, never as filler. Prefer "production multi-tenant agents" over "DeepAgentsJS + LangGraph". Prefer "browser-automation tooling" over "Chrome DevTools Protocol bindings".
- No proper nouns of secret projects, customers, or non-public people. Public companies and public technologies are okay only if they sharpen the trajectory.
- Use present-continuous voice: "Building X", "Shifting from A toward B", "Wrestling with Y". Avoid "is building", "has been doing".
- Maximize INTENT density, not VOCABULARY density. Every sentence should narrow the trajectory in a way that helps a stranger answer "what would they make my next week better at?"

Output the paragraph only. No preamble, no headers.

WHY-SEED (authoritative):
{{why_seed}}

SESSION DIGESTS (most recent first):
{{digests}}
