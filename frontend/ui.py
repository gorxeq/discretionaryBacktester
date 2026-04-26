import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from streamlit_lightweight_charts import renderLightweightCharts

st.set_page_config(layout="wide", page_title="Nifty Options Simulator")

# Backend URL
API_URL = "http://127.0.0.1:8000"

# --- STATE ---
if "session_id" not in st.session_state: st.session_state.session_id = None
if "current_state" not in st.session_state: st.session_state.current_state = "SELECTION"
if "all_candles" not in st.session_state: st.session_state.all_candles = []
if "visible_candles" not in st.session_state: st.session_state.visible_candles = []
if "total_pnl" not in st.session_state: st.session_state.total_pnl = 0.0
if "daily_pnl" not in st.session_state: st.session_state.daily_pnl = 0.0
if "replay_state" not in st.session_state: st.session_state.replay_state = "INIT"
if "active_strategy" not in st.session_state: st.session_state.active_strategy = None
if "strategy_preview" not in st.session_state: st.session_state.strategy_preview = None

# 1. Fetch market data
if not st.session_state.all_candles:
    try:
        res = requests.get(f"{API_URL}/market/history", timeout=10)
        if res.status_code == 200:
            st.session_state.all_candles = res.json()
    except Exception as e:
        st.error(f"Backend connection failed. Is the server running?")

