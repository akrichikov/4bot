PY = .venv/bin/python
PIP = .venv/bin/pip

.PHONY: venv install dev lint format test health cz-proxy cz-daemon notifications start-all stop-all hygiene pre-commit-install pre-commit-run site site-open health-strict status-index repo-layout guardrails schedule-sim schedule-run-sim status-aggregate site-all paths-show paths-json paths-doctor secrets-guard site-clean site-reset paths-env paths-md paths-export paths-validate paths-init results-prune results-rebuild-index report-daily-index report-version
.PHONY: help submodules-init deps-pty deps verify-pty deps-all pty-http pty-http-safe pty-queue-run pty-queue-wait pty-admin-restart pty-admin-resize pty-version pty-config pty-metrics vterm-info vterm-wait vterm-console vterm-snapshot vterm-admin-restart vterm-admin-resize

venv:
	python -m venv .venv
	$(PY) -m pip install --upgrade pip

install: venv
	$(PIP) install .
	$(PY) -m playwright install chromium

dev: venv
	$(PIP) install . '.[dev]'
	$(PY) -m playwright install chromium

# Initialize and update submodules (required for ptyterm)
submodules-init:
	git submodule update --init --recursive

# Install ptyterm from submodule if present; otherwise attempt sibling ../pty
# Usage: make deps-pty
deps-pty: venv
	@if [ -d "submodules/ptyterm" ]; then \
		echo "Installing ptyterm from submodules/ptyterm"; \
		$(PIP) install -e submodules/ptyterm; \
	elif [ -f "../pty/pyproject.toml" ]; then \
		echo "Installing ptyterm from ../pty"; \
		$(PIP) install -e ../pty; \
	else \
		echo "ERROR: ptyterm source not found. Run 'make submodules-init' or place sibling ../pty repo."; \
		exit 1; \
	fi

# Sync ptyterm remote and submodule URL
# Usage: make pty-remote-sync URL=https://github.com/org/ptyterm.git
pty-remote-sync:
	@if [ -z "$(URL)" ]; then echo "Usage: make pty-remote-sync URL=<remote>"; exit 1; fi
	$(PY) -m xbot.cli deps pty-remote-sync --url "$(URL)"

# Build ptyterm wheel/sdist into dist/ptyterm
pty-build:
	$(PIP) install build
	@if [ -d submodules/ptyterm ]; then \
		$(PY) -m build submodules/ptyterm -o dist/ptyterm; \
	else \
		echo "submodules/ptyterm not found; run 'make submodules-init'"; exit 2; \
	fi

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

# Launchd templates: render to bin/launchd/ and install into LaunchAgents
launchd-render:
	$(PY) -m scripts.launch.install_launchd_from_templates render

launchd-install:
	$(PY) -m scripts.launch.install_launchd_from_templates install

system-health:
	$(PY) -m xbot.cli health system --json-out Docs/status/system_health.json || true

system-health-html:
	$(PY) -m xbot.cli health system-html --out-html Docs/status/system_health.html --out-json Docs/status/system_health.json || true

status-index:
	$(PY) -m xbot.cli health status-index || true

site:
	$(MAKE) system-health-html
	$(MAKE) paths-export
	$(MAKE) repo-layout
	$(MAKE) report-daily-index
	$(MAKE) status-index

# Build status site via CLI (Make-free orchestration). Optional --STRICT=true and --HEALTH=true
STRICT ?= false
HEALTH ?= false
site-cli:
	$(PY) -m xbot.cli site build --out-dir Docs/status $(if $(filter $(STRICT),true),--strict,) $(if $(filter $(HEALTH),true),--include-health,)

# Optional: evaluate guardrails if input file exists
# Usage: make guardrails GUARD_IN=path/to/replies.txt
guardrails:
	@if [ -n "$(GUARD_IN)" ] && [ -f "$(GUARD_IN)" ]; then \
		$(PY) -m xbot.cli health safety-eval --in "$(GUARD_IN)" --json-out Docs/status/guardrail_eval.json ; \
		else echo "(skip) guardrails: set GUARD_IN=<file> and ensure it exists" ; fi

secrets-guard:
	@echo "Scanning for sensitive prints (excluding Docs/ and scripts/manual/)" ; \
	rg -n "print\(.*(auth_token|ct0|kdt|att|password)" xbot apps scripts -g '!Docs/**' -g '!scripts/manual/**' || true
	@echo "Scanning artifacts/logs files for secrets (best-effort)" ; \
	$(PY) -m xbot.cli report scan-secrets --out Docs/status/secrets_scan.json || true

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

# Generate results daily index from current index.jsonl
report-daily-index:
	$(PY) -m xbot.cli report daily-index || true

report-version:
	$(PY) -m xbot.cli report version || true

# ---------------- ptyterm convenience -----------------
PTY_PORT ?= 9876
PTY_ADMIN ?= adm

deps: submodules-init deps-pty

verify-pty:
	$(PY) -m xbot.cli deps pty-verify

deps-all: deps verify-pty

pty-http:
	$(PY) -m ptyterm vterm http --port $(PTY_PORT) --admin-token $(PTY_ADMIN)

# Conservative policy preset: deny destructive commands, limit queue to 4, enable audit
pty-http-safe:
	$(PY) -m ptyterm vterm http \
		--port $(PTY_PORT) \
		--deny 'rm' \
		--deny 'shutdown' \
		--deny 'reboot' \
		--deny ':\(\)\{:\|:&\};:' \
		--max-queue 4 \
		--audit \
		--admin-token $(PTY_ADMIN)

pty-queue-run:
	$(PY) -m ptyterm queue run echo hello --target http://127.0.0.1:$(PTY_PORT)

