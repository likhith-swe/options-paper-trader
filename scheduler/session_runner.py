"""
Trading Session Runner
Ingests historical or live intraday data, simulates candle ticks, and coordinates execution.
"""

import datetime
import pandas as pd
import yfinance as yf
from typing import Dict, List, Tuple
from database.ledger import LedgerDB
from execution.paper_broker import PaperBroker
from strategies.nifty_1165 import Nifty1165Engine
from strategies.sensex_1ly import Sensex1lyEngine

class SessionRunner:
    def __init__(self, ledger: LedgerDB):
        self.ledger = ledger
        self.broker = PaperBroker(ledger)
        self.nifty_engine = Nifty1165Engine(self.broker)
        self.sensex_engine = Sensex1lyEngine(self.broker)

    def fetch_intraday_data(self, date_str: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Fetch 5-minute intraday candles for NIFTY (^NSEI) and SENSEX (^BSESN)."""
        print(f"Fetching intraday data for {date_str} from Yahoo Finance...")
        
        # Download Nifty
        df_nifty = yf.download('^NSEI', period='5d', interval='5m', progress=False)
        if isinstance(df_nifty.columns, pd.MultiIndex):
            df_nifty.columns = df_nifty.columns.get_level_values(0)
            
        # Download Sensex
        df_sensex = yf.download('^BSESN', period='5d', interval='5m', progress=False)
        if isinstance(df_sensex.columns, pd.MultiIndex):
            df_sensex.columns = df_sensex.columns.get_level_values(0)

        # Filter to requested date
        df_nifty = df_nifty[df_nifty.index.strftime('%Y-%m-%d') == date_str].copy()
        df_sensex = df_sensex[df_sensex.index.strftime('%Y-%m-%d') == date_str].copy()

        # Fallback synthetic generation if holiday / missing
        if len(df_nifty) == 0:
            print(f"Notice: No live intraday ticks returned for {date_str}. Using previous available trading session.")
            # Use last available date
            df_all = yf.download('^NSEI', period='5d', interval='5m', progress=False)
            if isinstance(df_all.columns, pd.MultiIndex):
                df_all.columns = df_all.columns.get_level_values(0)
            last_date = df_all.index.strftime('%Y-%m-%d')[-1]
            df_nifty = df_all[df_all.index.strftime('%Y-%m-%d') == last_date].copy()
            
            df_s_all = yf.download('^BSESN', period='5d', interval='5m', progress=False)
            if isinstance(df_s_all.columns, pd.MultiIndex):
                df_s_all.columns = df_s_all.columns.get_level_values(0)
            df_sensex = df_s_all[df_s_all.index.strftime('%Y-%m-%d') == last_date].copy()

        return df_nifty, df_sensex

    def run_session(self, date_str: str) -> Dict:
        """
        Execute full day's trading session candle-by-candle (Idempotent).
        """
        # Idempotency: if session for this date is already finalized, return existing summary
        if self.ledger.has_snapshot_for_date(date_str):
            print(f"• Session for {date_str} is already reconciled in ledger. Returning existing record.", flush=True)
            trades = self.ledger.get_trades_for_date(date_str)
            account = self.ledger.get_account()

            gross_pnl = sum(t['gross_pnl'] for t in trades)
            charges = sum(t['brokerage'] + t['taxes'] for t in trades)
            net_pnl = sum(t['net_pnl'] for t in trades)

            return {
                "date": date_str,
                "total_trades": len(trades),
                "winning_trades": sum(1 for t in trades if t['net_pnl'] > 0),
                "losing_trades": sum(1 for t in trades if t['net_pnl'] <= 0),
                "gross_pnl": round(gross_pnl, 2),
                "total_charges": round(charges, 2),
                "net_pnl": round(net_pnl, 2),
                "closing_cash_balance": round(account['cash_balance'], 2),
                "trades": trades
            }

        print(f"\n=======================================================", flush=True)
        print(f"  STARTING PAPER TRADING SESSION FOR: {date_str}", flush=True)
        print(f"=======================================================", flush=True)

        self.nifty_engine.reset_session()
        self.sensex_engine.reset_session()

        df_nifty, df_sensex = self.fetch_intraday_data(date_str)
        print(f"Loaded {len(df_nifty)} candles for NIFTY and {len(df_sensex)} candles for SENSEX.", flush=True)

        # Common timestamps (09:15 to 15:30)
        all_times = sorted(list(set(df_nifty.index).union(set(df_sensex.index))))
        
        all_events = []

        for i, ts in enumerate(all_times):
            time_str = ts.strftime("%H:%M")

            # 1. Process SENSEX candle
            if ts in df_sensex.index:
                s_candle = df_sensex.loc[ts]
                s_hist = df_sensex.loc[:ts]
                s_events = self.sensex_engine.process_candle(s_candle, s_hist, date_str)
                for e in s_events:
                    all_events.append({"timestamp": ts, "strategy": "SENSEX_1LY", "event": e})

            # 2. Process NIFTY candle
            if ts in df_nifty.index:
                n_candle = df_nifty.loc[ts]
                n_hist = df_nifty.loc[:ts]
                n_events = self.nifty_engine.process_candle(n_candle, n_hist, date_str)
                for e in n_events:
                    all_events.append({"timestamp": ts, "strategy": "NIFTY_1165", "event": e})

        # Record daily snapshot in ledger
        self.ledger.record_daily_snapshot(date_str, notes="Daily Automated Paper Trading Session")

        # Fetch today's closed trades and snapshot
        trades = self.ledger.get_trades_for_date(date_str)
        account = self.ledger.get_account()

        gross_pnl = sum(t['gross_pnl'] for t in trades)
        charges = sum(t['brokerage'] + t['taxes'] for t in trades)
        net_pnl = sum(t['net_pnl'] for t in trades)

        summary = {
            "date": date_str,
            "total_trades": len(trades),
            "winning_trades": sum(1 for t in trades if t['net_pnl'] > 0),
            "losing_trades": sum(1 for t in trades if t['net_pnl'] <= 0),
            "gross_pnl": round(gross_pnl, 2),
            "total_charges": round(charges, 2),
            "net_pnl": round(net_pnl, 2),
            "closing_cash_balance": round(account['cash_balance'], 2),
            "trades": trades
        }

        return summary
