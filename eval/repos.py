"""Target codebases for the real-LLM evaluation.

Four major, widely-used Python projects, each pinned to a release tag for
reproducibility, each in the ~9k-26k LOC range. `source_subpath` points at the
importable package directory (build_graph and the agents analyze this tree).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Repo:
    name: str
    url: str
    ref: str
    source_subpath: str  # dir (relative to clone root) holding the package source
    loc: int             # approx non-test LOC (for reporting)


REPOS: list[Repo] = [
    Repo("flask", "https://github.com/pallets/flask", "3.0.3", "src/flask", 9024),
    Repo("click", "https://github.com/pallets/click", "8.1.7", "src/click", 10124),
    Repo("httpx", "https://github.com/encode/httpx", "0.27.0", "httpx", 9033),
    Repo("rich", "https://github.com/Textualize/rich", "v13.7.1", "rich", 26427),
]


def get(name: str) -> Repo:
    for r in REPOS:
        if r.name == name:
            return r
    raise KeyError(name)
