# MESH V0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship MESH V0 in 7 days: a paste-able onboarding prompt + a local Claude Code skill (`mesh-trajectory`) + a central Claude Code skill on the founder laptop (`mesh-orchestrator`) that together produce one Bengaluru dinner of 6 builders on Saturday 2026-05-09.

**Architecture:** Two Claude agents communicating through a private GitHub repo (`mesh-data`) used as the only shared store. Local skill extracts Claude Code session history, summarizes via local Claude, validates against an 8-field schema, and pushes to git. Central skill reads all user files, asks Claude to compose tables, and writes invite markdown back. No web app, no database, no third-party API.

**Tech Stack:**
- Python 3.11+ (scripts: extraction, validation, git push, invite render)
- `pyyaml` (frontmatter parsing)
- `pytest` (TDD)
- `gh` CLI (GitHub auth + push) and `git` CLI (clone + commit)
- Claude Code skill format (markdown SKILL.md + `scripts/` + slash commands)

---

## File Structure

The working directory `/Users/sidhant.panda/workspaces/root-workspace/mesh/` is itself the public `mesh-skills` repo. The private `mesh-data` repo lives on GitHub only.

```
mesh/                                     <- this repo (public, "mesh-skills")
├── spec.md                               (already exists)
├── plan.md                               (this file)
├── README.md                             setup + install instructions
├── ONBOARD.md                            the paste-able prompt
├── pyproject.toml                        python deps + pytest config
├── skills/
│   ├── mesh-trajectory/                  USER-SIDE skill
│   │   ├── SKILL.md                      slash commands + flow instructions for Claude
│   │   ├── schema.py                     authoritative 8-field schema
│   │   ├── scripts/
│   │   │   ├── extract.py                reads ~/.claude/projects/*.jsonl
│   │   │   ├── validate.py               schema gate (REFUSES extra fields)
│   │   │   ├── push.py                   clones/pulls mesh-data, writes user file, pushes
│   │   │   └── render_invite.py          formats a dinner-*.md file for terminal display
│   │   └── prompts/
│   │       └── summarize.md              the prompt local Claude follows to write trajectory
│   └── mesh-orchestrator/                FOUNDER-SIDE skill
│       ├── SKILL.md                      slash command + flow for matching
│       ├── scripts/
│       │   ├── load_users.py             reads users/*.md from mesh-data, returns list of dicts
│       │   ├── parse_response.py         validates Claude's JSON table-composition output
│       │   └── write_invites.py          writes networking-dinners/dinner-YYYY-MM-DD/table-N.md
│       └── prompts/
│           └── compose.md                the prompt for Claude-as-matcher
└── tests/                                pytest tree, mirrors skills/
    ├── test_schema.py
    ├── test_validate.py
    ├── test_extract.py
    ├── test_push.py
    ├── test_load_users.py
    ├── test_parse_response.py
    └── test_write_invites.py
```

**`mesh-data` repo (private GitHub)** structure, populated by users + orchestrator at runtime:
```
mesh-data/
├── README.md                       audit trail explanation, schema link
├── users/
│   └── <email>.md                  one file per user
└── networking-dinners/
    └── dinner-YYYY-MM-DD/
        ├── table-1.md
        └── table-N.md
```

---

## Tech notes

- **Slash commands**: defined in each `SKILL.md` (e.g., `/mesh-onboard`, `/mesh-sync`, `/mesh-check`, `/mesh-orchestrate`). Each runs the skill instructions and invokes scripts via the Bash tool.
- **Local Claude as summarizer**: Claude reads extraction output and writes the 200-word trajectory directly in its response, then writes the file. No subprocess to a separate `claude` invocation.
- **Auth**: user provides a GitHub Personal Access Token (PAT) with write scope to `mesh-data` only, stored as env var `MESH_GH_TOKEN`. Founder laptop uses the same env var.
- **Email as primary key**: filename `users/<email>.md` (slashes in email replaced with `_`).

---

# Tasks

## Task 0: Repository + tooling bootstrap

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `.gitignore`
- Create: GitHub repo `mesh-data` (private)

- [ ] **Step 1: Initialize git in this repo**

```bash
cd /Users/sidhant.panda/workspaces/root-workspace/mesh
git init
git branch -m main
```

- [ ] **Step 2: Create `.gitignore`**

```bash
cat > .gitignore <<'EOF'
__pycache__/
*.pyc
.pytest_cache/
.venv/
.env
*.egg-info/
.DS_Store
EOF
```

- [ ] **Step 3: Create `pyproject.toml`**

```toml
[project]
name = "mesh-skills"
version = "0.0.1"
requires-python = ">=3.11"
dependencies = [
  "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-cov>=5.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

- [ ] **Step 4: Create `README.md`**

```markdown
# mesh-skills

MESH V0: AI-curated professional dinners for builders.

See `spec.md` for the product spec. See `plan.md` for the implementation plan.

## For users (attendees)

Paste the contents of `ONBOARD.md` into Claude Code on your machine.

## For the founder

After cloning, run:

    pip install -e ".[dev]"
    pytest

The `mesh-orchestrator` skill is in `skills/mesh-orchestrator/`. It runs on the founder laptop on Friday to compose tables for the Saturday dinner.
```

- [ ] **Step 5: Set up Python environment**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Expected: pytest installed; `pytest --collect-only` returns no tests yet.

- [ ] **Step 6: Create the private `mesh-data` repo on GitHub**

```bash
gh repo create mesh-data --private --description "MESH V0 shared store: user trajectories + dinner invites"
```

Expected output: `https://github.com/<your-handle>/mesh-data` created.

- [ ] **Step 7: Bootstrap mesh-data with README**

```bash
cd /tmp
gh repo clone mesh-data
cd mesh-data
cat > README.md <<'EOF'
# mesh-data

Private shared store for MESH V0. Two writers:
- Users: each commits exactly one file at `users/<email>.md` matching the schema in `mesh-skills/skills/mesh-trajectory/schema.py`.
- Founder: commits `networking-dinners/dinner-YYYY-MM-DD/table-N.md` files weekly.

Do not commit anything else here.
EOF
mkdir -p users networking-dinners
touch users/.gitkeep networking-dinners/.gitkeep
git add . && git commit -m "init: scaffold users/ and networking-dinners/"
git push origin main
cd /Users/sidhant.panda/workspaces/root-workspace/mesh
```

- [ ] **Step 8: First commit on mesh-skills**

```bash
git add .
git commit -m "init: pyproject, gitignore, README"
```

---

## Task 1: Schema definition

**Files:**
- Create: `skills/mesh-trajectory/schema.py`
- Test: `tests/test_schema.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_schema.py
from skills.mesh_trajectory.schema import SCHEMA_FIELDS, SCHEMA_VERSION, REQUIRED_FIELDS

def test_schema_version_is_one():
    assert SCHEMA_VERSION == 1

def test_required_fields_are_locked():
    assert REQUIRED_FIELDS == {
        "schema_version", "name", "email", "linkedin_url",
        "role", "city", "available_saturdays",
    }

def test_full_field_set_includes_optional():
    assert SCHEMA_FIELDS == REQUIRED_FIELDS | {"do_not_match", "embedding"}
```

- [ ] **Step 2: Run test, verify it fails**

```bash
mkdir -p skills/mesh_trajectory  # python module name (underscore)
touch skills/__init__.py skills/mesh_trajectory/__init__.py
pytest tests/test_schema.py -v
```

Expected: ImportError on `schema`.

- [ ] **Step 3: Write minimal implementation**

