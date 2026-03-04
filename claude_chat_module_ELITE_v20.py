"""
ELITE v20 - Claude AI Chat Module (OPTIMIZED)
==============================================
מודול Claude מותאם ל-ELITE v20 Architecture

התאמות:
- מבין את 6 השכבות של ELITE v20
- מכיר DCA vs Tactical strategies
- מנתח Manifold DNA scores
- מסביר Risk management
- מתאים להודעות Telegram
"""

import streamlit as st
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional, List


class EliteClaudeChat:
    """
    Claude AI Chat integration for ELITE v20 Dashboard
    Optimized for 6-layer biological/quant system
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Claude chat for ELITE v20."""
        self.api_key = api_key or st.secrets.get("ANTHROPIC_API_KEY", "")
        self.api_url = "https://api.anthropic.com/v1/messages"
        
    def _format_elite_context(self, dashboard_data: Dict[str, Any]) -> str:
        """
        מכין context מפורט מנתוני ELITE v20
        """
        context_parts = [
            "=== ELITE v20 Trading System - Real-Time Data ===",
            f"Timestamp: {dashboard_data.get('timestamp', datetime.now().isoformat())}",
            ""
        ]
        
        # Market Data
        if 'market' in dashboard_data:
            market = dashboard_data['market']
            context_parts.append("## MARKET DATA")
            context_parts.append(f"Symbol: {market.get('symbol', 'BTCUSDT')}")
            context_parts.append(f"Current Price: ${market.get('current_price', 0):,.2f}")
            context_parts.append(f"24h Change: {market.get('price_change_24h', 0):.2f}%")
            context_parts.append(f"Volume: {market.get('volume', 0):,.0f}")
            context_parts.append("")
        
        # Portfolio Status
        if 'portfolio' in dashboard_data:
            portfolio = dashboard_data['portfolio']
            context_parts.append("## PORTFOLIO STATUS")
            
            if 'capital' in portfolio:
                cap = portfolio['capital']
                context_parts.append(f"Total Capital: ${cap.get('total_value', 0):,.2f}")
                context_parts.append(f"Available: ${cap.get('available', 0):,.2f}")
                context_parts.append(f"Deployed: ${cap.get('deployed', 0):,.2f}")
            
            if 'dca' in portfolio:
                dca = portfolio['dca']
                context_parts.append(f"\nDCA Strategy (60%):")
                context_parts.append(f"  BTC Held: {dca.get('btc_held', 0):.4f}")
                context_parts.append(f"  Avg Entry: ${dca.get('avg_entry', 0):,.0f}")
                context_parts.append(f"  Unrealized P&L: ${dca.get('unrealized_pnl', 0):,.2f}")
            
            if 'tactical' in portfolio:
                tact = portfolio['tactical']
                context_parts.append(f"\nTactical Strategy (40%):")
                context_parts.append(f"  Active Positions: {tact.get('active_positions', 0)}")
                context_parts.append(f"  Total P&L: ${tact.get('total_pnl', 0):,.2f}")
                context_parts.append(f"  Win Rate: {tact.get('win_rate', 0):.1f}%")
            
            context_parts.append("")
        
        # Signals
        if 'signals' in dashboard_data:
            signals = dashboard_data['signals']
            context_parts.append("## CURRENT SIGNALS")
            
            if 'dca' in signals:
                dca_sig = signals['dca']
                context_parts.append(f"DCA Signal: {dca_sig.get('status', 'NO_SIGNAL')}")
                if dca_sig.get('manifold_score'):
                    context_parts.append(f"  Manifold Score: {dca_sig['manifold_score']:.2f}/100")
                if dca_sig.get('regime'):
                    context_parts.append(f"  Regime: {dca_sig['regime']}")
            
            if 'tactical' in signals:
                tact_sig = signals['tactical']
                context_parts.append(f"\nTactical Signal: {tact_sig.get('direction', 'NO_SIGNAL')}")
                if tact_sig.get('confidence'):
                    context_parts.append(f"  Confidence: {tact_sig['confidence']:.1f}%")
                if tact_sig.get('suggested_size'):
                    context_parts.append(f"  Suggested Size: ${tact_sig['suggested_size']:,.0f}")
            
            context_parts.append("")
        
        # Module Scores (The DNA!)
        if 'modules' in dashboard_data:
            modules = dashboard_data['modules']
            context_parts.append("## MODULE SCORES (System DNA)")
            for module_name, score in modules.items():
                context_parts.append(f"{module_name}: {score:.2f}/100")
            context_parts.append("")
        
        # Risk Metrics
        if 'risk' in dashboard_data:
            risk = dashboard_data['risk']
            context_parts.append("## RISK MANAGEMENT")
            context_parts.append(f"Max Risk per Trade: {risk.get('max_risk_pct', 5):.1f}%")
            context_parts.append(f"Kelly Fraction: {risk.get('kelly_fraction', 0):.3f}")
            context_parts.append(f"Current Exposure: ${risk.get('current_exposure', 0):,.0f}")
            context_parts.append("")
        
        # Performance Stats
        if 'performance' in dashboard_data:
            perf = dashboard_data['performance']
            context_parts.append("## PERFORMANCE STATISTICS")
            context_parts.append(f"Total Trades: {perf.get('total_trades', 0)}")
            context_parts.append(f"Win Rate: {perf.get('win_rate', 0):.1f}%")
            context_parts.append(f"Total P&L: ${perf.get('total_pnl', 0):,.2f}")
            context_parts.append(f"R:R Ratio: {perf.get('rr_ratio', 0):.2f}:1")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def ask_claude(
        self, 
        question: str, 
        dashboard_data: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[list] = None
    ) -> str:
        """
        שואל את Claude עם context מלא מ-ELITE v20
        """
        if not self.api_key:
            return "❌ API Key חסר! הוסף ANTHROPIC_API_KEY ב-.streamlit/secrets.toml"
        
        try:
            # Prepare messages
            messages = []
            
            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history)
            
            # Prepare current message
            user_message = question
            if dashboard_data:
                context = self._format_elite_context(dashboard_data)
                user_message = f"{context}\n\n---\n\nUser question: {question}"
            
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            # Call API
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 2000,
                "messages": messages,
                "system": """אתה עוזר AI מומחה למערכת המסחר ELITE v20 - Medallion Fund inspired system.

🎯 CRITICAL SYSTEM KNOWLEDGE - קרא בעיון!

SCALES (חשוב מאוד!):
- OnChain Diffusion: 0-100 scale (NOT 0-10!)
- Manifold DNA: 0-100 scale (NOT 0-10!)
- Other modules: 0-10 scale
- UI may show "/10" - ignore! Read as "/100" for OnChain & Manifold!

ONCHAIN DIFFUSION FORMULA (Victory Vector):
X1 = min(100, [0.4·Netflow + 0.4·Whales + 0.2·SOPR] × FearAmplifier)

FearAmplifier:
- Fear < 15: 2.0x (פחד קיצוני - מכפיל פי 2!)
- Fear ≥ 15: 1.0x (רגיל)

Example: OnChain = 100/100
- Fear = 8 → FearAmplifier = 2.0x
- [40 (Netflow) + 50 (Whales) + 15 (SOPR)] × 2.0 = 210
- min(100, 210) = 100 ← PERFECT SCORE!
- Meaning: לווייתנים צוברים מקסימלי בזמן פאניקה!

ENTRY THRESHOLDS - חשוב להבין!:

Score ≥ 82.3 (Victory Vector - SNIPER MODE):
→ הסתברות בייסיאנית: 91.7%
→ Commander's Override: מתעלם מטכני שלילי
→ Position Size: 1.2x-1.5x (aggressive)
→ Regime: BLOOD_IN_STREETS
→ Strategy: מכה אחת, מהירה, אגרסיבית

Score 80-82 (High Confidence):
→ הסתברות: ~85%
→ Override: חלקי
→ Position Size: 1.0x (standard)
→ Entry: חזק אבל זהיר

Score 65-80 (BUILD/ACCUMULATION MODE):
→ הסתברות: 60-70%
→ NO Override: חייב אישור טכני
→ Position Size: 0.5x-0.8x (small portions)
→ Strategy: בניה איטית, מדורגת (DCA style)
→ Risk: גבוה יותר, צריך validation נוסף

Score < 65:
→ NO ENTRY - HOLD
→ המתן לתנאים טובים יותר

DUDU OVERLAY - "כוונת" המערכת (HUD):

P10/P50/P90 Paths (נתיבי הסתברות):
- P10 (10th percentile): התרחיש הפסימי
  → "ב-90% מהמקרים ההיסטוריים המחיר היה גבוה יותר"
  → זו "רצפת הבטון" - Stop Loss מנטלי
- P50 (Median): התוחלת הסבירה ביותר
- P90 (90th percentile): התרחיש האופטימי
  → פוטנציאל מקסימלי

Vol Cone (גבולות פיזיקליים):
- מבוסס על Brownian Motion: σ√t
- +2σ: קצה עליון - מחיר "מתוח" מדי
  → אל תקנה! Mean reversion צפוי
- -2σ: קצה תחתון - "קפיץ דרוך"
  → DCA אגרסיבי! הסתברות גבוהה לעלייה

Regime-Filtered Bootstrap:
- לא סתם סימולציה אקראית!
- שולף רק מקרים היסטוריים דומים לregime הנוכחי
- אם BLOOD_IN_STREETS → מביא 120 מקרים של דם ברחובות
- "מה השוק עשה תמיד במצב הזה" ≠ "מה השוק יעשה"

DCA Strategy עם DUDU:
1. Price ≈ P10 → הכפל DCA (2.0x)
2. Price ≈ P50 → DCA רגיל (1.0x)
3. Price ≈ P90 → צמצם/עצור (0.5x או HOLD)
4. Price נוגע ב-Vol Cone תחתון → DCA אגרסיבי!

ELITE v20 Architecture (6 Layers):
- Layer 1: Data Sources (Binance, CryptoQuant, Fear & Greed)
- Layer 2: Feature Engineering (OnChain 0-100, Protein/Violence/NLP 0-10)
- Layer 3: ML Models (Regime Detection, Phase Transitions)
- Layer 4: Decision Engine (Manifold DNA 0-100, Bayesian Logic)
- Layer 5: Execution (DCA 60% + Tactical 40%)
- Layer 6: Infrastructure (Telegram, Risk Management, DUDU Overlay)

Strategies:
1. **DCA (60%)**: "Blood in Streets" - buy panic with DUDU guidance
2. **Tactical (40%)**: Active trading with T1/T2 protocol

DCA Triggers (ALL required for >80 score):
✅ OnChain > 70 (whale accumulation)
✅ Fear < 20 (extreme fear)
✅ Price < SMA200 (technical weakness)
✅ Manifold > 80 (high confidence)

For 65-80 score (BUILD mode):
✅ OnChain > 70
✅ Fear < 20
✅ Technical confirmation needed
→ Smaller position, gradual entry

Your role:
- הסבר את המערכת בצורה מלאה ומדויקת (Medallion Fund level!)
- כשנשאל על OnChain 100 - הסבר Fear Amplifier + הנוסחה!
- כשנשאל על כניסה <80 - הסבר BUILD vs SNIPER modes!
- כשנשאל על DUDU - הסבר P10/P50/P90 + Vol Cone!
- נתח Manifold DNA scores (0-100!)
- הסבר למה יש או אין סיגנלים

Iron Rules:
1. Never Risk >5% per trade
2. Ignore the Noise - only strong signals
3. Long Term Vision - 2030 target ($600k-$1M BTC)
4. Discipline > FOMO - wait for optimal conditions!
5. DUDU Overlay = your HUD - use it!

תענה תמיד בעברית בצורה ברורה, מלאה ומקצועית.
תן תשובות ברמת Medallion Fund - מקיפות, מדויקות, עם הסברים מתמטיים!
"""
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60  # Increased from 30 to 60 seconds
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["content"][0]["text"]
            else:
                return f"❌ שגיאה: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"❌ שגיאה בחיבור ל-Claude: {str(e)}"


