import sys
from pathlib import Path
from datetime import date


# Add backend to path
sys.path.append(str(Path.cwd()))

from backend.engine.market_data import MarketDataService

def test_data_loading():
    # Use actual paths relative to current execution
    md = MarketDataService(data_root="data", nifty_root="nifty")
    
    # Test Date we know exists (from `ls` earlier: 2021-02-04)
    test_date = date(2021, 2, 4)
    
    # 1. Test Spot Candle
    spot = md.get_spot_candle(test_date)
    assert spot is not None
    print(f"Spot loaded: {spot}")
    
    # 2. Test Available Strikes
    # This calls _get_day_options internally
    strikes = md.get_available_strikes(test_date)
    assert len(strikes) > 0
    print(f"Loaded {len(strikes)} strikes")
    
    # 3. Test Option Price
    # Pick a strike from the loaded strikes
    strike_price = list(strikes.keys())[0]
    
    # Get available option types for this strike
    opts = strikes[strike_price]
    opt_type = 'CALL' if opts.get('CALL') else 'PUT'
    
    # We need to find the expiry. get_available_strikes uses nearest expiry.
    # Let's get nearest expiry explicitly
    expiry = md.get_nearest_expiry(test_date)
    assert expiry is not None
    print(f"Nearest expiry: {expiry}")
    
    price = md.get_option_price(test_date, strike_price, opt_type, expiry, 'OPEN')
    assert price is not None
    print(f"Price for {strike_price} {opt_type}: {price}")

if __name__ == "__main__":
    test_data_loading()
