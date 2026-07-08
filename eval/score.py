"""Objective precision/recall/F1 scoring for callers/callees/impact queries.

Uses the existing jedi-based ground-truth engine (answer_key.py) — independent
of both arms — against the structured `symbols` list Codex reported in its
answer (see codex_runner.py's schema-constrained output).
"""

from __future__ import annotations

import json
from pathlib import Path

import answer_key
from fetch import source_dir
from graphutil import Graph
import repos as repos_mod

HERE = Path(__file__).resolve().parent
GRAPHS_DIR = HERE / "_graphs"
RESULTS_RAW_DIR = HERE / "results" / "raw"
RESULTS_SCORED_DIR = HERE / "results" / "scored"


def normalize_model_symbols(symbols: list[dict]) -> set[str]:
    out = set()
    for s in symbols or []:
        file = (s.get("file") or "").strip().lstrip("./")
        name = (s.get("name") or "").strip()
        if not file or not name:
            continue
        simple = name.split(".")[-1]
        out.add(f"{file}::{simple}")
    return out


def prf1(predicted: set[str], gold: set[str]) -> dict:
    if not predicted and not gold:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "tp": 0, "fp": 0, "fn": 0}
    tp = len(predicted & gold)
    fp = len(predicted - gold)
    fn = len(gold - predicted)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


_graph_cache: dict[str, Graph] = {}
_key_cache: dict[tuple, set[str] | None] = {}


def _graph_for(repo_name: str) -> Graph:
    if repo_name not in _graph_cache:
        _graph_cache[repo_name] = Graph(str(GRAPHS_DIR / f"{repo_name}.json"))
    return _graph_cache[repo_name]


def ground_truth_for(query: dict) -> set[str] | None:
    cache_key = (query["repo"], query["id"])
    if cache_key in _key_cache:
        return _key_cache[cache_key]
    repo = repos_mod.get(query["repo"])
    root = source_dir(repo)
    graph = _graph_for(repo.name)
    keys = answer_key.build(root, graph, query)
    _key_cache[cache_key] = keys
    return keys


def score_all(queries: list[dict], repeats: int) -> list[dict]:
    RESULTS_SCORED_DIR.mkdir(parents=True, exist_ok=True)
    scored = []
    for q in queries:
        gold = ground_truth_for(q)
        if gold is None:
            continue  # not an objectively-scorable query type or focus unresolved
        for arm in ("A", "B"):
            for r in range(repeats):
                raw_path = RESULTS_RAW_DIR / f"{q['id']}__{arm}__r{r}.json"
                if not raw_path.exists():
                    continue
                raw = json.loads(raw_path.read_text())
                if not raw.get("ok"):
                    continue
                predicted = normalize_model_symbols(raw.get("symbols", []))
                metrics = prf1(predicted, gold)
                record = {
                    "query_id": q["id"],
                    "repo": q["repo"],
                    "type": q["type"],
                    "arm": arm,
                    "repeat": r,
                    "gold": sorted(gold),
                    "predicted": sorted(predicted),
                    **metrics,
                }
                scored.append(record)
                out_path = RESULTS_SCORED_DIR / f"{q['id']}__{arm}__r{r}.json"
                out_path.write_text(json.dumps(record, indent=2))
    return scored


if __name__ == "__main__":
    import sys

    queries = json.loads((HERE / "queries.json").read_text())["queries"]
    repeats = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    results = score_all(queries, repeats)
    print(f"Scored {len(results)} (query, arm, repeat) records.")
    by_arm: dict[str, list[float]] = {"A": [], "B": []}
    for r in results:
        by_arm[r["arm"]].append(r["f1"])
    for arm, f1s in by_arm.items():
        if f1s:
            print(f"  Arm {arm}: mean F1 = {sum(f1s) / len(f1s):.3f} over {len(f1s)} runs")
