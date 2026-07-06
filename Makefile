.PHONY: setup fetch all clean

setup:
	python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

fetch:
	. .venv/bin/activate && python -m spike.fetch

all:
	. .venv/bin/activate && python -m spike.report

clean:
	rm -rf out/*.md out/*.json out/*.graphml
