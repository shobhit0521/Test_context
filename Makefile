.PHONY: install fetch eval report all clean

install:
	pip install -r requirements.txt

fetch:
	cd eval && python fetch.py

eval:
	cd eval && python run.py --sample 40

report:
	cd eval && python report.py

all: fetch eval report

clean:
	rm -rf eval/_repos eval/_graphs eval/results
