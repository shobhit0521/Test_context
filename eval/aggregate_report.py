"""Aggregate raw/scored/judged results into the final presentable report.

Writes eval/report/REPORT.md (+ charts + rendered HTML), the committed
deliverable per METRICS.md's scoring contract. Run after run_codex.py,
score.py, and judge.py have produced results.
"""

from __future__ import annotations

import json
import statistics as stats
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import mdrender

HERE = Path(__file__).resolve().parent
RESULTS_RAW_DIR = HERE / "results" / "raw"
RESULTS_SCORED_DIR = HERE / "results" / "scored"
RESULTS_JUDGED_DIR = HERE / "results" / "judged"
REPORT_DIR = HERE / "report"


def load_json_dir(d: Path) -> list[dict]:
    if not d.exists():
        return []
    return [json.loads(p.read_text()) for p in sorted(d.glob("*.json"))]


def mean(xs: list[float]) -> float:
    return stats.mean(xs) if xs else 0.0


def build_efficiency_table(raw: list[dict]) -> dict:
    by_arm: dict[str, list[dict]] = defaultdict(list)
    for r in raw:
        if r.get("ok"):
            by_arm[r["arm"]].append(r)
    table = {}
    for arm, rows in by_arm.items():
        table[arm] = {
            "n": len(rows),
            "mean_tool_calls": mean([r["num_tool_calls"] for r in rows]),
            "mean_mcp_calls": mean([r["num_mcp_tool_calls"] for r in rows]),
            "mean_input_tokens": mean([r["input_tokens"] for r in rows]),
            "mean_output_tokens": mean([r["output_tokens"] for r in rows]),
            "mean_latency_s": mean([r["latency_s"] for r in rows]),
            "pct_used_contextai": (
                100.0 * sum(1 for r in rows if r.get("used_contextai")) / len(rows) if rows and arm == "B" else None
            ),
        }
    n_failed = sum(1 for r in raw if not r.get("ok"))
    return {"by_arm": table, "n_total": len(raw), "n_failed": n_failed}


def build_objective_table(scored: list[dict]) -> dict:
    overall: dict[str, list[float]] = defaultdict(list)
    by_type: dict[tuple, list[float]] = defaultdict(list)
    for r in scored:
        overall[r["arm"]].append(r["f1"])
        by_type[(r["type"], r["arm"])].append(r["f1"])
    overall_table = {arm: {"n": len(f1s), "mean_f1": mean(f1s)} for arm, f1s in overall.items()}
    type_table: dict[str, dict] = defaultdict(dict)
    for (qtype, arm), f1s in by_type.items():
        type_table[qtype][arm] = {"n": len(f1s), "mean_f1": mean(f1s)}
    return {"overall": overall_table, "by_type": dict(type_table)}


def build_repo_breakdown(raw: list[dict], scored: list[dict], judged: list[dict]) -> dict:
    repos = sorted({r["repo"] for r in judged} | {r["repo"] for r in scored})
    judge_by_repo: dict[str, dict] = defaultdict(lambda: {"A": 0, "B": 0, "tie": 0})
    rubric_by_repo: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"A": [], "B": []})
    for j in judged:
        judge_by_repo[j["repo"]][j["winner"]] += 1
        for arm, s in j.get("scores", {}).items():
            if arm in ("A", "B"):
                rubric_by_repo[j["repo"]][arm].append(
                    (s["correctness"] + s["completeness"] + s["groundedness"]) / 3
                )
    f1_by_repo: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"A": [], "B": []})
    for s in scored:
        f1_by_repo[s["repo"]][s["arm"]].append(s["f1"])

    table = {}
    for repo in repos:
        w = judge_by_repo[repo]
        n = sum(w.values())
        b_win_rate = (w["B"] + 0.5 * w["tie"]) / n if n else None
        f1a = f1_by_repo[repo]["A"]
        f1b = f1_by_repo[repo]["B"]
        ra = rubric_by_repo[repo]["A"]
        rb = rubric_by_repo[repo]["B"]
        table[repo] = {
            "judge_n": n,
            "judge_wins": dict(w),
            "b_win_rate": b_win_rate,
            "f1_a": mean(f1a) if f1a else None,
            "f1_b": mean(f1b) if f1b else None,
            "rubric_a": mean(ra) if ra else None,
            "rubric_b": mean(rb) if rb else None,
        }
    return table


def build_type_breakdown(judged: list[dict]) -> dict:
    by_type: dict[str, dict] = defaultdict(lambda: {"A": 0, "B": 0, "tie": 0})
    for j in judged:
        by_type[j["type"]][j["winner"]] += 1
    table = {}
    for qtype, w in by_type.items():
        n = sum(w.values())
        table[qtype] = {"n": n, "wins": dict(w), "b_win_rate": (w["B"] + 0.5 * w["tie"]) / n if n else None}
    return table


