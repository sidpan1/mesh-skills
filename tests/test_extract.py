import json
from datetime import datetime, timezone
from pathlib import Path
from skills.mesh_trajectory.scripts.extract import (
    Session,
    classify_bucket,
    extract_corpus,
    extract_per_session,
    group_by_project,
    normalize_slug,
    scrub_message,
)


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def _make_jsonl(path: Path, messages: list[dict]):
    """Write messages in the REAL Claude Code format: type + nested message{role,content}."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(m) for m in messages))


def _msg(type_: str, text: str, ts: str) -> dict:
    """Build a real-shape Claude Code log entry with a single text content block."""
    return {
        "type": type_,
        "timestamp": ts,
        "message": {
            "role": type_,
            "content": [{"type": "text", "text": text}],
        },
    }


def _msg_str(type_: str, text: str, ts: str) -> dict:
    """Build a real-shape entry with string-form content (some user messages do this)."""
    return {
        "type": type_,
        "timestamp": ts,
        "message": {"role": type_, "content": text},
    }


def test_extract_returns_only_user_and_assistant_text(tmp_path):
    proj = tmp_path / "proj-a" / "abc-uuid.jsonl"
    _make_jsonl(proj, [
        _msg("user", "How do I add streaming to my agent?", "2026-04-20T10:00:00Z"),
        _msg("assistant", "You can use Server-Sent Events.", "2026-04-20T10:00:05Z"),
        _msg("system", "<system note>", "2026-04-20T10:00:10Z"),
        {"type": "file-history-snapshot", "timestamp": "2026-04-20T10:00:15Z", "snapshot": "x"},
    ])
    corpus = extract_corpus(projects_root=tmp_path, weeks=4, now="2026-04-25T00:00:00Z")
    assert "streaming" in corpus
    assert "Server-Sent Events" in corpus
    assert "<system note>" not in corpus
    assert "[user]" in corpus
    assert "[assistant]" in corpus


def test_extract_drops_messages_older_than_window(tmp_path):
    proj = tmp_path / "proj-b" / "def-uuid.jsonl"
    _make_jsonl(proj, [
        _msg("user", "OLD MESSAGE", "2026-01-01T00:00:00Z"),
        _msg("user", "RECENT MESSAGE", "2026-04-22T00:00:00Z"),
    ])
    corpus = extract_corpus(projects_root=tmp_path, weeks=4, now="2026-04-25T00:00:00Z")
    assert "OLD MESSAGE" not in corpus
    assert "RECENT MESSAGE" in corpus


def test_extract_handles_string_and_list_content(tmp_path):
    proj = tmp_path / "proj-d" / "ghi-uuid.jsonl"
    _make_jsonl(proj, [
        _msg_str("user", "STRING CONTENT MESSAGE", "2026-04-22T10:00:00Z"),
        _msg("assistant", "LIST CONTENT MESSAGE", "2026-04-22T10:00:05Z"),
    ])
    corpus = extract_corpus(projects_root=tmp_path, weeks=4, now="2026-04-25T00:00:00Z")
    assert "STRING CONTENT MESSAGE" in corpus
    assert "LIST CONTENT MESSAGE" in corpus


def test_extract_skips_non_text_content_blocks(tmp_path):
    proj = tmp_path / "proj-e" / "jkl-uuid.jsonl"
    _make_jsonl(proj, [
        {
            "type": "assistant",
            "timestamp": "2026-04-22T10:00:00Z",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "SECRET PRIVATE THINKING"},
                    {"type": "tool_use", "name": "Bash", "input": {"command": "TOOL_USE_LEAK"}},
                    {"type": "text", "text": "VISIBLE ASSISTANT TEXT"},
                ],
            },
        },
        {
            "type": "user",
            "timestamp": "2026-04-22T10:00:05Z",
            "message": {
                "role": "user",
                "content": [
                    {"type": "tool_result", "content": "TOOL_RESULT_LEAK"},
                ],
            },
        },
    ])
    corpus = extract_corpus(projects_root=tmp_path, weeks=4, now="2026-04-25T00:00:00Z")
    assert "VISIBLE ASSISTANT TEXT" in corpus
    assert "SECRET PRIVATE THINKING" not in corpus
    assert "TOOL_USE_LEAK" not in corpus
    assert "TOOL_RESULT_LEAK" not in corpus


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


def test_scrub_strips_github_pats_and_aws_keys():
    msg = (
        "token ghp_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA and "
        "AWS AKIAIOSFODNN7EXAMPLE and "
        "GITHUB_TOKEN=ghp_BBBBBBBBBBBBBBBBBBBBBBBBBBBBBB and "
        "MY_SECRET=hunter2hunter2"
    )
    out = scrub_message(msg)
    assert "ghp_AAAA" not in out
    assert "AKIAIOSFODNN7EXAMPLE" not in out
    assert "ghp_BBBB" not in out
    assert "hunter2" not in out


def test_scrub_does_not_mangle_https_urls():
    msg = "see https://api.github.com/repos/foo/bar/issues/1 for context"
    out = scrub_message(msg)
    assert "https://api.github.com/repos/foo/bar/issues/1" in out
    assert "[path]" not in out


def test_corpus_is_capped_to_max_chars(tmp_path):
    proj = tmp_path / "proj-c" / "mno-uuid.jsonl"
    _make_jsonl(proj, [
        _msg("user", "long " * 10000, "2026-04-22T00:00:00Z"),
    ])
    corpus = extract_corpus(projects_root=tmp_path, weeks=4, now="2026-04-25T00:00:00Z", max_chars=5000)
    assert len(corpus) <= 5000


def test_extract_per_session_returns_one_corpus_per_session(tmp_path):
    proj = tmp_path / "proj-a"
    _make_jsonl(proj / "uuid-aaa.jsonl", [
        _msg("user", "session A msg 1", "2026-04-22T10:00:00Z"),
        _msg("assistant", "session A msg 2", "2026-04-22T10:00:05Z"),
    ])
    _make_jsonl(proj / "uuid-bbb.jsonl", [
        _msg("user", "session B msg 1", "2026-04-23T10:00:00Z"),
    ])
    sessions = extract_per_session(projects_root=tmp_path, weeks=4, now="2026-04-25T00:00:00Z", min_corpus_chars=0)
    assert len(sessions) == 2
    assert sessions[0].session_id == "uuid-bbb"
    assert sessions[1].session_id == "uuid-aaa"
    assert "session B msg 1" in sessions[0].corpus
    assert "session A msg 1" in sessions[1].corpus


def test_extract_per_session_skips_sessions_outside_window(tmp_path):
    proj = tmp_path / "proj"
    _make_jsonl(proj / "old.jsonl", [
        _msg("user", "OLD", "2026-01-01T00:00:00Z"),
    ])
    _make_jsonl(proj / "new.jsonl", [
        _msg("user", "NEW", "2026-04-22T00:00:00Z"),
    ])
    sessions = extract_per_session(projects_root=tmp_path, weeks=4, now="2026-04-25T00:00:00Z", min_corpus_chars=0)
    assert len(sessions) == 1
    assert sessions[0].session_id == "new"


def test_extract_per_session_drops_empty_sessions(tmp_path):
    proj = tmp_path / "proj"
    _make_jsonl(proj / "noise.jsonl", [
        {"type": "system", "timestamp": "2026-04-22T10:00:00Z", "message": {"role": "system", "content": "noise"}},
        {"type": "file-history-snapshot", "timestamp": "2026-04-22T10:00:01Z", "snapshot": "x"},
    ])
    sessions = extract_per_session(projects_root=tmp_path, weeks=4, now="2026-04-25T00:00:00Z")
    assert sessions == []


def test_extract_per_session_drops_sessions_below_min_corpus_chars(tmp_path):
    proj = tmp_path / "proj"
    _make_jsonl(proj / "tiny.jsonl", [
        _msg("user", "hi", "2026-04-22T10:00:00Z"),
    ])
    _make_jsonl(proj / "real.jsonl", [
        _msg("user", "x" * 600, "2026-04-22T10:00:00Z"),
    ])
    sessions = extract_per_session(
        projects_root=tmp_path, weeks=4, now="2026-04-25T00:00:00Z",
        min_corpus_chars=500,
    )
    assert len(sessions) == 1
    assert sessions[0].session_id == "real"


def test_extract_per_session_excludes_named_projects(tmp_path):
    (tmp_path / "subagents").mkdir()
    (tmp_path / "real-proj").mkdir()
    _make_jsonl(tmp_path / "subagents" / "noise.jsonl", [
        _msg("user", "x" * 600, "2026-04-22T10:00:00Z"),
    ])
    _make_jsonl(tmp_path / "real-proj" / "real.jsonl", [
        _msg("user", "x" * 600, "2026-04-22T10:00:00Z"),
    ])
    sessions = extract_per_session(
        projects_root=tmp_path, weeks=4, now="2026-04-25T00:00:00Z",
        exclude_projects={"subagents"},
    )
    assert len(sessions) == 1
    assert sessions[0].project_slug == "real-proj"


def test_extract_per_session_caps_to_max_sessions_keeping_most_recent(tmp_path):
    proj = tmp_path / "proj"
    for i in range(5):
        _make_jsonl(proj / f"s{i}.jsonl", [
            _msg("user", "x" * 600, f"2026-04-{20 + i:02d}T10:00:00Z"),
        ])
    sessions = extract_per_session(
        projects_root=tmp_path, weeks=4, now="2026-04-25T00:00:00Z",
        max_sessions=3,
    )
    assert len(sessions) == 3
    assert [s.session_id for s in sessions] == ["s4", "s3", "s2"]


def test_normalize_slug_strips_user_home_prefix():
    assert normalize_slug("-Users-sidhant-workspaces-root-workspace-mesh") == "mesh"
    assert normalize_slug("-Users-alice-projects-foo-bar") == "foo-bar"
    # macOS encodes "." as "-" in the user-home segment; usernames can therefore
    # contain hyphens. Anchor on workspaces-root-workspace- / projects-, not on
    # a single-segment username.
    assert normalize_slug("-Users-sidhant-panda-workspaces-root-workspace-mesh") == "mesh"


def test_normalize_slug_extracts_leaf_under_monorepo():
    """sage-workspaces is a parent monorepo; leaf projects sit under -workspaces-projects-/-workspaces-external-/-workspaces-personal-."""
    assert normalize_slug(
        "-Users-sidhant-panda-workspaces-root-workspace-sage-workspaces-workspaces-projects-software-farms-poc"
    ) == "software-farms-poc"
    assert normalize_slug(
        "-Users-sidhant-panda-workspaces-root-workspace-sage-workspaces-workspaces-projects-managed-agents-platform"
    ) == "managed-agents-platform"
    assert normalize_slug(
        "-Users-sidhant-panda-workspaces-root-workspace-sage-workspaces-workspaces-external-sia-claude"
    ) == "sia-claude"
    assert normalize_slug(
        "-Users-sidhant-panda-workspaces-root-workspace-sage-workspaces-workspaces-personal-sidhant-panda"
    ) == "sidhant-panda"


def test_normalize_slug_keeps_monorepo_root_when_no_leaf_segment():
    """Sessions run in the monorepo root (not a leaf project) keep the monorepo name."""
    assert normalize_slug(
        "-Users-sidhant-panda-workspaces-root-workspace-sage-workspaces"
    ) == "sage-workspaces"


def test_normalize_slug_strips_claude_worktree_suffix():
    """Claude Code worktree slugs encode `--repos-<repo>--<branch>`; collapse to the base project."""
    assert normalize_slug(
        "-Users-sidhant-panda-workspaces-root-workspace-sage-workspaces-workspaces-projects-software-farms-poc--repos-sage-workspaces--sf-2-10-artifacts"
    ) == "software-farms-poc"
    assert normalize_slug(
        "-Users-sidhant-panda-workspaces-root-workspace-me-private-projects-hermes-admin--claude-worktrees-strange-archimedes-d871d7"
    ) == "me-private-projects-hermes-admin"


def test_group_by_project_collapses_sessions(tmp_path):
    sessions = [
        Session(session_id="a", project_slug="-Users-x-mesh", last_seen=_dt("2026-04-26"), corpus="x" * 600),
        Session(session_id="b", project_slug="-Users-x-mesh", last_seen=_dt("2026-04-25"), corpus="x" * 600),
        Session(session_id="c", project_slug="-Users-x-chat", last_seen=_dt("2026-04-24"), corpus="x" * 600),
    ]
    groups = group_by_project(sessions)
    assert set(groups.keys()) == {"mesh", "chat"}
    assert len(groups["mesh"]) == 2
    assert groups["mesh"][0].session_id == "a"


def test_classify_bucket_returns_one_of_four_labels():
    assert classify_bucket(25) == "CENTRAL"
    assert classify_bucket(10) == "REGULAR"
    assert classify_bucket(3) == "OCCASIONAL"
    assert classify_bucket(1) == "ONE-OFF"


def test_classify_bucket_thresholds_inclusive():
    assert classify_bucket(20) == "CENTRAL"
    assert classify_bucket(19) == "REGULAR"
    assert classify_bucket(5) == "REGULAR"
    assert classify_bucket(4) == "OCCASIONAL"
    assert classify_bucket(2) == "OCCASIONAL"
