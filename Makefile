# Use python3 by default; override with `make PYTHON=python`
PYTHON ?= python3

.PHONY: install fetch eval report all clean

install:
	$(PYTHON) -m pip install -r requirements.txt

fetch:
	cd eval && $(PYTHON) fetch.py

eval:
	cd eval && $(PYTHON) run.py --sample 40

report:
	cd eval && $(PYTHON) report.py

all: fetch eval report

clean:
	rm -rf eval/_repos eval/_graphs eval/results