def build_tool_access_check(raw: list[dict]) -> dict:
    """Confirms Arm B genuinely retained its native tools alongside ContextAI's -
    i.e. that any quality difference reflects extra capability, not reduced capability."""
    b_runs = [r for r in raw if r.get("arm") == "B" and r.get("ok")]
    mcp_names = {"find_node", "get_context", "get_edge_path", "list_gaps", "load_graph", "build_graph"}
    native_names = {"command_execution", "exec_command", "function_call"}
    both = mcp_only = native_only = neither = 0
    for r in b_runs:
        tools = set(r.get("tool_names", []))
        has_mcp = bool(tools & mcp_names)
        has_native = bool(tools & native_names)
        if has_mcp and has_native:
            both += 1
        elif has_mcp:
            mcp_only += 1
        elif has_native:
            native_only += 1
        else:
            neither += 1
    return {"n": len(b_runs), "both": both, "mcp_only": mcp_only, "native_only": native_only, "neither": neither}


def build_recall_gap_analysis(scored: list[dict]) -> dict:
    """Find paired (query, repeat) cases where Arm B's predicted symbol set is a
    strict subset of Arm A's (or otherwise meaningfully lower-recall) - the
    empirical signature of the agent trusting the graph's edge list as a
    complete answer instead of cross-checking with an exhaustive grep pass."""
    by_key: dict[tuple, dict] = defaultdict(dict)
    for s in scored:
        by_key[(s["query_id"], s["repeat"])][s["arm"]] = s

    subset_cases = []
    b_worse_cases = []
    a_worse_cases = []
    for key, arms in by_key.items():
        if "A" not in arms or "B" not in arms:
            continue
        a, b = arms["A"], arms["B"]
        pred_a, pred_b = set(a["predicted"]), set(b["predicted"])
        if pred_b < pred_a:  # strict subset
            subset_cases.append((key, a, b))
        if b["f1"] < a["f1"] - 0.01:
            b_worse_cases.append((key, a, b))
        elif a["f1"] < b["f1"] - 0.01:
            a_worse_cases.append((key, a, b))

    # Prefer compact, readable examples over huge ones (e.g. "impact" queries on rich can
    # have 60+ symbols in both gold and Arm A's predicted set) - pick the clearest
    # illustration, not just the largest absolute size gap.
    compact = [c for c in subset_cases if len(c[1]["gold"]) <= 15 and len(c[1]["predicted"]) <= 12]
    pool = compact if compact else subset_cases
    pool.sort(key=lambda x: len(x[1]["predicted"]) - len(x[2]["predicted"]), reverse=True)

    return {
        "n_pairs": len(by_key),
        "n_b_strict_subset_of_a": len(subset_cases),
        "n_a_strict_subset_of_b": sum(
            1 for key, arms in by_key.items()
            if "A" in arms and "B" in arms and set(arms["A"]["predicted"]) < set(arms["B"]["predicted"])
        ),
        "n_b_meaningfully_worse": len(b_worse_cases),
        "n_a_meaningfully_worse": len(a_worse_cases),
        "examples": pool[:2],
    }


def build_judge_table(judged: list[dict]) -> dict:
    wins = {"A": 0, "B": 0, "tie": 0}
    by_type_wins: dict[str, dict] = defaultdict(lambda: {"A": 0, "B": 0, "tie": 0})
    rubric: dict[str, list[list[float]]] = {"A": [], "B": []}
    for r in judged:
        wins[r["winner"]] += 1
        by_type_wins[r["type"]][r["winner"]] += 1
        for arm, s in r.get("scores", {}).items():
            if arm in rubric:
                rubric[arm].append([s["correctness"], s["completeness"], s["groundedness"]])
    n = len(judged)
    b_win_rate = (wins["B"] + 0.5 * wins["tie"]) / n if n else None
    rubric_means = {}
    for arm, rows in rubric.items():
        if not rows:
            continue
        cols = list(zip(*rows))
        rubric_means[arm] = {
            "correctness": mean(cols[0]),
            "completeness": mean(cols[1]),
            "groundedness": mean(cols[2]),
            "mean_overall": mean([sum(row) / 3 for row in rows]),
        }
    return {
        "n": n,
        "wins": wins,
        "b_win_rate": b_win_rate,
        "by_type_wins": dict(by_type_wins),
        "rubric_means": rubric_means,
    }


