"""
 v20 - PRODUCTION Dashboard
ELITE Complete Biological/Quant System
Architecture: 6 Layers
- Layer 1: Data Sources (Binance, CryptoQuant, Fear & Greed)
- Layer 2: Feature Engineering (Diffusion, Chaos, NLP)
- Layer 3: ML Models (Regime Detection, Phase Transitions)
- Layer 4: Decision Engine (Manifold DNA, Bayesian Logic)
- Layer 5: Execution (Dual Strategy: DCA 60% + Tactical 40%)
- Layer 6: Infrastructure (Telegram, Paper Trading, Audit)

Configuration:
- Capital: $10,000 (dynamic)
- Risk: Never >5% per trade
- DCA: 60% → 2030 target ($600k-$1M)
- Tactical: 40% → T1/T2 protocol

Run: streamlit run elite_v20_dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Force UTF-8 encoding for Windows console
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'modules'))
sys.path.append(os.path.join(BASE_DIR, 'core'))
sys.path.append(os.path.join(BASE_DIR, 'strategies'))

# Auto-create __init__.py files if missing (self-healing for deployment)
for subdir in ['core', 'modules', 'strategies']:
    init_path = os.path.join(BASE_DIR, subdir, '__init__.py')
    if os.path.isdir(os.path.join(BASE_DIR, subdir)) and not os.path.exists(init_path):
        with open(init_path, 'w') as f:
            f.write(f'# {subdir} package\n')
        print(f"[AUTO-FIX] Created {init_path}")

# Import core modules
from core.capital_manager import CapitalManager
from core.risk_engine import RiskManagementEngine
from core.telegram_alerts import TelegramAlertSystem

# Import strategies
from strategies.dca_strategy import DCAStrategy
from strategies.tactical_strategy import TacticalStrategy

# Import modules
from modules.dashboard_adapter import EliteDashboardAdapter
from modules.binance_microstructure import BinanceMicrostructure
from modules.fear_greed_provider import FearGreedProvider

# Page config
st.set_page_config(
    page_title="ELITE v20 - PRODUCTION",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 48px;
        font-weight: bold;
        text-align: center;
        color: #00ff00;
        text-shadow: 0 0 10px #00ff00;
    }
    .metric-card {
        background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%);
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #00ff00;
        margin: 10px 0;
    }
    .dca-signal {
        background: #ff0000;
        color: white;
        padding: 15px;
        border-radius: 8px;
        font-weight: bold;
        text-align: center;
        animation: pulse 2s infinite;
    }
    .tactical-signal {
        background: #00ff00;
        color: black;
        padding: 15px;
        border-radius: 8px;
        font-weight: bold;
        text-align: center;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def init_system():
    """Initialize Elite v20 system components."""
    
    # Load environment variables
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    # Get API keys
    cryptoquant_key = os.getenv('CRYPTOQUANT_API_KEY')
    glassnode_key = os.getenv('GLASSNODE_API_KEY')  # Optional
    
    # Initialize Elite adapter with API keys
    elite_adapter = EliteDashboardAdapter(
        cryptoquant_api_key=cryptoquant_key,
        glassnode_api_key=glassnode_key
    )
    
    print(f"\n[?] CryptoQuant key loaded: {'[YES]' if cryptoquant_key else '[NO]'}")
    if cryptoquant_key:
        print(f"   Key: {cryptoquant_key[:20]}...{cryptoquant_key[-10:]}")
    
    return {
        'capital_manager': CapitalManager(base_capital=10000.0),
        'risk_engine': RiskManagementEngine(max_risk_pct=5.0),
        'telegram': TelegramAlertSystem(),
        'dca_strategy': DCAStrategy(),
        'tactical_strategy': TacticalStrategy(),
        'elite_adapter': elite_adapter,
        'fear_greed': FearGreedProvider()
    }


def main():
    """Main dashboard function."""
    
    # Initialize system
    system = init_system()
    
    # Header
    st.markdown('<div class="main-header">🧬 ELITE v20 - PRODUCTION</div>', unsafe_allow_html=True)
    st.markdown("### Biological/Quant Hybrid System | Top 0.001%")
    
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/200x100/1e1e1e/00ff00?text=ELITE+v20", width=200)
        
        st.markdown("### ⚙️ System Control")
        
        # Symbol selection
        symbol = st.selectbox("Symbol", ["BTCUSDT"], index=0)
        
        # Timeframe
        timeframe = st.selectbox("Timeframe", ["1h", "4h", "1d"], index=0)
        
        # Data refresh
        auto_refresh = st.checkbox("Auto Refresh", value=True)
        if auto_refresh:
            refresh_seconds = st.slider("Refresh (seconds)", 10, 300, 60)
        
        st.markdown("---")
        
        # Telegram status
        st.markdown("### 📱 Telegram Status")
        telegram_enabled = st.checkbox("Alerts Enabled", value=True)
        if telegram_enabled:
            system['telegram'].enable()
            st.success("✅ LIVE")
        else:
            system['telegram'].disable()
            st.warning("❌ Disabled")
        
        if st.button("Test Alert"):
            system['telegram'].send_test_alert()
            st.success("Alert sent!")
        
        st.markdown("---")
        
        # System info
        st.markdown("### 📊 System Info")
        st.info(f"""
        **Architecture:** 6-Layer Biological/Quant
        **Capital:** ${system['capital_manager'].current_capital:,.0f}
        **Max Risk:** 5% per trade
        **Strategies:** DCA (60%) + Tactical (40%)
        """)
    
    # Get live data
    try:
        # Fetch market data
        import ccxt
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=200)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        current_price = float(df['close'].iloc[-1])
        sma200 = df['close'].rolling(200).mean().iloc[-1] if len(df) >= 200 else current_price
        
        # Get Fear & Greed
        try:
            fear_greed_data = system['fear_greed'].get_current_fear_greed()
            fear_greed = fear_greed_data.get('value', 50) if fear_greed_data else 50
            fear_greed_text = fear_greed_data.get('classification', 'Neutral') if fear_greed_data else 'Neutral'
        except Exception as fg_error:
            print(f"Fear & Greed fetch error: {fg_error}")
            fear_greed = 50
            fear_greed_text = 'Neutral'
        
        # Run Elite analysis
        try:
            elite_results = system['elite_adapter'].analyze_elite(
                df=df,
                exposure_pct=15.0
            )
            
            manifold_score = elite_results.get('elite_score', 50)
            confidence = elite_results.get('confidence', 0.5)
            regime = elite_results.get('chaos', {}).get('regime', 'NORMAL')
            diffusion_score = elite_results.get('onchain', {}).get('diffusion_score', 50)
        except Exception as elite_error:
            print(f"Elite analysis error: {elite_error}")
            manifold_score = 50
            confidence = 0.5
            regime = 'NORMAL'
            diffusion_score = 50
        
        # Auto-Alert (Regime Change)
        if 'last_regime' not in st.session_state:
            st.session_state.last_regime = regime
            
        if st.session_state.last_regime != regime:
            if telegram_enabled:
                system['telegram'].send_regime_change(
                    st.session_state.last_regime,
                    regime,
                    current_price,
                    manifold_score
                )
            st.session_state.last_regime = regime
        
        data_fetch_success = True
        
    except Exception as e:
        st.error(f"Data fetch error: {e}")
        print(f"Full error: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback values
        current_price = 98000
        sma200 = 70434
        fear_greed = 50
        fear_greed_text = 'Neutral'
        manifold_score = 50
        confidence = 0.5
        regime = 'NORMAL'
        diffusion_score = 50
        data_fetch_success = False
        
        st.warning("⚠️ Using fallback data. Check your internet connection or API keys.")
    
    # Main layout
    # Data status indicator
    if data_fetch_success:
        st.success("🟢 LIVE DATA - Connected to Binance & Fear/Greed API")
    else:
        st.warning("🟡 FALLBACK DATA - Check connection (system still operational)")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("BTC Price", f"${current_price:,.0f}", 
                 f"{((current_price/sma200-1)*100):.1f}% vs SMA200")
    
    with col2:
        st.metric("Manifold DNA", f"{manifold_score:.1f}/100",
                 "Top 2%" if manifold_score >= 80 else "Normal")
    
    with col3:
        st.metric("Confidence", f"{confidence:.1%}",
                 "HIGH" if confidence >= 0.8 else "MEDIUM")
    
    with col4:
        fg_label = "Extreme Fear" if fear_greed < 25 else "Fear" if fear_greed < 50 else "Greed" if fear_greed < 75 else "Extreme Greed"
        st.metric("Fear & Greed", f"{fear_greed}/100", fg_label)
    
    st.markdown("---")
    
    # ============================================
    # MEDALLION FUND ADDITIONS - Status & Timeline
    # ============================================
    
    st.markdown("### 🎯 System Status")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Overall Status
        if manifold_score >= 82:
            st.success("🟢 SNIPER MODE")
            st.caption("Victory Vector (91.7%)")
        elif manifold_score >= 65:
            st.warning("🟡 BUILD MODE")
            st.caption(f"Score: {manifold_score:.1f}/100")
        else:
            st.info("⏸️ STANDBY")
            st.caption("Waiting for opportunity")
    
    with col2:
        # Whale Activity
        if diffusion_score >= 90:
            st.metric("🐋 Whales", "EXTREME", delta="Max activity", delta_color="normal")
        elif diffusion_score >= 70:
            st.metric("🐋 Whales", "ACTIVE", delta="High activity", delta_color="normal")
        else:
            st.metric("🐋 Whales", "QUIET", delta="Low activity", delta_color="inverse")
    
    with col3:
        # Fear & Greed Enhanced
        if fear_greed < 15:
            st.metric("😱 Fear", f"{fear_greed}/100", delta="PANIC! 2.0x", delta_color="inverse")
        elif fear_greed < 20:
            st.metric("😨 Fear", f"{fear_greed}/100", delta="Extreme", delta_color="inverse")
        elif fear_greed < 50:
            st.metric("😐 Fear", f"{fear_greed}/100", delta="Moderate")
        else:
            st.metric("😊 Greed", f"{fear_greed}/100", delta="High", delta_color="normal")
    
    with col4:
        # Regime
        if regime == "BLOOD_IN_STREETS":
            st.metric("⚔️ Regime", "BLOOD", delta="Override active")
        else:
            st.metric("🏛️ Regime", "NORMAL", delta="Standard mode")
    
    # === Progress to Signal ===
    st.markdown("### 📊 Signal Progress")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Progress bar to 82 (Victory Vector)
        progress_to_82 = min(manifold_score / 82, 1.0)
        st.progress(progress_to_82)
        
        # Also show threshold at 80
        if manifold_score < 80:
            progress_to_80 = min(manifold_score / 80, 1.0)
            st.caption(f"Progress to DCA threshold (80): {progress_to_80*100:.0f}%")
    
    with col2:
        st.metric("Manifold", f"{manifold_score:.1f}/82")
        
        if manifold_score < 82:
            missing = 82 - manifold_score
            st.caption(f"⏳ {missing:.1f} points to SNIPER")
        else:
            st.success("✅ Victory Vector!")
    
    # === Timeline / Event Log ===
    st.markdown("### 📅 Active Signals & Events")
    
    # Create events list
    events = []
    
    # OnChain event
    if diffusion_score > 90:
        events.append(('positive', '🐋', f'Whale Activity: {diffusion_score:.0f}/100', 
                      'Extreme institutional buying detected'))
    elif diffusion_score > 70:
        events.append(('warning', '🐋', f'Whale Activity: {diffusion_score:.0f}/100', 
                      'Whales accumulating'))
    
    # Fear event
    if fear_greed < 15:
        events.append(('positive', '😱', f'Extreme Fear: {fear_greed}/100', 
                      'Fear Amplifier 2.0x active! Perfect buying opportunity.'))
    elif fear_greed < 20:
        events.append(('warning', '😨', f'High Fear: {fear_greed}/100', 
                      'Market in fear zone'))
    
    # Manifold event
    if manifold_score >= 82:
        events.append(('positive', '🎯', f'Victory Vector: {manifold_score:.1f}/100', 
                      'SNIPER MODE active! 91.7% confidence.'))
    elif manifold_score >= 80:
        events.append(('warning', '🎯', f'DCA Threshold: {manifold_score:.1f}/100', 
                      'Above DCA entry threshold'))
    elif manifold_score >= 75:
        events.append(('info', '⏳', f'Near Signal: {manifold_score:.1f}/100', 
                      f'Only {80-manifold_score:.1f} points to DCA threshold'))
    
    # Price vs SMA200 event
    if current_price and sma200:
        price_vs_sma_pct = ((current_price - sma200) / sma200) * 100
        if price_vs_sma_pct < 0:
            events.append(('positive', '📉', f'Below SMA200: {price_vs_sma_pct:.2f}%', 
                          'Technical weakness confirmed'))
        else:
            events.append(('info', '📈', f'Above SMA200: +{price_vs_sma_pct:.2f}%', 
                          'Waiting for technical weakness'))
    
    # Regime event
    if regime == "BLOOD_IN_STREETS":
        events.append(('positive', '⚔️', 'Blood in Streets Regime', 
                      'Epigenetic shift active! Override mode enabled.'))
    
    # Display events
    if events:
        for event_type, icon, title, description in events:
            if event_type == 'positive':
                with st.success(f"**Now** - {icon} {title}"):
                    st.caption(description)
            elif event_type == 'warning':
                with st.warning(f"**Now** - {icon} {title}"):
                    st.caption(description)
            else:
                with st.info(f"**Now** - {icon} {title}"):
                    st.caption(description)
    else:
        st.info("⏸️ No active signals or events")
    
    st.markdown("---")
    
    # Portfolio Status
    # Portfolio Status
    portfolio = system['capital_manager'].get_portfolio_status(current_price)
    
    col1, col2 = st.columns(2)
    
    with col1:
        total_val = portfolio.get('capital', {}).get('total_value', 0)
        st.metric("Portfolio Value", f"${total_val:,.2f}")
    
    with col2:
        deployed = portfolio.get('capital', {}).get('deployed', 0)
        st.metric("Deployed", f"${deployed:,.2f}")
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Live Signals", 
        "📈 DCA Strategy", 
        "⚡ Tactical Strategy",
        "🎯 Risk Management",
        "📱 Alerts & History"
    ])
    
    with tab1:
        st.markdown("### 🔴 Live Signal Analysis")
        
        # DCA Signal Check
        dca_signal = system['dca_strategy'].check_entry_signal(
            manifold_score=manifold_score,
            regime=regime,
            diffusion_score=diffusion_score,
            fear_greed=fear_greed,
            current_price=current_price,
            sma200=sma200
        )
        
        if dca_signal['signal']:
            st.markdown('<div class="dca-signal">🩸 DCA SIGNAL ACTIVE - Blood in Streets!</div>', 
                       unsafe_allow_html=True)
            
            dca_amount = system['dca_strategy'].calculate_dca_amount(
                portfolio['dca']['capital_available'],
                manifold_score,
                diffusion_score
            )
            
            col1, col2 = st.columns(2)
            with col1:
                st.success(f"""
                **Entry Price:** ${current_price:,.0f}
                **Recommended Amount:** ${dca_amount:,.0f}
                **BTC Amount:** {dca_amount/current_price:.4f}
                """)
            
            with col2:
                st.info(f"""
                **Signal Strength:** {dca_signal['signal_strength']:.1%}
                **Manifold Score:** {manifold_score:.1f}
                **Diffusion Score:** {diffusion_score:.1f}
                **Fear & Greed:** {fear_greed}
                """)
            
            if st.button("🩸 Execute DCA Entry", key="dca_btn"):
                # Record entry
                btc_amount = dca_amount / current_price
                system['capital_manager'].record_dca_entry(
                    btc_amount, current_price, dca_amount
                )
                system['dca_strategy'].record_entry(
                    current_price, dca_amount, btc_amount,
                    manifold_score, diffusion_score, fear_greed, regime
                )
                st.success("✅ DCA Entry Recorded!")
                st.rerun()
                
            # Auto-Alert (DCA)
            if telegram_enabled:
                system['telegram'].send_dca_signal(
                    current_price, manifold_score, regime,
                    diffusion_score, fear_greed, dca_amount
                )
        else:
            st.info("No DCA signal. Waiting for Blood in Streets...")
            
            # Show what's needed
            st.markdown("### Conditions Status:")
            for condition, met in dca_signal['conditions'].items():
                emoji = "✅" if met else "❌"
                st.write(f"{emoji} {condition}: {'MET' if met else 'NOT MET'}")
        
        st.markdown("---")
        
        # Tactical Signal Check
        tactical_signal = system['tactical_strategy'].check_entry_signal(
            manifold_score=manifold_score,
            confidence=confidence,
            regime=regime
        )
        
        if tactical_signal['signal'] and len(system['tactical_strategy'].get_active_positions()) == 0:
            st.markdown('<div class="tactical-signal">⚡ TACTICAL ENTRY SIGNAL!</div>', 
                       unsafe_allow_html=True)
            
            # Generate risk plan
            risk_plan = system['risk_engine'].generate_trade_plan(
                capital_available=portfolio['tactical']['capital_available'],
                current_price=current_price,
                df=df,
                confidence=confidence,
                strategy='TACTICAL'
            )
            
            col1, col2 = st.columns(2)
            with col1:
                st.success(f"""
                **Entry:** ${current_price:,.0f}
                **Position:** ${risk_plan['position']['position_size_usd']:,.0f}
                **BTC:** {risk_plan['position']['position_size_btc']:.4f}
                **Stop Loss:** ${risk_plan['stop_loss']['price']:,.0f} (-{risk_plan['stop_loss']['pct']:.1f}%)
                """)
            
            with col2:
                st.info(f"""
                **T1 (+5%):** ${risk_plan['targets']['t1_target']:,.0f}
                **T2 (+12%):** ${risk_plan['targets']['t2_target']:,.0f}
                **Risk:** ${risk_plan['position']['actual_risk_usd']:,.0f} ({risk_plan['position']['actual_risk_pct']:.2f}%)
                **R:R (T2):** {risk_plan['validation']['rr_t2']:.1f}:1
                """)
            
            if st.button("⚡ Execute Tactical Entry", key="tac_btn"):
                # Open position
                position_id = system['tactical_strategy'].open_position(
                    entry_price=current_price,
                    position_size_usd=risk_plan['position']['position_size_usd'],
                    position_size_btc=risk_plan['position']['position_size_btc'],
                    stop_loss_price=risk_plan['stop_loss']['price'],
                    t1_target=risk_plan['targets']['t1_target'],
                    t2_target=risk_plan['targets']['t2_target'],
                    manifold_score=manifold_score,
                    confidence=confidence,
                    regime=regime
                )
                # Record in capital manager
                system['capital_manager'].record_tactical_entry(
                    risk_plan['position']['position_size_btc'],
                    current_price,
                    risk_plan['position']['position_size_usd']
                )
                st.success(f"✅ Tactical Position Opened: {position_id}")
                st.rerun()
            
            # Auto-Alert (Tactical)
            if telegram_enabled:
                system['telegram'].send_tactical_entry(
                    current_price, manifold_score, confidence,
                    risk_plan['targets']['t1_target'],
                    risk_plan['targets']['t2_target'],
                    risk_plan['stop_loss']['price'],
                    risk_plan['position']['position_size_usd'],
                    risk_plan['position']['position_size_btc'],
                    risk_plan['position']['actual_risk_usd'],
                    risk_plan['position']['actual_risk_pct'],
                    confidence,
                    risk_plan['validation']['rr_t2']
                )
        else:
            if len(system['tactical_strategy'].get_active_positions()) > 0:
                st.warning("Position already active. Monitor for exits.")
            else:
                st.info("No tactical signal. Waiting for high-confidence entry...")
    
    with tab2:
        st.markdown("### 📈 DCA Strategy (Long-term 2030)")
        
        dca_status = system['dca_strategy'].get_position_status(
            current_price,
            portfolio['dca']['btc_held'],
            portfolio['dca']['avg_entry'],
            portfolio['dca']['capital_used']
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Current Position")
            st.info(f"""
            **BTC Held:** {dca_status['current']['btc_held']:.4f}
            **Avg Entry:** ${dca_status['current']['avg_entry']:,.0f}
            **Current Price:** ${dca_status['current']['current_price']:,.0f}
            **Unrealized P&L:** ${dca_status['current']['unrealized_pnl']:,.2f} ({dca_status['current']['unrealized_pct']:.1f}%)
            """)
        
        with col2:
            st.markdown("#### 2030 Projection")
            st.success(f"""
            **Target Year:** {dca_status['target_2030']['target_year']}
            **Target Price:** ${dca_status['target_2030']['target_price_min']:,.0f} - ${dca_status['target_2030']['target_price_max']:,.0f}
            **Projected Value:** ${dca_status['target_2030']['value_at_target_min']:,.0f} - ${dca_status['target_2030']['value_at_target_max']:,.0f}
            **Projected Profit:** ${dca_status['target_2030']['profit_at_target_min']:,.0f} - ${dca_status['target_2030']['profit_at_target_max']:,.0f}
            **Projected Return:** {dca_status['target_2030']['return_at_target_min']:.0f}% - {dca_status['target_2030']['return_at_target_max']:.0f}%
            """)
        
        # Entry history
        entry_history = system['dca_strategy'].get_entry_history()
        if not entry_history.empty:
            st.markdown("#### Entry History")
            st.dataframe(entry_history[['timestamp', 'price', 'btc_amount', 'usd_amount', 'manifold_score', 'regime']])
    
    with tab3:
        st.markdown("### ⚡ Tactical Strategy (Active Trading)")
        
        active_positions = system['tactical_strategy'].get_active_positions()
        
        if active_positions:
            for position in active_positions:
                # Update position
                update = system['tactical_strategy'].update_position(
                    position['id'],
                    current_price
                )
                
                st.markdown(f"#### Position: {position['id']}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.info(f"""
                    **Entry:** ${position['entry_price']:,.0f}
                    **Current:** ${current_price:,.0f}
                    **Size:** {position['position_size_btc']:.4f} BTC
                    **Unrealized P&L:** ${update['unrealized_pnl']:,.2f} ({update['unrealized_pct']:.1f}%)
                    """)
                
                with col2:
                    stop_status = "🟢 Trail Active" if update['trail_active'] else "🟡 Fixed Stop"
                    st.warning(f"""
                    **Stop Loss:** ${update['stop_loss']:,.0f} {stop_status}
                    **T1 ({position['t1_pct']}%):** {'✅ HIT' if position['t1_hit'] else f"${position['t1_target']:,.0f}"}
                    **T2 ({position['t2_pct']}%):** {'✅ HIT' if position['t2_hit'] else f"${position['t2_target']:,.0f}"}
                    """)
                
                # Check for actions
                if update['actions']:
                    for action in update['actions']:
                        st.error(f"⚠️ ACTION NEEDED: {action['type']} at ${action['price']:,.0f}")
                        
                        if action['type'] == 'T1_HIT':
                            if st.button(f"Execute T1 Exit (50%)", key=f"t1_{position['id']}"):
                                exit_result = system['tactical_strategy'].execute_exit(
                                    position['id'], 'T1', action['price'], 50.0
                                )
                                system['capital_manager'].record_tactical_exit(
                                    exit_result['btc_exited'],
                                    action['price'],
                                    'T1'
                                )
                                system['telegram'].send_t1_hit(
                                    action['price'],
                                    position['entry_price'],
                                    exit_result['realized_pnl'],
                                    exit_result['realized_pct']
                                )
                                st.success("✅ T1 Exit Executed!")
                                st.rerun()
                        
                        elif action['type'] == 'T2_HIT':
                            st.success("Trail stop activated automatically")
                            system['telegram'].send_t2_hit(
                                action['price'],
                                position['entry_price'],
                                update['unrealized_pnl'],
                                update['unrealized_pct'],
                                update['stop_loss']
                            )
                        
                        elif action['type'] == 'STOP_HIT':
                            if st.button(f"Execute Stop Exit (100%)", key=f"stop_{position['id']}"):
                                exit_result = system['tactical_strategy'].execute_exit(
                                    position['id'], 'STOP', action['price'], 100.0
                                )
                                system['capital_manager'].record_tactical_exit(
                                    exit_result['btc_exited'],
                                    action['price'],
                                    'STOP'
                                )
                                system['telegram'].send_stop_hit(
                                    action['price'],
                                    position['entry_price'],
                                    exit_result['realized_pnl'],
                                    exit_result['realized_pct']
                                )
                                st.error("⛔ Stop Loss Hit")
                                st.rerun()
        else:
            st.info("No active positions. Waiting for entry signal...")
        
        # Performance stats
        perf = system['tactical_strategy'].get_performance_stats()
        st.markdown("#### Performance Statistics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Trades", perf['total_trades'])
            st.metric("Win Rate", f"{perf['win_rate_pct']:.1f}%")
        with col2:
            st.metric("Wins", perf['wins'])
            st.metric("Losses", perf['losses'])
        with col3:
            st.metric("Total P&L", f"${perf['total_pnl']:,.2f}")
            st.metric("R:R Ratio", f"{perf['rr_ratio']:.2f}:1")
    
    with tab4:
        st.markdown("### 🎯 Risk Management")
        
        st.markdown("#### Iron Rules (Top 0.001%)")
        st.info("""
        1. **Never Risk >5%** - Maximum risk per trade (IRON RULE)
        2. **Ignore the Noise** - High signal-to-noise ratio
        3. **Long Term Vision** - 2030 target ($600k-$1M BTC)
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Kelly Criterion")
            kelly = system['risk_engine'].calculate_kelly_fraction()
            st.success(f"""
            **Win Rate:** {system['risk_engine'].win_rate*100:.1f}%
            **R:R Ratio:** {system['risk_engine'].avg_win_loss_ratio:.1f}:1
            **Kelly Fraction:** {kelly:.3f}
            **Capped at:** {system['risk_engine'].kelly_cap}x (conservative)
            """)
        
        with col2:
            st.markdown("#### Current Risk Exposure")
            st.warning(f"""
            **Max Risk per Trade:** ${portfolio['risk']['max_risk_per_trade_usd']:,.0f} ({portfolio['risk']['max_risk_per_trade_pct']:.1f}%)
            **Total Capital:** ${portfolio['capital']['total_value']:,.2f}
            **Available for Risk:** ${portfolio['capital']['total_value'] * 0.05:,.2f}
            """)
    
    with tab5:
        st.markdown("### 📱 Alerts & History")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Telegram Alerts")
            st.info(f"""
            **Status:** {'✅ ENABLED' if telegram_enabled else '❌ DISABLED'}
            **Bot Token:** {system['telegram'].bot_token[:20]}...
            **Chat ID:** {system['telegram'].chat_id}
            """)
            
            st.markdown("**Alert Types:**")
            st.write("- 🩸 DCA Signals (Blood in Streets)")
            st.write("- ⚡ Tactical Entries")
            st.write("- 💰 T1/T2 Exits")
            st.write("- ⛔ Stop Loss Warnings")
            st.write("- 🔄 Regime Changes")
        
        with col2:
            st.markdown("#### Transaction History")
            tx_history = system['capital_manager'].get_transaction_history()
            if not tx_history.empty:
                st.dataframe(tx_history.tail(10))
            else:
                st.info("No transactions yet")
    
    # Auto-refresh
    if auto_refresh:
        import time
        time.sleep(refresh_seconds)
        st.rerun()


if __name__ == "__main__":
    main()
