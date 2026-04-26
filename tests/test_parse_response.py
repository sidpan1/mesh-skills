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
