"""
Unit Test Suite for Autonomous Paper Trading Bot
"""

import os
import unittest
import datetime
from database.ledger import LedgerDB
from execution.option_model import OptionPricingModel
from execution.paper_broker import PaperBroker
from config.settings import PortfolioSettings

class TestPaperTradingBot(unittest.TestCase):
    def setUp(self):
        # Use a temporary test database
        self.test_db = "/Users/likhith/.gemini/antigravity/scratch/options-paper-trader/data/test_paper.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        self.ledger = LedgerDB(self.test_db)
        self.broker = PaperBroker(self.ledger)

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_account_initialization(self):
        acc = self.ledger.get_account()
        self.assertEqual(acc["initial_balance"], 1000000.0)
        self.assertEqual(acc["cash_balance"], 1000000.0)
        self.assertEqual(acc["allocated_margin"], 0.0)

    def test_strike_resolution(self):
        # NIFTY nearest 50
        self.assertEqual(OptionPricingModel.get_atm_strike(23883.0, "NIFTY"), 23900)
        self.assertEqual(OptionPricingModel.get_atm_strike(23820.0, "NIFTY"), 23800)
        # SENSEX nearest 100
        self.assertEqual(OptionPricingModel.get_atm_strike(76446.0, "SENSEX"), 76400)
        self.assertEqual(OptionPricingModel.get_atm_strike(76477.0, "SENSEX"), 76500)

    def test_paper_trade_lifecycle(self):
        # Execute BUY order
        buy_res = self.broker.execute_buy(
            trade_id="T-TEST-001",
            trade_date="2026-09-07",
            strategy="NIFTY_1165",
            instrument="NIFTY24SEP23900CE",
            underlying="NIFTY",
            option_type="CE",
            nominal_price=150.0,
            quantity=100, # 4 lots
            entry_time="2026-09-07 09:50:00"
        )
        self.assertEqual(buy_res["status"], "FILLED")
        self.assertGreater(buy_res["fill_price"], 150.0) # slippage applied
        
        acc = self.ledger.get_account()
        self.assertLess(acc["cash_balance"], 1000000.0)
        self.assertGreater(acc["allocated_margin"], 0.0)

        # Execute SELL order with profit (+30 points)
        sell_res = self.broker.execute_sell(
            trade_id="T-TEST-001",
            nominal_price=185.0,
            quantity=100,
            exit_time="2026-09-07 10:45:00",
            exit_reason="TARGET_HIT_+30%",
            initial_margin=buy_res["initial_margin"],
            underlying="NIFTY"
        )
        self.assertGreater(sell_res["gross_pnl"], 0.0)
        self.assertGreater(sell_res["net_pnl"], 0.0)

        acc_after = self.ledger.get_account()
        self.assertEqual(acc_after["allocated_margin"], 0.0)
        self.assertGreater(acc_after["cash_balance"], 1000000.0)

if __name__ == "__main__":
    unittest.main()
