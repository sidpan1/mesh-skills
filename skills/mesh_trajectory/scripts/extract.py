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
