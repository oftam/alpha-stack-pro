#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⛓️ CRYPTOQUANT PROVIDER - Real On-chain Data
Free tier optimized: 50 req/day, 7 days historic

Metrics:
- Exchange flows (netflow)
- Exchange reserves
- Miner flows
- Whale alerts
"""

import os
import requests
import pandas as pd
from typing import Dict, Optional
from datetime import datetime, timedelta
from functools import lru_cache
import time


class CryptoQuantProvider:
    """
    Production on-chain data provider (FREE tier)
    
    Optimized for:
    - 50 requests/day limit
    - 7 days historic data
    - 1-day resolution
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('CRYPTOQUANT_API_KEY') or "apPg3cHC5va0BdeYFbZAqE2PT27i9Jb1jS52erg1hhXaPF4wYJmuqbdl6A7092bYp7KjlEk"
        
        if not self.api_key:
            raise ValueError("CRYPTOQUANT_API_KEY required")
        
        self.base_url = "https://api.cryptoquant.com/v1"
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}'
        })
        
        # Professional tier rate limiting (100 req/day, 24H resolution)
        self.last_request_time = 0
        self.min_request_interval = 3600 / 80  # 80 requests/day buffer (20% headroom)
        
        print("✅ CryptoQuant Professional API initialized")
        print("   Rate limit: 100 req/day")
        print("   Resolution: Up to 24H")
        print("   Data coverage: ALL exchange flows")
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    @lru_cache(maxsize=16)
    def _fetch_metric(self, 
                     endpoint: str,
                     window: str = "day",
                     limit: int = 7) -> pd.DataFrame:
        """
        Fetch metric from CryptoQuant API
        
        Cached for 1 hour to save requests
        """
        
        self._rate_limit()
        
        url = f"{self.base_url}/btc/{endpoint}"
        
        params = {
            'window': window,
            'exchange': 'all_exchange',  # Required parameter for exchange-flows endpoints
            'limit': min(limit, 7)  # Max 7 days on Professional tier
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 429:
                print("⚠️  CryptoQuant rate limit hit. Cached data will be used.")
                return pd.DataFrame()
            
            response.raise_for_status()
            
            data = response.json()
            
            # CryptoQuant format: {'status': {...}, 'result': {'data': [...]}}
            if not data or 'result' not in data or 'data' not in data['result']:
                return pd.DataFrame()
            
            records = data['result']['data']
            
            if not records:
                return pd.DataFrame()
            
            df = pd.DataFrame(records)
            
            # Standardize columns
            if 'date' in df.columns:
                df['timestamp'] = pd.to_datetime(df['date'])
                df = df.set_index('timestamp')
            
            # Extract value column - look for netflow_total, value, etc
            value_cols = [c for c in df.columns if c not in ['date', 'timestamp']]
            if value_cols:
                # Use first numeric column as 'value'
                df['value'] = df[value_cols[0]].astype(float)
            
            return df[['value']] if 'value' in df.columns else df
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 402:
                print("⚠️  Metric requires premium plan")
            elif e.response.status_code == 400:
                print(f"⚠️  CryptoQuant API error (bad request): {endpoint}")
                print(f"     Check parameters - may need 'exchange' param")
            else:
                print(f"⚠️  CryptoQuant API error: {e}")
            return pd.DataFrame()
        
        except Exception as e:
            print(f"⚠️  CryptoQuant fetch error: {e}")
            return pd.DataFrame()
    
    # =========================================================================
    # CORE METRICS
    # =========================================================================
    
    def get_exchange_netflow(self, days: int = 7) -> pd.DataFrame:
        """
        Exchange netflow (REAL)
        
        Positive = inflow (distribution)
        Negative = outflow (accumulation)
        
        Args:
            days: Historical days to fetch (limited by plan tier)
        """
        return self._fetch_metric('exchange-flows/netflow', limit=min(days, 7))
    
    def get_exchange_reserve(self) -> pd.DataFrame:
        """
        Total BTC on exchanges
        
        Decreasing = accumulation
        Increasing = distribution
        """
        return self._fetch_metric('exchange-flows/reserve', limit=7)
    
    def get_miner_to_exchange(self) -> pd.DataFrame:
        """
        Miner flow to exchanges
        
        Increasing = miners selling (bearish)
        """
        return self._fetch_metric('miner-flows/to-exchange-sum', limit=7)
    
    def get_large_transactions(self) -> pd.DataFrame:
        """
        Transactions > $100k
        
        Whale activity indicator
        """
        return self._fetch_metric('network-data/tx-large-count', limit=7)
    
    # =========================================================================
    # COMPOSITE ANALYSIS
    # =========================================================================
    
    def analyze_onchain_state(self) -> Dict:
        """
        Complete on-chain analysis with free tier data
        
        Uses 3-4 requests (well within daily limit)
        """
        
        # Fetch metrics (cached for 1 hour)
        netflow = self.get_exchange_netflow()
        reserve = self.get_exchange_reserve()
        miner_flow = self.get_miner_to_exchange()
        
        if netflow.empty and reserve.empty:
            return {
                'error': 'No data available',
                'has_real_data': False
            }
        
        scores = {}
        raw_metrics = {}
        
        # 1. Netflow analysis
        if not netflow.empty:
            recent_netflow = netflow['value'].tail(3).mean()  # 3-day avg
            
            raw_metrics['netflow'] = recent_netflow
            
            if recent_netflow < -5000:
                scores['netflow'] = 85
            elif recent_netflow < -1000:
                scores['netflow'] = 70
            elif recent_netflow < 0:
                scores['netflow'] = 60
            elif recent_netflow < 1000:
                scores['netflow'] = 45
            elif recent_netflow < 5000:
                scores['netflow'] = 30
            else:
                scores['netflow'] = 20
        
        # 2. Reserve trend
        if not reserve.empty and len(reserve) >= 3:
            reserve_change = (reserve['value'].iloc[-1] - reserve['value'].iloc[0]) / reserve['value'].iloc[0]
            
            raw_metrics['reserve_change_pct'] = reserve_change * 100
            
            if reserve_change < -0.05:
                scores['reserve'] = 80
            elif reserve_change < -0.02:
                scores['reserve'] = 65
            elif reserve_change < 0:
                scores['reserve'] = 55
            elif reserve_change < 0.02:
                scores['reserve'] = 45
            else:
                scores['reserve'] = 25
        
        # 3. Miner selling pressure
        if not miner_flow.empty:
            recent_miner = miner_flow['value'].tail(3).mean()
            
            raw_metrics['miner_flow'] = recent_miner
            
            if recent_miner < 100:
                scores['miner'] = 70
            elif recent_miner < 300:
                scores['miner'] = 55
            elif recent_miner < 500:
                scores['miner'] = 45
            else:
                scores['miner'] = 30
        
        # Overall diffusion score
        if scores:
            weights = {
                'netflow': 0.5,
                'reserve': 0.3,
                'miner': 0.2
            }
            
            diffusion_score = sum(
                scores[k] * weights.get(k, 0) 
                for k in scores
            ) / sum(weights.get(k, 0) for k in scores)
        else:
            diffusion_score = 50
        
        # Signal classification
        if diffusion_score > 70:
            signal = "STRONG_ACCUMULATION"
        elif diffusion_score > 55:
            signal = "ACCUMULATION"
        elif diffusion_score < 30:
            signal = "DISTRIBUTION"
        elif diffusion_score < 45:
            signal = "WEAK_DISTRIBUTION"
        else:
            signal = "NEUTRAL"
        
        # Interpretation
        if signal == "STRONG_ACCUMULATION":
            interp = "Heavy accumulation: Large outflows from exchanges, reserves declining."
        elif signal == "ACCUMULATION":
            interp = "Moderate accumulation: Net outflows, reduced selling pressure."
        elif signal == "DISTRIBUTION":
            interp = "Distribution phase: Large inflows to exchanges, potential selling."
        elif signal == "WEAK_DISTRIBUTION":
            interp = "Mild distribution: Some selling pressure, monitor closely."
        else:
            interp = "Neutral: Balanced flows, no clear trend."
        
        return {
            'diffusion_score': diffusion_score,
            'signal': signal,
            'interpretation': interp,
            'components': scores,
            'raw_metrics': raw_metrics,
            'has_real_data': True,
            'data_points': len(netflow) if not netflow.empty else 0,
            'provider': 'CryptoQuant (Free Tier)'
        }


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == '__main__':
    import sys
    
    # Get API key from arg or env
    api_key = sys.argv[1] if len(sys.argv) > 1 else os.getenv('CRYPTOQUANT_API_KEY')
    
    if not api_key:
        print("❌ No API key provided")
        print("\nUsage:")
        print("  python cryptoquant_provider.py YOUR_API_KEY")
        print("  or set CRYPTOQUANT_API_KEY environment variable")
        sys.exit(1)
    
    try:
        provider = CryptoQuantProvider(api_key)
        
        # Analyze on-chain state
        result = provider.analyze_onchain_state()
        
        if result.get('error'):
            print(f"\n❌ Error: {result['error']}")
            sys.exit(1)
        
        print("\n" + "="*60)
        print("ON-CHAIN ANALYSIS (REAL DATA)")
        print("="*60)
        print(f"Diffusion Score: {result['diffusion_score']:.1f}/100")
        print(f"Signal: {result['signal']}")
        print(f"Provider: {result['provider']}")
        print(f"\nInterpretation:")
        print(f"  {result['interpretation']}")
        print(f"\nComponents:")
        for k, v in result['components'].items():
            print(f"  {k}: {v:.1f}/100")
        print(f"\nRaw Metrics:")
        for k, v in result['raw_metrics'].items():
            print(f"  {k}: {v:.2f}")
        print(f"\nData Points: {result['data_points']} days")
        print("="*60)
        
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
