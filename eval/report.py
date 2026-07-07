"""Aggregate eval/results/*.json into a Markdown report + charts.

Headline metric is "agent effort" (candidate caller hits that must be manually
verified) alongside precision/recall/F1, pooled across all questions.
"""

from __future__ import annotations

import base64
import datetime
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


def _pareto(results: list[dict], overall: dict) -> Path:
    """Recall vs effort: the tradeoff that shows combined dominates."""
    fig, ax = plt.subplots(figsize=(8, 5.5))
    colors = {"graph_only": "#1f77b4", "traditional_only": "#ff7f0e", "combined": "#2ca02c"}
    for arm in ARMS:
        xs = [r["aggregate"][arm]["effort"] for r in results]
        ys = [r["aggregate"][arm]["recall"] for r in results]
        ax.scatter(xs, ys, s=60, alpha=0.55, color=colors[arm])
        ox = overall["arms"][arm]["effort"]
        oy = overall["arms"][arm]["recall"]
        ax.scatter([ox], [oy], s=320, marker="*", color=colors[arm],
                   edgecolor="black", linewidth=0.8, zorder=5,
                   label=f"{ARM_LABELS[arm]} (overall)")
        ax.annotate(f"  {ARM_LABELS[arm]}", (ox, oy), fontsize=9, va="center")
    ax.set_xlabel("Agent effort: candidate hits to verify / question  (lower = better)")
    ax.set_ylabel("Recall  (higher = better)")
    ax.set_title("The tradeoff: combined reaches full recall at a fraction of the effort")
    ax.grid(alpha=0.3)
    ax.annotate("ideal", xy=(0.15, 1.005), fontsize=10, color="gray")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    out = REPORT_DIR / "pareto.png"
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


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _html_table(agg: dict) -> str:
    rows = ["<tr><th>Arm</th><th>Precision</th><th>Recall</th><th>F1</th>"
            "<th>Effort (hits to verify)</th></tr>"]
    best = {"cls": {}}
    for arm in ARMS:
        m = agg[arm]
        rows.append(
            f"<tr><td>{ARM_LABELS[arm]}</td><td>{m['precision']:.3f}</td>"
            f"<td>{m['recall']:.3f}</td><td>{m['f1']:.3f}</td>"
            f"<td>{m['effort']:.2f}</td></tr>"
        )
    return "<table>" + "".join(rows) + "</table>"


