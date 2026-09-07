"""
Persistent SQLite Ledger & Portfolio Database Manager
Maintains audit trail of cash balance, trade logs, statutory charges, and daily snapshots.
"""

import os
import sqlite3
import datetime
from typing import Dict, List, Optional
from config.settings import DB_PATH, PortfolioSettings

class LedgerDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            cur = conn.cursor()
            
            # 1. Accounts Table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS account (
                account_id TEXT PRIMARY KEY,
                initial_balance REAL NOT NULL,
                cash_balance REAL NOT NULL,
                allocated_margin REAL NOT NULL DEFAULT 0.0,
                realized_pnl REAL NOT NULL DEFAULT 0.0,
                total_charges REAL NOT NULL DEFAULT 0.0,
                updated_at TEXT NOT NULL
            );
            """)

            # 2. Trades Table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                trade_date TEXT NOT NULL,
                strategy TEXT NOT NULL,
                instrument TEXT NOT NULL,
                underlying TEXT NOT NULL,
                option_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                entry_time TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_time TEXT,
                exit_price REAL,
                exit_reason TEXT,
                gross_pnl REAL DEFAULT 0.0,
                brokerage REAL DEFAULT 0.0,
                taxes REAL DEFAULT 0.0,
                net_pnl REAL DEFAULT 0.0,
                status TEXT NOT NULL
            );
            """)

            # 3. Daily Snapshots Table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_snapshots (
                snapshot_date TEXT PRIMARY KEY,
                opening_balance REAL NOT NULL,
                closing_balance REAL NOT NULL,
                daily_gross_pnl REAL NOT NULL,
                daily_charges REAL NOT NULL,
                daily_net_pnl REAL NOT NULL,
                total_trades INTEGER NOT NULL,
                winning_trades INTEGER NOT NULL,
                losing_trades INTEGER NOT NULL,
                roi_pct REAL NOT NULL,
                notes TEXT
            );
            """)

            # Initialize Default Account if not present
            cur.execute("SELECT COUNT(*) FROM account WHERE account_id = 'PRIMARY_PORTFOLIO'")
            if cur.fetchone()[0] == 0:
                settings = PortfolioSettings()
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cur.execute("""
                INSERT INTO account (account_id, initial_balance, cash_balance, allocated_margin, realized_pnl, total_charges, updated_at)
                VALUES ('PRIMARY_PORTFOLIO', ?, ?, 0.0, 0.0, 0.0, ?)
                """, (settings.initial_cash, settings.initial_cash, now_str))
            
            conn.commit()

    def get_account(self) -> Dict:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM account WHERE account_id = 'PRIMARY_PORTFOLIO'")
            row = cur.fetchone()
            if row:
                return dict(row)
            return {}

    def log_trade_entry(
        self,
        trade_id: str,
        trade_date: str,
        strategy: str,
        instrument: str,
        underlying: str,
        option_type: str,
        quantity: int,
        entry_time: str,
        entry_price: float,
        initial_margin: float,
        entry_charges: float
    ):
        with self._get_conn() as conn:
            cur = conn.cursor()
            # Deduct cash for initial margin + entry charges
            cur.execute("""
            UPDATE account 
            SET cash_balance = cash_balance - ? - ?,
                allocated_margin = allocated_margin + ?,
                total_charges = total_charges + ?,
                updated_at = ?
            WHERE account_id = 'PRIMARY_PORTFOLIO'
            """, (initial_margin, entry_charges, initial_margin, entry_charges, entry_time))

            # Insert Trade record as OPEN
            cur.execute("""
            INSERT INTO trades (
                trade_id, trade_date, strategy, instrument, underlying, option_type, 
                quantity, entry_time, entry_price, status, brokerage, taxes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)
            """, (
                trade_id, trade_date, strategy, instrument, underlying, option_type,
                quantity, entry_time, entry_price, 20.0, entry_charges - 20.0
            ))
            conn.commit()

    def log_trade_exit(
        self,
        trade_id: str,
        exit_time: str,
        exit_price: float,
        exit_reason: str,
        initial_margin: float,
        exit_proceeds: float,
        exit_charges: float
    ) -> Dict:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM trades WHERE trade_id = ?", (trade_id,))
            t = cur.fetchone()
            if not t:
                raise ValueError(f"Trade {trade_id} not found in database")

            qty = t["quantity"]
            entry_px = t["entry_price"]
            gross_pnl = round((exit_price - entry_px) * qty, 2)
            
            existing_brokerage = t["brokerage"]
            existing_taxes = t["taxes"]
            
            exit_brokerage = 20.0
            exit_taxes = exit_charges - exit_brokerage
            
            total_brok = existing_brokerage + exit_brokerage
            total_tax = existing_taxes + exit_taxes
            net_pnl = round(gross_pnl - total_brok - total_tax, 2)

            # Update Trade Record
            cur.execute("""
            UPDATE trades 
            SET exit_time = ?, exit_price = ?, exit_reason = ?, gross_pnl = ?, 
                brokerage = ?, taxes = ?, net_pnl = ?, status = 'CLOSED'
            WHERE trade_id = ?
            """, (exit_time, exit_price, exit_reason, gross_pnl, total_brok, total_tax, net_pnl, trade_id))

            # Update Account: return initial margin + gross PnL - exit charges
            cur.execute("""
            UPDATE account
            SET cash_balance = cash_balance + ? - ?,
                allocated_margin = allocated_margin - ?,
                realized_pnl = realized_pnl + ?,
                total_charges = total_charges + ?,
                updated_at = ?
            WHERE account_id = 'PRIMARY_PORTFOLIO'
            """, (exit_proceeds, exit_charges, initial_margin, gross_pnl, exit_charges, exit_time))

            conn.commit()

            return {
                "trade_id": trade_id,
                "gross_pnl": gross_pnl,
                "total_charges": round(total_brok + total_tax, 2),
                "net_pnl": net_pnl,
                "exit_reason": exit_reason
            }

    def record_daily_snapshot(self, date_str: str, notes: str = ""):
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM trades WHERE trade_date = ? AND status = 'CLOSED'", (date_str,))
            trades = [dict(r) for r in cur.fetchall()]

            cur.execute("SELECT * FROM account WHERE account_id = 'PRIMARY_PORTFOLIO'")
            acc = dict(cur.fetchone())

            tot_trades = len(trades)
            wins = sum(1 for t in trades if t["net_pnl"] > 0)
            losses = sum(1 for t in trades if t["net_pnl"] <= 0)
            gross = round(sum(t["gross_pnl"] for t in trades), 2)
            charges = round(sum(t["brokerage"] + t["taxes"] for t in trades), 2)
            net = round(sum(t["net_pnl"] for t in trades), 2)

            closing_bal = round(acc["cash_balance"] + acc["allocated_margin"], 2)
            opening_bal = round(closing_bal - net, 2)
            roi_pct = round((net / opening_bal) * 100.0, 3) if opening_bal > 0 else 0.0

            cur.execute("""
            INSERT OR REPLACE INTO daily_snapshots (
                snapshot_date, opening_balance, closing_balance, daily_gross_pnl,
                daily_charges, daily_net_pnl, total_trades, winning_trades, losing_trades, roi_pct, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date_str, opening_bal, closing_bal, gross, charges, net,
                tot_trades, wins, losses, roi_pct, notes
            ))
            conn.commit()

    def has_snapshot_for_date(self, date_str: str) -> bool:
        """Return True if a daily snapshot already exists for the given date."""
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM daily_snapshots WHERE snapshot_date = ?", (date_str,))
            return cur.fetchone()[0] > 0

    def get_trades_for_date(self, date_str: str) -> List[Dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM trades WHERE trade_date = ? ORDER BY entry_time ASC", (date_str,))
            return [dict(r) for r in cur.fetchall()]

    def get_all_snapshots(self) -> List[Dict]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM daily_snapshots ORDER BY snapshot_date ASC")
            return [dict(r) for r in cur.fetchall()]
