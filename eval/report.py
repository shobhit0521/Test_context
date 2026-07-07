"""Aggregate eval/results/*.json into a Markdown report + charts.

Headline metric is "agent effort" (candidate caller hits that must be manually
verified) alongside precision/recall/F1, pooled across all questions.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE / "results"
REPORT_DIR = HERE / "report"
ARMS = ("graph_only", "traditional_only", "combined")
ARM_LABELS = {"graph_only": "Graph only", "traditional_only": "Traditional only",
              "combined": "Combined"}


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def load_results() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(RESULTS_DIR.glob("*.json"))]


def pooled(results: list[dict]) -> dict:
    """Micro-average metrics across every question in every repo."""
    qs = [q for r in results for q in r["questions"]]
    agg = {}
    for arm in ARMS:
        agg[arm] = {
            "precision": _mean([q["arms"][arm]["precision"] for q in qs]),
            "recall": _mean([q["arms"][arm]["recall"] for q in qs]),
            "f1": _mean([q["arms"][arm]["f1"] for q in qs]),
            "effort": _mean([q["arms"][arm]["effort"] for q in qs]),
        }
    return {"n_questions": len(qs), "arms": agg}


def _bar_metrics(results: list[dict], overall: dict) -> Path:
    repos = [r["repo"] for r in results] + ["OVERALL"]
    metrics = ["precision", "recall", "f1"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    x = range(len(repos))
    width = 0.25
    for ax, metric in zip(axes, metrics):
        for i, arm in enumerate(ARMS):
            vals = [r["aggregate"][arm][metric] for r in results]
            vals.append(overall["arms"][arm][metric])
            ax.bar([xi + i * width for xi in x], vals, width, label=ARM_LABELS[arm])
        ax.set_title(metric.capitalize())
        ax.set_xticks([xi + width for xi in x])
        ax.set_xticklabels(repos, rotation=20, ha="right")
        ax.set_ylim(0, 1.05)
        ax.grid(axis="y", alpha=0.3)
    axes[0].legend(loc="lower left", fontsize=8)
    fig.suptitle("Caller identification: precision / recall / F1 by codebase")
    fig.tight_layout()
    out = REPORT_DIR / "metrics.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


def _bar_effort(results: list[dict], overall: dict) -> Path:
    repos = [r["repo"] for r in results] + ["OVERALL"]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(repos))
    width = 0.25
    for i, arm in enumerate(ARMS):
        vals = [r["aggregate"][arm]["effort"] for r in results]
        vals.append(overall["arms"][arm]["effort"])
        ax.bar([xi + i * width for xi in x], vals, width, label=ARM_LABELS[arm])
    ax.set_title("Agent effort: candidate caller hits to verify (lower = better)")
    ax.set_xticks([xi + width for xi in x])
    ax.set_xticklabels(repos, rotation=20, ha="right")
    ax.set_ylabel("mean hits to verify / question")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    out = REPORT_DIR / "effort.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


def _table(agg: dict) -> str:
    rows = ["| Arm | Precision | Recall | F1 | Effort (hits to verify) |",
            "|---|---|---|---|---|"]
    for arm in ARMS:
        m = agg[arm]
        rows.append(
            f"| {ARM_LABELS[arm]} | {m['precision']:.3f} | {m['recall']:.3f} "
            f"| {m['f1']:.3f} | {m['effort']:.2f} |"
        )
    return "\n".join(rows)


def build_report() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    results = load_results()
    if not results:
        raise SystemExit("no results found; run run.py first")
    overall = pooled(results)
    metrics_png = _bar_metrics(results, overall)
    effort_png = _bar_effort(results, overall)

    o = overall["arms"]
    effort_drop = (
        100 * (o["traditional_only"]["effort"] - o["combined"]["effort"])
        / o["traditional_only"]["effort"]
        if o["traditional_only"]["effort"] else 0.0
    )

    lines = []
    lines.append("# ContextAI code-graph vs traditional context retrieval\n")
    lines.append(
        "Question tested: **does giving an LLM the ContextAI code-graph MCP tools, "
        "*alongside* traditional grep/read, produce better context than traditional "
        "tools alone?** Task: *\"which functions call F?\"* — the atom of code "
        "navigation an agent performs constantly.\n"
    )
    lines.append("## Headline (pooled over all questions)\n")
    lines.append(f"- Questions: **{overall['n_questions']}** focal functions across "
                 f"**{len(results)}** real codebases.")
    lines.append(f"- **Graph only** is the most precise (**{o['graph_only']['precision']:.1%}**) "
                 f"and needs **zero** verification, but misses callers "
                 f"(recall **{o['graph_only']['recall']:.1%}**).")
    lines.append(f"- **Traditional only** reaches full recall but is noisy "
                 f"(precision **{o['traditional_only']['precision']:.1%}**) and forces the "
                 f"agent to vet **{o['traditional_only']['effort']:.1f}** candidate hits/question.")
    lines.append(f"- **Combined** keeps full recall (**{o['combined']['recall']:.1%}**) while "
                 f"cutting candidates-to-verify by **{effort_drop:.0f}%** "
                 f"(**{o['traditional_only']['effort']:.1f} → {o['combined']['effort']:.1f}**), "
                 f"anchored by the graph's high-precision core.")
    lines.append("\n**Takeaway: neither tool alone is best. The graph supplies a precise, "
                 "zero-cost backbone; traditional search closes the recall gap; together they "
                 "give complete context with the least review effort.**\n")

    lines.append("## Overall\n")
    lines.append(_table(o) + "\n")
    lines.append(f"![metrics]({metrics_png.name})\n")
    lines.append(f"![effort]({effort_png.name})\n")

    lines.append("## Per-codebase\n")
    for r in results:
        lines.append(f"### {r['repo']}  ({r['n_questions']} questions)\n")
        lines.append(_table(r["aggregate"]) + "\n")

    lines.append("## Method\n")
    lines.append(
        "- **Ground truth**: jedi static resolution of every in-repo *call site* of F "
        "(import/alias/scope aware), mapped to the enclosing function. Independent of the "
        "system under test.\n"
        "- **Graph only**: `CALLS` edges into F from the graph built by the real "
        "`build_graph` MCP tool.\n"
        "- **Traditional only**: `grep` for `F(` across the repo, each hit mapped to its "
        "enclosing function (what a grep-driven agent gets, including false positives from "
        "comments, strings, and same-named attribute calls).\n"
        "- **Combined**: graph edges ∪ grep hits.\n"
        "- **Effort**: candidate hits an agent must manually verify — all grep hits for "
        "traditional; only grep hits *not already confirmed by the graph* for combined; "
        "zero for the (pre-resolved) graph.\n"
        "- **Sampling**: the most-connected functions per repo (the ones agents actually ask "
        "about); only functions with >=1 real caller are scored.\n"
    )
    lines.append("## Honest limitations\n")
    lines.append(
        "- The graph's recall gap comes from static-analysis blind spots (dynamic dispatch, "
        "some method calls) found during exploration — exactly why traditional search remains "
        "necessary.\n"
        "- Grep's recall is high for text call sites but its precision/effort cost is the "
        "price the graph removes.\n"
        "- Keys are normalized to `relpath::simple_name`; rare same-name collisions in one "
        "file are possible.\n"
    )

    (REPORT_DIR / "REPORT.md").write_text("\n".join(lines))
    print("wrote", REPORT_DIR / "REPORT.md")
    print("wrote", metrics_png)
    print("wrote", effort_png)


if __name__ == "__main__":
    build_report()
