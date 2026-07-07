# Test_context

Evaluation harness proving that **ContextAI's code-graph MCP tools, used alongside
traditional `grep`/read, give an LLM better context than traditional tools alone.**

See [`eval/`](eval/) for the harness and [`eval/report/REPORT.md`](eval/report/REPORT.md)
for results across 4 real codebases (`requests`, `flask`, `click`, and ContextAI itself).

## Headline

Across **140** focal functions in **4** codebases, on the task *"which functions call F?"*:

| Arm | Precision | Recall | Effort (hits to verify) |
|---|---|---|---|
| Graph only | **0.93** | 0.83 | **0.0** |
| Traditional only | 0.89 | **1.00** | 4.31 |
| Combined | 0.86 | **1.00** | **1.32** |

The graph alone is the most precise and needs zero verification but misses ~17% of
callers; traditional search is complete but noisy (4.3 hits to vet per question);
**combined keeps full recall while cutting verification effort by ~69%**. Neither
tool alone wins — together they give complete context with the least review effort.

## Quick start

```bash
pip install -r requirements.txt
make all        # fetch repos -> build graphs (MCP) + score -> report
```

Open [`eval/report/report.html`](eval/report/report.html) for the self-contained report
(embedded charts, ready to present or print to PDF).

## Using the MCP server (Cursor and Claude Code)

The evaluation is **client-agnostic**: it drives the `contextai-mcp` server over raw MCP
(stdio) — exactly the tools Cursor or Claude Code would call — so the measured result holds
for any MCP client. To connect the server in a client:

**Claude Code** (reads `.mcp.json` at the project root — already committed here):
```bash
pip install contextai-mcp
# either rely on the committed .mcp.json, or register explicitly:
claude mcp add contextai-graph -- python3 -m contextai_mcp
```

**Cursor** (reads `.cursor/mcp.json` — already committed here):
```bash
pip install contextai-mcp   # then reload Cursor; the "contextai-graph" server appears
```

Both configs launch the server as `python3 -m contextai_mcp`, which is PATH-independent
(the console script installs to `~/.local/bin`, which is not always on `PATH`).
