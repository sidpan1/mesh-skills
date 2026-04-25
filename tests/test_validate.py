import pytest
from skills.mesh_trajectory.scripts.validate import validate_payload, ValidationError

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
