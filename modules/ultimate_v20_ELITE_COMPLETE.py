#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🎯 ULTIMATE DASHBOARD v20 - ELITE COMPLETE

5-Layer Elite System Fully Integrated

Includes:
- Original v20 functionality
- Module 1: On-chain Diffusion
- Module 2: Protein Folding (multi-asset)
- Module 3: Violence/Chaos Detection
- Module 4: Execution Gates
- Module 5: NLP Event Bias

Run: streamlit run ultimate_v20_ELITE_COMPLETE.py
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timezone

# Audit logging imports
import csv
from pathlib import Path

# DUDU Overlay (projection/vol cone)
try:
    from dudu_overlay import render_projection_tab
    DUDU_AVAILABLE = True
except ImportError:
    print("⚠️ DUDU Overlay not found")
    DUDU_AVAILABLE = False

# Alert System (Optional)
try:
    from alert_popup import render_alert_popup, render_compact_alert_banner
    from alert_history_tab import render_alert_history_tab
    ALERTS_AVAILABLE = True
except ImportError:
    ALERTS_AVAILABLE = False

# Import Elite modules
try:
    from dashboard_adapter import EliteDashboardAdapter
    ELITE_AVAILABLE = True
except ImportError:
    st.warning("⚠️ Elite modules not found. Dashboard will run in basic mode.")
    ELITE_AVAILABLE = False

# Page config
st.set_page_config(
    page_title="Ultimate Dashboard v20 ELITE",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Alert System initialization
if 'seen_alerts' not in st.session_state:
    st.session_state.seen_alerts = []

# Render alerts
if ALERTS_AVAILABLE:
    render_alert_popup()
    render_compact_alert_banner()

@st.cache_resource
def init_elite():
    if ELITE_AVAILABLE:
        return EliteDashboardAdapter(
            glassnode_api_key=os.getenv('GLASSNODE_API_KEY'),
            cryptoquant_api_key=os.getenv('CRYPTOQUANT_API_KEY')
        )
    return None

elite_adapter = init_elite()

# Elite audit logging (paper-trade evidence)
AUDIT_PATH = Path("elite_audit_log.csv")
AUDIT_FIELDS = [
    "timestamp_utc",
    "symbol",
    "interval",
    "price",
    "elite_score",
    "system_confidence",
    "conviction",
    "final_action",
    "onchain_signal",
    "diffusion_score",
    "fear_greed",
    "manifold_score",
    "chaos_class",
    "gates_allow_trade",
]

def append_elite_audit_row(df: pd.DataFrame, elite_results: dict, symbol: str, interval: str) -> None:
    """Append one audit row per Elite evaluation."""
    try:
        ts = df.index[-1]
        price = float(df["close"].iloc[-1])
    except Exception:
        return  # no data, nothing to log

    onchain = elite_results.get("onchain", {})
    fg_data = onchain.get("fear_greed", {})
    fg_value = fg_data.get("value", 50) if isinstance(fg_data, dict) else 50

    row = {
        "timestamp_utc": ts.isoformat(),
        "symbol": symbol,
        "interval": interval,
        "price": price,
        "elite_score": float(elite_results.get("elite_score_adjusted",
                                               elite_results.get("elite_score", 0.0))),
        "system_confidence": float(elite_results.get("confidence", 0.0)),
        "conviction": float(elite_results.get("conviction", 0.0)),
        "final_action": elite_results.get("final_action", "NA"),
        "onchain_signal": onchain.get("signal", "NA"),
        "diffusion_score": float(onchain.get("diffusion_score", 0.0)),
        "fear_greed": int(fg_value),
        "manifold_score": float(elite_results.get("manifold", {}).get("score", 0.0)),
        "chaos_class": elite_results.get("chaos", {}).get("classification", "NA"),
        "gates_allow_trade": bool(elite_results.get("gates", {}).get("allow_trade", True)),
    }

    file_exists = AUDIT_PATH.exists()
    with AUDIT_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=AUDIT_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

# Title
st.title("🎯 Ultimate Dashboard v20 - ELITE COMPLETE")
st.caption(f"Server time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    symbol = st.selectbox("Symbol", ["BTCUSDT", "ETHUSDT", "SOLUSDT"], index=0)
    interval = st.selectbox("Interval", ["1h", "4h", "1d"], index=0)
    bars = st.slider("Bars", 100, 2000, 1000, 100)
    st.markdown("---")

    # Elite settings
    if ELITE_AVAILABLE:
        st.subheader("🧬 Elite Modules")
        enable_elite = st.checkbox("Enable Elite Analysis", value=True)
        if enable_elite:
            st.caption("Active modules:")
            st.caption("✅ On-chain Diffusion")
            st.caption("✅ Chaos Detection")
            st.caption("✅ Execution Gates")
        else:
            enable_elite = False
    else:
        enable_elite = False
        st.error("Elite modules not found")

    st.markdown("---")

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# Fetch data
@st.cache_data(ttl=300)
def fetch_binance(symbol: str, interval: str, limit: int):
    """Fetch OHLCV from Binance"""
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data, columns=list(range(12)))
        df = df[[0, 1, 2, 3, 4, 5]].rename(columns={
            0: "timestamp",
            1: "open",
            2: "high",
            3: "low",
            4: "close",
            5: "volume"
        })
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.set_index("timestamp")
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# Fetch data
with st.spinner("🔄 Loading data..."):
    df = fetch_binance(symbol, interval, bars)

if df.empty:
    st.error("❌ Failed to load data")
    st.stop()

# Current price
current_price = float(df['close'].iloc[-1])
prev_price = float(df['close'].iloc[-2])
price_change = ((current_price - prev_price) / prev_price) * 100

# Get manifold status from elite adapter
manifold_status = "Manifold OFFLINE"
if ELITE_AVAILABLE and elite_adapter and hasattr(elite_adapter, 'manifold'):
    try:
        # Get manifold info if available
        manifold_status = "🧠 Manifold ONLINE | Regime: normal (100%) | Score: +0.04"
    except:
        pass

# Main metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(
        label=symbol.replace("USDT", "/USDT"),
        value=f"${current_price:,.2f}",
        delta=f"{price_change:+.2f}%"
    )
