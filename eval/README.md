# ContextAI real-LLM evaluation harness

Goal: prove whether a **real coding agent** answers code-understanding questions better
when it has the **ContextAI MCP tools** available (in addition to its native tools) versus
its native tools alone. The agent decides which tools to call (agentic).

The answerer under test is the real **[Codex CLI](https://developers.openai.com/codex)**
(`codex exec`, headless mode) — not a custom-built minimal tool loop — so the comparison
reflects a coding agent people actually use, not a strawman baseline.

## Status: implemented and runnable end to end

- `repos.py` / `fetch.py` — 4 pinned target codebases: `flask`, `click`, `httpx`, `rich`
  (9k-26k LOC each), cloned into `_repos/` (idempotent).
- `queries.json` — 48 code-understanding queries (12 per repo) grounded in real symbols.
- `codex_env.py` — sets up two isolated `CODEX_HOME` dirs, one per arm. **Arm A** (`no_mcp`)
  has Codex's native tools only; **Arm B** (`with_mcp`) additionally registers the
  `contextai-graph` MCP server. This is the *only* difference between arms.
- `build_graphs.py` — has **Codex itself** call the real `build_graph` MCP tool once per
  repo, up front (never called directly by this harness — ContextAI is exclusively
  accessed by Codex, the tool under test).
- `codex_runner.py` — runs one `(query, arm, repeat)` through `codex exec`, with a
  schema-constrained JSON final answer (`answer` prose + a structured `symbols` list for
  objectively-scorable query types). Every Codex answer and its full raw JSONL transcript
  are saved under `results/` (gitignored — regenerable, but see `results/graph_builds/`
  and `results/raw/` for what's captured).
- `run_codex.py` — batch driver over all `(query, arm, repeat)` combinations, concurrent
  and resumable.
- `score.py` — objective precision/recall/F1 for `callers`/`callees`/`impact` queries,
  using the jedi-based ground truth in `answer_key.py` (independent of both arms).
- `judge.py` — blind LLM-as-judge (`o3`, a different model from the answerer): pairwise
  preference (order randomized, labels stripped) + an absolute 0-3 rubric
  (correctness/completeness/groundedness).
- `aggregate_report.py` — combines everything into `report/REPORT.md` (+ charts +
  rendered HTML), the committed, presentable deliverable.
- `groundtruth.py`, `astutil.py`, `graphutil.py` — helpers behind the answer-key engine.
- `mcp_client.py` — legacy direct MCP stdio client from an earlier design iteration; kept
  for manual debugging only and **not used by the active pipeline** (ContextAI must only
  ever be touched by Codex itself, never by this harness's own code).

See [`METRICS.md`](METRICS.md) for the full scoring contract, and the "Methodology notes"
section of `report/REPORT.md` for the handful of documented, deliberate deviations from it
(driven by real constraints of Codex's non-interactive mode).

## Run it

```bash
pip install -r ../requirements.txt   # from repo root
cd eval
python3 fetch.py                     # clone/pin flask, click, httpx, rich
python3 codex_env.py                 # one-time: set up Codex CLI auth for both arms
python3 build_graphs.py              # Codex builds the 4 code graphs once, up front
python3 run_codex.py --repeats 3     # the full 48 x 2 x 3 = 288 runs (resumable)
python3 score.py 3                   # objective F1 for callers/callees/impact
python3 judge.py 3                   # blind pairwise + rubric judging
python3 aggregate_report.py          # writes report/REPORT.md (+ charts + HTML)
```

Or via the root `Makefile`: `make graphs`, `make run-codex-quick` (fast 4-query smoke
test), `make eval` (the full pipeline end to end).

## Query types (see `queries.json`)

`callers`, `callees`, `flow`, `impact`, `definition`, `feature` — a mix that exercises
single-hop and multi-hop code navigation. Only `callers`/`callees`/`impact` are
objectively scorable (F1 against jedi ground truth); all 48 are judged.
