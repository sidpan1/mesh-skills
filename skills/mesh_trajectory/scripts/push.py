"""Validator-gated git push to mesh-data repo.

Flow:
  1. Validate frontmatter + body via validate_payload (raises ValidationError).
  2. Write users/<slugified-email>.md inside a working clone of mesh-data.
  3. Stage, commit, push.

Auth model: trusts the user's local git. We do NOT inject any tokens. If the
local git auth (gh CLI, credential helper, SSH key, etc.) does not have access
to the repo, `check_repo_access` raises PushAborted with a clear message
telling the user to ask the repo owner for access.

Aborts with PushAborted on git/auth/network failures.
The validator gate runs BEFORE any disk write that could be pushed.
"""
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


def check_repo_access(repo_url: str) -> None:
    """Verify local git can reach the repo. Raises PushAborted with a friendly
    message if not — typically because the user hasn't been granted access yet.
    Uses `git ls-remote --exit-code` which is read-only and non-interactive."""
    res = subprocess.run(
        ["git", "ls-remote", "--exit-code", repo_url, "HEAD"],
        capture_output=True, text=True,
    )
    if res.returncode != 0:
        raise PushAborted(
            f"cannot access {repo_url}.\n"
            f"Your local git auth does not have permission to read this repo. "
            f"Ask the founder to grant you access, then re-run.\n"
            f"(Tip: `gh auth status` shows your current GitHub auth.)\n"
            f"git error: {res.stderr.strip()}"
        )


def push_to_mesh_data(repo_url: str, frontmatter: dict, body: str, workdir: Path) -> str:
    """Clone (or pull) mesh-data into workdir, write file, push. Returns commit SHA.
    Trusts local git auth; verifies access first."""
    check_repo_access(repo_url)
    if not (workdir / ".git").exists():
        _run(["git", "clone", repo_url, str(workdir)], cwd=Path.cwd())
    else:
        _run(["git", "remote", "set-url", "origin", repo_url], cwd=workdir)
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
