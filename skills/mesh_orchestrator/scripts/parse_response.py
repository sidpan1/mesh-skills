"""Parse + validate the JSON Claude returns from the compose prompt."""
import json
import re

REQUIRED_TOP = frozenset({"dinner_date", "venue", "low_quorum", "tables"})
REQUIRED_TABLE = frozenset({"table", "attendees", "why_this_table"})
REQUIRED_ATTENDEE = frozenset({"email", "name", "role", "trajectory_one_liner"})
ALLOWED_TABLE_SIZES = frozenset({6, 7})  # 7 only when total available is 13/19/25
LOW_QUORUM_MIN_TABLE_SIZE = 2  # at least 2 attendees needed for a table to make sense


class ParseError(Exception):
    pass


def _strip_fences(s: str) -> str:
    s = s.strip()
    if not (s.startswith("```") or s.startswith("~~~")):
        return s
    s = re.sub(r"^(?:```|~~~)[a-zA-Z]*\s*\n", "", s)
    s = re.sub(r"\n\s*(?:```|~~~)\s*$", "", s)
    return s.strip()


def parse_response(text: str) -> dict:
    try:
        data = json.loads(_strip_fences(text))
    except json.JSONDecodeError as e:
        raise ParseError(f"invalid JSON: {e}")
    if not isinstance(data, dict):
        raise ParseError(f"top-level must be JSON object, got {type(data).__name__}")

    missing = REQUIRED_TOP - set(data.keys())
    if missing:
        raise ParseError(f"missing top-level key(s): {sorted(missing)}")

    if not isinstance(data["tables"], list):
        raise ParseError(f"tables must be a list, got {type(data['tables']).__name__}")
    if not data["tables"]:
        raise ParseError("tables must contain at least one table")

    low_quorum = bool(data.get("low_quorum"))
    seen_emails: set[str] = set()
    for t in data["tables"]:
        if not isinstance(t, dict):
            raise ParseError(f"table must be an object, got {type(t).__name__}")
        if not REQUIRED_TABLE <= set(t.keys()):
            raise ParseError(f"table missing keys: {sorted(REQUIRED_TABLE - set(t.keys()))}")
        if not isinstance(t["attendees"], list):
            raise ParseError(
                f"table {t['table']} attendees must be a list, got {type(t['attendees']).__name__}"
            )
        n = len(t["attendees"])
        if low_quorum:
            if n < LOW_QUORUM_MIN_TABLE_SIZE or n > max(ALLOWED_TABLE_SIZES):
                raise ParseError(
                    f"low-quorum table {t['table']} has {n} attendees; "
                    f"must be {LOW_QUORUM_MIN_TABLE_SIZE}-{max(ALLOWED_TABLE_SIZES)}"
                )
        elif n not in ALLOWED_TABLE_SIZES:
            raise ParseError(f"table {t['table']} has {n} attendees; must be 6 (or 7 once)")
        for a in t["attendees"]:
            if not isinstance(a, dict):
                raise ParseError(f"attendee must be an object, got {type(a).__name__}")
            if not REQUIRED_ATTENDEE <= set(a.keys()):
                raise ParseError(f"attendee missing keys: {sorted(REQUIRED_ATTENDEE - set(a.keys()))}")
            if a["email"] in seen_emails:
                raise ParseError(f"duplicate attendee across tables: {a['email']}")
            seen_emails.add(a["email"])

    return data
