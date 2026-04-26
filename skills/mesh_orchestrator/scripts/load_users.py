"""Load users/*.md from a mesh-data clone, filter by available_saturday + city."""
from dataclasses import dataclass
from pathlib import Path
import yaml


@dataclass
class User:
    email: str
    name: str
    linkedin_url: str
    role: str
    city: str
    available_saturdays: list[str]
    do_not_match: list[str]
    body: str


def _parse(path: Path) -> User | None:
    text = path.read_text()
    if not text.startswith("---\n"):
        return None
    _, fm_text, body = text.split("---\n", 2)
    fm = yaml.safe_load(fm_text)
    # Hand-edited files may have unquoted ISO dates that YAML loads as datetime.date
    # objects; coerce to strings so target-date comparison works.
    sats = [str(s) for s in fm["available_saturdays"]]
    return User(
        email=fm["email"],
        name=fm["name"],
        linkedin_url=fm["linkedin_url"],
        role=fm["role"],
        city=fm["city"],
        available_saturdays=sats,
        do_not_match=fm.get("do_not_match", []) or [],
        body=body.strip(),
    )


def load_users_for_date(
    mesh_data_root: Path,
    target_date: str,
    city: str = "Bengaluru",
) -> list[User]:
    users: list[User] = []
    users_dir = mesh_data_root / "users"
    if not users_dir.exists():
        return users
    for f in sorted(users_dir.glob("*.md")):
        try:
            u = _parse(f)
        except Exception:
            continue
        if u is None:
            continue
        if u.city != city:
            continue
        if target_date not in u.available_saturdays:
            continue
        users.append(u)
    return users
