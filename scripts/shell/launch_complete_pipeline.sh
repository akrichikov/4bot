#!/bin/bash

# Complete CZ Pipeline Launcher
# Starts all components: RabbitMQ, VTerm HTTP, VTerm Proxy, and Notification Daemon

# Resolve repo root relative to this script (scripts/shell -> repo)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"

# Defaults for Safari headless in-memory mode unless overridden by env
export BROWSER_NAME="${BROWSER_NAME:-webkit}"
export AUTH_MODE="${AUTH_MODE:-cookies}"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          COMPLETE CZ PIPELINE LAUNCHER                        ║"
echo "║                                                               ║"
echo "║  Components:                                                  ║"
echo "║    1. RabbitMQ Message Broker                                ║"
echo "║    2. VTerm HTTP Server (Port 8765)                          ║"
echo "║    3. VTerm Request Proxy Manager                            ║"
echo "║    4. CZ Notification Daemon                                 ║"
echo "╚══════════════════════════════════════════════════════════════╗"
echo ""

cd "$SCRIPT_DIR"
mkdir -p "$LOG_DIR"

# Function to check if a process is running
check_process() {
    local process_name="$1"
    local check_cmd="$2"

    if eval "$check_cmd" > /dev/null 2>&1; then
        echo "✅ $process_name: RUNNING"
        return 0
    else
        echo "❌ $process_name: NOT RUNNING"
        return 1
    fi
}

# Function to start a component
start_component() {
    local name="$1"
    local cmd="$2"
    local log_file="$3"
    local check_cmd="$4"

    echo "🚀 Starting $name..."

    if eval "$check_cmd" > /dev/null 2>&1; then
        echo "   Already running"
    else
        nohup $cmd > "$log_file" 2>&1 &
        echo "   Started with PID: $!"
        sleep 2
    fi
}

case "$1" in
    start)
        echo "🔧 Starting all components..."
        echo ""

        # 1. Start RabbitMQ
        if ! rabbitmqctl status > /dev/null 2>&1; then
            echo "Starting RabbitMQ..."
            brew services start rabbitmq
            sleep 5
        fi
        check_process "RabbitMQ" "rabbitmqctl status"

        # 2. Start VTerm HTTP Server
        start_component \
            "VTerm HTTP Server" \
            "python3 -m xbot.vterm_http" \
            "$LOG_DIR/vterm_http.log" \
            "curl -s http://127.0.0.1:8765/health"

        # 3. Start VTerm Request Proxy Manager
        start_component \
            "VTerm Request Proxy" \
            "python3 -m apps.cz.vterm_request_proxy_manager" \
            "$LOG_DIR/vterm_proxy.log" \
            "pgrep -f vterm_request_proxy_manager.py"

        # 4. Start CZ Notification Daemon
        start_component \
            "CZ Notification Daemon" \
            "python3 -m apps.cz.cz_vterm_rabbitmq_daemon" \
            "$LOG_DIR/cz_daemon.log" \
            "pgrep -f cz_vterm_rabbitmq_daemon.py"

        echo ""
        echo "✅ All components started!"
        echo ""
        echo "📄 Log files:"
        echo "   VTerm HTTP: $LOG_DIR/vterm_http.log"
        echo "   VTerm Proxy: $LOG_DIR/vterm_proxy.log"
        echo "   CZ Daemon: $LOG_DIR/cz_daemon.log"
        echo ""
        echo "📊 Monitor with: $0 status"
        echo "🛑 Stop with: $0 stop"
        ;;

    stop)
        echo "🛑 Stopping all components..."
        echo ""

        # Kill Python processes
        pkill -f "cz_vterm_rabbitmq_daemon.py" 2>/dev/null
        echo "   Stopped CZ Daemon"

        pkill -f "vterm_request_proxy_manager.py" 2>/dev/null
        echo "   Stopped VTerm Proxy"

        pkill -f "xbot.vterm_http" 2>/dev/null
        echo "   Stopped VTerm HTTP"

        # Optional: Stop RabbitMQ
        if [ "$2" == "--all" ]; then
            brew services stop rabbitmq
            echo "   Stopped RabbitMQ"
        fi

        echo ""
        echo "✅ Components stopped"
        ;;

    status)
        echo "📊 Pipeline Status:"
        echo ""

        # Check each component
        check_process "RabbitMQ" "rabbitmqctl status"

        # Check queues
        if rabbitmqctl status > /dev/null 2>&1; then
            echo "   Queues:"
            rabbitmqctl list_queues name messages | grep -E "4bot_request|4bot_response" | sed 's/^/     /'
        fi

        check_process "VTerm HTTP" "curl -s http://127.0.0.1:8765/health"
        check_process "VTerm Proxy" "pgrep -f vterm_request_proxy_manager.py"
        check_process "CZ Daemon" "pgrep -f cz_vterm_rabbitmq_daemon.py"

        echo ""
        echo "📄 Recent logs:"
        echo ""

        # Show last few lines from each log
        for log in vterm_http vterm_proxy cz_daemon; do
            if [ -f "$LOG_DIR/${log}.log" ]; then
                echo "   ${log}:"
                tail -n 3 "$LOG_DIR/${log}.log" | sed 's/^/     /'
            fi
        done
        ;;

    test)
        echo "🧪 Testing Pipeline End-to-End..."
        echo ""

        # First ensure everything is running
        $0 status
        echo ""

        echo "📤 Sending test notification to RabbitMQ..."

        # Create test script under repo (no /tmp)
        mkdir -p "$SCRIPT_DIR/artifacts/tmp"
        cat > "$SCRIPT_DIR/artifacts/tmp/test_pipeline.py" << 'EOF'
#!/usr/bin/env python3
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xbot.rabbitmq_manager import RabbitMQManager

# Send test CZ reply request
manager = RabbitMQManager()
if manager.connect():
    success = manager.publish_cz_reply_request(
        post_url="https://x.com/test/status/12345",
        post_id="12345",
        author_handle="testuser",
        content="When moon? Is this project dead?"
    )
    if success:
        print("✅ Test message sent to RabbitMQ")
        print("   Check logs for processing...")
    else:
        print("❌ Failed to send test message")
    manager.close()
else:
    print("❌ Failed to connect to RabbitMQ")
EOF

        python3 "$SCRIPT_DIR/artifacts/tmp/test_pipeline.py"

        echo ""
        echo "⏳ Waiting for processing..."
        sleep 5

        echo ""
        echo "📊 Checking results:"
        rabbitmqctl list_queues name messages | grep -E "4bot_request|4bot_response"

        echo ""
        echo "📄 Recent proxy logs:"
        tail -n 10 "$LOG_DIR/vterm_proxy.log" | grep -E "CZ reply|Generated"
        ;;

    logs)
        echo "📄 Tailing all logs..."
        echo "   Press Ctrl+C to stop"
        echo ""

        # Use multitail if available, otherwise tail multiple files
        if command -v multitail > /dev/null; then
            multitail \
                -l "tail -f $LOG_DIR/vterm_http.log" \
                -l "tail -f $LOG_DIR/vterm_proxy.log" \
                -l "tail -f $LOG_DIR/cz_daemon.log"
        else
            tail -f "$LOG_DIR"/*.log
        fi
        ;;

    *)
        echo "Usage: $0 {start|stop|status|test|logs}"
        echo ""
        echo "Commands:"
        echo "  start  - Start all pipeline components"
        echo "  stop   - Stop all components (add --all to stop RabbitMQ too)"
        echo "  status - Show status of all components"
        echo "  test   - Run end-to-end pipeline test"
        echo "  logs   - Tail all log files"
        exit 1
        ;;
esac
