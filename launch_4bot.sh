#!/bin/bash

# Launch 4Bot - Unified In-Memory Headless Bot
# This script sets up the environment and launches the orchestrator

echo "🚀 4Bot Launcher - Starting setup..."

# Set working directory
cd /Users/doctordre/projects/4bot

# Create profile directories for 4botbsc
echo "📁 Creating profile directories..."
mkdir -p config/profiles/4botbsc/.x-user
mkdir -p logs/4botbsc

# Check if RabbitMQ is running
echo "🐰 Checking RabbitMQ status..."
if ! rabbitmqctl status > /dev/null 2>&1; then
    echo "⚠️  RabbitMQ is not running. Starting RabbitMQ..."
    brew services start rabbitmq
    sleep 5
fi

# Setup RabbitMQ exchange and queues
echo "📡 Setting up RabbitMQ infrastructure..."
python rabbitmq_setup.py

# Kill any existing monitoring processes
echo "🔄 Cleaning up existing processes..."
pkill -f "notification_json_parser.py" 2>/dev/null
pkill -f "quick_monitor.py" 2>/dev/null
pkill -f "notification_rabbitmq_bridge.py" 2>/dev/null

# Export environment variables
export PYTHONPATH="/Users/doctordre/projects/4bot:$PYTHONPATH"
export X_USER="4botbsc@gmail.com"
export BOT_PROFILE="4botbsc"

# Create log file with timestamp
LOG_FILE="logs/4botbsc/bot_$(date +%Y%m%d_%H%M%S).log"

echo "✅ Setup complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🤖 4Bot Configuration:"
echo "   Profile: 4botbsc"
echo "   User: 4botbsc@gmail.com"
echo "   Mode: Headless"
echo "   Log: $LOG_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 Launching 4Bot Orchestrator..."
echo "   Press Ctrl+C to stop"
echo ""

# Launch the orchestrator with logging
python 4bot_orchestrator.py 2>&1 | tee "$LOG_FILE"