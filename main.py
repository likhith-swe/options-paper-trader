"""
Master CLI Entrypoint: Autonomous Options Paper Trading Bot
"""

import sys
import os
import argparse
import datetime
import subprocess
from database.ledger import LedgerDB
from scheduler.session_runner import SessionRunner
from scheduler.daemon import DailyTradingDaemon
from reporting.notifier import TradeNotifier

def cmd_run_today(date_str: str = None):
    """Execute trading session for a given date (default: today) using real intraday data."""
    ledger = LedgerDB()
    runner = SessionRunner(ledger)
    target_date = date_str or datetime.datetime.now().strftime("%Y-%m-%d")
    summary = runner.run_session(target_date)
    recap = TradeNotifier.dispatch(summary)
    print("\n" + recap)

def cmd_status():
    """Print current account balance and active positions."""
    ledger = LedgerDB()
    acc = ledger.get_account()
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    trades = ledger.get_trades_for_date(today_str)

    cash = acc.get("cash_balance", 1000000.0)
    allocated = acc.get("allocated_margin", 0.0)
    total_equity = cash + allocated
    net_pnl = acc.get("realized_pnl", 0.0) - acc.get("total_charges", 0.0)
    roi_pct = (net_pnl / 1000000.0) * 100.0

    print("================================================================")
    print("  💼 PAPER TRADING ACCOUNT STATUS")
    print("================================================================")
    print(f"• Account ID:             PRIMARY_PORTFOLIO")
    print(f"• Initial Capital:        ₹ 10,00,000.00")
    print(f"• Total Portfolio Equity: ₹ {total_equity:,.2f}")
    print(f"• Available Free Cash:    ₹ {cash:,.2f}")
    print(f"• Margin in Open Trades:  ₹ {allocated:,.2f}")
    print(f"• Realized Net P&L:       ₹ {net_pnl:+,.2f} ({roi_pct:+.2f}%)")
    print(f"• Total Statutory Taxes:  ₹ {acc.get('total_charges', 0.0):,.2f}")
    print(f"• Today's Trades Count:   {len(trades)}")
    print("================================================================")

def cmd_report():
    """Print formatted daily report card."""
    ledger = LedgerDB()
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    trades = ledger.get_trades_for_date(today_str)
    acc = ledger.get_account()

    gross = sum(t['gross_pnl'] for t in trades)
    charges = sum(t['brokerage'] + t['taxes'] for t in trades)
    net = sum(t['net_pnl'] for t in trades)

    summary = {
        "date": today_str,
        "total_trades": len(trades),
        "winning_trades": sum(1 for t in trades if t['net_pnl'] > 0),
        "losing_trades": sum(1 for t in trades if t['net_pnl'] <= 0),
        "gross_pnl": round(gross, 2),
        "total_charges": round(charges, 2),
        "net_pnl": round(net, 2),
        "closing_cash_balance": round(acc['cash_balance'], 2),
        "trades": trades
    }
    print(TradeNotifier.generate_daily_recap(summary))

def cmd_dashboard():
    """Launch Streamlit web dashboard."""
    dashboard_path = os.path.join(os.path.dirname(__file__), "reporting", "dashboard.py")
    venv_streamlit = os.path.join(os.path.dirname(__file__), ".venv", "bin", "streamlit")
    streamlit_bin = venv_streamlit if os.path.exists(venv_streamlit) else "streamlit"
    
    print(f"Launching interactive dashboard on http://localhost:8501 ...")
    subprocess.run([streamlit_bin, "run", dashboard_path, "--server.port=8501", "--server.address=0.0.0.0"])

def cmd_daemon():
    """Start background automated daily scheduler."""
    daemon = DailyTradingDaemon()
    daemon.run_daily_loop()

def main():
    parser = argparse.ArgumentParser(description="Autonomous Options Paper Trading Bot")
    parser.add_argument(
        "command",
        choices=["run-today", "status", "report", "dashboard", "start-daemon"],
        help="Action to execute"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Target session date (YYYY-MM-DD) for run-today command"
    )
    args = parser.parse_args()

    if args.command == "run-today":
        cmd_run_today(args.date)
    elif args.command == "status":
        cmd_status()
    elif args.command == "report":
        cmd_report()
    elif args.command == "dashboard":
        cmd_dashboard()
    elif args.command == "start-daemon":
        cmd_daemon()

if __name__ == "__main__":
    main()
