## 1. Context

This product is a replay-based options trading simulator designed for discretionary strategy practice, not indicator-based backtesting. The core objective is to allow a user to replay historical Nifty data day-by-day and express a **directional conviction** using predefined **options strategies** instead of buy/sell actions.

The system replaces traditional trade execution with a **five-state directional strategy model**, mapped from -2 (strongly bearish) to +2 (strongly bullish). Each state corresponds to a specific options structure. The replay engine enables the user to move forward one candle at a time, deploy strategies at any point during the day, and observe end-of-day PnL based on those decisions.

The product is intended as a **decision-training and hypothesis-validation tool**, helping users evaluate whether their daily market opinions were expressed optimally through strategy selection.

---

## 2. User Journey

1. **Application Entry**  
   The user opens the application. Historical Nifty daily candles (full history) are displayed on the chart.

2. **Starting Point Selection**  
   The user selects a specific daily candle as the starting point.
   - All candles prior to the selected candle remain visible.
   - All candles after the selected candle are hidden.

3. **Replay Mode Activation**  
   The user enters replay mode.
   - A "Next Candle" button becomes active.
   - Only one future daily candle can be revealed at a time.

4. **Market Observation & Decision**  
   After each new candle is revealed, the user:
   - Observes price action and context
   - May choose **not** to deploy any strategy
   - Or selects one of the five strategy buttons

5. **Strategy Deployment**  
   When a strategy button is clicked:
   - A position is opened at that day’s close (or defined execution price)
   - Strategy details are locked (structure, strikes, quantity multiplier)
   - The position remains active until end of day

6. **End-of-Day Evaluation**  
   At the end of the day:
   - PnL is calculated for all active strategies
   - Capital, margin usage, and cumulative PnL are updated

7. **Progression**  
   The user clicks "Next Candle" to move to the next trading day and repeats the process.

---

## 3. Strategy Model (Directional State Mapping)

The system supports exactly five strategy states, mapped to directional conviction:

| Direction State | Meaning | Strategy Type |
|-----------------|---------|---------------|
| -2 | Strongly Bearish | Naked Put Buying |
| -1 | Moderately Bearish | Bear Call Spread |
| 0 | Directionless / Range | Naked Strangle |
| +1 | Moderately Bullish | Bull Put Spread |
| +2 | Strongly Bullish | Naked Call Buying |

Each strategy:
- Has predefined construction rules
- Uses ATM-based strike selection (with fixed offsets)
- Supports a **quantity multiplier** to scale exposure

---

## 4. Functional Requirements (Modules)

### 4.1 Replay Engine Module
- Allow selection of any historical daily candle as replay start
- Hide all future candles beyond the selected point
- Reveal exactly one new candle per "Next Candle" action
- Prevent skipping or fast-forwarding

### 4.2 Strategy Interaction Module
- Replace Buy/Sell buttons with five strategy buttons (-2 to +2)
- Allow at most one strategy deployment per day (configurable later)
- Allow user to skip strategy deployment for a day
- Apply quantity multiplier at deployment time

### 4.3 Strategy Construction Module
- Automatically construct option legs based on:
  - Strategy type
  - Spot price of the day
  - Nearest expiry
- Ensure deterministic construction (same inputs → same structure)

### 4.4 PnL & Capital Module
- Calculate end-of-day PnL only (no intraday exits in v1)
- Track:
  - Daily PnL
  - Cumulative PnL
  - Capital curve
  - Margin usage

### 4.5 Visualization Module
- Chart showing daily candles
- Overlay showing active strategy markers
- PnL panel showing daily and cumulative results

---

## 5. Non-Functional Requirements

- Deterministic replay: same actions must always produce the same results
- Fast load and replay (no visible lag between candles)
- No repainting or future leakage
- Clear separation between replay state and strategy logic

---

## 6. Acceptance Criteria

- User can select any historical daily candle and start replay
- Future candles are fully hidden until revealed
- Exactly one candle is revealed per "Next Candle" click
- Strategy buttons (-2 to +2) are available at each step
- Deploying a strategy opens a position for that day
- PnL is calculated correctly at end of day
- Skipping a day without a strategy does not affect state

---

## 7. Test Cases

