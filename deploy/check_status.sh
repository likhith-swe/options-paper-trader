#!/usr/bin/env bash
# ==============================================================================
# Checks status and recent logs of the macOS background daemon
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "================================================================"
echo "  🔍 BACKGROUND DAEMON STATUS"
echo "================================================================"

STATUS=$(launchctl list | grep "com.likhith.optionspapertrader" || true)

if [ -n "$STATUS" ]; then
    echo "• Service Status: ACTIVE / LOADED"
    echo "• Launchd Entry:  $STATUS"
else
    echo "• Service Status: NOT LOADED"
    echo "  Run ./deploy/install_mac_daemon.sh to start it."
fi

echo "----------------------------------------------------------------"
echo "  RECENT DAEMON LOGS (last 15 lines):"
echo "----------------------------------------------------------------"
if [ -f "$PROJECT_ROOT/logs/daemon.log" ]; then
    tail -n 15 "$PROJECT_ROOT/logs/daemon.log"
else
    echo "  (No log file found at logs/daemon.log yet)"
fi

if [ -f "$PROJECT_ROOT/logs/daemon_error.log" ] && [ -s "$PROJECT_ROOT/logs/daemon_error.log" ]; then
    echo "----------------------------------------------------------------"
    echo "  RECENT ERROR LOGS:"
    echo "----------------------------------------------------------------"
    tail -n 10 "$PROJECT_ROOT/logs/daemon_error.log"
fi

echo "================================================================"
