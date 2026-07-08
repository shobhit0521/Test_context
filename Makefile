# Use python3 by default; override with `make PYTHON=python`
PYTHON ?= python3

.PHONY: install fetch clean

install:
	$(PYTHON) -m pip install -r requirements.txt

fetch:
	cd eval && $(PYTHON) fetch.py

# NOTE: the real-LLM eval runner + report targets are added once the metrics
# design is agreed and an OPENAI_API_KEY secret is provided.

clean:
	rm -rf eval/_repos eval/_graphs eval/results
