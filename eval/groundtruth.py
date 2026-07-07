"""Ground-truth caller resolution via jedi.

jedi performs real static analysis (import/alias/scope resolution with type
inference), well beyond text matching, so we treat its resolved references as
the reference answer for "which functions call F". This is independent of the
system under test (the ContextAI graph) and of the grep baseline.
"""

from __future__ import annotations

import functools
from pathlib import Path

import jedi

import astutil


@functools.lru_cache(maxsize=8)
def _project(root: str) -> jedi.Project:
    return jedi.Project(root)


def _is_call_site(source: str, line: int, col: int, name: str) -> bool:
    """True if the reference at (line, col) is a call: `name(` or `obj.name(`."""
    lines = source.splitlines()
    if not (1 <= line <= len(lines)):
        return False
    text = lines[line - 1]
    after = text[col + len(name):]
    return after.lstrip().startswith("(")


def caller_keys(root: Path, target_relpath: str, name_line: int, name_col: int,
                func_name: str) -> set[str]:
    """Return normalized keys of every function that *calls* the target.

    We ask jedi for all references to the target definition, drop the definition
    itself and non-call references (imports, decorators, value passing), keep
    in-repo call sites, and map each to its enclosing function.
    """
    root = Path(root).resolve()
    target_abs = root / target_relpath
    src = target_abs.read_text(encoding="utf-8", errors="replace")
    script = jedi.Script(src, path=str(target_abs), project=_project(str(root)))

    try:
        refs = script.get_references(name_line, name_col, include_builtins=False)
    except Exception:
        return set()

    _source_cache: dict[Path, str] = {}
    callers: set[str] = set()
    for ref in refs:
        if ref.is_definition():
            continue
        mod = ref.module_path
        if not mod:
            continue
        mod = Path(mod).resolve()
        try:
            mod.relative_to(root)
        except ValueError:
            continue  # reference lives outside the analyzed source tree
        if mod not in _source_cache:
            _source_cache[mod] = mod.read_text(encoding="utf-8", errors="replace")
        if not _is_call_site(_source_cache[mod], ref.line, ref.column, func_name):
            continue  # not an actual call (import / decorator / value use)
        callers.add(astutil.enclosing_key(root, mod, ref.line))
    return callers