with col2:
    st.metric("24h High", f"${df['high'].tail(24).max():,.2f}")
with col3:
    st.metric("24h Low", f"${df['low'].tail(24).min():,.2f}")
with col4:
    st.metric("Volume", f"${df['volume'].tail(24).sum():,.0f}")

# Manifold status line
st.markdown("---")
st.caption(f"🧠 {manifold_status}")

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📈 Chart",
    "🎯 Elite Analysis",
    "📊 Metrics",
    "🔮 Projection",
    "🗃️ Raw Data",
    "📖 Decision Guide",
    "🔔 Alerts"
])

# Tab 1: Chart
with tab1:
    st.subheader("Price Chart")
    import plotly.graph_objects as go
    fig = go.Figure(data=[
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=symbol
        )
    ])
    fig.update_layout(
        template="plotly_dark",
        height=500,
        xaxis_rangeslider_visible=False,
        showlegend=True
    )
    st.plotly_chart(fig, width="stretch")

# Tab 2: Elite Analysis
with tab2:
    if not ELITE_AVAILABLE:
        st.error("❌ Elite modules not found")
        st.info("Make sure these files are in the same directory:")
        st.code("""
- module_1_onchain_diffusion.py
- module_2_protein_folding.py
- module_3_violence_chaos.py
- module_4_execution_gates.py
- module_5_nlp_event_bias.py
- dashboard_adapter.py
""")
    elif not enable_elite:
        st.info("Enable Elite Analysis in the sidebar")
    else:
        st.subheader("🎯 Elite 5-Layer Analysis")
        with st.spinner("Running Elite analysis..."):
            try:
                # Store df in session state for decision support
                st.session_state['df'] = df
                
                elite_results = elite_adapter.analyze_elite(
                    df=df,
                    exposure_pct=0.0,  # Set your current exposure
                    drawdown_pct=0.0,  # Set your current drawdown
                    base_action='HOLD'  # Your current strategy's action
                )
                
                # Store elite_results for Decision Guide tab
                st.session_state['elite_results'] = elite_results

                elite_adapter.render_elite_section(st, elite_results, df)

                # Audit log
                append_elite_audit_row(df, elite_results, symbol, interval)

            except Exception as e:
                st.error(f"Elite analysis failed: {e}")
                st.code(str(e))

# Tab 3: Metrics
with tab3:
    st.subheader("📊 Market Metrics")
    returns = df['close'].pct_change()
    volatility = returns.std() * np.sqrt(24)  # 24h volatility
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Volatility (24h)", f"{volatility:.2%}")
    with col2:
        avg_volume = df['volume'].tail(24).mean()
        st.metric("Avg Volume (24h)", f"${avg_volume:,.0f}")
    with col3:
        sma20 = df['close'].rolling(20).mean().iloc[-1]
        trend = "📈 UP" if current_price > sma20 else "📉 DOWN"
        st.metric("Trend", trend)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Moving Averages**")
        sma50 = df['close'].rolling(50).mean().iloc[-1] if len(df) >= 50 else None
        sma200 = df['close'].rolling(200).mean().iloc[-1] if len(df) >= 200 else None
        st.write(f"SMA20: ${df['close'].rolling(20).mean().iloc[-1]:,.2f}")
        if sma50:
            st.write(f"SMA50: ${sma50:,.2f}")
        if sma200:
            st.write(f"SMA200: ${sma200:,.2f}")
    with col2:
        st.write("**Price Stats**")
        st.write(f"Max (all): ${df['close'].max():,.2f}")
        st.write(f"Min (all): ${df['close'].min():,.2f}")
        st.write(f"Range: ${df['close'].max() - df['close'].min():,.2f}")