### 7.1 Replay Flow Tests
- Verify that future candles are not visible before replay
- Verify correct candle order during replay
- Verify replay cannot skip days

### 7.2 Strategy Deployment Tests
- Deploy each of the five strategies on identical days and validate structure
- Verify quantity multiplier scales PnL linearly
- Verify only allowed strategies can be deployed

### 7.3 PnL Accuracy Tests
- Manually compute expected PnL for sample days and compare
- Validate zero-strategy days result in zero PnL

### 7.4 Edge Case Tests
- Expiry day handling
- Gap-up / gap-down days
- Days with no valid option strikes

---

## 8. Out of Scope (v1)

- Intraday exits or adjustments
- Dynamic strike selection by user
- Greeks-based rebalancing
- Automated strategy recommendations

---

## 9. Success Metrics

- User can complete multi-year replay without confusion
- Decisions are auditable day-by-day
- PnL curve reflects realistic options strategy behavior

---

## 10. Development Plan (PRD → Build → Test → Deploy)

### 10.1 PRD Understanding (What Is Being Built)

The product is a **deterministic replay-based options strategy simulator**, not a traditional backtester. The core unit of interaction is a **daily decision**, expressed via one of five predefined options strategies mapped to directional conviction (-2 to +2).

Key non-negotiables:
- Replay-first (no future leakage)
- Strategy-level execution (not buy/sell)
- Deterministic outcomes for identical actions
- Day-wise PnL booking

---

### 10.2 Backend Architecture & Data Model (Authoritative)

#### 10.2.1 Data Assumptions

The backend operates entirely on **pre-downloaded historical data**:
- Nifty spot OHLC (Daily)
- Nifty options OHLC (1-minute)
- ATM ±10 strikes
- 4–5 years of data

There is **no live data dependency** in v1.

Data is treated as **read-only and immutable**.

---

#### 10.2.2 Storage Layout (Recommended)

```
data/
 ├─ spot/
 │   └─ nifty_daily.parquet
 ├─ options/
 │   └─ expiry=YYYYMMDD/
 │        └─ strike=XXXXX_type=CE|PE.parquet
```

- Columnar format (Parquet) for fast slicing
- Indexed by timestamp and expiry

---

#### 10.2.3 Core Backend Services (Python)

1. **Replay Engine Service**  
   - Owns current replay date and sub-state (open / close)
   - Prevents illegal transitions

2. **Market Data Service**  
   - Fetches spot and option prices for given date/time
   - Resolves nearest expiry automatically

3. **Strategy Engine**  
   - Converts direction state → strategy template
   - Builds option legs (default or overridden strikes)

4. **PnL Engine**  
   - Calculates end-of-day PnL
   - Handles overnight gaps

All services are **stateless** except replay session state.

---

### 10.3 Frontend–Backend Contract (API Design)

The frontend communicates with the backend via **event-driven APIs**.  
Each user action maps to a backend state transition.

#### 10.3.1 Session Initialization

**POST** `/session/start`

Request:
```
{
  "start_date": "2019-06-03"
}
```

Response:
```
{
  "session_id": "abc123",
  "current_state": "INIT",
  "visible_candles": [...]
}
```

---

#### 10.3.2 Next Button (Replay Advance)

**POST** `/session/next`

Request:
```
{
  "session_id": "abc123"
}
```

Response:
```
{
  "state": "DAY_OPEN_REVEALED | DAY_CLOSE_REVEALED",
  "spot_candle": { "open": ..., "high": ..., "low": ..., "close": ... },
  "active_positions": [...],
  "mtm_pnl": ...
}
```

---

#### 10.3.3 Strategy Preview (Before Execution)

**POST** `/strategy/preview`

Request:
```
{
  "session_id": "abc123",
  "direction_state": 0,
  "strike_overrides": [
    { "type": "CE", "strike": 19800 },
    { "type": "PE", "strike": 19600 }
  ],
  "quantity_multiplier": 1
}
```

Response:
```
{
  "legs": [...],
  "margin_required": ...,
  "max_profit": ...,
  "max_loss": ...
}
```

---

#### 10.3.4 Strategy Execution

**POST** `/strategy/execute`

Request:
```
{
  "session_id": "abc123",
  "entry_timing": "TODAY_CLOSE | NEXT_OPEN",
  "strategy_payload": {...}
}
```

