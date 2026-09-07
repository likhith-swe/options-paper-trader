"""
Virtual Paper Broker & Order Execution Engine
Simulates realistic order fills, bid-ask spread slippage, and statutory exchange charges.
"""

import math
from typing import Dict, Optional
from config.settings import BrokerCostSettings, PortfolioSettings
from database.ledger import LedgerDB

class PaperBroker:
    def __init__(self, ledger: LedgerDB):
        self.ledger = ledger
        self.costs = BrokerCostSettings()
        self.portfolio_cfg = PortfolioSettings()

    def calculate_charges(self, price: float, quantity: int, is_buy: bool) -> float:
        """
        Calculate complete SEBI, Exchange, STT, Stamp Duty, Brokerage, and GST charges.
        STT applies only on SELL turnover for options (0.1% of premium value).
        Stamp duty applies only on BUY turnover (0.003%).
        """
        turnover = price * quantity
        brokerage = self.costs.flat_brokerage_per_order
        txn_charge = turnover * self.costs.exchange_txn_charge_rate
        sebi_charge = turnover * self.costs.sebi_turnover_rate
        gst = (brokerage + txn_charge + sebi_charge) * self.costs.gst_rate

        if is_buy:
            stamp_duty = turnover * self.costs.stamp_duty_buy
            stt = 0.0
        else:
            stamp_duty = 0.0
            stt = turnover * self.costs.stt_rate_sell

        total_charges = brokerage + txn_charge + sebi_charge + gst + stamp_duty + stt
        return round(total_charges, 2)

    def calculate_slippage(self, base_price: float, quantity: int, is_buy: bool, underlying: str) -> float:
        """
        Simulate realistic bid-ask spread and queue depletion friction:
        - NIFTY: ~0.30 - 0.70 pts for 1-10 lots.
        - SENSEX: ~0.60 - 1.50 pts for 1-10 lots.
        """
        lots = quantity / (self.portfolio_cfg.nifty_lot_size if underlying == "NIFTY" else self.portfolio_cfg.sensex_lot_size)
        base_spread = 0.35 if underlying == "NIFTY" else 0.85
        impact = base_spread * (1.0 + 0.04 * math.sqrt(max(1.0, lots)))
        
        # Slippage hurts: buy at ask (higher), sell at bid (lower)
        if is_buy:
            return round(base_price + impact, 2)
        else:
            return round(max(1.0, base_price - impact), 2)

    def execute_buy(
        self,
        trade_id: str,
        trade_date: str,
        strategy: str,
        instrument: str,
        underlying: str,
        option_type: str,
        nominal_price: float,
        quantity: int,
        entry_time: str
    ) -> Dict:
        """Execute a simulated paper buy order."""
        # 1. Calculate realistic fill price with slippage
        fill_price = self.calculate_slippage(nominal_price, quantity, is_buy=True, underlying=underlying)
        initial_margin = round(fill_price * quantity, 2)
        entry_charges = self.calculate_charges(fill_price, quantity, is_buy=True)

        # 2. Check margin balance in ledger
        account = self.ledger.get_account()
        cash_avail = account.get("cash_balance", 0.0)

        if cash_avail < (initial_margin + entry_charges):
            raise ValueError(
                f"Insufficient funds: Required ₹{initial_margin + entry_charges:,.2f}, Available: ₹{cash_avail:,.2f}"
            )

        # 3. Log trade entry to SQLite ledger
        self.ledger.log_trade_entry(
            trade_id=trade_id,
            trade_date=trade_date,
            strategy=strategy,
            instrument=instrument,
            underlying=underlying,
            option_type=option_type,
            quantity=quantity,
            entry_time=entry_time,
            entry_price=fill_price,
            initial_margin=initial_margin,
            entry_charges=entry_charges
        )

        return {
            "trade_id": trade_id,
            "status": "FILLED",
            "fill_price": fill_price,
            "quantity": quantity,
            "initial_margin": initial_margin,
            "entry_charges": entry_charges
        }

    def execute_sell(
        self,
        trade_id: str,
        nominal_price: float,
        quantity: int,
        exit_time: str,
        exit_reason: str,
        initial_margin: float,
        underlying: str
    ) -> Dict:
        """Execute a simulated paper sell order closing an open position."""
        fill_price = self.calculate_slippage(nominal_price, quantity, is_buy=False, underlying=underlying)
        exit_proceeds = round(fill_price * quantity, 2)
        exit_charges = self.calculate_charges(fill_price, quantity, is_buy=False)

        res = self.ledger.log_trade_exit(
            trade_id=trade_id,
            exit_time=exit_time,
            exit_price=fill_price,
            exit_reason=exit_reason,
            initial_margin=initial_margin,
            exit_proceeds=exit_proceeds,
            exit_charges=exit_charges
        )
        res["exit_fill_price"] = fill_price
        res["exit_proceeds"] = exit_proceeds
        res["exit_charges"] = exit_charges
        return res
