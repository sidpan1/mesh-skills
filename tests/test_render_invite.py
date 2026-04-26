from pathlib import Path
from skills.mesh_trajectory.scripts.render_invite import render_invite

SAMPLE = """---
dinner_date: "2026-05-09"
time: "19:00"
venue: "The Permit Room, Indiranagar"
table: 1
attendees:
  - email: asha@example.com
    name: Asha Rao
    role: Founding Engineer
    trajectory_one_liner: "Building agent harness unification across runtimes"
  - email: rohit@example.com
    name: Rohit K
    role: PM
    trajectory_one_liner: "Exploring agent eval from product side"
---

# Why this table

Asha and Rohit are the Guide-Explorer pair: Asha three months deep in agent
harnesses, Rohit just starting to think about evaluation as a product surface.
"""


def test_render_includes_venue_time_and_attendees(tmp_path):
    f = tmp_path / "table-1.md"
    f.write_text(SAMPLE)
    out = render_invite(f)
    assert "Permit Room" in out
    assert "Sat 2026-05-09 19:00" in out
    assert "Asha Rao" in out
    assert "Rohit K" in out
    assert "Why this table" in out
