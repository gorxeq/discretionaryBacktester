from pydantic import BaseModel
from typing import List, Optional
from datetime import date as date_type

class Candle(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float

class OptionLeg(BaseModel):
    option_type: str  # 'CALL' or 'PUT'
    strike: float
    expiry: str
    qty: int
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None

class Strategy(BaseModel):
    id: str
    direction_state: int  # -2 to +2
    structure_type: str
    legs: List[OptionLeg]
    entry_time: str
    entry_spot: float
    exit_time: Optional[str] = None
    exit_spot: Optional[float] = None
    quantity_multiplier: int
    margin_used: float
    status: str  # 'ACTIVE' | 'CLOSED'

# API Requests
class SessionStartRequest(BaseModel):
    start_date: str

class StrategyPreviewRequest(BaseModel):
    session_id: str
    direction_state: int
    strike_overrides: Optional[List[dict]] = None
    quantity_multiplier: int = 1

class StrategyExecuteRequest(BaseModel):
    session_id: str
    direction_state: int
    quantity_multiplier: int = 1
    strike_overrides: Optional[List[dict]] = None

# API Responses
class SessionResponse(BaseModel):
    session_id: str
    current_state: str
    visible_candles: List[Candle]

class ReplayNextResponse(BaseModel):
    state: str
    spot_candle: Candle
    active_positions: List[Strategy]
    mtm_pnl: float
    total_pnl: float

class StrategyPreviewResponse(BaseModel):
    legs: List[OptionLeg]
    margin_required: float
    max_profit: float
    max_loss: float
