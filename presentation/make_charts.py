"""Simplified, friendly-labeled result charts for a non-technical audience.

Same underlying numbers as eval/report/REPORT.md (48 questions x 2 modes x 3
repeats = 288 runs, 144 judged), just re-drawn with plain-language titles and
bigger, simpler visuals instead of technical axis labels.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

NAVY = "#1a1a2e"
GREEN = "#2ca02c"
GRAY = "#94a3b8"
LIGHT_GRAY = "#e5e7eb"
AMBER = "#d97706"

plt.rcParams["font.size"] = 13


def chart_headline_preference():
    """A wins 50, tie 58, B wins 36 (n=144)."""
    fig, ax = plt.subplots(figsize=(9.5, 6))
    fig.patch.set_facecolor("white")
    labels = ["Preferred\nMode A\n(no map)", "Couldn't tell\nthe difference", "Preferred\nMode B\n(with map)"]
    values = [50, 58, 36]
    colors = [GRAY, LIGHT_GRAY, GREEN]
    bars = ax.bar(labels, values, color=colors, width=0.6, edgecolor="white", linewidth=2)
    for b, v in zip(bars, values):
        pct = v / 144 * 100
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v}\n({pct:.0f}%)", ha="center",
                fontsize=15, weight="bold", color=NAVY)
    ax.set_ylim(0, 68)
    ax.set_title("Out of 144 questions judged by a neutral AI referee", fontsize=16, weight="bold", color=NAVY, pad=18)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.get_yaxis().set_visible(False)
    ax.tick_params(axis="x", labelsize=13, colors=NAVY)
    fig.tight_layout()
    fig.savefig(ASSETS / "chart_headline.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def chart_by_project():
    """Judge win-rate by project, framed as 'how often the map version was preferred'."""
    fig, ax = plt.subplots(figsize=(11, 6))
    fig.patch.set_facecolor("white")
    projects = ["Click", "Flask", "HTTPX", "Rich"]
    rates = [44, 49, 47, 40]
    bars = ax.bar(projects, rates, color=GREEN, width=0.55, edgecolor="white", linewidth=2)
    ax.axhline(50, color=GRAY, linestyle="--", linewidth=2)
    ax.text(3.85, 51.5, "the map wins exactly half the time", fontsize=11.5, color="#666666", ha="right", style="italic")
    for b, v in zip(bars, rates):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v}%", ha="center", fontsize=15, weight="bold", color=NAVY)
    ax.set_ylim(0, 62)
    ax.set_title("How often the \"with map\" answer was preferred, by project", fontsize=16, weight="bold", color=NAVY, pad=18)
    ax.set_ylabel("")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.get_yaxis().set_visible(False)
    ax.tick_params(axis="x", labelsize=14.5, colors=NAVY)
    fig.tight_layout()
    fig.savefig(ASSETS / "chart_by_project.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def chart_cost():
    """Efficiency: tool calls similar, tokens ~1.7x for Arm B."""
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 6))
    fig.patch.set_facecolor("white")

    ax = axes[0]
    modes = ["Mode A\n(no map)", "Mode B\n(with map)"]
    steps = [14.4, 13.8]
    bars = ax.bar(modes, steps, color=[GRAY, GREEN], width=0.55, edgecolor="white", linewidth=2)
    for b, v in zip(bars, steps):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.3, f"{v}", ha="center", fontsize=15, weight="bold", color=NAVY)
    ax.set_title("Steps taken\nto answer\n(about the same)", fontsize=14.5, weight="bold", color=NAVY)
    ax.set_ylim(0, 17)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.get_yaxis().set_visible(False)
    ax.tick_params(axis="x", labelsize=12.5, colors=NAVY)

    ax = axes[1]
    tokens = [178, 301]
    bars = ax.bar(modes, tokens, color=[GRAY, AMBER], width=0.55, edgecolor="white", linewidth=2)
    for b, v in zip(bars, tokens):
        ax.text(b.get_x() + b.get_width() / 2, v + 7, f"{v}k", ha="center", fontsize=15, weight="bold", color=NAVY)
    ax.set_title("How much reading\nit did per question\n(~1.7x more with the map)", fontsize=14.5, weight="bold", color=NAVY)
    ax.set_ylim(0, 340)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.get_yaxis().set_visible(False)
    ax.tick_params(axis="x", labelsize=12.5, colors=NAVY)

    fig.tight_layout()
    fig.savefig(ASSETS / "chart_cost.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def chart_recall_gap():
    """The 19 vs 1 subset pattern, drawn as a simple comparison."""
    fig, ax = plt.subplots(figsize=(9.5, 6))
    fig.patch.set_facecolor("white")
    labels = ["No-map version gave a\nshorter answer", "Map version gave a\nSHORTER answer\n(missed some correct items)"]
    values = [1, 19]
    colors = [GRAY, AMBER]
    bars = ax.barh(labels, values, color=colors, height=0.5, edgecolor="white", linewidth=2)
    for b, v in zip(bars, values):
        unit = "time" if v == 1 else "times"
        ax.text(v + 0.4, b.get_y() + b.get_height() / 2, f"{v} {unit}", va="center", fontsize=15, weight="bold", color=NAVY)
    ax.set_xlim(0, 24)
    ax.set_title("When one answer was a subset of the other,\nit was almost always the \"with map\" answer that was incomplete",
                 fontsize=15, weight="bold", color=NAVY, pad=16)
    ax.spines[["top", "right", "bottom"]].set_visible(False)
    ax.get_xaxis().set_visible(False)
    ax.tick_params(axis="y", labelsize=13, colors=NAVY)
    fig.tight_layout()
    fig.savefig(ASSETS / "chart_recall_gap.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    chart_headline_preference()
    chart_by_project()
    chart_cost()
    chart_recall_gap()
    print("Charts written to", ASSETS)
