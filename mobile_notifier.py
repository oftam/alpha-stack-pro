"""
Elite v20 - Mobile Fortress
============================
Push notifications via Telegram Bot
Works on iPhone, Android, any device - FREE!

Setup:
1. Create bot: message @BotFather on Telegram → /newbot
2. Get your chat_id: message @userinfobot
3. Add to .streamlit/secrets.toml:
   TELEGRAM_BOT_TOKEN = "your_token"
   TELEGRAM_CHAT_ID = "your_chat_id"

Author: ELITE v20 System
"""

import requests
import json
from datetime import datetime
from typing import Optional, Dict, Any

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False


class EliteMobileNotifier:
    """
    Sends push notifications to Telegram for ELITE v20 signals
    """
    
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """Initialize Telegram notifier."""
        
        # Try to get from Streamlit secrets first
        if STREAMLIT_AVAILABLE:
            try:
                self.bot_token = bot_token or st.secrets.get("TELEGRAM_BOT_TOKEN", "")
                self.chat_id = chat_id or st.secrets.get("TELEGRAM_CHAT_ID", "")
            except Exception:
                self.bot_token = bot_token or ""
                self.chat_id = chat_id or ""
        else:
            import os
            self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
            self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.available = bool(self.bot_token and self.chat_id)
        
        if self.available:
            print("✅ Telegram notifier ready")
        else:
            print("⚠️ Telegram not configured (add TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID)")
    
    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send a message to Telegram."""
        if not self.available:
            return False
        
        try:
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": parse_mode
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️ Telegram error: {e}")
            return False
    
    def alert_victory_vector(self, score: float, kelly_fraction: float, action: str):
        """
        🚨 Victory Vector Alert
        Sent when Victory Vector activates
        """
        emoji = "🟢" if action == "BUY" else "🔴" if action == "SELL" else "🟡"
        
        msg = f"""
🚨 <b>ELITE v20 - VICTORY VECTOR ALERT</b>

{emoji} <b>ACTION: {action}</b>
📊 Score: <b>{score:.1f}/100</b>
💰 Kelly Fraction: <b>{kelly_fraction:.1%}</b>
🕐 Time: {datetime.now().strftime('%H:%M:%S')}

<i>Check dashboard for full analysis</i>
"""
        return self.send_message(msg.strip())
    
    def alert_divergence(self, divergence_score: float, direction: str, 
                          onchain_score: float, etf_flow: float):
        """
        🔍 Divergence Alert
        Sent when on-chain vs macro divergence detected
        """
        emoji = "🟢" if direction == "BULLISH" else "🔴"
        
        msg = f"""
🔍 <b>ELITE v20 - DIVERGENCE ALERT</b>

{emoji} <b>{direction} DIVERGENCE</b>
📈 Divergence Score: <b>+{divergence_score:.1f} pts</b>
🐋 On-Chain: <b>{onchain_score:.0f}/100</b>
💸 ETF Flow: <b>${etf_flow:+.0f}M</b>
🕐 Time: {datetime.now().strftime('%H:%M:%S')}

⚡ <b>SNIPER ENTRY OPPORTUNITY</b>
<i>Whales accumulating while retail sells</i>
"""
        return self.send_message(msg.strip())
    
    def alert_sniper_mode(self, entry_price: float, size_pct: float, 
                           manifold_score: float, regime: str):
        """
        🎯 Sniper Mode Alert
        Sent when SNIPER BUY/SELL signal fires
        """
        msg = f"""
🎯 <b>ELITE v20 - SNIPER MODE ACTIVATED</b>

💎 <b>SNIPER BUY SIGNAL</b>
💵 Entry Price: <b>${entry_price:,.0f}</b>
📊 Position Size: <b>{size_pct:.0f}%</b>
🧬 Manifold Score: <b>{manifold_score:.0f}/100</b>
🌊 Regime: <b>{regime}</b>
🕐 Time: {datetime.now().strftime('%H:%M:%S')}

<i>Execute within 15 minutes for optimal entry</i>
"""
        return self.send_message(msg.strip())
    
    def check_sniper_trigger(self, elite_results: dict, fear_greed: int) -> bool:
        """
        Check if all 4 SNIPER EXECUTION conditions are met.
        
        Returns True if trigger fires (sends Telegram alert automatically).
        
        Conditions:
          1. Fear & Greed <= 15  (macro discount window open)
          2. OnChain == STRONG_ACCUMULATION  (whales still backing)
          3. Book Imbalance >= -0.20  (sell wall absorbed)
          4. TRUECVD >= 0.0  (buyers attacking aggressively)
        """
        try:
            onchain = elite_results.get('onchain', {})
            protein = elite_results.get('protein', {})
            
            onchain_signal = onchain.get('signal', '')
            book_imbalance = float(protein.get('book_imbalance', -999))
            truecvd = float(protein.get('cvd_delta', protein.get('truecvd', -999)))
            
            cond1 = fear_greed <= 15
            cond2 = onchain_signal == 'STRONG_ACCUMULATION'
            cond3 = book_imbalance >= -0.20
            cond4 = truecvd >= 0.0
            
            if cond1 and cond2 and cond3 and cond4:
                self.alert_sniper_execution_trigger(
                    fear_greed=fear_greed,
                    onchain_signal=onchain_signal,
                    book_imbalance=book_imbalance,
                    truecvd=truecvd,
                    elite_score=float(elite_results.get('elite_score', 0))
                )
                return True
            return False
        except Exception as e:
            print(f"⚠️ Sniper trigger check error: {e}")
            return False

    def alert_sniper_execution_trigger(self, fear_greed: int, onchain_signal: str,
                                        book_imbalance: float, truecvd: float,
                                        elite_score: float) -> bool:
        """
        🔥 URGENT: SNIPER EXECUTION TRIGGER
        Fires when microstructure reversal confirms Fear extreme.
        All 4 conditions must be met simultaneously.
        """
        msg = f"""🔥 <b>URGENT: SNIPER EXECUTION TRIGGER</b> 🔥

