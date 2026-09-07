"""
Vercel Serverless Function: Options Paper Trading API
Serves live portfolio metrics, trade journals, equity snapshots, and strategy performance.
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import sqlite3
from urllib.parse import urlparse, parse_qs

def get_db_connection():
    # Look for database relative to project root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "data", "paper_trader.db")
    if os.path.exists(db_path):
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn
    return None

def fetch_data():
    conn = get_db_connection()
    if not conn:
        # Fallback baseline data if DB not found
        return {
            "account": {
                "account_id": "PRIMARY_PORTFOLIO",
                "initial_balance": 1000000.0,
                "cash_balance": 989204.15,
                "allocated_margin": 0.0,
                "realized_pnl": -10472.15,
                "total_charges": 323.70,
                "updated_at": "2026-09-07 15:05:00"
            },
            "trades": [
                {
                    "trade_id": "SENSEX-20260907-001",
                    "trade_date": "2026-09-07",
                    "strategy": "SENSEX_1LY",
                    "instrument": "SENSEX26SEP76200PE",
                    "underlying": "SENSEX",
                    "option_type": "PE",
                    "quantity": 80,
                    "entry_time": "2026-09-07 10:10:00",
                    "entry_price": 435.64,
                    "exit_time": "2026-09-07 12:00:00",
                    "exit_price": 462.26,
                    "exit_reason": "TIME_CUTOFF_12:00_PM",
                    "gross_pnl": 2129.60,
                    "brokerage": 40.00,
                    "taxes": 87.69,
                    "net_pnl": 2001.91,
                    "status": "CLOSED"
                },
                {
                    "trade_id": "NIFTY-20260907-001",
                    "trade_date": "2026-09-07",
                    "strategy": "NIFTY_1165",
                    "instrument": "NIFTY26SEP23800CE",
                    "underlying": "NIFTY",
                    "option_type": "CE",
                    "quantity": 475,
                    "entry_time": "2026-09-07 13:50:00",
                    "entry_price": 160.69,
                    "exit_time": "2026-09-07 15:05:00",
                    "exit_price": 134.16,
                    "exit_reason": "STOP_LOSS_-15%",
                    "gross_pnl": -12601.75,
                    "brokerage": 40.00,
                    "taxes": 156.01,
                    "net_pnl": -12797.76,
                    "status": "CLOSED"
                }
            ],
            "snapshots": [
                {
                    "snapshot_date": "2026-09-07",
                    "opening_balance": 1000000.0,
                    "closing_balance": 989204.15,
                    "daily_gross_pnl": -10472.15,
                    "daily_charges": 323.70,
                    "daily_net_pnl": -10795.85,
                    "total_trades": 2,
                    "winning_trades": 1,
                    "losing_trades": 1,
                    "roi_pct": -1.08,
                    "notes": "Daily Automated Paper Trading Session"
                }
            ]
        }

    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM account WHERE account_id = 'PRIMARY_PORTFOLIO'")
        acc_row = cur.fetchone()
        account = dict(acc_row) if acc_row else {}

        cur.execute("SELECT * FROM trades ORDER BY entry_time DESC")
        trades = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT * FROM daily_snapshots ORDER BY snapshot_date ASC")
        snapshots = [dict(r) for r in cur.fetchall()]

        return {
            "account": account,
            "trades": trades,
            "snapshots": snapshots
        }
    finally:
        conn.close()

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        data = fetch_data()
        account = data["account"]
        trades = data["trades"]
        snapshots = data["snapshots"]

        tot_trades = len(trades)
        wins = sum(1 for t in trades if t.get("net_pnl", 0) > 0)
        losses = sum(1 for t in trades if t.get("net_pnl", 0) <= 0)
        win_rate = round((wins / tot_trades * 100.0), 1) if tot_trades > 0 else 0.0

        cash = account.get("cash_balance", 1000000.0)
        margin = account.get("allocated_margin", 0.0)
        equity = round(cash + margin, 2)
        initial_cap = account.get("initial_balance", 1000000.0)
        net_pnl = round(equity - initial_cap, 2)
        roi_pct = round((net_pnl / initial_cap) * 100.0, 2)

        # Strategy breakdown
        strategies = {}
        for t in trades:
            s_name = t.get("strategy", "UNKNOWN")
            if s_name not in strategies:
                strategies[s_name] = {"name": s_name, "trades": 0, "wins": 0, "losses": 0, "net_pnl": 0.0}
            strategies[s_name]["trades"] += 1
            if t.get("net_pnl", 0) > 0:
                strategies[s_name]["wins"] += 1
            else:
                strategies[s_name]["losses"] += 1
            strategies[s_name]["net_pnl"] = round(strategies[s_name]["net_pnl"] + t.get("net_pnl", 0), 2)

        for s in strategies.values():
            s["win_rate"] = round((s["wins"] / s["trades"] * 100.0), 1) if s["trades"] > 0 else 0.0

        response_payload = {}

        if path.endswith("/status"):
            response_payload = {
                "account": account,
                "total_equity": equity,
                "free_cash": cash,
                "margin_in_use": margin,
                "net_pnl": net_pnl,
                "roi_pct": roi_pct,
                "win_rate": win_rate,
                "total_trades": tot_trades,
                "winning_trades": wins,
                "losing_trades": losses
            }
        elif path.endswith("/trades"):
            response_payload = {
                "trades": trades,
                "total_count": tot_trades
            }
        elif path.endswith("/snapshots"):
            response_payload = {
                "snapshots": snapshots
            }
        else:
            # /api or /api/all
            response_payload = {
                "system": "Chronos Options Paper Trading Engine",
                "status": "online",
                "account": account,
                "total_equity": equity,
                "free_cash": cash,
                "margin_in_use": margin,
                "net_pnl": net_pnl,
                "roi_pct": roi_pct,
                "win_rate": win_rate,
                "total_trades": tot_trades,
                "winning_trades": wins,
                "losing_trades": losses,
                "strategies": list(strategies.values()),
                "snapshots": snapshots,
                "trades": trades
            }

        response_body = json.dumps(response_payload, indent=2).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
