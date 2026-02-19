"""
ELITE v20 - Google Gemini Chat Module
======================================
מודול Gemini מותאם ל-ELITE v20 Architecture
(Migrated from Claude API to save costs)

התאמות:
- מבין את 6 השכבות של ELITE v20
- מכיר DCA vs Tactical strategies
- מנתח Manifold DNA scores
- מסביר Risk management
- מתאים להודעות Telegram
"""

import streamlit as st
import json
from datetime import datetime
from typing import Dict, Any, Optional, List

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ google-generativeai not installed. Run: pip install google-generativeai")

print("🧬 Gemini Module v3.2 loaded (token limit fix)")

def _safe_extract_text(response) -> str:
    """
    Safely extract text from a Gemini response.
    Gemini 2.5 Pro can return complex multi-part responses
    (images, code, function calls) where response.text crashes.
    """
    try:
        # Debug: Show response structure
        print(f"🔍 DEBUG Response type: {type(response).__name__}")
        
        # Check candidates
        candidates = getattr(response, 'candidates', None)
        if candidates:
            print(f"🔍 DEBUG Candidates count: {len(candidates)}")
            if len(candidates) > 0:
                candidate = candidates[0]
                finish_reason = getattr(candidate, 'finish_reason', 'UNKNOWN')
                print(f"🔍 DEBUG Finish reason: {finish_reason}")
                
                # Check safety ratings
                safety = getattr(candidate, 'safety_ratings', None)
                if safety:
                    print(f"🔍 DEBUG Safety ratings: {safety}")
                
                content = getattr(candidate, 'content', None)
                if content:
                    parts = getattr(content, 'parts', None)
                    if parts and len(parts) > 0:
                        print(f"🔍 DEBUG Parts count: {len(parts)}")
                        text_parts = []
                        for i, part in enumerate(parts):
                            print(f"🔍 DEBUG Part {i} type: {type(part).__name__}, has text: {hasattr(part, 'text')}")
                            if hasattr(part, 'text'):
                                t = part.text
                                if t:
                                    text_parts.append(t)
                                    print(f"🔍 DEBUG Part {i} text length: {len(t)}")
                                else:
                                    print(f"🔍 DEBUG Part {i} text is empty/None")
                        if text_parts:
                            return '\n'.join(text_parts)
                        print("⚠️ DEBUG: All parts had empty text")
                    else:
                        print(f"⚠️ DEBUG: No parts in content (parts={parts})")
                else:
                    print(f"⚠️ DEBUG: No content in candidate")
        else:
            print(f"⚠️ DEBUG: No candidates in response")
        
        # Method 2: Try response.text as last resort
        try:
            t = response.text
            if t:
                print(f"🔍 DEBUG: Fell through to response.text, length={len(t)}")
                return t
        except (ValueError, AttributeError) as e:
            print(f"⚠️ DEBUG: response.text failed: {e}")
        
        # Method 3: Check prompt_feedback for blocks
        feedback = getattr(response, 'prompt_feedback', None)
        if feedback:
            print(f"🔍 DEBUG Prompt feedback: {feedback}")
            block_reason = getattr(feedback, 'block_reason', None)
            if block_reason and str(block_reason) != '0':
                return f"[BLOCKED by safety filter: {block_reason}]"
        
        return ""
    except Exception as e:
        print(f"⚠️ Text extraction error: {e}")
        import traceback
        traceback.print_exc()
        return ""


