from pathlib import Path
from skills.mesh_orchestrator.scripts.load_users import (
    load_users_for_date, User,
)
from skills.mesh_trajectory.schema import SECTION_FIELDS

FIXTURES = Path(__file__).parent / "fixtures"


def _write_user(dir: Path, email: str, sats: list[str], body: str = "body " * 60):
    (dir / "users").mkdir(parents=True, exist_ok=True)
    fm = (
        f"---\nschema_version: 1\nname: {email}\nemail: {email}\n"
        f"linkedin_url: https://x\nrole: Eng\ncity: Bengaluru\n"
        f"available_saturdays:\n"
    )
    for s in sats:
        fm += f"  - '{s}'\n"
    fm += "---\n\n" + body
    slug = email.lower().replace("@", "_at_").replace(".", "_")
    (dir / "users" / f"{slug}.md").write_text(fm)


def test_loads_only_users_available_on_target_date(tmp_path):
    _write_user(tmp_path, "a@x.com", ["2026-05-09"])
    _write_user(tmp_path, "b@x.com", ["2026-05-09", "2026-05-16"])
    _write_user(tmp_path, "c@x.com", ["2026-05-16"])  # not available 5/9
    users = load_users_for_date(tmp_path, "2026-05-09")
    emails = sorted(u.email for u in users)
    assert emails == ["a@x.com", "b@x.com"]


def test_user_has_body_attribute(tmp_path):
    _write_user(tmp_path, "a@x.com", ["2026-05-09"], body="trajectory text " * 20)
    users = load_users_for_date(tmp_path, "2026-05-09")
    assert "trajectory text" in users[0].body


def test_handles_unquoted_iso_dates(tmp_path):
    # YAML parses unquoted 2026-05-09 as datetime.date — must still match.
    (tmp_path / "users").mkdir(parents=True, exist_ok=True)
    (tmp_path / "users" / "z_at_y.md").write_text(
        "---\nschema_version: 1\nname: Z\nemail: z@y.com\n"
        "linkedin_url: https://x\nrole: Eng\ncity: Bengaluru\n"
        "available_saturdays:\n  - 2026-05-09\n  - 2026-05-16\n---\n\n" + ("body " * 60)
    )
    users = load_users_for_date(tmp_path, "2026-05-09")
    assert [u.email for u in users] == ["z@y.com"]


def test_skips_users_in_wrong_city(tmp_path, monkeypatch):
    # Write a Mumbai user manually (bypass our test helper which hardcodes Bengaluru)
    (tmp_path / "users").mkdir(parents=True, exist_ok=True)
    (tmp_path / "users" / "x_at_y.md").write_text(
        "---\nschema_version: 1\nname: X\nemail: x@y.com\n"
        "linkedin_url: https://x\nrole: Eng\ncity: Mumbai\n"
        "available_saturdays: ['2026-05-09']\n---\n\n" + ("body " * 60)
    )
    users = load_users_for_date(tmp_path, "2026-05-09")
    assert users == []


# --- v2 sections + v1 adapter ---

def test_v2_user_exposes_parsed_sections(tmp_path):
    (tmp_path / "users").mkdir()
    (tmp_path / "users" / "asha_at_example_com.md").write_text(
        (FIXTURES / "user_v2_valid.md").read_text()
    )
    users = load_users_for_date(tmp_path, "2026-05-09")
    assert len(users) == 1
    u = users[0]
    assert set(u.sections.keys()) == set(SECTION_FIELDS)
    assert "founding engineer" in u.sections["Work context"].lower()
    assert "agent harness" in u.sections["Top of mind"].lower()


def test_v1_user_has_only_recent_months_populated(tmp_path):
    (tmp_path / "users").mkdir()
    (tmp_path / "users" / "legacy_at_example_com.md").write_text(
        (FIXTURES / "user_v1_legacy.md").read_text()
    )
    users = load_users_for_date(tmp_path, "2026-05-09")
    assert len(users) == 1
    u = users[0]
    assert set(u.sections.keys()) == set(SECTION_FIELDS)
    assert u.sections.get("Summary", "") == ""
    assert u.sections["Work context"] == ""
    assert u.sections["Top of mind"] == ""
    assert u.sections["Long-term background"] == ""
    assert "schema_version 1" in u.sections["Recent months"].lower()
    # Legacy body field still populated for any caller that looks at it.
    assert u.body == u.sections["Recent months"]


# --- v3 + v2 adapter (plan 09 Task 8) ---

def test_v3_user_exposes_all_5_sections(tmp_path):
    (tmp_path / "users").mkdir()
    (tmp_path / "users" / "asha_at_example_com.md").write_text(
        (FIXTURES / "user_v3_valid.md").read_text()
    )
    users = load_users_for_date(tmp_path, "2026-05-09")
    assert len(users) == 1
    u = users[0]
    assert set(u.sections.keys()) == set(SECTION_FIELDS)
    assert "fintech" in u.sections["Summary"].lower()
    assert "founding engineer" in u.sections["Work context"].lower()


def test_v2_user_gets_empty_summary_in_adapter(tmp_path):
    (tmp_path / "users").mkdir()
    (tmp_path / "users" / "v2_at_example_com.md").write_text(
        (FIXTURES / "user_v2_valid.md").read_text()
    )
    users = load_users_for_date(tmp_path, "2026-05-09")
    assert len(users) == 1
    u = users[0]
    assert u.sections["Summary"] == ""
    assert "founding engineer" in u.sections["Work context"].lower()


def test_user_sections_is_ordered(tmp_path):
    (tmp_path / "users").mkdir()
    (tmp_path / "users" / "asha_at_example_com.md").write_text(
        (FIXTURES / "user_v2_valid.md").read_text()
    )
    users = load_users_for_date(tmp_path, "2026-05-09")
    assert list(users[0].sections.keys()) == list(SECTION_FIELDS)
