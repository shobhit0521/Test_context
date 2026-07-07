"""Target codebases for the evaluation.

Each entry pins a repo to a tag/commit for reproducibility and points at the
directory that actually holds the Python source to analyze. `contextai` is a
local "dogfood" target copied from the installed packages (no network needed).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Repo:
    name: str
    # Either a git url + ref, or local=True to copy installed packages.
    url: str | None = None
    ref: str | None = None
    # Path (relative to the clone root) that contains the source to analyze.
    source_subpath: str = "."
    local_packages: list[str] = field(default_factory=list)


REPOS: list[Repo] = [
    Repo(
        name="requests",
        url="https://github.com/psf/requests",
        ref="v2.32.3",
        source_subpath="src/requests",
    ),
    Repo(
        name="flask",
        url="https://github.com/pallets/flask",
        ref="3.0.3",
        source_subpath="src/flask",
    ),
    Repo(
        name="click",
        url="https://github.com/pallets/click",
        ref="8.1.7",
        source_subpath="src/click",
    ),
    # Dogfood: analyze ContextAI's own source (copied from installed packages).
    Repo(
        name="contextai",
        local_packages=["graph", "contextai_mcp"],
        source_subpath=".",
    ),
]


def get(name: str) -> Repo:
    for r in REPOS:
        if r.name == name:
            return r
    raise KeyError(name)
