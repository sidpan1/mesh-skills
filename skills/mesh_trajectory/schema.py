"""Authoritative schema for MESH V0 user payload.

Two locked contracts in this module:
  1. SCHEMA_FIELDS  - the 8 frontmatter keys; never extend without updating
                      spec.md AND adding a failing test.
  2. SECTION_FIELDS - the ordered H2 headings inside the body, per schema
                      version. Versioned via SECTION_FIELDS_BY_VERSION.
                      Never extend or rename a version without updating
                      spec.md AND adding a failing test.

Any field or section not declared here is forbidden; validate.py enforces both.
"""
from datetime import date

SCHEMA_VERSION = 3

# Versions the validator accepts. v1, v2, v3 each gated against its own
# migration cutoff in validate.py V3.
ACCEPTED_SCHEMA_VERSIONS = frozenset({1, 2, 3})
MIGRATION_CUTOFF_DATE_V2 = date(2026, 6, 1)   # v1 -> v2 (set by plan 05)
MIGRATION_CUTOFF_DATE_V3 = date(2026, 7, 1)   # v2 -> v3 (set by plan 09)

# Backward-compat alias for code written against plan 05's single cutoff.
MIGRATION_CUTOFF_DATE = MIGRATION_CUTOFF_DATE_V2

REQUIRED_FIELDS = frozenset({
    "schema_version",
    "name",
    "email",
    "linkedin_url",
    "role",
    "city",
    "available_saturdays",
})

OPTIONAL_FIELDS = frozenset({
    "do_not_match",
    "embedding",
})

SCHEMA_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS

# Body shape per schema version. Order matters: validate.py V4 enforces this
# exact sequence per version.
SECTION_FIELDS_BY_VERSION = {
    2: (
        "Work context",
        "Top of mind",
        "Recent months",
        "Long-term background",
    ),
    3: (
        "Summary",
        "Work context",
        "Top of mind",
        "Recent months",
        "Long-term background",
    ),
}

SECTION_WORD_CAPS_BY_VERSION = {
    2: {
        "Work context":         50,
        "Top of mind":          75,
        "Recent months":        100,
        "Long-term background": 75,
    },
    3: {
        "Summary":              50,
        "Work context":         50,
        "Top of mind":          75,
        "Recent months":        100,
        "Long-term background": 75,
    },
}

TOTAL_BODY_WORD_CAP_BY_VERSION = {
    2: 250,
    3: 350,
}

# Intermediate L3-scratch caps (NOT validator-enforced; consumed by L3 prompts).
# Doubled from v2 caps so L3 has headroom and L4 (coherence) has rich source
# material to compress + rephrase from.
INTERMEDIATE_SECTION_WORD_CAPS = {
    "Work context":         100,
    "Top of mind":          150,
    "Recent months":        200,
    "Long-term background": 150,
}
TOTAL_INTERMEDIATE_WORD_CAP = sum(INTERMEDIATE_SECTION_WORD_CAPS.values())

# Backward-compat aliases. Code written against plan 05's flat constants
# (e.g. orchestrator load_users.py) reads these and gets v3 by default.
SECTION_FIELDS = SECTION_FIELDS_BY_VERSION[SCHEMA_VERSION]
SECTION_WORD_CAPS = SECTION_WORD_CAPS_BY_VERSION[SCHEMA_VERSION]
TOTAL_BODY_WORD_CAP = TOTAL_BODY_WORD_CAP_BY_VERSION[SCHEMA_VERSION]
