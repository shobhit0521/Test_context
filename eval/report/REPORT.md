# ContextAI vs. traditional tools — Codex agentic evaluation results

Real-LLM evaluation: the [Codex CLI](https://developers.openai.com/codex) (`codex exec`, model `gpt-5-codex`) answers the same code-understanding questions twice per query — once with its native tools only (**Arm A**), once with the same tools **plus the ContextAI `contextai-graph` MCP server** (**Arm B**). Codex decides itself which tools to call. See [`METRICS.md`](METRICS.md) for the full scoring contract.

## Headline: blind judge win-rate

Arm B win-rate over Arm A (ties = 0.5): **45.1%** across 144 judged queries — A wins 50, ties 58, B wins 36.

![quality](quality.png)

## Objective correctness (callers / callees / impact)

| Arm | n | mean F1 |
|---|---|---|
| A | 87 | 0.740 |
| B | 87 | 0.745 |

| Query type | Arm A F1 | Arm B F1 |
|---|---|---|
| callees | 0.805 | 0.797 |
| callers | 0.844 | 0.831 |
| impact | 0.520 | 0.565 |

## Absolute rubric (0-3 per axis, judge-scored)

| Arm | Correctness | Completeness | Groundedness | Mean |
|---|---|---|---|---|
| A | 2.62 | 2.59 | 2.84 | 2.69 |
| B | 2.57 | 2.48 | 2.85 | 2.63 |

## Efficiency

![efficiency](efficiency.png)

| Arm | n | mean tool calls | mean MCP calls | mean input tokens | mean output tokens | mean latency (s) | % used ContextAI |
|---|---|---|---|---|---|---|---|
| A | 144 | 14.4 | 0.0 | 177898 | 2734 | 42.0 | n/a |
| B | 144 | 13.8 | 10.0 | 300852 | 2534 | 44.1 | 100% |

Total runs: 288, failed: 0.

## Methodology notes / deviations from METRICS.md

- **Answerer**: Codex CLI (`codex exec`, model `gpt-5-codex`), not a raw OpenAI chat completion — chosen so the comparison reflects a real, widely-used coding agent rather than a custom-built minimal tool loop.
- **Judge**: `o3` (a distinct OpenAI model from the answerer), blind, pairwise order randomized, given the objective answer key as reference when available.
- **Sandbox**: both arms run with `--dangerously-bypass-approvals-and-sandbox`. Codex's non-interactive mode currently auto-cancels MCP tool call approvals instead of allowing them (see [openai/codex#24135](https://github.com/openai/codex/issues/24135)), so Arm B needs the bypass to use ContextAI at all; it is applied uniformly to Arm A too so the *only* difference between arms is tool availability, not sandboxing. This is a contained, documented trade-off: read-oriented questions against pinned, throwaway clones.
- **Tool-call budget**: METRICS.md specifies a 25-tool-call cap; the Codex CLI has no native per-run tool-call limit, so a wall-clock timeout is used instead as the safety bound.
- ContextAI is only ever accessed by Codex itself (via the `contextai-graph` MCP server registered in Codex's own config) — never by the harness's orchestration code directly.
