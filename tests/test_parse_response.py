import json
import pytest
from skills.mesh_orchestrator.scripts.parse_response import (
    parse_response, ParseError,
)

VALID = {
    "dinner_date": "2026-05-09",
    "venue": "The Permit Room",
    "low_quorum": False,
    "tables": [{
        "table": 1,
        "attendees": [
            {"email": f"u{i}@x.com", "name": f"U{i}", "role": "Eng",
             "trajectory_one_liner": "Building X"} for i in range(6)
        ],
        "why_this_table": "good intersections",
    }],
}


def test_valid_response_parses():
    out = parse_response(json.dumps(VALID))
    assert out["dinner_date"] == "2026-05-09"
    assert len(out["tables"]) == 1


def test_strips_code_fences():
    wrapped = "```json\n" + json.dumps(VALID) + "\n```"
    out = parse_response(wrapped)
    assert len(out["tables"]) == 1


def test_table_with_wrong_size_raises():
    bad = json.loads(json.dumps(VALID))
    bad["tables"][0]["attendees"] = bad["tables"][0]["attendees"][:5]
    with pytest.raises(ParseError, match="6"):
        parse_response(json.dumps(bad))


def test_duplicate_attendee_across_tables_raises():
    bad = json.loads(json.dumps(VALID))
    bad["tables"].append(json.loads(json.dumps(bad["tables"][0])))
    bad["tables"][1]["table"] = 2
    with pytest.raises(ParseError, match="duplicate"):
        parse_response(json.dumps(bad))


def test_missing_required_key_raises():
    bad = {k: v for k, v in VALID.items() if k != "tables"}
    with pytest.raises(ParseError, match="tables"):
        parse_response(json.dumps(bad))


def test_invalid_json_raises():
    with pytest.raises(ParseError, match="JSON"):
        parse_response("not json")


def test_low_quorum_allows_under_six_attendees():
    low = json.loads(json.dumps(VALID))
    low["low_quorum"] = True
    low["tables"][0]["attendees"] = low["tables"][0]["attendees"][:3]
    out = parse_response(json.dumps(low))
    assert len(out["tables"][0]["attendees"]) == 3


def test_low_quorum_still_refuses_solo_table():
    low = json.loads(json.dumps(VALID))
    low["low_quorum"] = True
    low["tables"][0]["attendees"] = low["tables"][0]["attendees"][:1]
    with pytest.raises(ParseError, match="low-quorum"):
        parse_response(json.dumps(low))


def test_tables_non_list_raises():
    bad = json.loads(json.dumps(VALID))
    bad["tables"] = {"not": "a list"}
    with pytest.raises(ParseError, match="tables must be a list"):
        parse_response(json.dumps(bad))


def test_attendees_non_list_raises():
    bad = json.loads(json.dumps(VALID))
    bad["tables"][0]["attendees"] = None
    with pytest.raises(ParseError, match="attendees must be a list"):
        parse_response(json.dumps(bad))


def test_strips_unfenced_markdown_block():
    wrapped = "```\n" + json.dumps(VALID) + "\n```"
    out = parse_response(wrapped)
    assert len(out["tables"]) == 1


def test_top_level_must_be_object():
    with pytest.raises(ParseError, match="object"):
        parse_response("[1, 2, 3]")
