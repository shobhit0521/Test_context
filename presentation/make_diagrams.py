"""Generates all custom diagrams used in the presentation deck.

These are plain-language conceptual diagrams (not data charts) - built with
matplotlib for precise control over layout, but designed to read like
illustrations, not technical plots: no axes, no jargon, big friendly shapes.

Every diagram is built dense on purpose - the deck trades slide count for
information per slide, so each figure carries what used to take 2-3 slides.
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
PURPLE = "#9333ea"
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
    """Without a map (grep-style search) vs with a map (graph lookup)."""
    fig, ax = _new_fig()

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

    ax.plot([6.65, 6.65], [0.6, 6.9], color=BORDER, linewidth=2, linestyle="--")

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


def diagram_three_repos():
    """The whole project as three repos chained together."""
    fig, ax = _new_fig()
    ax.text(6.665, 7.05, "One project, three repos", ha="center", fontsize=25, weight="bold", color=NAVY)

    boxes = [
        (0.5, GREEN, "ContextAI", "Code-graph engine",
         "Reads a Python project (AST +\nruntime tracing) and emits a\ntyped graph.json of every\nfunction/class and how they\nconnect.",
         "github.com/shobhit0521/ContextAI"),
        (4.85, BLUE, "ConnectContext", "The MCP bridge",
         "Wraps ContextAI's graph API as\n8 tools an LLM agent can call\nover the open Model Context\nProtocol. Published on PyPI as\ncontextai-mcp.",
         "github.com/shobhit0521/ConnectContext"),
        (9.2, AMBER, "Test_context\n(this repo)", "The evaluation",
         "Wires ConnectContext into a real\ncoding agent (Codex) and measures,\nwith 288 real runs, whether having\nthe map actually improves its\nanswers.",
         "github.com/shobhit0521/Test_context"),
    ]
    box_w, box_h, y = 3.65, 4.3, 1.55
    for x, color, title, kicker, body, repo in boxes:
        head = _box(ax, x, y + box_h - 1.05, box_w, 1.05, title, fc=color, ec=color,
                     fontsize=16.5, fontcolor="white", weight="bold")
        ax.text(x + box_w / 2, y + box_h - 1.25, kicker, ha="center", va="top",
                fontsize=11.5, color=color, weight="bold", style="italic")
        body_box = FancyBboxPatch((x, y), box_w, box_h - 1.65, boxstyle="round,pad=0.02,rounding_size=0.06",
                                   linewidth=1.8, edgecolor=color, facecolor=LIGHT, zorder=2)
        ax.add_patch(body_box)
        ax.text(x + box_w / 2, y + (box_h - 1.65) / 2, body, ha="center", va="center",
                fontsize=11.3, color="#333333", weight="normal", zorder=3)
        ax.text(x + box_w / 2, y - 0.32, repo, ha="center", va="center",
                fontsize=10.2, color="#777777", style="italic")

    _arrow(ax, (4.15, y + 1.7), (4.85, y + 1.7), color=NAVY, lw=3.0)
    ax.text(4.5, y + 2.05, "imported\nas a library", ha="center", fontsize=10, color="#555555", style="italic")
    _arrow(ax, (8.5, y + 1.7), (9.2, y + 1.7), color=NAVY, lw=3.0)
    ax.text(8.85, y + 2.05, "registered as\nan MCP server", ha="center", fontsize=10, color="#555555", style="italic")

    ax.text(6.665, 0.55,
            "Build the map  \u2192  plug it into a real agent  \u2192  measure whether it actually helps.",
            ha="center", va="center", fontsize=14, color=NAVY, weight="bold", style="italic")

    fig.tight_layout()
    fig.savefig(ASSETS / "three_repos.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def diagram_contextai_arch():
    """ContextAI deep dive: extraction layers + what's in the graph."""
    fig, ax = _new_fig()
    ax.text(6.665, 7.05, "ContextAI: how source code becomes a graph", ha="center",
            fontsize=22, weight="bold", color=NAVY)

    ax.text(3.15, 6.35, "Four extraction layers, merged into one graph", ha="center",
            fontsize=14, weight="bold", color=NAVY)
    layers = [
        ("1", "AST + types", "functions, classes, imports, call sites, signatures", GREEN, "done"),
        ("2", "Framework conventions", "routes \u2192 handlers, templates, static assets (Flask)", GREEN, "done"),
        ("2.5", "Pattern matching", "DB tables, hardcoded URLs, cache ops, template refs", AMBER, "partial"),
        ("3", "Runtime tracing", "sys.settrace + asyncio hooks confirm real call chains", GREEN, "done"),
    ]
    ly = 5.55
    for num, title, desc, color, status in layers:
        ax.add_patch(plt.Circle((0.85, ly + 0.18), 0.26, fc=color, ec=color))
        ax.text(0.85, ly + 0.18, num, ha="center", va="center", fontsize=10.5, color="white", weight="bold")
        ax.text(1.35, ly + 0.34, title, ha="left", va="center", fontsize=12.7, color=NAVY, weight="bold")
        ax.text(1.35, ly - 0.06, desc, ha="left", va="center", fontsize=10, color="#555555")
        ly -= 0.98
    ax.text(0.85, ly + 0.55, "static analysis sees what code says \u2014 runtime tracing sees what it does",
            ha="left", va="center", fontsize=10.3, color="#777777", style="italic")

    ax.plot([6.35, 6.35], [1.0, 6.6], color=BORDER, linewidth=2, linestyle="--")

    ax.text(9.9, 6.35, "What ends up in the graph", ha="center", fontsize=14, weight="bold", color=NAVY)
    _box(ax, 6.7, 4.55, 3.05, 1.5,
         "NODES\nfunction, class,\nroute, table, \u2026\n+ signature, side effects,\nerror handling, complexity",
         fc=BLUE, ec=BLUE, fontsize=9.6, fontcolor="white")
    _box(ax, 9.95, 4.55, 3.05, 1.5,
         "EDGES\nCALLS, IMPORTS,\nREADS/WRITES, \u2026\n+ contract, criticality,\non_failure behavior",
         fc=PURPLE, ec=PURPLE, fontsize=9.6, fontcolor="white")
    _box(ax, 6.75, 2.75, 6.25, 1.4,
         "GAPS \u2014 the graph is honest about what it couldn't resolve:\nunresolved_calls and dynamic_gaps (decorators, registry lookups)\nare flagged per node, not silently dropped.",
         fc=LIGHT, ec=AMBER, fontsize=11, fontcolor="#333333", weight="normal")

    ax.text(9.9, 1.55, "153 passing tests  \u00b7  alpha status  \u00b7  Python 3.11+  \u00b7  Python (.py) and Jupyter (.ipynb) projects",
            ha="center", va="center", fontsize=11, color="#555555", style="italic")

    fig.tight_layout()
    fig.savefig(ASSETS / "contextai_arch.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def diagram_connectcontext_tools():
    """ConnectContext deep dive: MCP bridge + the 8 tools it exposes."""
    fig, ax = _new_fig()
    ax.text(6.665, 7.1, "ConnectContext: the MCP bridge", ha="center", fontsize=22, weight="bold", color=NAVY)

    _box(ax, 0.4, 5.95, 3.1, 0.85, "Any MCP client\nClaude \u00b7 Cursor \u00b7 Codex CLI", fc=NAVY, ec=NAVY,
         fontsize=10.8, fontcolor="white")
    _box(ax, 5.1, 5.95, 3.1, 0.85, "ConnectContext\n(contextai-mcp server)", fc=BLUE, ec=BLUE,
         fontsize=10.8, fontcolor="white")
    _box(ax, 9.8, 5.95, 3.1, 0.85, "ContextAI\ngraph/api.py", fc=GREEN, ec=GREEN,
         fontsize=10.8, fontcolor="white")
    _arrow(ax, (3.5, 6.37), (5.1, 6.37), color=NAVY, lw=2.4)
    ax.text(4.3, 6.62, "MCP / stdio", ha="center", fontsize=9.3, color="#555555", style="italic")
    _arrow(ax, (8.2, 6.37), (9.8, 6.37), color=NAVY, lw=2.4)
    ax.text(9.0, 6.62, "python import", ha="center", fontsize=9.3, color="#555555", style="italic")

    ax.text(6.665, 5.45, "Published on PyPI \u2014 any client runs it with zero manual install via  uvx contextai-mcp",
            ha="center", fontsize=11.5, color="#555555", style="italic")

    ax.text(3.3, 5.0, "Stable \u2014 read-only, never executes code", ha="center", fontsize=12.3, weight="bold", color=GREEN)
    stable = ["build_graph", "load_graph", "find_node", "get_context", "get_edge_path", "list_gaps"]
    xs = [0.5, 2.55, 4.6, 0.5, 2.55, 4.6]
    ys = [4.15, 4.15, 4.15, 3.35, 3.35, 3.35]
    for name, x, y in zip(stable, xs, ys):
        _box(ax, x, y, 1.9, 0.62, name, fc=WHITE, ec=GREEN, fontsize=10.3, fontcolor=GREEN, weight="bold", lw=1.8)

    ax.plot([6.9, 6.9], [1.6, 5.25], color=BORDER, linewidth=2, linestyle="--")

    ax.text(10.0, 5.0, "Experimental \u2014 executes target code", ha="center", fontsize=12.3, weight="bold", color=AMBER)
    experimental = ["run_trace", "merge_trace"]
    xs2 = [7.6, 10.1]
    for name, x in zip(experimental, xs2):
        _box(ax, x, 4.15, 2.2, 0.62, name, fc=WHITE, ec=AMBER, fontsize=10.3, fontcolor=AMBER, weight="bold", lw=1.8)
    ax.text(10.0, 3.35,
            "run_trace executes the target in a\nsubprocess and returns the exact path\nto a crash \u2014 use on trusted code only.",
            ha="center", va="top", fontsize=10, color="#555555")

    ax.text(6.665, 1.05,
            "Real bug found here: launching the server with its cwd inside a target repo let a same-named\n"
            "project file (Flask's typing.py) silently hijack Python's own stdlib import and crash on startup.",
            ha="center", va="center", fontsize=10.8, color="#994d00", style="italic")

    fig.tight_layout()
    fig.savefig(ASSETS / "connectcontext_tools.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def diagram_methodology():
    """Test_context deep dive: two arms, the pipeline, and how grading worked - one dense figure."""
    fig, ax = _new_fig()
    ax.text(6.665, 7.15, "Test_context: how the evaluation was run", ha="center", fontsize=22, weight="bold", color=NAVY)

    ax.text(3.3, 6.55, "Same AI, tested two ways", ha="center", fontsize=13.5, weight="bold", color=NAVY)
    _box(ax, 0.5, 5.55, 2.55, 0.85, "Arm A\nCodex + native tools only", fc=GRAY, ec=GRAY, fontsize=10.5, fontcolor="white")
    _box(ax, 3.4, 5.55, 2.55, 0.85, "Arm B\n+ ConnectContext's MCP tools", fc=GREEN, ec=GREEN, fontsize=10.5, fontcolor="white")
    ax.text(3.3, 5.3, "same model \u00b7 same prompt \u00b7 only the tool differs", ha="center", fontsize=9.7,
            color="#777777", style="italic")

    ax.plot([6.65, 6.65], [0.35, 6.9], color=BORDER, linewidth=1.6, linestyle="--")

    ax.text(10.0, 6.55, "Graded two independent ways", ha="center", fontsize=13.5, weight="bold", color=NAVY)
    _box(ax, 7.15, 5.55, 2.6, 0.85, "Objective F1\nvs. jedi ground truth", fc=AMBER, ec=AMBER, fontsize=10.3, fontcolor="white")
    _box(ax, 10.1, 5.55, 2.6, 0.85, "Blind LLM judge\nlabels hidden, order random", fc=PURPLE, ec=PURPLE, fontsize=10.3, fontcolor="white")

    steps = [
        ("1", "Fetch & pin\n4 real repos\n(Flask, Click,\nHTTPX, Rich)", GRAY),
        ("2", "Build 1 graph\nper repo via\nConnectContext's\nbuild_graph", GREEN),
        ("3", "Ask 48 Qs\n\u00d7 2 arms\n\u00d7 3 repeats\n= 288 runs", BLUE),
        ("4", "Score:\nF1 + blind\njudge on\nevery run", AMBER),
        ("5", "Report:\nwin-rate,\nefficiency,\ndeep dive", PURPLE),
    ]
    n = len(steps)
    box_w, gap = 2.15, 0.3
    total_w = n * box_w + (n - 1) * gap
    start_x = (13.33 - total_w) / 2
    y = 2.1
    for i, (num, label, color) in enumerate(steps):
        x = start_x + i * (box_w + gap)
        ax.add_patch(plt.Circle((x + box_w / 2, y + 1.85), 0.28, fc=color, ec=color))
        ax.text(x + box_w / 2, y + 1.85, num, ha="center", va="center", fontsize=13, color="white", weight="bold")
        _box(ax, x, y, box_w, 1.35, label, fc="white", ec=color, fontsize=10.6, fontcolor=NAVY, lw=2.2)
        if i < n - 1:
            _arrow(ax, (x + box_w + 0.04, y + 0.68), (x + box_w + gap - 0.04, y + 0.68), color="#999999", lw=2.0)

    ax.text(6.665, 0.55,
            "48 hand-written questions \u00d7 6 reasoning types (callers/callees/flow/impact/definition/feature) \u00d7 4 repos \u00b7 zero run failures",
            ha="center", va="center", fontsize=11, color="#444444", weight="bold")

    fig.tight_layout()
    fig.savefig(ASSETS / "methodology.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    diagram_search_vs_map()
    diagram_three_repos()
    diagram_contextai_arch()
    diagram_connectcontext_tools()
    diagram_methodology()
    print("Diagrams written to", ASSETS)
