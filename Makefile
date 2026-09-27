PYTHON = python3
SCRIPT = fly_in.py
CONFIG = cj.map

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) $(SCRIPT) $(CONFIG)

test:
	$(PYTHON) -m pytest -q

lint:
	flake8 .
	mypy --warn-return-any --warn-unused-ignores --ignore-missing-imports \
		--disallow-untyped-defs --check-untyped-defs .

clean:
	rm -rf __pycache__ */__pycache__ .mypy_cache .pytest_cache

re: clean run

.PHONY: install run test lint clean re
