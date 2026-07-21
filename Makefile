# Use python3 by default; override with `make PYTHON=python`
PYTHON ?= python3
REPEATS ?= 3

.PHONY: install fetch codex-setup graphs run-codex run-codex-quick judge score report eval clean

install:
	$(PYTHON) -m pip install -r requirements.txt

fetch:
	cd eval && $(PYTHON) fetch.py

# Answerer under test: the real Codex CLI (`codex exec`). Arm A = Codex's
# native tools only; Arm B = the same + the contextai-graph MCP server.
# ContextAI is only ever touched by Codex itself, never by this harness.
codex-setup:
	cd eval && $(PYTHON) codex_env.py

graphs: codex-setup
	cd eval && $(PYTHON) build_graphs.py

# Full run: 48 queries x 2 arms x REPEATS (default 3) = up to 288 runs. Resumable.
run-codex: graphs
	cd eval && $(PYTHON) run_codex.py --repeats $(REPEATS)

# Fast smoke test: one query per repo, 1 repeat, both arms.
run-codex-quick: graphs
	cd eval && $(PYTHON) run_codex.py --query-id flask-01 --query-id click-02 \
		--query-id httpx-06 --query-id rich-08 --repeats 1

judge:
	cd eval && $(PYTHON) judge.py $(REPEATS)

score:
	cd eval && $(PYTHON) score.py $(REPEATS)

report:
	cd eval && $(PYTHON) aggregate_report.py

# Run everything end to end and produce the final report.
eval: run-codex score judge report

clean:
	rm -rf eval/_repos eval/_graphs eval/results eval/_codex_home