class EliteGeminiChat:
    """
    Google Gemini AI Chat integration for ELITE v20 Dashboard
    Optimized for 6-layer biological/quant system
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Gemini chat for ELITE v20."""
        self.api_key = api_key or st.secrets.get("GOOGLE_API_KEY", "")
        
        if not GEMINI_AVAILABLE:
            print("❌ Gemini unavailable - google-generativeai not installed")
            self.model = None
            return
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            # Use Gemini 2.5 Pro (Gemini V20 project - Pro access)
            try:
                self.model = genai.GenerativeModel('models/gemini-2.5-pro')
                print("✅ Gemini 2.5 Pro loaded")
            except Exception:
                # Fallback to flash if pro unavailable
                self.model = genai.GenerativeModel('models/gemini-2.0-flash')
                print("⚠️ Fallback to Gemini 2.0 Flash")
        else:
            self.model = None
        
        # Initialize Google Sheets connector (optional)
        try:
            from google_finance_connector import GoogleFinanceConnector
            self.sheets_connector = GoogleFinanceConnector()
            if self.sheets_connector.sheet:
                print("✅ Google Sheets Macro connected")
        except Exception as e:
            print(f"⚠️ Sheets connector unavailable: {e}")
            self.sheets_connector = None
        
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
                if tact_sig.get('confidence') is not None:
                    conf_val = tact_sig['confidence']
                    # If stored as decimal (0.0-1.0), convert to percentage
                    if conf_val <= 1.0:
                        conf_val = conf_val * 100
                    context_parts.append(f"  Confidence: {conf_val:.0f}%")
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
    
    def ask_gemini(
        self, 
        question: str, 
        dashboard_data: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[list] = None
    ) -> str:
        """
        שואל את Gemini עם context מלא מ-ELITE v20
        """
        if not self.api_key:
            return "❌ API Key חסר! הוסף GOOGLE_API_KEY ב-.streamlit/secrets.toml"
        
        if not self.model:
            return "❌ Gemini לא זמין - התקן: pip install google-generativeai"
        
        try:
            # Build system prompt — STRICT GROUNDING to real dashboard data only
            system_instruction = """אתה עוזר AI מומחה למערכת המסחר ELITE v20.

🚨 כלל ברזל 1: דיוק מוחלט — דווח רק על נתונים מה-context
- אל תמציא מספרים, הסתברויות, ציונים או מצבים שאינם בנתונים שקיבלת.
- אם נתון חסר — כתוב "לא זמין" ולא השערה.
- אם הנתון הוא 94 — כתוב 94, לא 100. אם Confidence הוא 100% ל-HOLD — כתוב את זה.

🚨 כלל ברזל 2: Final Action = האמת היחידה
- ה-Final Action מהדשבורד הוא הסיגנל. לא התיאוריה, לא הנוסחה.
- אם הדשבורד אומר HOLD — אל תשדר BUY בשום צורה, ישירה או עקיפה.

🚨 כלל ברזל 3: אין הסתברויות מהאוויר
- אין "91.7% הסתברות היסטורית" — זה לא אומת בבדיקות.
- בדיקות שבוצעו הראו: Fear<15 לבד = p-value=0.87, אין edge סטטיסטי.
- אם תשאלו על הסתברויות — ציין שאינן מאומתות.

הסולמות הנכונים:
- OnChain Diffusion: 0-100
- Manifold DNA: 0-100
- Chaos/Violence: נמוך = שוק רגוע (טוב)
- system_confidence: ערך עשרוני 0.0–1.0 — הצג כאחוזים! (1.0 = 100%, לא 1%)
  דוגמה: confidence=1.0 → "ביטחון: 100%" לא "ביטחון: 1%"

מה כן לעשות:
1. ענה בעברית ברורה
2. הצג נתוני dashboard כפי שהם
3. הסבר את המשמעות — לא תחזיות
4. אם אין context מהדשבורד — אמור זאת

🚨 כלל ברזל 4: שפה מקצועית בלבד — ללא כינויים פנימיים
- אין "צלף" / "SNIPER MODE" — השתמש ב: "אות כניסה בעוצמה גבוהה"
- אין "דודו" / "DUDU" — השתמש ב: "מדד ההקרנה" או "Projection Score"
- אין "Manifold DNA" — השתמש ב: "מדד הבריאות המבנית של השוק"
- אין "Protein Folding" — השתמש ב: "ניתוח מיקרוסטרוקטורה"
- אין "Bayesian Collapse" — השתמש ב: "אישור סטטיסטי לכניסה"
- אין "Blood in Streets" — השתמש ב: "מצב פחד קיצוני בשוק"
- שפת ה-output: מקצועית, מדויקת, מתאימה למשקיעים"""


            # Prepare user message with context
            if dashboard_data:
                context = self._format_elite_context(dashboard_data)
                full_message = f"{system_instruction}\n\n{context}\n\n---\n\nUser question: {question}"
            else:
                full_message = f"{system_instruction}\n\n---\n\nUser question: {question}"
            
            # Call Gemini API
            print(f"🤖 Sending request to Gemini... (Length: {len(full_message)})")
            
            try:
                response = self.model.generate_content(
                    full_message,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=8192,
                        temperature=0.7,
                    )
                )
            except Exception as e:
                print(f"❌ Gemini network error: {e}")
                return f"שגיאת תקשורת עם ג'מיני: {e}"
            
            # Safe text extraction (Gemini 2.5 Pro compatible)
            print("✅ Received response from Gemini")
            try:
                response.resolve()  # Ensure response is fully resolved
            except Exception as e:
                print(f"⚠️ response.resolve() failed: {e}")
            
            final_text = _safe_extract_text(response)
            
            if not final_text:
                print("⚠️ Empty response text")
                return "ג'מיני החזיר תשובה ריקה. נסה לשאול שוב."
            
            if final_text.startswith("[BLOCKED"):
                print(f"⚠️ {final_text}")
                return f"התשובה נחסמה על ידי פילטר בטיחות של גוגל.\n{final_text}"
                
            print("✅ Response processed successfully")
            return final_text
            
        except Exception as e:
            print(f"❌ General error in ask_gemini: {e}")
            return f"❌ שגיאה כללית במערכת הצ'אט: {str(e)}"
    
    def fetch_macro_pulse(self) -> Dict[str, Any]:
        """
        מושך נתוני מאקרו בזמן אמת עם Gemini Pro + Google Search
        
        Uses Gemini 2.5 Pro with Google Search grounding for:
        - BTC ETF flows (IBIT, FBTC)
        - VIX (Fear index)
        - S&P 500 change
        - Market sentiment
        
        Returns: Dict עם כל נתוני המאקרו
        """
        if not self.api_key or not self.model:
            return {
                'status': 'unavailable',
                'btc_etf_flow_24h': 0,
                'sp500_change': 0,
                'vix': 0,
                'sentiment': 'NEUTRAL',
                'note': 'Gemini not configured'
            }
        
        try:
            prompt = """You are a financial data assistant. Search for the LATEST real-time market data and respond ONLY with these exact lines, no extra text:

ETF_FLOW: <net BTC ETF flow today in millions USD, negative=outflow, e.g. -410 or +280>
SP500: <S&P 500 percentage change today, e.g. -0.8 or +1.2>
VIX: <current VIX value, e.g. 18.5>
SENTIMENT: <exactly one of: Bullish, Bearish, Neutral>
RATE_CUT: <Fed rate cut probability percentage, e.g. 65>

Search for: Bitcoin ETF flows today IBIT FBTC, VIX index current, S&P 500 today change"""

            # Use Google Search grounding for real-time data
            try:
                from google.generativeai.types import Tool
                search_tool = Tool(google_search_retrieval={})
                response = self.model.generate_content(
                    prompt,
                    tools=[search_tool],
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=2048,
                        temperature=0.1,
                    )
                )
            except Exception:
                # Fallback: call without search grounding
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=2048,
                        temperature=0.1,
                    )
                )
            
            # Safe text extraction (Gemini 2.5 Pro compatible)
            response.resolve()  # Ensure response is fully resolved
            text = _safe_extract_text(response).strip()
            print(f"📡 Macro raw response: {text[:200]}")
            
            # Parse structured response
            result = {
                'status': 'live',
                'btc_etf_flow_24h': 0.0,
                'sp500_change': 0.0,
                'vix': 20.0,
                'sentiment': 'Neutral',
                'fed_rate_cut_prob': 60,
                'timestamp': datetime.now().isoformat(),
                'source': 'Gemini Pro + Google Search'
            }
            
            for line in text.split('\n'):
                line = line.strip()
                try:
                    if line.startswith('ETF_FLOW:'):
                        val = line.split(':', 1)[1].strip().replace('+', '').replace('M', '').replace('$', '')
                        result['btc_etf_flow_24h'] = float(val)
                    elif line.startswith('SP500:'):
                        val = line.split(':', 1)[1].strip().replace('+', '').replace('%', '')
                        result['sp500_change'] = float(val)
                    elif line.startswith('VIX:'):
                        val = line.split(':', 1)[1].strip()
                        result['vix'] = float(val)
                    elif line.startswith('SENTIMENT:'):
                        val = line.split(':', 1)[1].strip()
                        if val in ['Bullish', 'Bearish', 'Neutral']:
                            result['sentiment'] = val
                    elif line.startswith('RATE_CUT:'):
                        val = line.split(':', 1)[1].strip().replace('%', '')
                        result['fed_rate_cut_prob'] = int(float(val))
                except (ValueError, IndexError):
                    continue
            
            print(f"✅ Live macro: ETF={result['btc_etf_flow_24h']}M, VIX={result['vix']}, SP500={result['sp500_change']}%")
            return result
            
        except Exception as e:
            print(f"⚠️ Macro fetch error: {e}")
            return {
                'status': 'error',
                'btc_etf_flow_24h': 0,
                'sp500_change': 0,
                'vix': 20,
                'sentiment': 'Neutral',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }





