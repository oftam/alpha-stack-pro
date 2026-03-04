#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 ELITE v20 - MULTI-TIMEFRAME DASHBOARD (Standalone)
Real-time confluence analysis across 1H, 4H, 1D

Port 8511
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys
import os

# Add paths - dashboard is in dashboards/, need to go up one level
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'modules'))
sys.path.append(os.path.join(BASE_DIR, 'scripts'))  # For multi_timeframe_dashboard_ORIGINAL.py

# Import the multi-timeframe class
from multi_timeframe_dashboard_ORIGINAL import MultiTimeframeDashboard

# Import Elite adapter for analysis
try:
    from modules.dashboard_adapter import EliteDashboardAdapter
    ELITE_AVAILABLE = True
except:
    ELITE_AVAILABLE = False

# Page config
st.set_page_config(
    page_title="Multi-Timeframe - ELITE v20",
    page_icon="📊",
    layout="wide"
)

# Initialize
mtf = MultiTimeframeDashboard()

# Sidebar controls
with st.sidebar:
    st.image("https://via.placeholder.com/200x100/1e1e1e/00ff00?text=MTF+Analysis", width=200)
    st.markdown("### ⚙️ Controls")
    
    symbol = st.selectbox("Symbol", ["BTCUSDT"], index=0)
    
    auto_refresh = st.checkbox("Auto Refresh", value=False)
    if auto_refresh:
        refresh_seconds = st.slider("Refresh (seconds)", 30, 300, 60)
    
    st.markdown("---")
    st.info("""
    **Multi-Timeframe Analysis**
    
    📊 Analyzes 1H, 4H, 1D
    🎯 Confluence detection
    🚨 Priority alerts
    """)

# Get data from Binance
try:
    import ccxt
    exchange = ccxt.binance()
    
    signals_data = {}
    
    # Fetch and analyze each timeframe
    for tf in ['1h', '4h', '1d']:
        try:
            # Fetch OHLCV
            limit = 500 if tf == '1h' else 300
            ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Simple analysis (can be replaced with Elite adapter)
            if ELITE_AVAILABLE:
                # Use Elite analysis
                try:
                    from dotenv import load_dotenv
                    load_dotenv()
                    
                    cryptoquant_key = os.getenv('CRYPTOQUANT_API_KEY')
                    elite_adapter = EliteDashboardAdapter(
                        cryptoquant_api_key=cryptoquant_key,
                        glassnode_api_key=None
                    )
                    
                    elite_results = elite_adapter.analyze_elite(df=df, exposure_pct=15.0)
                    
                    signals_data[tf] = {
                        'manifold': elite_results.get('elite_score', 50),
                        'confidence': elite_results.get('confidence', 0.5),
                        'diffusion': elite_results.get('onchain', {}).get('diffusion_score', 50),
                        'regime': elite_results.get('chaos', {}).get('regime', 'NORMAL')
                    }
                except Exception as e:
                    print(f"Elite analysis error for {tf}: {e}")
                    # Fallback to simple analysis
                    signals_data[tf] = _simple_analysis(df)
            else:
                # Simple moving average based analysis
                signals_data[tf] = _simple_analysis(df)
                
        except Exception as e:
            print(f"Error fetching {tf}: {e}")
            signals_data[tf] = {
                'manifold': 50,
                'confidence': 0.5,
                'diffusion': 50,
                'regime': 'UNKNOWN'
            }
    
    data_fetch_success = True

except Exception as e:
    st.error(f"Data fetch error: {e}")
    
    # Fallback mock data
    signals_data = {
        '1h': {'manifold': 75.2, 'confidence': 0.82, 'diffusion': 68.5, 'regime': 'VOLATILE'},
        '4h': {'manifold': 82.1, 'confidence': 0.88, 'diffusion': 79.3, 'regime': 'NORMAL'},
        '1d': {'manifold': 71.8, 'confidence': 0.75, 'diffusion': 72.1, 'regime': 'NORMAL'}
    }
    data_fetch_success = False
    st.warning("⚠️ Using fallback data")

# Helper function for simple analysis
def _simple_analysis(df):
    """Simple MA-based analysis when Elite not available"""
    close = df['close']
    
    # Calculate MAs
    sma20 = close.rolling(20).mean().iloc[-1] if len(df) >= 20 else close.iloc[-1]
    sma50 = close.rolling(50).mean().iloc[-1] if len(df) >= 50 else close.iloc[-1]
    current = close.iloc[-1]
    
    # Simple scoring
    if current > sma20 > sma50:
        manifold = 75 + np.random.rand() * 10
        confidence = 0.7 + np.random.rand() * 0.2
    elif current < sma20 < sma50:
        manifold = 25 + np.random.rand() * 10
        confidence = 0.7 + np.random.rand() * 0.2
    else:
        manifold = 45 + np.random.rand() * 10
        confidence = 0.5 + np.random.rand() * 0.2
    
    return {
        'manifold': manifold,
        'confidence': confidence,
        'diffusion': manifold * 0.9,  # Approximate
        'regime': 'TRENDING' if abs(current - sma20) / sma20 > 0.02 else 'NORMAL'
    }

# Status indicator
if data_fetch_success:
    st.success("🟢 LIVE DATA - Connected to Binance")
else:
    st.warning("🟡 FALLBACK DATA - Demo mode")

# Render the MTF dashboard
mtf.render_dashboard(signals_data)

# Auto-refresh
if auto_refresh and data_fetch_success:
    import time
    time.sleep(refresh_seconds)
    st.rerun()