```python
# skills/mesh_trajectory/schema.py
"""Authoritative schema for MESH V0 user payload.

Any field not in SCHEMA_FIELDS is forbidden. The validator enforces this.
"""

SCHEMA_VERSION = 1

REQUIRED_FIELDS = {
    "schema_version",
    "name",
    "email",
    "linkedin_url",
    "role",
    "city",
    "available_saturdays",
}

OPTIONAL_FIELDS = {
    "do_not_match",
    "embedding",
}

SCHEMA_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS
```

- [ ] **Step 4: Run test, verify it passes**

```bash
pytest tests/test_schema.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/ tests/test_schema.py
git commit -m "feat(schema): define V0 8-field user payload schema"
```

---

## Task 2: Pre-push validator (the privacy gate)

**Files:**
- Create: `skills/mesh-trajectory/scripts/validate.py` (also place at `skills/mesh_trajectory/scripts/validate.py` for python import)
- Test: `tests/test_validate.py`

We use the underscored path `skills/mesh_trajectory/` for Python imports throughout. The `SKILL.md` and `scripts/` will live under the dashed path `skills/mesh-trajectory/` in the actual skill directory served to Claude Code. Use a symlink: `ln -s mesh_trajectory skills/mesh-trajectory` so both paths point to the same directory.

- [ ] **Step 1: Create the symlink so both naming conventions work**

```bash
cd skills && ln -s mesh_trajectory mesh-trajectory && cd ..
ls -la skills/  # verify symlink
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_validate.py
import pytest
from skills.mesh_trajectory.scripts.validate import validate_payload, ValidationError

VALID = {
    "schema_version": 1,
    "name": "Asha Rao",
    "email": "asha@example.com",
    "linkedin_url": "https://linkedin.com/in/asharao",
    "role": "Founding Engineer",
    "city": "Bengaluru",
    "available_saturdays": ["2026-05-09"],
}

def test_valid_minimal_passes():
    validate_payload(VALID, body="A 50 word body about my work " * 4)

def test_valid_with_optional_fields():
    p = VALID | {"do_not_match": ["x@y.com"], "embedding": None}
    validate_payload(p, body="A 50 word body about my work " * 4)

def test_extra_field_is_refused():
    p = VALID | {"raw_conversation": "secret"}
    with pytest.raises(ValidationError, match="forbidden field"):
        validate_payload(p, body="ok body")

def test_missing_required_field_is_refused():
    p = {k: v for k, v in VALID.items() if k != "email"}
    with pytest.raises(ValidationError, match="missing required"):
        validate_payload(p, body="ok body")

def test_wrong_schema_version_is_refused():
    p = VALID | {"schema_version": 99}
    with pytest.raises(ValidationError, match="schema_version"):
        validate_payload(p, body="ok body")

def test_city_must_be_bengaluru_in_v0():
    p = VALID | {"city": "Mumbai"}
    with pytest.raises(ValidationError, match="city"):
        validate_payload(p, body="ok body")

def test_body_too_short_is_refused():
    with pytest.raises(ValidationError, match="body"):
        validate_payload(VALID, body="too short")

def test_body_too_long_is_refused():
    with pytest.raises(ValidationError, match="body"):
        validate_payload(VALID, body="word " * 500)
```

- [ ] **Step 3: Run, verify it fails**

```bash
mkdir -p skills/mesh_trajectory/scripts
touch skills/mesh_trajectory/scripts/__init__.py
pytest tests/test_validate.py -v
```

Expected: ImportError on `validate`.

- [ ] **Step 4: Implement the validator**

```python
# skills/mesh_trajectory/scripts/validate.py
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

V0_ALLOWED_CITIES = {"Bengaluru"}
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
    _, fm_text, body = text.split("---\n", 2)
    return yaml.safe_load(fm_text), body.strip()


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
```

- [ ] **Step 5: Run, verify all 8 tests pass**

```bash
pytest tests/test_validate.py -v
```

Expected: 8 passed.

- [ ] **Step 6: Commit**

```bash
git add skills/ tests/test_validate.py
git commit -m "feat(validate): privacy-gate validator refuses non-schema fields"
```

---

## Task 3: Claude Code session extractor

**Files:**
- Create: `skills/mesh_trajectory/scripts/extract.py`
- Test: `tests/test_extract.py`

The extractor reads `~/.claude/projects/*/conversation.jsonl` files (one per project), filters to the last 4 weeks, and produces a plain-text corpus that Claude can summarize. It must NOT include filesystem paths, secrets in command outputs, or personal identifiers from tool results.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_extract.py
import json
from pathlib import Path
from skills.mesh_trajectory.scripts.extract import (
    extract_corpus, scrub_message,
)


def _make_jsonl(path: Path, messages: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(m) for m in messages))


def test_extract_returns_only_user_and_assistant_text(tmp_path):
    proj = tmp_path / "proj-a" / "conversation.jsonl"
    _make_jsonl(proj, [
        {"role": "user", "content": "How do I add streaming to my agent?", "timestamp": "2026-04-20T10:00:00Z"},
        {"role": "assistant", "content": "You can use Server-Sent Events.", "timestamp": "2026-04-20T10:00:05Z"},
        {"role": "tool", "content": "<file contents redacted>", "timestamp": "2026-04-20T10:00:10Z"},
    ])
    corpus = extract_corpus(projects_root=tmp_path, weeks=4, now="2026-04-25T00:00:00Z")
    assert "streaming" in corpus
    assert "Server-Sent Events" in corpus
    assert "<file contents redacted>" not in corpus


def test_extract_drops_messages_older_than_window(tmp_path):
    proj = tmp_path / "proj-b" / "conversation.jsonl"
    _make_jsonl(proj, [
        {"role": "user", "content": "OLD MESSAGE", "timestamp": "2026-01-01T00:00:00Z"},
        {"role": "user", "content": "RECENT MESSAGE", "timestamp": "2026-04-22T00:00:00Z"},
    ])
    corpus = extract_corpus(projects_root=tmp_path, weeks=4, now="2026-04-25T00:00:00Z")
    assert "OLD MESSAGE" not in corpus
    assert "RECENT MESSAGE" in corpus


def test_scrub_strips_absolute_paths():
    msg = "Read /Users/sid/secret/notes.md and /home/x/.ssh/id_rsa"
    out = scrub_message(msg)
    assert "/Users/sid/secret/notes.md" not in out
    assert "/home/x/.ssh/id_rsa" not in out
    assert "[path]" in out


def test_scrub_strips_likely_api_keys():
    msg = "OPENAI_API_KEY=sk-1234567890abcdef1234567890abcdef and ANTHROPIC_API_KEY=sk-ant-foo"
    out = scrub_message(msg)
    assert "sk-1234567890" not in out
    assert "sk-ant-foo" not in out
    assert "[redacted-key]" in out


def test_corpus_is_capped_to_max_chars(tmp_path):
    proj = tmp_path / "proj-c" / "conversation.jsonl"
    _make_jsonl(proj, [
        {"role": "user", "content": "long " * 10000, "timestamp": "2026-04-22T00:00:00Z"},
    ])
    corpus = extract_corpus(projects_root=tmp_path, weeks=4, now="2026-04-25T00:00:00Z", max_chars=5000)
    assert len(corpus) <= 5000