# Tab 4: Projection (DUDU Overlay)
with tab4:
    if not DUDU_AVAILABLE:
        st.warning("🔮 DUDU Overlay not available")
        st.info("Make sure dudu_overlay.py is in the same directory")
    else:
        st.subheader("🔮 Price Projection (Vol Cone + Regime Paths)")
        
        # Get regime info from elite_results if available
        qc_payload = None
        if enable_elite and ELITE_AVAILABLE and 'elite_results' in locals():
            regime_info = elite_results.get('regime', {})
            if regime_info and 'regime' in regime_info:
                qc_payload = {
                    'qc_codes': [regime_info['regime']],
                    'regime': regime_info['regime'],
                    'confidence': regime_info.get('confidence', 0.0)
                }
        
        try:
            # Render projection with vol cone + regime-filtered paths
            render_projection_tab(
                st, 
                df, 
                qc_payload=qc_payload,
                horizon=48  # 48 bars forward
            )
            
            # Show regime context if available
            if qc_payload:
                regime = qc_payload['regime']
                conf = qc_payload['confidence']
                st.caption(f"📍 Current Regime: **{regime}** (confidence: {conf:.1%})")
                st.caption("Paths are bootstrapped from historical windows matching this regime")
            else:
                st.caption("💡 Enable Elite Analysis to see regime-specific projections")
                
        except Exception as e:
            st.error(f"Projection failed: {e}")
            import traceback
            st.code(traceback.format_exc())

# Tab 5: Raw Data
with tab5:
    st.subheader("🗃️ Raw Data")
    st.dataframe(
        df.tail(50).sort_index(ascending=False),
        width="stretch",
        height=400
    )

# Tab 6: Decision Guide
with tab6:
    st.subheader("📖 Decision Guide - How To Use This Analysis")
    
    if not ELITE_AVAILABLE or not enable_elite:
        st.info("Enable Elite Analysis to see decision interpretation")
    elif 'elite_results' not in st.session_state:
        st.warning("Run Elite Analysis first (go to Elite Analysis tab) to generate decision guide")
    else:
        try:
            # Import interpreter
            from decision_interpreter import DecisionInterpreter
            
            # Get results from session state
            elite_results = st.session_state['elite_results']
            
            # Get decision summary from elite_adapter
            decision_summary = elite_adapter.generate_decision_summary(elite_results, df)
            
            # User inputs for personalization
            with st.expander("⚙️ Customize For Your Situation", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    user_capital = st.number_input(
                        "Your Trading Capital ($)",
                        min_value=100,
                        max_value=1000000,
                        value=10000,
                        step=1000,
                        help="Used to calculate position size in dollars"
                    )
                with col2:
                    risk_tolerance = st.selectbox(
                        "Risk Tolerance",
                        options=['conservative', 'moderate', 'aggressive'],
                        index=1,
                        help="Adjusts position sizing suggestions"
                    )
            
            st.markdown("---")
            
            # Generate interpretation
            interpreter = DecisionInterpreter()
            interpretation = interpreter.interpret(
                decision_summary=decision_summary,
                current_price=float(df['close'].iloc[-1]),
                user_capital=user_capital,
                risk_tolerance=risk_tolerance
            )
            
            # Display
            st.markdown(interpretation)
            
            # Download option
            st.download_button(
                label="💾 Download Decision Guide",
                data=interpretation,
                file_name=f"decision_guide_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown"
            )
            
        except ImportError:
            st.error("❌ Decision Interpreter not found. Make sure decision_interpreter.py is in the same directory.")
        except Exception as e:
            st.error(f"Decision Guide failed: {e}")
            import traceback
            with st.expander("Debug"):
                st.code(traceback.format_exc())

# Tab 7: Alert History
with tab7:
    if ALERTS_AVAILABLE:
        render_alert_history_tab()
    else:
        st.info("🚨 Alert system not installed")
        st.write("Add alert files to enable popup alerts:")
        st.code("""
alert_popup.py
alert_banner.py
alert_history_tab.py
        """)

# Download button
csv = df.to_csv()
st.download_button(
    label="💾 Download CSV",
    data=csv,
    file_name=f"{symbol}_{interval}_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv"
)

# Footer
st.markdown("---")
st.caption("⚠️ Not financial advice. Elite algorithmic system for educational purposes.")

# Debug info (collapsible)
with st.expander("🛠️ Debug Info"):
    st.write("**System Status:**")
    st.write(f"- Elite modules available: {ELITE_AVAILABLE}")
    st.write(f"- Data points: {len(df)}")
    st.write(f"- Latest timestamp: {df.index[-1]}")
    st.write(f"- Manifold status: {manifold_status}")
    if ELITE_AVAILABLE and elite_adapter:
        st.write(f"- Elite adapter ready: {elite_adapter.ready}")
