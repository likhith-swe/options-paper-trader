"""
SENSEX 1lyAlgos Early Momentum Catcher Engine
Implements Opening Range Breakout + 40-pt Hard Stop Loss + 12:00 PM Hard Time Cutoff.
"""

import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from config.settings import Sensex1lySettings, PortfolioSettings
from execution.option_model import OptionPricingModel
from execution.paper_broker import PaperBroker

class Sensex1lyEngine:
    def __init__(self, broker: PaperBroker):
        self.broker = broker
        self.cfg = Sensex1lySettings()
        self.port_cfg = PortfolioSettings()
        self.reset_session()

    def reset_session(self):
        """Reset intraday state variables."""
        self.active_position: Optional[Dict] = None
        self.trades_taken_today: int = 0
        self.opening_range_high: Optional[float] = None
        self.opening_range_low: Optional[float] = None
        self.opening_range_recorded: bool = False
        self.trade_counter: int = 0

    def process_candle(
        self,
        current_candle: pd.Series,
        history_df: pd.DataFrame,
        trade_date_str: str
    ) -> List[Dict]:
        """
        Process incoming candle tick for SENSEX.
        Enforces 1 trade/day, 40-pt SL, and 12:00 PM cutoff.
        """
        executed_actions = []
        dt = current_candle.name
        if isinstance(dt, str):
            dt = pd.to_datetime(dt)
            
        time_str = dt.strftime("%H:%M")
        current_spot = float(current_candle['Close'])

        # -------------------------------------------------------------
        # 1. RECORD OPENING RANGE (09:15 to 09:30 AM)
        # -------------------------------------------------------------
        if not self.opening_range_recorded:
            if time_str <= "09:30":
                # Collect candles up to 09:30
                or_df = history_df[history_df.index.strftime("%H:%M") <= "09:30"]
                if len(or_df) >= 3: # at least 3 x 5m candles or 5 x 3m candles
                    self.opening_range_high = float(or_df['High'].max())
                    self.opening_range_low = float(or_df['Low'].min())
                    self.opening_range_recorded = True
            return executed_actions

        # -------------------------------------------------------------
        # 2. EVALUATE ACTIVE POSITION IF OPEN
        # -------------------------------------------------------------
        if self.active_position is not None:
            pos = self.active_position
            opt_type = pos['option_type']
            entry_px = pos['entry_premium']
            strike = pos['strike']
            qty = pos['quantity']
            
            curr_prem = OptionPricingModel.compute_option_price(
                entry_spot=pos['entry_spot'],
                current_spot=current_spot,
                entry_premium=entry_px,
                option_type=opt_type,
                entry_time=pos['entry_time_dt'],
                current_time=dt,
                strike=strike
            )
            
            points_diff = curr_prem - entry_px
            
            # Trailing Stop Loss to Cost if profit crosses +60 points
            if points_diff >= self.cfg.trailing_trigger_points:
                pos['trailing_active'] = True

            # Exit Condition A: Target Hit (+80 points)
            if points_diff >= self.cfg.target_points:
                res = self.broker.execute_sell(
                    trade_id=pos['trade_id'],
                    nominal_price=curr_prem,
                    quantity=qty,
                    exit_time=dt.strftime("%Y-%m-%d %H:%M:%S"),
                    exit_reason="TARGET_HIT_+80_PTS",
                    initial_margin=pos['initial_margin'],
                    underlying="SENSEX"
                )
                executed_actions.append(res)
                self.active_position = None

            # Exit Condition B: Stop Loss Hit (40 points below entry)
            elif points_diff <= -self.cfg.hard_stop_loss_points:
                res = self.broker.execute_sell(
                    trade_id=pos['trade_id'],
                    nominal_price=curr_prem,
                    quantity=qty,
                    exit_time=dt.strftime("%Y-%m-%d %H:%M:%S"),
                    exit_reason="STOP_LOSS_-40_PTS",
                    initial_margin=pos['initial_margin'],
                    underlying="SENSEX"
                )
                executed_actions.append(res)
                self.active_position = None

            # Exit Condition C: Breakeven Stop if trailing active and price falls back
            elif pos.get('trailing_active', False) and points_diff <= 0.0:
                res = self.broker.execute_sell(
                    trade_id=pos['trade_id'],
                    nominal_price=curr_prem,
                    quantity=qty,
                    exit_time=dt.strftime("%Y-%m-%d %H:%M:%S"),
                    exit_reason="TRAILING_STOP_AT_COST",
                    initial_margin=pos['initial_margin'],
                    underlying="SENSEX"
                )
                executed_actions.append(res)
                self.active_position = None

            # Exit Condition D: Mandatory Pre-Noon Hard Cutoff (12:00 PM Sharp)
            elif time_str >= self.cfg.hard_time_cutoff:
                res = self.broker.execute_sell(
                    trade_id=pos['trade_id'],
                    nominal_price=curr_prem,
                    quantity=qty,
                    exit_time=dt.strftime("%Y-%m-%d %H:%M:%S"),
                    exit_reason="TIME_CUTOFF_12:00_PM",
                    initial_margin=pos['initial_margin'],
                    underlying="SENSEX"
                )
                executed_actions.append(res)
                self.active_position = None

        # -------------------------------------------------------------
        # 3. EVALUATE NEW BREAKOUT ENTRY (STRICTLY 1 TRADE / DAY)
        # -------------------------------------------------------------
        if self.active_position is None and self.trades_taken_today < self.cfg.max_trades_per_day:
            # Must be before 11:30 AM for entry
            if time_str >= "11:30":
                return executed_actions

            if self.opening_range_high and current_spot > self.opening_range_high:
                # Bullish Breakout -> BUY ATM CE
                res = self._enter_trade(
                    spot=current_spot,
                    dt=dt,
                    trade_date_str=trade_date_str,
                    opt_type="CE",
                    reason="OPENING_RANGE_HIGH_BREAKOUT"
                )
                if res:
                    executed_actions.append(res)

            elif self.opening_range_low and current_spot < self.opening_range_low:
                # Bearish Breakdown -> BUY ATM PE
                res = self._enter_trade(
                    spot=current_spot,
                    dt=dt,
                    trade_date_str=trade_date_str,
                    opt_type="PE",
                    reason="OPENING_RANGE_LOW_BREAKDOWN"
                )
                if res:
                    executed_actions.append(res)

        return executed_actions

    def _enter_trade(
        self,
        spot: float,
        dt: datetime.datetime,
        trade_date_str: str,
        opt_type: str,
        reason: str
    ) -> Optional[Dict]:
        """Execute buy order for SENSEX ATM option."""
        strike = OptionPricingModel.get_atm_strike(spot, underlying="SENSEX")
        instrument = OptionPricingModel.get_instrument_name("SENSEX", strike, opt_type, trade_date_str)
        initial_prem = OptionPricingModel.estimate_initial_atm_premium(spot, underlying="SENSEX")
        
        # SENSEX allocation is ₹2,00,000 baseline
        # Standard lot size: 20 units. Max capital deployed ~ ₹40,000 (roughly 4 to 5 lots)
        lots = max(2, int(40000.0 / (initial_prem * self.port_cfg.sensex_lot_size)))
        total_quantity = lots * self.port_cfg.sensex_lot_size

        self.trade_counter += 1
        trade_id = f"SENSEX-{trade_date_str.replace('-','')}-{self.trade_counter:03d}"
        
        try:
            fill_res = self.broker.execute_buy(
                trade_id=trade_id,
                trade_date=trade_date_str,
                strategy="SENSEX_1LY",
                instrument=instrument,
                underlying="SENSEX",
                option_type=opt_type,
                nominal_price=initial_prem,
                quantity=total_quantity,
                entry_time=dt.strftime("%Y-%m-%d %H:%M:%S")
            )
            
            self.active_position = {
                "trade_id": trade_id,
                "instrument": instrument,
                "option_type": opt_type,
                "strike": strike,
                "quantity": total_quantity,
                "entry_premium": fill_res['fill_price'],
                "entry_spot": spot,
                "entry_time_dt": dt,
                "initial_margin": fill_res['initial_margin'],
                "trailing_active": False,
                "reason": reason
            }
            self.trades_taken_today += 1
            fill_res["reason"] = reason
            fill_res["instrument"] = instrument
            return fill_res
            
        except ValueError as e:
            print(f"[SENSEX_1LY] Margin check failed: {e}")
            return None
