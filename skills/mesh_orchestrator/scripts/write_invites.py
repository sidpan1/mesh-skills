"""Write one networking-dinners/dinner-YYYY-MM-DD/table-N.md per table."""
from pathlib import Path
import yaml


def write_invites(mesh_data_root: Path, response: dict, time: str = "19:00") -> list[Path]:
    dinner_dir = mesh_data_root / "networking-dinners" / f"dinner-{response['dinner_date']}"
    dinner_dir.mkdir(parents=True, exist_ok=True)
    out: list[Path] = []
    for t in response["tables"]:
        fm = {
            "dinner_date": response["dinner_date"],
            "time": time,
            "venue": response["venue"],
            "table": t["table"],
            "attendees": t["attendees"],
        }
        body = "# Why this table\n\n" + t["why_this_table"].strip() + "\n"
        text = "---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n\n" + body
        path = dinner_dir / f"table-{t['table']}.md"
        path.write_text(text)
        out.append(path)
    return out
