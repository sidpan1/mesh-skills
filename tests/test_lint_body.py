import json
import pytest
from skills.mesh_trajectory.scripts.lint_body import parse_lint_response, LintFlag, LintParseError


def test_parses_valid_json_array():
    raw = json.dumps([
        {"span": "promotion case", "category": "career", "severity": "high", "reason": "internal review"},
    ])
    flags = parse_lint_response(raw)
    assert len(flags) == 1
    assert flags[0].span == "promotion case"
    assert flags[0].category == "career"
    assert flags[0].severity == "high"


def test_parses_empty_array():
    assert parse_lint_response("[]") == []


def test_strips_markdown_code_fences():
    raw = "```json\n[]\n```"
    assert parse_lint_response(raw) == []


def test_rejects_non_array_root():
    with pytest.raises(LintParseError):
        parse_lint_response('{"span": "x"}')


def test_rejects_missing_required_keys():
    raw = json.dumps([{"span": "x", "category": "career"}])  # missing severity, reason
    with pytest.raises(LintParseError):
        parse_lint_response(raw)


def test_rejects_unknown_category():
    raw = json.dumps([
        {"span": "x", "category": "made-up", "severity": "high", "reason": "n/a"},
    ])
    with pytest.raises(LintParseError):
        parse_lint_response(raw)


def test_rejects_unknown_severity():
    raw = json.dumps([
        {"span": "x", "category": "other", "severity": "critical", "reason": "n/a"},
    ])
    with pytest.raises(LintParseError):
        parse_lint_response(raw)
