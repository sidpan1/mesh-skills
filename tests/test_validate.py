from datetime import date
import pytest
from skills.mesh_trajectory.scripts.validate import (
    validate_payload, parse_markdown, ValidationError,
)

VALID_V2 = {
    "schema_version": 2,
    "name": "Asha Rao",
    "email": "asha@example.com",
    "linkedin_url": "https://linkedin.com/in/asharao",
    "role": "Founding Engineer",
    "city": "Bengaluru",
    "available_saturdays": ["2026-05-09"],
}

VALID_V1 = VALID_V2 | {"schema_version": 1}

# Body that satisfies the OLD single-body 50-300 word check. Sections
# (V4-V8) are not enforced until Tasks 3-7.
LEGACY_BODY = "word " * 60


# --- V1: forbidden field rejection ---

def test_extra_field_is_refused():
    p = VALID_V2 | {"raw_conversation": "secret"}
    with pytest.raises(ValidationError, match="forbidden field"):
        validate_payload(p, body=LEGACY_BODY)


# --- V2: required field presence ---

def test_missing_required_field_is_refused():
    p = {k: v for k, v in VALID_V2.items() if k != "email"}
    with pytest.raises(ValidationError, match="missing required"):
        validate_payload(p, body=LEGACY_BODY)


# --- V3: schema_version gate with migration window ---

def test_v2_passes_during_window():
    try:
        validate_payload(VALID_V2, body=LEGACY_BODY, today=date(2026, 5, 1))
    except ValidationError as e:
        assert "schema_version" not in str(e), f"V3 should pass v2: {e}"


def test_v1_passes_during_migration_window():
    try:
        validate_payload(VALID_V1, body=LEGACY_BODY, today=date(2026, 5, 1))
    except ValidationError as e:
        assert "schema_version" not in str(e), f"V3 should accept v1 pre-cutoff: {e}"


def test_v1_refused_after_migration_cutoff():
    with pytest.raises(ValidationError, match=r"schema_version.*1.*after.*2026-06-01"):
        validate_payload(VALID_V1, body=LEGACY_BODY, today=date(2026, 6, 1))


def test_unknown_schema_version_is_refused():
    p = VALID_V2 | {"schema_version": 99}
    with pytest.raises(ValidationError, match="schema_version"):
        validate_payload(p, body=LEGACY_BODY, today=date(2026, 5, 1))


def test_v3_default_today_is_real_today():
    try:
        validate_payload(VALID_V2, body=LEGACY_BODY)
    except ValidationError as e:
        assert "schema_version" not in str(e), f"V3 default-today path: {e}"


# --- city ---

def test_city_must_be_bengaluru_in_v0():
    p = VALID_V2 | {"city": "Mumbai"}
    with pytest.raises(ValidationError, match="city"):
        validate_payload(p, body=LEGACY_BODY)


# --- legacy body word check (will be replaced by V6+V7 in Tasks 5+6) ---

def test_body_too_short_is_refused_legacy():
    with pytest.raises(ValidationError, match="body"):
        validate_payload(VALID_V2, body="too short")


# --- parse_markdown framing (unchanged from plan 04) ---

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
