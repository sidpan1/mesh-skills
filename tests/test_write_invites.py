from pathlib import Path
import yaml
from skills.mesh_orchestrator.scripts.write_invites import write_invites

RESPONSE = {
    "dinner_date": "2026-05-09",
    "venue": "The Permit Room",
    "low_quorum": False,
    "tables": [{
        "table": 1,
        "attendees": [
            {"email": f"u{i}@x.com", "name": f"U{i}", "role": "Eng",
             "trajectory_one_liner": f"Building X{i}"} for i in range(6)
        ],
        "why_this_table": "good intersections",
    }],
}


def test_writes_one_file_per_table(tmp_path):
    paths = write_invites(tmp_path, RESPONSE, time="19:00")
    assert len(paths) == 1
    f = paths[0]
    assert f.parent.name == "dinner-2026-05-09"
    assert f.name == "table-1.md"
    text = f.read_text()
    assert text.startswith("---\n")
    fm = yaml.safe_load(text.split("---\n")[1])
    assert fm["dinner_date"] == "2026-05-09"
    assert fm["time"] == "19:00"
    assert fm["venue"] == "The Permit Room"
    assert len(fm["attendees"]) == 6
    assert "good intersections" in text


def test_creates_dinner_dir(tmp_path):
    write_invites(tmp_path, RESPONSE, time="19:00")
    assert (tmp_path / "networking-dinners" / "dinner-2026-05-09").is_dir()
