"""The three retrieval arms for "who calls function F?".

- traditional_only: what a grep-driven agent finds (text search + scope mapping).
- graph_only:       what the ContextAI graph's CALLS edges report.
- combined:         graph edges plus grep hits (the hero: graph precision anchor
                    + grep recall for the graph's dynamic/method blind spots).

Each arm returns (predicted_key_set, effort), where effort is a transparent
proxy for how much an agent must review: grep hits are unverified (every hit
must be checked), graph edges are pre-confirmed (0 to check).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import astutil
from graphutil import Graph


@dataclass
class ArmResult:
    predicted: set[str]
    effort: int  # number of candidate hits an agent must manually verify


def graph_only(graph: Graph, target_id: str) -> ArmResult:
    keys = graph.caller_keys(target_id)
    # Graph edges are typed + pre-resolved: an agent trusts them without review.
    return ArmResult(predicted=keys, effort=0)


def _grep_caller_hits(root: Path, func_name: str, target_relpath: str, def_line: int):
    """Yield (relpath-key) for every textual call-like hit of func_name."""
    pat = re.compile(rf"\b{re.escape(func_name)}\s*\(")
    def_pat = re.compile(rf"\bdef\s+{re.escape(func_name)}\b")
    hits: list[str] = []
    for f in root.rglob("*.py"):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = astutil.relpath(root, f)
        defs = None
        for i, line in enumerate(text.splitlines(), start=1):
            if not pat.search(line):
                continue
            if def_pat.search(line):
                continue  # the definition itself, not a call
            if rel == target_relpath and i == def_line:
                continue
            if defs is None:
                try:
                    defs = astutil.function_defs(text)
                except SyntaxError:
                    defs = []
            hits.append(astutil.key(rel, astutil.enclosing_name(defs, i)))
    return hits


def traditional_only(root: Path, func_name: str, target_relpath: str, def_line: int) -> ArmResult:
    hits = _grep_caller_hits(root, func_name, target_relpath, def_line)
    # Every raw grep hit is a candidate an agent must verify.
    return ArmResult(predicted=set(hits), effort=len(hits))


def combined(graph: Graph, target_id: str, root: Path, func_name: str,
             target_relpath: str, def_line: int) -> ArmResult:
    g = graph_only(graph, target_id)
    hits = _grep_caller_hits(root, func_name, target_relpath, def_line)
    predicted = set(g.predicted) | set(hits)
    # Graph-confirmed callers need no review; only grep extras do.
    extras_to_verify = len({h for h in hits} - g.predicted)
    return ArmResult(predicted=predicted, effort=extras_to_verify)
