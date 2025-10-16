#!/bin/bash
# Cleanup orphaned Playwright driver processes
# Run this periodically to prevent resource leaks

PLAYWRIGHT_COUNT=$(ps aux | grep "playwright/driver/node" | grep -v grep | wc -l | tr -d ' ')

if [ "$PLAYWRIGHT_COUNT" -gt 0 ]; then
    echo "🧹 Found $PLAYWRIGHT_COUNT orphaned Playwright processes"
    pkill -f "playwright/driver/node"
    sleep 1
    REMAINING=$(ps aux | grep "playwright/driver/node" | grep -v grep | wc -l | tr -d ' ')
    echo "✅ Cleanup complete - $REMAINING remaining"
else
    echo "✅ No orphaned processes found"
fi