pty-queue-wait:
	$(PY) -m ptyterm queue wait 1 --target http://127.0.0.1:$(PTY_PORT) --timeout 5

pty-admin-restart:
	python - <<'PY'
import urllib.request, os
req = urllib.request.Request(f"http://127.0.0.1:{os.environ.get('PTY_PORT','9876')}/admin/restart", method='POST', headers={'X-VTerm-Admin': os.environ.get('PTY_ADMIN','adm')})
print(urllib.request.urlopen(req).read().decode('utf-8'))
PY

pty-admin-resize:
	python - <<'PY'
import urllib.request, json, os
port = os.environ.get('PTY_PORT','9876')
data = json.dumps({'rows': 24, 'cols': 80}).encode('utf-8')
req = urllib.request.Request(f"http://127.0.0.1:{port}/admin/resize", data=data, method='POST', headers={'content-type':'application/json','X-VTerm-Admin': os.environ.get('PTY_ADMIN','adm')})
print(urllib.request.urlopen(req).read().decode('utf-8'))
PY

pty-version:
	python - <<'PY'
import urllib.request, os
port = os.environ.get('PTY_PORT','9876')
print(urllib.request.urlopen(f"http://127.0.0.1:{port}/version").read().decode('utf-8'))
PY

pty-config:
	python - <<'PY'
import urllib.request, os
port = os.environ.get('PTY_PORT','9876')
print(urllib.request.urlopen(f"http://127.0.0.1:{port}/config").read().decode('utf-8'))
PY

pty-metrics:
	python - <<'PY'
import urllib.request, os
port = os.environ.get('PTY_PORT','9876')
print(urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics").read().decode('utf-8')[:1000])
PY

vterm-info:
	$(PY) -m xbot.cli vterm info --base http://127.0.0.1:$(PTY_PORT)

vterm-wait:
	$(PY) -m xbot.cli vterm wait --base http://127.0.0.1:$(PTY_PORT)

vterm-console:
	$(PY) -m xbot.cli vterm console --base http://127.0.0.1:$(PTY_PORT)

vterm-snapshot:
	VT_BASE=http://127.0.0.1:$(PTY_PORT) $(PY) scripts/monitor/vterm_snapshot.py

vterm-admin-restart:
	$(PY) -m xbot.cli vterm admin-restart --base http://127.0.0.1:$(PTY_PORT) --admin-token $(PTY_ADMIN)

vterm-admin-resize:
	$(PY) -m xbot.cli vterm admin-resize --base http://127.0.0.1:$(PTY_PORT) --admin-token $(PTY_ADMIN) --rows 24 --cols 80

help-pty:
	@echo "PTY helpers (set PTY_PORT, PTY_ADMIN as needed)"; \
	echo "  make pty-http             # start HTTP server"; \
	echo "  make pty-queue-run        # enqueue echo hello"; \
	echo "  make pty-queue-wait       # wait for job 1"; \
	echo "  make pty-admin-restart    # restart shell (admin token)"; \
	echo "  make pty-admin-resize     # resize PTY 80x24"; \
	echo "  make pty-version          # GET /version"; \
	echo "  make pty-config           # GET /config"; \
	echo "  make pty-metrics          # GET /metrics (truncated)"; \
	echo "  make vterm-info           # combined /version + /config via xbot"; \
	echo "  make vterm-wait           # wait for /health"; \
	echo "  make vterm-console        # open web console"; \
	echo "  make vterm-snapshot       # write Docs/status/vterm_snapshot.json";

# Full site pipeline: health, optional guardrails/scheduler, aggregated status, index
# Example: make site-all GUARD_IN=Docs/status/sample_replies.txt PROFILES="a:1:5;b:2:6"
site-all:
	$(MAKE) system-health-html
	$(MAKE) paths-export
	$(MAKE) guardrails
	$(MAKE) schedule-sim
	$(MAKE) repo-layout
	$(MAKE) report-daily-index
	$(MAKE) status-aggregate
	$(MAKE) status-index

# Remove generated status artifacts (safe: only HTML/JSON under Docs/status)
site-clean:
	rm -f Docs/status/*.html Docs/status/*.json || true

# Full refresh: clean then rebuild status site and extras
site-reset:
	$(MAKE) site-clean
	$(MAKE) site-all

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

# Paths inspection helpers
paths-show:
	$(PY) -m xbot.cli paths show

paths-json:
	$(PY) -m xbot.cli paths show --json-out Docs/status/paths.json

paths-doctor:
	$(PY) -m xbot.cli paths doctor --ensure --json-out Docs/status/paths_doctor.json || true

paths-env:
	$(PY) -m xbot.cli paths env --json-out Docs/status/paths_env.json

paths-md:
	$(PY) -m xbot.cli paths markdown --out-md Docs/status/paths.md

paths-export:
	$(PY) -m xbot.cli paths export

paths-validate:
	$(PY) -m xbot.cli paths validate --strict --json-out Docs/status/paths_validate.json || true

paths-init:
	$(PY) -m xbot.cli paths init
## Prune aged result artifacts (default DAYS=14). Non-recursive; preserves index.jsonl/latest.json/report.html
DAYS ?= 14
results-prune:
	$(PY) -m xbot.cli results prune --days $(DAYS)

results-rebuild-index:
	$(PY) -m xbot.cli results rebuild-index || true
help:
	@echo "4bot Make targets:"; \
	echo "  make help-pty         # list PTY/VTerm operator helpers"; \
	echo "  make deps-all         # init submodules + install ptyterm + verify"; \
	echo "  make site            # build status site (see Docs/status)"; \
	echo "  make test            # run test suite"; \
	echo "  make pty-http-safe   # start HTTP with safe policy preset (see Docs/status/2025-10-20_ptyterm_presets.md)";
