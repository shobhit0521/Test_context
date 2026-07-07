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
