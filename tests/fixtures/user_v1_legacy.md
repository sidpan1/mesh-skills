---
schema_version: 1
name: Legacy User
email: legacy@example.com
linkedin_url: https://linkedin.com/in/legacyuser
role: Senior Engineer
city: Bengaluru
available_saturdays:
  - "2026-05-09"
---

This is the original single-paragraph body from a schema_version 1 user file. It contains a mix of role, recent work, and substrate that the v2 schema would have decomposed into four sections. The orchestrator's v1 adapter treats this entire paragraph as the Recent months section so the matcher can still reason about this user during the migration window. Word count here is comfortably inside the legacy 50-300 range so V3 accepts it pre-cutoff.
