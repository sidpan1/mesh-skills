"""Read ~/.claude/projects/<project>/<session-uuid>.jsonl, scrub, return a corpus.

The corpus is what local Claude reads to write the trajectory summary.
Only user + assistant text, scrubbed of paths and API-key shapes.

Real Claude Code session-log shape:
    {
      "type": "user" | "assistant" | "system" | "file-history-snapshot" | ...,
      "timestamp": "2026-03-06T08:10:48.513Z",
      "message": { "role": "user" | "assistant", "content": str | [ {type, ...} ] },
      ...
    }
We keep only type ∈ {user, assistant} and extract only `text` blocks (skip
`thinking`, `tool_use`, `tool_result` — those leak filesystem state and PII).
"""
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_PROJECTS_ROOT = Path.home() / ".claude" / "projects"
DEFAULT_WEEKS = 4
DEFAULT_MAX_CHARS = 60_000

# URLs are stashed before path-scrub so https://host/path/segments isn't
# mangled into https:/[path]. After path-scrub they're restored verbatim.
_URL_RE = re.compile(r"\bhttps?://\S+")
_PATH_RE = re.compile(r"(/[A-Za-z0-9_\-./~]+){2,}")

# Covers: OpenAI/Anthropic sk- keys, GitHub PAT/OAuth/server/refresh/user
# tokens (gh[pousr]_), AWS access key IDs (AKIA + 16 alnum), and ENV-style
# assignments where the variable name ends in _API_KEY, _TOKEN, or _SECRET.
_KEY_RE = re.compile(
    r"("
    r"sk-[A-Za-z0-9_\-]{12,}"
    r"|gh[pousr]_[A-Za-z0-9]{20,}"
    r"|AKIA[A-Z0-9]{16}"
    r"|[A-Z][A-Z0-9_]+_(?:API_KEY|TOKEN|SECRET)=\S+"
    r")"
)


def scrub_message(text: str) -> str:
    text = _KEY_RE.sub("[redacted-key]", text)
    urls: list[str] = []

    def _stash(m: re.Match) -> str:
        urls.append(m.group(0))
        return f"\x00URL{len(urls) - 1}\x00"

    text = _URL_RE.sub(_stash, text)
    text = _PATH_RE.sub("[path]", text)
    for i, u in enumerate(urls):
        text = text.replace(f"\x00URL{i}\x00", u)
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
    for jsonl in sorted(projects_root.rglob("*.jsonl")):
        for line in jsonl.read_text().splitlines():
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("type") not in ("user", "assistant"):
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
            text = _extract_text(msg.get("message"))
            if not text.strip():
                continue
            chunks.append(f"[{msg['type']}] {scrub_message(text)}")

    corpus = "\n\n".join(chunks)
    return corpus[:max_chars]


@dataclass
class Session:
    session_id: str
    project_slug: str
    last_seen: datetime
    corpus: str


DEFAULT_EXCLUDE_PROJECTS = frozenset({"subagents"})


_WORKSPACE_ROOT_ANCHOR = "workspaces-root-workspace-"
_PROJECTS_ANCHOR = "projects-"
_LEAF_SEGMENTS = (
    "-workspaces-projects-",
    "-workspaces-external-",
    "-workspaces-personal-",
)


def normalize_slug(slug: str) -> str:
    """Collapse path-encoded slug to logical project name.

    Strips the leading '-Users-<name>-' user-home path (usernames may contain
    hyphens because macOS encodes '.' as '-' in slugs, e.g. 'sidhant.panda'
    becomes 'sidhant-panda'), drops Claude Code worktree '--'-suffix encodings,
    and extracts the leaf project under monorepo subpaths
    '-workspaces-(projects|external|personal)-'.
    """
    s = slug.lstrip("-")
    if s.startswith("Users-"):
        s = s[len("Users-"):]
        anchor_idx = s.find(_WORKSPACE_ROOT_ANCHOR)
        if anchor_idx != -1:
            s = s[anchor_idx + len(_WORKSPACE_ROOT_ANCHOR):]
        else:
            proj_idx = s.find(_PROJECTS_ANCHOR)
            if proj_idx != -1:
                s = s[proj_idx + len(_PROJECTS_ANCHOR):]
            else:
                dash_idx = s.find("-")
                if dash_idx != -1:
                    s = s[dash_idx + 1:]

    dd_idx = s.find("--")
    if dd_idx != -1:
        s = s[:dd_idx]

    for seg in _LEAF_SEGMENTS:
        idx = s.find(seg)
        if idx != -1:
            s = s[idx + len(seg):]
            break

    return s


def group_by_project(sessions: list[Session]) -> dict[str, list[Session]]:
    """Group sessions by normalized project slug, most-recent-first within group."""
    groups: dict[str, list[Session]] = {}
    for s in sessions:
        key = normalize_slug(s.project_slug)
        groups.setdefault(key, []).append(s)
    for key in groups:
        groups[key].sort(key=lambda s: s.last_seen, reverse=True)
    return groups


def classify_bucket(session_count: int) -> str:
    """Return CENTRAL (>=20) | REGULAR (5-19) | OCCASIONAL (2-4) | ONE-OFF (1)."""
    if session_count >= 20:
        return "CENTRAL"
    if session_count >= 5:
        return "REGULAR"
    if session_count >= 2:
        return "OCCASIONAL"
    return "ONE-OFF"


def extract_per_session(
    projects_root: Path = DEFAULT_PROJECTS_ROOT,
    weeks: int = DEFAULT_WEEKS,
    now: str | None = None,
    max_chars_per_session: int = 8_000,
    min_corpus_chars: int = 500,
    max_sessions: int = 200,
    exclude_projects: frozenset[str] | set[str] | None = None,
) -> list[Session]:
    cutoff = (
        _parse_ts(now) if now else datetime.now(timezone.utc)
    ) - timedelta(weeks=weeks)
    if exclude_projects is None:
        exclude_projects = DEFAULT_EXCLUDE_PROJECTS

    sessions: list[Session] = []
    for jsonl in sorted(projects_root.rglob("*.jsonl")):
        if jsonl.parent.name in exclude_projects:
            continue
        chunks: list[str] = []
        last_seen: datetime | None = None
        for line in jsonl.read_text().splitlines():
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("type") not in ("user", "assistant"):
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
            text = _extract_text(msg.get("message"))
            if not text.strip():
                continue
            chunks.append(f"[{msg['type']}] {scrub_message(text)}")
            if last_seen is None or ts > last_seen:
                last_seen = ts

        if not chunks or last_seen is None:
            continue

        corpus = "\n\n".join(chunks)[:max_chars_per_session]
        if len(corpus) < min_corpus_chars:
            continue
        sessions.append(Session(
            session_id=jsonl.stem,
            project_slug=jsonl.parent.name,
            last_seen=last_seen,
            corpus=corpus,
        ))

    sessions.sort(key=lambda s: s.last_seen, reverse=True)
    return sessions[:max_sessions]


def _extract_text(inner) -> str:
    if not isinstance(inner, dict):
        return ""
    content = inner.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                t = item.get("text", "")
                if isinstance(t, str):
                    parts.append(t)
        return " ".join(parts)
    return ""


def main() -> int:
    print(extract_corpus())
    return 0


if __name__ == "__main__":
    sys.exit(main())
