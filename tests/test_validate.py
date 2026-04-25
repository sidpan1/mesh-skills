import pytest
from skills.mesh_trajectory.scripts.validate import (
    validate_payload, parse_markdown, ValidationError,
)

VALID = {
    "schema_version": 1,
    "name": "Asha Rao",
    "email": "asha@example.com",
    "linkedin_url": "https://linkedin.com/in/asharao",
    "role": "Founding Engineer",
    "city": "Bengaluru",
    "available_saturdays": ["2026-05-09"],
}

def test_valid_minimal_passes():
    validate_payload(VALID, body="word " * 60)

def test_valid_with_optional_fields():
    p = VALID | {"do_not_match": ["x@y.com"], "embedding": None}
    validate_payload(p, body="word " * 60)

def test_extra_field_is_refused():
    p = VALID | {"raw_conversation": "secret"}
    with pytest.raises(ValidationError, match="forbidden field"):
        validate_payload(p, body="ok body")

def test_missing_required_field_is_refused():
    p = {k: v for k, v in VALID.items() if k != "email"}
    with pytest.raises(ValidationError, match="missing required"):
        validate_payload(p, body="ok body")

def test_wrong_schema_version_is_refused():
    p = VALID | {"schema_version": 99}
    with pytest.raises(ValidationError, match="schema_version"):
        validate_payload(p, body="ok body")

def test_city_must_be_bengaluru_in_v0():
    p = VALID | {"city": "Mumbai"}
    with pytest.raises(ValidationError, match="city"):
        validate_payload(p, body="ok body")

def test_body_too_short_is_refused():
    with pytest.raises(ValidationError, match="body"):
        validate_payload(VALID, body="too short")

def test_body_too_long_is_refused():
    with pytest.raises(ValidationError, match="body"):
        validate_payload(VALID, body="word " * 500)


def test_parse_markdown_refuses_missing_opening_fence(tmp_path):
    f = tmp_path / "u.md"
    f.write_text("name: Asha\n")
    with pytest.raises(ValidationError, match="begin with"):
        parse_markdown(f)


def test_parse_markdown_refuses_missing_closing_fence(tmp_path):
    f = tmp_path / "u.md"
    f.write_text("---\nname: Asha\n")
    with pytest.raises(ValidationError, match="closing"):
        parse_markdown(f)


def test_parse_markdown_refuses_empty_frontmatter(tmp_path):
    f = tmp_path / "u.md"
    f.write_text("---\n---\n\nbody")
    with pytest.raises(ValidationError, match="mapping"):
        parse_markdown(f)
