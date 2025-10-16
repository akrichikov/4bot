#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT_DIR/Docs/status"
mkdir -p "$LOG_DIR"

# 1) Ensure RabbitMQ exchange/queues exist (durable)
python "$ROOT_DIR/rabbitmq_setup.py" || true

# 2) Start VTerm HTTP (if not running)
export BROWSER_NAME=webkit
if ! curl -sS "http://127.0.0.1:9876/health" >/dev/null 2>&1; then
  nohup python -m xbot.cli vterm http --port 9876 --audit-log "$LOG_DIR/vterm_audit.jsonl" --audit > "$LOG_DIR/vterm_http.log" 2>&1 &
  sleep 1
fi

# 3) Start VTerm request proxy consumer
nohup python "$ROOT_DIR/cz_vterm_request_proxy.py" > "$LOG_DIR/cz_vterm_request_proxy.log" 2>&1 &

# 4) Start CZ reply manager consumer
PROFILE="${PROFILE:-4botbsc}"
nohup env BROWSER_NAME=webkit python "$ROOT_DIR/cz_reply_manager.py" > "$LOG_DIR/cz_reply_manager.log" 2>&1 &

# 5) Start Notifications → RabbitMQ bridge (mentions for @4botbsc only)
nohup env BROWSER_NAME=webkit python "$ROOT_DIR/notification_rabbitmq_bridge.py" 31536000 --only-handle 4botbsc > "$LOG_DIR/notification_bridge.log" 2>&1 &

echo "CZ pipeline started. Logs in $LOG_DIR"
