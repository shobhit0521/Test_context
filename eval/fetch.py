"""Fetch/pin target codebases into eval/_repos/<name>.

Clones git repos at a pinned ref (shallow), or copies installed packages for the
local "dogfood" target. Idempotent: re-running reuses an existing checkout.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from repos import REPOS, Repo

HERE = Path(__file__).resolve().parent
REPOS_DIR = HERE / "_repos"


def source_dir(repo: Repo) -> Path:
    """Absolute path to the source that build_graph / ground truth should analyze."""
    return (REPOS_DIR / repo.name / repo.source_subpath).resolve()


def _copy_local_packages(repo: Repo, dest: Path) -> None:
    import importlib.util

    dest.mkdir(parents=True, exist_ok=True)
    for pkg in repo.local_packages:
        spec = importlib.util.find_spec(pkg)
        if not spec or not spec.origin:
            raise RuntimeError(f"cannot locate installed package '{pkg}'")
        pkg_dir = Path(spec.origin).parent
        target = dest / pkg
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(
            pkg_dir, target,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )


def fetch(repo: Repo) -> Path:
    root = REPOS_DIR / repo.name
    if repo.local_packages:
        if not root.exists():
            _copy_local_packages(repo, root)
        return source_dir(repo)

    if root.exists():
        return source_dir(repo)

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
            print(f"{r.name:12} -> {path}  ({n_py} .py files)")


if __name__ == "__main__":
    main()
