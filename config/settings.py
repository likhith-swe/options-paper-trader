"""
Portfolio & Strategy Configuration Settings
Autonomous Paper Trading Engine: ₹10 Lakhs Starting Balance
"""

import os
from dataclasses import dataclass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "paper_trader.db")

@dataclass
class BrokerCostSettings:
    flat_brokerage_per_order: float = 20.0       # ₹20 flat per executed order
    stt_rate_sell: float = 0.001                 # 0.1% Securities Transaction Tax on Sell turnover
    exchange_txn_charge_rate: float = 0.0005     # ~0.05% Exchange turnover fee
    sebi_turnover_rate: float = 0.000001         # ₹10 per Crore SEBI charge
    stamp_duty_buy: float = 0.00003              # 0.003% Stamp duty on buy turnover
    gst_rate: float = 0.18                       # 18% GST on (brokerage + txn charges + sebi)

@dataclass
class PortfolioSettings:
    initial_cash: float = 1000000.0              # ₹ 10,00,000.00 (10 Lakhs Total Portfolio)
    nifty_capital_allocation: float = 800000.0   # 80% (₹ 8,00,000)
    sensex_capital_allocation: float = 200000.0  # 20% (₹ 2,00,000)
    
    # Lot Sizing
    nifty_lot_size: int = 25                     # 25 units per lot
    sensex_lot_size: int = 20                    # 20 units per lot (BSE Sensex standard lot)
    
    # Capital per Lot Limits
    nifty_max_capital_per_lot: float = 100000.0  # ~8 to 10 lots deployed max
    sensex_max_capital_per_lot: float = 25000.0  # ~8 to 10 lots deployed max

@dataclass
class Nifty1165Settings:
    supertrend_period: int = 10
    supertrend_multiplier: float = 2.0
    fast_ema_period: int = 9
    slow_ema_period: int = 20
    stop_loss_pct: float = 0.15                  # -15% stop loss on entry premium
    target_pct: float = 0.30                     # +30% target on premium
    trailing_sl_pct: float = 0.15                # 15% trailing stop once +30% reached
    martingale_multiplier: float = 2.0           # 2x sizing on stop loss reverse
    noise_quarantine_cutoff_time: str = "09:45"  # No entries 09:15 to 09:45
    session_cutoff_time: str = "15:14"           # Unconditional intraday squareoff

@dataclass
class Sensex1lySettings:
    opening_range_minutes: int = 15              # 09:15 to 09:30 opening range
    hard_stop_loss_points: float = 40.0          # 40 fixed points below entry
    target_points: float = 80.0                  # +80 points baseline target
    trailing_trigger_points: float = 60.0        # Trail SL to cost at +60 points
    hard_time_cutoff: str = "12:00"              # Mandatory pre-noon exit at 12:00 PM
    max_trades_per_day: int = 1                  # Strictly 1 trade per day
