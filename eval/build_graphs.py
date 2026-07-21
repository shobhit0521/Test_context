"""Build the ContextAI code graph for every target repo, once, up front —
using Codex itself to call the real `build_graph` MCP tool.

Important: this harness never talks to the contextai-graph MCP server
directly. ContextAI access is exclusively Codex's — the coding tool under
test — so every interaction with it (including this one-time graph build)
goes through a real `codex exec` call in the Arm B ("with_mcp") CODEX_HOME.
Every Codex response (full JSONL transcript + result summary) is saved under
eval/results/graph_builds/, per the same "store every Codex answer" policy
used for the query runner (see codex_runner.py).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import codex_env
from fetch import source_dir
from repos import REPOS, Repo

HERE = Path(__file__).resolve().parent
GRAPHS_DIR = HERE / "_graphs"
RESULTS_DIR = HERE / "results" / "graph_builds"
BUILD_TIMEOUT_S = 240


def build_one(repo: Repo, force: bool = False) -> dict:
    out = GRAPHS_DIR / f"{repo.name}.json"
    result_path = RESULTS_DIR / f"{repo.name}.json"

    if out.exists() and not force:
        record = {"repo": repo.name, "skipped": True, "output": str(out)}
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(record, indent=2))
        return record

    root = source_dir(repo)
    prompt = (
        "Call the contextai-graph MCP tool `build_graph` with "
        f'project_root="{root}" and output="{out}". '
        "Report the raw tool result verbatim, then stop."
    )
    env = codex_env.subprocess_env()
    env["CODEX_HOME"] = str(codex_env.WITH_MCP_HOME)
    cmd = [
        "codex",
        "exec",
        "--json",
        "--dangerously-bypass-approvals-and-sandbox",
        "--skip-git-repo-check",
        "-C",
        str(HERE),  # safe cwd, never inside a target repo (see codex_env.py)
        prompt,
    ]

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        cmd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=BUILD_TIMEOUT_S,
    )
    record = {
        "repo": repo.name,
        "project_root": str(root),
        "output": str(out),
        "returncode": proc.returncode,
        "stdout_transcript": proc.stdout,
        "stderr_tail": proc.stderr[-3000:],
        "graph_created": out.exists(),
    }
    result_path.write_text(json.dumps(record, indent=2))
    return record


def build_all(force: bool = False) -> None:
    codex_env.ensure_setup()
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    for repo in REPOS:
        record = build_one(repo, force=force)
        if record.get("skipped"):
            status = "skipped (exists)"
        elif record.get("graph_created"):
            status = "ok"
        else:
            status = "FAILED"
        print(f"{repo.name:8} -> {status}")


if __name__ == "__main__":
    import sys

    build_all(force="--force" in sys.argv)
