from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .models.schemas import *
from .engine.market_data import MarketDataService
from .engine.replay import ReplayEngine
from .engine.strategy import StrategyEngine
from .engine.pnl import PnLEngine
from .engine.summary import SummaryEngine
from datetime import datetime, timedelta
import uuid
import traceback

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000", "*"],  # Allow React app and others
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler to ensure CORS headers are always included
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    error_msg = str(exc)
    print(f"Unhandled exception: {error_msg}")
    print(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {error_msg}"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

# Global services
market_data = MarketDataService()
strategy_engine = StrategyEngine(market_data)
pnl_engine = PnLEngine(market_data)
summary_engine = SummaryEngine()

# In-memory session storage
sessions = {}

@app.get("/")
async def root():
    return {"status": "ok", "message": "Backend is running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "port": 8000}

@app.get("/market/history")
async def get_market_history():
    df = market_data.daily_df
    return [
        {"date": str(row["date"]), "open": row["open"], "high": row["high"], "low": row["low"], "close": row["close"]}
        for _, row in df.iterrows()
    ]

@app.post("/session/start")
async def start_session(req: SessionStartRequest):
    try:
        print(f"Received start_session request for date: {req.start_date}")
        session_id = str(uuid.uuid4())
        start_date = datetime.strptime(req.start_date, '%Y-%m-%d').date()
        print(f"Parsed date: {start_date}")
        
        replay = ReplayEngine(market_data)
        if not replay.start_session(start_date):
            print(f"Invalid start date: {start_date}")
            raise HTTPException(status_code=400, detail="Invalid start date")
        
        print(f"Session started, visible dates: {len(replay.visible_dates)}")
        
        sessions[session_id] = {
            "replay": replay,
            "active_strategy": None,
            "realized_pnl": 0.0,    # Only from closed trades
            "unrealized_pnl": 0.0,  # Current open position cumulative MTM
            "pnl_history": [],
            "trade_history": []
        }
        
        # Get initial visible candles
        visible_candles = []
        for d in replay.visible_dates:
            candle = market_data.get_spot_candle(d)
            if candle:
                # Convert date to string for JSON serialization
                # Only include fields needed for Candle model
                candle_dict = {
                    "date": str(candle["date"]),
                    "open": float(candle["open"]),
                    "high": float(candle["high"]),
                    "low": float(candle["low"]),
                    "close": float(candle["close"])
                }
                visible_candles.append(candle_dict)

        print(f"Created {len(visible_candles)} visible candles")
        
        response_data = {
            "session_id": session_id,
            "current_state": replay.state,
            "visible_candles": visible_candles
        }
        
        print(f"Returning response with session_id: {session_id}")
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = f"Error in start_session: {str(e)}\n{traceback.format_exc()}"
        print("=" * 50)
        print("ERROR IN START_SESSION:")
        print(error_msg)
        print("=" * 50)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/session/next")
async def next_step(req: dict):
    session_id = req.get("session_id")
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    replay = session["replay"]
    rollover_info = None
    
    if session["active_strategy"]:
        current_date = replay.get_current_date()
        current_state = replay.state
        strategy = session["active_strategy"]
        
        # Check for expiry rollover when moving from DAY_CLOSE to next day
        if current_state == "DAY_CLOSE_REVEALED":
            # Check if any leg expires today
            legs_expiring = any(
                datetime.strptime(leg["expiry"], '%Y-%m-%d').date() == current_date 
                for leg in strategy["legs"]
            )
            
            if legs_expiring:
                # ROLLOVER: 
                # 1. Close at expiry close price → book to realized
                # 2. Get next expiry 
                # 3. Re-enter with next expiry
                
                rollover_pnl = 0.0
                for leg in strategy["legs"]:
                    expiry_dt = datetime.strptime(leg["expiry"], '%Y-%m-%d').date()
                    close_price = market_data.get_option_price(
                        current_date, leg["strike"], leg["option_type"], expiry_dt, 'CLOSE'
                    )
                    if close_price is not None:
                        rollover_pnl += (close_price - leg["entry_price"]) * leg["qty"]
                
                # Book rollover PnL to realized
                session["realized_pnl"] += rollover_pnl
                
                # Advance to next trading day FIRST
                replay.next_step()
                new_date = replay.get_current_date()
                
                # Get next expiry from the new date
                next_expiry = market_data.get_nearest_expiry(new_date)
                
                # Get new ATM for naked strategy strike recalculation
                spot_open = market_data.get_spot_candle(new_date)['open']
                new_atm = round(spot_open / 50) * 50
                
                # Re-enter with new expiry - entry price is OPEN of new day for next expiry
                direction = strategy["direction_state"]
                for leg in strategy["legs"]:
                    leg["expiry"] = str(next_expiry)
                    
                    # For naked strategies, recalculate strike relative to new ATM
                    if direction == -2:  # Naked Put
                        leg["strike"] = new_atm - 100
                    elif direction == +2:  # Naked Call
                        leg["strike"] = new_atm + 100
                    # Spreads keep same strikes for consistency
                    
                    # Entry at OPEN of new day for the new expiry contract
                    new_entry = market_data.get_option_price(
                        new_date, leg["strike"], leg["option_type"], next_expiry, 'OPEN'
                    )
                    print(f"Rollover entry: {new_date}, strike={leg['strike']}, type={leg['option_type']}, expiry={next_expiry}, price={new_entry}")
                    if new_entry:
                        leg["entry_price"] = new_entry
                        leg["current_price"] = new_entry
                        leg["last_valuation_price"] = new_entry
                    else:
                        print(f"WARNING: Could not get new entry price for rollover!")
                
                rollover_info = {"pnl_booked": rollover_pnl, "new_expiry": str(next_expiry)}
                
                # Unrealized is 0 right after rollover entry (entry = current price)
                session["unrealized_pnl"] = 0.0
                
            else:
                # Normal transition to next day
                replay.next_step()
                new_date = replay.get_current_date()
                # Update leg valuations
                unrealized = 0.0
                for leg in strategy["legs"]:
                    expiry_dt = datetime.strptime(leg["expiry"], '%Y-%m-%d').date()
                    curr_price = market_data.get_option_price(
                        new_date, leg["strike"], leg["option_type"], expiry_dt, 'OPEN'
                    )
                    if curr_price:
                        unrealized += (curr_price - leg["entry_price"]) * leg["qty"]
                        leg["current_price"] = curr_price
                        leg["last_valuation_price"] = curr_price
                session["unrealized_pnl"] = unrealized
                
        elif current_state in ["DAY_OPEN_REVEALED", "STRATEGY_ACTIVE"]:
            # Moving to DAY_CLOSE: Calculate unrealized at close
            replay.next_step()
            unrealized = 0.0
            for leg in strategy["legs"]:
                expiry_dt = datetime.strptime(leg["expiry"], '%Y-%m-%d').date()
                curr_price = market_data.get_option_price(
                    current_date, leg["strike"], leg["option_type"], expiry_dt, 'CLOSE'
                )
                if curr_price:
                    unrealized += (curr_price - leg["entry_price"]) * leg["qty"]
                    leg["current_price"] = curr_price
                    leg["last_valuation_price"] = curr_price
            session["unrealized_pnl"] = unrealized
        else:
            replay.next_step()
    else:
        replay.next_step()
        session["unrealized_pnl"] = 0.0
    
    # Build response
    response = {
        "state": replay.state,
        "spot_candle": replay.get_current_state_payload(),
        "active_positions": [session["active_strategy"]] if session["active_strategy"] else [],
        "realized_pnl": session["realized_pnl"],
        "unrealized_pnl": session["unrealized_pnl"]
    }
    
    if rollover_info:
        response["rollover"] = rollover_info
        
    return response

@app.post("/strategy/preview", response_model=StrategyPreviewResponse)
async def preview_strategy(req: StrategyPreviewRequest):
    session = sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    replay = session["replay"]
    date = replay.get_current_date()
    spot = market_data.get_spot_candle(date)["open"]
    
    legs = strategy_engine.construct_strategy(
        req.direction_state, spot, date, req.quantity_multiplier, req.strike_overrides
    )
    metrics = strategy_engine.get_preview_metrics(legs, req.direction_state)
    
    return StrategyPreviewResponse(
        legs=legs,
        **metrics
    )

@app.post("/strategy/execute")
async def execute_strategy(req: StrategyExecuteRequest):
    session = sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    replay = session["replay"]
    
    # Allow execution in both DAY_OPEN_REVEALED and DAY_CLOSE_REVEALED
    if replay.state not in ["DAY_OPEN_REVEALED", "DAY_CLOSE_REVEALED"]:
        raise HTTPException(status_code=400, detail="Can only execute when market data is revealed")
    
    # Check if already have an active strategy
    if session["active_strategy"]:
        raise HTTPException(status_code=400, detail="Already have an active position. Close it first.")

    # Determine entry timing based on state
    entry_timing = 'OPEN' if replay.state == "DAY_OPEN_REVEALED" else 'CLOSE'
    
    # Construct strategy
    curr_date = replay.get_current_date()
    spot = market_data.get_spot_candle(curr_date)[entry_timing.lower()]
    
    legs = strategy_engine.construct_strategy(
        req.direction_state, spot, curr_date, req.quantity_multiplier, req.strike_overrides
    )
    
    # Capture entry prices at current timing (OPEN or CLOSE)
    for leg in legs:
        expiry_date = datetime.strptime(leg["expiry"], '%Y-%m-%d').date()
        price = market_data.get_option_price(
            curr_date, leg["strike"], leg["option_type"], expiry_date, entry_timing
        )
        if price is None:
            raise HTTPException(status_code=400, detail=f"Could not get price for {leg['option_type']} {leg['strike']} on {curr_date}")
        leg["entry_price"] = price
        leg["last_valuation_price"] = price

    session["active_strategy"] = {
        "id": str(uuid.uuid4()),
        "direction_state": req.direction_state,
        "legs": legs,
        "entry_time": str(curr_date),
        "entry_timing": entry_timing,  # Track whether entered at OPEN or CLOSE
        "entry_spot": spot,
        "quantity_multiplier": req.quantity_multiplier,
        "status": "ACTIVE"
    }
    
    replay.state = "STRATEGY_ACTIVE"
    
    return {"strategy_id": session["active_strategy"]["id"], "status": "ACTIVE", "entry_timing": entry_timing}

@app.post("/strategy/close")
async def close_strategy(req: dict):
    session_id = req.get("session_id")
    session = sessions.get(session_id)
    if not session or not session["active_strategy"]:
        raise HTTPException(status_code=400, detail="No active strategy")
    
    replay = session["replay"]
    curr_date = replay.get_current_date()
    timing = 'OPEN' if replay.state in ["DAY_OPEN_REVEALED", "STRATEGY_ACTIVE"] else 'CLOSE'
    
    # Calculate final realized PnL from ENTRY to EXIT
    final_pnl = 0.0
    strategy = session["active_strategy"]
    for leg in strategy["legs"]:
        curr_price = market_data.get_option_price(
            curr_date, leg["strike"], leg["option_type"],
            datetime.strptime(leg["expiry"], '%Y-%m-%d').date(), timing
        )
        if curr_price is not None:
            # PnL = (exit_price - entry_price) * qty
            final_pnl += (curr_price - leg["entry_price"]) * leg["qty"]
            
    # Add to realized PnL
    session["realized_pnl"] += final_pnl
    session["unrealized_pnl"] = 0.0
    
    # Store in trade history
    session["trade_history"].append({
        "strategy_id": strategy["id"],
        "realized_pnl": final_pnl,
        "exit_time": str(curr_date),
        "exit_spot": market_data.get_spot_candle(curr_date)[timing.lower()]
    })
    
    session["active_strategy"] = None
    replay.state = "FLAT" if replay.state == "STRATEGY_ACTIVE" else replay.state
    
    return {
        "realized_pnl": final_pnl, 
        "total_realized": session["realized_pnl"],
        "status": "FLAT"
    }

@app.get("/session/summary")
async def get_session_summary(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return summary_engine.calculate_summary(session)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
