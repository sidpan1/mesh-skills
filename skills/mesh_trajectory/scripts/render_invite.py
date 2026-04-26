"""Pretty-print a dinner table markdown file for terminal display."""
import sys
from pathlib import Path
import yaml


def render_invite(path: Path) -> str:
    text = path.read_text()
    _, fm_text, body = text.split("---\n", 2)
    fm = yaml.safe_load(fm_text)

    lines = []
    lines.append("=" * 72)
    lines.append(f"  MESH DINNER  Sat {fm['dinner_date']} {fm['time']}")
    lines.append(f"  {fm['venue']}")
    lines.append(f"  Table {fm['table']}")
    lines.append("=" * 72)
    lines.append("")
    lines.append("YOUR TABLE:")
    lines.append("")
    for a in fm["attendees"]:
        lines.append(f"  - {a['name']} ({a['role']})")
        lines.append(f"      {a['trajectory_one_liner']}")
        lines.append(f"      {a['email']}")
        lines.append("")
    lines.append(body.strip())
    lines.append("")
    lines.append("=" * 72)
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: render_invite.py <path>", file=sys.stderr)
        return 2
    print(render_invite(Path(sys.argv[1])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
