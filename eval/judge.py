"""Blind LLM-as-judge: pairwise preference + absolute rubric.

Grades the *already-produced* Arm A vs Arm B answers from Codex (see
codex_runner.py / results/raw/). The judge never touches ContextAI or any
coding-tool CLI — it only reads text that Codex already wrote and scores it,
per METRICS.md's bias controls:
  - blind to which arm produced which answer (labels stripped)
  - order randomized
  - given the objective answer key as reference, when available
  - a different model from the answerer (Codex uses gpt-5-codex; judge uses o3)
"""

from __future__ import annotations

import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI

import score as score_mod

HERE = Path(__file__).resolve().parent
RESULTS_RAW_DIR = HERE / "results" / "raw"
RESULTS_JUDGED_DIR = HERE / "results" / "judged"

JUDGE_MODEL = "o3"

RUBRIC_SCHEMA = {
    "type": "object",
    "properties": {
        "winner": {"type": "string", "enum": ["1", "2", "tie"]},
        "reason": {"type": "string"},
        "scores": {
            "type": "object",
            "properties": {
                "1": {
                    "type": "object",
                    "properties": {
                        "correctness": {"type": "integer", "minimum": 0, "maximum": 3},
                        "completeness": {"type": "integer", "minimum": 0, "maximum": 3},
                        "groundedness": {"type": "integer", "minimum": 0, "maximum": 3},
                    },
                    "required": ["correctness", "completeness", "groundedness"],
                    "additionalProperties": False,
                },
                "2": {
                    "type": "object",
                    "properties": {
                        "correctness": {"type": "integer", "minimum": 0, "maximum": 3},
                        "completeness": {"type": "integer", "minimum": 0, "maximum": 3},
                        "groundedness": {"type": "integer", "minimum": 0, "maximum": 3},
                    },
                    "required": ["correctness", "completeness", "groundedness"],
                    "additionalProperties": False,
                },
            },
            "required": ["1", "2"],
            "additionalProperties": False,
        },
    },
    "required": ["winner", "reason", "scores"],
    "additionalProperties": False,
}


def _build_judge_prompt(question: str, gold: set[str] | None, resp1: str, resp2: str) -> str:
    parts = [
        "You are a blind, impartial judge evaluating two AI answers to the same "
        "code-understanding question about a real open-source Python codebase. "
        "You do not know which tool produced which answer, and their order is randomized.",
        "",
        f"Question: {question}",
    ]
    if gold:
        parts += [
            "",
            "Reference answer key (ground truth, from static analysis — treat as authoritative "
            "for judging factual correctness, but the responses may phrase things differently):",
            json.dumps(sorted(gold)),
        ]
    parts += [
        "",
        "Response 1:",
        resp1,
        "",
        "Response 2:",
        resp2,
        "",
        "First decide pairwise: which response is better overall (\"1\", \"2\", or \"tie\" if "
        "truly comparable), and why (cite specifics).",
        "Then score each response independently, 0-3 on each axis:",
        "- correctness: no false statements about the code",
        "- completeness: covers the real answer, not a fragment",
        "- groundedness: claims cite real files/symbols that plausibly exist",
    ]
    return "\n".join(parts)


def judge_pair(question: str, gold: set[str] | None, answer_a: str, answer_b: str) -> dict:
    client = OpenAI()
    swap = random.random() < 0.5
    resp1, resp2 = (answer_b, answer_a) if swap else (answer_a, answer_b)
    label1, label2 = ("B", "A") if swap else ("A", "B")

    prompt = _build_judge_prompt(question, gold, resp1, resp2)
    completion = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "judgment", "schema": RUBRIC_SCHEMA, "strict": True},
        },
    )
    payload = json.loads(completion.choices[0].message.content)

    winner_slot = payload["winner"]
    if winner_slot == "tie":
        winner_arm = "tie"
    else:
        winner_arm = label1 if winner_slot == "1" else label2

    scores_by_arm = {
        label1: payload["scores"]["1"],
        label2: payload["scores"]["2"],
    }
    return {
        "winner": winner_arm,
        "reason": payload["reason"],
        "scores": scores_by_arm,
        "judge_model": JUDGE_MODEL,
        "swapped": swap,
    }


def judge_all(queries: list[dict], repeats: int, concurrency: int = 6) -> list[dict]:
    RESULTS_JUDGED_DIR.mkdir(parents=True, exist_ok=True)
    judged: list[dict] = []
    todo: list[tuple[dict, int, set | None, dict, dict]] = []

    for q in queries:
        gold = score_mod.ground_truth_for(q)
        for r in range(repeats):
            out_path = RESULTS_JUDGED_DIR / f"{q['id']}__r{r}.json"
            if out_path.exists():
                judged.append(json.loads(out_path.read_text()))
                continue
            path_a = RESULTS_RAW_DIR / f"{q['id']}__A__r{r}.json"
            path_b = RESULTS_RAW_DIR / f"{q['id']}__B__r{r}.json"
            if not (path_a.exists() and path_b.exists()):
                continue
            raw_a = json.loads(path_a.read_text())
            raw_b = json.loads(path_b.read_text())
            if not (raw_a.get("ok") and raw_b.get("ok")):
                continue
            todo.append((q, r, gold, raw_a, raw_b))

    def _work(item):
        q, r, gold, raw_a, raw_b = item
        verdict = judge_pair(q["question"], gold, raw_a["answer"], raw_b["answer"])
        record = {"query_id": q["id"], "repo": q["repo"], "type": q["type"], "repeat": r, **verdict}
        out_path = RESULTS_JUDGED_DIR / f"{q['id']}__r{r}.json"
        out_path.write_text(json.dumps(record, indent=2))
        return record

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(_work, item) for item in todo]
        for fut in as_completed(futures):
            record = fut.result()
            judged.append(record)
            print(f"judged {record['query_id']} r{record['repeat']}: winner={record['winner']}")

    return judged


if __name__ == "__main__":
    import sys

    queries = json.loads((HERE / "queries.json").read_text())["queries"]
    repeats = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    results = judge_all(queries, repeats)
    wins = {"A": 0, "B": 0, "tie": 0}
    for r in results:
        wins[r["winner"]] += 1
    print(f"\n{len(results)} judged. Wins: {wins}")
    if results:
        b_rate = (wins["B"] + 0.5 * wins["tie"]) / len(results)
        print(f"Arm B win-rate (ties=0.5): {b_rate:.1%}")