```

- [ ] **Step 2: Run, verify failure**

```bash
pytest tests/test_extract.py -v
```

Expected: ImportError on `extract`.

- [ ] **Step 3: Implement the extractor**

```python
# skills/mesh_trajectory/scripts/extract.py
"""Read ~/.claude/projects/*/conversation.jsonl, scrub, return a corpus.

The corpus is what local Claude reads to write the trajectory summary.
Only user + assistant text, scrubbed of paths and API-key shapes.
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_PROJECTS_ROOT = Path.home() / ".claude" / "projects"
DEFAULT_WEEKS = 4
DEFAULT_MAX_CHARS = 60_000

_PATH_RE = re.compile(r"(/[A-Za-z0-9_\-./~]+){2,}")
_KEY_RE = re.compile(r"\b(sk-[A-Za-z0-9_\-]{12,}|[A-Z][A-Z0-9_]+_API_KEY=\S+)\b")


def scrub_message(text: str) -> str:
    text = _KEY_RE.sub("[redacted-key]", text)
    text = _PATH_RE.sub("[path]", text)
    return text


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def extract_corpus(
    projects_root: Path = DEFAULT_PROJECTS_ROOT,
    weeks: int = DEFAULT_WEEKS,
    now: str | None = None,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str:
    cutoff = (
        _parse_ts(now) if now else datetime.now(timezone.utc)
    ) - timedelta(weeks=weeks)

    chunks: list[str] = []
    for jsonl in sorted(projects_root.rglob("conversation.jsonl")):
        for line in jsonl.read_text().splitlines():
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("role") not in ("user", "assistant"):
                continue
            ts_str = msg.get("timestamp")
            if not ts_str:
                continue
            try:
                ts = _parse_ts(ts_str)
            except ValueError:
                continue
            if ts < cutoff:
                continue
            content = msg.get("content")
            if not isinstance(content, str):
                continue
            chunks.append(f"[{msg['role']}] {scrub_message(content)}")

    corpus = "\n\n".join(chunks)
    return corpus[:max_chars]


def main() -> int:
    print(extract_corpus())
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, verify all 5 tests pass**

```bash
pytest tests/test_extract.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/mesh_trajectory/scripts/extract.py tests/test_extract.py
git commit -m "feat(extract): scrub + window Claude Code session jsonl files"
```

---

## Task 4: Push script (validator-gated git push)

**Files:**
- Create: `skills/mesh_trajectory/scripts/push.py`
- Test: `tests/test_push.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_push.py
import subprocess
from pathlib import Path
import pytest
from skills.mesh_trajectory.scripts.push import (
    write_user_file, slugify_email, PushAborted,
)
from skills.mesh_trajectory.scripts.validate import ValidationError


def test_slugify_email_replaces_at_and_dot():
    assert slugify_email("a.b@c.com") == "a_b_at_c_com"


def test_write_user_file_creates_valid_markdown(tmp_path):
    fm = {
        "schema_version": 1, "name": "Asha", "email": "asha@example.com",
        "linkedin_url": "https://linkedin.com/in/a", "role": "Eng",
        "city": "Bengaluru", "available_saturdays": ["2026-05-09"],
    }
    body = "A reasonable trajectory body. " * 10
    out = write_user_file(tmp_path, fm, body)
    assert out.name == "asha_at_example_com.md"
    text = out.read_text()
    assert text.startswith("---\n")
    assert "schema_version: 1" in text
    assert body.strip() in text


def test_write_user_file_aborts_on_validator_failure(tmp_path):
    fm = {"schema_version": 1, "name": "Asha"}  # missing required fields
    with pytest.raises(ValidationError):
        write_user_file(tmp_path, fm, "body " * 60)


def test_write_user_file_refuses_non_schema_field(tmp_path):
    fm = {
        "schema_version": 1, "name": "Asha", "email": "a@b.com",
        "linkedin_url": "https://x", "role": "Eng", "city": "Bengaluru",
        "available_saturdays": ["2026-05-09"],
        "raw_conversation": "leak attempt",
    }
    with pytest.raises(ValidationError, match="forbidden"):
        write_user_file(tmp_path, fm, "body " * 60)
```

- [ ] **Step 2: Run, verify failure**

```bash
pytest tests/test_push.py -v
```

Expected: ImportError on `push`.

- [ ] **Step 3: Implement push.py**

```python
# skills/mesh_trajectory/scripts/push.py
"""Validator-gated git push to mesh-data repo.

Flow:
  1. Validate frontmatter + body via validate_payload (raises ValidationError).
  2. Write users/<slugified-email>.md inside a working clone of mesh-data.
  3. Stage, commit, push.

