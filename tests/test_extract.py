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
