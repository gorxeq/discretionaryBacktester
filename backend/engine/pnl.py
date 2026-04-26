from typing import List, Dict
from datetime import date as date_type
from .market_data import MarketDataService

class PnLEngine:
    def __init__(self, market_data: MarketDataService):
        self.market_data = market_data

    def calculate_day_pnl(self, strategy: Dict, current_date: date_type, step: str) -> float:
        """
        Calculates PnL for the current step (DAY_OPEN or DAY_CLOSE).
        'strategy' contains legs with entry prices and current status.
        """
        total_pnl = 0.0
        
        for leg in strategy['legs']:
            option_type = leg['option_type']
            strike = leg['strike']
            expiry = leg['expiry']
            # qty already includes quantity_multiplier from strategy construction
            qty = leg['qty']
            
            # Convert string expiry back to date if needed
            if isinstance(expiry, str):
                from datetime import datetime
                expiry_dt = datetime.strptime(expiry, '%Y-%m-%d').date()
            else:
                expiry_dt = expiry
            
            if step == 'DAY_OPEN':
                # PnL = (Current Open - Previous Price) * Qty
                # Previous Price is entry_price if opened yesterday at close, 
                # or previous day's close price if carried.
                # For simplicity, we track 'last_valuation_price' in strategy state.
                curr_price = self.market_data.get_option_price(current_date, strike, option_type, expiry_dt, 'OPEN')
                prev_price = leg.get('last_valuation_price', leg['entry_price'])
                
                if curr_price is not None and prev_price is not None:
                    total_pnl += (curr_price - prev_price) * qty
                
                # Update valuation price for next step
                leg['last_valuation_price'] = curr_price
                
            elif step == 'DAY_CLOSE':
                # PnL = (Current Close - Previous Price) * Qty
                # Previous Price is today's Open price.
                curr_price = self.market_data.get_option_price(current_date, strike, option_type, expiry_dt, 'CLOSE')
                prev_price = leg.get('last_valuation_price', leg['entry_price'])
                
                if curr_price is not None and prev_price is not None:
                    total_pnl += (curr_price - prev_price) * qty
                
                # Update valuation price for next step
                leg['last_valuation_price'] = curr_price
                
        return total_pnl
