#!/bin/bash

# CZ Headless Batch Reply Launcher
# Runs completely headless with no browser window

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           CZ Headless Batch Reply Launcher                   ║"
echo "║                                                              ║"
echo "║  🚀 Running in HEADLESS mode                                ║"
echo "║  🔒 Self-filtering ENABLED                                  ║"
echo "║  ⚡ Fast and efficient                                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Set working directory
cd /Users/doctordre/projects/4bot

# Export environment
export PYTHONPATH="/Users/doctordre/projects/4bot:$PYTHONPATH"
export X_USER="4botbsc@gmail.com"
export HEADLESS=true

# Create log directory
mkdir -p logs/headless_batch

# Create timestamp for log
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="logs/headless_batch/headless_${TIMESTAMP}.log"

echo "📊 Configuration:"
echo "   Mode: HEADLESS (no browser window)"
echo "   Profile: 4botbsc"
echo "   Self-Filter: ACTIVE ✅"
echo "   Log: $LOG_FILE"
echo ""

# Check for running instances
if pgrep -f "cz_headless_batch.py" > /dev/null; then
    echo "⚠️  Another headless batch is already running"
    echo "   Kill it first with: pkill -f cz_headless_batch.py"
    exit 1
fi

echo "🚀 Starting headless batch reply..."
echo ""

# Run the headless batch reply
python3 cz_headless_batch.py 2>&1 | tee "$LOG_FILE"

echo ""
echo "✅ Headless batch complete!"
echo "   Check log at: $LOG_FILE"