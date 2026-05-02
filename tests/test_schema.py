from datetime import date
from skills.mesh_trajectory.schema import (
    SCHEMA_FIELDS, SCHEMA_VERSION, REQUIRED_FIELDS,
    SECTION_FIELDS, SECTION_WORD_CAPS, TOTAL_BODY_WORD_CAP,
    SECTION_FIELDS_BY_VERSION, SECTION_WORD_CAPS_BY_VERSION,
    TOTAL_BODY_WORD_CAP_BY_VERSION,
    INTERMEDIATE_SECTION_WORD_CAPS, TOTAL_INTERMEDIATE_WORD_CAP,
    MIGRATION_CUTOFF_DATE_V2, MIGRATION_CUTOFF_DATE_V3,
    ACCEPTED_SCHEMA_VERSIONS,
)


def test_schema_version_is_three():
    assert SCHEMA_VERSION == 3


def test_required_fields_are_locked():
    assert REQUIRED_FIELDS == {
        "schema_version", "name", "email", "linkedin_url",
        "role", "city", "available_saturdays",
    }


def test_full_field_set_includes_optional():
    assert SCHEMA_FIELDS == REQUIRED_FIELDS | {"do_not_match", "embedding"}


def test_section_fields_by_version_v2():
    assert SECTION_FIELDS_BY_VERSION[2] == (
        "Work context", "Top of mind", "Recent months", "Long-term background",
    )


def test_section_fields_by_version_v3():
    assert SECTION_FIELDS_BY_VERSION[3] == (
        "Summary", "Work context", "Top of mind", "Recent months", "Long-term background",
    )


def test_section_word_caps_by_version_v2():
    assert SECTION_WORD_CAPS_BY_VERSION[2] == {
        "Work context": 50, "Top of mind": 75, "Recent months": 100, "Long-term background": 75,
    }


def test_section_word_caps_by_version_v3():
    assert SECTION_WORD_CAPS_BY_VERSION[3] == {
        "Summary": 50, "Work context": 50, "Top of mind": 75, "Recent months": 100, "Long-term background": 75,
    }


def test_total_body_word_cap_by_version():
    assert TOTAL_BODY_WORD_CAP_BY_VERSION == {2: 250, 3: 350}


def test_intermediate_caps_match_doubled_v2():
    assert INTERMEDIATE_SECTION_WORD_CAPS == {
        "Work context":         100,
        "Top of mind":          150,
        "Recent months":        200,
        "Long-term background": 150,
    }


def test_total_intermediate_word_cap():
    assert TOTAL_INTERMEDIATE_WORD_CAP == 600
    assert TOTAL_INTERMEDIATE_WORD_CAP == sum(INTERMEDIATE_SECTION_WORD_CAPS.values())


def test_section_fields_alias_points_at_v3():
    assert SECTION_FIELDS == SECTION_FIELDS_BY_VERSION[3]


def test_section_word_caps_alias_points_at_v3():
    assert SECTION_WORD_CAPS == SECTION_WORD_CAPS_BY_VERSION[3]


def test_total_body_word_cap_alias_points_at_v3():
    assert TOTAL_BODY_WORD_CAP == TOTAL_BODY_WORD_CAP_BY_VERSION[3]


def test_migration_cutoff_v2_is_2026_06_01():
    assert MIGRATION_CUTOFF_DATE_V2 == date(2026, 6, 1)


def test_migration_cutoff_v3_is_2026_07_01():
    assert MIGRATION_CUTOFF_DATE_V3 == date(2026, 7, 1)


def test_accepted_schema_versions_includes_v1_v2_v3_pre_v2_cutoff():
    assert ACCEPTED_SCHEMA_VERSIONS == frozenset({1, 2, 3})
