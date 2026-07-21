# Test_context

Evaluation of whether **ContextAI's code-graph MCP tools help a real coding agent
understand code better** — when the agent has them available alongside its native tools
and decides itself which tools to call (agentic).

## Approach

For each of **48 code-understanding queries** (12 across each of 4 major Python repos),
the real **[Codex CLI](https://developers.openai.com/codex)** (`codex exec`) answers
**twice**:

- **Arm A** — Codex + its native tools only.
- **Arm B** — Codex + its native tools **+ the ContextAI `contextai-graph` MCP server**.

Codex was chosen (over a custom-built tool loop) so the comparison reflects a real,
widely-used coding agent rather than a strawman baseline. We then compare the **agent's
answers and efficiency** across arms via a blind LLM judge, objective F1 scoring
(callers/callees/impact, against jedi-based ground truth), and tool-call/token/latency
efficiency.

## Target codebases (`eval/repos.py`)

| Repo | ~LOC | Domain |
|---|---|---|
| `flask` | 9,024 | web framework |
| `click` | 10,124 | CLI framework |
| `httpx` | 9,033 | HTTP client |
| `rich` | 26,427 | terminal rendering / TUI |

## Status

Implemented and runnable end to end: the target repos, the 48-query set
(`eval/queries.json`), the Codex-driven agentic runner, objective scoring, blind judging,
and report generation are all in place. See [`eval/README.md`](eval/README.md) for how
each piece works, and `eval/report/REPORT.md` for results.

## Quick start

```bash
pip install -r requirements.txt
make fetch             # clone/pin flask, click, httpx, rich
make graphs            # Codex builds the 4 code graphs once, up front
make run-codex-quick   # fast smoke test: 1 query/repo, both arms
make eval              # full pipeline: run (48x2x3) + score + judge + report
```
