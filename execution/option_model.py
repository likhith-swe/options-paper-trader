"""
Option Pricing Model & ATM Strike Resolver
Accurately models option premium fluctuations, Greeks (Delta ~0.50), and intraday theta decay.
"""

import math
import datetime
from typing import Dict, Tuple

class OptionPricingModel:
    @staticmethod
    def get_atm_strike(spot_price: float, underlying: str = "NIFTY") -> int:
        """Resolve nearest ATM strike price."""
        if underlying == "NIFTY":
            step = 50
        else: # SENSEX
            step = 100
        return int(round(spot_price / step) * step)

    @staticmethod
    def get_instrument_name(underlying: str, strike: int, option_type: str, trade_date: str) -> str:
        """Format exchange instrument code, e.g. NIFTY24SEP23850CE or SENSEX24SEP76400PE."""
        dt = datetime.datetime.strptime(trade_date, "%Y-%m-%d")
        month_code = dt.strftime("%b").upper()
        year_code = dt.strftime("%y")
        return f"{underlying}{year_code}{month_code}{strike}{option_type.upper()}"

    @staticmethod
    def estimate_initial_atm_premium(spot_price: float, underlying: str = "NIFTY", vix: float = 14.0) -> float:
        """
        Estimate morning opening ATM premium based on spot and historical volatility.
        Typical NIFTY ATM: ₹120 - ₹180.
        Typical SENSEX ATM: ₹350 - ₹550.
        """
        if underlying == "NIFTY":
            # Roughly 0.6% - 0.75% of spot on non-expiry mornings
            base = spot_price * 0.0065 * (vix / 13.5)
            return round(max(90.0, min(240.0, base)), 2)
        else: # SENSEX
            base = spot_price * 0.0055 * (vix / 13.5)
            return round(max(280.0, min(650.0, base)), 2)

    @staticmethod
    def compute_option_price(
        entry_spot: float,
        current_spot: float,
        entry_premium: float,
        option_type: str,
        entry_time: datetime.datetime,
        current_time: datetime.datetime,
        strike: int
    ) -> float:
        """
        Compute dynamic option premium as spot moves, incorporating:
        1. Delta ~0.50 (ATM sensitivity) with Gamma curvature
        2. Intraday Theta decay (time elapsed between entry and current tick)
        """
        delta_spot = current_spot - entry_spot
        
        # Elapsed trading minutes (out of 375 daily minutes)
        elapsed_minutes = max(0.0, (current_time - entry_time).total_seconds() / 60.0)
        
        # Base Delta: Call is +0.50, Put is -0.50
        # Gamma effect: as in-the-money depth increases, delta shifts towards 0.65; OTM shifts towards 0.35
        if option_type == "CE":
            moneyness = (current_spot - strike) / (strike * 0.01) # percent ITM/OTM
            effective_delta = 0.50 + max(-0.25, min(0.25, moneyness * 0.05))
            spot_contribution = delta_spot * effective_delta
        else: # PE
            moneyness = (strike - current_spot) / (strike * 0.01)
            effective_delta = 0.50 + max(-0.25, min(0.25, moneyness * 0.05))
            spot_contribution = -delta_spot * effective_delta

        # Theta Decay: ~8% to 15% daily decay across 375 minutes
        # Faster decay between 12:00 PM and 15:30 PM
        current_hour = current_time.hour + current_time.minute / 60.0
        decay_rate = 0.00035 if current_hour < 12.0 else 0.00065
        theta_decay = entry_premium * (decay_rate * elapsed_minutes)

        estimated_premium = entry_premium + spot_contribution - theta_decay
        # Minimum intrinsic boundary: if ITM, cannot be less than intrinsic value
        if option_type == "CE":
            intrinsic = max(0.0, current_spot - strike)
        else:
            intrinsic = max(0.0, strike - current_spot)

        return round(max(max(5.0, intrinsic), estimated_premium), 2)
