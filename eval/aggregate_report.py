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


def render_markdown(efficiency: dict, objective: dict, judge: dict, chart_files: list[str]) -> str:
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

    lines.append("## Headline: blind judge win-rate")
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

    lines.append("## Objective correctness (callers / callees / impact)")
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

    lines.append("## Absolute rubric (0-3 per axis, judge-scored)")
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

    lines.append("## Efficiency")
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

    lines.append("## Methodology notes / deviations from METRICS.md")
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

    chart_files = make_charts(efficiency, objective, judge_table)
    md = render_markdown(efficiency, objective, judge_table, chart_files)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "REPORT.md"
    report_path.write_text(md)
    mdrender.render(report_path, REPORT_DIR / "REPORT.html")
    print(f"Wrote {report_path}, charts: {chart_files}, and REPORT.html")


if __name__ == "__main__":
    main()
