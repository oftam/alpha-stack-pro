#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚡ MODULE 3: VIOLENCE & CHAOS DETECTOR
Detects market regime transitions and volatility clustering

Integrates:
- Regime detection (from manifold_premium_layer)
- Volatility clustering
- Phase transition detection
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import numba

@numba.jit(nopython=True, fastmath=True, cache=True)
def _numba_calculate_true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    n = len(close)
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i-1])
        lc = abs(low[i] - close[i-1])
        tr[i] = max(hl, hc, lc)
    return tr

@numba.jit(nopython=True, fastmath=True, cache=True)
def _numba_calculate_violence_components(tr: np.ndarray, close: np.ndarray, lookback: int) -> tuple:
    n = len(close)
    if n < 20:
        return 0.0, 0.0, False

    recent_tr_mean = np.mean(tr[-5:])
    long_term_tr_mean = np.mean(tr[-lookback:])
    vol_clustering = recent_tr_mean > long_term_tr_mean * 1.5

    returns = np.zeros(20)
    for i in range(20):
        idx = n - 20 + i
        # Prevent wrapping around to the end of the array if idx == 0
        if idx > 0 and close[idx-1] > 0:
            returns[i] = (close[idx] - close[idx-1]) / close[idx-1]

    volatility = np.std(returns) * 100
    atr = np.mean(tr[-14:])
    price = close[-1]
    atr_ratio = (atr / price) * 100 if price > 0 else 0.0

    return atr_ratio, volatility, vol_clustering


class Regime(Enum):
    """Market regimes"""
    CALM = "CALM"
    VOLATILE = "VOLATILE"
    CHAOS = "CHAOS"
    BLOOD_IN_STREETS = "BLOOD_IN_STREETS"


@dataclass
class ChaosResult:
    """Chaos detection result"""
    regime: Regime
    violence_score: float  # 0-100
    volatility: float
    is_clustered: bool
    confidence: float


class ViolenceChaosDetector:
    """
    Detects market chaos and regime transitions
    
    Methods:
    - Volatility clustering (GARCH-like)
    - True Range analysis
    - Regime classification
    """
    
    def __init__(self, lookback: int = 20):
        self.lookback = lookback
        print("✅ Violence & Chaos detector initialized")
    
    def calculate_true_range(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate True Range
        
        TR = max(high - low, |high - prev_close|, |low - prev_close|)
        """
        if df.empty or 'high' not in df.columns or 'low' not in df.columns or 'close' not in df.columns:
            return pd.Series(dtype=float)
        
        # Use numba for fast execution
        tr_array = _numba_calculate_true_range(
            df['high'].values.astype(np.float64),
            df['low'].values.astype(np.float64),
            df['close'].values.astype(np.float64)
        )
        return pd.Series(tr_array, index=df.index)
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Average True Range"""
        tr = self.calculate_true_range(df)
        if tr.empty:
            return 0.0
        return tr.tail(period).mean()
    
    def detect_volatility_clustering(self, df: pd.DataFrame) -> bool:
        """
        Detect if volatility is clustering (high vol begets high vol)
        
        Simple method: Check if recent volatility > long-term average
        """
        if len(df) < self.lookback * 2:
            return False
        
        tr = self.calculate_true_range(df)
        if tr.empty:
            return False
        
        recent_vol = tr.tail(5).mean()
        long_term_vol = tr.tail(self.lookback).mean()
        
        return recent_vol > long_term_vol * 1.5
    
    def calculate_violence_score(self, df: pd.DataFrame) -> float:
        """
        Violence score: 0-100
        
        Based on:
        - ATR/Price ratio (higher = more violent)
        - Volatility clustering
        - Recent price swings
        """
        if df.empty or len(df) < 20 or 'high' not in df.columns or 'low' not in df.columns or 'close' not in df.columns:
            return 50.0

        # Use numba components to speed up
        tr_array = _numba_calculate_true_range(
            df['high'].values.astype(np.float64),
            df['low'].values.astype(np.float64),
            df['close'].values.astype(np.float64)
        )
        
        atr_ratio, volatility, is_clustered = _numba_calculate_violence_components(
            tr_array,
            df['close'].values.astype(np.float64),
            self.lookback
        )
        
        # Clustering bonus
        clustering_bonus = 20 if is_clustered else 0
        
        # Combine (normalize to 0-100)
        base_score = min(100, (atr_ratio * 10 + volatility * 2) * 2)
        violence_score = min(100, base_score + clustering_bonus)
        
        return violence_score
    
    def classify_regime(self, violence_score: float, fear_greed: Optional[int] = None) -> Regime:
        """
        Classify market regime
        
        Regimes:
        - CALM: violence < 30
        - VOLATILE: violence 30-60
        - CHAOS: violence 60-80
        - BLOOD_IN_STREETS: violence > 80 + extreme fear
        """
        if violence_score < 30:
            return Regime.CALM
        elif violence_score < 60:
            return Regime.VOLATILE
        elif violence_score < 80:
            return Regime.CHAOS
        else:
            # Check for blood in streets (extreme violence + extreme fear)
            if fear_greed is not None and fear_greed < 20:
                return Regime.BLOOD_IN_STREETS
            return Regime.CHAOS
    
    def analyze(self, 
                df: pd.DataFrame,
                fear_greed: Optional[int] = None) -> ChaosResult:
        """
        Full chaos analysis
        
        Returns:
            ChaosResult with regime and scores
        """
        if df.empty:
            return ChaosResult(
                regime=Regime.CALM,
                violence_score=50.0,
                volatility=0.0,
                is_clustered=False,
                confidence=0.5
            )
        
        # Calculate metrics
        violence_score = self.calculate_violence_score(df)
        regime = self.classify_regime(violence_score, fear_greed)
        is_clustered = self.detect_volatility_clustering(df)
        
        # Volatility (annualized)
        returns = df['close'].pct_change().tail(20)
        volatility = returns.std() * np.sqrt(365) * 100 if len(returns) > 1 else 0.0
        
        # Confidence (based on data quality)
        confidence = min(1.0, len(df) / 100)
        
        return ChaosResult(
            regime=regime,
            violence_score=violence_score,
            volatility=volatility,
            is_clustered=is_clustered,
            confidence=confidence
        )


# Example usage
if __name__ == '__main__':
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='1H')
    
    # Simulate volatile market
    close = 100 + np.cumsum(np.random.randn(100) * 2)
    high = close + np.abs(np.random.randn(100))
    low = close - np.abs(np.random.randn(100))
    
    df = pd.DataFrame({
        'close': close,
        'high': high,
        'low': low,
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates)
    
    # Test
    detector = ViolenceChaosDetector()
    result = detector.analyze(df, fear_greed=25)
    
    print(f"\n⚡ Chaos Analysis:")
    print(f"  Regime: {result.regime.value}")
    print(f"  Violence Score: {result.violence_score:.1f}/100")
    print(f"  Volatility: {result.volatility:.1f}%")
    print(f"  Clustering: {result.is_clustered}")
    print(f"  Confidence: {result.confidence:.1%}")
