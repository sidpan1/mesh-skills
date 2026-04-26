import subprocess
from pathlib import Path
import pytest
from skills.mesh_trajectory.scripts.push import (
    write_user_file, slugify_email, check_repo_access, PushAborted,
)
from skills.mesh_trajectory.scripts.validate import ValidationError


def test_slugify_email_replaces_at_and_dot():
    assert slugify_email("a.b@c.com") == "a_b_at_c_com"


def test_write_user_file_creates_valid_markdown(tmp_path):
    fm = {
        "schema_version": 1, "name": "Asha", "email": "asha@example.com",
        "linkedin_url": "https://linkedin.com/in/a", "role": "Eng",
        "city": "Bengaluru", "available_saturdays": ["2026-05-09"],
    }
    body = "A reasonable trajectory body. " * 20
    out = write_user_file(tmp_path, fm, body)
    assert out.name == "asha_at_example_com.md"
    text = out.read_text()
    assert text.startswith("---\n")
    assert "schema_version: 1" in text
    assert body.strip() in text


def test_write_user_file_aborts_on_validator_failure(tmp_path):
    fm = {"schema_version": 1, "name": "Asha"}  # missing required fields
    with pytest.raises(ValidationError):
        write_user_file(tmp_path, fm, "body " * 60)


def test_write_user_file_refuses_non_schema_field(tmp_path):
    fm = {
        "schema_version": 1, "name": "Asha", "email": "a@b.com",
        "linkedin_url": "https://x", "role": "Eng", "city": "Bengaluru",
        "available_saturdays": ["2026-05-09"],
        "raw_conversation": "leak attempt",
    }
    with pytest.raises(ValidationError, match="forbidden"):
        write_user_file(tmp_path, fm, "body " * 60)


def _bare_repo_with_one_commit(path: Path) -> str:
    """Create a bare repo with a single seed commit on main. Returns file:// URL."""
    bare = path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(bare)], check=True, capture_output=True)
    work = path / "seed"
    subprocess.run(["git", "init", "-b", "main", str(work)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(work), "config", "user.email", "t@t"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(work), "config", "user.name", "t"], check=True, capture_output=True)
    (work / "README.md").write_text("seed")
    subprocess.run(["git", "-C", str(work), "add", "README.md"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(work), "commit", "-m", "init"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(work), "push", str(bare), "main"], check=True, capture_output=True)
    return f"file://{bare}"


def test_check_repo_access_passes_for_reachable_repo(tmp_path):
    url = _bare_repo_with_one_commit(tmp_path)
    check_repo_access(url)  # should not raise


def test_check_repo_access_aborts_for_missing_repo(tmp_path):
    bogus = f"file://{tmp_path}/does-not-exist.git"
    with pytest.raises(PushAborted, match="cannot access"):
        check_repo_access(bogus)


def test_check_repo_access_message_mentions_founder(tmp_path):
    bogus = f"file://{tmp_path}/nope.git"
    with pytest.raises(PushAborted, match="founder"):
        check_repo_access(bogus)
