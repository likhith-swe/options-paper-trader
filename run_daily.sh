#!/usr/bin/env bash
# Chronos Options Paper Trading Bot - Daily Execution Runner
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$DIR/.venv/bin/python"

case "$1" in
    run-today)
        echo "Executing today's paper trading session..."
        $PYTHON "$DIR/main.py" run-today
        ;;
    status)
        $PYTHON "$DIR/main.py" status
        ;;
    report)
        $PYTHON "$DIR/main.py" report
        ;;
    dashboard)
        echo "Launching Web Dashboard on http://localhost:8501 ..."
        $PYTHON "$DIR/main.py" dashboard
        ;;
    daemon)
        echo "Starting Background Daily Trading Daemon..."
        $PYTHON "$DIR/main.py" start-daemon
        ;;
    *)
        echo "Usage: $0 {run-today|status|report|dashboard|daemon}"
        exit 1
        ;;
esac
