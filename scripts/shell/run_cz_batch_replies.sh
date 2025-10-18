#!/bin/bash

# CZ Batch Reply Launcher
# Finds and replies to all non-4botbsc posts

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              CZ Batch Reply Launcher                         ║"
echo "║                                                              ║"
echo "║  🔍 Scanning for all non-4botbsc posts...                   ║"
echo "║  💬 Will reply to each with CZ persona                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Set working directory
cd /Users/doctordre/projects/4bot

# Export environment
export PYTHONPATH="/Users/doctordre/projects/4bot:$PYTHONPATH"
export X_USER="4botbsc@gmail.com"

# Create log directory
mkdir -p logs/cz_batch

# Create timestamp for log
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="logs/cz_batch/batch_${TIMESTAMP}.log"

echo "📊 Configuration:"
echo "   Profile: 4botbsc"
echo "   Filter: Excluding ALL 4botbsc/4bot posts"
echo "   Log: $LOG_FILE"
echo ""
echo "🚀 Starting batch reply process..."
echo ""

# Run the batch reply script
python3 cz_batch_reply.py 2>&1 | tee "$LOG_FILE"

echo ""
echo "✅ Batch reply process complete!"
echo "   Check log at: $LOG_FILE"