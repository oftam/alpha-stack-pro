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

import math
import os
import requests
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta


# =============================================================================
# 🧬 THE MVRV CAPITULATION GENE — “The Naor Insight”
# =============================================================================

def calculate_mvrv_alpha_factor(mvrv_ratio: Optional[float]) -> float:
    """
    Translate MVRV Ratio into an institutional Alpha boost/penalty.
    Instead of hardcoding a price trigger, we measure structural capitulation
    via the Topological Invariant: MVRV.

    MVRV < 0.7  → +25 pts  (generational undervaluation, maximum conviction)
    MVRV < 1.0  → +10 pts  (undervaluation zone, steady accumulation)
    1.0 ≤ MVRV ≤ 3.0 →   0 pts  (fair value noise)
    MVRV > 3.0  → −15 pts  (overvaluation / distribution zone)

    Returns float ∈ [−15, +25] — safe to add directly to the 0–100 gene score.
    """
    if mvrv_ratio is None:
        return 0.0
    if mvrv_ratio < 0.7:
        return 25.0   # Maximum conviction (Capitulation)
    if mvrv_ratio < 1.0:
        return 10.0   # Undervaluation zone
    if mvrv_ratio > 3.0:
        return -15.0  # Overvaluation / Distribution
    return 0.0        # Fair value — no edge


def _sigmoid(x: float) -> float:
    """Numerically stable sigmoid."""
    return 1.0 / (1.0 + math.exp(-max(-20, min(20, x))))


# Alias — "The Naor Insight" name used in architect docs
naor_mvrv_gene = calculate_mvrv_alpha_factor


def naor_fear_amplifier(
    fear: Optional[float],   # Fear & Greed index 0-100
    sopr: Optional[float],   # SOPR (< 1 = capitulation)
    mvrv: Optional[float],   # MVRV ratio
) -> float:
    """
    Triple-convergence Fear Amplifier — "Naor Gate".

    Computes a multiplicative boost (≥1.0) applied to the diffusion score
    when multiple capitulation signals align simultaneously:

        MVRV < 0.7   → structural undervaluation  (+0.5x boost)
        SOPR < 0.95  → realised losses / panic     (+0.3x boost)
        Fear  < 20   → extreme fear / retail dump  (+0.2x boost)
        All three    → triple convergence bonus     (+0.5x extra)

    Returns a multiplier in [1.0, 2.0].
    Neutral (no signal) → 1.0 (no change to base score).

    Examples
    --------
    MVRV=0.69, SOPR=0.92, Fear=12 → 1.0 + 0.5 + 0.3 + 0.2 + 0.5 = 2.0
    MVRV=1.5,  SOPR=1.01, Fear=45 → 1.0 (no boost)
    MVRV=0.69, SOPR=1.01, Fear=45 → 1.5 (MVRV only)
    """
    boost = 0.0
    hits  = 0

    if mvrv is not None and mvrv < 0.7:
        boost += 0.5
        hits  += 1
    if sopr is not None and sopr < 0.95:
        boost += 0.3
        hits  += 1
    if fear is not None and fear < 20:
        boost += 0.2
        hits  += 1

    # Triple-convergence bonus — when all three align simultaneously
    if hits == 3:
        boost += 0.5   # ← BLOOD_IN_STREETS signal

    return min(2.0, 1.0 + boost)   # cap at 2x


def fetch_live_mvrv() -> Optional[float]:
    """
    Multi-source MVRV puller — fallback chain:
      1. CryptoQuant Professional (if plan covers it)
      2. CoinMetrics Community API (free, no key needed)
    """
    api_key = os.getenv("CRYPTOQUANT_API_KEY")

    # ── Source 1: CryptoQuant ─────────────────────────────────────────────────
    if api_key:
        MVRV_ENDPOINTS = [
            ("https://api.cryptoquant.com/v1/btc/market-indicator/mvrv-ratio", "mvrv_ratio"),
            ("https://api.cryptoquant.com/v1/btc/market-indicator/mvrv", "mvrv"),
        ]
        headers = {"Authorization": f"Bearer {api_key}"}
        params  = {"window": "day", "limit": 2}
        for url, field in MVRV_ENDPOINTS:
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=10)
                if resp.status_code == 200:
                    data = resp.json().get("result", {}).get("data", [])
                    if data:
                        latest = data[-1]
                        for key in (field, "mvrv_ratio", "mvrv", "value"):
                            if key in latest:
                                mvrv = float(latest[key])
                                print(f"✅ MVRV (CryptoQuant) = {mvrv:.4f}")
                                return mvrv
                # 403 / 404 = not on this plan tier — skip silently
            except Exception:
                pass

    # ── Source 2: CoinMetrics Community API (free, no key required) ──────────
    # CapMVRVFF = Free-Float MVRV Ratio for BTC, updated daily
    try:
        cm_url = (
            "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
            "?assets=btc&metrics=CapMVRVFF&frequency=1d&limit=2"
        )
        cm_resp = requests.get(cm_url, timeout=10)
        if cm_resp.status_code == 200:
            series = cm_resp.json().get("data", [])
            if series:
                val = series[-1].get("CapMVRVFF")
                if val is not None:
                    mvrv = float(val)
                    print(f"✅ MVRV (CoinMetrics Community, free) = {mvrv:.4f}")
                    return mvrv
    except Exception as exc:
        print(f"⚠️ CoinMetrics MVRV fallback failed: {exc}")

    print("⚠️ All MVRV sources exhausted — gene silenced (neutral, 0 pts).")
    return None



