"""
Daily Automated Background Daemon
Schedules and orchestrates daily algorithmic trading sessions on market days (Monday to Friday).
"""

import time
import datetime
import traceback
from database.ledger import LedgerDB
from scheduler.session_runner import SessionRunner
from reporting.notifier import TradeNotifier

class DailyTradingDaemon:
    def __init__(self):
        self.ledger = LedgerDB()
        self.runner = SessionRunner(self.ledger)

    def is_market_day(self, dt: datetime.date) -> bool:
        """Return True if weekday (Monday=0 to Friday=4)."""
        return dt.weekday() < 5

    def run_daily_loop(self):
        """Continuous loop monitoring clock and executing sessions."""
        print("================================================================", flush=True)
        print("  🚀 CHRONOS OPTIONS PAPER TRADING DAEMON ACTIVATED", flush=True)
        print("  Portfolio Capital: ₹ 10,00,000.00 | Active Mon - Fri", flush=True)
        print("================================================================", flush=True)

        now = datetime.datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        # Check if today's session has already been finalized
        if self.ledger.has_snapshot_for_date(today_str):
            last_executed_date = today_str
            print(f"[{now.strftime('%H:%M:%S')}] Market session for {today_str} is already reconciled.", flush=True)
        else:
            last_executed_date = None

        while True:
            now = datetime.datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M")

            # Check if market day
            if self.is_market_day(now.date()):
                # Session trigger: 15:31 PM (reconciliation window)
                if time_str >= "15:31" and last_executed_date != today_str:
                    print(f"[{now.strftime('%H:%M:%S')}] Market closed for {today_str}. Reconciling day's session...", flush=True)
                    try:
                        summary = self.runner.run_session(today_str)
                        recap = TradeNotifier.dispatch(summary)
                        print(recap, flush=True)
                        last_executed_date = today_str
                    except Exception as e:
                        print(f"Error during daily session execution: {e}", flush=True)
                        traceback.print_exc()

                elif "09:15" <= time_str <= "15:30":
                    # During market hours
                    print(f"[{now.strftime('%H:%M:%S')}] Live market window active. Monitoring ticks...", flush=True)

            else:
                print(f"[{now.strftime('%H:%M:%S')}] Weekend / Market Closed. Next session Monday 09:15 AM.", flush=True)

            # Sleep 30 seconds before next check
            time.sleep(30)
