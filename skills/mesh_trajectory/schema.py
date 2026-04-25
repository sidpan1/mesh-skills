"""Authoritative schema for MESH V0 user payload.

Any field not in SCHEMA_FIELDS is forbidden. The validator enforces this.
"""

SCHEMA_VERSION = 1

REQUIRED_FIELDS = {
    "schema_version",
    "name",
    "email",
    "linkedin_url",
    "role",
    "city",
    "available_saturdays",
}

OPTIONAL_FIELDS = {
    "do_not_match",
    "embedding",
}

SCHEMA_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS
