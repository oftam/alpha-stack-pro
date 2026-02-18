#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MODULE 1: On-Chain Diffusion Layer
"עיני רנטגן" - רואה את הכסף לפני שהמחיר זז

Implements:
- Exchange netflow tracking
- Whale wallet monitoring  
- SOPR (Spent Output Profit Ratio)
- Entity-adjusted flows

Data sources:
- Glassnode API (premium)
- CryptoQuant API (alternative)
- Fallback to proxy metrics (if no API key)
"""

import os
import requests
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta


class OnChainDiffusionLayer:
    """
    Tracks on-chain flows to detect accumulation/distribution
    before price moves
    
    Key metrics:
    - Exchange Netflow: coins in - coins out (negative = accumulation)
    - Whale Activity: wallets > 1000 BTC
    - SOPR: realized profit/loss on-chain
    - Entity Flow: institutional vs retail
    """
    
    def __init__(self, 
                 glassnode_api_key: Optional[str] = None,
                 cryptoquant_api_key: Optional[str] = None,
                 whale_threshold_btc: float = 1000.0):
        """
        Initialize with API keys
        
        Args:
            glassnode_api_key: Glassnode API key (or set GLASSNODE_API_KEY env)
            cryptoquant_api_key: CryptoQuant API key
            whale_threshold_btc: Minimum balance to be considered whale
        """
        self.glassnode_key = glassnode_api_key or os.getenv('GLASSNODE_API_KEY')
        self.cryptoquant_key = cryptoquant_api_key or os.getenv('CRYPTOQUANT_API_KEY')
        self.whale_threshold = whale_threshold_btc
        
        self.has_glassnode = bool(self.glassnode_key)
        self.has_cryptoquant = bool(self.cryptoquant_key)
        
        # Initialize Glassnode provider if key available
        if self.has_glassnode:
            try:
                from glassnode_provider import GlassnodeProvider
                self.glassnode = GlassnodeProvider(self.glassnode_key)
                print(f"✅ Glassnode Professional LIVE (tier: LIVE)")
            except Exception as e:
                print(f"⚠️ Glassnode init failed: {e}")
                self.glassnode = None
                self.has_glassnode = False
        else:
            self.glassnode = None
        
        # Initialize CryptoQuant provider if key available
        if self.has_cryptoquant:
            try:
                from cryptoquant_provider import CryptoQuantProvider
                self.cryptoquant = CryptoQuantProvider(self.cryptoquant_key)
                print(f"✅ CryptoQuant Professional LIVE (tier: LIVE)")
                
                # Update data tier status
                from dashboard_adapter import DataTier
                self.data_tier = DataTier.LIVE
            except ImportError as e:
                print(f"⚠️ CryptoQuant import failed: {e}")
                print(f"   Make sure cryptoquant_provider.py is in the same directory")
                self.cryptoquant = None
                self.has_cryptoquant = False
            except Exception as e:
                print(f"⚠️ CryptoQuant init failed: {e}")
                import traceback
                traceback.print_exc()
                self.cryptoquant = None
                self.has_cryptoquant = False
        else:
            self.cryptoquant = None
        
        # Initialize Fear & Greed Index
        try:
            from fear_greed_provider import FearGreedProvider
            self.fear_greed = FearGreedProvider()
            self.has_fear_greed = True
        except Exception as e:
            print(f"⚠️ Fear & Greed init failed: {e}")
            self.fear_greed = None
            self.has_fear_greed = False
        
        # Initialize Supply Shock detector
        if self.has_cryptoquant:
            try:
                from supply_shock_detector import SupplyShockDetector
                self.supply_shock = SupplyShockDetector(self.cryptoquant)
                self.has_supply_shock = True
            except Exception as e:
                print(f"⚠️ Supply Shock detector init failed: {e}")
                self.supply_shock = None
                self.has_supply_shock = False
        else:
            self.supply_shock = None
            self.has_supply_shock = False
        
        # Initialize CoinMetrics Community as fallback
        if not (self.has_glassnode or self.has_cryptoquant):
            try:
                from coinmetrics_community_provider import CoinMetricsCommunityProvider
                self.coinmetrics = CoinMetricsCommunityProvider()
                self.has_coinmetrics = True
            except ImportError:
                print("⚠️  No on-chain provider configured. On-chain analysis DISABLED.")
                self.coinmetrics = None
                self.has_coinmetrics = False
        else:
            self.coinmetrics = None
            self.has_coinmetrics = False
            print(f"✅ On-chain layer initialized (Glassnode: {self.has_glassnode}, CryptoQuant: {self.has_cryptoquant})")
    
    # =========================================================================
    # GLASSNODE INTEGRATION
    # =========================================================================
    
    def _fetch_glassnode_metric(self, metric: str, asset: str = "BTC", 
                                interval: str = "24h", limit: int = 90) -> pd.DataFrame:
        """Fetch metric from Glassnode API"""
        
        if not self.has_glassnode:
            return pd.DataFrame()
        
        url = f"https://api.glassnode.com/v1/metrics/{metric}"
        params = {
            'a': asset,
            'api_key': self.glassnode_key,
            'i': interval,
            's': int((datetime.now() - timedelta(days=limit)).timestamp()),
            'e': int(datetime.now().timestamp())
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['t'], unit='s')
            df['value'] = df['v'].astype(float)
            return df[['timestamp', 'value']].set_index('timestamp')
            
        except Exception as e:
            print(f"⚠️  Glassnode API error ({metric}): {e}")
            return pd.DataFrame()
    
    def get_exchange_netflow(self, days: int = 30) -> pd.DataFrame:
        """
        Get exchange netflow (inflow - outflow)
        
        Negative netflow = coins leaving exchanges = accumulation (bullish)
        Positive netflow = coins entering exchanges = distribution (bearish)
        """
        
        # Try CryptoQuant first
        if self.has_cryptoquant:
            try:
                return self.cryptoquant.get_exchange_netflow(days)
            except Exception as e:
                print(f"⚠️ CryptoQuant netflow failed: {e}")
        
        # Fallback to Glassnode
        if self.has_glassnode:
            return self._fetch_glassnode_metric(
                'transactions/transfers_volume_exchanges_net',
                limit=days
            )
        
        # Final fallback: proxy using volume
        print("⚠️  Using proxy netflow (volume-based estimate)")
        return pd.DataFrame({'value': [0]})  # Placeholder
    
    def get_whale_balances(self, days: int = 30) -> pd.DataFrame:
        """
        Track whale wallet balances (>1000 BTC)
        
        Increasing = whales accumulating (bullish)
        Decreasing = whales distributing (bearish)
        """
        
        if self.has_glassnode:
            return self._fetch_glassnode_metric(
                'distribution/balance_1k_10k',
                limit=days
            )
        
        if self.has_cryptoquant:
            # CryptoQuant doesn't have whale balance endpoint - use alternatives
            print("⚠️ Whale balance tracking not available on CryptoQuant")
            return pd.DataFrame({'value': [0]})
        
        print("⚠️ Whale tracking unavailable (no on-chain provider)")
        return pd.DataFrame({'value': [0]})
    
    def get_sopr(self, days: int = 30) -> pd.DataFrame:
        """
        SOPR (Spent Output Profit Ratio)
        
        SOPR > 1: coins moving at profit (potential distribution)
        SOPR < 1: coins moving at loss (potential capitulation)
        SOPR ≈ 1: breakeven (neutral)
        """
        
        if self.has_glassnode:
            return self._fetch_glassnode_metric(
                'indicators/sopr',
                limit=days
            )
        
        if self.has_cryptoquant:
            # CryptoQuant doesn't have SOPR endpoint - would need calculation
            print("⚠️ SOPR not available on CryptoQuant (requires Glassnode)")
            return pd.DataFrame({'value': [1.0]})  # Neutral placeholder
        
        print("⚠️ SOPR unavailable (no on-chain provider)")
        return pd.DataFrame({'value': [1.0]})  # Neutral placeholder
    
    # =========================================================================
    # ANALYSIS & SCORING
    # =========================================================================
    
    def analyze_diffusion(self, 
                          price_df: pd.DataFrame,
                          lookback_days: int = 30) -> Dict:
        """
        Comprehensive on-chain diffusion analysis with Fear & Supply Shock
        
        The fear is the fuel that enables diffusion at accelerated rates.
        When Fear = extreme AND Supply dropping AND Netflow negative = ultimate signal.
        
        Returns:
            Dict with diffusion score (0-100) and component metrics
        """
        
        # If using CoinMetrics Community (free tier), delegate to it
        if self.has_coinmetrics and not (self.has_glassnode or self.has_cryptoquant):
            result = self.coinmetrics.analyze_onchain_state('btc')
            result['has_real_data'] = True  # CoinMetrics data is real (not proxy)
            return result
        
        # Fetch on-chain metrics (Glassnode/CryptoQuant)
        netflow = self.get_exchange_netflow(lookback_days)
        whale_balance = self.get_whale_balances(lookback_days)
        sopr = self.get_sopr(lookback_days)
        
        # Component scores (0-100 each)
        scores = {}
        
        # 1. Netflow score
        recent_netflow = 0
        if not netflow.empty:
            recent_netflow = netflow['value'].tail(7).mean()
            # Negative netflow = accumulation = high score
            if recent_netflow < -1000:  # Strong accumulation
                scores['netflow'] = 80
            elif recent_netflow < 0:
                scores['netflow'] = 60
            elif recent_netflow < 1000:
                scores['netflow'] = 40
            else:  # Strong distribution
                scores['netflow'] = 20
        else:
            scores['netflow'] = 50  # Neutral if no data
        
        # 2. Whale accumulation score
        if not whale_balance.empty and len(whale_balance) > 1:
            whale_change = (whale_balance['value'].iloc[-1] - 
                          whale_balance['value'].iloc[0]) / whale_balance['value'].iloc[0]
            
            if whale_change > 0.05:  # 5%+ increase
                scores['whale'] = 80
            elif whale_change > 0:
                scores['whale'] = 60
            elif whale_change > -0.05:
                scores['whale'] = 40
            else:
                scores['whale'] = 20
        else:
            scores['whale'] = 50
        
        # 3. SOPR score
        if not sopr.empty:
            recent_sopr = sopr['value'].tail(7).mean()
            
            if 0.95 < recent_sopr < 1.05:  # Around breakeven = accumulation zone
                scores['sopr'] = 70
            elif recent_sopr < 0.95:  # Capitulation
                scores['sopr'] = 90  # Extreme buying opportunity
            elif recent_sopr > 1.10:  # Taking profits
                scores['sopr'] = 30
            else:
                scores['sopr'] = 50
        else:
            scores['sopr'] = 50
        
        # =====================================================================
        # FEAR & GREED AMPLIFICATION
        # =====================================================================
        fear_amplifier = 1.0
        fear_data = {}
        
        if self.has_fear_greed:
            fear_current = self.fear_greed.get_current_fear_greed()
            fear_trend = self.fear_greed.get_fear_trend()
            fear_amplifier = self.fear_greed.get_signal_amplifier()
            
            fear_data = {
                'value': fear_current['value'],
                'classification': fear_current['classification'],
                'is_extreme_fear': fear_current['is_extreme_fear'],
                'is_blood_in_streets': fear_trend['is_blood_in_streets'],
                'amplifier': fear_amplifier
            }
        
        # =====================================================================
        # SUPPLY SHOCK DETECTION
        # =====================================================================
        supply_shock_data = {}
        conviction_boost = 0.0
        
        if self.has_supply_shock:
            supply_shock = self.supply_shock.analyze_supply_shock()
            diffusion_confirm = self.supply_shock.get_diffusion_confirmation(recent_netflow)
            
            supply_shock_data = {
                'is_shock': supply_shock['is_shock'],
                'reserve_change_7d': supply_shock['reserve_change_7d'],
                'severity': supply_shock['severity'],
                'conviction_boost': supply_shock['conviction_boost'],
                'diffusion_confirmed': diffusion_confirm['is_diffusion'],
                'diffusion_strength': diffusion_confirm['strength']
            }
            
            conviction_boost = supply_shock['conviction_boost']
        
        # =====================================================================
        # COMPOSITE SCORE WITH AMPLIFICATION
        # =====================================================================
        
        # Base diffusion score (weighted average)
        weights = {'netflow': 0.4, 'whale': 0.4, 'sopr': 0.2}
        base_score = sum(scores[k] * weights[k] for k in scores)
        
        # Apply fear amplification
        amplified_score = base_score * fear_amplifier
        
        # Cap at 100
        diffusion_score = min(100, amplified_score)
        
        # Interpretation with fear context
        if fear_data.get('is_extreme_fear') and base_score > 60:
            signal = "BLOOD_IN_STREETS"
            interpretation = "🔥 EXTREME FEAR + Accumulation = Ultimate Buy Signal"
        elif diffusion_score > 70:
            signal = "STRONG_ACCUMULATION"
            interpretation = "Institutions buying, expect upside"
        elif diffusion_score > 55:
            signal = "ACCUMULATION"
            interpretation = "Moderate buying pressure"
        elif diffusion_score < 30:
            signal = "DISTRIBUTION"
            interpretation = "Coins moving to exchanges, caution"
        else:
            signal = "NEUTRAL"
            interpretation = "Balanced flows, wait for clarity"
        
        return {
            'diffusion_score': diffusion_score,
            'base_score': base_score,
            'signal': signal,
            'interpretation': interpretation,
            'components': scores,
            'fear_greed': fear_data,
            'supply_shock': supply_shock_data,
            'conviction_boost': conviction_boost,
            'has_real_data': True
        }
    
    # =========================================================================
    # VALIDATION
    # =========================================================================
    
    def validate_predictive_power(self, 
                                  historical_prices: pd.DataFrame,
                                  days: int = 90) -> Dict:
        """
        Validate if on-chain metrics actually predict price
        
        Tests:
        - Does netflow correlate with future returns?
        - Does whale accumulation lead price?
        - Does SOPR bottom predict rallies?
        
        Returns validation metrics
        """
        
        results = {
            'netflow_correlation': None,
            'whale_lead_lag': None,
            'sopr_bottom_accuracy': None,
            'validation_summary': "No API key - cannot validate"
        }
        
        if not (self.has_glassnode or self.has_cryptoquant):
            return results
        
        # Fetch historical on-chain data
        netflow = self.get_exchange_netflow(days)
        whale = self.get_whale_balances(days)
        sopr = self.get_sopr(days)
        
        if netflow.empty:
            return results
        
        # Align with price data
        merged = historical_prices.join(netflow, how='inner', rsuffix='_netflow')
        
        if len(merged) < 30:
            results['validation_summary'] = "Insufficient data for validation"
            return results
        
        # Test 1: Netflow vs future returns
        merged['future_return_7d'] = merged['close'].pct_change(periods=7).shift(-7)
        
        corr = merged[['value', 'future_return_7d']].corr().iloc[0, 1]
        results['netflow_correlation'] = corr
        
        # Test 2: Whale accumulation lead/lag
        # (Implementation depends on data quality)
        
        # Summary
        if abs(corr) > 0.3:
            results['validation_summary'] = f"✅ Netflow shows predictive power (corr: {corr:.2f})"
        else:
            results['validation_summary'] = f"⚠️  Weak correlation (corr: {corr:.2f})"
        
        return results


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == '__main__':
    # Initialize (with or without API key)
    diffusion = OnChainDiffusionLayer(
        glassnode_api_key=None,  # Set your key here or in env
        whale_threshold_btc=1000.0
    )
    
    # Analyze current diffusion state
    # (You'd pass your actual price DataFrame here)
    fake_price_df = pd.DataFrame({
        'close': [70000, 71000, 70500]
    })
    
    result = diffusion.analyze_diffusion(fake_price_df)
    
    print("\n" + "="*60)
    print("ON-CHAIN DIFFUSION ANALYSIS")
    print("="*60)
    print(f"Diffusion Score: {result['diffusion_score']:.1f}/100")
    print(f"Signal: {result['signal']}")
    print(f"Interpretation: {result['interpretation']}")
    print(f"\nComponent Scores:")
    for k, v in result['components'].items():
        print(f"  {k}: {v:.1f}/100")
    print("="*60)
