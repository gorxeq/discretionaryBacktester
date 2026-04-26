"""Manual PnL verification script for options replay engine."""
import pandas as pd
from datetime import date, timedelta

# Load spot data
spot_df = pd.read_parquet('data/nifty_daily.parquet')
spot_df['date'] = pd.to_datetime(spot_df['date']).dt.date

# Convert expiry_date to date
if 'expiry_date' in spot_df.columns:
    spot_df['expiry_date'] = pd.to_datetime(spot_df['expiry_date']).dt.date

# Find dates with 3+ days to expiry (for overnight testing)
spot_df['dte'] = spot_df.apply(lambda row: (row['expiry_date'] - row['date']).days if isinstance(row['expiry_date'], date) else 0, axis=1)

good_dates = spot_df[(spot_df['dte'] >= 3) & (spot_df['date'] >= date(2021, 1, 1))].head(5)
print("=== GOOD TEST DATES (3+ DTE) ===")
for _, row in good_dates.iterrows():
    print(f"{row['date']} -> Expiry: {row['expiry_date']} ({row['dte']} DTE), O={row['open']:.2f}, C={row['close']:.2f}")

# Pick first good date
if len(good_dates) > 0:
    test_date = good_dates.iloc[0]['date']
    expiry = good_dates.iloc[0]['expiry_date']
    spot_open = good_dates.iloc[0]['open']
    spot_close = good_dates.iloc[0]['close']
    
    # Get next trading date
    next_idx = spot_df[spot_df['date'] > test_date].index[0]
    next_row = spot_df.loc[next_idx]
    next_date = next_row['date']
    
    print(f"\n=== TEST SCENARIO ===")
    print(f"Day 1: {test_date}")
    print(f"Day 2: {next_date}")
    print(f"Expiry: {expiry}")
    
    # Calculate ATM
    atm = round(spot_open / 50) * 50
    print(f"ATM at Day1 Open: {atm}")
    
    # Strangle strikes (Neutral strategy: SELL CALL ATM+4, SELL PUT ATM-4)
    call_strike = atm + 200
    put_strike = atm - 200
    print(f"Strangle: SELL CALL {call_strike}, SELL PUT {put_strike}")
    
    # Load options data
    df1 = pd.read_parquet(f'nifty/{test_date}/options.parquet')
    df1['expiry_date'] = pd.to_datetime(df1['expiry_date']).dt.date
    df1 = df1.sort_values('timestamp')
    
    # Get option prices for Day 1
    d1_call = df1[(df1['strike'] == call_strike) & (df1['option_type'] == 'CALL') & (df1['expiry_date'] == expiry)]
    d1_put = df1[(df1['strike'] == put_strike) & (df1['option_type'] == 'PUT') & (df1['expiry_date'] == expiry)]
    
    if len(d1_call) > 0 and len(d1_put) > 0:
        call_entry = d1_call.iloc[0]['open']
        put_entry = d1_put.iloc[0]['open']
        call_close = d1_call.iloc[-1]['close']
        put_close = d1_put.iloc[-1]['close']
        
        print(f"\n=== DAY 1 PRICES ===")
        print(f"CALL {call_strike}: Entry(Open)={call_entry}, Close={call_close}")
        print(f"PUT {put_strike}: Entry(Open)={put_entry}, Close={put_close}")
        
        # PnL calculation for SHORT (qty = -50)
        # Short means we SELL at entry, so profit when price goes DOWN
        # PnL = (current_price - entry_price) * qty = (current - entry) * (-50)
        qty = -50
        
        # After 1st Next: goes to DAY_CLOSE_REVEALED
        call_pnl_d1 = (call_close - call_entry) * qty
        put_pnl_d1 = (put_close - put_entry) * qty
        total_pnl_d1 = call_pnl_d1 + put_pnl_d1
        
        print(f"\n=== PNL AFTER DAY 1 CLOSE ===")
        print(f"CALL PnL: ({call_close} - {call_entry}) * {qty} = {call_pnl_d1}")
        print(f"PUT PnL: ({put_close} - {put_entry}) * {qty} = {put_pnl_d1}")
        print(f"TOTAL MTM PNL: {total_pnl_d1}")
        
        # Load Day 2
        try:
            df2 = pd.read_parquet(f'nifty/{next_date}/options.parquet')
            df2['expiry_date'] = pd.to_datetime(df2['expiry_date']).dt.date
            df2 = df2.sort_values('timestamp')
            
            d2_call = df2[(df2['strike'] == call_strike) & (df2['option_type'] == 'CALL') & (df2['expiry_date'] == expiry)]
            d2_put = df2[(df2['strike'] == put_strike) & (df2['option_type'] == 'PUT') & (df2['expiry_date'] == expiry)]
            
            if len(d2_call) > 0 and len(d2_put) > 0:
                call_d2_open = d2_call.iloc[0]['open']
                put_d2_open = d2_put.iloc[0]['open']
                
                print(f"\n=== DAY 2 PRICES ===")
                print(f"CALL {call_strike}: Open={call_d2_open}")
                print(f"PUT {put_strike}: Open={put_d2_open}")
                
                # PnL change from Day 1 Close to Day 2 Open
                call_pnl_overnight = (call_d2_open - call_close) * qty
                put_pnl_overnight = (put_d2_open - put_close) * qty
                
                print(f"\n=== OVERNIGHT PNL ===")
                print(f"CALL overnight: ({call_d2_open} - {call_close}) * {qty} = {call_pnl_overnight}")
                print(f"PUT overnight: ({put_d2_open} - {put_close}) * {qty} = {put_pnl_overnight}")
                print(f"CUMULATIVE PNL after Day2 Open: {total_pnl_d1 + call_pnl_overnight + put_pnl_overnight}")
            else:
                print("Day 2 option data not found for these strikes")
        except:
            print("Day 2 options file not found")
    else:
        print("Day 1 option data not found for these strikes")