# ============================================================================
# STREAMLIT SIDEBAR RENDERING
# ============================================================================

def render_gemini_sidebar_elite(dashboard_data: Dict[str, Any]):
    """
    מציג Gemini chat sidebar ב-MEDALLION Dashboard
    """
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🤖 שאל את Gemini (Elite AI)")
        
        # Initialize chat
        if 'gemini_chat' not in st.session_state:
            st.session_state.gemini_chat = EliteGeminiChat()
        
        if 'gemini_history' not in st.session_state:
            st.session_state.gemini_history = []
        
        # Check availability
        if not st.session_state.gemini_chat.model:
            st.warning("⚠️ Gemini לא מוגדר")
            st.info("הוסף GOOGLE_API_KEY ל-.streamlit/secrets.toml")
            st.markdown("[Get API Key](https://aistudio.google.com/app/apikey)")
            return
        
        # Quick action buttons
        st.markdown("**שאלות מהירות:**")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📊 נתח מצב", key="gemini_analyze"):
                question = "נתח את המצב הנוכחי והמלץ על פעולה"
                with st.spinner("🤔 חושב..."):
                    answer = st.session_state.gemini_chat.ask_gemini(
                        question, 
                        dashboard_data
                    )
                    st.session_state.gemini_history.append({
                        'q': question,
                        'a': answer,
                        'time': datetime.now().isoformat()
                    })
        
        with col2:
            if st.button("⚠️ ניהול סיכונים", key="gemini_risk"):
                question = "מה הסיכונים הנוכחיים ואיך לנהל אותם?"
                with st.spinner("🤔 חושב..."):
                    answer = st.session_state.gemini_chat.ask_gemini(
                        question, 
                        dashboard_data
                    )
                    st.session_state.gemini_history.append({
                        'q': question,
                        'a': answer,
                        'time': datetime.now().isoformat()
                    })
        
        # Custom question
        user_question = st.text_area(
            "שאל שאלה מותאמת אישית:",
            height=100,
            key="gemini_custom_question"
        )
        
        if st.button("📤 שלח שאלה", key="gemini_submit"):
            if user_question:
                with st.spinner("🤔 Gemini חושב..."):
                    answer = st.session_state.gemini_chat.ask_gemini(
                        user_question, 
                        dashboard_data
                    )
                    st.session_state.gemini_history.append({
                        'q': user_question,
                        'a': answer,
                        'time': datetime.now().isoformat()
                    })
        
        # Display conversation history
        if st.session_state.gemini_history:
            st.markdown("---")
            st.markdown("### 💬 היסטוריית שיחה")
            
            for i, entry in enumerate(reversed(st.session_state.gemini_history[-5:])):
                with st.expander(f"שאלה {len(st.session_state.gemini_history)-i}: {entry['q'][:50]}..."):
                    st.markdown(f"**Q:** {entry['q']}")
                    st.markdown(f"**A:** {entry['a']}")
                    st.caption(f"🕐 {entry['time']}")
        
        # Clear history
        if st.button("🗑️ נקה היסטוריה", key="gemini_clear"):
            st.session_state.gemini_history = []
            st.rerun()


def prepare_elite_dashboard_data(
    market_data: Dict,
    portfolio_data: Dict,
    signals: Dict,
    modules: Dict,
    risk_metrics: Dict,
    performance: Dict
) -> Dict[str, Any]:
    """
    מכין dictionary מאורגן לGemini
    """
    return {
        'timestamp': datetime.now().isoformat(),
        'market': market_data,
        'portfolio': portfolio_data,
        'signals': signals,
        'modules': modules,
        'risk': risk_metrics,
        'performance': performance
    }


# Test mode
if __name__ == "__main__":
    print("🧪 Testing Gemini Chat Module...")
    
    # Test basic connection
    chat = EliteGeminiChat()
    
    if chat.model:
        print("✅ Gemini initialized")
        
        # Test question
        response = chat.ask_gemini("מה זה ELITE v20?")
        print(f"\n📨 Response:\n{response}")
    else:
        print("❌ Gemini not available")
        print("Set GOOGLE_API_KEY in environment or .streamlit/secrets.toml")
