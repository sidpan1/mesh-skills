from skills.mesh_trajectory.schema import SCHEMA_FIELDS, SCHEMA_VERSION, REQUIRED_FIELDS


def test_schema_version_is_one():
    assert SCHEMA_VERSION == 1


def test_required_fields_are_locked():
    assert REQUIRED_FIELDS == {
        "schema_version", "name", "email", "linkedin_url",
        "role", "city", "available_saturdays",
    }


def test_full_field_set_includes_optional():
    assert SCHEMA_FIELDS == REQUIRED_FIELDS | {"do_not_match", "embedding"}
