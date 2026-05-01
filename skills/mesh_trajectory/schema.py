"""Authoritative schema for MESH V0 user payload.

Two locked contracts in this module:
  1. SCHEMA_FIELDS  - the 8 frontmatter keys; never extend without updating
                      spec.md AND adding a failing test.
  2. SECTION_FIELDS - the 4 ordered H2 headings inside the body; never extend
                      or rename without updating spec.md AND adding a failing test.

Any field or section not declared here is forbidden; validate.py enforces both.
"""
from datetime import date

SCHEMA_VERSION = 2

# Versions the validator accepts. v1 is accepted for the migration window
# (until MIGRATION_CUTOFF_DATE). After that date, only SCHEMA_VERSION is
# accepted. See validate.py V3.
ACCEPTED_SCHEMA_VERSIONS = frozenset({1, 2})
MIGRATION_CUTOFF_DATE = date(2026, 6, 1)

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

# Body shape: four ordered H2 sections.
# Order matters: validate.py V4 enforces this exact sequence.
SECTION_FIELDS = (
    "Work context",
    "Top of mind",
    "Recent months",
    "Long-term background",
)

SECTION_WORD_CAPS = {
    "Work context":          50,
    "Top of mind":           75,
    "Recent months":        100,
    "Long-term background":  75,
}

TOTAL_BODY_WORD_CAP = 250
