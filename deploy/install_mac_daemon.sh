#!/usr/bin/env bash
# ==============================================================================
# Installs and launches the Options Paper Trading Bot as a background macOS daemon
# ==============================================================================

set -e

PLIST_NAME="com.likhith.optionspapertrader.plist"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TARGET_DIR="$HOME/Library/LaunchAgents"
TARGET_PLIST="$TARGET_DIR/$PLIST_NAME"

echo "================================================================"
echo "  📦 INSTALLING MACOS BACKGROUND DAEMON"
echo "================================================================"

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$TARGET_DIR"

# If already loaded, unload first
if launchctl list | grep -q "com.likhith.optionspapertrader"; then
    echo "• Unloading existing daemon instance..."
    launchctl unload "$TARGET_PLIST" 2>/dev/null || true
fi

# Copy plist to ~/Library/LaunchAgents
echo "• Copying plist to $TARGET_PLIST ..."
cp "$SCRIPT_DIR/$PLIST_NAME" "$TARGET_PLIST"

# Load plist into launchd
echo "• Loading LaunchAgent into macOS launchd..."
launchctl load "$TARGET_PLIST"

echo "----------------------------------------------------------------"
echo "  ✅ DAEMON SUCCESSFULLY INSTALLED & ACTIVATED"
echo "----------------------------------------------------------------"
echo "• Status: Running in background"
echo "• Auto-Start: Enabled on system login"
echo "• Output Log: $PROJECT_ROOT/logs/daemon.log"
echo "• Error Log:  $PROJECT_ROOT/logs/daemon_error.log"
echo ""
echo "To check live daemon logs, run:"
echo "  tail -f $PROJECT_ROOT/logs/daemon.log"
echo ""
echo "To uninstall the daemon, run:"
echo "  $SCRIPT_DIR/uninstall_mac_daemon.sh"
echo "================================================================"
