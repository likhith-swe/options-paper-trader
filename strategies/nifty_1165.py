"""
NIFTY 50 Quantman Strategy 1165 Engine
Implements 4-Case Multi-Regime Indicator Alignment + 2x Asymmetric Martingale Recovery.
"""

import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from config.settings import Nifty1165Settings, PortfolioSettings
from execution.option_model import OptionPricingModel
from execution.paper_broker import PaperBroker

class Nifty1165Engine:
    def __init__(self, broker: PaperBroker):
        self.broker = broker
        self.cfg = Nifty1165Settings()
        self.port_cfg = PortfolioSettings()
        self.reset_session()

    def reset_session(self):
        """Reset intraday state variables."""
        self.active_position: Optional[Dict] = None
        self.martingale_level: int = 1       # Sizing: 1x base, 2x after SL
        self.total_trades_today: int = 0
        self.trade_counter: int = 0

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Vectorized computation of Supertrend (10, 2), 9/20 EMA, and VWAP."""
        df = df.copy()
        high = df['High'].values
        low = df['Low'].values
        close = df['Close'].values
        vol = df['Volume'].values if 'Volume' in df.columns else np.ones(len(df))
        
        # 1. Dual EMA
        df['ema_fast'] = df['Close'].ewm(span=self.cfg.fast_ema_period, adjust=False).mean()
        df['ema_slow'] = df['Close'].ewm(span=self.cfg.slow_ema_period, adjust=False).mean()

        # 2. VWAP
        cum_vol = np.cumsum(vol)
        cum_vol[cum_vol == 0] = 1.0 # avoid div by zero
        cum_pv = np.cumsum(close * vol)
        df['vwap'] = cum_pv / cum_vol

        # 3. Supertrend (10, 2)
        n = len(df)
        atr_period = self.cfg.supertrend_period
        multiplier = self.cfg.supertrend_multiplier

        # True Range
        tr = np.zeros(n)
        for i in range(1, n):
            tr[i] = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
        if n > 0:
            tr[0] = high[0] - low[0]
            
        atr = pd.Series(tr).rolling(window=atr_period, min_periods=1).mean().values
        
        upper_band = (high + low) / 2.0 + multiplier * atr
        lower_band = (high + low) / 2.0 - multiplier * atr
        
        supertrend = np.zeros(n)
        direction = np.ones(n) # 1 = Bullish, -1 = Bearish
        
        for i in range(1, n):
            if close[i] > upper_band[i-1]:
                direction[i] = 1
            elif close[i] < lower_band[i-1]:
                direction[i] = -1
            else:
                direction[i] = direction[i-1]
                if direction[i] == 1 and lower_band[i] < lower_band[i-1]:
                    lower_band[i] = lower_band[i-1]
                if direction[i] == -1 and upper_band[i] > upper_band[i-1]:
                    upper_band[i] = upper_band[i-1]
                    
            supertrend[i] = lower_band[i] if direction[i] == 1 else upper_band[i]

        df['supertrend'] = supertrend
        df['supertrend_bullish'] = direction == 1
        return df

    def process_candle(
        self,
        current_candle: pd.Series,
        history_df: pd.DataFrame,
        trade_date_str: str
    ) -> List[Dict]:
        """
        Process incoming candle tick.
        Evaluates active trade risk/profit, 15:14 cutoff, and new entry signals.
        """
        executed_actions = []
        dt = current_candle.name
        if isinstance(dt, str):
            dt = pd.to_datetime(dt)
            
        time_str = dt.strftime("%H:%M")
        current_spot = float(current_candle['Close'])

        # Compute technical indicators
        df_ind = self.compute_indicators(history_df)
        latest = df_ind.iloc[-1]
        
        st_bullish = bool(latest['supertrend_bullish'])
        ema_bullish = bool(latest['ema_fast'] > latest['ema_slow'])
        above_vwap = bool(latest['Close'] > latest['vwap'])

        # -------------------------------------------------------------
        # 1. EVALUATE ACTIVE POSITION IF OPEN
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
            
            pnl_pct = (curr_prem - entry_px) / entry_px
            
            # Check Exit Condition A: Target Hit (+30%)
            if pnl_pct >= self.cfg.target_pct:
                res = self.broker.execute_sell(
                    trade_id=pos['trade_id'],
                    nominal_price=curr_prem,
                    quantity=qty,
                    exit_time=dt.strftime("%Y-%m-%d %H:%M:%S"),
                    exit_reason="TARGET_HIT_+30%",
                    initial_margin=pos['initial_margin'],
                    underlying="NIFTY"
                )
                executed_actions.append(res)
                self.active_position = None
                self.martingale_level = 1 # Reset to 1x on win

            # Check Exit Condition B: Stop Loss Hit (-15%) -> TRIGGER 2X MARTINGALE INVERSION
            elif pnl_pct <= -self.cfg.stop_loss_pct:
                res = self.broker.execute_sell(
                    trade_id=pos['trade_id'],
                    nominal_price=curr_prem,
                    quantity=qty,
                    exit_time=dt.strftime("%Y-%m-%d %H:%M:%S"),
                    exit_reason="STOP_LOSS_-15%",
                    initial_margin=pos['initial_margin'],
                    underlying="NIFTY"
                )
                executed_actions.append(res)
                self.active_position = None
                
                # Reverse direction immediately with 2x multiplier
                reverse_type = "PE" if opt_type == "CE" else "CE"
                self.martingale_level = 2 # 2x Martingale recovery
                
                # Check if before 15:00 for reversal
                if time_str < "15:00":
                    inv_res = self._enter_trade(
                        spot=current_spot,
                        dt=dt,
                        trade_date_str=trade_date_str,
                        opt_type=reverse_type,
                        reason="MARTINGALE_2X_INVERSION"
                    )
                    if inv_res:
                        executed_actions.append(inv_res)

            # Check Exit Condition C: Mandatory Session Cutoff (15:14)
            elif time_str >= self.cfg.session_cutoff_time:
                res = self.broker.execute_sell(
                    trade_id=pos['trade_id'],
                    nominal_price=curr_prem,
                    quantity=qty,
                    exit_time=dt.strftime("%Y-%m-%d %H:%M:%S"),
                    exit_reason="SESSION_CUTOFF_15:14",
                    initial_margin=pos['initial_margin'],
                    underlying="NIFTY"
                )
                executed_actions.append(res)
                self.active_position = None
                self.martingale_level = 1

        # -------------------------------------------------------------
        # 2. EVALUATE NEW ENTRIES IF NO ACTIVE POSITION
        # -------------------------------------------------------------
        if self.active_position is None:
            # Check noise quarantine (09:15 to 09:45 lockout)
            if time_str < self.cfg.noise_quarantine_cutoff_time:
                return executed_actions # Quarantined
                
            # No new trades after 15:00
            if time_str >= "15:00":
                return executed_actions

            # Case 1: Bullish Entry (Supertrend + EMA + VWAP all Bullish)
            if st_bullish and ema_bullish and above_vwap:
                res = self._enter_trade(
                    spot=current_spot,
                    dt=dt,
                    trade_date_str=trade_date_str,
                    opt_type="CE",
                    reason="CASE_1_BULLISH_ALIGNMENT"
                )
                if res:
                    executed_actions.append(res)

            # Case 2: Bearish Entry (Supertrend + EMA + VWAP all Bearish)
            elif (not st_bullish) and (not ema_bullish) and (not above_vwap):
                res = self._enter_trade(
                    spot=current_spot,
                    dt=dt,
                    trade_date_str=trade_date_str,
                    opt_type="PE",
                    reason="CASE_2_BEARISH_ALIGNMENT"
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
        """Execute buy order and record active position in memory."""
        strike = OptionPricingModel.get_atm_strike(spot, underlying="NIFTY")
        instrument = OptionPricingModel.get_instrument_name("NIFTY", strike, opt_type, trade_date_str)
        initial_prem = OptionPricingModel.estimate_initial_atm_premium(spot, underlying="NIFTY")
        
        # Sizing: NIFTY capital is ₹8,00,000 baseline
        # Max deploy per trade ~ ₹1,00,000 (roughly 12.5% of NIFTY pot) * martingale_multiplier
        base_lots = max(2, int(80000.0 / (initial_prem * self.port_cfg.nifty_lot_size)))
        actual_lots = base_lots * self.martingale_level
        total_quantity = actual_lots * self.port_cfg.nifty_lot_size

        self.trade_counter += 1
        trade_id = f"NIFTY-{trade_date_str.replace('-','')}-{self.trade_counter:03d}"
        
        try:
            fill_res = self.broker.execute_buy(
                trade_id=trade_id,
                trade_date=trade_date_str,
                strategy="NIFTY_1165",
                instrument=instrument,
                underlying="NIFTY",
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
                "reason": reason
            }
            self.total_trades_today += 1
            fill_res["reason"] = reason
            fill_res["instrument"] = instrument
            return fill_res
            
        except ValueError as e:
            print(f"[NIFTY_1165] Margin check failed: {e}")
            return None
