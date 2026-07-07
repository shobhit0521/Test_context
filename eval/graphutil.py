"""Helpers for reading the ContextAI graph JSON and normalizing node ids.

Node ids look like "<relpath>::<name>". We normalize them to the same key
scheme used by astutil so graph results compare directly against jedi ground
truth and grep results.
"""

from __future__ import annotations

import json
from pathlib import Path


def node_key(node_id: str) -> str:
    """Map a graph node id to a normalized "<relpath>::<simple_name>" key.

    Ids look like "<relpath>::<name>" for module-level functions and
    "<relpath>::<Class>::<method>" (or "Class.method") for methods.
    """
    if "::" not in node_id:
        return node_id
    parts = node_id.split("::")
    rel = parts[0]
    name = parts[-1]
    if name in ("__file__", "__main__", "module"):
        return f"{rel}::<module>"
    simple = name.split(".")[-1]  # handle Class.method form too
    return f"{rel}::{simple}"


class Graph:
    def __init__(self, path: str):
        data = json.loads(Path(path).read_text())
        self.nodes = data.get("nodes", [])
        self.edges = data.get("edges", [])
        self._by_id = {n["id"]: n for n in self.nodes}

    def function_nodes(self) -> list[dict]:
        return [n for n in self.nodes if n.get("type") == "FUNCTION"]

    def degree(self, node_id: str) -> int:
        return sum(
            1 for e in self.edges if e.get("from") == node_id or e.get("to") == node_id
        )

    def caller_keys(self, target_id: str) -> set[str]:
        """Keys of functions that CALL target_id, per the graph's edges."""
        out: set[str] = set()
        for e in self.edges:
            if e.get("to") == target_id and e.get("type") == "CALLS":
                src = e.get("from")
                if src:
                    out.add(node_key(src))
        return out
