#!/bin/bash

# CZ Auto-Responder Daemon Launcher
# Launches the headless daemon that monitors and replies to X posts as CZ

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           CZ Auto-Responder Daemon Launcher                  ║"
echo "║                                                              ║"
echo "║  🤖 Starting headless X/Twitter monitoring daemon           ║"
echo "║  🔒 Self-post filtering enabled                             ║"
echo "║  ⚡ In-memory execution mode                                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Set working directory
cd /Users/doctordre/projects/4bot

# Check Python environment
echo "🔍 Checking Python environment..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.8+"
    exit 1
fi

# Create necessary directories
echo "📁 Creating profile directories..."
mkdir -p config/profiles/4botbsc/.x-user
mkdir -p logs/cz_daemon
mkdir -p Docs/status

# Export environment variables
export PYTHONPATH="/Users/doctordre/projects/4bot:$PYTHONPATH"
export X_USER="4botbsc@gmail.com"
export BOT_PROFILE="4botbsc"
export CZ_MAX_REPLIES="20"
export CZ_REPLY_PROB="0.3"

# Check if VTerm HTTP is already running
echo "🔍 Checking VTerm HTTP server..."
if curl -s http://127.0.0.1:9876/health > /dev/null 2>&1; then
    echo "✅ VTerm HTTP server is already running"
else
    echo "🚀 Starting VTerm HTTP server..."
    python3 -m xbot.vterm_http --host 127.0.0.1 --port 9876 > logs/cz_daemon/vterm_http.log 2>&1 &
    VTERM_PID=$!
    echo "   VTerm PID: $VTERM_PID"

    # Wait for VTerm to start
    for i in {1..10}; do
        if curl -s http://127.0.0.1:9876/health > /dev/null 2>&1; then
            echo "✅ VTerm HTTP server started successfully"
            break
        fi
        echo "   Waiting for VTerm to start... ($i/10)"
        sleep 2
    done
fi

# Kill any existing daemon processes
echo "🔄 Cleaning up existing processes..."
pkill -f "launch_cz_daemon.py" 2>/dev/null
pkill -f "cz_auto_daemon.py" 2>/dev/null

# Create log file with timestamp
LOG_FILE="logs/cz_daemon/daemon_$(date +%Y%m%d_%H%M%S).log"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🤖 CZ Daemon Configuration:"
echo "   Profile: 4botbsc"
echo "   User: 4botbsc@gmail.com"
echo "   Mode: Headless In-Memory"
echo "   Self-Filter: ENABLED"
echo "   Max Replies: 20/hour"
echo "   Reply Chance: 30% general, 90% mentions"
echo "   Log: $LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 Launching CZ Auto-Responder Daemon..."
echo "   Press Ctrl+C to stop"
echo ""

# Launch the daemon
python3 launch_cz_daemon.py 2>&1 | tee "$LOG_FILE"

# Cleanup on exit
echo ""
echo "🛑 Daemon stopped. Cleaning up..."
pkill -f "vterm_http" 2>/dev/null
echo "✅ Cleanup complete"