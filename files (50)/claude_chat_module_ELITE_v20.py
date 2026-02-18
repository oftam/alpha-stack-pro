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
                    context_parts.append(f"  Manifold Score: {dca_sig['manifold_score']:.2f}/10")
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
                context_parts.append(f"{module_name}: {score:.2f}/10")
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
                "system": """אתה עוזר AI מומחה למערכת המסחר ELITE v20.

ELITE v20 היא מערכת ביולוגית-קוונטיטטיבית היברידית עם 6 שכבות:
- Layer 1: Data Sources (Binance, CryptoQuant, Fear & Greed)
- Layer 2: Feature Engineering (OnChain Diffusion, Protein Folding, Violence/Chaos, NLP)
- Layer 3: ML Models (Regime Detection, Phase Transitions)
- Layer 4: Decision Engine (Manifold DNA, Bayesian Logic)
- Layer 5: Execution (DCA 60% + Tactical 40%)
- Layer 6: Infrastructure (Telegram, Risk Management)

אסטרטגיות:
1. **DCA Strategy (60%)**: קנייה בדם ברחובות, מטרה 2030 ($600k-$1M BTC)
2. **Tactical Strategy (40%)**: מסחר אקטיבי עם T1/T2 protocol

מטרתך:
- להסביר את המערכת בצורה ברורה ומדויקת
- לנתח את ה-Manifold DNA scores
- להסביר למה יש או אין סיגנלים
- לתת insights על הסיכונים והאסטרטגיות
- לעזור בקבלת החלטות מושכלות

עקרונות ברזל:
1. Never Risk >5% per trade
2. Ignore the Noise - רק סיגנלים חזקים
3. Long Term Vision - 2030 target

תענה תמיד בעברית בצורה ברורה ומקצועית.
אם אין לך מספיק מידע - תגיד זאת בכנות.
"""
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
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
