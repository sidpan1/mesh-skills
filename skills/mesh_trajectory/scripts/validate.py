"""Pre-push validator. Privacy gate. REFUSES any field not in SCHEMA_FIELDS.

Usage as CLI:
    python -m skills.mesh_trajectory.scripts.validate path/to/user.md
"""
import os
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path
import yaml
from skills.mesh_trajectory.schema import (
    SCHEMA_FIELDS, REQUIRED_FIELDS, SCHEMA_VERSION,
    ACCEPTED_SCHEMA_VERSIONS,
    MIGRATION_CUTOFF_DATE_V2, MIGRATION_CUTOFF_DATE_V3,
    SECTION_FIELDS, SECTION_WORD_CAPS, TOTAL_BODY_WORD_CAP,
    SECTION_FIELDS_BY_VERSION, SECTION_WORD_CAPS_BY_VERSION,
    TOTAL_BODY_WORD_CAP_BY_VERSION,
)

V0_ALLOWED_CITIES = frozenset({"Bengaluru"})
# Legacy single-body word check; V6+V7 supersede this in later tasks.
BODY_MIN_WORDS = 50
BODY_MAX_WORDS = 300


class ValidationError(Exception):
    pass


_H2_RE = re.compile(r"^##\s+(.+?)\s*$")

# V8 regex set. Conservative; failures name the offending substring so the
# user can rephrase. False-positives are acceptable, false-negatives are not.
# Phone: any run of 7+ digits possibly preceded by + and interleaved with
# single-character separators (space, hyphen, dot). Catches +91 98765 43210,
# 98765-43210, 415.555.0123, 9876543210, +1 (415) 555-0123 (after stripping
# parens).
_PHONE_RE = re.compile(r"(?:\+?\d(?:[\s\-.]?\d){6,14})")
_EMAIL_RE = re.compile(r"[\w\.\-+]+@[\w\.\-]+\.[A-Za-z]{2,}")
_ADDRESS_RE = re.compile(
    r"(?:#\s*\d+[A-Z]?[-/]?\d*[A-Z]?"
    r"|\b\d+[A-Z]?[-/]\d+[A-Z]?\b"
    r"|\b(?:HSR Layout|Indiranagar|Koramangala|Whitefield|Marathahalli|Jayanagar|Bellandur)\b)",
    re.IGNORECASE,
)


def _load_stoplist() -> list[str]:
    """Committed stop-list plus optional per-user override.

    Override path: env $MESH_PII_EXTRA_PATH, else ~/.mesh/pii_extra.txt.
    """
    base = Path(__file__).parent.parent / "pii_stoplist.txt"
    override = Path(os.environ.get("MESH_PII_EXTRA_PATH") or Path.home() / ".mesh" / "pii_extra.txt")
    terms: list[str] = []
    for path in (base, override):
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            terms.append(line)
    return terms


def parse_sections(body: str) -> dict[str, str]:
    """Walk markdown body, return ordered {h2_text: section_body} dict.

    Heading text is NFC-normalized and stripped of trailing whitespace.
    Section bodies preserve interior whitespace; leading/trailing newlines
    are stripped. The returned dict preserves insertion order (Python 3.7+).
    Lines before the first H2 are ignored (no heading to attach to).
    """
    sections: dict[str, str] = {}
    current_heading: str | None = None
    current_lines: list[str] = []
    for line in body.splitlines():
        m = _H2_RE.match(line)
        if m:
            if current_heading is not None:
                sections[current_heading] = "\n".join(current_lines).strip()
            current_heading = unicodedata.normalize("NFC", m.group(1))
            current_lines = []
        else:
            if current_heading is not None:
                current_lines.append(line)
    if current_heading is not None:
        sections[current_heading] = "\n".join(current_lines).strip()
    return sections