Aborts with PushAborted on git/auth/network failures.
The validator gate runs BEFORE any disk write that could be pushed.
"""
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
import yaml

from skills.mesh_trajectory.scripts.validate import validate_payload, ValidationError


class PushAborted(Exception):
    pass


def slugify_email(email: str) -> str:
    return email.lower().replace("@", "_at_").replace(".", "_")


def write_user_file(users_dir: Path, frontmatter: dict, body: str) -> Path:
    """Validate then write. Raises ValidationError before any write."""
    validate_payload(frontmatter, body)
    users_dir.mkdir(parents=True, exist_ok=True)
    out = users_dir / f"{slugify_email(frontmatter['email'])}.md"
    rendered = "---\n" + yaml.safe_dump(frontmatter, sort_keys=False) + "---\n\n" + body.strip() + "\n"
    out.write_text(rendered)
    return out


def _run(cmd: list[str], cwd: Path) -> str:
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        raise PushAborted(f"{shlex.join(cmd)} failed: {res.stderr.strip()}")
    return res.stdout.strip()


def _authed_url(repo_url: str) -> str:
    """Inject MESH_GH_TOKEN into HTTPS URL if present. Required for non-interactive push."""
    token = os.environ.get("MESH_GH_TOKEN")
    if not token:
        return repo_url
    if repo_url.startswith("https://github.com/"):
        return repo_url.replace("https://", f"https://oauth2:{token}@", 1)
    return repo_url


def push_to_mesh_data(repo_url: str, frontmatter: dict, body: str, workdir: Path) -> str:
    """Clone (or pull) mesh-data into workdir, write file, push. Returns commit SHA."""
    auth_url = _authed_url(repo_url)
    if not (workdir / ".git").exists():
        _run(["git", "clone", auth_url, str(workdir)], cwd=Path.cwd())
    else:
        _run(["git", "remote", "set-url", "origin", auth_url], cwd=workdir)
        _run(["git", "pull", "--rebase"], cwd=workdir)

    out_path = write_user_file(workdir / "users", frontmatter, body)
    _run(["git", "add", str(out_path.relative_to(workdir))], cwd=workdir)
    _run(["git", "commit", "-m", f"user: {frontmatter['email']} weekly sync"], cwd=workdir)
    _run(["git", "push", "origin", "main"], cwd=workdir)
    return _run(["git", "rev-parse", "HEAD"], cwd=workdir)


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: push.py <mesh-data-repo-url> <frontmatter.yaml> <body.md>", file=sys.stderr)
        return 2
    fm = yaml.safe_load(Path(sys.argv[2]).read_text())
    body = Path(sys.argv[3]).read_text()
    repo_url = sys.argv[1]
    workdir = Path.home() / ".cache" / "mesh-data"
    workdir.parent.mkdir(parents=True, exist_ok=True)
    try:
        sha = push_to_mesh_data(repo_url, fm, body, workdir)
    except (ValidationError, PushAborted) as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 1
    print(sha)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, verify push tests pass**

```bash
pytest tests/test_push.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/mesh_trajectory/scripts/push.py tests/test_push.py
git commit -m "feat(push): validator-gated git push to mesh-data"
```

---

## Task 5: mesh-trajectory SKILL.md (the user-facing flow)

**Files:**
- Create: `skills/mesh_trajectory/SKILL.md`
- Create: `skills/mesh_trajectory/prompts/summarize.md`

- [ ] **Step 1: Write `prompts/summarize.md`**

```markdown
You are summarizing a Claude Code conversation corpus into a 200-word professional trajectory.

Read the corpus below. Produce one paragraph (180-220 words) that answers:
1. What is this person actually working on right now? (the substance, not the surface)
2. Where are they heading? (what is their focus shifting toward?)
3. What is the texture of their work? (infra, product, research, ops, etc.)

Constraints:
- Use present-continuous voice: "Building X", "Exploring Y", "Shifting from A toward B".
- No proper nouns of secret projects, customers, or non-public people.
- No file paths, code snippets, command output.
- No claims about what the person believes or intends; only what they're working on.
- Maximize semantic density. Every word should narrow the trajectory.

Output the paragraph only. No preamble, no headers.

CORPUS:
{{corpus}}
```

- [ ] **Step 2: Write `SKILL.md`**

```markdown
---
name: mesh-trajectory
description: MESH user-side skill. Onboards user, syncs trajectory weekly, displays dinner invites. Slash commands /mesh-onboard, /mesh-sync, /mesh-check, /mesh-status.
allowed_tools:
  - Bash
  - Read
  - Write
  - Edit
---

# mesh-trajectory

User-side skill for MESH V0. Reads local Claude Code sessions, summarizes via local Claude, and pushes a 200-word trajectory to the private `mesh-data` repo. Pulls and renders dinner invites.

## Slash commands

| Command | What it does |
|---|---|
| `/mesh-onboard` | First-time setup: collect Q&A, install env, run first sync. |
| `/mesh-sync` | Re-extract sessions, regenerate trajectory, push update. |
| `/mesh-check` | Pull mesh-data and show pending dinner invite, if any. |
| `/mesh-status` | Show current user file + last sync time + next Saturday status. |

## /mesh-onboard flow

1. Greet the user. Confirm they have read `spec.md` privacy section.
2. Ask the user, one at a time:
   - Full name
   - Primary email
   - LinkedIn URL
   - Role (free-text)
   - City (must be Bengaluru in V0; warn and abort if not)
   - Available Saturdays for the next 4 weeks (default to all)
   - Optional: emails of people they should NOT be matched with (`do_not_match`)
3. Ask the user for their `MESH_GH_TOKEN` (GitHub PAT with `repo` scope on `mesh-data`). Set in env.
4. Ask the user for the mesh-data repo URL (default: provided in onboarding prompt).
5. Run `python -m skills.mesh_trajectory.scripts.extract > /tmp/mesh_corpus.txt`. Show the user the corpus length and confirm they're OK with the contents being summarized (the corpus does not leave the device, only the summary).
6. Read `prompts/summarize.md`. Substitute `{{corpus}}` with `/tmp/mesh_corpus.txt` contents. Generate the 200-word trajectory paragraph in your response.
7. Write the paragraph to `/tmp/mesh_body.md`. Show it to the user. Ask them to edit (open in $EDITOR or paste replacement). Loop until approved.
8. Compose the YAML frontmatter from collected answers. Write to `/tmp/mesh_fm.yaml`.
9. Run `python -m skills.mesh_trajectory.scripts.push $REPO_URL /tmp/mesh_fm.yaml /tmp/mesh_body.md`.
10. On success, print: "MESH onboarding complete. You'll get an invite via /mesh-check on Friday evening."
11. On REFUSED output: explain what was rejected and why. Do not retry without user fixing the input.

## /mesh-sync flow

Same as /mesh-onboard from step 5 onwards, reusing answers stored in `~/.config/mesh/profile.yaml` (created on first onboard).

## /mesh-check flow

1. `git -C ~/.cache/mesh-data pull --rebase`
2. Find `networking-dinners/dinner-*/table-*.md` files containing the user's email.
3. For the most recent matching file, run `python -m skills.mesh_trajectory.scripts.render_invite <path>` and show the formatted output.
4. If none, print: "No invite yet. Founder runs the orchestrator on Fridays."

## /mesh-status flow

1. Show `users/<slugified-email>.md` from local mesh-data clone.
2. Show last commit timestamp on that file.
3. Show next Saturday from `available_saturdays` and whether an invite for that date exists.

## Privacy contract

- The corpus generated by `extract.py` lives at `/tmp/mesh_corpus.txt` and is deleted at the end of onboarding/sync.
- Only the validated payload reaches `mesh-data`. The validator REFUSES any non-schema field; never bypass.
- The user reviews the trajectory body before push. No silent regeneration.
```

- [ ] **Step 3: Quick smoke test (no formal pytest, but verify file exists and renders)**

```bash
ls skills/mesh_trajectory/SKILL.md skills/mesh_trajectory/prompts/summarize.md
head -20 skills/mesh_trajectory/SKILL.md
```

Expected: both files present, frontmatter present.

- [ ] **Step 4: Commit**

```bash
git add skills/mesh_trajectory/SKILL.md skills/mesh_trajectory/prompts/summarize.md
git commit -m "feat(mesh-trajectory): SKILL.md + summarize prompt"
```

---

## Task 6: render_invite.py (formats a dinner-*.md for terminal)

**Files:**
- Create: `skills/mesh_trajectory/scripts/render_invite.py`
- Test: `tests/test_render_invite.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_render_invite.py
from pathlib import Path
from skills.mesh_trajectory.scripts.render_invite import render_invite

SAMPLE = """---
dinner_date: "2026-05-09"
time: "19:00"
venue: "The Permit Room, Indiranagar"
table: 1
attendees:
  - email: asha@example.com
    name: Asha Rao
    role: Founding Engineer
    trajectory_one_liner: "Building agent harness unification across runtimes"
  - email: rohit@example.com
    name: Rohit K
    role: PM
    trajectory_one_liner: "Exploring agent eval from product side"
---

# Why this table

