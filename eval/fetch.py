"""Fetch/pin target codebases into eval/_repos/<name>.

Clones each repo at its pinned tag (shallow). Idempotent: an existing checkout
is reused.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from repos import REPOS, Repo

HERE = Path(__file__).resolve().parent
REPOS_DIR = HERE / "_repos"


def source_dir(repo: Repo) -> Path:
    """Absolute path to the source tree to analyze."""
    return (REPOS_DIR / repo.name / repo.source_subpath).resolve()


def fetch(repo: Repo) -> Path:
    root = REPOS_DIR / repo.name
    if not root.exists():
        root.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", repo.ref, repo.url, str(root)],
            check=True,
        )
    return source_dir(repo)


def main() -> None:
    names = sys.argv[1:] or [r.name for r in REPOS]
    for r in REPOS:
        if r.name in names:
            path = fetch(r)
            n_py = len(list(path.rglob("*.py")))
            print(f"{r.name:8} -> {path}  ({n_py} .py files)")


if __name__ == "__main__":
    main()
