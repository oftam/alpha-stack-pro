"""
Elite v20 - Telegram Alert System
Real-time notifications for DCA and Tactical signals

User Configuration:
- Bot Token: 8308113066:AAHRwqy3nix2t6GRq-UGOJYJ9WM722FZ0_o
- Chat ID: 397917344
"""

import os
import requests
from datetime import datetime
from typing import Dict, Optional
import json


class TelegramAlertSystem:
    """
    Send real-time alerts via Telegram for both strategies.
    
    Alert Types:
    - DCA: Blood in Streets opportunities (long-term HOLD)
    - Tactical: Entry/Exit signals (T1/T2 protocol)
    - Risk: Stop loss warnings, gate status changes
    - System: Confidence changes, regime shifts
    """
    
    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None
    ):
        """
        Initialize Telegram alert system.
        
        Args:
            bot_token: Telegram bot token (from env if None)
            chat_id: Telegram chat ID (from env if None)
        """
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN', '8308113066:AAHRwqy3nix2t6GRq-UGOJYJ9WM722FZ0_o')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID', '397917344')
        
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.enabled = True
        
        # Alert history (prevent spam)
        self.last_alerts = {}
        self.cooldown_seconds = 300  # 5 minutes between similar alerts
    
    def _send_message(self, text: str, parse_mode: str = 'Markdown') -> bool:
        """
        Send message via Telegram API.
        
        Args:
            text: Message text
            parse_mode: Parse mode ('Markdown' or 'HTML')
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            print(f"[Telegram] Disabled: {text}")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                print(f"[Telegram] ✅ Sent: {text[:50]}...")
                return True
            else:
                print(f"[Telegram] ❌ Error {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print(f"[Telegram] ❌ Exception: {e}")
            return False
    
    def _should_send_alert(self, alert_type: str) -> bool:
        """
        Check if alert should be sent (cooldown logic).
        
        Args:
            alert_type: Type of alert (e.g., 'DCA_SIGNAL', 'T1_HIT')
            
        Returns:
            True if alert should be sent
        """
        now = datetime.now()
        
        if alert_type in self.last_alerts:
            last_time = self.last_alerts[alert_type]
            elapsed = (now - last_time).total_seconds()
            
            if elapsed < self.cooldown_seconds:
                return False
        
        self.last_alerts[alert_type] = now
        return True
    
    def send_dca_signal(
        self,
        btc_price: float,
        manifold_score: float,
        regime: str,
        diffusion_score: float,
        fear_greed: int,
        recommended_usd: float,
        target_2030: str = "$600k-$1M"
    ) -> bool:
        """
        Send DCA opportunity alert (Blood in Streets).
        
        Args:
            btc_price: Current BTC price
            manifold_score: Manifold DNA score
            regime: Current regime
            diffusion_score: On-chain diffusion score
            fear_greed: Fear & Greed Index (0-100)
            recommended_usd: Recommended DCA amount
            target_2030: 2030 price target
            
        Returns:
            True if sent successfully
        """
        if not self._should_send_alert('DCA_SIGNAL'):
            return False
        
        text = f"""🩸 *DCA OPPORTUNITY - Blood in Streets*

📊 *Market Status:*
BTC: ${btc_price:,.0f}
Manifold DNA: *{manifold_score:.1f}* (Top 2%)
Regime: `{regime}`

🐋 *Smart Money:*
Whales Accumulating: {diffusion_score:.0f}/100
Fear Index: *Extreme* ({fear_greed}/100)

💎 *DCA Action:*
BUY: ${recommended_usd:,.0f} (60% allocation)
⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}

🎯 *Strategy: STRATEGIC - HOLD until 2030*
Target: {target_2030}