# --- SELECTION ---
if st.session_state.current_state == "SELECTION":
    st.title("Nifty 50 - Strategy Simulator")
    
    if st.session_state.all_candles:
        df = pd.DataFrame(st.session_state.all_candles)
        df['date'] = pd.to_datetime(df['date'])
        for col in ['open', 'high', 'low', 'close']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna().sort_values('date')
        
        # 1. Selection Controls
        with st.container():
            st.subheader("1. Select Start Date")
            unique_dates = df['date'].dt.date.unique()
            selected_date = st.select_slider("Pick a date to start the replay from:", options=unique_dates, value=unique_dates[0])
            
            if st.button("🚀 Start Bar Replay from " + str(selected_date), use_container_width=True):
                res = requests.post(f"{API_URL}/session/start", json={"start_date": str(selected_date)})
                if res.status_code == 200:
                    data = res.json()
                    st.session_state.session_id = data["session_id"]
                    st.session_state.current_state = "REPLAY"
                    st.session_state.replay_state = data.get("current_state", "INIT")
                    # Only show candles up to selected date (backend returns only visible candles)
                    st.session_state.visible_candles = [
                        {"time": c["date"], "open": c["open"], "high": c["high"], "low": c["low"], "close": c["close"]}
                        for c in data["visible_candles"]
                    ]
                    st.session_state.total_pnl = 0.0
                    st.session_state.daily_pnl = 0.0
                    st.session_state.active_strategy = None
                    st.session_state.selected_direction = None
                    # Auto-transition to DAY_OPEN_REVEALED to show strategy buttons immediately
                    if st.session_state.replay_state == "INIT":
                        # Click next to reveal day open
                        next_res = requests.post(f"{API_URL}/session/next", json={"session_id": st.session_state.session_id})
                        if next_res.status_code == 200:
                            next_data = next_res.json()
                            st.session_state.replay_state = next_data.get("state", "DAY_OPEN_REVEALED")
                            # Update the last candle if needed
                            if st.session_state.visible_candles:
                                new_c = next_data["spot_candle"]
                                if st.session_state.visible_candles[-1]["time"] == new_c["date"]:
                                    st.session_state.visible_candles[-1] = {
                                        "time": new_c["date"], 
                                        "open": new_c["open"], 
                                        "high": new_c["high"], 
                                        "low": new_c["low"], 
                                        "close": new_c["close"]
                                    }
                    st.rerun()

        st.divider()
        
        # 2. History Chart (Standard Plotly - Guaranteed to render)
        st.subheader("Historical Context")
        fig = go.Figure(data=[go.Candlestick(
            x=df['date'],
            open=df['open'], high=df['high'],
            low=df['low'], close=df['close'],
            increasing_line_color='#089981', decreasing_line_color='#f23645'
        )])
        fig.update_layout(
            template="plotly_dark",
            height=600,
            xaxis_rangeslider_visible=True,
            margin=dict(l=0, r=0, t=0, b=0)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Loading market data...")

# --- REPLAY ---
elif st.session_state.current_state == "REPLAY":
    # Header with current state
    col_header1, col_header2 = st.columns([3, 1])
    with col_header1:
        current_date = st.session_state.visible_candles[-1]["time"] if st.session_state.visible_candles else "N/A"
        st.subheader(f"📊 Replay: {current_date} | State: {st.session_state.replay_state}")
    with col_header2:
        if st.button("🚪 Exit Replay", use_container_width=True):
            st.session_state.session_id = None
            st.session_state.current_state = "SELECTION"
            st.session_state.visible_candles = []
            st.session_state.replay_state = "INIT"
            st.session_state.active_strategy = None
            st.rerun()
    
    # PnL Panel
    pnl_col1, pnl_col2, pnl_col3 = st.columns(3)
    with pnl_col1:
        st.metric("Daily PnL", f"₹ {st.session_state.daily_pnl:,.2f}", 
                 delta=f"{st.session_state.daily_pnl:,.2f}" if st.session_state.daily_pnl != 0 else None)
    with pnl_col2:
        st.metric("Cumulative PnL", f"₹ {st.session_state.total_pnl:,.2f}")
    with pnl_col3:
        strategy_status = "🟢 ACTIVE" if st.session_state.active_strategy else "⚪ FLAT"
        st.metric("Position", strategy_status)
    
    st.divider()
    
    # Chart
    chart_opts = {
        "layout": {
            "backgroundColor": "#0c0d10", 
            "textColor": "#d1d4dc",
            "handleScale": {
                "axisPressedMouseMove": False,
                "axisDoubleClickReset": False,
                "axisTouchMouseReset": False
            },
            "handleScroll": {
                "horzTouchDrag": False, 
                "vertTouchDrag": False,
                "mouseWheel": True,
                "pressedMouseMove": True
            }
        },
        "grid": {"vertLines": {"color": "#1e222d"}, "horzLines": {"color": "#1e222d"}},
        "width": 1600,
        "height": 600,
        "crosshair": {"mode": 0},  # Disable crosshair
    }
    
    # Prepare candle data - ONLY show visible candles (up to selected date)
    # All future candles are hidden per PRD requirement
    chart_candles = []
    
    # Show all visible candles except the last one (which may be partial)
    for c in st.session_state.visible_candles[:-1] if len(st.session_state.visible_candles) > 1 else []:
        chart_candles.append(c)
    
    # Last candle - show based on state
    if st.session_state.visible_candles:
        last_candle = st.session_state.visible_candles[-1].copy()
        if st.session_state.replay_state in ["DAY_OPEN_REVEALED", "STRATEGY_ACTIVE", "INIT"]:
            # Show only open price (flat line) when day open is revealed
            last_candle["high"] = last_candle["open"]
            last_candle["low"] = last_candle["open"]
            last_candle["close"] = last_candle["open"]
        chart_candles.append(last_candle)
    
    chart_data = [{
        "chart": chart_opts,
        "series": [
            {
                "type": "Candlestick",
                "data": chart_candles,
                "options": {"upColor": "#089981", "downColor": "#f23645"}
            }
        ]
    }]
    
    renderLightweightCharts(chart_data, "replay_view")
    
    st.divider()
    
    # Strategy Selection Section - Show when INIT or DAY_OPEN_REVEALED
    if st.session_state.replay_state in ["INIT", "DAY_OPEN_REVEALED"]:
        st.subheader("🎯 Deploy Strategy")
        st.caption("Select your directional conviction for today's market")
        
        # Strategy buttons
        strategy_cols = st.columns(5)
        strategy_configs = [
            (-2, "🔴 Strongly Bearish", "Naked Put Buy", "#f23645"),
            (-1, "🟠 Moderately Bearish", "Bear Call Spread", "#ff6b35"),
            (0, "⚪ Directionless", "Naked Strangle", "#888888"),
            (+1, "🟢 Moderately Bullish", "Bull Put Spread", "#089981"),
            (+2, "🟢 Strongly Bullish", "Naked Call Buy", "#00d4aa")
        ]
        
        # Use session state to track selected direction
        if "selected_direction" not in st.session_state:
            st.session_state.selected_direction = None
        
        for idx, (direction, label, desc, color) in enumerate(strategy_configs):
            with strategy_cols[idx]:
                button_label = f"{label}\n{desc}"
                if st.button(button_label, key=f"strat_{direction}", use_container_width=True, 
                           type="primary" if st.session_state.selected_direction == direction else "secondary"):
                    st.session_state.selected_direction = direction
                    st.rerun()
        
        selected_direction = st.session_state.selected_direction
        
        # Quantity multiplier
        qty_mult = st.number_input("Quantity Multiplier", min_value=1, max_value=10, value=1, step=1)
        
        # Preview and Execute
        if selected_direction is not None:
            # Preview strategy
            try:
                preview_res = requests.post(
                    f"{API_URL}/strategy/preview",
                    json={
                        "session_id": st.session_state.session_id,
                        "direction_state": selected_direction,
                        "quantity_multiplier": qty_mult
                    }
                )
                if preview_res.status_code == 200:
                    preview_data = preview_res.json()
                    st.session_state.strategy_preview = preview_data
                    
                    # Show preview
                    with st.expander("📋 Strategy Preview", expanded=True):
                        st.write(f"**Strategy:** {strategy_configs[selected_direction + 2][2]}")
                        st.write(f"**Margin Required:** ₹ {preview_data['margin_required']:,.2f}")
                        st.write("**Legs:**")
                        for leg in preview_data["legs"]:
                            st.write(f"- {leg['option_type']} {leg['strike']} x {leg['qty']} (Expiry: {leg['expiry']})")
                        
                        # Execute button
                        if st.button("✅ Execute Strategy", type="primary", use_container_width=True):
                            exec_res = requests.post(
                                f"{API_URL}/strategy/execute",
                                json={
                                    "session_id": st.session_state.session_id,
                                    "direction_state": selected_direction,
                                    "quantity_multiplier": qty_mult
                                }
                            )
                            if exec_res.status_code == 200:
                                st.success("Strategy executed successfully!")
                                st.session_state.strategy_preview = None
                                st.session_state.selected_direction = None
                                st.rerun()
                            else:
                                st.error(f"Execution failed: {exec_res.text}")
            except Exception as e:
                st.error(f"Error previewing strategy: {e}")
        
        # Skip day option
        st.divider()
        if st.button("⏭️ Skip Day (No Strategy)", use_container_width=True):
            # Move to next step without strategy
            try:
                res = requests.post(f"{API_URL}/session/next", json={"session_id": st.session_state.session_id})
                if res.status_code == 200:
                    data = res.json()
                    new_c = data["spot_candle"]
                    vc = st.session_state.visible_candles
                    if vc and vc[-1]["time"] == new_c["date"]:
                        vc[-1] = {"time": new_c["date"], "open": new_c["open"], "high": new_c["high"], 
                                 "low": new_c["low"], "close": new_c["close"]}
                    else:
                        vc.append({"time": new_c["date"], "open": new_c["open"], "high": new_c["high"], 
                                  "low": new_c["low"], "close": new_c["close"]})
                    st.session_state.replay_state = data.get("state", "INIT")
                    st.session_state.total_pnl = data.get("total_pnl", 0.0)
                    st.session_state.daily_pnl = data.get("daily_pnl", 0.0)
                    st.session_state.active_strategy = data.get("active_positions", [None])[0] if data.get("active_positions") else None
                    st.session_state.selected_direction = None
                    st.rerun()
            except Exception as e:
                st.error(f"Error advancing: {e}")
    
    # Active Strategy Display
    if st.session_state.active_strategy:
        st.info(f"**Active Strategy:** {st.session_state.active_strategy.get('direction_state', 'N/A')} | "
                f"Entry: {st.session_state.active_strategy.get('entry_time', 'N/A')}")
        if st.button("🔴 Close Strategy", type="secondary"):
            close_res = requests.post(
                f"{API_URL}/strategy/close",
                json={"session_id": st.session_state.session_id}
            )
            if close_res.status_code == 200:
                st.success("Strategy closed!")
                st.rerun()
    
    st.divider()
    
    # Next Candle Button
    c1, c2, c3 = st.columns([2, 1, 2])
    with c2:
        if st.button("⏭️ NEXT CANDLE →", use_container_width=True, type="primary"):
            try:
                res = requests.post(f"{API_URL}/session/next", json={"session_id": st.session_state.session_id})
                if res.status_code == 200:
                    data = res.json()
                    new_c = data["spot_candle"]
                    vc = st.session_state.visible_candles
                    
                    # Update or add candle
                    if vc and vc[-1]["time"] == new_c["date"]:
                        vc[-1] = {"time": new_c["date"], "open": new_c["open"], "high": new_c["high"], 
                                 "low": new_c["low"], "close": new_c["close"]}
                    else:
                        vc.append({"time": new_c["date"], "open": new_c["open"], "high": new_c["high"], 
                                  "low": new_c["low"], "close": new_c["close"]})
                    
                    # Update state
                    st.session_state.replay_state = data.get("state", "INIT")
                    st.session_state.total_pnl = data.get("total_pnl", 0.0)
                    st.session_state.daily_pnl = data.get("daily_pnl", 0.0)
                    st.session_state.active_strategy = data.get("active_positions", [None])[0] if data.get("active_positions") else None
                    st.session_state.selected_direction = None
                    
                    st.rerun()
            except Exception as e:
                st.error(f"Error advancing: {e}")
    
    # Sidebar Info
    with st.sidebar:
        st.header("Session Info")
        st.write(f"**State:** {st.session_state.replay_state}")
        st.write(f"**Total PnL:** ₹ {st.session_state.total_pnl:,.2f}")
        if st.session_state.active_strategy:
            st.write(f"**Active Strategy:** {st.session_state.active_strategy.get('direction_state', 'N/A')}")