Asha and Rohit are the Guide-Explorer pair: Asha three months deep in agent
harnesses, Rohit just starting to think about evaluation as a product surface.
"""


def test_render_includes_venue_time_and_attendees(tmp_path):
    f = tmp_path / "table-1.md"
    f.write_text(SAMPLE)
    out = render_invite(f)
    assert "Permit Room" in out
    assert "Sat 2026-05-09 19:00" in out
    assert "Asha Rao" in out
    assert "Rohit K" in out
    assert "Why this table" in out
```

- [ ] **Step 2: Run, verify failure**

```bash
pytest tests/test_render_invite.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement render_invite.py**

```python
# skills/mesh_trajectory/scripts/render_invite.py
"""Pretty-print a dinner table markdown file for terminal display."""
import sys
from pathlib import Path
import yaml


def render_invite(path: Path) -> str:
    text = path.read_text()
    _, fm_text, body = text.split("---\n", 2)
    fm = yaml.safe_load(fm_text)

    lines = []
    lines.append("=" * 72)
    lines.append(f"  MESH DINNER  Sat {fm['dinner_date']} {fm['time']}")
    lines.append(f"  {fm['venue']}")
    lines.append(f"  Table {fm['table']}")
    lines.append("=" * 72)
    lines.append("")
    lines.append("YOUR TABLE:")
    lines.append("")
    for a in fm["attendees"]:
        lines.append(f"  - {a['name']} ({a['role']})")
        lines.append(f"      {a['trajectory_one_liner']}")
        lines.append(f"      {a['email']}")
        lines.append("")
    lines.append(body.strip())
    lines.append("")
    lines.append("=" * 72)
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: render_invite.py <path>", file=sys.stderr)
        return 2
    print(render_invite(Path(sys.argv[1])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run, verify pass**

```bash
pytest tests/test_render_invite.py -v
```

Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/mesh_trajectory/scripts/render_invite.py tests/test_render_invite.py
git commit -m "feat(render): pretty-print dinner invite for terminal"
```

---

## Task 7: Orchestrator load_users.py

**Files:**
- Create: `skills/mesh_orchestrator/scripts/load_users.py`
- Create: `skills/__init__.py`, `skills/mesh_orchestrator/__init__.py`, `skills/mesh_orchestrator/scripts/__init__.py`
- Test: `tests/test_load_users.py`

- [ ] **Step 1: Create the package skeleton**

```bash
mkdir -p skills/mesh_orchestrator/scripts skills/mesh_orchestrator/prompts
touch skills/mesh_orchestrator/__init__.py skills/mesh_orchestrator/scripts/__init__.py
cd skills && ln -s mesh_orchestrator mesh-orchestrator && cd ..
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_load_users.py
from pathlib import Path
from skills.mesh_orchestrator.scripts.load_users import (
    load_users_for_date, User,
)


def _write_user(dir: Path, email: str, sats: list[str], body: str = "body " * 60):
    (dir / "users").mkdir(parents=True, exist_ok=True)
    fm = (
        f"---\nschema_version: 1\nname: {email}\nemail: {email}\n"
        f"linkedin_url: https://x\nrole: Eng\ncity: Bengaluru\n"
        f"available_saturdays:\n"
    )
    for s in sats:
        fm += f"  - '{s}'\n"
    fm += "---\n\n" + body
    slug = email.lower().replace("@", "_at_").replace(".", "_")
    (dir / "users" / f"{slug}.md").write_text(fm)


def test_loads_only_users_available_on_target_date(tmp_path):
    _write_user(tmp_path, "a@x.com", ["2026-05-09"])
    _write_user(tmp_path, "b@x.com", ["2026-05-09", "2026-05-16"])
    _write_user(tmp_path, "c@x.com", ["2026-05-16"])  # not available 5/9
    users = load_users_for_date(tmp_path, "2026-05-09")
    emails = sorted(u.email for u in users)
    assert emails == ["a@x.com", "b@x.com"]


def test_user_has_body_attribute(tmp_path):
    _write_user(tmp_path, "a@x.com", ["2026-05-09"], body="trajectory text " * 20)
    users = load_users_for_date(tmp_path, "2026-05-09")
    assert "trajectory text" in users[0].body


def test_skips_users_in_wrong_city(tmp_path, monkeypatch):
    # Write a Mumbai user manually (bypass our test helper which hardcodes Bengaluru)
    (tmp_path / "users").mkdir(parents=True, exist_ok=True)
    (tmp_path / "users" / "x_at_y.md").write_text(
        "---\nschema_version: 1\nname: X\nemail: x@y.com\n"
        "linkedin_url: https://x\nrole: Eng\ncity: Mumbai\n"
        "available_saturdays: ['2026-05-09']\n---\n\nbody " * 60
    )
    users = load_users_for_date(tmp_path, "2026-05-09")
    assert users == []
```

- [ ] **Step 3: Run, verify failure**

```bash
pytest tests/test_load_users.py -v
```

Expected: ImportError.

- [ ] **Step 4: Implement load_users.py**

```python
# skills/mesh_orchestrator/scripts/load_users.py
"""Load users/*.md from a mesh-data clone, filter by available_saturday + city."""
from dataclasses import dataclass
from pathlib import Path
import yaml


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


def _parse(path: Path) -> User | None:
    text = path.read_text()
    if not text.startswith("---\n"):
        return None
    _, fm_text, body = text.split("---\n", 2)
    fm = yaml.safe_load(fm_text)
    return User(
        email=fm["email"],
        name=fm["name"],
        linkedin_url=fm["linkedin_url"],
        role=fm["role"],
        city=fm["city"],
        available_saturdays=fm["available_saturdays"],
        do_not_match=fm.get("do_not_match", []) or [],
        body=body.strip(),
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
```

- [ ] **Step 5: Run, verify all 3 tests pass**

```bash
pytest tests/test_load_users.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add skills/mesh_orchestrator/ tests/test_load_users.py
git commit -m "feat(orchestrator): load_users filters by date and city"
```

---

## Task 8: Compose prompt + parse_response.py

**Files:**
- Create: `skills/mesh_orchestrator/prompts/compose.md`
- Create: `skills/mesh_orchestrator/scripts/parse_response.py`
- Test: `tests/test_parse_response.py`

- [ ] **Step 1: Write the compose prompt**

```markdown
# skills/mesh_orchestrator/prompts/compose.md
You are MESH's matching engine. You read every available user's trajectory and compose tables of 6 for an in-person dinner this Saturday in Bengaluru.

## Inputs you have

- Dinner date: {{dinner_date}}
- Venue: {{venue}}
- Available users (each as JSON below): name, email, role, do_not_match, trajectory body.

## What to optimize

Compose tables that maximize the chance of a "this changed my career" conversation. The signal you're looking for:

1. **Guide x Explorer** (highest value): one person three months deep in a topic, another just starting to explore the same topic from a different angle. These are the dinners that bend trajectories.
2. **Fellow Explorers**: shared open question, similar velocity. Good energy.
3. **Adjacent problem spaces**: same domain (e.g., agent infra), different vantage point (infra vs product vs research).

Hard constraints (NEVER violate):

- Each table has exactly 6 attendees, unless total available is 13/19/25 etc., in which case last table is 7. If total < 12, output one table only with whatever is available and flag low-quorum.
- No two attendees from the same company (infer from role/email domain).
- Respect every user's `do_not_match` list.
- A given user appears in exactly one table.

## Output format (strict JSON)

```json
{
  "dinner_date": "{{dinner_date}}",
  "venue": "{{venue}}",
  "low_quorum": false,
  "tables": [
    {
      "table": 1,
      "attendees": [
        {
          "email": "asha@example.com",
          "name": "Asha Rao",
          "role": "Founding Engineer",
          "trajectory_one_liner": "Building agent harness unification across runtimes"
        }
      ],
      "why_this_table": "One paragraph explaining the trajectory intersections that make this table interesting. Reference specific people by first name. Call out the Guide x Explorer pairs."
    }
  ]
}
```

Output ONLY the JSON. No preamble. No code fences. Just the raw JSON object.

## Users

{{users_json}}
```

- [ ] **Step 2: Write the failing test for parse_response.py**

```python
# tests/test_parse_response.py
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
```

- [ ] **Step 3: Run, verify failure**

```bash
pytest tests/test_parse_response.py -v
```

Expected: ImportError.

- [ ] **Step 4: Implement parse_response.py**

```python
# skills/mesh_orchestrator/scripts/parse_response.py
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
```

- [ ] **Step 5: Run, verify all 6 tests pass**

```bash
pytest tests/test_parse_response.py -v
```

Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add skills/mesh_orchestrator/prompts/compose.md skills/mesh_orchestrator/scripts/parse_response.py tests/test_parse_response.py
git commit -m "feat(orchestrator): compose prompt + JSON parser with constraint checks"
```

---

## Task 9: write_invites.py

**Files:**
- Create: `skills/mesh_orchestrator/scripts/write_invites.py`
- Test: `tests/test_write_invites.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_write_invites.py
from pathlib import Path
import yaml
from skills.mesh_orchestrator.scripts.write_invites import write_invites

RESPONSE = {
    "dinner_date": "2026-05-09",
    "venue": "The Permit Room",
    "low_quorum": False,
    "tables": [{
        "table": 1,
        "attendees": [
            {"email": f"u{i}@x.com", "name": f"U{i}", "role": "Eng",
             "trajectory_one_liner": f"Building X{i}"} for i in range(6)
        ],
        "why_this_table": "good intersections",
    }],
}


def test_writes_one_file_per_table(tmp_path):
    paths = write_invites(tmp_path, RESPONSE, time="19:00")
    assert len(paths) == 1
    f = paths[0]
    assert f.parent.name == "dinner-2026-05-09"
    assert f.name == "table-1.md"
    text = f.read_text()
    assert text.startswith("---\n")
    fm = yaml.safe_load(text.split("---\n")[1])
    assert fm["dinner_date"] == "2026-05-09"
    assert fm["time"] == "19:00"
    assert fm["venue"] == "The Permit Room"
    assert len(fm["attendees"]) == 6
    assert "good intersections" in text


def test_creates_dinner_dir(tmp_path):
    write_invites(tmp_path, RESPONSE, time="19:00")
    assert (tmp_path / "networking-dinners" / "dinner-2026-05-09").is_dir()
```

- [ ] **Step 2: Run, verify failure**

```bash
pytest tests/test_write_invites.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement write_invites.py**

```python
# skills/mesh_orchestrator/scripts/write_invites.py
"""Write one networking-dinners/dinner-YYYY-MM-DD/table-N.md per table."""
from pathlib import Path
import yaml


def write_invites(mesh_data_root: Path, response: dict, time: str = "19:00") -> list[Path]:
    dinner_dir = mesh_data_root / "networking-dinners" / f"dinner-{response['dinner_date']}"
    dinner_dir.mkdir(parents=True, exist_ok=True)
    out: list[Path] = []
    for t in response["tables"]:
        fm = {
            "dinner_date": response["dinner_date"],
            "time": time,
            "venue": response["venue"],
            "table": t["table"],
            "attendees": t["attendees"],
        }
        body = "# Why this table\n\n" + t["why_this_table"].strip() + "\n"
        text = "---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n\n" + body
        path = dinner_dir / f"table-{t['table']}.md"
        path.write_text(text)
        out.append(path)
    return out
```

- [ ] **Step 4: Run, verify both tests pass**

```bash
pytest tests/test_write_invites.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add skills/mesh_orchestrator/scripts/write_invites.py tests/test_write_invites.py
git commit -m "feat(orchestrator): write_invites emits per-table markdown"
```

---

## Task 10: mesh-orchestrator SKILL.md

**Files:**
- Create: `skills/mesh_orchestrator/SKILL.md`

- [ ] **Step 1: Write the SKILL.md**

```markdown
---
name: mesh-orchestrator
description: MESH founder-side skill. Reads users from mesh-data, asks Claude to compose tables, writes invites. Slash command /mesh-orchestrate.
allowed_tools:
  - Bash
  - Read
  - Write
  - Edit
---

# mesh-orchestrator

Founder-side skill, run on the founder's laptop on Friday morning to compose tables for the upcoming Saturday dinner.

## Slash command

`/mesh-orchestrate <dinner_date>` (default: next Saturday)

## Flow

1. Compute `dinner_date` (default: next Saturday in YYYY-MM-DD).
2. Ask the user (founder) for the venue if not previously set this week. Save in `~/.config/mesh/orchestrator.yaml`.
3. `git -C ~/.cache/mesh-data pull --rebase`
4. Run `python -c "from skills.mesh_orchestrator.scripts.load_users import load_users_for_date; import json; print(json.dumps([u.__dict__ for u in load_users_for_date(__import__('pathlib').Path('~/.cache/mesh-data').expanduser(), '<dinner_date>')]))"` and capture the JSON list.
5. If fewer than 6 users available: print the list, ask founder whether to proceed (low-quorum dinner) or cancel.
6. Read `prompts/compose.md`. Substitute `{{dinner_date}}`, `{{venue}}`, `{{users_json}}`.
7. Generate the response (you, Claude, ARE the matching engine here). Output the strict JSON per the prompt.
8. Run `python -c "from skills.mesh_orchestrator.scripts.parse_response import parse_response; import sys, json; print(json.dumps(parse_response(sys.stdin.read())))" < /tmp/mesh_response.json` to validate. On ParseError, regenerate with the error in your context.
9. Show the founder the parsed response. Founder approves or asks for changes (in which case re-prompt with feedback).
10. Run `python -c "from skills.mesh_orchestrator.scripts.write_invites import write_invites; import json, pathlib; write_invites(pathlib.Path('~/.cache/mesh-data').expanduser(), json.load(open('/tmp/mesh_response.json')), time='19:00')"`.
11. `cd ~/.cache/mesh-data && git add networking-dinners && git commit -m "dinner: <dinner_date> tables composed" && git push`.
12. Print: "Invites pushed. Now WhatsApp the cohort: 'invites live, run /mesh-check'."

## Failure handling

- If load_users returns empty: cancel dinner, push a `dinner-<date>/cancelled.md` with reason.
- If parse_response keeps failing: print the raw Claude output, fall back to manual table composition by editing markdown directly.
- If git push fails: do not retry blindly; show founder the error, let them resolve auth/conflicts.

## Privacy

- Never log full user bodies in the terminal beyond what the founder needs to spot-check.
- The mesh-data clone is already private; do not copy it elsewhere.
```

- [ ] **Step 2: Quick smoke check**

```bash
ls skills/mesh_orchestrator/SKILL.md
head -10 skills/mesh_orchestrator/SKILL.md
```

- [ ] **Step 3: Commit**

```bash
git add skills/mesh_orchestrator/SKILL.md
git commit -m "feat(mesh-orchestrator): SKILL.md with /mesh-orchestrate flow"
```

---

## Task 11: ONBOARD.md (the paste-able prompt)

**Files:**
- Create: `ONBOARD.md`

- [ ] **Step 1: Write ONBOARD.md**

```markdown
# Paste this into Claude Code

You are about to onboard the user into MESH, a curated dinner-club for Bengaluru builders.

## Step 0: Confirm context

Tell the user:

> "MESH curates a Saturday-7pm dinner for 6 builders, matched on what you're actually
>  building (read from your local Claude Code sessions). I'll install a small skill,
>  ask you a few questions, summarize your trajectory locally, and push only that summary
>  to a private repo. Raw conversations never leave your machine. Continue?"

If they decline: stop. Otherwise proceed.

## Step 1: Install the skill

Run these bash commands (show them to the user first):

```bash
mkdir -p ~/.claude/skills
cd ~/.claude/skills
if [ ! -d mesh-skills ]; then
  git clone https://github.com/<your-handle>/mesh-skills.git
fi
cd mesh-skills
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
ln -snf "$PWD/skills/mesh_trajectory" ~/.claude/skills/mesh-trajectory
```

## Step 2: Collect the user's GitHub PAT

Tell the user:

> "I need a GitHub Personal Access Token with `repo` scope on the `mesh-data`
>  repository. Visit https://github.com/settings/tokens, create a fine-grained
>  token scoped to `mesh-data` only, and paste it here."

Set in env: `export MESH_GH_TOKEN=<token>` and persist to `~/.config/mesh/env`.

## Step 3: Run /mesh-onboard

Tell the user to run `/mesh-onboard`. The skill takes over from here.

## Step 4 (founder, post-event):

Once onboarded, the user will get an invite via `/mesh-check` on Friday evening.
The dinner is the following Saturday at 7pm in Bengaluru.
```

- [ ] **Step 2: Commit**

```bash
git add ONBOARD.md
git commit -m "feat(onboard): paste-able prompt that installs mesh-trajectory skill"
```

---

## Task 12: Dogfood end-to-end with 5 friends (Day 6)

**Files:** none new; this is a manual run-through that exercises all the code.

- [ ] **Step 1: Recruit 5 friends with Claude Code installed**

Pick 5 builders you know personally. Get a yes/no on a 30-minute Saturday-evening commitment for the dogfood "dinner #0" the day before launch.

- [ ] **Step 2: Send each friend the ONBOARD.md content**

Via WhatsApp/Signal. Watch them paste it into their Claude Code. Capture failures.

- [ ] **Step 3: Verify each friend's `users/<email>.md` lands in `mesh-data`**

```bash
cd ~/.cache/mesh-data && git pull
ls users/
```

Expected: 5 user files. Inspect each by hand to verify schema compliance and that no raw conversation content leaked.

- [ ] **Step 4: Run /mesh-orchestrate for next Saturday**

In your local Claude Code, run `/mesh-orchestrate 2026-05-02` (or whatever date you choose for dinner #0). Have Claude compose one table of 5 (or 6 if you're attending).

- [ ] **Step 5: Verify the friends receive their invite**

Each friend runs `/mesh-check`. Verify the rendered output is correct.

- [ ] **Step 6: Hold dinner #0**

Sit at the table. Take notes on:
- Did the conversation flow?
- Were the Claude-proposed pairings actually interesting?
- What broke during onboarding/sync/check for each friend?

- [ ] **Step 7: Triage + fix critical bugs (rest of Day 6 + AM Day 7)**

For each blocker discovered: file as a TODO in `KNOWN_ISSUES.md`. Fix anything that breaks the launch flow. Defer cosmetic issues.

- [ ] **Step 8: Commit fixes**

```bash
git add KNOWN_ISSUES.md  # plus any code fixes
git commit -m "fix(dogfood): issues from dinner #0 dogfood run"
```

---

## Task 13: Launch event prep (Day 7 AM)

**Files:**
- Create: `LAUNCH_PLAYBOOK.md`

- [ ] **Step 1: Book the venue for dinner #1 (Saturday 2026-05-09 at 7pm in Bengaluru)**

Pick a venue: 6 seats, conversational acoustics, decent food, BYOB or full bar. Pre-book + pay deposit.

- [ ] **Step 2: Write the LAUNCH_PLAYBOOK.md**

```markdown
# MESH Launch Event Playbook (Friday 2026-05-01)

## Logistics

- Venue: [TBD by Day 7]
- Time: 7pm-9pm
- Capacity: 30 invitees
- Wifi: confirm SSID/password in advance; print on cards
- Power: enough strips for 30 laptops

## Talk track (5 minutes)

1. The pitch: "Networking that matches on what you're building, not what you claim."
2. The mechanism: "You install a skill, it reads your last 4 weeks of Claude Code sessions locally,
   summarizes via your own Claude, and uploads only the 200-word summary."
3. The privacy: "Raw conversations never leave your machine. The validator refuses any field
   we didn't tell you about. Repo is private. You can edit/delete anytime."
4. The ask: "Paste this prompt into your Claude. 5 minutes. Then enjoy dinner."

## On-site flow

1. Greet, hand each attendee a printed card with the ONBOARD.md URL + a QR code.
2. Walk around. Help people who get stuck on git/PAT setup.
3. Track install failures in `LAUNCH_ISSUES.md` (one line each).
4. By 8:30pm: count `users/*.md` in mesh-data. Target: 25+/30 onboarded.
5. Announce: "Dinner #1 invites go out next Friday. Run /mesh-check after 6pm."

## Failure modes (from spec)

- Skill install fails → fall back to Google Form (URL printed on card).
- PAT confusion → walk through it personally.
- WiFi flaky → tether mobile hotspot.
```

- [ ] **Step 3: Print 30 cards (URL + QR code)**

QR code points to the raw ONBOARD.md on github.

- [ ] **Step 4: Test the WhatsApp group send**

Add all 30 to a WhatsApp group "MESH Cohort 1." Test that messages go through.

- [ ] **Step 5: Final commit before launch**

```bash
git add LAUNCH_PLAYBOOK.md
git commit -m "docs: launch playbook for 2026-05-01"
git push origin main
```

- [ ] **Step 6: GO**

Friday 2026-05-01 evening: run the event.

---

# Self-Review Checklist

Spec coverage check (each spec section -> task that implements it):

| Spec section | Implementing task(s) |
|---|---|
| Forcing functions (timeline, slot, AI layer, store) | T0 (repos), T13 (launch event date) |
| Architecture diagram | T1-T10 collectively |
| Components 1 (onboarding prompt) | T11 |
| Components 2 (mesh-trajectory skill) | T1, T2, T3, T4, T5, T6 |
| Components 3 (mesh-data repo) | T0 |
| Components 4 (mesh-orchestrator skill) | T7, T8, T9, T10 |
| Components 5 (mesh-feedback) | OUT OF SCOPE V0 |
| Components 6 (mesh-eval) | OUT OF SCOPE V0 |
| Data schema (8 fields, validator) | T1, T2 |
| Matching: Claude as engine | T8 (compose prompt) |
| Failure mode: too few opt-ins | T10 (orchestrator handles low quorum) |
| Failure mode: skill install fails | T13 (Google Form fallback in playbook) |
| Failure mode: bad match (do_not_match) | T1 (schema), T8 (compose prompt enforces) |
| Failure mode: privacy leak | T2 (validator REFUSES) |
| Failure mode: orchestrator garbage | T8 (parse_response) |
| Verification: dogfood with 5 friends | T12 |
| Privacy contract | T2 (validator), T5 (SKILL.md), T11 (ONBOARD.md) |

Placeholder scan: none in tasks above. Venue is TBD until Day 7 step 1, which is acceptable because it's an external dependency the founder owns.

Type consistency: `User` dataclass in T7, parsed from frontmatter dict produced by T2, matches schema fields from T1. `parse_response` (T8) returns a dict consumed by `write_invites` (T9) using the same key names. Verified.

---

# Execution Handoff

Plan complete. See execution log below for what actually happened when this plan ran.

---

# EXECUTION LOG (appended 2026-04-26)

Iteration 1 was executed via `superpowers:subagent-driven-development`. Each task was implemented by a fresh haiku subagent with TDD discipline, then reviewed by a spec-compliance subagent and a code-quality subagent (sonnet for the security-sensitive ones: T3 extractor, T4 push). T0 was executed directly by the controller because it had GitHub side-effects.

## Task status

| # | Task | Status | Final commit | Notes |
|---|---|---|---|---|
| T0 | Bootstrap (git, venv, mesh-data repo) | ✓ DONE | 58bbbea | Created sidpan1/mesh-data (private). mesh-skills repo NOT pushed to GitHub by user choice. |
| T1 | Schema | ✓ DONE | eedc78b | Frozen sets after code-quality review. |
| T2 | Validator | ✓ DONE | 96e2ce2 | Hardened to refuse malformed YAML frontmatter (missing closing `---`, empty FM, non-mapping). |
| T3 | Extractor | ✓ DONE | b9b3204, cdb29cb | **Critical fix:** original code read `conversation.jsonl` with flat `{role,content,ts}` structure; real Claude Code format is `<UUID>.jsonl` with nested `{type, message:{role,content:[{type:text,text}]}, timestamp}`. Tests passed against synthetic format but produced empty corpus on real data. Final review caught this; code rewritten to handle real format. Also expanded scrubbing: GitHub PATs (gh[pousr]_), AWS keys (AKIA*), `*_TOKEN`/`*_SECRET` env vars; URLs preserved through path-scrub via stash/restore. |
| T4 | Push script | ✓ DONE | 8e00c82, 25521e5 | Hardened: token scrubbed from stderr on git failure, `_authed_url` tested. **Then later replaced entirely** when the user dropped the PAT model — see "Mid-flight architectural change" below. |
| T5 | mesh-trajectory SKILL.md + summarize prompt | ✓ DONE | 4bfc124, cdb29cb | Added explicit `rm -f /tmp/mesh_corpus.txt` immediately after summarization. Switched all `python` invocations to absolute path `~/.claude/skills/mesh-skills/.venv/bin/python` because Claude Code bash runs from user's CWD, not skill dir. Added `~/.config/mesh/profile.yaml` persistence step so `/mesh-sync` doesn't re-ask Q&A. |
| T6 | render_invite | ✓ DONE | ac7d4e1 | Trivial; no review surfaced issues. |
| T7 | load_users | ✓ DONE | a7d0b43, cdb29cb | Added unquoted-ISO-date coercion (`str(s) for s in ...`) so hand-edited user files don't silently fail to match. |
| T8 | Compose prompt + parse_response | ✓ DONE | 33aff27, 0795f41 | **Important fix:** original code rejected tables of size != 6 or 7 even when `low_quorum: true`, contradicting the prompt that says "if total < 12, output one table only". Added low_quorum branch (size 2-7), type-checks for tables/attendees being lists, support for ` ``` ` and `~~~` fences (with/without language tag). |
| T9 | write_invites | ✓ DONE | 1273653 | Trivial. |
| T10 | mesh-orchestrator SKILL.md | ✓ DONE | fb6f3db, 25521e5 | Initially injected MESH_GH_TOKEN; later removed when auth model changed. |
| T11 | ONBOARD.md | ✓ DONE | c10de4e, 25521e5 | Initially had PAT-collection step; later replaced with `git ls-remote` precheck. Visible founder reminder block added at top (must be removed before distribution). |
| T12 | Dogfood with 5 friends | ⏸ NOT DONE | — | Manual; never recruited. Self-onboard (Phase 2 of verification) hit the bias problem before reaching 5-friend stage. |
| T13 | Launch event prep | ⏸ NOT DONE | — | Manual; pending. |

## What worked

- **TDD discipline + subagent-driven dispatch.** Per-task implementer + spec reviewer + code-quality reviewer caught real defects every cycle. Spec reviewers caught zero false positives; code-quality reviewers each found at least one Important fix that the implementer missed.
- **Frozen sets** for schema constants. One-line change, prevents a whole class of contract-corruption bugs.
- **Validator-before-write** in `push.py`. The privacy gate has not been bypassable in any iteration.
- **Token scrub in stderr.** Defensive; not strictly necessary against current GitHub git versions but cheap insurance.
- **End-of-iteration sub-Claude review of the entire branch.** This is what caught the showstopper extractor bug (synthetic test format ≠ real Claude Code format). Without this, dogfood would have produced empty corpora on every friend's machine.

## What didn't work

- **Synthetic test data masked a real-world incompatibility.** The original `test_extract.py` constructed jsonl in a flat `{role, content, timestamp}` shape that bore no resemblance to actual Claude Code session files. All tests passed; the code did not work. **Lesson: when reading user-machine data, write at least one test that reads against a real fixture from the user's actual `~/.claude/projects/`.** Only the final-review pass (sonnet, end-to-end) caught this — per-task reviewers had no incentive to question the test fixture format.
- **The summarize prompt is biased toward "how" over "why".** Self-onboard run produced a stack-heavy 230-word body (DeepAgentsJS, LangGraph, MCP, Fly.io). User flagged: "It seems too technical (the how) rather than the intent (the what and why)". Two root causes: (1) the corpus only captures debugging *transactions* with Claude, not the user's underlying *intent*; (2) the prompt's "maximize semantic density" constraint unintentionally rewards stack words because they ARE dense. **This blocked the dogfood.**
- **Single-shot summarization over a 60K corpus** loses signal in the noise. Frequency of mention (LangGraph appears 30+ times) gets pattern-matched as importance, even when the underlying activity (multi-tenant agent platform productionization) is what actually matters.
- **Spec.md deferred recursive memory consolidation to V0.1.** This was the wrong call given the bias problem above. Should have shipped recursive summarization in V0.

## Hardenings applied beyond the original plan

- Frozen schema sets (T1)
- Validator refuses malformed YAML frontmatter cleanly (T2)
- Extractor: real Claude Code format (T3, post-final-review)
- Extractor: GitHub PAT, AWS key, _TOKEN/_SECRET env-var scrubbing (T3, code-quality review)
- Extractor: URL preservation through path scrub (T3, code-quality review)
- Push: token redacted from stderr (T4)
- Push: `_authed_url` test coverage (T4) — later removed with auth model change
- parse_response: `low_quorum` size relaxation, type-checks (T8, code-quality review)
- parse_response: `~~~` fences, language-tag-less fences (T8)
- load_users: unquoted-ISO-date coercion (T7, post-final-review)
- SKILL.md: absolute python path; profile.yaml persistence; corpus deletion at step 7 not at end (T5, post-final-review)
- ONBOARD.md: token persistence to `~/.config/mesh/env` sourced from .zshrc/.bashrc (T11) — later removed with auth model change

## Mid-flight architectural change: dropped MESH_GH_TOKEN

After T11, user instructed: "assume the user has git installed in his local setup. So we will be using that instead, not anything else. Just check and flag if they don't have access." Implemented:

- Removed `_authed_url`, `_scrub_token`, MESH_GH_TOKEN env-var handling from push.py
- Added `check_repo_access(repo_url)` using `git ls-remote --exit-code` with a user-friendly "ping the founder for access" error
- Removed PAT step from ONBOARD.md, replaced with one-line `git ls-remote` precheck
- Removed token injection from orchestrator SKILL.md push step
- Replaced 4 PAT/scrub tests with 3 access-precheck tests (using local file:// bare repo so no network)

Net: 5 PAT tests removed, 3 access tests added → 49 total tests passing.

## Verification result

| Phase | Outcome |
|---|---|
| Phase 1: code-level smoke (4 commands) | ✓ All four green: 49 tests pass; `git ls-remote` reaches mesh-data; extract on real corpus produces 61KB; render_invite formats cleanly. |
| Phase 2: self-onboard as user #1 | ✗ Stopped at trajectory body review. The body was technically valid (passes validator: 233 words, all schema fields, Bengaluru, no extra fields) but failed the product test: too "how", not enough "why". User declined to push. |
| Phase 3: orchestrator dry-run | ⏸ Not attempted (Phase 2 blocked first). |

## Open items handed off to plan 02

- **Recursive summarization** (per-session → synthesis) to fix the intent-vs-stack bias.
- **Intent-first prompt rewrite** (`summarize.md`) demanding WHO and WHY before WHAT.
- **User "why" seed question** added to `/mesh-onboard` so the user can directly inject their motivation (the model can't infer it from debugging chatter alone).
- Re-run Phase 2 verification after the above land.
- Then T12 (dogfood with 5 friends) and T13 (launch event prep) become unblocked.
- One ops item: push `mesh-skills` to public GitHub before sending ONBOARD.md to anyone.
- One ops item: remove the founder pre-launch reminder block at the top of ONBOARD.md before distribution.

