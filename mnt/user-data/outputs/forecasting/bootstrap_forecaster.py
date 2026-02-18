#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Bootstrap Forecaster - Regime-Conditioned Path Sampling

This is your DUDU overlay, enhanced for ensemble integration:
- Better regime detection
- Adaptive window selection
- Confidence scoring
- Standard ForecastOutput format
"""

import numpy as np
import pandas as pd
from typing import Optional, List, Union
from .ensemble import ForecastOutput


class BootstrapForecaster:
    """
    Non-parametric forecaster using historical path resampling
    
    Your original DUDU overlay logic, enhanced:
    1. Sample historical return windows matching current regime
    2. Build forward price paths from these samples
    3. No distributional assumptions (non-parametric)
    
    Advantages:
    - Captures real market behavior (tail events, skew)
    - No assumptions about distribution shape
    - Regime-aware (bull vs bear vs ranging)
    
    Limitations:
    - Limited by historical data (can't forecast unprecedented events)
    - Assumes future ≈ similar past regimes
    """
    
    def __init__(self,
                 min_windows: int = 20,
                 lookback: int = 1500):
        """
        Initialize bootstrap forecaster
        
        Args:
            min_windows: Minimum matching windows required
            lookback: How far back to search for matching regimes
        """
        self.min_windows = min_windows
        self.lookback = lookback
    
    def _compute_regime_features(self, 
                                 returns: pd.Series,
                                 window_size: int = 30) -> pd.DataFrame:
        """
        Compute rolling regime features
        
        Features:
        - vol: Volatility (std of returns)
        - trend: Price momentum (cumulative return)
        - autocorr: Return persistence (lag-1 autocorr)
        
        These define what "similar regime" means
        """
        features = pd.DataFrame(index=returns.index)
        
        # Volatility
        features['vol'] = returns.rolling(window_size).std()
        
        # Trend (cumulative return over window)
        features['trend'] = returns.rolling(window_size).apply(
            lambda x: np.prod(1 + x) - 1
        )
        
        # Autocorrelation (momentum persistence)
        features['autocorr'] = returns.rolling(window_size).apply(
            lambda x: x.autocorr(lag=1) if len(x) > 1 else 0
        )
        
        return features.fillna(0)
    
    def _find_matching_windows(self,
                              features: pd.DataFrame,
                              current_features: dict,
                              horizon: int,
                              tolerance: float = 0.3) -> List[int]:
        """
        Find historical windows matching current regime
        
        Matching criteria:
        - Similar volatility (within tolerance)
        - Similar trend direction
        - Similar autocorrelation
        
        Returns:
            List of start indices for matching windows
        """
        # Valid window starts (need horizon bars ahead)
        valid_starts = range(len(features) - horizon - 1)
        
        matches = []
        
        for start in valid_starts:
            window_features = features.iloc[start]
            
            # Check each feature within tolerance
            vol_match = abs(window_features['vol'] - current_features['vol']) / (current_features['vol'] + 1e-9) < tolerance
            trend_match = np.sign(window_features['trend']) == np.sign(current_features['trend'])
            autocorr_match = abs(window_features['autocorr'] - current_features['autocorr']) < tolerance
            
            if vol_match and trend_match and autocorr_match:
                matches.append(start)
        
        return matches
    
    def _simple_regime_match(self,
                            returns: pd.Series,
                            regime: str,
                            horizon: int) -> List[int]:
        """
        Simple regime matching (fallback if feature-based fails)
        
        Uses string regime labels:
        - HIGH_VOL: vol > 90th percentile
        - LOW_VOL: vol < 10th percentile
        - TRENDING: |trend| > threshold
        - RANGING: |trend| < threshold
        """
        vol = returns.rolling(30).std()
        trend = returns.rolling(30).apply(lambda x: np.prod(1 + x) - 1)
        
        vol_p90 = vol.quantile(0.9)
        vol_p10 = vol.quantile(0.1)
        
        valid_starts = range(len(returns) - horizon - 1)
        matches = []
        
        for start in valid_starts:
            v = vol.iloc[start]
            t = trend.iloc[start]
            
            if regime == 'HIGH_VOL' and v > vol_p90:
                matches.append(start)
            elif regime == 'LOW_VOL' and v < vol_p10:
                matches.append(start)
            elif regime == 'TRENDING' and abs(t) > 0.05:
                matches.append(start)
            elif regime == 'RANGING' and abs(t) < 0.05:
                matches.append(start)
        
        return matches
    
    def forecast(self,
                 close: pd.Series,
                 horizon: int = 48,
                 n_paths: int = 1000,
                 regime: Optional[str] = None) -> ForecastOutput:
        """
        Generate bootstrap forecast
        
        Args:
            close: Price series
            horizon: Forecast horizon
            n_paths: Number of paths to sample
            regime: Regime label (or None for all history)
            
        Returns:
            ForecastOutput with sampled paths
        """
        # Compute returns
        returns = close.pct_change().dropna()
        last_price = float(close.iloc[-1])
        
        # Limit lookback
        returns = returns.tail(self.lookback)
        
        # Find matching windows
        if regime and regime != 'DEFAULT':
            # Try feature-based matching first
            features = self._compute_regime_features(returns)
            current_features = {
                'vol': features['vol'].iloc[-1],
                'trend': features['trend'].iloc[-1],
                'autocorr': features['autocorr'].iloc[-1]
            }
            
            matches = self._find_matching_windows(
                features, current_features, horizon, tolerance=0.3
            )
            
            # Fallback to simple regime if too few matches
            if len(matches) < self.min_windows:
                matches = self._simple_regime_match(returns, regime, horizon)
        else:
            # Use all windows
            matches = list(range(len(returns) - horizon - 1))
        
        # Final fallback: use all data if still too few
        if len(matches) < self.min_windows:
            matches = list(range(len(returns) - horizon - 1))
            print(f"    Bootstrap: Using all {len(matches)} windows (regime filter too strict)")
        else:
            print(f"    Bootstrap: Found {len(matches)} matching windows")
        
        # Sample windows
        rng = np.random.default_rng(42)
        chosen = rng.choice(matches, size=n_paths, replace=True)
        
        # Build paths
        paths = np.zeros((n_paths, horizon + 1))
        paths[:, 0] = last_price
        
        returns_arr = returns.values
        
        for i, start in enumerate(chosen):
            # Get return window
            window_returns = returns_arr[start:start + horizon]
            
            # Build price path
            for t in range(1, horizon + 1):
                if t - 1 < len(window_returns):
                    paths[i, t] = paths[i, t-1] * (1 + window_returns[t-1])
                else:
                    paths[i, t] = paths[i, t-1]  # Flat if ran out
        
        # Compute percentiles
        p10 = np.percentile(paths, 10, axis=0)
        p50 = np.percentile(paths, 50, axis=0)
        p90 = np.percentile(paths, 90, axis=0)
        mean = np.mean(paths, axis=0)
        std = np.std(paths, axis=0)
        
        # Confidence based on number of matching windows
        # More matches = higher confidence (more data to learn from)
        confidence = min(1.0, len(matches) / 100)
        
        return ForecastOutput(
            p10=p10,
            p50=p50,
            p90=p90,
            mean=mean,
            std=std,
            paths=paths,
            model_name='Bootstrap',
            confidence=confidence,
            metadata={
                'method': 'Regime-conditioned bootstrap',
                'regime': regime or 'ALL',
                'n_matching_windows': len(matches),
                'n_total_windows': len(returns) - horizon - 1,
                'match_rate': len(matches) / max(1, len(returns) - horizon - 1)
            }
        )


# =============================================================================
# VALIDATION - Bootstrap vs Parametric
# =============================================================================

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    
    # Generate data with regime changes
    np.random.seed(42)
    
    # Regime 1: Low vol
    r1 = np.random.randn(300) * 0.01
    
    # Regime 2: High vol
    r2 = np.random.randn(300) * 0.04
    
    # Regime 3: Trending
    r3 = np.random.randn(300) * 0.02 + 0.003  # Positive drift
    
    returns = np.concatenate([r1, r2, r3])
    prices = 50000 * np.cumprod(1 + returns)
    
    dates = pd.date_range('2023-01-01', periods=len(returns), freq='1h')
    close = pd.Series(prices, index=dates)
    
    # Forecast with bootstrap (we're in trending regime now)
    forecaster = BootstrapForecaster()
    forecast = forecaster.forecast(close, horizon=48, n_paths=500, regime='TRENDING')
    
    # Plot
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Historical
    ax.plot(range(-100, 1), close.tail(101).values, 'k-', label='History', linewidth=2)
    
    # Show regime changes
    ax.axvspan(-100, -100 + 300, alpha=0.1, color='blue', label='Low Vol')
    ax.axvspan(-100 + 300, -100 + 600, alpha=0.1, color='red', label='High Vol')
    ax.axvspan(-100 + 600, 0, alpha=0.1, color='green', label='Trending')
    
    # Forecast
    t = np.arange(0, 49)
    ax.plot(t, forecast.p50, 'purple', label='Bootstrap P50', linewidth=2, linestyle='--')
    ax.fill_between(t, forecast.p10, forecast.p90, alpha=0.3, color='purple', label='Bootstrap P10-P90')
    
    ax.set_title(f"Bootstrap Forecast (Regime: {forecast.metadata['regime']})")
    ax.set_xlabel('Horizon (bars)')
    ax.set_ylabel('Price')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('/home/claude/bootstrap_demo.png', dpi=150)
    print("✅ Bootstrap demo saved to bootstrap_demo.png")
    
    # Print summary
    print("\n" + "="*60)
    print("BOOTSTRAP FORECAST SUMMARY")
    print("="*60)
    print(f"Method: {forecast.metadata['method']}")
    print(f"Regime: {forecast.metadata['regime']}")
    print(f"Matching windows: {forecast.metadata['n_matching_windows']} / {forecast.metadata['n_total_windows']}")
    print(f"Match rate: {forecast.metadata['match_rate']:.1%}")
    print(f"Confidence: {forecast.confidence:.2%}")
    print(f"\n24h ahead:")
    print(f"  P10: ${forecast.p10[24]:,.2f}")
    print(f"  P50: ${forecast.p50[24]:,.2f}")
    print(f"  P90: ${forecast.p90[24]:,.2f}")
    print("="*60)
