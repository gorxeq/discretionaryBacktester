import pandas as pd
from pathlib import Path
from datetime import datetime, date as date_type
from typing import Optional, Dict
from functools import lru_cache

# Path to sharpe4 data directory (single source of truth)
SHARPE4_DATA_ROOT = Path(r"C:\Users\naman\Documents\sharpe4\data")

class MarketDataService:
    def __init__(self, data_root=None, nifty_root=None):
        # Use sharpe4/data as the single source of truth
        self.data_root = Path(data_root) if data_root else SHARPE4_DATA_ROOT
        self.nifty_root = Path(nifty_root) if nifty_root else (SHARPE4_DATA_ROOT / "nifty")
        
        # Generate nifty_daily.parquet from options data if it doesn't exist or is stale
        self._ensure_daily_data()
        
        self.daily_df = pd.read_parquet(self.data_root / "nifty_daily.parquet")
        self.daily_df['date'] = pd.to_datetime(self.daily_df['date']).dt.date
        self.daily_df = self.daily_df.sort_values('date').drop_duplicates(subset=['date']).reset_index(drop=True)
    
    def _ensure_daily_data(self):
        """Generate or update nifty_daily.parquet from options data."""
        daily_path = self.data_root / "nifty_daily.parquet"
        
        # Get all available dates from nifty options folders
        available_dates = sorted([
            d.name for d in self.nifty_root.iterdir() 
            if d.is_dir() and len(d.name) == 10  # YYYY-MM-DD format
        ])
        
        if not available_dates:
            raise ValueError(f"No options data found in {self.nifty_root}")
        
        # Check if daily file exists and has latest date
        needs_update = True
        if daily_path.exists():
            try:
                existing_df = pd.read_parquet(daily_path)
                existing_df['date'] = pd.to_datetime(existing_df['date']).dt.strftime('%Y-%m-%d')
                existing_dates = set(existing_df['date'].unique())
                new_dates = set(available_dates) - existing_dates
                needs_update = len(new_dates) > 0
                if needs_update:
                    print(f"Found {len(new_dates)} new dates to add to nifty_daily.parquet")
            except Exception as e:
                print(f"Error reading existing daily file: {e}")
                needs_update = True
        else:
            print("nifty_daily.parquet not found, generating from options data...")
        
        if needs_update:
            self._generate_daily_from_options(available_dates, daily_path)
    
    def _generate_daily_from_options(self, dates: list, output_path: Path):
        """Generate daily OHLC data from 1-minute options data."""
        import numpy as np
        
        daily_records = []
        
        for date_str in dates:
            options_file = self.nifty_root / date_str / "options.parquet"
            if not options_file.exists():
                continue
            
            try:
                df = pd.read_parquet(options_file)
                
                # Get underlying/spot price from the options data
                # The 'spot' column contains the actual spot price
                if 'spot' in df.columns:
                    df_sorted = df.sort_values('timestamp')
                    spot_open = df_sorted.iloc[0]['spot']
                    spot_close = df_sorted.iloc[-1]['spot']
                    spot_high = df['spot'].max()
                    spot_low = df['spot'].min()
                else:
                    # Fallback: estimate from ATM strike prices
                    spot_open = df['strike'].median()
                    spot_close = spot_open
                    spot_high = spot_open
                    spot_low = spot_open
                
                # Get expiry date for this trading date
                if 'expiry_date' in df.columns:
                    expiry = pd.to_datetime(df['expiry_date']).min()
                    if hasattr(expiry, 'date'):
                        expiry = expiry.date()
                else:
                    expiry = None
                
                daily_records.append({
                    'date': date_str,
                    'open': float(spot_open),
                    'high': float(spot_high),
                    'low': float(spot_low),
                    'close': float(spot_close),
                    'expiry_date': expiry
                })
            except Exception as e:
                print(f"Error processing {date_str}: {e}")
                continue
        
        if daily_records:
            daily_df = pd.DataFrame(daily_records)
            daily_df['date'] = pd.to_datetime(daily_df['date'])
            daily_df = daily_df.sort_values('date').reset_index(drop=True)
            daily_df.to_parquet(output_path, index=False)
            print(f"Generated nifty_daily.parquet with {len(daily_df)} trading days")
        
    def get_daily_candles(self, start_date: date_type):
        return self.daily_df[self.daily_df['date'] >= start_date].to_dict('records')

    def get_spot_candle(self, date: date_type):
        row = self.daily_df[self.daily_df['date'] == date]
        if row.empty:
            return None
        return row.iloc[0].to_dict()

    @lru_cache(maxsize=32)
    def _get_day_options(self, date: date_type) -> pd.DataFrame:
        """Cached loader for daily options data"""
        date_str = date.strftime('%Y-%m-%d')
        file_path = self.nifty_root / date_str / "options.parquet"
        
        if not file_path.exists():
            return pd.DataFrame()
        
        df = pd.read_parquet(file_path)
        # Convert timestamp to datetime if not already
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Convert expiry to date object for comparison
        # First ensure it's datetime, then extract date
        if not pd.api.types.is_datetime64_any_dtype(df['expiry_date']):
             df['expiry_date'] = pd.to_datetime(df['expiry_date'])
        
        df['expiry_date'] = df['expiry_date'].dt.date
        return df

    def get_option_price(self, date: date_type, strike: float, option_type: str, expiry: date_type, time_of_day: str) -> Optional[float]:
        """
        Fetch option price at a specific time (OPEN or CLOSE).
        """
        df = self._get_day_options(date)
        if df.empty:
            return None
        
        # Filter by strike, type, expiry
        # Use query for potential speedup or boolean indexing
        mask = (df['strike'] == strike) & (df['option_type'] == option_type) & (df['expiry_date'] == expiry)
        res = df[mask]
        
        if res.empty:
            return None
            
        # Sort by timestamp to get first/last
        res = res.sort_values('timestamp')
        
        if time_of_day == 'OPEN':
            return res.iloc[0]['open']
        elif time_of_day == 'CLOSE':
            return res.iloc[-1]['close']
        
        return None

    def get_nearest_expiry(self, date: date_type) -> Optional[date_type]:
        """
        Get the nearest expiry date for a given trading date.
        Uses the daily_df's expiry_date column which is pre-computed.
        """
        row = self.daily_df[self.daily_df['date'] == date]
        if row.empty:
            return None
        expiry = row.iloc[0]['expiry_date']
        if hasattr(expiry, 'date'):
            return expiry.date()
        return expiry
    
    def get_available_strikes(self, date: date_type) -> Dict[float, Dict]:
        """
        Get all available strikes for the current day's nearest expiry.
        Useful for building strategy legs.
        """
        date_str = date.strftime('%Y-%m-%d')
        file_path = self.nifty_root / date_str / "options.parquet"
        if not file_path.exists():
            return {}
        
        df = pd.read_parquet(file_path, columns=['strike', 'option_type', 'expiry_date', 'open', 'close'])
        df['expiry_date'] = pd.to_datetime(df['expiry_date']).dt.date
        
        # Get nearest expiry from daily_df
        nearest_expiry = self.get_nearest_expiry(date)
        if not nearest_expiry:
            nearest_expiry = df['expiry_date'].min()
        
        expiry_data = df[df['expiry_date'] == nearest_expiry]
        strikes = {}
        for _, row in expiry_data.iterrows():
            s = row['strike']
            if s not in strikes:
                strikes[s] = {'CALL': None, 'PUT': None}
            strikes[s][row['option_type']] = {'open': row['open'], 'close': row['close']}
            
        return strikes
