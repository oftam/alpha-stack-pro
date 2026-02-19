"""
🧬 ELITE v20 MEDALLION DASHBOARD - Complete Integration
======================================================
הארכיטקטורה המלאה: Genotype + Bayesian + Execution + DUDU + Claude

מחבר את כל הרכיבים:
├─ Dashboard Adapter (5 modules orchestrator)
├─ DUDU Overlay (Manifold Projection)
├─ Divergence Chart (Price vs OnChain)
├─ Claude AI (Expert Analysis)
└─ Defense Protocol (Fail-Safe System)

Run: streamlit run elite_v20_dashboard_MEDALLION.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys
import os
import importlib
from datetime import datetime
from pathlib import Path

# Add paths for module imports
# Dashboard is in dashboards/ - need to go up one level to root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'modules'))

# ============================================================================
# IMPORTS - Core Systems
# ============================================================================

# 1. Elite Adapter (orchestrates all 5 modules)
try:
    from modules.dashboard_adapter import EliteDashboardAdapter
    ELITE_AVAILABLE = True
except ImportError:
    try:
        from dashboard_adapter import EliteDashboardAdapter
        ELITE_AVAILABLE = True
    except ImportError:
        ELITE_AVAILABLE = False
        st.error("⚠️ Elite Adapter not found!")

# 2. DUDU Overlay (Manifold Projection)
try:
    import importlib
    import dudu_overlay
    # Force reload to get latest version
    importlib.reload(dudu_overlay)
    from dudu_overlay import render_projection_tab
    DUDU_AVAILABLE = True
    # Debug: Check which file was loaded
    import os
    dudu_path = dudu_overlay.__file__
    print(f"✅ DUDU loaded from: {dudu_path}")
except ImportError as e:
    DUDU_AVAILABLE = False
    print(f"❌ DUDU Error: {e}")

# 3. Divergence Chart (Liquidity X-Ray)
try:
    from divergence_chart import render_divergence_chart
    DIVERGENCE_AVAILABLE = True
except ImportError:
    DIVERGENCE_AVAILABLE = False

# 4. AI Chat (Gemini - Google Ultra)
try:
    import gemini_chat_module_ELITE_v20
    importlib.reload(gemini_chat_module_ELITE_v20)
    from gemini_chat_module_ELITE_v20 import render_gemini_sidebar_elite, prepare_elite_dashboard_data
    GEMINI_AVAILABLE = True
    print("✅ Gemini AI loaded (Google Ultra) - FORCE RELOADED")
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ Gemini AI not available")

# Legacy Claude support (backup)
CLAUDE_AVAILABLE = False

# 5. Memory System (Organizational Memory)
try:
    from memory_logger import get_logger
    MEMORY_AVAILABLE = True
    print("✅ Memory System loaded")
except ImportError:
    MEMORY_AVAILABLE = False
    print("⚠️ Memory System not available - signals will not be saved")

# 6. Mobile Fortress (Telegram Push Notifications)
try:
    from mobile_notifier import EliteMobileNotifier
    mobile_notifier = EliteMobileNotifier()
    MOBILE_AVAILABLE = mobile_notifier.available
    if MOBILE_AVAILABLE:
        print("✅ Mobile Fortress ready (Telegram)")
    else:
        print("⚠️ Mobile Fortress: Add TELEGRAM_BOT_TOKEN to secrets.toml")
except ImportError:
    MOBILE_AVAILABLE = False
    mobile_notifier = None
    print("⚠️ Mobile Fortress not available")

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Elite v20 Medallion",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 42px;
        font-weight: bold;
        text-align: center;
        color: #00ff00;
        text-shadow: 0 0 10px #00ff00;
        margin-bottom: 10px;
    }
    .metric-card {
        background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%);
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #00ff00;
        margin: 10px 0;
    }
    .regime-blood {
        background: #8b0000;
        color: white;
        padding: 10px;
        border-radius: 5px;
        font-weight: bold;
        text-align: center;
        animation: pulse 2s infinite;
    }
    .regime-normal {
        background: #2d2d2d;
        color: white;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SYSTEM INITIALIZATION
# ============================================================================

@st.cache_resource
def init_elite_system():
    """Initialize Elite v20 system with all modules"""
    if not ELITE_AVAILABLE:
        return None
    
    # Load API keys from environment
    from dotenv import load_dotenv
    load_dotenv()
    
    cryptoquant_key = os.getenv('CRYPTOQUANT_API_KEY')
    glassnode_key = os.getenv('GLASSNODE_API_KEY')
    
    return EliteDashboardAdapter(
        cryptoquant_api_key=cryptoquant_key,
        glassnode_api_key=glassnode_key
    )

@st.cache_resource
def start_sentinel_daemon():
    """
    🛡️ ELITE SENTINEL - Background Market Monitor
    Runs in a separate thread (singleton) to check for signals every 15 mins.
    """
    import threading
    import time
    
    # Validation: Check if already running
    for t in threading.enumerate():
        if t.name == "SentinelWorker":
            print("🛡️ Sentinel already active")
            return

    def sentinel_loop():
        print("🛡️ Sentinel Active: Monitoring market every 15m...")
        last_action = None
        
        # Initialize specialized components for the thread
        try:
            from modules.dashboard_adapter import EliteDashboardAdapter
            from modules.mobile_notifier import EliteMobileNotifier
            import ccxt
            import os
            from dotenv import load_dotenv
            
            load_dotenv()
            notifier = EliteMobileNotifier()
            if not notifier.available:
                print("⚠️ Sentinel disabled: No Telegram config")
                return

            # Initialize adapter (needs keys)
            cryptoquant_key = os.getenv('CRYPTOQUANT_API_KEY')
            glassnode_key = os.getenv('GLASSNODE_API_KEY')
            adapter = EliteDashboardAdapter(cryptoquant_api_key=cryptoquant_key, glassnode_api_key=glassnode_key)
            
            while True:
                try:
                    # 1. Quiet Data Fetch (multi-exchange fallback)
                    for ex_name in ['bybit', 'kraken', 'okx', 'binance']:
                        try:
                            exchange = getattr(ccxt, ex_name)()
                            ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=100)
                            break
                        except Exception:
                            continue
                    else:
                        print("⚠️ Sentinel: All exchanges failed")
                        time.sleep(900)
                        continue
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    current_price = df['close'].iloc[-1]
                    
                    # 2. Quiet Analysis
                    results = adapter.analyze_elite(df, exposure_pct=15.0)
                    
                    # 3. Sentinel Logic
                    current_action = results.get('final_action', 'HOLD')
                    confidence = results.get('confidence', 0)
                    manifold_score = results.get('elite_score', 0)
                    diffusion_score = results.get('onchain', {}).get('diffusion_score', 50)
                    
                    # Fetch real Fear & Greed for Sentinel (no st.cache)
                    try:
                        import requests as req
                        fg_resp = req.get("https://api.alternative.me/fng/", timeout=10)
                        fg_value = int(fg_resp.json()['data'][0]['value'])
                    except Exception:
                        fg_value = 50  # fallback only on error
                    
                    fg_label = "Extreme Fear" if fg_value < 20 else "Fear" if fg_value < 40 else "Neutral" if fg_value < 60 else "Greed" if fg_value < 80 else "Extreme Greed"
                    
                    # Prepare Data
                    alert_data = {
                        'action': current_action,
                        'confidence': int(confidence * 100),
                        'conf_label': "HIGH" if confidence >= 0.8 else "MEDIUM" if confidence >= 0.6 else "LOW",
                        'price': current_price,
                        'dna': round(manifold_score, 1),
                        'div_label': "BULLISH" if diffusion_score > 60 else "BEARISH" if diffusion_score < 40 else "NEUTRAL",
                        'div_score': round(diffusion_score, 1),
                        'sentiment': fg_value,
                        'sent_label': fg_label,
                        'strategy_hint': f"Regime: {results.get('chaos', {}).get('regime', 'NORMAL')}"
                    }
                    
                    # Trigger Conditions
                    should_alert = False
                    
                    # A. Status Change
                    if last_action and current_action != last_action:
                        should_alert = True
                        print(f"🛡️ Sentinel: Action changed {last_action} -> {current_action}")
                    
                    # B. Critical Events
                    if manifold_score >= 82:
                        should_alert = True
                    
                    if diffusion_score >= 80 or diffusion_score <= 20:
                        should_alert = True
                        
                    # Send Alert
                    if should_alert:
                        notifier.send_smart_alert(alert_data)
                        print("🛡️ Sentinel: Alert sent!")
                    
                    last_action = current_action
                    
                except Exception as e:
                    print(f"⚠️ Sentinel Loop Error: {e}")
                
                # Sleep 15 minutes
                time.sleep(900)
                
        except Exception as e:
            print(f"⚠️ Sentinel Startup Error: {e}")

    # Start the thread
    t = threading.Thread(target=sentinel_loop, name="SentinelWorker", daemon=True)
    t.start()
    print("🛡️ Sentinel started in background")

# ============================================================================
# DATA FETCHING
# ============================================================================

@st.cache_data(ttl=300)
def fetch_crypto_data(symbol: str, interval: str, limit: int = 500):
    """Fetch OHLCV with multi-exchange fallback (Binance may be geo-blocked)"""
    import ccxt
    
    # Map symbols: BTCUSDT → BTC/USDT for non-Binance exchanges
    normalized = symbol.replace('USDT', '/USDT').replace('BUSD', '/BUSD') if '/' not in symbol else symbol
    
    exchanges = ['bybit', 'binance', 'kraken', 'okx']
    
    for ex_name in exchanges:
        try:
            exchange = getattr(ccxt, ex_name)()
            sym = symbol if ex_name == 'binance' else normalized
            ohlcv = exchange.fetch_ohlcv(sym, interval, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            print(f"✅ Data from {ex_name}")
            return df
        except Exception as e:
            print(f"⚠️ {ex_name} failed: {e}")
            continue
    
    st.error("All exchanges failed! Check your internet connection.")
    return pd.DataFrame()

# Keep old name as alias for compatibility
fetch_binance_data = fetch_crypto_data

@st.cache_data(ttl=600)
def fetch_fear_greed():
    """Fetch Fear & Greed Index"""
    import requests
    try:
        url = "https://api.alternative.me/fng/"
        r = requests.get(url, timeout=10)
        data = r.json()
        return int(data['data'][0]['value'])
    except:
        return 50  # neutral fallback

# ============================================================================
# MAIN DASHBOARD
# ============================================================================

def main():
    """Main dashboard execution"""
    
    # Initialize system
    elite_system = init_elite_system()

    # Start Sentinel (Background Monitor)
    try:
        start_sentinel_daemon()
    except Exception as e:
        print(f"⚠️ Sentinel startup failed: {e}")
    
    # Initialize memory logger
    memory_logger = None
    if MEMORY_AVAILABLE:
        try:
            memory_logger = get_logger()
        except Exception as e:
            st.warning(f"⚠️ Memory system unavailable: {e}")
    
    # ========================================================================
    # SIDEBAR - Controls & Claude AI
    # ========================================================================
    
    with st.sidebar:
        st.markdown("## ⚙️ System Control")
        
        # Asset selection
        symbol = st.selectbox("Asset", ["BTCUSDT", "ETHUSDT", "SOLUSDT"], index=0)
        interval = st.selectbox("Timeframe", ["1h", "4h", "1d"], index=0)
        
        st.markdown("---")
        
        # Elite Engine toggle
        st.markdown("### 🧬 Elite Protocol")
        enable_elite = st.checkbox("Activate Elite Engine", value=True)
        
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        
        # Defense Protocol Checklist
        st.markdown("### 🛡️ Defense Protocol")
        with st.expander("Pre-Flight Checklist"):
            st.markdown("""
            **Before Trading:**
            - [ ] Data latency < 5 min
            - [ ] API connections active
            - [ ] DUDU windows ≥ 20
            - [ ] Manifold score > 80
            - [ ] Violence score < 3.0
            """)
        
        st.markdown("---")
    
    # ========================================================================
    # HEADER
    # ========================================================================
    
    st.markdown('<div class="main-header">🧬 ELITE v20 MEDALLION</div>', unsafe_allow_html=True)
    st.caption(f"**{symbol}** | Architecture: Genotype → Bayesian → Execution → DUDU → Claude")
    
    # ========================================================================
    # DATA LOADING
    # ========================================================================
    
    with st.spinner("🌀 Connecting to Quantum Field..."):
        df = fetch_crypto_data(symbol, interval)
        fear_greed = fetch_fear_greed()
        
        if df.empty:
            st.error("No data available!")
            st.stop()
        
        current_price = float(df['close'].iloc[-1])
        data_timestamp = df.index[-1]
        
        # Data latency check (Defense Protocol Layer 3)
        # DISABLED: Causing false positives with timestamp comparison
        # TODO: Fix timestamp comparison logic
        # if data_timestamp.tz is None:
        #     data_timestamp = data_timestamp.tz_localize('UTC')
        # now_utc = datetime.now().astimezone(data_timestamp.tz) if data_timestamp.tz else datetime.now()
        # data_age = (now_utc - data_timestamp).total_seconds() / 60
        # if data_age > 5:
        #     st.warning(f"⚠️ Data is {data_age:.1f} min old (threshold: 5 min)")
        
        st.success(f"🟢 Data loaded successfully - {len(df)} bars")
    
    # ========================================================================
    # ELITE ANALYSIS
    # ========================================================================
    
    elite_results = {}
    if enable_elite and elite_system and ELITE_AVAILABLE:
        with st.spinner("🧬 Running Elite Analysis..."):
            elite_results = elite_system.analyze_elite(
                df=df,
                exposure_pct=15.0  # default exposure
            )
            
            # AUTO-LOG SIGNAL TO MEMORY SYSTEM
            if memory_logger and MEMORY_AVAILABLE and elite_results:
                try:
                    signal_id = memory_logger.log_daily_signal(
                        elite_results=elite_results,
                        current_price=current_price
                    )
                    if signal_id:
                        st.success(f"📅 Signal logged to memory (ID: {signal_id})")
                except Exception as e:
                    st.warning(f"⚠️ Memory logging failed: {e}")
    
    # Extract key metrics
    manifold_score = elite_results.get('elite_score', 50) if elite_results else 50
    confidence = elite_results.get('confidence', 0.5) if elite_results else 0.5
    regime = elite_results.get('chaos', {}).get('regime', 'NORMAL') if elite_results else 'NORMAL'
    violence_score = elite_results.get('chaos', {}).get('violence_score', 1.0) if elite_results else 1.0
    diffusion_score = elite_results.get('onchain', {}).get('diffusion_score', 50) if elite_results else 50
    final_action = elite_results.get('final_action', 'HOLD') if elite_results else 'HOLD'
    
    # ========================================================================
    # METRICS BAR
    # ========================================================================
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("BTC Price", f"${current_price:,.0f}", 
                 f"{df['close'].pct_change().iloc[-1]:.2%}")
    
    with col2:
        manifold_color = "🟢" if manifold_score >= 82 else "🟡" if manifold_score >= 65 else "⚪"
        st.metric(f"{manifold_color} Manifold DNA", 
                 f"{manifold_score:.1f}/100",
                 regime)
    
    with col3:
        conf_color = "🟢" if confidence >= 0.8 else "🟡" if confidence >= 0.6 else "🔴"
        st.metric(f"{conf_color} Confidence", 
                 f"{confidence:.1%}",
                 "HIGH" if confidence >= 0.8 else "MEDIUM" if confidence >= 0.6 else "LOW")
    
    with col4:
        fg_emoji = "😱" if fear_greed < 20 else "😐" if fear_greed < 50 else "😊"
        st.metric(f"{fg_emoji} Fear & Greed", 
                 f"{fear_greed}/100",
                 "Extreme Fear" if fear_greed < 20 else "Greed" if fear_greed > 75 else "Neutral")
    
    st.markdown("---")
    
    # ========================================================================
    # REGIME & ACTION BAR
    # ========================================================================
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if regime == "BLOOD_IN_STREETS":
            st.markdown('<div class="regime-blood">🩸 BLOOD IN STREETS - Override Active!</div>', 
                       unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="regime-normal">🏛️ {regime}</div>', 
                       unsafe_allow_html=True)
    
    with col2:
        action_color = {
            'BUY': '🟢',
            'ADD': '🟢',
            'HOLD': '🟡',
            'REDUCE': '🔴',
            'WAIT': '⚪'
        }.get(final_action, '⚪')
        
        st.markdown(f'<div class="regime-normal">{action_color} Commander\'s Call: **{final_action}**</div>', 
                   unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========================================================================
    # TABS
    # ========================================================================
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Market Structure",
        "🧬 Elite Analysis", 
        "🔮 DUDU Projection",
        "🩻 Divergence Chart"
    ])
    
    # ------------------------------------------------------------------------
    # TAB 1: Market Structure
    # ------------------------------------------------------------------------
    with tab1:
        import plotly.graph_objects as go
        
        fig = go.Figure()
        
        # Candlesticks
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price'
        ))
        
        # SMA200 if available
        if len(df) >= 200:
            sma200 = df['close'].rolling(200).mean()
            fig.add_trace(go.Scatter(
                x=df.index,
                y=sma200,
                mode='lines',
                name='SMA200',
                line=dict(color='orange', width=2)
            ))
        
        fig.update_layout(
            template='plotly_dark',
            height=600,
            xaxis_title='Time',
            yaxis_title='Price (USD)',
            hovermode='x unified'
        )
        
        try:
            st.plotly_chart(fig, width="stretch")
        except TypeError:
            st.plotly_chart(fig, use_container_width=True)
        
        # Volume
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Bar(
            x=df.index,
            y=df['volume'],
            name='Volume'
        ))
        fig_vol.update_layout(
            template='plotly_dark',
            height=200,
            showlegend=False
        )
        try:
            st.plotly_chart(fig_vol, width="stretch")
        except TypeError:
            st.plotly_chart(fig_vol, use_container_width=True)
    
    # ------------------------------------------------------------------------
    # TAB 2: Elite Analysis (show all modules)
    # ------------------------------------------------------------------------
    with tab2:
        st.subheader("🧬 Elite v20 - Medallion Analysis")
        
        if enable_elite and elite_system and elite_results:
            # Render the full Elite analysis section
            elite_system.render_elite_section(st, elite_results, df)
        else:
            st.warning("⚠️ Elite Engine is disabled or unavailable")
    
    # ------------------------------------------------------------------------
    # TAB 3: DUDU Projection
    # ------------------------------------------------------------------------
    with tab3:
        st.subheader("🔮 Manifold Projection (DUDU Overlay)")
        st.caption("Past: Regime Filter | Present: Dynamic Vol Cone | Future: Bootstrap Paths")
        
        if DUDU_AVAILABLE:
            # Create QC payload for regime filtering
            qc_payload = {
                'regime': regime,
                'confidence': confidence,
                'qc_codes': [regime]  # Filter historical windows by regime
            }
            
            try:
                # ✅ FIXED: Updated modules/dudu_overlay.py with correct version!
                render_projection_tab(
                    st,
                    df,
                    qc_payload=qc_payload,
                    horizon=48,
                    current_regime=regime,
                    current_violence=violence_score  # 🚀 Dynamic Calibration!
                )
                
                # Undersampling warning (Defense Protocol Layer 4)
                st.info("💡 **Defense Check**: If 'Windows used' < 20, reduce position size by 0.5x")
                
            except Exception as e:
                st.error(f"DUDU Error: {e}")
                import traceback
                st.code(traceback.format_exc())
        else:
            st.warning("⚠️ DUDU Overlay module not available")
    
    # ------------------------------------------------------------------------
    # TAB 4: Divergence Chart
    # ------------------------------------------------------------------------
    with tab4:
        st.subheader("🩻 Liquidity X-Ray (Price vs OnChain)")
        st.caption("Green = Bullish Divergence (Whales buying) | Red = Bearish Divergence")
        
        if DIVERGENCE_AVAILABLE:
            try:
                # Pass the full elite_results dictionary
                render_divergence_chart(
                    st,
                    df,
                    elite_results if elite_results else {}
                )
            except Exception as e:
                st.error(f"Divergence Error: {e}")
        else:
            st.warning("⚠️ Divergence Chart module not available")
    
    # ========================================================================
    # MACRO PULSE (Google Finance Integration)
    # ========================================================================
    
    if GEMINI_AVAILABLE:
        st.markdown("---")
        st.markdown("## 📊 Macro Pulse (Google Finance)")
        st.caption("Real-time market context from Google Finance")
        
        # Fetch macro data
        try:
            from gemini_chat_module_ELITE_v20 import EliteGeminiChat
            if 'gemini_chat' not in st.session_state:
                st.session_state.gemini_chat = EliteGeminiChat()
            
            macro_data = st.session_state.gemini_chat.fetch_macro_pulse()
            
            # Debug info
            st.caption(f"Debug: Status = {macro_data.get('status')}")
            
            if macro_data.get('status') in ['live', 'demo']:
                # Display metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    etf_flow = macro_data.get('btc_etf_flow_24h', 0)
                    delta_color = "normal" if etf_flow >= 0 else "inverse"
                    st.metric(
                        "BTC ETF Flows (24h)", 
                        f"${etf_flow:+.0f}M", 
                        delta=f"{'+' if etf_flow > 0 else ''}Inflow" if etf_flow >= 0 else "Outflow",
                        delta_color=delta_color
                    )
                
                with col2:
                    sp500 = macro_data.get('sp500_change', 0)
                    st.metric(
                        "S&P 500 (Today)", 
                        f"{sp500:+.2f}%",
                        delta="Bullish" if sp500 > 0 else "Bearish"
                    )
                
                with col3:
                    vix = macro_data.get('vix', 0)
                    st.metric(
                        "VIX (Fear Index)", 
                        f"{vix:.1f}",
                        delta="High volatility" if vix > 20 else "Calm"
                    )
                
                with col4:
                    sentiment = macro_data.get('sentiment', 'NEUTRAL')
                    emoji = "🟢" if sentiment == "Bullish" else "🔴" if sentiment == "Bearish" else "🟡"
                    st.metric(
                        "Market Sentiment", 
                        f"{emoji} {sentiment}"
                    )
                
                # Divergence Alert
                if diffusion_score > 70 and etf_flow < -200:
                    st.warning("""
                    ⚠️ **DIVERGENCE ALERT!**
                    
                    - **On-Chain:** 🟢 Whales accumulating (Score: {:.0f}/100)
                    - **ETF Flows:** 🔴 Retail selling (${:+.0f}M outflow)
                    - **Action:** SNIPER ENTRY opportunity (institutional vs retail split)
                    """.format(diffusion_score, etf_flow))
                
                elif diffusion_score < 50 and etf_flow > 200:
                    st.info("""
                    ℹ️ **Macro Confluence:**
                    
                    - **On-Chain:** 🟡 Neutral activity
                    - **ETF Flows:** 🟢 Retail buying (${:+.0f}M inflow)
                    - **Note:** Watch for on-chain confirmation
                    """.format(etf_flow))
                
                st.caption(f"Last updated: {macro_data.get('timestamp', 'N/A')}")
                
                # Show note if demo mode
                if macro_data.get('status') == 'demo':
                    st.info("ℹ️ **Demo Mode:** Using sample data. Real-time Google Finance data requires Gemini Pro API (paid tier).")
            
            else:
                st.info("⚠️ Macro data unavailable - check API connectivity")
        
        except Exception as e:
            st.warning(f"⚠️ Macro Pulse error: {str(e)}")
    
    
    # ========================================================================
    # AI CHAT (Gemini in sidebar)
    # ========================================================================
    
    if GEMINI_AVAILABLE:
        # Prepare dashboard data for Gemini
        dashboard_data = prepare_elite_dashboard_data(
            market_data={
                'symbol': symbol,
                'current_price': current_price,
                'price_change_24h': 0  # Add if available
            },
            portfolio_data={
                'capital': {'total_value': 10000, 'available': 5000},
                'dca': {'btc_held': 0.05, 'avg_entry': 95000},
                'tactical': {'active_positions': 0, 'total_pnl': 0}
            },
            signals={
                'dca': {'status': final_action, 'manifold_score': manifold_score, 'regime': regime},
                'tactical': {'direction': final_action, 'confidence': confidence}
            },
            modules={
                'Manifold DNA': manifold_score,
                'OnChain Diffusion': diffusion_score,
                'Chaos/Violence': violence_score,
                'Fear & Greed': fear_greed
            },
            risk_metrics={
                'max_risk_pct': 5.0,
                'kelly_fraction': 0.25,
                'current_exposure': 0
            },
            performance={
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'rr_ratio': 0
            }
        )
        
        # Render Gemini sidebar
        render_gemini_sidebar_elite(dashboard_data)
    
    # ========================================================================
    # MOBILE FORTRESS - Sidebar Panel
    # ========================================================================
    
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📱 Mobile Fortress")
        
        if MOBILE_AVAILABLE:
            st.success("✅ Telegram Connected")
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🧪 Test Alert", key="test_telegram"):
                    mobile_notifier.test_connection()
                    st.success("Sent!")
            with col_b:
                if st.button("📊 Daily Brief", key="daily_brief"):
                    brief_data = {
                        'action': final_action,
                        'confidence': confidence,
                        'price': current_price,
                        'dna': manifold_score,
                        'div_label': "BULLISH" if diffusion_score > 60 else "BEARISH" if diffusion_score < 40 else "NEUTRAL",
                        'div_score': diffusion_score,
                        'sentiment': fear_greed,
                        'strategy_hint': f"Regime: {regime}"
                    }
                    mobile_notifier.daily_summary(brief_data)
                    st.success("Sent!")
            
            # Auto-alert on Victory Vector
            if final_action in ["SNIPER_BUY", "BUY"] and confidence > 80:
                if 'last_alert_action' not in st.session_state or \
                   st.session_state.last_alert_action != final_action:
                    mobile_notifier.alert_victory_vector(
                        score=manifold_score,
                        kelly_fraction=0.25,
                        action="BUY"
                    )
                    st.session_state.last_alert_action = final_action
                    st.toast("🚨 Alert sent to phone!", icon="📱")
        else:
            st.warning("📵 Not configured")
            st.caption("Add to secrets.toml:")
            st.code("""TELEGRAM_BOT_TOKEN = "..."
TELEGRAM_CHAT_ID = "..." """, language="toml")
            st.markdown("[Setup Guide →](https://t.me/BotFather)")
    
    # ========================================================================
    # FOOTER
    # ========================================================================
    
    st.markdown("---")
    st.caption(f"""
    🚀 **Elite v20 Medallion** | Last Update: {data_timestamp.strftime('%Y-%m-%d %H:%M UTC')}
    
    **System Status:**
    - Elite Adapter: {'✅' if ELITE_AVAILABLE else '❌'}
    - DUDU Overlay: {'✅' if DUDU_AVAILABLE else '❌'}
    - Divergence: {'✅' if DIVERGENCE_AVAILABLE else '❌'}
    - Gemini AI: {'✅' if GEMINI_AVAILABLE else '❌'}
    """)

# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    main()
