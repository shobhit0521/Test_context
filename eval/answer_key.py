"""Objective ground-truth answer keys for callers / callees / impact queries.

These keys let us score the LLM's *stated* answer without a judge. Built from
jedi (trusted static resolution) and the code graph's CALLS edges. Keys use the
same normalized "<relpath>::<simple_name>" form as the rest of the harness.
"""

from __future__ import annotations

import ast
import functools
from pathlib import Path

import jedi

import astutil
import groundtruth
from graphutil import Graph, node_key


def resolve_focus(graph: Graph, focus: str) -> dict | None:
    """Map a query 'focus' like 'Flask.make_response' to a graph FUNCTION node."""
    simple = focus.split(".")[-1].strip()
    cls = focus.split(".")[0].strip() if "." in focus else None
    cands = [n for n in graph.function_nodes() if n.get("name") == simple]
    if not cands:
        return None
    if cls:
        for n in cands:
            parts = n["id"].split("::")
            if cls in parts:  # e.g. "src.../app.py::Flask::make_response"
                return n
    return cands[0]


def _defloc(root: Path, node: dict):
    loc = node.get("location") or {}
    rel = loc.get("file_path")
    approx = loc.get("line_start")
    if not (rel and approx):
        return None
    src = (root / rel).read_text(encoding="utf-8", errors="replace")
    cands = [d for d in astutil.function_defs(src) if d.name == node["name"]]
    if not cands:
        return None
    fd = min(cands, key=lambda d: abs(d.lineno - approx))
    return rel, fd, src


def callers(root: Path, graph: Graph, node: dict) -> set[str]:
    dl = _defloc(root, node)
    if not dl:
        return set()
    rel, fd, _ = dl
    return groundtruth.caller_keys(root, rel, fd.lineno, fd.name_col, node["name"])


def callees(root: Path, graph: Graph, node: dict) -> set[str]:
    dl = _defloc(root, node)
    if not dl:
        return set()
    rel, fd, src = dl
    abs_file = root / rel
    script = jedi.Script(src, path=str(abs_file), project=jedi.Project(str(root)))
    tree = ast.parse(src)
    out: set[str] = set()
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        if not (fd.lineno <= getattr(f, "lineno", 0) <= fd.end_lineno):
            continue
        if isinstance(f, ast.Name):
            line, col = f.lineno, f.col_offset
        elif isinstance(f, ast.Attribute):
            line, col = f.end_lineno, f.end_col_offset - len(f.attr)
        else:
            continue
        try:
            defs = script.goto(line, col, follow_imports=True)
        except Exception:
            continue
        for d in defs:
            mp = d.module_path
            if not mp:
                continue
            try:
                Path(mp).resolve().relative_to(root)
            except ValueError:
                continue
            out.add(astutil.key(astutil.relpath(root, Path(mp)), d.name))
    out.discard(astutil.key(rel, node["name"]))  # drop self-recursion
    return out


@functools.lru_cache(maxsize=8)
def _symbol_index(root_str: str) -> dict[tuple[str, str], astutil.FuncDef]:
    """Map (relpath, simple_name) -> its FuncDef, across the repo (jedi-independent)."""
    root = Path(root_str)
    idx: dict[tuple[str, str], astutil.FuncDef] = {}
    for f in root.rglob("*.py"):
        if f.name.startswith("test_") or f.name.endswith("_test.py"):
            continue
        try:
            src = f.read_text(encoding="utf-8", errors="replace")
            defs = astutil.function_defs(src)
        except (OSError, SyntaxError):
            continue
        rel = astutil.relpath(root, f)
        for d in defs:
            idx.setdefault((rel, d.name), d)  # first def wins on rare name dup
    return idx


def _callers_of_key(root: Path, key: str, index: dict) -> set[str]:
    if "::" not in key:
        return set()
    rel, name = key.rsplit("::", 1)
    if name == "<module>":
        return set()
    fd = index.get((rel, name))
    if fd is None:
        return set()
    return groundtruth.caller_keys(root, rel, fd.lineno, fd.name_col, name)


def impact(root: Path, graph: Graph, node: dict) -> set[str]:
    """Transitive reverse reachability via jedi: everything that (in)directly
    calls `node`. Independent of the graph (uses jedi at each hop); bounded for
    safety."""
    index = _symbol_index(str(root))
    start = node_key(node["id"])
    seen: set[str] = set()
    frontier = [start]
    depth = 0
    while frontier and depth < 8 and len(seen) < 300:
        nxt: list[str] = []
        for k in frontier:
            for c in _callers_of_key(root, k, index):
                if c not in seen and c != start:
                    seen.add(c)
                    nxt.append(c)
        frontier = nxt
        depth += 1
    return seen


KEY_BUILDERS = {"callers": callers, "callees": callees, "impact": impact}


def build(root: Path, graph: Graph, query: dict) -> set[str] | None:
    """Return the ground-truth key set for an objective query, or None if the
    query type isn't objectively scorable (flow / definition / feature)."""
    builder = KEY_BUILDERS.get(query["type"])
    if builder is None:
        return None
    node = resolve_focus(graph, query["focus"])
    if node is None:
        return None
    keys = builder(root, graph, node)
    # Drop module-scope entries: the eval asks "which functions", and the model
    # answers with function names, so "<module>" keys aren't matchable.
    return {k for k in keys if not k.endswith("::<module>")}
