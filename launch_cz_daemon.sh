#!/bin/bash

# CZ Notification Daemon Launcher
# Complete pipeline: Notifications → VTerm → RabbitMQ → Reply Posting

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           CZ NOTIFICATION DAEMON LAUNCHER                     ║"
echo "║                                                               ║"
echo "║  📋 Complete Pipeline:                                       ║"
echo "║     • Monitor @4botbsc mentions                              ║"
echo "║     • Generate CZ replies via VTerm                          ║"
echo "║     • Queue in RabbitMQ (persistent)                         ║"
echo "║     • Post replies with tab management                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Set working directory
cd /Users/doctordre/projects/4bot

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check if RabbitMQ is running
if ! rabbitmqctl status > /dev/null 2>&1; then
    echo "❌ RabbitMQ is not running. Starting it..."
    brew services start rabbitmq
    sleep 5
fi

# Check if VTerm HTTP server is running
if ! curl -s http://127.0.0.1:8765/health > /dev/null; then
    echo "❌ VTerm HTTP server is not running. Starting it..."
    nohup python3 -m xbot.vterm_http > logs/vterm_http.log 2>&1 &
    echo "   VTerm HTTP started with PID: $!"
    sleep 3
fi

# Create log directory if needed
mkdir -p logs

# Check which method to use
if [ "$1" == "launchd" ]; then
    echo ""
    echo "📱 Installing as launchd daemon..."

    # Copy plist to LaunchAgents
    cp com.4botbsc.cz-daemon.plist ~/Library/LaunchAgents/

    # Unload if already loaded
    launchctl unload ~/Library/LaunchAgents/com.4botbsc.cz-daemon.plist 2>/dev/null

    # Load the daemon
    launchctl load ~/Library/LaunchAgents/com.4botbsc.cz-daemon.plist

    echo "✅ Daemon installed and started"
    echo ""
    echo "📊 Check status with:"
    echo "   launchctl list | grep 4botbsc"
    echo ""
    echo "📄 View logs at:"
    echo "   tail -f logs/cz_daemon.out.log"
    echo "   tail -f logs/cz_daemon.err.log"
    echo ""
    echo "🛑 To stop daemon:"
    echo "   launchctl unload ~/Library/LaunchAgents/com.4botbsc.cz-daemon.plist"

elif [ "$1" == "stop" ]; then
    echo ""
    echo "🛑 Stopping CZ daemon..."

    # Stop launchd daemon if running
    launchctl unload ~/Library/LaunchAgents/com.4botbsc.cz-daemon.plist 2>/dev/null

    # Kill any running Python processes
    pkill -f "cz_vterm_rabbitmq_daemon.py" 2>/dev/null
    pkill -f "cz_notification_daemon.py" 2>/dev/null

    echo "✅ Daemon stopped"

elif [ "$1" == "status" ]; then
    echo ""
    echo "📊 CZ Daemon Status:"
    echo ""

    # Check launchd
    if launchctl list | grep -q "com.4botbsc.cz-daemon"; then
        echo "✅ LaunchD daemon: RUNNING"
        launchctl list | grep "com.4botbsc.cz-daemon"
    else
        echo "❌ LaunchD daemon: NOT RUNNING"
    fi

    # Check Python processes
    if pgrep -f "cz_vterm_rabbitmq_daemon.py" > /dev/null; then
        echo "✅ Python daemon: RUNNING"
        ps aux | grep "cz_vterm_rabbitmq_daemon.py" | grep -v grep
    else
        echo "❌ Python daemon: NOT RUNNING"
    fi

    # Check VTerm
    if curl -s http://127.0.0.1:8765/health > /dev/null; then
        echo "✅ VTerm HTTP: RUNNING"
    else
        echo "❌ VTerm HTTP: NOT RUNNING"
    fi

    # Check RabbitMQ
    if rabbitmqctl status > /dev/null 2>&1; then
        echo "✅ RabbitMQ: RUNNING"
        echo "   Queues:"
        rabbitmqctl list_queues name messages | grep -E "4bot_request|4bot_response"
    else
        echo "❌ RabbitMQ: NOT RUNNING"
    fi

else
    echo ""
    echo "🚀 Starting CZ daemon in foreground..."
    echo "   Press Ctrl+C to stop"
    echo ""

    # Run in foreground
    python3 cz_vterm_rabbitmq_daemon.py
fi