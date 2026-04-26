from pathlib import Path
from skills.mesh_orchestrator.scripts.load_users import (
    load_users_for_date, User,
)


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
