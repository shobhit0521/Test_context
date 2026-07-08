# Test_context

Evaluation of whether **ContextAI's code-graph MCP tools help a real LLM understand code
better** — when the LLM has them available alongside traditional `grep`/read and decides
itself which tools to call (agentic).

## Approach

For each of **48 code-understanding queries** (12 across each of 4 major Python repos), a
real LLM answers **twice**:

- **Arm A** — LLM + traditional tools (grep/read) only.
- **Arm B** — LLM + traditional tools **+ ContextAI MCP tools**.

We then compare the **model's answers and efficiency** across arms.

## Target codebases (`eval/repos.py`)

| Repo | ~LOC | Domain |
|---|---|---|
| `flask` | 9,024 | web framework |
| `click` | 10,124 | CLI framework |
| `httpx` | 9,033 | HTTP client |
| `rich` | 26,427 | terminal rendering / TUI |

## Status

The target repos, the 48-query set (`eval/queries.json`), and the tool plumbing are in
place. The agentic runner + scoring are added once the scoring metrics are agreed and an
`OPENAI_API_KEY` is provided. See [`eval/README.md`](eval/README.md).

## Quick start (what runs today)

```bash
pip install -r requirements.txt
make fetch     # clone/pin flask, click, httpx, rich
```