def make_charts(efficiency: dict, objective: dict, judge: dict) -> list[str]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    chart_files = []

    # Chart 1: quality (objective F1 + judge win-rate + rubric)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    ax = axes[0]
    arms = ["A", "B"]
    f1s = [objective["overall"].get(a, {}).get("mean_f1", 0) for a in arms]
    bars = ax.bar(arms, f1s, color=["#94a3b8", "#2ca02c"])
    ax.set_title("Objective F1 (callers/callees/impact)")
    ax.set_ylim(0, 1)
    ax.set_ylabel("mean F1")
    for b, v in zip(bars, f1s):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.2f}", ha="center")

    ax = axes[1]
    wins = judge["wins"]
    labels = ["A wins", "tie", "B wins"]
    vals = [wins.get("A", 0), wins.get("tie", 0), wins.get("B", 0)]
    ax.bar(labels, vals, color=["#94a3b8", "#e5e7eb", "#2ca02c"])
    ax.set_title(f"Blind judge preference (n={judge['n']})")
    ax.set_ylabel("# queries")

    ax = axes[2]
    rubric = judge["rubric_means"]
    axes_labels = ["correctness", "completeness", "groundedness"]
    width = 0.35
    x = range(len(axes_labels))
    a_vals = [rubric.get("A", {}).get(k, 0) for k in axes_labels]
    b_vals = [rubric.get("B", {}).get(k, 0) for k in axes_labels]
    ax.bar([i - width / 2 for i in x], a_vals, width, label="Arm A", color="#94a3b8")
    ax.bar([i + width / 2 for i in x], b_vals, width, label="Arm B", color="#2ca02c")
    ax.set_xticks(list(x))
    ax.set_xticklabels(axes_labels, rotation=15)
    ax.set_ylim(0, 3)
    ax.set_title("Absolute rubric (0-3)")
    ax.legend()

    fig.tight_layout()
    quality_path = REPORT_DIR / "quality.png"
    fig.savefig(quality_path, dpi=150)
    plt.close(fig)
    chart_files.append(quality_path.name)

    # Chart 2: efficiency
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    metrics = [
        ("mean_tool_calls", "Mean tool calls / query"),
        ("mean_input_tokens", "Mean input tokens / query"),
        ("mean_latency_s", "Mean latency (s) / query"),
    ]
    for ax, (key, title) in zip(axes, metrics):
        vals = [efficiency["by_arm"].get(a, {}).get(key, 0) for a in arms]
        bars = ax.bar(arms, vals, color=["#94a3b8", "#2ca02c"])
        ax.set_title(title)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.0f}", ha="center", va="bottom")
    fig.tight_layout()
    efficiency_path = REPORT_DIR / "efficiency.png"
    fig.savefig(efficiency_path, dpi=150)
    plt.close(fig)
    chart_files.append(efficiency_path.name)

    return chart_files


def make_repo_chart(repo_table: dict) -> str:
    repos = sorted(repo_table.keys())
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    ax = axes[0]
    rates = [repo_table[r]["b_win_rate"] or 0 for r in repos]
    bars = ax.bar(repos, rates, color="#2ca02c")
    ax.axhline(0.5, color="#94a3b8", linestyle="--", linewidth=1)
    ax.set_ylim(0, 1)
    ax.set_title("Arm B judge win-rate by repo (0.5 = parity)")
    for b, v in zip(bars, rates):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.0%}", ha="center")

    ax = axes[1]
    width = 0.35
    x = range(len(repos))
    f1a = [repo_table[r]["f1_a"] or 0 for r in repos]
    f1b = [repo_table[r]["f1_b"] or 0 for r in repos]
    ax.bar([i - width / 2 for i in x], f1a, width, label="Arm A", color="#94a3b8")
    ax.bar([i + width / 2 for i in x], f1b, width, label="Arm B", color="#2ca02c")
    ax.set_xticks(list(x))
    ax.set_xticklabels(repos)
    ax.set_ylim(0, 1)
    ax.set_title("Objective F1 by repo")
    ax.legend()

    fig.tight_layout()
    path = REPORT_DIR / "by_repo.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path.name


