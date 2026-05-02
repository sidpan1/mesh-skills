"""Load users/*.md from a mesh-data clone, filter by available_saturday + city.

For schema_version 2 files, parse the body's four H2 sections and expose them
as User.sections. For schema_version 1 files (migration window only), populate
sections["Recent months"] with the entire body and leave the other three empty
so the matcher can still reason about the user. The User.body field stays
populated with the raw body string for any caller that does not yet read
sections.
"""
from dataclasses import dataclass, field
from pathlib import Path
import yaml

from skills.mesh_trajectory.scripts.validate import parse_sections
from skills.mesh_trajectory.schema import SECTION_FIELDS


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
    sections: dict[str, str] = field(default_factory=dict)


def _build_sections(schema_version: int, body: str) -> dict[str, str]:
    """Return an ordered {section_name: text} dict over SECTION_FIELDS (v3).

    For v3 files, parse all 5 sections from the body.
    For v2 files, parse the 4 v2 sections and add Summary="" so the dict
    matches the v3 SECTION_FIELDS shape that the matcher expects.
    For v1 files, dump the entire body into Recent months and leave Summary,
    Work context, Top of mind, Long-term background empty.
    """
    if schema_version == 3:
        parsed = parse_sections(body)
        return {name: parsed.get(name, "") for name in SECTION_FIELDS}
    if schema_version == 2:
        parsed = parse_sections(body)
        out: dict[str, str] = {}
        for name in SECTION_FIELDS:
            if name == "Summary":
                out[name] = ""
            else:
                out[name] = parsed.get(name, "")
        return out
    # v1 fallback: full body into Recent months.
    return {
        "Summary": "",
        "Work context": "",
        "Top of mind": "",
        "Recent months": body,
        "Long-term background": "",
    }


def _parse(path: Path) -> User | None:
    text = path.read_text()
    if not text.startswith("---\n"):
        return None
    _, fm_text, body = text.split("---\n", 2)
    fm = yaml.safe_load(fm_text)
    body = body.strip()
    sats = [str(s) for s in fm["available_saturdays"]]
    return User(
        email=fm["email"],
        name=fm["name"],
        linkedin_url=fm["linkedin_url"],
        role=fm["role"],
        city=fm["city"],
        available_saturdays=sats,
        do_not_match=fm.get("do_not_match", []) or [],
        body=body,
        sections=_build_sections(int(fm["schema_version"]), body),
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
