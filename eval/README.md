# ContextAI real-LLM evaluation harness

Goal: prove whether a **real LLM** answers code-understanding questions better when it
has the **ContextAI MCP tools** available (in addition to traditional grep/read) versus
traditional tools alone. The LLM decides which tools to call (agentic).

## Status

Being rebuilt from a retrieval-quality proxy into a real-LLM, agentic evaluation.

**Ready now (no API key needed):**
- `repos.py` — 4 pinned target codebases: `flask`, `click`, `httpx`, `rich` (9k-26k LOC each).
- `fetch.py` — clone/pin the repos into `_repos/` (idempotent).
- `queries.json` — **48 code-understanding queries (12 per repo)** grounded in real symbols.
- `mcp_client.py` — async client that drives the real `contextai-mcp` server over stdio.
- `groundtruth.py`, `astutil.py`, `graphutil.py` — helpers used to build gradeable answer keys.

**Pending (needs agreed metrics + `OPENAI_API_KEY`):**
- the agentic runner: two arms per query
  - Arm A: LLM + traditional tools (grep/read),
  - Arm B: LLM + traditional tools **+ ContextAI MCP tools**,
- scoring + report generation.

## Run what exists

```bash
pip install -r ../requirements.txt   # from repo root: pip install -r requirements.txt
cd eval
python3 fetch.py                     # clone/pin flask, click, httpx, rich
```

## Query types (see `queries.json`)

`callers`, `callees`, `flow`, `impact`, `definition`, `feature` — a mix that exercises
single-hop and multi-hop code navigation.