⚠️ This is long-term accumulation.
Do NOT sell on short-term volatility!
"""
        
        return self._send_message(text)
    
    def send_tactical_entry(
        self,
        btc_price: float,
        manifold_score: float,
        confidence: float,
        t1_target: float,
        t2_target: float,
        stop_loss: float,
        position_usd: float,
        position_btc: float,
        risk_usd: float,
        risk_pct: float,
        win_prob: float,
        rr_ratio: float
    ) -> bool:
        """
        Send Tactical entry signal (T1/T2 protocol).
        
        Args:
            btc_price: Current BTC price
            manifold_score: Manifold DNA score
            confidence: System confidence
            t1_target: T1 target price
            t2_target: T2 target price
            stop_loss: Stop loss price
            position_usd: Position size in USD
            position_btc: Position size in BTC
            risk_usd: Risk amount in USD
            risk_pct: Risk percentage
            win_prob: Win probability
            rr_ratio: Risk/Reward ratio
            
        Returns:
            True if sent successfully
        """
        if not self._should_send_alert('TACTICAL_ENTRY'):
            return False
        
        text = f"""⚡ *TACTICAL ENTRY - Override Protocol*

📊 *Signal:*
BTC: ${btc_price:,.0f} → Entry *NOW*
Score: {manifold_score:.1f} | Confidence: *{confidence:.1%}*

🎯 *Targets:*
T1: ${t1_target:,.0f} (+{((t1_target/btc_price-1)*100):.1f}%) → Exit 50%
T2: ${t2_target:,.0f} (+{((t2_target/btc_price-1)*100):.1f}%) → Trail 3%
Stop: ${stop_loss:,.0f} (-{((1-stop_loss/btc_price)*100):.1f}%)

💰 *Position:*
Size: ${position_usd:,.0f} (40% allocation)
   BTC: {position_btc:.4f}
   Risk: ${risk_usd:.0f} ({risk_pct:.2f}%)

📈 *Edge:*
Win Probability: {win_prob:.1%}
R:R Ratio: {rr_ratio:.1f}:1

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
"""
        
        return self._send_message(text)
    
    def send_t1_hit(
        self,
        btc_price: float,
        entry_price: float,
        profit_usd: float,
        profit_pct: float
    ) -> bool:
        """
        Send T1 target hit alert.
        
        Args:
            btc_price: Current BTC price
            entry_price: Entry price
            profit_usd: Profit in USD
            profit_pct: Profit percentage
            
        Returns:
            True if sent successfully
        """
        if not self._should_send_alert('T1_HIT'):
            return False
        
        text = f"""💰 *T1 TARGET HIT (+5%)*

📊 *Trade Update:*
Entry: ${entry_price:,.0f}
Current: ${btc_price:,.0f}
Profit: *${profit_usd:,.0f}* (+{profit_pct:.1f}%)

✅ *Action: EXIT 50%*
✅ *MOVE STOP TO BREAKEVEN*

Remaining 50% riding to T2
Risk: *ELIMINATED* ✅

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
"""
        
        return self._send_message(text)
    
    def send_t2_hit(
        self,
        btc_price: float,
        entry_price: float,
        profit_usd: float,
        profit_pct: float,
        trail_stop: float
    ) -> bool:
        """
        Send T2 target hit alert.
        
        Args:
            btc_price: Current BTC price
            entry_price: Entry price
            profit_usd: Profit in USD
            profit_pct: Profit percentage
            trail_stop: Trailing stop price
            
        Returns:
            True if sent successfully
        """
        if not self._should_send_alert('T2_HIT'):
            return False
        
        text = f"""🚀 *T2 TARGET HIT (+12%)*

📊 *Trade Update:*
Entry: ${entry_price:,.0f}
Current: ${btc_price:,.0f}
Profit: *${profit_usd:,.0f}* (+{profit_pct:.1f}%)

✅ *Action: TRAIL STOP 3%*
Trail: ${trail_stop:,.0f}

Let momentum run with safety net!

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
"""
        
        return self._send_message(text)
    
    def send_stop_loss_warning(
        self,
        btc_price: float,
        stop_loss: float,
        distance_pct: float,
        strategy: str = 'TACTICAL'
    ) -> bool:
        """
        Send stop loss warning.
        
        Args:
            btc_price: Current BTC price
            stop_loss: Stop loss price
            distance_pct: Distance to stop loss (%)
            strategy: Strategy type
            
        Returns:
            True if sent successfully
        """
        if not self._should_send_alert('STOP_WARNING'):
            return False
        
        text = f"""⛔ *STOP LOSS WARNING*

📊 *{strategy} Position:*
Current: ${btc_price:,.0f}
Stop: ${stop_loss:,.0f}
Distance: *{distance_pct:.1f}%*