✅ ALL 4 CONDITIONS MET — EXECUTE NOW

1️⃣ Fear &amp; Greed: <b>{fear_greed}/100</b> (Extreme Fear ✅)
2️⃣ OnChain: <b>{onchain_signal}</b> (Whales buying ✅)
3️⃣ Book Imbalance: <b>{book_imbalance:+.3f}</b> (Sell wall gone ✅)
4️⃣ TRUECVD: <b>{truecvd:+.2f}</b> (Buyers attacking ✅)

📊 Elite Score: <b>{elite_score:.0f}/100</b>
🕐 Time: {datetime.now().strftime('%H:%M:%S')}

⚡ <b>HOLD → EXECUTE. This is the signal.</b>
<i>Execute within 15 minutes for optimal entry.</i>"""
        return self.send_message(msg.strip())

    def daily_summary(self, data: Dict[str, Any]) -> bool:
        """
        📊 ELITE v20 - Daily Briefing (Smart Format)
        Sends full analysis: Action, DNA, Divergence, Sentiment, Strategy
        """
        action = data.get('action', 'HOLD')
        action_emoji = "🟢" if action in ['BUY', 'STRONG_BUY', 'SNIPER_BUY'] else "🔴" if 'SELL' in action else "🟡"
        confidence = data.get('confidence', 0)
        
        msg = f"""🚨 *ELITE v20 - DAILY BRIEFING* 🚨
{datetime.now().strftime('%A, %d/%m/%Y')}

📊 *Status:* {action_emoji} *{action}* ({confidence}%)

₿ *BTC:* ${data.get('price', 0):,.0f}
🧬 *DNA:* {data.get('dna', 0):.0f}/100
🟢 *Divergence:* *{data.get('div_label', 'N/A')}* ({data.get('div_score', 0):.1f})
😱 *Sentiment:* {data.get('sentiment', 50)}/100

💡 *Strategy:* {data.get('strategy_hint', 'Check dashboard')}
🕐 {datetime.now().strftime('%H:%M')}"""
        return self.send_message(msg.strip(), parse_mode="Markdown")
    
    def send_smart_alert(self, data: Dict[str, Any]) -> bool:
        """
        🚨 ELITE v20 - Smart Sentinel Alert
        Sends a rich Markdown formatted alert with full system analysis
        """
        # Format emoji for action
        action_emoji = "🟢" if data.get('action') in ['BUY', 'STRONG_BUY', 'SNIPER_BUY'] else "🔴" if 'SELL' in data.get('action', '') else "🟡"
        
        msg = f"""
🚨 *ELITE v20 - SIGNAL ALERT* 🚨
Status: {action_emoji} *{data.get('action', 'N/A')}*
Confidence: {data.get('confidence', 0)}% ({data.get('conf_label', 'N/A')})
-------------------------
₿ BTC Price: ${data.get('price', 0):,}
🧬 Manifold DNA: {data.get('dna', 0)}/100
🟢 Divergence: *{data.get('div_label', 'N/A')}* ({data.get('div_score', 0)})
😱 Sentiment: {data.get('sentiment', 0)}/100 ({data.get('sent_label', 'N/A')})
-------------------------
💡 *Strategy:* {data.get('strategy_hint', 'Check dashboard')}
"""
        return self.send_message(msg.strip(), parse_mode="Markdown")

    def test_connection(self) -> bool:
        """Test Telegram connection."""
        msg = """
✅ <b>ELITE v20 Mobile Fortress</b>

🎉 Connection successful!
📱 You will receive alerts for:
  • Victory Vector activation
  • Divergence detection  
  • Sniper Mode signals
  • Daily briefings

<i>System ready! 🚀</i>
"""
        return self.send_message(msg.strip())


# ============================================================
# Standalone test
# ============================================================
if __name__ == "__main__":
    import os
    
    # Load from .env if available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    
    if not token or not chat_id:
        print("""
❌ Missing Telegram credentials!

Setup steps:
1. Open Telegram → search @BotFather
2. Send: /newbot
3. Follow instructions → copy the token
4. Search @userinfobot → send any message → copy your ID
5. Add to .env:
   TELEGRAM_BOT_TOKEN=your_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
6. Run this script again
""")
    else:
        notifier = EliteMobileNotifier(token, chat_id)
        print("🧪 Testing connection...")
        
        if notifier.test_connection():
            print("✅ Telegram connected! Check your phone!")
            
            # Test a signal
            notifier.alert_victory_vector(
                score=84.0,
                kelly_fraction=0.25,
                action="BUY"
            )
            print("✅ Test signal sent!")
        else:
            print("❌ Connection failed - check token and chat_id")
