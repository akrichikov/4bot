PY = .venv/bin/python
PIP = .venv/bin/pip

.PHONY: venv install dev lint format test health

venv:
	python -m venv .venv
	$(PY) -m pip install --upgrade pip

install: venv
	$(PIP) install .
	$(PY) -m playwright install chromium

dev: venv
	$(PIP) install . '.[dev]'
	$(PY) -m playwright install chromium

lint:
	$(PY) -m ruff check .

format:
	$(PY) -m black xbot tests

test:
	.venv/bin/pytest -q

health:
	$(PY) -m xbot.cli health selectors --tweet-url $$HEALTH_TWEET_URL --profile $$PROFILE || true
