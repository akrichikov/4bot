PY = .venv/bin/python
PIP = .venv/bin/pip

.PHONY: venv install dev lint format test health cz-proxy cz-daemon notifications start-all stop-all hygiene pre-commit-install pre-commit-run site site-open health-strict status-index repo-layout guardrails schedule-sim schedule-run-sim status-aggregate site-all

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

hygiene:
	.venv/bin/pytest -q tests/test_repo_hygiene.py tests/test_wrapper_hygiene.py

pre-commit-install:
	$(PIP) install pre-commit
	.venv/bin/pre-commit install

pre-commit-run:
	.venv/bin/pre-commit run --all-files

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

status-index:
	$(PY) -m xbot.cli health status-index || true

site:
	$(MAKE) system-health-html
	$(MAKE) status-index

# Optional: evaluate guardrails if input file exists
# Usage: make guardrails GUARD_IN=path/to/replies.txt
guardrails:
	@if [ -n "$(GUARD_IN)" ] && [ -f "$(GUARD_IN)" ]; then \
		$(PY) -m xbot.cli health safety-eval --in "$(GUARD_IN)" --json-out Docs/status/guardrail_eval.json ; \
		else echo "(skip) guardrails: set GUARD_IN=<file> and ensure it exists" ; fi

# Optional: run scheduler simulation into Docs/status/scheduler_sim.json
# Usage: make schedule-sim PROFILES="a:1:10;b:2:10" SIM_SECONDS=10 SIM_DT_MS=100
PROFILES ?= a:1:10;b:2:10
SIM_SECONDS ?= 10
SIM_DT_MS ?= 100
schedule-sim:
	@if [ -n "$(PROFILES)" ]; then \
		$(PY) -m xbot.cli schedule simulate --profiles "$(PROFILES)" --seconds $(SIM_SECONDS) --dt-ms $(SIM_DT_MS) --json-out Docs/status/scheduler_sim.json ; \
		else echo "(skip) schedule-sim: set PROFILES=name:rps:burst;..." ; fi

# Run orchestrator simulation with queues
# Usage: make schedule-run-sim PROFILES="a:1:10;b:2:10" ITEMS="a=100;b=50" SIM_SECONDS=30 SIM_DT_MS=50 QUIET="a=22:00-06:00"
ITEMS ?=
QUIET ?=
schedule-run-sim:
	@if [ -n "$(PROFILES)" ] && [ -n "$(ITEMS)" ]; then \
		$(PY) -m xbot.cli schedule run-sim --profiles "$(PROFILES)" --items "$(ITEMS)" --seconds $(SIM_SECONDS) --dt-ms $(SIM_DT_MS) --quiet "$(QUIET)" --json-out Docs/status/scheduler_run.json ; \
		else echo "(skip) schedule-run-sim: set PROFILES=name:rps:burst;... and ITEMS=name=count;..." ; fi

status-aggregate:
	$(PY) -m xbot.cli report aggregate-status --out Docs/status/status_summary.json || true

# Full site pipeline: health, optional guardrails/scheduler, aggregated status, index
# Example: make site-all GUARD_IN=Docs/status/sample_replies.txt PROFILES="a:1:5;b:2:6"
site-all:
	$(MAKE) system-health-html
	$(MAKE) guardrails
	$(MAKE) schedule-sim
	$(MAKE) status-aggregate
	$(MAKE) status-index

site-open:
	$(PY) - <<'PY'
import pathlib, webbrowser
p = pathlib.Path('Docs/status/index.html')
webbrowser.open(p.resolve().as_uri())
PY

health-strict:
	$(PY) -m xbot.cli health system --json-out Docs/status/system_health.json --strict || true

repo-layout:
	$(PY) -m xbot.cli report repo-layout --out Docs/status/repo_layout.md --depth 2