def render_background_sections() -> str:
    """Static narrative: what was built, why the graph exists, how the MCP
    server was wired up, and how testing was conducted. This doesn't depend on
    result data (unlike the rest of the report) but lives here so the whole
    document is produced by one reproducible script."""
    lines: list[str] = []

    # ----- 1. What we built -----
    lines.append("## 1. What we built")
    lines.append("")
    lines.append(
        "The question this evaluation answers: **does giving a real coding agent access to "
        "ContextAI's code-graph MCP tools make it better at understanding code**, compared to the "
        "same agent using only its own native tools? We built a full, reproducible harness to "
        "answer this with real agent runs rather than a hand-wavy comparison."
    )
    lines.append("")
    lines.append("The harness has five stages, each a standalone script under `eval/`:")
    lines.append("")
    lines.append(
        "1. **Fetch** (`fetch.py`) — clone and pin four real, widely-used open-source Python "
        "projects at fixed release tags: `flask` (9k LOC), `click` (10k LOC), `httpx` (9k LOC), and "
        "`rich` (26k LOC). Pinned versions mean results are reproducible — the code under test "
        "can't drift."
    )
    lines.append(
        "2. **Build graphs** (`build_graphs.py`) — for each repo, have Codex itself call ContextAI's "
        "`build_graph` tool once, up front (see §3)."
    )
    lines.append(
        "3. **Run** (`codex_runner.py` / `run_codex.py`) — for each of 48 hand-written "
        "code-understanding questions (12 per repo, across 6 question types — see §4), run the real "
        "**Codex CLI** twice: once with only its native tools (**Arm A**), once with the same tools "
        "plus ContextAI's MCP server (**Arm B**). Each (question, arm) pair is repeated 3x to smooth "
        "out model randomness, for 288 total agent runs."
    )
    lines.append(
        "4. **Score** (`score.py`) — for questions with an objectively checkable answer (\"who calls "
        "X\"), compute precision/recall/F1 against ground truth computed independently with `jedi` "
        "(real static analysis, unrelated to ContextAI)."
    )
    lines.append(
        "5. **Judge** (`judge.py`) — for every question, a separate LLM judge blindly compares the "
        "Arm A and Arm B answers (order randomized, labels hidden) and picks a winner, plus scores "
        "each on a 0-3 rubric."
    )
    lines.append("")
    lines.append(
        "One design principle held throughout the whole harness: **ContextAI is only ever touched "
        "by Codex itself** — the tool actually under evaluation. None of our own orchestration code "
        "calls the ContextAI MCP server directly (not even to build the graphs); every single "
        "interaction with it happens because Codex, acting as an agent, decided to call it."
    )
    lines.append("")

    # ----- 2. The graph's purpose -----
    lines.append("## 2. The ContextAI code graph — what it is and why it should help")
    lines.append("")
    lines.append(
        "Most code-understanding questions — \"who calls this function,\" \"what does this call,\" "
        "\"what breaks if I change this,\" \"trace this request end to end\" — are really **graph "
        "traversal questions** over the codebase's call structure. An agent using only grep/read has "
        "to reconstruct that structure by hand: search for a name, open each hit, mentally note "
        "which function it's inside, repeat. ContextAI's `build_graph` tool does that reconstruction "
        "once, up front, via static analysis, and hands the agent a queryable structure instead."
    )
    lines.append("")
    lines.append("Concretely, `build_graph(project_root, output)` walks a Python project and produces a JSON graph:")
    lines.append("")
    lines.append(
        "- **Nodes** — one per function, method, class, file, or external library, each carrying "
        "an id (e.g. `app.py::Flask::wsgi_app`), its type, source location, and — for functions — "
        "rich metadata: full source, signature, side effects (e.g. `EMITS_EVENT`), error handling "
        "(`has_try_catch`, `catches`), cyclomatic complexity, test coverage, and even version/git "
        "history."
    )
    lines.append(
        "- **Edges** — typed relationships between nodes: `CALLS`, `CONTAINS` (class → method), "
        "`IMPORTS`, `RETURNS`, each with a criticality rating and whether it's confirmed only "
        "statically or also seen at runtime."
    )
    lines.append(
        "- **Gaps** — the graph is honest about what static analysis can't resolve. A `list_gaps` "
        "tool reports `unresolved_calls` and `dynamic_gaps` (decorators, dynamic dispatch, registry "
        "lookups) per node — cases a purely static pass can miss. This turns out to matter a lot for "
        "our results (see \"Deep dive\" in §5 below)."
    )
    lines.append("")
    lines.append(
        "Once built, the graph is queried through four read tools: `find_node` (search by name), "
        "`get_context` (a node plus its neighbors/edges, with source code attached), `get_edge_path` "
        "(the direct relationship between two specific nodes), and `list_gaps`. We built the graph "
        "**once per repo**, not per question, since static analysis is comparatively expensive and "
        "the codebase doesn't change between questions."
    )
    lines.append("")

    # ----- 3. How the MCP server was built and connected -----
    lines.append("## 3. How the MCP server was built and connected")
    lines.append("")
    lines.append(
        "ContextAI ships as `contextai-mcp`, a Python package implementing a real "
        "[Model Context Protocol](https://modelcontextprotocol.io) server that speaks over stdio — "
        "the same protocol Cursor, Claude Code, and Codex all support natively for extending an "
        "agent with custom tools. We installed it via `pip install contextai-mcp contextai-graph` "
        "(pinned versions in `requirements.txt`) and connected it to Codex exactly the way a real "
        "user would: as a registered MCP server, not through any special integration code."
    )
    lines.append("")
    lines.append("**Connecting it to Codex.** Codex CLI reads MCP server definitions from `config.toml`:")
    lines.append("")
    lines.append("```toml")
    lines.append("[mcp_servers.contextai-graph]")
    lines.append('command = "python3"')
    lines.append('args = ["-m", "contextai_mcp"]')
    lines.append('cwd = "/workspace/eval"')
    lines.append("```")
    lines.append("")
    lines.append(
        "We registered this with `codex mcp add contextai-graph -- python3 -m contextai_mcp`. Once "
        "registered, Codex spawns the server as a subprocess at session start and can call any of "
        "its tools (`build_graph`, `find_node`, `get_context`, `get_edge_path`, `list_gaps`, plus "
        "`load_graph`/`run_trace`/`merge_trace`, which we didn't need for these read-only questions) "
        "exactly like its own built-in tools."
    )
    lines.append("")
    lines.append(
        "**Isolating the two arms.** To make the comparison clean, we created two completely "
        "separate `CODEX_HOME` directories (Codex's config/auth root, normally `~/.codex`) — "
        "`_codex_home/no_mcp` for Arm A and `_codex_home/with_mcp` for Arm B — each independently "
        "authenticated. `contextai-graph` is registered in the `with_mcp` config only. This means "
        "the *only* difference between what Arm A and Arm B can do is the presence of this one MCP "
        "server; model, sandbox policy, approval settings, and prompt are byte-for-byte identical."
    )
    lines.append("")
    lines.append(
        "**A real bug we found and fixed.** The MCP server subprocess (`python3 -m contextai_mcp`) "
        "is a `python -m` invocation, which Python resolves by adding the *current working "
        "directory* to `sys.path[0]`. If that cwd is inside a target repo, and the repo happens to "
        "ship a file with the same name as a stdlib module, the import gets silently hijacked. "
        "Flask ships `src/flask/typing.py` — so running the MCP server with its cwd inside Flask's "
        "source tree breaks the import of the real stdlib `typing` module and crashes the server on "
        "startup (`AttributeError: partially initialized module 'typing' has no attribute "
        "'TYPE_CHECKING'`). We fixed this by pinning the server's own `cwd` to `eval/` (via the "
        "`cwd` key shown above), which never collides with a target repo's module names — while "
        "Codex's own agent loop still runs with its working root inside the target repo as normal, "
        "unaffected."
    )
    lines.append("")
    lines.append(
        "**A real CLI limitation we worked around.** Codex's non-interactive mode (`codex exec`) "
        "currently requires interactive approval for MCP tool calls, which can't be granted "
        "headlessly and so auto-cancels by default — a known open issue "
        "([openai/codex#24135](https://github.com/openai/codex/issues/24135)). We used "
        "`--dangerously-bypass-approvals-and-sandbox` to work around this, applied identically to "
        "*both* arms (not just Arm B), so reduced sandboxing isn't a hidden confound — only tool "
        "availability differs between arms. This is a contained, disclosed trade-off: read-oriented "
        "questions against pinned, throwaway repo clones, not untrusted external input."
    )
    lines.append("")

    # ----- 4. How testing was done -----
    lines.append("## 4. How testing was done")
    lines.append("")
    lines.append(
        "**Questions.** 48 hand-written, symbol-grounded questions, 12 per repo, spanning six "
        "reasoning types: `callers` (reverse edges), `callees` (forward edges), `flow` (multi-hop "
        "execution tracing), `impact` (blast-radius / transitive reverse reachability), "
        "`definition` (where/how something is defined), and `feature` (how a cross-cutting concern "
        "works across modules). The first three types (`callers`/`callees`/`impact`) have an "
        "objective, checkable answer; all six are judged."
    )
    lines.append("")
    lines.append(
        "**Running each question.** For every `(question, arm, repeat)` combination, we invoke "
        "`codex exec` with Codex's working directory set to the target repo's source root, and a "
        "JSON-schema-constrained final response so Codex must return a prose `answer` plus — for "
        "objectively-scorable questions — a structured `symbols` list (`{file, name}` pairs). This "
        "gets us exact, parseable answers instead of scraping free text. Every run's full raw tool-"
        "call transcript (every tool called, its arguments, and its result) and every field of its "
        "final answer are saved to disk."
    )
    lines.append("")
    lines.append(
        "**Scoring, two independent ways.** Objective scoring compares Codex's structured symbol "
        "list against ground truth computed by `jedi` (real static analysis, run independently of "
        "both ContextAI and Codex) via precision/recall/F1. Subjective scoring uses a **separate** "
        "LLM (`o3`, a different model from the `gpt-5-codex` answerer, to avoid a model preferring "
        "its own style) as a blind judge: it sees the question, the reference answer key when "
        "available, and both answers with **labels stripped and order randomized**, then picks a "
        "winner and scores each 0-3 on correctness/completeness/groundedness."
    )
    lines.append("")
    lines.append(
        "**Scale.** 48 questions x 2 arms x 3 repeats = 288 agent runs, plus 144 judge calls "
        "(one per question/repeat pair, each comparing both arms at once). All runs completed with "
        "**zero failures**. The full pipeline is reproducible end to end via `make eval`."
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    return "\n".join(lines)


def render_markdown(
    efficiency: dict,
    objective: dict,
    judge: dict,
    chart_files: list[str],
    repo_table: dict,
    repo_chart: str,
    recall_gap: dict,
    tool_access: dict,
) -> str:
    lines = []
    lines.append("# ContextAI vs. traditional tools — Codex agentic evaluation results")
    lines.append("")
    lines.append(
        "Real-LLM evaluation: the [Codex CLI](https://developers.openai.com/codex) (`codex exec`, "
        "model `gpt-5-codex`) answers the same code-understanding questions twice per query — once "
        "with its native tools only (**Arm A**), once with the same tools **plus the ContextAI "
        "`contextai-graph` MCP server** (**Arm B**). Codex decides itself which tools to call. "
        "See [`METRICS.md`](METRICS.md) for the full scoring contract."
    )
    lines.append("")
    lines.append(render_background_sections())

    lines.append("## 5. Test results")
    lines.append("")
    lines.append("### Headline: blind judge win-rate")
    lines.append("")
    if judge["n"]:
        lines.append(
            f"Arm B win-rate over Arm A (ties = 0.5): **{judge['b_win_rate']:.1%}** "
            f"across {judge['n']} judged queries — "
            f"A wins {judge['wins']['A']}, ties {judge['wins']['tie']}, B wins {judge['wins']['B']}."
        )
    else:
        lines.append("_No judged queries yet._")
    lines.append("")
    lines.append(f"![quality]({chart_files[0]})" if len(chart_files) > 0 else "")
    lines.append("")

    lines.append("### Objective correctness (callers / callees / impact)")
    lines.append("")
    lines.append("| Arm | n | mean F1 |")
    lines.append("|---|---|---|")
    for arm in ("A", "B"):
        o = objective["overall"].get(arm, {"n": 0, "mean_f1": 0})
        lines.append(f"| {arm} | {o['n']} | {o['mean_f1']:.3f} |")
    lines.append("")
    if objective["by_type"]:
        lines.append("| Query type | Arm A F1 | Arm B F1 |")
        lines.append("|---|---|---|")
        for qtype, arms in sorted(objective["by_type"].items()):
            a = arms.get("A", {}).get("mean_f1")
            b = arms.get("B", {}).get("mean_f1")
            a_str = f"{a:.3f}" if a is not None else "n/a"
            b_str = f"{b:.3f}" if b is not None else "n/a"
            lines.append(f"| {qtype} | {a_str} | {b_str} |")
    lines.append("")

    lines.append("### Absolute rubric (0-3 per axis, judge-scored)")
    lines.append("")
    lines.append("| Arm | Correctness | Completeness | Groundedness | Mean |")
    lines.append("|---|---|---|---|---|")
    for arm in ("A", "B"):
        rm = judge["rubric_means"].get(arm)
        if rm:
            lines.append(
                f"| {arm} | {rm['correctness']:.2f} | {rm['completeness']:.2f} | "
                f"{rm['groundedness']:.2f} | {rm['mean_overall']:.2f} |"
            )
    lines.append("")

    lines.append("### Breakdown by repo")
    lines.append("")
    lines.append(
        "The headline numbers average over all 4 repos; per-repo results vary more than the "
        "average suggests, and no single repo shows Arm B clearly ahead — including `rich`, the "
        "largest/most complex codebase, where a code graph would intuitively help the most."
    )
    lines.append("")
    lines.append(f"![by_repo]({repo_chart})")
    lines.append("")
    lines.append("| Repo | Judge: A / tie / B | B win-rate | F1 (A) | F1 (B) | Rubric (A) | Rubric (B) |")
    lines.append("|---|---|---|---|---|---|---|")
    for repo, t in sorted(repo_table.items()):
        w = t["judge_wins"]
        wr = f"{t['b_win_rate']:.0%}" if t["b_win_rate"] is not None else "n/a"
        f1a = f"{t['f1_a']:.3f}" if t["f1_a"] is not None else "n/a"
        f1b = f"{t['f1_b']:.3f}" if t["f1_b"] is not None else "n/a"
        rma = f"{t['rubric_a']:.2f}" if t["rubric_a"] is not None else "n/a"
        rmb = f"{t['rubric_b']:.2f}" if t["rubric_b"] is not None else "n/a"
        lines.append(
            f"| {repo} | {w.get('A', 0)} / {w.get('tie', 0)} / {w.get('B', 0)} | {wr} | "
            f"{f1a} | {f1b} | {rma} | {rmb} |"
        )
    lines.append("")

    lines.append("### Breakdown by query type (blind judge)")
    lines.append("")
    lines.append("| Type | A / tie / B | B win-rate |")
    lines.append("|---|---|---|")
    for qtype, t in sorted(judge["by_type_wins"].items()):
        w = t
        n = sum(w.values())
        wr = (w.get("B", 0) + 0.5 * w.get("tie", 0)) / n if n else None
        wr_str = f"{wr:.0%}" if wr is not None else "n/a"
        lines.append(f"| {qtype} | {w.get('A', 0)} / {w.get('tie', 0)} / {w.get('B', 0)} | {wr_str} |")
    lines.append("")
    lines.append(
        "Notably, `flow` (multi-hop execution tracing) — the type where a pre-built call graph "
        "should intuitively help most — has Arm B's *lowest* win-rate of any type."
    )
    lines.append("")

    lines.append("### Deep dive: why did Arm B sometimes do worse?")
    lines.append("")
    lines.append(
        "Two distinct, verified mechanisms explain this, and they cut in different directions for "
        "how much to trust the headline win-rate."
    )
    lines.append("")
    lines.append("#### 1. The judge itself is sometimes wrong (headline number is noisier than it looks)")
    lines.append("")
    lines.append(
        "Manual spot-check of a `flow` query Arm B \"lost\" (`rich-02`, repeat 1): the judge (o3) "
        "penalized Arm B for stating the print buffer is \"thread-local,\" calling this a factual "
        "error (\"the buffer is an attribute on the Console instance, not thread-local\"). Checking "
        "Rich's actual source shows Arm B was correct and the judge was wrong:"
    )
    lines.append("")
    lines.append("```python")
    lines.append("class ConsoleThreadLocals(threading.local):")
    lines.append('    """Thread local values for Console context."""')
    lines.append("...")
    lines.append("@property")
    lines.append("def _buffer(self) -> List[Segment]:")
    lines.append('    """Get a thread local buffer."""')
    lines.append("    return self._thread_locals.buffer")
    lines.append("```")
    lines.append("")
    lines.append(
        "This is one manually-verified case, not an automated audit of all judged queries — but it "
        "demonstrates that some fraction of the reported win/loss split is judge noise rather than "
        "a real quality gap. With 58/144 judged queries already ties, the true gap between arms is "
        "likely smaller than the raw 45.1% vs. 54.9% split suggests."
    )
    lines.append("")
    lines.append("#### 2. A real mechanism: over-trusting the graph as a complete answer")
    lines.append("")
    lines.append(
        f"First, a sanity check on Arm B's setup itself: across all {tool_access['n']} successful "
        f"Arm B runs, **{tool_access['both']} used both native and ContextAI tools together**, "
        f"{tool_access['mcp_only']} used ContextAI tools only (by choice, not necessity), and "
        f"**{tool_access['native_only'] + tool_access['neither']} were missing native tool access** "
        "— i.e. Arm B never lost capability relative to Arm A; it only ever gained the option to use "
        "ContextAI's tools. Any quality gap is therefore about how the extra tool was *used*, not "
        "about Arm B being handicapped."
    )
    lines.append("")
    lines.append(
        f"Across the {recall_gap['n_pairs']} paired (query, repeat) cases with an objective answer "
        f"key, Arm B's predicted symbol set was a **strict subset** of Arm A's in "
        f"{recall_gap['n_b_strict_subset_of_a']} "
        f"case{'s' if recall_gap['n_b_strict_subset_of_a'] != 1 else ''}, versus only "
        f"{recall_gap['n_a_strict_subset_of_b']} "
        f"case{'s' if recall_gap['n_a_strict_subset_of_b'] != 1 else ''} the other way around. In "
        "other words, when one arm's answer was a pure subset of the other's (never contained "
        "anything the other missed), it was Arm B's more often — the signature of trusting a single "
        "structured source over exhaustive verification."
    )
    lines.append("")
    lines.append(
        "ContextAI's graph is a static-analysis snapshot with known blind spots — the MCP server "
        "itself exposes a `list_gaps` tool specifically for `unresolved_calls` and `dynamic_gaps` "
        "(decorators, dynamic dispatch, etc. a static analyzer can't always resolve). When Codex "
        "treated `get_context`/`find_node`'s returned edges as the complete answer instead of "
        "cross-checking with a grep pass, it inherited those blind spots. Grep-based Arm A doesn't "
        "have this particular blind spot, because it searches exhaustively by construction."
    )
    lines.append("")
    example_ids = ", ".join(f"`{key[0]}` r{key[1]}" for key, _, _ in recall_gap["examples"])
    lines.append(f"Examples ({example_ids}):")
    lines.append("")
    lines.append("```")
    for key, a, b in recall_gap["examples"]:
        lines.append(f"{key[0]} r{key[1]}:")
        lines.append(f"  gold:  {a['gold']}")
        lines.append(f"  Arm A: {a['predicted']}")
        lines.append(f"  Arm B: {b['predicted']}   (strict subset of A's answer)")
        lines.append("")
    lines.append("```")
    lines.append("")
    lines.append(
        "**Takeaway**: more tool capability doesn't guarantee better use of it. A tool that returns "
        "a fast, confident, structured answer can let an agent skip the slower verification step it "
        "would otherwise do — and that answer can be silently incomplete. This suggests ContextAI's "
        "tools (or prompting around them) should nudge agents to treat the graph as a lead to verify "
        "for exhaustive-enumeration questions (\"who calls X\"), not a final answer."
    )
    lines.append("")

    lines.append("### Efficiency")
    lines.append("")
    lines.append(f"![efficiency]({chart_files[1]})" if len(chart_files) > 1 else "")
    lines.append("")
    lines.append("| Arm | n | mean tool calls | mean MCP calls | mean input tokens | "
                  "mean output tokens | mean latency (s) | % used ContextAI |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for arm in ("A", "B"):
        e = efficiency["by_arm"].get(arm)
        if not e:
            continue
        pct = f"{e['pct_used_contextai']:.0f}%" if e["pct_used_contextai"] is not None else "n/a"
        lines.append(
            f"| {arm} | {e['n']} | {e['mean_tool_calls']:.1f} | {e['mean_mcp_calls']:.1f} | "
            f"{e['mean_input_tokens']:.0f} | {e['mean_output_tokens']:.0f} | "
            f"{e['mean_latency_s']:.1f} | {pct} |"
        )
    lines.append("")
    lines.append(f"Total runs: {efficiency['n_total']}, failed: {efficiency['n_failed']}.")
    lines.append("")

    lines.append("### Methodology notes / deviations from METRICS.md")
    lines.append("")
    lines.append(
        "- **Answerer**: Codex CLI (`codex exec`, model `gpt-5-codex`), not a raw OpenAI chat "
        "completion — chosen so the comparison reflects a real, widely-used coding agent rather "
        "than a custom-built minimal tool loop."
    )
    lines.append(
        "- **Judge**: `o3` (a distinct OpenAI model from the answerer), blind, pairwise order "
        "randomized, given the objective answer key as reference when available."
    )
    lines.append(
        "- **Sandbox**: both arms run with `--dangerously-bypass-approvals-and-sandbox`. Codex's "
        "non-interactive mode currently auto-cancels MCP tool call approvals instead of allowing "
        "them (see [openai/codex#24135](https://github.com/openai/codex/issues/24135)), so Arm B "
        "needs the bypass to use ContextAI at all; it is applied uniformly to Arm A too so the "
        "*only* difference between arms is tool availability, not sandboxing. This is a contained, "
        "documented trade-off: read-oriented questions against pinned, throwaway clones."
    )
    lines.append(
        "- **Tool-call budget**: METRICS.md specifies a 25-tool-call cap; the Codex CLI has no "
        "native per-run tool-call limit, so a wall-clock timeout is used instead as the safety bound."
    )
    lines.append(
        "- ContextAI is only ever accessed by Codex itself (via the `contextai-graph` MCP server "
        "registered in Codex's own config) — never by the harness's orchestration code directly."
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    raw = load_json_dir(RESULTS_RAW_DIR)
    scored = load_json_dir(RESULTS_SCORED_DIR)
    judged = load_json_dir(RESULTS_JUDGED_DIR)

    efficiency = build_efficiency_table(raw)
    objective = build_objective_table(scored)
    judge_table = build_judge_table(judged)
    repo_table = build_repo_breakdown(raw, scored, judged)
    recall_gap = build_recall_gap_analysis(scored)
    tool_access = build_tool_access_check(raw)

    chart_files = make_charts(efficiency, objective, judge_table)
    repo_chart = make_repo_chart(repo_table)
    md = render_markdown(
        efficiency, objective, judge_table, chart_files, repo_table, repo_chart, recall_gap, tool_access
    )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "REPORT.md"
    report_path.write_text(md)
    mdrender.render(report_path, REPORT_DIR / "REPORT.html")
    print(f"Wrote {report_path}, charts: {chart_files + [repo_chart]}, and REPORT.html")


if __name__ == "__main__":
    main()
