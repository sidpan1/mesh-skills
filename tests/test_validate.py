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
    # v1 still uses the legacy 50-300 word check during the migration window.
    with pytest.raises(ValidationError, match="body"):
        validate_payload(VALID_V1, body="too short")


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


# --- V4: exactly SECTION_FIELDS H2s, in order ---

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> tuple[dict, str]:
    return parse_markdown(FIXTURES / name)


def _v2_body(**overrides) -> str:
    """Build a v2 body from sections; override individual sections by name."""
    sections = {
        "Work context": "founding engineer at a small fintech owning agent orchestration",
        "Top of mind": "migrating an in house agent harness onto a unified runtime this quarter",
        "Recent months": "shipped a new version of the underwriting agent stack and an offline eval harness",
        "Long-term background": "several years backend systems plus prior ranking infrastructure work",
    }
    sections.update(overrides)
    parts = []
    for name in ("Work context", "Top of mind", "Recent months", "Long-term background"):
        parts.append(f"## {name}\n\n{sections[name]}")
    return "\n\n".join(parts)


def test_v2_fixture_passes_v4():
    fm, body = _fixture("user_v2_valid.md")
    validate_payload(fm, body, today=date(2026, 5, 1))


def test_missing_section_is_refused_with_section_name():
    body = _v2_body()
    body = body.replace(
        "## Top of mind\n\nmigrating an in house agent harness onto a unified runtime this quarter\n\n",
        "",
    )
    with pytest.raises(ValidationError, match="Top of mind"):
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))


def test_sections_out_of_order_are_refused():
    body = (
        "## Work context\n\nfounding engineer\n\n"
        "## Recent months\n\nshipped a new version of the underwriting agent stack\n\n"
        "## Top of mind\n\nmigrating an in house agent harness this quarter\n\n"
        "## Long-term background\n\nseveral years backend systems\n"
    )
    with pytest.raises(ValidationError, match="order"):
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))


def test_section_heading_typo_is_refused_with_rename_hint():
    body = _v2_body().replace("## Work context", "## Work Context")  # capital C
    with pytest.raises(ValidationError, match=r"rename.*Work Context.*Work context"):
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))


# --- V5: no extra H2 headings outside SECTION_FIELDS ---

def test_extra_h2_heading_in_body_is_refused():
    body = _v2_body() + "\n\n## Personal context\n\nfamily of four in indiranagar"
    with pytest.raises(ValidationError, match=r"unexpected section.*Personal context"):
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))


def test_extra_h2_at_top_of_body_is_refused():
    body = "## Bonus\n\nfree text\n\n" + _v2_body()
    with pytest.raises(ValidationError, match=r"unexpected section.*Bonus"):
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))


# --- V6: per-section word caps ---

def test_section_over_its_word_cap_is_refused_with_actual_count():
    long_section = " ".join(["word"] * 51)  # cap is 50
    body = _v2_body(**{"Work context": long_section})
    with pytest.raises(ValidationError, match=r"Work context.*51.*50"):
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))


def test_each_section_has_its_own_cap():
    long_section = " ".join(["word"] * 101)  # Recent months cap is 100
    body = _v2_body(**{"Recent months": long_section})
    with pytest.raises(ValidationError, match=r"Recent months.*101.*100"):
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))


def test_section_at_exact_cap_passes():
    exact = " ".join(["word"] * 50)
    body = _v2_body(**{"Work context": exact})
    try:
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))
    except ValidationError as e:
        assert "Work context" not in str(e), f"V6 should pass at exact cap: {e}"


# --- V7: total body cap + retire legacy single-body check for v2 ---

def test_total_body_over_cap_is_refused_even_when_each_section_under_its_cap():
    sections = {
        "Work context":          " ".join(["w"] * 50),   # 50
        "Top of mind":           " ".join(["w"] * 70),   # 70
        "Recent months":         " ".join(["w"] * 80),   # 80
        "Long-term background":  " ".join(["w"] * 51),   # 51 -> total 251
    }
    body = _v2_body(**sections)
    with pytest.raises(ValidationError, match=r"total body.*251.*250"):
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))


def test_total_body_at_exact_cap_passes():
    sections = {
        "Work context":          " ".join(["w"] * 50),
        "Top of mind":           " ".join(["w"] * 75),
        "Recent months":         " ".join(["w"] * 75),
        "Long-term background":  " ".join(["w"] * 50),
    }  # total 250
    body = _v2_body(**sections)
    try:
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))
    except ValidationError as e:
        assert "total body" not in str(e), f"V7 should pass at exact cap: {e}"


def test_v1_body_word_check_still_runs_during_migration_window():
    with pytest.raises(ValidationError, match="body must be"):
        validate_payload(VALID_V1, body="too short", today=date(2026, 5, 1))


def test_v2_body_below_50_words_is_NOT_refused_by_legacy_check():
    sections = {
        "Work context":          "one",
        "Top of mind":           "two",
        "Recent months":         "three",
        "Long-term background":  "four",
    }
    body = _v2_body(**sections)
    try:
        validate_payload(VALID_V2, body, today=date(2026, 5, 1))
    except ValidationError as e:
        assert "body must be" not in str(e), f"v2 should not hit legacy word check: {e}"