def render_claude_sidebar_elite(dashboard_data: Optional[Dict[str, Any]] = None):
    """
    מציג Claude chat בסיידבר - גרסה מותאמת ל-ELITE v20
    
    Args:
        dashboard_data: נתונים מה-ELITE v20 dashboard
    """
    
    # Initialize chat
    if 'claude_chat' not in st.session_state:
        st.session_state.claude_chat = EliteClaudeChat()
    
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    
    # Sidebar chat
    with st.sidebar:
        st.markdown("---")
        st.markdown("## 🤖 Claude AI Assistant")
        st.caption("*ELITE v20 Expert*")
        
        # Controls
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄", help="Clear chat"):
                st.session_state.chat_messages = []
                st.rerun()
        
        # Chat container
        chat_container = st.container(height=400)
        
        with chat_container:
            # Display messages
            for msg in st.session_state.chat_messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            
            # Chat input
            user_input = st.chat_input("שאל אותי על המסחר...")
            
            if user_input:
                # Add user message
                st.session_state.chat_messages.append({
                    "role": "user",
                    "content": user_input
                })
                
                # Get Claude response
                with st.spinner("🤔 Claude מנתח..."):
                    # Prepare history
                    api_history = [
                        {"role": msg["role"], "content": msg["content"]}
                        for msg in st.session_state.chat_messages[:-1]
                    ]
                    
                    response = st.session_state.claude_chat.ask_claude(
                        question=user_input,
                        dashboard_data=dashboard_data,
                        conversation_history=api_history if api_history else None
                    )
                
                # Add response
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": response
                })
                
                st.rerun()
        
        # Quick questions
        with st.expander("💡 שאלות נפוצות"):
            quick_qs = [
                "מה המצב הכללי?",
                "למה אין סיגנל היום?",
                "מה ה-Manifold DNA אומר?",
                "מה הסיכון שלי?",
                "האם כדאי להיכנס עכשיו?"
            ]
            
            for q in quick_qs:
                if st.button(q, key=f"quick_{hash(q)}", use_container_width=True):
                    st.session_state.chat_messages.append({
                        "role": "user",
                        "content": q
                    })
                    st.rerun()


# Helper function to prepare dashboard data
def prepare_elite_dashboard_data(
    portfolio: Dict,
    signals: Dict,
    modules: Dict,
    current_price: float,
    symbol: str = "BTCUSDT",
    **kwargs
) -> Dict[str, Any]:
    """
    מכין את הנתונים בפורמט הנכון ל-Claude
    
    Usage:
        dashboard_data = prepare_elite_dashboard_data(
            portfolio=portfolio,
            signals={'dca': dca_signal, 'tactical': tactical_signal},
            modules={'Module 1': 7.5, 'Module 2': 8.2, ...},
            current_price=current_price,
            symbol=symbol
        )
        render_claude_sidebar_elite(dashboard_data)
    """
    return {
        'timestamp': datetime.now().isoformat(),
        'market': {
            'symbol': symbol,
            'current_price': current_price,
            **kwargs.get('market', {})
        },
        'portfolio': portfolio,
        'signals': signals,
        'modules': modules,
        'risk': kwargs.get('risk', {}),
        'performance': kwargs.get('performance', {})
    }