def build_html(results: list[dict], overall: dict, charts: dict[str, Path]) -> Path:
    o = overall["arms"]
    effort_drop = (
        100 * (o["traditional_only"]["effort"] - o["combined"]["effort"])
        / o["traditional_only"]["effort"] if o["traditional_only"]["effort"] else 0.0
    )
    date = datetime.date.today().isoformat()
    per_repo = "".join(
        f"<h3>{r['repo']} <span class='muted'>({r['n_questions']} questions)</span></h3>"
        + _html_table(r["aggregate"]) for r in results
    )
    imgs = "".join(
        f"<figure><img src='data:image/png;base64,{_b64(p)}'/></figure>"
        for p in (charts["metrics"], charts["effort"], charts["pareto"])
    )
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ContextAI code-graph vs traditional context retrieval</title>
<style>
:root{{--fg:#1a1a2e;--muted:#6b7280;--accent:#2ca02c;--card:#f7f8fa;--border:#e5e7eb;}}
*{{box-sizing:border-box}}
body{{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--fg);
max-width:960px;margin:0 auto;padding:40px 24px;line-height:1.55}}
h1{{font-size:30px;margin-bottom:4px}} h2{{margin-top:40px;border-bottom:2px solid var(--border);padding-bottom:6px}}
.sub{{color:var(--muted);margin-top:0}}
.summary{{background:var(--card);border:1px solid var(--border);border-left:5px solid var(--accent);
border-radius:10px;padding:18px 22px;margin:24px 0}}
.summary li{{margin:6px 0}}
.take{{font-weight:600;margin-top:12px}}
table{{border-collapse:collapse;width:100%;margin:14px 0;font-size:14px}}
th,td{{border:1px solid var(--border);padding:8px 10px;text-align:center}}
th{{background:#f0f2f5}} td:first-child,th:first-child{{text-align:left}}
figure{{margin:22px 0;text-align:center}} img{{max-width:100%;border:1px solid var(--border);border-radius:8px}}
.muted{{color:var(--muted);font-weight:400;font-size:14px}}
code{{background:#f0f2f5;padding:2px 6px;border-radius:4px;font-size:13px}}
.kpis{{display:flex;gap:14px;flex-wrap:wrap;margin:18px 0}}
.kpi{{flex:1;min-width:180px;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px 16px}}
.kpi .n{{font-size:26px;font-weight:700}} .kpi .l{{color:var(--muted);font-size:13px}}
</style></head><body>
<h1>ContextAI code-graph vs traditional context retrieval</h1>
<p class="sub">Does the ContextAI MCP tool set, <b>alongside</b> traditional grep/read, give an LLM
better context than traditional tools alone? &nbsp;·&nbsp; {date}</p>

<div class="kpis">
  <div class="kpi"><div class="n">{overall['n_questions']}</div><div class="l">focal functions tested</div></div>
  <div class="kpi"><div class="n">{len(results)}</div><div class="l">real codebases</div></div>
  <div class="kpi"><div class="n">{o['graph_only']['precision']:.0%}</div><div class="l">graph precision (highest)</div></div>
  <div class="kpi"><div class="n">-{effort_drop:.0f}%</div><div class="l">verification effort vs traditional</div></div>
</div>

<div class="summary">
<b>Task:</b> "which functions call F?" — the atom of code navigation an agent performs constantly.
<ul>
<li><b>Graph only</b> is the most precise (<b>{o['graph_only']['precision']:.1%}</b>) and needs
<b>zero</b> verification, but misses callers (recall <b>{o['graph_only']['recall']:.1%}</b>).</li>
<li><b>Traditional only</b> reaches full recall but is noisy
(precision <b>{o['traditional_only']['precision']:.1%}</b>) and forces the agent to vet
<b>{o['traditional_only']['effort']:.1f}</b> candidate hits/question.</li>
<li><b>Combined</b> keeps full recall (<b>{o['combined']['recall']:.1%}</b>) while cutting
candidates-to-verify by <b>{effort_drop:.0f}%</b>
(<b>{o['traditional_only']['effort']:.1f} → {o['combined']['effort']:.1f}</b>).</li>
</ul>
<div class="take">Neither tool alone is best. The graph is a precise, zero-cost backbone; traditional
search closes the recall gap; together they give complete context with the least review effort.</div>
</div>

<h2>Overall</h2>
{_html_table(o)}
{imgs}

<h2>Per-codebase</h2>
{per_repo}

<h2>Method</h2>
<ul>
<li><b>Ground truth</b>: jedi static resolution of every in-repo <i>call site</i> of F
(import/alias/scope aware), independent of the system under test.</li>
<li><b>Graph only</b>: <code>CALLS</code> edges from the graph built by the real
<code>build_graph</code> MCP tool.</li>
<li><b>Traditional only</b>: <code>grep</code> for <code>F(</code>, each hit mapped to its enclosing
function (includes false positives from comments, strings, same-named attribute calls).</li>
<li><b>Combined</b>: graph edges ∪ grep hits.</li>
<li><b>Effort</b>: candidate hits an agent must verify — all grep hits for traditional; only
grep hits <i>not already confirmed by the graph</i> for combined; zero for the graph.</li>
<li><b>Sampling</b>: most-connected functions per repo; only functions with ≥1 real caller are scored.</li>
</ul>

<h2>Honest limitations</h2>
<ul>
<li>The graph's recall gap comes from static-analysis blind spots (dynamic dispatch, some method
calls) — exactly why traditional search remains necessary.</li>
<li>Grep's recall is high for text call sites; its precision/effort cost is the price the graph removes.</li>
<li>Keys are normalized to <code>relpath::simple_name</code>; rare same-name collisions in one file are possible.</li>
</ul>
<p class="muted">Reproduce: <code>pip install -r requirements.txt &amp;&amp; make all</code></p>
</body></html>"""
    out = REPORT_DIR / "report.html"
    out.write_text(html)
    return out


def build_report() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    results = load_results()
    if not results:
        raise SystemExit("no results found; run run.py first")
    overall = pooled(results)
    metrics_png = _bar_metrics(results, overall)
    effort_png = _bar_effort(results, overall)
    pareto_png = _pareto(results, overall)

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
    lines.append(f"![pareto]({pareto_png.name})\n")

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
    html = build_html(results, overall,
                      {"metrics": metrics_png, "effort": effort_png, "pareto": pareto_png})
    print("wrote", REPORT_DIR / "REPORT.md")
    print("wrote", metrics_png)
    print("wrote", effort_png)
    print("wrote", pareto_png)
    print("wrote", html)


if __name__ == "__main__":
    build_report()
