"""Pre-push validator. Privacy gate. REFUSES any field not in SCHEMA_FIELDS.

Usage as CLI:
    python -m skills.mesh_trajectory.scripts.validate path/to/user.md
"""
import sys
from pathlib import Path
import yaml
from skills.mesh_trajectory.schema import (
    SCHEMA_FIELDS, REQUIRED_FIELDS, SCHEMA_VERSION,
)

V0_ALLOWED_CITIES = frozenset({"Bengaluru"})
BODY_MIN_WORDS = 50
BODY_MAX_WORDS = 300


class ValidationError(Exception):
    pass


def validate_payload(frontmatter: dict, body: str) -> None:
    keys = set(frontmatter.keys())

    extra = keys - SCHEMA_FIELDS
    if extra:
        raise ValidationError(f"forbidden field(s) present: {sorted(extra)}")

    missing = REQUIRED_FIELDS - keys
    if missing:
        raise ValidationError(f"missing required field(s): {sorted(missing)}")

    if frontmatter["schema_version"] != SCHEMA_VERSION:
        raise ValidationError(
            f"schema_version must be {SCHEMA_VERSION}, got {frontmatter['schema_version']}"
        )

    if frontmatter["city"] not in V0_ALLOWED_CITIES:
        raise ValidationError(
            f"city must be one of {sorted(V0_ALLOWED_CITIES)} in V0, got {frontmatter['city']}"
        )

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
