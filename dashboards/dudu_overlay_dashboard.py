#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 DUDU OVERLAY - Standalone Dashboard
Vol Cone + Regime Paths Projection
ELITE v20 - Dashboard #3 (Port 8512)
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys
import os

# Add paths - dashboard is in dashboards/, need to go up one level
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Import dudu overlay from modules directory
try:
    from modules.dudu_overlay import render_projection_tab
    DUDU_AVAILABLE = True
except ImportError:
    try:
        from dudu_overlay import render_projection_tab
        DUDU_AVAILABLE = True
    except ImportError as e:
        DUDU_AVAILABLE = False
        st.error(f"⚠️ DUDU module not found: {e}")

# Page config
st.set_page_config(
    page_title="DUDU Overlay - ELITE v20",
    page_icon="📊",
    layout="wide"
)

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/200x100/1e1e1e/00ff00?text=DUDU+Overlay", width=200)
    st.markdown("### ⚙️ Controls")
    
    symbol = st.selectbox("Symbol", ["BTCUSDT"], index=0)
    timeframe = st.selectbox("Timeframe", ["1h", "4h", "1d"], index=0)
    horizon = st.slider("Projection Horizon (bars)", 24, 96, 48)
    
    auto_refresh = st.checkbox("Auto Refresh", value=False)
    if auto_refresh:
        refresh_seconds = st.slider("Refresh (seconds)", 30, 300, 60)
    
    st.markdown("---")
    st.info("""
    **DUDU Overlay**
    
    📈 Vol Cone projection
    🎲 Regime-based paths
    📊 Bootstrap simulation
    """)

st.title("📊 DUDU Overlay - Projection Dashboard")
st.caption("Vol Cone + Regime Paths | ELITE v20")

# Get market data
try:
    import ccxt
    exchange = ccxt.binance()
    
    # Fetch data
    limit = 1200 if timeframe == '1h' else 500
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    
    current_price = float(df['close'].iloc[-1])
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Price", f"${current_price:,.0f}")
    with col2:
        change_24h = ((df['close'].iloc[-1] - df['close'].iloc[-24]) / df['close'].iloc[-24] * 100) if len(df) >= 24 else 0
        st.metric("24h Change", f"{change_24h:.2f}%")
    with col3:
        vol = df['close'].pct_change().std() * 100
        st.metric("Volatility", f"{vol:.2f}%")
    
    st.markdown("---")
    
    st.success("🟢 LIVE DATA - Connected to Binance")
    
    # Render projection
    render_projection_tab(st, df, qc_payload=None, horizon=horizon)
    
    data_success = True

except Exception as e:
    st.error(f"Data fetch error: {e}")
    st.warning("⚠️ Using fallback demo data")
    
    # Generate demo data
    dates = pd.date_range(end=pd.Timestamp.now(), periods=500, freq='1H')
    price = 70000
    returns = np.random.randn(500) * 0.02
    prices = price * np.cumprod(1 + returns)
    
    df = pd.DataFrame({
        'close': prices
    }, index=dates)
    
    render_projection_tab(st, df, qc_payload=None, horizon=48)
    
    data_success = False

# Info section
with st.expander("ℹ️ About DUDU Overlay"):
    st.markdown("""
    ### Vol Cone + Regime Paths Projection
    
    **Vol Cone:**
    - Shows volatility-based price bands
    - 1σ and 2σ confidence intervals
    - Based on historical volatility
    
    **Regime Paths:**
    - Bootstrap simulation of future price paths
    - Uses similar historical market regimes
    - Shows P10, P50 (median), P90 percentiles
    
    **Use Cases:**
    - Set realistic profit targets
    - Plan position sizing
    - Understand potential price ranges
    - Risk management
    """)

# Auto-refresh
if auto_refresh and data_success:
    import time
    time.sleep(refresh_seconds)
    st.rerun()