def validate_payload(frontmatter: dict, body: str, today: date | None = None) -> None:
    today = today or date.today()
    keys = set(frontmatter.keys())

    # V1: forbidden field rejection
    extra = keys - SCHEMA_FIELDS
    if extra:
        raise ValidationError(f"forbidden field(s) present: {sorted(extra)}")

    # V2: required fields present
    missing = REQUIRED_FIELDS - keys
    if missing:
        raise ValidationError(f"missing required field(s): {sorted(missing)}")

    # V3: schema_version gate with per-version migration windows.
    sv = frontmatter["schema_version"]
    if sv not in ACCEPTED_SCHEMA_VERSIONS:
        raise ValidationError(
            f"schema_version must be one of {sorted(ACCEPTED_SCHEMA_VERSIONS)}, got {sv}"
        )
    if sv == 1 and today >= MIGRATION_CUTOFF_DATE_V2:
        raise ValidationError(
            f"schema_version 1 not accepted after {MIGRATION_CUTOFF_DATE_V2.isoformat()}; "
            f"re-run /mesh-trajectory sync to migrate to schema_version {SCHEMA_VERSION}"
        )
    if sv == 2 and today >= MIGRATION_CUTOFF_DATE_V3:
        raise ValidationError(
            f"schema_version 2 not accepted after {MIGRATION_CUTOFF_DATE_V3.isoformat()}; "
            f"re-run /mesh-trajectory sync to migrate to schema_version {SCHEMA_VERSION}"
        )

    # city
    if frontmatter["city"] not in V0_ALLOWED_CITIES:
        raise ValidationError(
            f"city must be one of {sorted(V0_ALLOWED_CITIES)} in V0, got {frontmatter['city']}"
        )

    # V4-V7: section structure rules dispatch on schema_version.
    if sv in (2, 3):
        sections = parse_sections(body)
        actual = list(sections.keys())
        expected = list(SECTION_FIELDS_BY_VERSION[sv])
        caps = SECTION_WORD_CAPS_BY_VERSION[sv]
        total_cap = TOTAL_BODY_WORD_CAP_BY_VERSION[sv]

        # Typo detection: case-only mismatch suggests a rename.
        for a in actual:
            for e in expected:
                if a != e and a.lower() == e.lower():
                    raise ValidationError(
                        f"section heading typo: rename '{a}' to '{e}'"
                    )

        # V5: extras (H2 headings outside SECTION_FIELDS_BY_VERSION[sv])
        unexpected = [a for a in actual if a not in expected]
        if unexpected:
            raise ValidationError(
                f"unexpected section heading(s) in body: {unexpected}; "
                f"only {expected} are allowed for schema_version {sv}"
            )

        # V4 (continued): missing
        missing = [e for e in expected if e not in actual]
        if missing:
            raise ValidationError(f"missing required section(s): {missing}")

        # V4 (continued): order
        if actual != expected:
            raise ValidationError(
                f"sections must appear in this order: {expected}; got: {actual}"
            )

        # V6: each section <= caps[name]
        for name in expected:
            wc = len(sections[name].split())
            cap = caps[name]
            if wc > cap:
                raise ValidationError(
                    f"section '{name}' has {wc} words; cap is {cap}"
                )

        # V7: total body <= total_cap
        total = sum(len(sections[name].split()) for name in expected)
        if total > total_cap:
            raise ValidationError(
                f"total body has {total} words; cap is {total_cap}"
            )

        # V8: PII stop-list pass (unchanged from plan 05).
        own_email = frontmatter["email"].lower()
        body_lower = body.lower()

        m = _PHONE_RE.search(body)
        if m:
            raise ValidationError(f"PII (phone) in body: '{m.group(0)}'")
        for em in _EMAIL_RE.findall(body):
            if em.lower() != own_email:
                raise ValidationError(f"PII (email) in body: '{em}'")
        m = _ADDRESS_RE.search(body)
        if m:
            raise ValidationError(f"PII (address) in body: '{m.group(0)}'")
        for term in _load_stoplist():
            pattern = r"\b" + re.escape(term.lower()) + r"\b"
            if re.search(pattern, body_lower):
                raise ValidationError(f"PII (stoplist) in body: '{term}'")

    else:
        # v1 only: legacy single-body word check (50-300).
        word_count = len(body.split())
        if word_count < BODY_MIN_WORDS or word_count > BODY_MAX_WORDS:
            raise ValidationError(
                f"body must be {BODY_MIN_WORDS}-{BODY_MAX_WORDS} words, got {word_count}"
            )


def parse_markdown(path: Path) -> tuple[dict, str]:
    text = path.read_text()
    if not text.startswith("---\n"):
        raise ValidationError("file must begin with YAML frontmatter '---'")
    parts = text.split("---\n", 2)
    if len(parts) != 3:
        raise ValidationError("file must end frontmatter with closing '---'")
    _, fm_text, body = parts
    fm = yaml.safe_load(fm_text)
    if not isinstance(fm, dict):
        raise ValidationError("frontmatter must be a YAML mapping")
    return fm, body.strip()


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate.py <path/to/user.md>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    try:
        fm, body = parse_markdown(path)
        validate_payload(fm, body)
    except ValidationError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
