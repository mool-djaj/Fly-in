PYTHON = python3
SCRIPT = fly_in.py
CONFIG = cj.map

install:
	pip install -r requirements.txt

run:
	$(PYTHON) $(SCRIPT) $(CONFIG)

test:
	$(PYTHON) -m pytest -q

debug:
	$(PYTHON) -m pdb $(SCRIPT) $(CONFIG)

clean:
	rm -rf __pycache__
	rm -rf .mypy_cache
	rm -rf */__pycache__

lint:
	flake8 .
	mypy --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs .

lint-strict:
	flake8 .
	mypy --strict .

.PHONY: install run debug clean lint lint-strict