import pandas as pd
import os
from pathlib import Path
from tqdm import tqdm

def preprocess_nifty_data(base_dir="nifty"):
    base_path = Path(base_dir)
    results = []

    # Get all date directories
    date_dirs = sorted([d for d in base_path.iterdir() if d.is_dir()])
    
    print(f"Found {len(date_dirs)} days to process.")

    for date_dir in tqdm(date_dirs):
        file_path = date_dir / "options.parquet"
        if not file_path.exists():
            continue
        
        try:
            # Load only necessary columns to save memory
            df = pd.read_parquet(file_path, columns=['timestamp', 'spot', 'expiry_date'])
            
            if df.empty:
                continue
            
            # Ensure timestamp is datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Get daily spot OHLC
            # First, get unique spot prices per timestamp
            spot_per_timestamp = df.groupby('timestamp')['spot'].first()
            
            daily_open = spot_per_timestamp.iloc[0]
            daily_high = spot_per_timestamp.max()
            daily_low = spot_per_timestamp.min()
            daily_close = spot_per_timestamp.iloc[-1]
            
            # Get nearest expiry (minimum expiry date >= current date)
            current_date = pd.to_datetime(date_dir.name).date()
            df['expiry_date'] = pd.to_datetime(df['expiry_date']).dt.date
            
            # Nearest expiry usually is the one in the data, but let's be sure
            future_expiries = df[df['expiry_date'] >= current_date]['expiry_date'].unique()
            if len(future_expiries) > 0:
                nearest_expiry = sorted(future_expiries)[0]
            else:
                nearest_expiry = df['expiry_date'].max() # Fallback

            results.append({
                'date': date_dir.name,
                'open': daily_open,
                'high': daily_high,
                'low': daily_low,
                'close': daily_close,
                'expiry_date': nearest_expiry
            })
            
        except Exception as e:
            print(f"Error processing {date_dir.name}: {e}")

    final_df = pd.DataFrame(results)
    final_df['date'] = pd.to_datetime(final_df['date'])
    final_df = final_df.sort_values('date')
    
    # Create data directory if not exists
    os.makedirs("data", exist_ok=True)
    final_df.to_parquet("data/nifty_daily.parquet", index=False)
    print(f"Preprocessed data saved to data/nifty_daily.parquet. Total days: {len(final_df)}")

if __name__ == "__main__":
    preprocess_nifty_data()
