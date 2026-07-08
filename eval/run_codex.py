"""Batch driver: runs every (query, arm, repeat) through Codex.

Resumable — a run is skipped if its result file already exists (use --force
to redo). Concurrency is bounded with a thread pool since each run just
shells out to `codex exec` and blocks.

Usage:
    python3 run_codex.py                       # everything: 48 queries x 2 arms x REPEATS
    python3 run_codex.py --repeats 1            # quick pass, 1 repeat per (query, arm)
    python3 run_codex.py --repo flask           # just one repo
    python3 run_codex.py --query-id flask-01    # just one query
    python3 run_codex.py --arm B                # just one arm
    python3 run_codex.py --concurrency 8
    python3 run_codex.py --force                # redo even if results exist
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import codex_env
import codex_runner as cr

HERE = Path(__file__).resolve().parent


def load_queries() -> list[dict]:
    return json.loads((HERE / "queries.json").read_text())["queries"]


def plan(queries: list[dict], arms: list[str], repeats: int) -> list[tuple[dict, str, int]]:
    jobs = []
    for q in queries:
        for arm in arms:
            for r in range(repeats):
                jobs.append((q, arm, r))
    return jobs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--repo", action="append", default=None, help="filter to repo(s); repeatable")
    ap.add_argument("--query-id", action="append", default=None, help="filter to query id(s); repeatable")
    ap.add_argument("--type", action="append", default=None, help="filter to query type(s); repeatable")
    ap.add_argument("--arm", choices=["A", "B"], default=None, help="only run one arm")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--timeout", type=int, default=cr.DEFAULT_TIMEOUT_S)
    args = ap.parse_args()

    codex_env.ensure_setup()

    queries = load_queries()
    if args.repo:
        queries = [q for q in queries if q["repo"] in args.repo]
    if args.query_id:
        queries = [q for q in queries if q["id"] in args.query_id]
    if args.type:
        queries = [q for q in queries if q["type"] in args.type]
    if not queries:
        print("No queries matched the given filters.", file=sys.stderr)
        sys.exit(1)

    arms = [args.arm] if args.arm else ["A", "B"]
    jobs = plan(queries, arms, args.repeats)

    todo = []
    skipped = 0
    for q, arm, r in jobs:
        out = cr.result_path(q["id"], arm, r)
        if out.exists() and not args.force:
            skipped += 1
            continue
        todo.append((q, arm, r))

    print(f"{len(jobs)} total runs planned; {skipped} already done, {len(todo)} to run "
          f"(concurrency={args.concurrency}).")

    start = time.monotonic()
    done = 0
    failed = 0

    def _work(item):
        q, arm, r = item
        result = cr.run_query(q, arm, r, timeout_s=args.timeout)
        out = cr.result_path(q["id"], arm, r)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result.to_dict(), indent=2))
        return q["id"], arm, r, result.ok, result.error

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(_work, item) for item in todo]
        for fut in as_completed(futures):
            qid, arm, r, ok, error = fut.result()
            done += 1
            status = "OK" if ok else f"FAIL ({error})"
            elapsed = time.monotonic() - start
            print(f"[{done}/{len(todo)}] {qid:12} arm={arm} r={r}  {status}   ({elapsed:.0f}s elapsed)")
            if not ok:
                failed += 1

    print(f"\nDone. {done} runs completed ({failed} failed), {skipped} skipped, "
          f"{time.monotonic() - start:.0f}s total.")


if __name__ == "__main__":
    main()
