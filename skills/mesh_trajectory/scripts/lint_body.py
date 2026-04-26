"""LLM-as-judge privacy lint: parse and validate the JSON output of the lint prompt.

The judge prompt asks local Claude to scan the candidate body and emit a JSON
array of suspect spans. This module consumes that JSON, validates the shape
strictly, and returns dataclasses ready for the interactive resolution loop in
SKILL.md (one AskUserQuestion round per flag: KEEP / REDACT / REPHRASE).
"""
from dataclasses import dataclass
import json
import re

ALLOWED_CATEGORIES = frozenset({"career", "family-health", "internal-codename", "customer-partner", "other"})
ALLOWED_SEVERITIES = frozenset({"high", "medium", "low"})


class LintParseError(ValueError):
    pass


@dataclass
class LintFlag:
    span: str
    category: str
    severity: str
    reason: str


def parse_lint_response(raw: str) -> list[LintFlag]:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise LintParseError(f"invalid JSON: {e}")
    if not isinstance(data, list):
        raise LintParseError("root must be array")
    flags: list[LintFlag] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise LintParseError(f"item {i} not object")
        for key in ("span", "category", "severity", "reason"):
            if key not in item:
                raise LintParseError(f"item {i} missing {key}")
        if item["category"] not in ALLOWED_CATEGORIES:
            raise LintParseError(f"item {i} unknown category {item['category']!r}")
        if item["severity"] not in ALLOWED_SEVERITIES:
            raise LintParseError(f"item {i} unknown severity {item['severity']!r}")
        flags.append(LintFlag(
            span=item["span"], category=item["category"],
            severity=item["severity"], reason=item["reason"],
        ))
    return flags
