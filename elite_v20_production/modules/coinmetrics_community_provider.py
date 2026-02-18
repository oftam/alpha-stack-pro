#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 COINMETRICS COMMUNITY PROVIDER - Free Tier On-chain Data
Optimized for free tier limitations with aggressive caching

Free Tier Limits:
- Limited historical data
- Rate limited (slower requests)
- Community endpoints only

Strategy:
- Cache everything (1 hour TTL)
- Minimal API calls
- Fallback to neutral if error
"""

import requests
import pandas as pd
from typing import Dict, Optional
from datetime import datetime, timedelta
from functools import lru_cache
import time


class CoinMetricsCommunityProvider:
    """
    Free tier on-chain data provider
    
    Focus: Validation, not production
    - Netflow estimates
    - Active addresses
    - Transaction counts
    """
    
    def __init__(self):
        self.base_url = "https://api.coinmetrics.io/v4"
        self.session = requests.Session()
        
        # Rate limiting (be conservative on free tier)
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 2 seconds between requests
        
        print("✅ CoinMetrics Community provider initialized (FREE tier)")
        print("   Limited history, rate limited - for validation only")
    
    def _rate_limit(self):
        """Enforce conservative rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    @lru_cache(maxsize=32)
    def _fetch_metric(self, 
                     asset: str,
                     metric: str,
                     frequency: str = "1d",
                     limit: int = 7) -> pd.DataFrame:
        """
        Fetch metric from CoinMetrics Community API
        
        Cached for 1 hour to minimize API calls
        """
        
        self._rate_limit()
        
        url = f"{self.base_url}/timeseries/asset-metrics"
        
        params = {
            'assets': asset.lower(),
            'metrics': metric,
            'frequency': frequency,
            'limit_per_asset': limit,
            'page_size': limit
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 429:
                print("⚠️  CoinMetrics rate limit hit. Using cached data.")
                return pd.DataFrame()
            
            response.raise_for_status()
            
            data = response.json()
            
            if not data or 'data' not in data:
                return pd.DataFrame()
            
            records = data['data']
            
            if not records:
                return pd.DataFrame()
            
            df = pd.DataFrame(records)
            
            # Standardize columns
            if 'time' in df.columns:
                df['timestamp'] = pd.to_datetime(df['time'])
                df = df.set_index('timestamp')
            
            # Extract metric value
            if metric in df.columns:
                df['value'] = df[metric].astype(float)
            
            return df[['value']] if 'value' in df.columns else df
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("⚠️  CoinMetrics authentication required (community limit?)")
            else:
                print(f"⚠️  CoinMetrics API error: {e}")
            return pd.DataFrame()
        
        except Exception as e:
            print(f"⚠️  CoinMetrics fetch error: {e}")
            return pd.DataFrame()
    
    # =========================================================================
    # AVAILABLE METRICS (Community Tier)
    # =========================================================================
    
    def get_active_addresses(self, asset: str = "btc") -> pd.DataFrame:
        """
        Active addresses (daily)
        
        Proxy for network activity
        """
        return self._fetch_metric(asset, 'AdrActCnt', limit=7)
    
    def get_transaction_count(self, asset: str = "btc") -> pd.DataFrame:
        """
        Transaction count (daily)
        
        Network usage indicator
        """
        return self._fetch_metric(asset, 'TxCnt', limit=7)
    
    def get_transfer_volume(self, asset: str = "btc") -> pd.DataFrame:
        """
        Transfer volume in native units
        
        Estimate of on-chain flow
        """
        return self._fetch_metric(asset, 'TxTfrValAdjNtv', limit=7)
    
    def get_price_usd(self, asset: str = "btc") -> pd.DataFrame:
        """Reference rate (for correlation checks)"""
        return self._fetch_metric(asset, 'PriceUSD', limit=7)
    
    # =========================================================================
    # COMPOSITE ANALYSIS
    # =========================================================================
    
    def analyze_onchain_state(self, asset: str = "btc") -> Dict:
        """
        On-chain analysis using FREE community metrics
        
        Focus: Activity trends (not exchange flows - not available on free tier)
        """
        
        # Fetch available metrics
        active_addrs = self.get_active_addresses(asset)
        tx_count = self.get_transaction_count(asset)
        transfer_vol = self.get_transfer_volume(asset)
        
        if active_addrs.empty and tx_count.empty and transfer_vol.empty:
            return {
                'error': 'No data available',
                'has_real_data': False,
                'diffusion_score': 50,
                'signal': 'NEUTRAL',
                'interpretation': 'No on-chain provider configured.',
                'provider': 'None'
            }
        
        scores = {}
        raw_metrics = {}
        
        # 1. Active addresses trend
        if not active_addrs.empty and len(active_addrs) >= 3:
            recent_avg = active_addrs['value'].tail(3).mean()
            older_avg = active_addrs['value'].head(3).mean()
            change_pct = ((recent_avg - older_avg) / older_avg) * 100
            
            raw_metrics['active_addresses_change_pct'] = change_pct
            
            if change_pct > 10:
                scores['activity'] = 70
            elif change_pct > 5:
                scores['activity'] = 60
            elif change_pct > 0:
                scores['activity'] = 55
            elif change_pct > -5:
                scores['activity'] = 45
            else:
                scores['activity'] = 35
        
        # 2. Transaction volume trend
        if not tx_count.empty and len(tx_count) >= 3:
            recent_tx = tx_count['value'].tail(3).mean()
            older_tx = tx_count['value'].head(3).mean()
            tx_change_pct = ((recent_tx - older_tx) / older_tx) * 100
            
            raw_metrics['tx_count_change_pct'] = tx_change_pct
            
            if tx_change_pct > 10:
                scores['transactions'] = 65
            elif tx_change_pct > 0:
                scores['transactions'] = 55
            elif tx_change_pct > -10:
                scores['transactions'] = 45
            else:
                scores['transactions'] = 35
        
        # 3. Transfer volume trend
        if not transfer_vol.empty and len(transfer_vol) >= 3:
            recent_vol = transfer_vol['value'].tail(3).mean()
            older_vol = transfer_vol['value'].head(3).mean()
            vol_change_pct = ((recent_vol - older_vol) / older_vol) * 100
            
            raw_metrics['transfer_volume_change_pct'] = vol_change_pct
            
            if vol_change_pct > 15:
                scores['volume'] = 70
            elif vol_change_pct > 5:
                scores['volume'] = 60
            elif vol_change_pct > 0:
                scores['volume'] = 55
            else:
                scores['volume'] = 45
        
        # Overall diffusion score
        if scores:
            weights = {
                'activity': 0.4,
                'transactions': 0.3,
                'volume': 0.3
            }
            
            diffusion_score = sum(
                scores[k] * weights.get(k, 0) 
                for k in scores
            ) / sum(weights.get(k, 0) for k in scores)
        else:
            diffusion_score = 50
        
        # Signal classification (conservative - community data is lagged)
        if diffusion_score > 65:
            signal = "ACCUMULATION"
        elif diffusion_score > 55:
            signal = "NEUTRAL_BULLISH"
        elif diffusion_score < 40:
            signal = "DISTRIBUTION"
        elif diffusion_score < 50:
            signal = "NEUTRAL_BEARISH"
        else:
            signal = "NEUTRAL"
        
        # Interpretation
        if signal == "ACCUMULATION":
            interp = "Network activity increasing: more addresses active, higher tx volume."
        elif signal == "NEUTRAL_BULLISH":
            interp = "Moderate activity increase: slight bullish tilt on-chain."
        elif signal == "DISTRIBUTION":
            interp = "Network activity declining: fewer addresses, lower volume."
        elif signal == "NEUTRAL_BEARISH":
            interp = "Activity decreasing slightly: mild bearish tilt."
        else:
            interp = "Network activity stable: no clear trend."
        
        return {
            'diffusion_score': diffusion_score,
            'signal': signal,
            'interpretation': interp,
            'components': scores,
            'raw_metrics': raw_metrics,
            'has_real_data': True,
            'data_points': len(active_addrs) if not active_addrs.empty else 0,
            'provider': 'CoinMetrics (Community/FREE)',
            'note': 'Limited history, validation only - not for production decisions'
        }


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == '__main__':
    try:
        provider = CoinMetricsCommunityProvider()
        
        # Analyze on-chain state
        result = provider.analyze_onchain_state('btc')
        
        if result.get('error'):
            print(f"\n❌ Error: {result['error']}")
            exit(1)
        
        print("\n" + "="*60)
        print("ON-CHAIN ANALYSIS (COMMUNITY/FREE)")
        print("="*60)
        print(f"Diffusion Score: {result['diffusion_score']:.1f}/100")
        print(f"Signal: {result['signal']}")
        print(f"Provider: {result['provider']}")
        print(f"\nInterpretation:")
        print(f"  {result['interpretation']}")
        
        if result['components']:
            print(f"\nComponents:")
            for k, v in result['components'].items():
                print(f"  {k}: {v:.1f}/100")
        
        if result['raw_metrics']:
            print(f"\nRaw Metrics:")
            for k, v in result['raw_metrics'].items():
                print(f"  {k}: {v:.2f}%")
        
        print(f"\nData Points: {result['data_points']} days")
        print(f"\n⚠️  Note: {result['note']}")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
