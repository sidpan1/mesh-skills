from datetime import date
from skills.mesh_trajectory.schema import (
    SCHEMA_FIELDS, SCHEMA_VERSION, REQUIRED_FIELDS,
    SECTION_FIELDS, SECTION_WORD_CAPS, TOTAL_BODY_WORD_CAP,
    MIGRATION_CUTOFF_DATE, ACCEPTED_SCHEMA_VERSIONS,
)


def test_schema_version_is_two():
    assert SCHEMA_VERSION == 2


def test_required_fields_are_locked():
    assert REQUIRED_FIELDS == {
        "schema_version", "name", "email", "linkedin_url",
        "role", "city", "available_saturdays",
    }


def test_full_field_set_includes_optional():
    assert SCHEMA_FIELDS == REQUIRED_FIELDS | {"do_not_match", "embedding"}


def test_section_fields_are_locked_and_ordered():
    assert SECTION_FIELDS == (
        "Work context",
        "Top of mind",
        "Recent months",
        "Long-term background",
    )


def test_section_word_caps_match_design_doc():
    assert SECTION_WORD_CAPS == {
        "Work context":          50,
        "Top of mind":           75,
        "Recent months":        100,
        "Long-term background":  75,
    }


def test_section_word_caps_cover_every_section():
    assert set(SECTION_WORD_CAPS.keys()) == set(SECTION_FIELDS)


def test_total_body_word_cap_is_250():
    assert TOTAL_BODY_WORD_CAP == 250


def test_migration_cutoff_date_is_2026_06_01():
    assert MIGRATION_CUTOFF_DATE == date(2026, 6, 1)


def test_accepted_schema_versions_during_window():
    assert ACCEPTED_SCHEMA_VERSIONS == frozenset({1, 2})
