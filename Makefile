PYTHON ?= python
PIP ?= pip

.PHONY: install dev test serve cli-help demo build upload-test upload

install:
	$(PIP) install -r requirements.txt && $(PIP) install -e .

dev:
	$(PIP) install -r requirements.txt && $(PIP) install -e .[dev]

test:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q

serve:
	$(PYTHON) -m agentvault_mcp.server

cli-help:
	agentvault --help || true

demo:
	$(PYTHON) examples/orchestrator.py

build:
	$(PYTHON) -m build

upload-test:
	$(PYTHON) -m twine upload --repository testpypi dist/*

upload:
	$(PYTHON) -m twine upload dist/*
