# ContextAI MCP evaluation harness

Reproducible benchmark answering one question:

> Does giving an LLM the **ContextAI code-graph MCP tools** *alongside* traditional
> `grep`/read produce **better context** than traditional tools alone?

The task measured is **"which functions call F?"** — the atom of code navigation an
agent performs constantly — across several real codebases, comparing three arms:

| Arm | How context is gathered |
|---|---|
| `graph_only` | ContextAI `build_graph` → `CALLS` edges (via the real MCP server) |
| `traditional_only` | `grep` for `F(` + map each hit to its enclosing function |
| `combined` | graph edges ∪ grep hits (the hero) |

Ground truth is computed **independently** with `jedi` (import/alias/scope-aware
static resolution of real call sites), so the system under test never grades itself.

## Metrics

- **precision / recall / F1** of each arm's caller set vs jedi ground truth.
- **effort** = candidate hits an agent must manually verify: all grep hits for
  `traditional_only`; only grep hits *not already confirmed by the graph* for
  `combined`; zero for the pre-resolved graph.

## Run it

```bash
pip install -r ../requirements.txt        # from repo root: pip install -r requirements.txt
cd eval
python fetch.py                           # clone/pin target repos (+ dogfood copy)
python run.py --sample 40                 # build graphs (MCP) + score all repos
python report.py                          # write report/REPORT.md + charts
```

Run a single codebase: `python run.py --sample 40 flask`.

## Layout

```
eval/
  repos.py        target codebases (pinned) + dogfood config
  fetch.py        clone/pin repos into _repos/ (idempotent)
  mcp_client.py   async client for the contextai-mcp stdio server
  groundtruth.py  jedi-based reference caller resolution (call sites only)
  graphutil.py    read graph JSON + normalize node ids to comparable keys
  astutil.py      enclosing-function resolution + key normalization
  arms.py         graph_only / traditional_only / combined retrieval
  metrics.py      precision / recall / F1
  run.py          orchestrator -> results/<repo>.json
  report.py       aggregate -> report/REPORT.md + charts
  report/         committed presentable results (REPORT.md + PNG charts)
```

`_repos/`, `_graphs/`, and `results/` are regenerable and git-ignored.
