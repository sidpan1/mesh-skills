"""Parse + validate the JSON Claude returns from the compose prompt."""
import json
import re

REQUIRED_TOP = {"dinner_date", "venue", "low_quorum", "tables"}
REQUIRED_TABLE = {"table", "attendees", "why_this_table"}
REQUIRED_ATTENDEE = {"email", "name", "role", "trajectory_one_liner"}
ALLOWED_TABLE_SIZES = {6, 7}  # 7 only when total available is 13/19/25


class ParseError(Exception):
    pass


def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n", "", s)
        s = re.sub(r"\n```$", "", s)
    return s


def parse_response(text: str) -> dict:
    try:
        data = json.loads(_strip_fences(text))
    except json.JSONDecodeError as e:
        raise ParseError(f"invalid JSON: {e}")

    missing = REQUIRED_TOP - set(data.keys())
    if missing:
        raise ParseError(f"missing top-level key(s): {sorted(missing)}")

    seen_emails: set[str] = set()
    for t in data["tables"]:
        if set(t.keys()) < REQUIRED_TABLE:
            raise ParseError(f"table missing keys: {sorted(REQUIRED_TABLE - set(t.keys()))}")
        n = len(t["attendees"])
        if n not in ALLOWED_TABLE_SIZES:
            raise ParseError(f"table {t['table']} has {n} attendees; must be 6 (or 7 once)")
        for a in t["attendees"]:
            if set(a.keys()) < REQUIRED_ATTENDEE:
                raise ParseError(f"attendee missing keys: {sorted(REQUIRED_ATTENDEE - set(a.keys()))}")
            if a["email"] in seen_emails:
                raise ParseError(f"duplicate attendee across tables: {a['email']}")
            seen_emails.add(a["email"])

    return data
