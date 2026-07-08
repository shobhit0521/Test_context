"""Runs one (query, arm, repeat) through the real Codex CLI (`codex exec`).

Arm A = Codex's native tools only (shell/read/apply_patch).
Arm B = the same, plus the contextai-graph MCP server.

Both arms run with `--dangerously-bypass-approvals-and-sandbox`. This is a
deliberate, documented trade-off: Codex's non-interactive mode currently has
no way to non-interactively approve MCP tool calls (they auto-cancel — see
https://github.com/openai/codex/issues/24135), so Arm B needs the bypass to
function at all. Applying it uniformly to Arm A too keeps the *only*
difference between arms the tool set (contextai-graph present or absent),
which is the variable we're actually testing (METRICS.md's bias-control
principle). We only run this against pinned, throwaway clones of well-known
open-source repos with read-oriented questions, so the reduced sandboxing is
an acceptable, contained risk.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import codex_env
import repos as repos_mod
from fetch import source_dir

HERE = Path(__file__).resolve().parent
GRAPHS_DIR = HERE / "_graphs"
RESULTS_RAW_DIR = HERE / "results" / "raw"
SCHEMA_PATH = HERE / "answer_schema.json"
TRANSCRIPTS_DIR = HERE / "results" / "transcripts"

DEFAULT_TIMEOUT_S = 300

OBJECTIVE_SYMBOL_HINTS = {
    "callers": "every function that (directly) calls the focal symbol",
    "callees": "every function/method the focal symbol (directly) calls",
    "impact": "every function that directly or transitively calls the focal symbol (its full blast radius)",
}


def _symbols_instruction(query_type: str) -> str:
    hint = OBJECTIVE_SYMBOL_HINTS.get(query_type)
    if hint is None:
        return "Leave this as an empty array `[]` for this question type."
    return (
        f"List {hint}, each as {{\"file\": <path relative to the project root>, "
        '"name": <simple function/method name, e.g. "wsgi_app" not "Flask.wsgi_app">}. '
        "Only include functions defined in this codebase (skip stdlib/third-party calls). "
        "If there are none, use an empty array."
    )


def build_prompt(query: dict, arm: str, graph_path: Path | None) -> str:
    symbols_instr = _symbols_instruction(query["type"])
    lines = [
        f'You are answering a code-understanding question about the "{query["repo"]}" '
        "open-source Python codebase. Your current working directory IS the root of the "
        "codebase you should analyze — do not `cd` elsewhere.",
        "",
        f"Question: {query['question']}",
        "",
    ]
    if arm == "B":
        lines += [
            "You have access to the `contextai-graph` MCP server's tools "
            "(find_node, get_context, get_edge_path, list_gaps, load_graph). "
            f"A code graph for this exact repo has already been built at `{graph_path}` — "
            "prefer these tools with that graph_path over manually grepping/reading files.",
            "",
        ]
    lines += [
        "Respond with your final answer as the schema-constrained JSON object with two fields:",
        '- "answer": a clear, well-cited prose answer referencing the real files/functions you found.',
        f'- "symbols": {symbols_instr}',
        "",
        "Be efficient: use as few tool calls as you reasonably can while still being correct.",
    ]
    return "\n".join(lines)


@dataclass
class RunResult:
    query_id: str
    arm: str
    repeat: int
    ok: bool
    answer: str = ""
    symbols: list[dict] = field(default_factory=list)
    num_tool_calls: int = 0
    num_mcp_tool_calls: int = 0
    used_contextai: bool = False
    tool_names: list[str] = field(default_factory=list)
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0
    latency_s: float = 0.0
    model: str = ""
    error: str | None = None
    transcript_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__


def _parse_transcript(text: str) -> dict[str, Any]:
    events = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    tool_calls = []
    used_contextai = False
    usage = {}
    model = ""
    for ev in events:
        et = ev.get("type")
        if et == "item.completed":
            item = ev.get("item", {})
            it = item.get("type")
            if it == "mcp_tool_call":
                tool_calls.append(item.get("tool", "mcp_tool"))
                if item.get("server") == "contextai-graph":
                    used_contextai = True
            elif it in ("command_execution", "exec_command", "function_call"):
                tool_calls.append(it)
        elif et == "turn.completed":
            usage = ev.get("usage", {}) or {}
        elif et == "turn.failed":
            pass
        if ev.get("model"):
            model = ev["model"]

    return {
        "tool_calls": tool_calls,
        "used_contextai": used_contextai,
        "usage": usage,
        "model": model,
        "events": events,
    }


def run_query(
    query: dict,
    arm: str,
    repeat: int,
    timeout_s: int = DEFAULT_TIMEOUT_S,
) -> RunResult:
    repo = repos_mod.get(query["repo"])
    project_root = source_dir(repo)
    graph_path = GRAPHS_DIR / f"{repo.name}.json"

    prompt = build_prompt(query, arm, graph_path if arm == "B" else None)
    codex_home = codex_env.codex_home_for(arm)

    run_id = uuid.uuid4().hex[:8]
    last_message_path = TRANSCRIPTS_DIR / f"{query['id']}__{arm}__r{repeat}__{run_id}.msg.json"
    transcript_path = TRANSCRIPTS_DIR / f"{query['id']}__{arm}__r{repeat}__{run_id}.jsonl"
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    env = codex_env.subprocess_env()
    env["CODEX_HOME"] = str(codex_home)

    cmd = [
        "codex",
        "exec",
        "--json",
        "--dangerously-bypass-approvals-and-sandbox",
        "--skip-git-repo-check",
        "-C",
        str(project_root),
        "--output-schema",
        str(SCHEMA_PATH),
        "-o",
        str(last_message_path),
        prompt,
    ]

    result = RunResult(query_id=query["id"], arm=arm, repeat=repeat, ok=False)
    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as e:
        result.error = f"timeout after {timeout_s}s"
        result.latency_s = time.monotonic() - start
        transcript_path.write_text((e.stdout or "") if isinstance(e.stdout, str) else "")
        result.transcript_path = str(transcript_path)
        return result

    result.latency_s = time.monotonic() - start
    transcript_path.write_text(proc.stdout)
    result.transcript_path = str(transcript_path)

    parsed = _parse_transcript(proc.stdout)
    result.num_tool_calls = len(parsed["tool_calls"])
    result.tool_names = parsed["tool_calls"]
    result.num_mcp_tool_calls = sum(
        1 for t in parsed["tool_calls"]
        if t in ("find_node", "get_context", "get_edge_path", "list_gaps", "load_graph", "build_graph")
    )
    result.used_contextai = parsed["used_contextai"]
    usage = parsed["usage"]
    result.input_tokens = usage.get("input_tokens", 0)
    result.cached_input_tokens = usage.get("cached_input_tokens", 0)
    result.output_tokens = usage.get("output_tokens", 0)
    result.reasoning_output_tokens = usage.get("reasoning_output_tokens", 0)
    result.model = parsed["model"] or "gpt-5-codex"

    if last_message_path.exists() and last_message_path.stat().st_size > 0:
        try:
            payload = json.loads(last_message_path.read_text())
            result.answer = payload.get("answer", "")
            result.symbols = payload.get("symbols", [])
            result.ok = True
        except json.JSONDecodeError:
            result.error = "failed to parse structured last message"
    else:
        result.error = f"no last message written (exit code {proc.returncode}); stderr: {proc.stderr[-2000:]}"

    return result


def result_path(query_id: str, arm: str, repeat: int) -> Path:
    return RESULTS_RAW_DIR / f"{query_id}__{arm}__r{repeat}.json"


def run_and_save(query: dict, arm: str, repeat: int, force: bool = False) -> Path:
    out_path = result_path(query["id"], arm, repeat)
    if out_path.exists() and not force:
        return out_path
    RESULTS_RAW_DIR.mkdir(parents=True, exist_ok=True)
    result = run_query(query, arm, repeat)
    out_path.write_text(json.dumps(result.to_dict(), indent=2))
    return out_path


if __name__ == "__main__":
    import sys

    codex_env.ensure_setup()
    queries = json.loads((HERE / "queries.json").read_text())["queries"]
    qid = sys.argv[1] if len(sys.argv) > 1 else "flask-01"
    arm = sys.argv[2] if len(sys.argv) > 2 else "B"
    q = next(q for q in queries if q["id"] == qid)
    r = run_query(q, arm, repeat=0)
    print(json.dumps(r.to_dict(), indent=2))