def inject_naor_gene(base_manifold: float) -> float:
    """
    Injects the MVRV Topological Invariant into any manifold score.

    Usage (anywhere in the codebase):
        from modules.module_1_onchain_diffusion import inject_naor_gene
        elite_score = inject_naor_gene(raw_score)   # adds up to ±25 pts

    Bayesian cap: output is strictly clamped to [0, 100].
    """
    mvrv        = fetch_live_mvrv()
    mvrv_alpha  = calculate_mvrv_alpha_factor(mvrv)
    return max(0.0, min(100.0, base_manifold + mvrv_alpha))


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
        
        For CryptoQuant: uses miner outflow as large-holder proxy.
        Miner HIGH outflow = large sellers active (bearish).
        Miner LOW outflow  = hodl mode / accumulation (bullish).
        """
        
        if self.has_glassnode:
            return self._fetch_glassnode_metric(
                'distribution/balance_1k_10k',
                limit=days
            )
        
        if self.has_cryptoquant:
            try:
                # Use miner outflow as a real CQ-sourced large-holder proxy:
                # High outflow = miners dumping (bearish), Low outflow = hodling (bullish)
                miner_df = self.cryptoquant.get_miner_outflow(days)
                if miner_df is not None and not miner_df.empty:
                    # Invert direction so caller's whale_change logic works:
                    # low outflow → high "balance" proxy score (accumulation)
                    max_val = miner_df['value'].max() or 1
                    miner_df['value'] = max_val - miner_df['value']
                    print(f"✅ CryptoQuant exchange netflow (large-holder proxy) ({len(miner_df)} pts)")
                    return miner_df
            except Exception as e:
                print(f"⚠️ CryptoQuant miner outflow failed: {e}")
            # NOTE: Exchange reserve is NOT a valid proxy for whale balances — it measures
            # all BTC on exchanges, not individual large-holder behavior. Do NOT fall back.
            print("⚠️ Whale proxy unavailable (miner-flows/outflow returned no data). Scoring neutral.")
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
    
    def get_mvrv_ratio(self) -> Optional[float]:
        """
        Fetch live MVRV Ratio from CryptoQuant Professional API.
        Endpoint: /v1/btc/network-indicator/mvrv
        Response:  data['result']['data'][-1]['mvrv']
        Falls back to None gracefully — gene stays at 0 (neutral).
        """
        if not self.has_cryptoquant:
            return None
        # Bug fix: use self.cryptoquant_key (correct attribute name)
        # Bug fix: correct endpoint — market-indicator/mvrv-ratio (not network-indicator)
        return fetch_live_mvrv()  # reuse the standalone fetcher (reads same env key)

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
        
        # ── 4. MVRV Capitulation Gene (“Naor Insight”) ──────────────────────
        mvrv_ratio = self.get_mvrv_ratio()
        mvrv_alpha = calculate_mvrv_alpha_factor(mvrv_ratio)
        # Convert alpha (−15 to +25) to a 0–100 gene score for display
        # Neutral (alpha=0) → score=50; +25 → 100; −15 → 35
        scores['mvrv'] = max(0, min(100, 50 + mvrv_alpha * 2))

        # =====================================================================
        # COMPOSITE SCORE — Weighted Gene Pool
        # weights: netflow 35%, whale 35%, sopr 15%, mvrv 15%
        # =====================================================================
        weights = {'netflow': 0.35, 'whale': 0.35, 'sopr': 0.15, 'mvrv': 0.15}
        base_score = sum(scores[k] * weights[k] for k in scores)
        
        # Apply fear amplification — ONLY when whales are accumulating (base > 70)
        # Fear without diffusion = panic, not edge. Don't amplify noise.
        if base_score > 70:
            amplified_score = base_score * fear_amplifier
        else:
            amplified_score = base_score  # No amplification — whales are not buying
        
        # ── POLARITY GUARD (Sprint 10) ─────────────────────────────────
        # Positive netflow = coins entering exchanges = SELL PRESSURE.
        # It is physically impossible for the composite score to be
        # bullish (>70) while netflow screams distribution.
        # The netflow gene acts as a hard ceiling on the composite.
        netflow_gene = scores.get('netflow', 50)
        if netflow_gene <= 20:          # strong distribution
            amplified_score = min(amplified_score, 35)
        elif netflow_gene <= 40:        # mild distribution
            amplified_score = min(amplified_score, 55)
        # netflow_gene >= 60 → accumulation, no cap needed
        
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
        
        # has_real_data = True if we have a live API provider (not pure proxy)
        has_live_provider = bool(self.has_glassnode or self.has_cryptoquant)
        
        return {
            'diffusion_score': round(diffusion_score, 1),
            'base_score':      round(base_score, 1),
            'signal':          signal,
            'interpretation':  interpretation,
            'components':      scores,
            'mvrv_ratio':      mvrv_ratio,
            'mvrv_alpha':      round(mvrv_alpha, 1),
            'fear_greed':      fear_data,
            'supply_shock':    supply_shock_data,
            'conviction_boost': conviction_boost,
            'has_real_data':   has_live_provider,
            'data_source':     'CryptoQuant' if self.has_cryptoquant else 'Glassnode' if self.has_glassnode else 'CoinMetrics',
            'recent_netflow':  round(recent_netflow, 2),
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
