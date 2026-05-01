"""Pre-push validator. Privacy gate. REFUSES any field not in SCHEMA_FIELDS.

Usage as CLI:
    python -m skills.mesh_trajectory.scripts.validate path/to/user.md
"""
import sys
from datetime import date
from pathlib import Path
import yaml
from skills.mesh_trajectory.schema import (
    SCHEMA_FIELDS, REQUIRED_FIELDS, SCHEMA_VERSION,
    ACCEPTED_SCHEMA_VERSIONS, MIGRATION_CUTOFF_DATE,
)

V0_ALLOWED_CITIES = frozenset({"Bengaluru"})
# Legacy single-body word check; V6+V7 supersede this in later tasks.
BODY_MIN_WORDS = 50
BODY_MAX_WORDS = 300


class ValidationError(Exception):
    pass


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

    # V3: schema_version gate with migration window
    sv = frontmatter["schema_version"]
    if sv not in ACCEPTED_SCHEMA_VERSIONS:
        raise ValidationError(
            f"schema_version must be one of {sorted(ACCEPTED_SCHEMA_VERSIONS)}, got {sv}"
        )
    if sv == 1 and today >= MIGRATION_CUTOFF_DATE:
        raise ValidationError(
            f"schema_version 1 not accepted after {MIGRATION_CUTOFF_DATE.isoformat()}; "
            f"re-run /mesh-trajectory sync to migrate to schema_version 2"
        )

    # city
    if frontmatter["city"] not in V0_ALLOWED_CITIES:
        raise ValidationError(
            f"city must be one of {sorted(V0_ALLOWED_CITIES)} in V0, got {frontmatter['city']}"
        )

    # Legacy body word check (replaced by V6+V7 in subsequent tasks)
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
