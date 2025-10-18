# Critical Path 10: Optional Hardening (Resilience, Timeouts, Rate Control)

## Objectives
- Increase operational resilience under flaky networks, UI drift, and service hiccups without changing features.
- Standardize retry policies, timeouts, circuit‑breakers, and rate limits across browser ops, HTTP calls, and messaging.
- Improve observability of failures and backoffs via structured logs and metrics, keeping overhead minimal.

## Deliverables
- New modules/utilities: `xbot/retries.py` (retry/circuit helpers), `xbot/timeout.py` (timeout profiles), `xbot/metrics.py` (lightweight counters/latency), extensions to `xbot/ratelimit.py`.
- Refactors in high‑risk paths: Playwright page navigation/actions, aiohttp calls (if any), `vterm_client` → `vterm_http`, RabbitMQ publish/consume in `rabbitmq_manager`/`notify_to_rmq`.
- Settings: retry/backoff/timeout knobs in `xbot.settings` (with sane defaults), rate profiles in config model (CP9).
- Audit: structured events for retries, circuit open/half‑open/close, and rate‑limit throttle decisions.

## Design
1) Retry Policies (tenacity)
- Core decorator `retryable(op: str, stop, wait, retry_on)` returning sync/async compatible wrapper.
- Defaults: `stop_after_attempt(3)` or `stop_after_delay(10s)`, `wait_exponential_jitter(initial=0.2, max=2.0)`, `reraise=True`.
- Retry on: Playwright `TimeoutError`, `aiohttp.ClientError`, network `OSError`, HTTP 5xx, connection resets; never on 4xx/validation.
- Per‑operation profiles: `goto`, `click`, `wait_for_selector`, `http_get/http_post`, `rmq_publish` with tailored stop/wait.
- Logging: on_retry handler emits audit line with attempt, elapsed, next_sleep, exc_class.

2) Timeouts
- `TimeoutProfile` with defaults (short=3s, normal=10s, long=30s, io=15s, http=8s).
- Map operations to profiles; `page.goto` long; element waits normal; network IO http.
- Make overridable via env/CLI flags; expose in config dump.

3) Circuit Breaker
- Rolling window per endpoint (e.g., vterm HTTP, RabbitMQ) with consecutive failure threshold N (e.g., 5) and cool‑down T (e.g., 60s).
- States: closed → open → half‑open; audit transitions; open state fails fast with remediation hint.
- Integrate into vterm client calls and optional RMQ publish path.

4) Rate Limiting & Backpressure
- TokenBucket per action class (reply_post, like_post, dm, http_calls) with capacity and refill/sec.
- Pull reply policies from config (CP9) and map to buckets (e.g., 20 replies/hour → 1 token/180s, configurable burst).
- When depleted, either sleep until available or return throttle decision (active vs `--dry-run`).
- Emit audit throttle events with ETA.

5) Idempotency Guards
- Idempotency keys: replies use `tweet_id + profile`; RMQ messages use `message_id`.
- Block duplicate action within cool‑down window; leverage `artifacts/state/replied_mentions.json` and in‑memory cache.

6) Metrics & Observability
- `xbot/metrics.py`: counters (`retries_total{op}`), histograms (`latency_ms{op}`), gauges (`circuit_state{endpoint}`).
- Output JSONL under `logs/metrics/{service}.jsonl`; reuse CP3 rotation.
- `xbot ops status --json` to include recent aggregates (min/avg/p95 per op) when available.

## Task Breakdown
1) Implement `retries.py`
   - `retryable` decorator (sync/async), profiles dict, on_retry hook to logging/audit; unit tests for retry conditions.
2) Implement `timeout.py`
   - `TimeoutProfile`, map ops→profile; helper to compute absolute timeouts; expose via settings.
3) Implement circuit breaker helper
   - Class `CircuitBreaker(name, fail_threshold, cooldown_s)`; context manager; unit tests.
4) Extend `ratelimit.py`
   - Add `TokenBucket`; config mapping; helper `should_throttle(action)->Decision(allow,sleep_s,reason)` and `consume()`.
5) Integrate in hotspots
   - Playwright: wrap `page.goto`, `wait_for_selector`, `click` in `retryable` with mapped timeouts.
   - vterm HTTP: wrap requests in `retryable` + circuit breaker; surface clear errors.
   - RabbitMQ publish: retry transient channel/connection errors (bounded), audit failures.
6) Metrics plumbing
   - Thin wrappers to record latency and counts around `retryable` blocks.
7) Tests (offline)
   - `retryable`: deterministic failures then success; assert attempts.
   - Circuit breaker: open → half‑open flow.
   - Token bucket: refill math; throttle decisions.
   - Playwright adapters: mock TimeoutError to validate retry hook (no live browser).
8) Settings & Docs
   - `xbot.settings` fields: `RETRY_MAX_ATTEMPTS`, `RETRY_MAX_DELAY`, `CB_FAIL_THRESHOLD`, `CB_COOLDOWN_S`, `RATE_*` defaults.
   - `Docs/hardening.md`: concepts, defaults, tuning guidance.

## Acceptance Criteria
- Wrapped ops retry on transient errors with exponential jitter; non‑retryable errors bubble with clear messages.
- Circuit breaker engages on sustained vterm/RMQ failures; audit shows transitions; resumes after cooldown.
- Rate limits enforce configured ceilings; throttle events emitted; no functional regression.
- Tests pass; metrics files appear with aggregates during local runs.

## Risks & Mitigations
- Over‑retry causing delays: conservative defaults; per‑op overrides; circuit breaker prevents storms.
- Error taxonomy complexity: centralize in `xbot.errors`; document retryable classes.
- Metrics growth: reuse CP3 rotation; keep JSON minimal.

## Timeline
- Day 0: retries/timeout/cb libs + unit tests; integrate vterm HTTP.
- Day 1: integrate Playwright hotspots + RMQ publish; token bucket; docs; polish.

## Metrics
- Fewer transient failures; lower mean time to recovery.
- Stable throughput under rate limits; bounded log/metrics size.
