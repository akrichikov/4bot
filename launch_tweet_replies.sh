#!/bin/bash

# CZ Tweet Reply Launcher
# Replies to specific tweets from the 4Bot Tweets.md file

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           CZ Tweet Reply Launcher                            ║"
echo "║                                                              ║"
echo "║  📋 Target: /Docs/4Bot Tweets.md                            ║"
echo "║  🤖 Account: 4botbsc@gmail.com                              ║"
echo "║  🚀 Mode: HEADLESS                                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Set working directory to repo root
cd "$(cd "$(dirname "$0")" && pwd)" || exit 1
cd .. 2>/dev/null || true

# Export environment
export PYTHONPATH="$(pwd):$PYTHONPATH"
export X_USER="4botbsc@gmail.com"

# Create log directory
mkdir -p logs/tweet_replies

# Create timestamp for log
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="logs/tweet_replies/replies_${TIMESTAMP}.log"

echo "📊 Configuration:"
echo "   Profile: 4botbsc"
echo "   Persona: CZ"
echo "   Rate limit: 5-10 seconds between replies"
echo "   Log: $LOG_FILE"
echo ""

# Count URLs in file
URL_COUNT=$(grep -o 'https://x\.com/[^/]*/status/[0-9]*' "Docs/4Bot Tweets.md" | sort -u | wc -l)
echo "📋 Found $URL_COUNT unique tweet URLs to process"
echo ""

# Estimated time
EST_TIME=$((URL_COUNT * 7 / 60))
echo "⏱️  Estimated time: ~$EST_TIME minutes"
echo ""

echo "🚀 Starting CZ tweet replies..."
echo "   This will reply to each tweet with CZ persona"
echo "   Press Ctrl+C to stop"
echo ""

# Run the tweet reply script
python3 -m apps.cz.cz_reply_to_tweets 2>&1 | tee "$LOG_FILE"

echo ""
echo "✅ Tweet reply process complete!"
echo "   Check log at: $LOG_FILE"
echo "   Check summary at: logs/tweet_reply_summary.json"
