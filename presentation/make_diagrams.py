"""Generates all custom diagrams used in the presentation deck.

These are plain-language conceptual diagrams (not data charts) - built with
matplotlib for precise control over layout, but designed to read like
illustrations, not technical plots: no axes, no jargon, big friendly shapes.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

# ---- shared palette ----
NAVY = "#1a1a2e"
GREEN = "#2ca02c"
GRAY = "#94a3b8"
LIGHT = "#f7f8fa"
BORDER = "#e5e7eb"
BLUE = "#2563eb"
AMBER = "#d97706"
WHITE = "#ffffff"


def _new_fig(w=13.33, h=7.5, bg=WHITE):
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def _box(ax, x, y, w, h, text, fc=WHITE, ec=NAVY, fontsize=15, fontcolor=NAVY,
         weight="bold", lw=2.2, boxstyle="round,pad=0.02,rounding_size=0.08"):
    box = FancyBboxPatch((x, y), w, h, boxstyle=boxstyle, linewidth=lw,
                          edgecolor=ec, facecolor=fc, zorder=2)
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
             fontsize=fontsize, color=fontcolor, weight=weight, zorder=3,
             wrap=True)
    return box


def _arrow(ax, xy_from, xy_to, color=NAVY, lw=2.6, style="-|>", connectionstyle="arc3,rad=0.0"):
    arrow = FancyArrowPatch(xy_from, xy_to, arrowstyle=style, mutation_scale=22,
                             color=color, linewidth=lw, connectionstyle=connectionstyle, zorder=1)
    ax.add_patch(arrow)


def diagram_search_vs_map():
    """Slide: without a map (grep-style search) vs with a map (graph lookup)."""
    fig, ax = _new_fig()

    # Left half: "without a map"
    ax.text(3.3, 6.9, "Without a map", ha="center", fontsize=22, weight="bold", color=NAVY)
    ax.text(3.3, 6.4, "The AI opens files one by one, searching for clues", ha="center",
            fontsize=13.5, color="#555555")
    file_labels = ["app.py", "routes.py", "models.py", "utils.py", "helpers.py", "views.py"]
    positions = [(1.0, 5.1), (2.6, 5.1), (4.2, 5.1), (1.0, 3.9), (2.6, 3.9), (4.2, 3.9)]
    for (fx, fy), label in zip(positions, file_labels):
        _box(ax, fx, fy, 1.35, 0.8, label, fc=LIGHT, ec=GRAY, fontsize=11.5, fontcolor="#444444", weight="normal")
    magnifier_x, magnifier_y = 3.3, 2.55
    ax.add_patch(plt.Circle((magnifier_x, magnifier_y + 0.15), 0.42, fill=False, ec=AMBER, linewidth=4))
    ax.plot([magnifier_x + 0.28, magnifier_x + 0.62], [magnifier_y - 0.13, magnifier_y - 0.5],
            color=AMBER, linewidth=4, solid_capstyle="round")
    ax.text(3.3, 1.65, "Slow, and easy to miss something\nhidden in a file never opened", ha="center",
            fontsize=12.5, color="#555555", style="italic")

    # divider
    ax.plot([6.65, 6.65], [0.6, 6.9], color=BORDER, linewidth=2, linestyle="--")

    # Right half: "with a map"
    ax.text(10.0, 6.9, "With a map", ha="center", fontsize=22, weight="bold", color=GREEN)
    ax.text(10.0, 6.4, "The AI already knows what connects to what", ha="center",
            fontsize=13.5, color="#555555")
    nodes = {
        "wsgi_app": (8.7, 5.3),
        "full_dispatch\n_request": (10.6, 5.5),
        "dispatch\n_request": (12.1, 4.9),
        "handle\n_exception": (9.4, 3.9),
        "finalize\n_request": (11.3, 3.6),
        "preprocess\n_request": (8.6, 4.1),
    }
    edges = [
        ("wsgi_app", "full_dispatch\n_request"),
        ("full_dispatch\n_request", "dispatch\n_request"),
        ("full_dispatch\n_request", "preprocess\n_request"),
        ("full_dispatch\n_request", "finalize\n_request"),
        ("wsgi_app", "handle\n_exception"),
        ("handle\n_exception", "finalize\n_request"),
    ]
    for a, b in edges:
        _arrow(ax, nodes[a], nodes[b], color="#bcd8bc", lw=2.4, style="-")
    for name, (nx, ny) in nodes.items():
        ax.add_patch(plt.Circle((nx, ny), 0.5, fc=GREEN, ec="#1f7a1f", linewidth=1.8, zorder=3))
        ax.text(nx, ny, name, ha="center", va="center", fontsize=9.3, color="white", weight="bold", zorder=4)
    ax.text(10.0, 1.65, "Fast, and nothing important is\nlikely to be missed", ha="center",
            fontsize=12.5, color="#555555", style="italic")

    fig.tight_layout()
    fig.savefig(ASSETS / "search_vs_map.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def diagram_graph_capabilities():
    """Slide: what the map actually captures."""
    fig, ax = _new_fig()
    ax.text(6.665, 6.95, "What goes into the map", ha="center", fontsize=24, weight="bold", color=NAVY)

    items = [
        ("Every function\n& class", "Where each\none lives, and\nwhat it's called"),
        ("Who calls\nwhom", "The connections\nbetween\nfunctions"),
        ("What each\npiece does", "Inputs, outputs,\nerror handling,\ncomplexity"),
        ("What's\nuncertain", "Honestly flags\ncalls it couldn't\nresolve for sure"),
    ]
    xs = [0.7, 3.85, 7.0, 10.15]
    colors = [GREEN, BLUE, AMBER, "#9333ea"]
    for (title, desc), x, c in zip(items, xs, colors):
        _box(ax, x, 3.9, 2.5, 1.9, title, fc=c, ec=c, fontsize=14.5, fontcolor="white", weight="bold")
        ax.text(x + 1.25, 3.35, desc, ha="center", va="top", fontsize=11.8, color="#444444")

    ax.text(6.665, 1.3,
            "Built once per project, by reading the code carefully —\n"
            "without ever running it — the same way a very fast, very careful new hire would.",
            ha="center", va="center", fontsize=13.5, color=NAVY, style="italic")

    fig.tight_layout()
    fig.savefig(ASSETS / "graph_capabilities.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def diagram_two_modes():
    """Slide: Arm A vs Arm B, in plain language."""
    fig, ax = _new_fig()
    ax.text(6.665, 6.95, "We tested the same AI two ways", ha="center", fontsize=24, weight="bold", color=NAVY)

    # Mode A
    _box(ax, 0.8, 4.5, 5.2, 1.7, "Mode A", fc=GRAY, ec=GRAY, fontsize=20, fontcolor="white")
    ax.text(3.4, 3.95, "The AI + its normal tools only", ha="center", fontsize=14, color=NAVY, weight="bold")
    ax.text(3.4, 3.35, "(search text, open & read files)", ha="center", fontsize=12.5, color="#555555")

    # Mode B
    _box(ax, 6.85, 4.5, 5.2, 1.7, "Mode B", fc=GREEN, ec=GREEN, fontsize=20, fontcolor="white")
    ax.text(9.45, 3.95, "The AI + normal tools + the map", ha="center", fontsize=14, color=NAVY, weight="bold")
    ax.text(9.45, 3.35, "(ContextAI's code graph, as an extra tool)", ha="center", fontsize=12.5, color="#555555")

    ax.plot([6.4, 6.4], [1.3, 6.5], color=BORDER, linewidth=2, linestyle="--")
    ax.text(6.665, 6.15, "vs", ha="center", fontsize=16, color="#999999", weight="bold")

    ax.text(6.665, 2.15,
            "Same questions. Same AI model. Same rules.\nThe map is the only thing that's different.",
            ha="center", va="center", fontsize=14, color=NAVY, style="italic")

    fig.tight_layout()
    fig.savefig(ASSETS / "two_modes.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def diagram_mcp_connection():
    """Slide: how the map got connected to the AI, via MCP."""
    fig, ax = _new_fig()
    ax.text(6.665, 6.95, "How we plugged the map into the AI", ha="center", fontsize=24, weight="bold", color=NAVY)

    _box(ax, 0.7, 4.6, 3.1, 1.5, "Codex\n(the AI assistant)", fc=NAVY, ec=NAVY, fontsize=14.5, fontcolor="white")

    _box(ax, 4.9, 5.5, 3.1, 1.1, "Its normal tools\n(search & read files)", fc=LIGHT, ec=GRAY,
         fontsize=12.5, fontcolor="#333333", weight="normal")
    _arrow(ax, (3.8, 5.55), (4.9, 6.0), color=GRAY, lw=2.4)

    _box(ax, 4.9, 3.4, 3.6, 1.5, "MCP\n\"a universal plug\"", fc=BLUE, ec=BLUE, fontsize=13.5, fontcolor="white")
    _arrow(ax, (3.8, 4.9), (4.9, 4.15), color=BLUE, lw=2.8)

    _box(ax, 9.1, 3.4, 3.3, 1.5, "ContextAI's\ncode map", fc=GREEN, ec=GREEN, fontsize=14.5, fontcolor="white")
    _arrow(ax, (8.5, 4.15), (9.1, 4.15), color=GREEN, lw=2.8)

    ax.text(6.665, 1.85,
            "MCP is an open standard lots of AI coding tools already speak.\n"
            "It let us hand Codex the map exactly the way a real user would — no special wiring.",
            ha="center", va="center", fontsize=13, color="#444444", style="italic")

    ax.text(6.665, 0.75,
            "For \"Mode A\" we simply didn't plug the map in — everything else stayed identical.",
            ha="center", va="center", fontsize=12.5, color="#777777")

    fig.tight_layout()
    fig.savefig(ASSETS / "mcp_connection.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def diagram_pipeline():
    """Slide: the end-to-end testing pipeline."""
    fig, ax = _new_fig()
    ax.text(6.665, 6.95, "How the test was run, end to end", ha="center", fontsize=24, weight="bold", color=NAVY)

    steps = [
        ("1", "Get 4 real\ncode projects", GRAY),
        ("2", "Build the map\n(Mode B only)", GREEN),
        ("3", "Ask 48 real\nquestions,\nboth modes,\n3x each", BLUE),
        ("4", "Grade the\nanswers,\ntwo ways", AMBER),
        ("5", "Write up\nwhat happened", "#9333ea"),
    ]
    n = len(steps)
    box_w, gap = 2.1, 0.35
    total_w = n * box_w + (n - 1) * gap
    start_x = (13.33 - total_w) / 2
    y = 3.4
    for i, (num, label, color) in enumerate(steps):
        x = start_x + i * (box_w + gap)
        ax.add_patch(plt.Circle((x + box_w / 2, y + 2.05), 0.32, fc=color, ec=color))
        ax.text(x + box_w / 2, y + 2.05, num, ha="center", va="center", fontsize=15, color="white", weight="bold")
        _box(ax, x, y, box_w, 1.5, label, fc="white", ec=color, fontsize=12.3, fontcolor=NAVY, lw=2.4)
        if i < n - 1:
            _arrow(ax, (x + box_w + 0.05, y + 0.75), (x + box_w + gap - 0.05, y + 0.75), color="#999999", lw=2.2)

    ax.text(6.665, 1.0,
            "288 total AI runs (48 questions x 2 modes x 3 repeats) + 144 independent judging rounds\n"
            "Zero crashes across the whole run.",
            ha="center", va="center", fontsize=13.5, color="#444444", weight="bold")

    fig.tight_layout()
    fig.savefig(ASSETS / "pipeline.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def diagram_grading():
    """Slide: two independent grading methods."""
    fig, ax = _new_fig()
    ax.text(6.665, 6.95, "We graded every answer two independent ways", ha="center", fontsize=23, weight="bold", color=NAVY)

    _box(ax, 0.9, 3.6, 5.3, 2.4, "The strict checker", fc=AMBER, ec=AMBER, fontsize=18, fontcolor="white")
    ax.text(3.55, 3.05, "For questions with one \"correct list\" of answers\n"
                        "(e.g. \"who calls this function\"), we compared\n"
                        "the AI's list against ground truth computed by\n"
                        "a completely separate, independent code tool.",
            ha="center", va="top", fontsize=12, color="#444444")

    _box(ax, 7.1, 3.6, 5.3, 2.4, "The blind judge", fc="#9333ea", ec="#9333ea", fontsize=18, fontcolor="white")
    ax.text(9.75, 3.05, "A separate AI read both answers side by side —\n"
                        "without knowing which mode produced which —\n"
                        "in random order, and picked the better one,\n"
                        "plus scored each for accuracy & completeness.",
            ha="center", va="top", fontsize=12, color="#444444")

    ax.text(6.665, 0.95, "Two different lenses on the same answers, so no single grading quirk decides the outcome.",
            ha="center", va="center", fontsize=13, color="#555555", style="italic")

    fig.tight_layout()
    fig.savefig(ASSETS / "grading.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    diagram_search_vs_map()
    diagram_graph_capabilities()
    diagram_two_modes()
    diagram_mcp_connection()
    diagram_pipeline()
    diagram_grading()
    print("Diagrams written to", ASSETS)
