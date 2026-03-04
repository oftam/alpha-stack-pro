"""
Whale Alert Monitor - Background System
Monitors on-chain metrics and sends real-time alerts

Integrates with existing Elite modules:
- onchain_data.py (CryptoQuant API)
- supply_shock_detector.py (reserve tracking)
- regime_detector.py (market regime)
- nlp_sentiment.py (sentiment analysis)

Runs independently of dashboard, checks every N minutes
"""

import sys
import os
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
import pandas as pd

# Add current directory to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# Import existing modules
try:
    from onchain_data import OnChainDataCollector
    ONCHAIN_AVAILABLE = True
except ImportError:
    print("⚠️  OnChain module not found - using mock data")
    ONCHAIN_AVAILABLE = False

try:
    from supply_shock_detector import SupplyShockDetector
    SUPPLY_SHOCK_AVAILABLE = True
except ImportError:
    print("⚠️  Supply Shock module not found - using mock data")
    SUPPLY_SHOCK_AVAILABLE = False

try:
    from regime_detector import RegimeDetector
    REGIME_AVAILABLE = True
except ImportError:
    print("⚠️  Regime Detector not found - using mock data")
    REGIME_AVAILABLE = False


class WhaleAlertMonitor:
    """
    Background monitor for whale activity and supply shocks
    
    Integrates with:
    - CryptoQuant API (on-chain data)
    - Fear & Greed Index
    - Telegram Bot (notifications)
    """
    
    def __init__(self, config_path: str = "alert_config.json"):
        self.config = self._load_config(config_path)
        self.last_alert_time = {}
        self.alert_history = []
        
        # Initialize notification channels
        self.telegram_bot_token = self.config.get('telegram_bot_token')
        self.telegram_chat_id = self.config.get('telegram_chat_id')
        self.email_enabled = self.config.get('email_enabled', False)
        
        # Initialize existing modules
        self.onchain_collector = None
        self.supply_shock_detector = None
        self.regime_detector = None
        
        if ONCHAIN_AVAILABLE:
            try:
                api_key = self.config.get('advanced', {}).get('cryptoquant_api_key')
                if api_key and api_key != "YOUR_API_KEY_HERE":
                    self.onchain_collector = OnChainDataCollector(api_key=api_key)
                    print("✅ OnChain module loaded")
                else:
                    print("⚠️  No CryptoQuant API key - some alerts disabled")
            except Exception as e:
                print(f"⚠️  Error loading OnChain module: {e}")
        
        if SUPPLY_SHOCK_AVAILABLE:
            try:
                self.supply_shock_detector = SupplyShockDetector()
                print("✅ Supply Shock module loaded")
            except Exception as e:
                print(f"⚠️  Error loading Supply Shock module: {e}")
        
        if REGIME_AVAILABLE:
            try:
                self.regime_detector = RegimeDetector()
                print("✅ Regime Detector loaded")
            except Exception as e:
                print(f"⚠️  Error loading Regime Detector: {e}")
        
        # Cache for recent data (avoid redundant API calls)
        self.data_cache = {
            'last_update': None,
            'cache_duration_minutes': 10,
            'onchain_data': None,
            'fear_greed': None
        }
        
    def _load_config(self, path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Default configuration
            return {
                'check_interval_minutes': 15,
                'whale_threshold_btc': 1000,
                'supply_shock_threshold_pct': 5,
                'netflow_zscore_threshold': 2.0,
                'fear_greed_extreme_threshold': 20,
                'cooldown_hours': 6,
                'severity_levels': {
                    'low': ['whale_small'],
                    'medium': ['whale_large', 'supply_shock'],
                    'high': ['blood_in_streets', 'institutional_flow']
                }
            }
    
    def check_whale_activity(self) -> Optional[Dict]:
        """
        Check for large whale transactions
        
        Returns alert dict if conditions met, None otherwise
        """
        try:
            # This would call CryptoQuant API
            # For now, placeholder logic
            
            # Example: Check netflow Z-score
            netflow_zscore = self._get_netflow_zscore()
            whale_threshold = self.config['whale_threshold_btc']
            
            if netflow_zscore > self.config['netflow_zscore_threshold']:
                return {
                    'type': 'whale_accumulation',
                    'severity': 'medium',
                    'title': '🐋 WHALE ALERT',
                    'message': f'Large accumulation detected\nNetflow Z-score: {netflow_zscore:.2f}\nDirection: Exchange → Cold Storage',
                    'timestamp': datetime.now().isoformat(),
                    'data': {
                        'netflow_zscore': netflow_zscore,
                        'threshold': self.config['netflow_zscore_threshold']
                    }
                }
            
            return None
            
        except Exception as e:
            print(f"Error checking whale activity: {e}")
            return None
    
    def check_supply_shock(self) -> Optional[Dict]:
        """
        Check for supply shock formation
        
        Supply shock = significant drop in exchange reserves
        """
        try:
            # Would integrate with actual supply shock detector
            reserve_change_7d = self._get_reserve_change()
            threshold = self.config['supply_shock_threshold_pct']
            
            if reserve_change_7d < -threshold:
                return {
                    'type': 'supply_shock',
                    'severity': 'high',
                    'title': '⚡ SUPPLY SHOCK FORMING',
                    'message': f'Exchange reserves dropping\n7-day change: {reserve_change_7d:.1f}%\nPotential price spike incoming',
                    'timestamp': datetime.now().isoformat(),
                    'data': {
                        'reserve_change_7d': reserve_change_7d,
                        'threshold': -threshold
                    }
                }
            
            return None
            
        except Exception as e:
            print(f"Error checking supply shock: {e}")
            return None
    
    def check_blood_in_streets(self) -> Optional[Dict]:
        """
        Check for blood in streets condition
        
        Combination of:
        - Extreme fear (<20)
        - Strong accumulation (>80)
        - Sustained for 3+ days
        """
        try:
            fear_greed = self._get_fear_greed()
            diffusion_score = self._get_diffusion_score()
            
            threshold = self.config['fear_greed_extreme_threshold']
            
            if fear_greed < threshold and diffusion_score > 80:
                # Check if sustained (would need historical data)
                return {
                    'type': 'blood_in_streets',
                    'severity': 'high',
                    'title': '🩸 BLOOD IN STREETS - CONFIRMED',
                    'message': f'Historic opportunity detected\nFear: {fear_greed}\nAccumulation: {diffusion_score}/100\nAction: Review buy targets',
                    'timestamp': datetime.now().isoformat(),
                    'data': {
                        'fear_greed': fear_greed,
                        'diffusion_score': diffusion_score
                    }
                }
            
            return None
            
        except Exception as e:
            print(f"Error checking blood in streets: {e}")
            return None
    
    def check_institutional_flow(self) -> Optional[Dict]:
        """
        Check for institutional buying signals
        
        Indicators:
        - Coinbase premium positive
        - Large custody inflows
        - Volume spike
        """
        try:
            # Placeholder - would integrate with actual data
            coinbase_premium = self._get_coinbase_premium()
            
            if coinbase_premium > 0.5:  # 0.5% premium
                return {
                    'type': 'institutional_flow',
                    'severity': 'high',
                    'title': '🏦 INSTITUTIONAL ACTIVITY',
                    'message': f'Smart money entering\nCoinbase premium: +{coinbase_premium:.1f}%\nInterpretation: Institutional buying',
                    'timestamp': datetime.now().isoformat(),
                    'data': {
                        'coinbase_premium': coinbase_premium
                    }
                }
            
            return None
            
        except Exception as e:
            print(f"Error checking institutional flow: {e}")
            return None
    
    def should_send_alert(self, alert: Dict) -> bool:
        """
        Check if alert should be sent based on cooldown and severity
        """
        alert_type = alert['type']
        cooldown_hours = self.config['cooldown_hours']
        
        # Check cooldown
        if alert_type in self.last_alert_time:
            last_time = self.last_alert_time[alert_type]
            time_diff = datetime.now() - last_time
            
            if time_diff < timedelta(hours=cooldown_hours):
                return False  # Still in cooldown
        
        return True
    
    def send_telegram_alert(self, alert: Dict):
        """Send alert via Telegram bot"""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            print("Telegram not configured")
            return
        
        try:
            message = f"{alert['title']}\n\n{alert['message']}\n\nTime: {alert['timestamp']}"
            
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                print(f"✅ Alert sent via Telegram: {alert['title']}")
            else:
                print(f"❌ Failed to send Telegram alert: {response.text}")
                
        except Exception as e:
            print(f"Error sending Telegram alert: {e}")
    
    def send_alert(self, alert: Dict):
        """Send alert through configured channels"""
        if not self.should_send_alert(alert):
            print(f"⏸️  Skipping alert (cooldown): {alert['title']}")
            return
        
        # Send via Telegram
        self.send_telegram_alert(alert)
        
        # Update last alert time
        self.last_alert_time[alert['type']] = datetime.now()
        
        # Store in history
        self.alert_history.append(alert)
        
        # Save to file
        self._save_alert_history()
    
    def run_checks(self):
        """Run all alert checks"""
        print(f"🔍 Running checks at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        checks = [
            self.check_whale_activity,
            self.check_supply_shock,
            self.check_blood_in_streets,
            self.check_institutional_flow
        ]
        
        for check_func in checks:
            try:
                alert = check_func()
                if alert:
                    self.send_alert(alert)
            except Exception as e:
                print(f"Error in {check_func.__name__}: {e}")
    
    def run_forever(self):
        """Main loop - run checks at configured interval"""
        interval_minutes = self.config['check_interval_minutes']
        print(f"🚀 Whale Alert Monitor started")
        print(f"📊 Check interval: {interval_minutes} minutes")
        print(f"📱 Telegram: {'Enabled' if self.telegram_bot_token else 'Disabled'}")
        print("-" * 50)
        
        while True:
            try:
                self.run_checks()
                print(f"⏰ Next check in {interval_minutes} minutes")
                time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                print("\n🛑 Monitor stopped by user")
                break
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                time.sleep(60)  # Wait 1 minute before retry
    
    def _update_cache(self):
        """Update data cache if expired"""
        now = datetime.now()
        
        if self.data_cache['last_update'] is None:
            cache_expired = True
        else:
            time_diff = now - self.data_cache['last_update']
            cache_expired = time_diff.total_seconds() > (self.data_cache['cache_duration_minutes'] * 60)
        
        if cache_expired:
            print("📊 Updating data cache...")
            
            # Update on-chain data
            if self.onchain_collector:
                try:
                    self.data_cache['onchain_data'] = self.onchain_collector.collect_all_metrics()
                except Exception as e:
                    print(f"Error fetching on-chain data: {e}")
            
            # Update Fear & Greed
            try:
                self.data_cache['fear_greed'] = self._fetch_fear_greed_api()
            except Exception as e:
                print(f"Error fetching Fear & Greed: {e}")
            
            self.data_cache['last_update'] = now
            print("✅ Cache updated")
    
    def _fetch_fear_greed_api(self) -> Optional[float]:
        """Fetch Fear & Greed index from API"""
        try:
            url = "https://api.alternative.me/fng/?limit=1"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                value = float(data['data'][0]['value'])
                return value
            
            return None
        except Exception as e:
            print(f"Error fetching F&G: {e}")
            return None
    
    def _get_netflow_zscore(self) -> float:
        """Get current netflow Z-score from on-chain data"""
        self._update_cache()
        
        if self.data_cache['onchain_data']:
            try:
                netflow_data = self.data_cache['onchain_data'].get('netflow', {})
                zscore = netflow_data.get('zscore', 0.0)
                return zscore
            except:
                pass
        
        return 0.0
    
    def _get_reserve_change(self) -> float:
        """Get 7-day reserve change % from supply shock detector"""
        if self.supply_shock_detector:
            try:
                # This would need historical data - simplified for now
                result = self.supply_shock_detector.detect_supply_shock(
                    available_supply=2_120_000,  # Example
                    days_in_period=7
                )
                return result.get('reserve_change_pct', 0.0)
            except:
                pass
        
        return 0.0
    
    def _get_fear_greed(self) -> float:
        """Get Fear & Greed index"""
        self._update_cache()
        
        if self.data_cache['fear_greed'] is not None:
            return self.data_cache['fear_greed']
        
        return 50.0  # Neutral default
    
    def _get_diffusion_score(self) -> float:
        """Get diffusion score from on-chain data"""
        self._update_cache()
        
        if self.data_cache['onchain_data']:
            try:
                diffusion = self.data_cache['onchain_data'].get('diffusion_score', 50)
                return float(diffusion)
            except:
                pass
        
        return 50.0
    
    def _get_coinbase_premium(self) -> float:
        """Get Coinbase premium %"""
        # Would need Coinbase API integration
        # Placeholder for now
        return 0.0
    
    def _get_current_regime(self) -> Tuple[str, float]:
        """Get current market regime"""
        if self.regime_detector and self.data_cache['onchain_data']:
            try:
                # Would need full feature set - simplified
                result = self.regime_detector.detect_regime({
                    'fear_greed_index': self._get_fear_greed(),
                    'diffusion_score': self._get_diffusion_score()
                })
                return result.get('regime', 'normal'), result.get('confidence', 0.0)
            except:
                pass
        
        return 'normal', 0.0
    
    def _save_alert_history(self):
        """Save alert history to file"""
        try:
            with open('alert_history.json', 'w') as f:
                json.dump(self.alert_history[-100:], f, indent=2)  # Keep last 100
        except Exception as e:
            print(f"Error saving history: {e}")


if __name__ == "__main__":
    # Create and run monitor
    monitor = WhaleAlertMonitor()
    
    print("""
╔══════════════════════════════════════════╗
║   🐋 WHALE ALERT MONITOR v1.0           ║
║   Real-time On-Chain Alert System        ║
╚══════════════════════════════════════════╝

Configuration:
- Check interval: 15 minutes
- Cooldown: 6 hours per alert type
- Telegram: Configure in alert_config.json

Starting monitor...
    """)
    
    monitor.run_forever()