⚠️ Approaching stop loss level!
Monitor closely for exit.

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
"""
        
        return self._send_message(text)
    
    def send_stop_hit(
        self,
        btc_price: float,
        entry_price: float,
        loss_usd: float,
        loss_pct: float,
        strategy: str = 'TACTICAL'
    ) -> bool:
        """
        Send stop loss hit notification.
        
        Args:
            btc_price: Current BTC price
            entry_price: Entry price
            loss_usd: Loss in USD
            loss_pct: Loss percentage
            strategy: Strategy type
            
        Returns:
            True if sent successfully
        """
        text = f"""⛔ *STOP LOSS HIT*

📊 *{strategy} Trade Closed:*
Entry: ${entry_price:,.0f}
Exit: ${btc_price:,.0f}
Loss: *-${abs(loss_usd):,.0f}* ({loss_pct:.1f}%)

✅ Risk managed properly
Moving to next opportunity

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
"""
        
        return self._send_message(text)
    
    def send_regime_change(
        self,
        old_regime: str,
        new_regime: str,
        btc_price: float,
        manifold_score: float
    ) -> bool:
        """
        Send regime change alert.
        
        Args:
            old_regime: Previous regime
            new_regime: New regime
            btc_price: Current BTC price
            manifold_score: Manifold score
            
        Returns:
            True if sent successfully
        """
        if not self._should_send_alert('REGIME_CHANGE'):
            return False
        
        emoji_map = {
            'BLOOD_IN_STREETS': '🩸',
            'CHAOS': '🌪️',
            'VOLATILE': '⚠️',
            'CALM': '🟢',
            'NORMAL': '📊'
        }
        
        text = f"""🔄 *REGIME CHANGE DETECTED*

{emoji_map.get(old_regime, '❓')} `{old_regime}`
    ↓
{emoji_map.get(new_regime, '❓')} `{new_regime}`

BTC: ${btc_price:,.0f}
Score: {manifold_score:.1f}

Strategy adjusted automatically.

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
"""
        
        return self._send_message(text)
    
    def send_system_status(
        self,
        status: Dict
    ) -> bool:
        """
        Send system status update.
        
        Args:
            status: System status dictionary
            
        Returns:
            True if sent successfully
        """
        portfolio = status.get('portfolio', {})
        capital = portfolio.get('capital', {})
        dca = portfolio.get('dca', {})
        tactical = portfolio.get('tactical', {})
        
        text = f"""📊 *ELITE v20 STATUS*

💰 *Portfolio:*
Total Value: ${capital.get('total_value', 0):,.0f}
P&L: ${capital.get('pnl_total', 0):,.0f} ({capital.get('return_pct', 0):.1f}%)

📈 *DCA (60%):*
BTC Held: {dca.get('btc_held', 0):.4f}
Avg Entry: ${dca.get('avg_entry', 0):,.0f}
Unrealized: ${dca.get('unrealized_pnl', 0):,.0f}

⚡ *Tactical (40%):*
BTC Held: {tactical.get('btc_held', 0):.4f}
Avg Entry: ${tactical.get('avg_entry', 0):,.0f}
Unrealized: ${tactical.get('unrealized_pnl', 0):,.0f}
Realized: ${tactical.get('realized_pnl', 0):,.0f}

🎯 *System:*
Confidence: {status.get('confidence', 0):.1%}
Regime: `{status.get('regime', 'UNKNOWN')}`

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
"""
        
        return self._send_message(text)
    
    def send_test_alert(self) -> bool:
        """
        Send test alert to verify connection.
        
        Returns:
            True if sent successfully
        """
        text = f"""✅ *ELITE v20 CONNECTED*

Telegram alerts are LIVE!

Bot: Active
Chat: {self.chat_id}

Ready to receive:
- 🩸 DCA signals
- ⚡ Tactical entries
- 💰 T1/T2 exits
- ⛔ Stop warnings
- 🔄 Regime changes

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
"""
        
        return self._send_message(text)
    
    def disable(self) -> None:
        """Disable all alerts."""
        self.enabled = False
        print("[Telegram] Alerts disabled")
    
    def enable(self) -> None:
        """Enable all alerts."""
        self.enabled = True
        print("[Telegram] Alerts enabled")
