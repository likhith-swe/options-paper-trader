#!/usr/bin/env bash
# ==============================================================================
# Unloads and uninstalls the macOS LaunchAgent background daemon
# ==============================================================================

set -e

PLIST_NAME="com.likhith.optionspapertrader.plist"
TARGET_PLIST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "================================================================"
echo "  🛑 UNINSTALLING MACOS BACKGROUND DAEMON"
echo "================================================================"

if launchctl list | grep -q "com.likhith.optionspapertrader"; then
    echo "• Unloading daemon from launchd..."
    launchctl unload "$TARGET_PLIST" 2>/dev/null || true
fi

if [ -f "$TARGET_PLIST" ]; then
    echo "• Removing $TARGET_PLIST ..."
    rm -f "$TARGET_PLIST"
fi

echo "✅ Daemon successfully stopped and uninstalled."
echo "================================================================"
