"""AST helpers shared by ground truth and the traditional (grep) arm.

Core job: given a file and a line number, determine which function *encloses*
that line, and produce a normalized key so results from three very different
sources (jedi, the ContextAI graph, and grep) can be compared apples-to-apples.

Normalized key = "<relpath>::<simple_name>", where a line that sits at module
scope (outside any def) maps to "<relpath>::<module>".
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


def relpath(root: Path, file: Path) -> str:
    return str(Path(file).resolve().relative_to(Path(root).resolve()))


def key(rel: str, simple_name: str) -> str:
    return f"{rel}::{simple_name}"


@dataclass
class FuncDef:
    name: str          # simple name (last component)
    qualname: str      # Class.method style
    lineno: int
    end_lineno: int
    name_col: int      # column where the def name starts (for jedi positioning)


def function_defs(source: str) -> list[FuncDef]:
    """All function/method definitions in a module, with line ranges."""
    tree = ast.parse(source)
    out: list[FuncDef] = []

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qual = f"{prefix}{child.name}"
                # column of the name = def keyword col + len("def "/"async def ")
                kw = "async def " if isinstance(child, ast.AsyncFunctionDef) else "def "
                out.append(
                    FuncDef(
                        name=child.name,
                        qualname=qual,
                        lineno=child.lineno,
                        end_lineno=getattr(child, "end_lineno", child.lineno),
                        name_col=child.col_offset + len(kw),
                    )
                )
                walk(child, qual + ".")
            elif isinstance(child, ast.ClassDef):
                walk(child, f"{prefix}{child.name}.")
            else:
                walk(child, prefix)

    walk(tree, "")
    return out


def enclosing_name(defs: list[FuncDef], line: int) -> str:
    """Innermost function containing `line`, or '<module>' if none."""
    best: FuncDef | None = None
    for d in defs:
        if d.lineno <= line <= d.end_lineno:
            if best is None or d.lineno > best.lineno:  # innermost = latest start
                best = d
    return best.name if best else "<module>"


def enclosing_key(root: Path, file: Path, line: int, source: str | None = None) -> str:
    if source is None:
        source = Path(file).read_text(encoding="utf-8", errors="replace")
    try:
        defs = function_defs(source)
    except SyntaxError:
        defs = []
    return key(relpath(root, file), enclosing_name(defs, line))