Response:
```
{
  "strategy_id": "strat_001",
  "status": "ACTIVE"
}
```

---

#### 10.3.5 Manual Close

**POST** `/strategy/close`

Request:
```
{
  "session_id": "abc123"
}
```

Response:
```
{
  "realized_pnl": ...,
  "status": "FLAT"
}
```

---

### 10.4 Testing Strategy

#### Unit Tests
- Strategy construction correctness
- Payoff and PnL calculations
- Quantity multiplier scaling

#### Replay Integrity Tests
- Candle reveal order enforcement
- Illegal action prevention
- Deterministic replay verification

---

### 10.2 Development Architecture

#### Backend (Primary – Python)

**Recommended Stack**:
- Python 3.11+
- NumPy / Pandas (PnL, payoff, data access)
- FastAPI (API layer)

**Core Backend Components**:

1. **Replay State Engine**
   - Owns time progression
   - Enforces legal actions per state
   - Emits immutable replay events

2. **Strategy Engine**
   - Maps direction state → strategy template
   - Builds option legs (default or user-adjusted)
   - Calculates payoff and MTM

3. **PnL & Portfolio Engine**
   - Day-close PnL booking
   - Overnight gap handling
   - Capital and margin tracking

4. **Data Access Layer**
   - Read-only historical data (Parquet/Arrow)
   - Fast timestamp + expiry lookup

---

#### Frontend (Preferred: React, Optional Python UI)

- React + Canvas/SVG for charting (TradingView-like UX)
- Communicates with backend via API events
- Python-only UI (Streamlit / PyWebView) acceptable for v1 if speed is prioritized over UX fidelity

---

### 10.3 Testing Strategy

#### Unit Tests
- Strategy construction correctness
- Payoff and PnL calculations
- Quantity multiplier scaling

#### Replay Integrity Tests
- Candle reveal order enforcement
- Illegal action prevention
- Deterministic replay verification

#### User Journey Tests
- Flat → Enter → Carry → Exit flows
- Immediate execution vs manual strike selection
- Overnight gap PnL correctness

---

### 10.4 Deployment Plan

- Local-first deployment (single user)
- Backend as local service
- Frontend as local web app
- No authentication required in v1

---

## 11. Replay State Machine (Formal)

### States

1. **INIT** – Start candle selected
2. **DAY_OPEN_REVEALED** – Next day open shown
3. **STRATEGY_ACTIVE** – Position open
4. **DAY_CLOSE_REVEALED** – H/L/C revealed, PnL booked
5. **FLAT** – No active strategy

### Allowed Transitions

- INIT → DAY_OPEN_REVEALED (Next)
- DAY_OPEN_REVEALED → STRATEGY_ACTIVE (Execute)
- DAY_OPEN_REVEALED → DAY_CLOSE_REVEALED (Next)
- STRATEGY_ACTIVE → DAY_CLOSE_REVEALED (Next)
- STRATEGY_ACTIVE → FLAT (Manual Close)
- DAY_CLOSE_REVEALED → DAY_OPEN_REVEALED (Next Day)

Illegal actions are blocked by design.

---

## 12. Strategy Object Schema (Authoritative)

```
Strategy {
  id
  direction_state: -2 | -1 | 0 | +1 | +2
  structure_type
  legs: [ { option_type, strike, expiry, qty } ]
  entry_time
  entry_price
  exit_time (optional)
  exit_price (optional)
  quantity_multiplier
  margin_used
  status: ACTIVE | CLOSED
}
```

- Strikes are locked at execution
- Defaults auto-generated, overrides user-driven

---

## 13. UI Event Flow (Single-Screen Wireframe Logic)

1. User selects start candle
2. Clicks **Next** → Day Open appears
3. Optional: selects strategy
   - Immediate Exec ON → auto execute
   - OFF → drag strike lines → Execute
4. Clicks **Next** → Day Close appears
5. PnL booked
6. Repeat

---

## 14. Out of Scope (Explicit)

- Intraday exits
- Strategy optimization
- Auto strategy recommendations
- Multi-user support

---

This PRD is intentionally capped to remain under ~4 pages and is suitable for direct handoff to an engineering team or LLM-based code generator.

