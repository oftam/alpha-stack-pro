#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
😱 FEAR & GREED INDEX PROVIDER
"הפחד הוא הדלק" - מדד הרגש כטריגר לדיפוזיה

Data source: Alternative.me API (free, real-time)
Updates: Daily
Range: 0-100 (0 = Extreme Fear, 100 = Extreme Greed)

Critical thresholds:
- Extreme Fear (0-20): Blood in the streets → BUY signal amplifier
- Fear (21-40): Caution → Neutral
- Neutral (41-60): Equilibrium
- Greed (61-80): Warning → Reduce exposure
- Extreme Greed (81-100): Euphoria → SELL signal amplifier
"""

import requests
import pandas as pd
from typing import Dict, Optional
from datetime import datetime, timedelta
from functools import lru_cache


class FearGreedProvider:
    """
    Crypto Fear & Greed Index (free API)
    
    The fear is the fuel that enables diffusion at accelerated rates.
    When fear = extreme AND netflow = negative → strongest buy signal.
    """
    
    def __init__(self):
        self.base_url = "https://api.alternative.me/fng/"
        print("✅ Fear & Greed Index initialized (free API)")
        print("   Source: Alternative.me")
        print("   Updates: Real-time")
    
    @lru_cache(maxsize=1)
    def get_current_fear_greed(self) -> Dict:
        """
        Get current Fear & Greed reading
        
        Returns:
            {
                'value': int (0-100),
                'classification': str ('Extreme Fear', 'Fear', etc),
                'timestamp': datetime,
                'is_extreme_fear': bool (value < 20),
                'is_extreme_greed': bool (value > 80)
            }
        """
        try:
            response = requests.get(f"{self.base_url}?limit=1", timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if data.get('data'):
                latest = data['data'][0]
                value = int(latest['value'])
                
                return {
                    'value': value,
                    'classification': latest['value_classification'],
                    'timestamp': datetime.fromtimestamp(int(latest['timestamp'])),
                    'is_extreme_fear': value < 20,
                    'is_extreme_greed': value > 80,
                    'is_fear': value < 40,
                    'is_greed': value > 60
                }
            
            return self._default_reading()
            
        except Exception as e:
            print(f"⚠️ Fear & Greed API error: {e}")
            return self._default_reading()
    
    @lru_cache(maxsize=1)
    def get_historical_fear_greed(self, days: int = 30) -> pd.DataFrame:
        """
        Get historical Fear & Greed data
        
        Args:
            days: Number of days to fetch (max 365)
            
        Returns:
            DataFrame with columns: value, classification, timestamp
        """
        try:
            response = requests.get(f"{self.base_url}?limit={days}", timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('data'):
                records = []
                for entry in data['data']:
                    records.append({
                        'timestamp': datetime.fromtimestamp(int(entry['timestamp'])),
                        'value': int(entry['value']),
                        'classification': entry['value_classification']
                    })
                
                df = pd.DataFrame(records)
                df = df.set_index('timestamp').sort_index()
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"⚠️ Fear & Greed historical error: {e}")
            return pd.DataFrame()
    
    def get_fear_trend(self, days: int = 7) -> Dict:
        """
        Analyze fear/greed trend over recent period
        
        Returns:
            {
                'avg_value': float,
                'trend': str ('increasing_fear', 'decreasing_fear', 'stable'),
                'extreme_fear_days': int (how many days in extreme fear),
                'is_blood_in_streets': bool (sustained extreme fear)
            }
        """
        df = self.get_historical_fear_greed(days)
        
        if df.empty:
            return {
                'avg_value': 50,
                'trend': 'stable',
                'extreme_fear_days': 0,
                'is_blood_in_streets': False
            }
        
        avg_value = df['value'].mean()
        recent_avg = df.tail(3)['value'].mean()
        older_avg = df.head(3)['value'].mean()
        
        # Trend detection
        if recent_avg < older_avg - 10:
            trend = 'increasing_fear'
        elif recent_avg > older_avg + 10:
            trend = 'decreasing_fear'
        else:
            trend = 'stable'
        
        # Extreme fear persistence
        extreme_fear_days = (df['value'] < 20).sum()
        is_blood_in_streets = extreme_fear_days >= 3  # 3+ days of extreme fear
        
        return {
            'avg_value': avg_value,
            'trend': trend,
            'extreme_fear_days': extreme_fear_days,
            'is_blood_in_streets': is_blood_in_streets
        }
    
    def _default_reading(self) -> Dict:
        """Fallback when API unavailable"""
        return {
            'value': 50,
            'classification': 'Neutral',
            'timestamp': datetime.now(),
            'is_extreme_fear': False,
            'is_extreme_greed': False,
            'is_fear': False,
            'is_greed': False
        }
    
    def get_signal_amplifier(self) -> float:
        """
        Get signal strength multiplier based on fear level
        
        Returns:
            Multiplier (0.5 - 2.0):
            - Extreme Fear: 2.0x (double signal strength)
            - Fear: 1.5x
            - Neutral: 1.0x (no change)
            - Greed: 0.75x
            - Extreme Greed: 0.5x (halve signal strength)
        """
        current = self.get_current_fear_greed()
        value = current['value']
        
        if value < 20:  # Extreme Fear
            return 2.0
        elif value < 40:  # Fear
            return 1.5
        elif value < 60:  # Neutral
            return 1.0
        elif value < 80:  # Greed
            return 0.75
        else:  # Extreme Greed
            return 0.5


if __name__ == "__main__":
    # Test
    provider = FearGreedProvider()
    
    current = provider.get_current_fear_greed()
    print(f"\n📊 Current Fear & Greed:")
    print(f"   Value: {current['value']}/100")
    print(f"   Classification: {current['classification']}")
    print(f"   Extreme Fear: {current['is_extreme_fear']}")
    
    trend = provider.get_fear_trend()
    print(f"\n📈 7-Day Trend:")
    print(f"   Average: {trend['avg_value']:.1f}")
    print(f"   Trend: {trend['trend']}")
    print(f"   Blood in streets: {trend['is_blood_in_streets']}")
    
    amplifier = provider.get_signal_amplifier()
    print(f"\n🔊 Signal Amplifier: {amplifier}x")
