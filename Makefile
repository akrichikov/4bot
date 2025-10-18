PY = .venv/bin/python
PIP = .venv/bin/pip

.PHONY: venv install dev lint format test health cz-proxy cz-daemon notifications start-all stop-all

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
	$(PY) -m black xbot apps scripts tests

test:
	.venv/bin/pytest -q

health:
	$(PY) -m xbot.cli health selectors --tweet-url $$HEALTH_TWEET_URL --profile $$PROFILE || true

cz-proxy:
	$(PY) -m apps.cz.vterm_request_proxy_manager

cz-daemon:
	$(PY) -m apps.cz.cz_vterm_rabbitmq_daemon

notifications:
	$(PY) -m xbot.notification_json_parser --duration 60

start-all:
	scripts/shell/launch_complete_pipeline.sh start

stop-all:
	scripts/shell/launch_complete_pipeline.sh stop

system-health:
	$(PY) -m xbot.cli health system --json-out Docs/status/system_health.json || true

system-health-html:
	$(PY) -m xbot.cli health system-html --out-html Docs/status/system_health.html --out-json Docs/status/system_health.json || true
