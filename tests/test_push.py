import subprocess
from pathlib import Path
import pytest
from skills.mesh_trajectory.scripts.push import (
    write_user_file, slugify_email, PushAborted,
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
