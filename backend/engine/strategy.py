from typing import List, Dict, Optional
from datetime import date as date_type
from .market_data import MarketDataService

class StrategyEngine:
    def __init__(self, market_data: MarketDataService):
        self.market_data = market_data

    def construct_strategy(self, direction_state: int, spot: float, date: date_type, quantity_multiplier: int = 1, overrides: Optional[List[dict]] = None):
        """
        Builds the legs for the selected strategy.
        Maps direction -2 to +2 to specific structures.
        """
        atm_strike = round(spot / 50) * 50
        legs = []
        
        if overrides:
            for ov in overrides:
                legs.append({
                    "option_type": ov["type"],
                    "strike": ov["strike"],
                    "qty": ov["qty"] * quantity_multiplier
                })
        else:
            # Base qty is 1 lot (will be multiplied by quantity_multiplier later)
            base_qty = 65  # 1 lot = 65 qty for Nifty (current lot size)
            
            if direction_state == -2:  # Naked Put Buy (Strong Bearish)
                legs.append({"option_type": "PUT", "strike": atm_strike - 100, "qty": base_qty})
            elif direction_state == -1:  # Bear Call Spread (Moderately Bearish)
                # Sell ATM+2 (100 pts OTM), Buy ATM+4 (200 pts OTM)
                legs.append({"option_type": "CALL", "strike": atm_strike + 100, "qty": -base_qty})
                legs.append({"option_type": "CALL", "strike": atm_strike + 200, "qty": base_qty})
            elif direction_state == 0:  # Short Strangle (Neutral)
                legs.append({"option_type": "CALL", "strike": atm_strike + 200, "qty": -base_qty})
                legs.append({"option_type": "PUT", "strike": atm_strike - 200, "qty": -base_qty})
            elif direction_state == +1:  # Bull Put Spread (Moderately Bullish)
                # Sell ATM-2 (100 pts OTM), Buy ATM-4 (200 pts OTM)
                legs.append({"option_type": "PUT", "strike": atm_strike - 100, "qty": -base_qty})
                legs.append({"option_type": "PUT", "strike": atm_strike - 200, "qty": base_qty})
            elif direction_state == +2:  # Naked Call Buy (Strong Bullish)
                legs.append({"option_type": "CALL", "strike": atm_strike + 100, "qty": base_qty})

        # Finalize legs with expiry and quantity multiplier
        final_legs = []
        
        # Get nearest expiry from market data service
        expiry = self.market_data.get_nearest_expiry(date)
        if not expiry:
            raise ValueError(f"Could not determine expiry for date {date}")

        for leg in legs:
            final_legs.append({
                "option_type": leg["option_type"],
                "strike": leg["strike"],
                "expiry": str(expiry),
                "qty": leg["qty"] * quantity_multiplier  # Apply multiplier only here
            })
            
        return final_legs

    def get_preview_metrics(self, legs: List[dict], direction_state: int = 0):
        """
        Calculate margin based on strategy type:
        - Naked buys (-2, +2): Estimated premium (~₹5000/lot as placeholder)
        - Spreads (-1, +1): Strike difference × qty (qty already includes multiplier)
        - Strangle (0): ₹2 lakhs per lot
        """
        lot_size = 65
        
        # Get total lots from legs (qty includes lot_size * multiplier)
        total_qty = abs(legs[0]["qty"]) if legs else lot_size
        lots = total_qty // lot_size
        
        if direction_state in [-2, +2]:
            # Naked buying - margin is premium. Estimate ~₹5000 per lot as placeholder
            margin = 5000 * lots
            max_loss = margin
        elif direction_state in [-1, +1]:
            # Spreads - margin = max loss = strike difference × total qty
            strikes = [leg["strike"] for leg in legs]
            strike_diff = abs(max(strikes) - min(strikes))
            margin = strike_diff * total_qty
            max_loss = margin
        elif direction_state == 0:
            # Short Strangle - ₹2 lakhs per lot
            margin = 200000 * lots
            max_loss = 0.0  # Unlimited risk, show 0 placeholder
        else:
            margin = 0.0
            max_loss = 0.0
            
        return {
            "margin_required": margin,
            "max_profit": 0.0,  # TBD or placeholder
            "max_loss": max_loss
        }
