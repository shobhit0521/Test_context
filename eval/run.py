"""Run the evaluation across target codebases.

For each repo:
  1. build the ContextAI graph via the real MCP `build_graph` tool,
  2. sample focal functions (most-connected -> the ones agents actually ask about),
  3. for each focal function with >=1 real caller, compute the caller set three
     ways (graph_only, traditional_only=grep, combined) and score each against
     jedi ground truth,
  4. write per-question detail + aggregates to eval/results/<repo>.json.

Usage:  python run.py [--sample N] [repo ...]
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import arms
import astutil
import groundtruth
import metrics
from fetch import fetch
from graphutil import Graph
from mcp_client import graph_session
from repos import REPOS, get

HERE = Path(__file__).resolve().parent
GRAPHS_DIR = HERE / "_graphs"
RESULTS_DIR = HERE / "results"
ARMS = ("graph_only", "traditional_only", "combined")


def _resolve_def(source: str, name: str, approx_line: int):
    """Find the FuncDef for `name` nearest to approx_line (handles decorators)."""
    candidates = [d for d in astutil.function_defs(source) if d.name == name]
    if not candidates:
        return None
    return min(candidates, key=lambda d: abs(d.lineno - approx_line))


async def build_all(repo_names: list[str]) -> dict[str, str]:
    """Build graphs for the given repos; return {repo: graph_path}."""
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    async with graph_session() as client:
        for name in repo_names:
            repo = get(name)
            src = str(fetch(repo))
            out = str(GRAPHS_DIR / f"{name}.json")
            stats = await client.build_graph(src, out)
            print(f"[build] {name}: {stats.get('nodes')} nodes, {stats.get('edges')} edges")
            paths[name] = out
    return paths


def evaluate_repo(name: str, graph_path: str, sample: int) -> dict:
    repo = get(name)
    root = fetch(repo)
    graph = Graph(graph_path)

    focal = graph.function_nodes()
    focal = [n for n in focal if graph.degree(n["id"]) > 0]
    focal.sort(key=lambda n: graph.degree(n["id"]), reverse=True)
    focal = focal[:sample]

    per_question = []
    for node in focal:
        node_id = node["id"]
        loc = node.get("location") or {}
        rel = loc.get("file_path")
        fname = node.get("name")
        approx_line = loc.get("line_start")
        if not (rel and fname and approx_line):
            continue
        abs_file = root / rel
        try:
            source = abs_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fd = _resolve_def(source, fname, approx_line)
        if fd is None:
            continue
        line, col = fd.lineno, fd.name_col

        truth = groundtruth.caller_keys(root, rel, line, col, fname)
        if not truth:
            continue  # only score functions that actually have callers

        results = {
            "graph_only": arms.graph_only(graph, node_id),
            "traditional_only": arms.traditional_only(root, fname, rel, line),
            "combined": arms.combined(graph, node_id, root, fname, rel, line),
        }
        entry = {
            "node_id": node_id,
            "name": fname,
            "file": rel,
            "degree": graph.degree(node_id),
            "n_truth_callers": len(truth),
            "arms": {},
        }
        for arm, res in results.items():
            prf = metrics.score(res.predicted, truth)
            entry["arms"][arm] = {
                "precision": round(prf.precision, 4),
                "recall": round(prf.recall, 4),
                "f1": round(prf.f1, 4),
                "effort": res.effort,
                "tp": prf.tp, "fp": prf.fp, "fn": prf.fn,
            }
        per_question.append(entry)

    aggregate = _aggregate(per_question)
    return {"repo": name, "n_questions": len(per_question),
            "aggregate": aggregate, "questions": per_question}


def _aggregate(per_question: list[dict]) -> dict:
    agg: dict[str, dict] = {}
    for arm in ARMS:
        agg[arm] = {
            "precision": round(metrics.mean([q["arms"][arm]["precision"] for q in per_question]), 4),
            "recall": round(metrics.mean([q["arms"][arm]["recall"] for q in per_question]), 4),
            "f1": round(metrics.mean([q["arms"][arm]["f1"] for q in per_question]), 4),
            "effort": round(metrics.mean([q["arms"][arm]["effort"] for q in per_question]), 3),
        }
    return agg


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=40, help="focal functions per repo")
    ap.add_argument("repos", nargs="*", help="repo names (default: all)")
    args = ap.parse_args()

    names = args.repos or [r.name for r in REPOS]
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    graph_paths = asyncio.run(build_all(names))

    for name in names:
        result = evaluate_repo(name, graph_paths[name], args.sample)
        out = RESULTS_DIR / f"{name}.json"
        out.write_text(json.dumps(result, indent=2))
        a = result["aggregate"]
        print(f"\n=== {name} ({result['n_questions']} questions) ===")
        print(f"{'arm':18} {'precision':>10} {'recall':>8} {'f1':>8} {'effort':>8}")
        for arm in ARMS:
            m = a[arm]
            print(f"{arm:18} {m['precision']:>10} {m['recall']:>8} {m['f1']:>8} {m['effort']:>8}")


if __name__ == "__main__":
    main()
