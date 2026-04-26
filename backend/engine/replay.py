from datetime import date as date_type, datetime
from typing import List, Optional, Dict
from .market_data import MarketDataService

class ReplayEngine:
    def __init__(self, market_data: MarketDataService):
        self.market_data = market_data
        self.current_date_index = -1
        self.state = "INIT"  # INIT, DAY_OPEN_REVEALED, STRATEGY_ACTIVE, DAY_CLOSE_REVEALED, FLAT
        self.visible_dates: List[date_type] = []
        self.all_dates = self.market_data.daily_df['date'].tolist()
        self.active_strategy = None
        
    def start_session(self, start_date: date_type):
        # Find index of start_date in all_dates
        try:
            print(f"[REPLAY] Searching for {start_date} type: {type(start_date)}")
            if self.all_dates:
                 print(f"[REPLAY] First date: {self.all_dates[0]} type: {type(self.all_dates[0])}")
            
            self.current_date_index = self.all_dates.index(start_date)
            # Visible dates are all dates up to start_date
            self.visible_dates = self.all_dates[:self.current_date_index + 1]
            self.state = "INIT"
            return True
        except ValueError as e:
            print(f"[REPLAY] ValueError: {e}")
            return False

    def next_step(self):
        """
        Transition via 'Next' button:
        - INIT -> DAY_OPEN_REVEALED (same day)
        - DAY_OPEN_REVEALED -> DAY_CLOSE_REVEALED (same day)
        - DAY_CLOSE_REVEALED -> DAY_OPEN_REVEALED (next day)
        - STRATEGY_ACTIVE -> DAY_CLOSE_REVEALED (same day)
        """
        if self.state == "INIT":
            self.state = "DAY_OPEN_REVEALED"
        elif self.state == "DAY_OPEN_REVEALED" or self.state == "STRATEGY_ACTIVE":
            self.state = "DAY_CLOSE_REVEALED"
        elif self.state == "DAY_CLOSE_REVEALED":
            self.current_date_index += 1
            if self.current_date_index >= len(self.all_dates):
                return None  # End of data
            self.visible_dates.append(self.all_dates[self.current_date_index])
            self.state = "DAY_OPEN_REVEALED"
        
        return self.get_current_state_payload()

    def get_current_date(self) -> date_type:
        return self.all_dates[self.current_date_index]

    def get_current_state_payload(self):
        curr_date = self.get_current_date()
        candle = self.market_data.get_spot_candle(curr_date)
        
        # In PRD: Reveal High/Low/Close only in DAY_CLOSE_REVEALED
        if self.state == "DAY_OPEN_REVEALED" or self.state == "STRATEGY_ACTIVE":
            # Filter candle to only show Open
            return {
                "date": str(curr_date),
                "open": candle["open"],
                "high": candle["open"], # Placeholder
                "low": candle["open"],  # Placeholder
                "close": candle["open"] # Placeholder
            }
        else:
            return {
                "date": str(curr_date),
                "open": candle["open"],
                "high": candle["high"],
                "low": candle["low"],
                "close": candle["close"]
            }
