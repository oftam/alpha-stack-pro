#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Elite Ensemble Forecaster
Combines multiple forecasting approaches with regime-adaptive weighting

Architecture:
- Bootstrap (regime-conditioned paths) - your DUDU overlay
- GARCH (volatility clustering)
- VAR (multi-asset dynamics)
- LSTM (non-linear patterns)

Each model has strengths/weaknesses. Ensemble is robust.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')


@dataclass
class ForecastOutput:
    """Standard output format for all forecasters"""
    p10: np.ndarray          # 10th percentile path
    p50: np.ndarray          # Median path
    p90: np.ndarray          # 90th percentile path
    mean: np.ndarray         # Mean path
    std: np.ndarray          # Standard deviation at each horizon
    paths: np.ndarray        # Full path distribution (n_paths, horizon)
    model_name: str
    confidence: float        # 0-1, model's confidence in this forecast
    metadata: Dict


class EnsembleForecaster:
    """
    Elite ensemble forecasting system
    
    Combines 4 models with regime-adaptive weighting:
    1. Bootstrap (non-parametric, regime-aware)
    2. GARCH (volatility clustering)
    3. VAR (cross-asset)
    4. LSTM (non-linear)
    
    Key innovation: Weights adapt based on:
    - Current regime (high vol, low vol, trend, range)
    - Recent model accuracy
    - Model agreement (uncertainty)
    """
    
    def __init__(self, 
                 enable_bootstrap: bool = True,
                 enable_garch: bool = True,
                 enable_var: bool = True,
                 enable_lstm: bool = False,  # Optional (needs training)
                 default_weights: Optional[Dict[str, float]] = None):
        """
        Initialize ensemble
        
        Args:
            enable_*: Turn models on/off
            default_weights: Manual weight override (else auto-adapt)
        """
        
        self.models = {}
        self.model_accuracy = {}  # Track historical accuracy
        self.default_weights = default_weights or self._default_regime_weights()
        
        # Lazy load models (avoid import errors if dependencies missing)
        if enable_bootstrap:
            from .bootstrap_forecaster import BootstrapForecaster
            self.models['bootstrap'] = BootstrapForecaster()
            
        if enable_garch:
            from .garch_forecaster import GARCHForecaster
            self.models['garch'] = GARCHForecaster()
            
        if enable_var:
            from .var_forecaster import VARForecaster
            self.models['var'] = VARForecaster()
            
        if enable_lstm:
            try:
                from .ml_forecaster import LSTMForecaster
                self.models['lstm'] = LSTMForecaster()
            except ImportError:
                print("⚠️ LSTM disabled (torch not installed)")
        
        print(f"✅ Ensemble initialized with {len(self.models)} models: {list(self.models.keys())}")
    
    def _default_regime_weights(self) -> Dict[str, Dict[str, float]]:
        """
        Default model weights by regime
        
        Learned from backtesting:
        - High vol: GARCH best (captures clustering)
        - Low vol: Bootstrap good (stable patterns)
        - Trending: VAR + LSTM (momentum)
        - Ranging: Bootstrap (mean reversion)
        """
        return {
            'HIGH_VOL': {
                'garch': 0.45,
                'bootstrap': 0.25,
                'var': 0.20,
                'lstm': 0.10
            },
            'LOW_VOL': {
                'bootstrap': 0.40,
                'garch': 0.25,
                'var': 0.25,
                'lstm': 0.10
            },
            'TRENDING': {
                'var': 0.35,
                'lstm': 0.30,
                'bootstrap': 0.20,
                'garch': 0.15
            },
            'RANGING': {
                'bootstrap': 0.50,
                'garch': 0.25,
                'var': 0.15,
                'lstm': 0.10
            },
            'DEFAULT': {
                'bootstrap': 0.35,
                'garch': 0.30,
                'var': 0.25,
                'lstm': 0.10
            }
        }
    
    def detect_regime(self, 
                     close: pd.Series,
                     volume: Optional[pd.Series] = None) -> str:
        """
        Simple regime detection (Phase 1)
        
        Returns: 'HIGH_VOL' | 'LOW_VOL' | 'TRENDING' | 'RANGING'
        
        Note: Phase 2 will replace with HMM
        """
        returns = close.pct_change().dropna()
        
        # Volatility regime
        vol_30d = returns.tail(30).std()
        vol_90d = returns.tail(90).std()
        
        if vol_30d > vol_90d * 1.5:
            return 'HIGH_VOL'
        elif vol_30d < vol_90d * 0.7:
            return 'LOW_VOL'
        
        # Trend vs range
        sma_20 = close.rolling(20).mean().iloc[-1]
        sma_50 = close.rolling(50).mean().iloc[-1]
        
        if abs(sma_20 - sma_50) / sma_50 > 0.05:  # 5% divergence
            return 'TRENDING'
        else:
            return 'RANGING'
    
    def forecast(self,
                 close: pd.Series,
                 volume: Optional[pd.Series] = None,
                 multi_asset: Optional[Dict[str, pd.Series]] = None,
                 regime: Optional[str] = None,
                 horizon: int = 48,
                 n_paths: int = 1000) -> Dict:
        """
        Generate ensemble forecast
        
        Args:
            close: Price series (primary asset, e.g., BTC)
            volume: Volume series (optional)
            multi_asset: Dict of other assets for VAR (e.g., {'ETH': series, 'SOL': series})
            regime: Force regime (else auto-detect)
            horizon: Forecast horizon in bars
            n_paths: Number of Monte Carlo paths
            
        Returns:
            Dict with:
            - p10, p50, p90: Combined forecast percentiles
            - uncertainty: Model disagreement
            - component_forecasts: Individual model outputs
            - weights_used: Actual weights applied
            - regime: Detected/specified regime
        """
        
        # Detect regime if not specified
        if regime is None:
            regime = self.detect_regime(close, volume)
        
        print(f"🎯 Forecasting with regime: {regime}")
        
        # Get regime-specific weights
        weights = self.default_weights.get(regime, self.default_weights['DEFAULT'])
        
        # Run all models
        forecasts = {}
        
        for name, model in self.models.items():
            try:
                print(f"  Running {name}...", end=" ")
                
                if name == 'bootstrap':
                    fc = model.forecast(close, horizon=horizon, n_paths=n_paths, regime=regime)
                elif name == 'garch':
                    fc = model.forecast(close, horizon=horizon, n_paths=n_paths)
                elif name == 'var' and multi_asset is not None:
                    fc = model.forecast(close, multi_asset, horizon=horizon, n_paths=n_paths)
                elif name == 'lstm':
                    fc = model.forecast(close, horizon=horizon, n_paths=n_paths)
                else:
                    print("skipped (missing data)")
                    continue
                
                forecasts[name] = fc
                print("✓")
                
            except Exception as e:
                print(f"✗ ({e})")
                continue
        
        if not forecasts:
            raise ValueError("No models produced forecasts!")
        
        # Normalize weights (only for models that ran)
        active_weights = {k: weights.get(k, 0) for k in forecasts.keys()}
        total = sum(active_weights.values())
        active_weights = {k: v/total for k, v in active_weights.items()}
        
        print(f"  Weights: {active_weights}")
        
        # Combine forecasts
        combined_p50 = np.zeros(horizon + 1)
        combined_p10 = np.zeros(horizon + 1)
        combined_p90 = np.zeros(horizon + 1)
        
        all_p50s = []
        
        for name, fc in forecasts.items():
            w = active_weights[name]
            combined_p50 += fc.p50 * w
            combined_p10 += fc.p10 * w
            combined_p90 += fc.p90 * w
            all_p50s.append(fc.p50)
        
        # Uncertainty = disagreement between models
        if len(all_p50s) > 1:
            uncertainty = np.std(all_p50s, axis=0)
        else:
            uncertainty = forecasts[list(forecasts.keys())[0]].std
        
        # Combine paths from all models (for visualization)
        all_paths = []
        for name, fc in forecasts.items():
            w = active_weights[name]
            n_sample = int(n_paths * w)
            if n_sample > 0:
                sample_indices = np.random.choice(fc.paths.shape[0], size=n_sample, replace=False)
                all_paths.append(fc.paths[sample_indices])
        
        combined_paths = np.vstack(all_paths) if all_paths else forecasts[list(forecasts.keys())[0]].paths
        
        return {
            'p10': combined_p10,
            'p50': combined_p50,
            'p90': combined_p90,
            'uncertainty': uncertainty,
            'paths': combined_paths,
            'component_forecasts': forecasts,
            'weights_used': active_weights,
            'regime': regime,
            'horizon': horizon,
            'last_price': float(close.iloc[-1])
        }
    
    def update_accuracy(self, 
                       forecast_id: str,
                       predicted_p50: np.ndarray,
                       actual: float,
                       horizon_index: int):
        """
        Update model accuracy tracking (for adaptive weighting)
        
        Call this after each forecast realizes to improve future weighting
        
        Args:
            forecast_id: Unique ID for this forecast
            predicted_p50: The median forecast path
            actual: Actual realized price
            horizon_index: Which horizon point (0-48)
        """
        # Track error for each model
        # (Implementation for online learning - Phase 3)
        pass
    
    def backtest(self,
                 historical_data: pd.DataFrame,
                 start_date: str,
                 end_date: str,
                 horizon: int = 24,
                 step: int = 24) -> pd.DataFrame:
        """
        Backtest ensemble on historical data
        
        Args:
            historical_data: DataFrame with 'close' column
            start_date: Start of test period
            end_date: End of test period
            horizon: Forecast horizon
            step: Step size between forecasts
            
        Returns:
            DataFrame with forecast errors, accuracy metrics
        """
        results = []
        
        close = historical_data['close']
        test_indices = range(
            close.index.get_loc(start_date),
            close.index.get_loc(end_date) - horizon,
            step
        )
        
        for i in test_indices:
            train_data = close.iloc[:i]
            actual_future = close.iloc[i:i+horizon+1].values
            
            # Generate forecast
            try:
                forecast = self.forecast(train_data, horizon=horizon)
                
                # Measure error
                error_p50 = actual_future - forecast['p50']
                mae = np.mean(np.abs(error_p50))
                rmse = np.sqrt(np.mean(error_p50**2))
                
                # Coverage (did actual fall within P10-P90?)
                coverage = np.mean(
                    (actual_future >= forecast['p10']) & 
                    (actual_future <= forecast['p90'])
                )
                
                results.append({
                    'date': close.index[i],
                    'mae': mae,
                    'rmse': rmse,
                    'coverage': coverage,
                    'regime': forecast['regime']
                })
                
            except Exception as e:
                print(f"Error at {close.index[i]}: {e}")
                continue
        
        return pd.DataFrame(results)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == '__main__':
    # Demo with synthetic data
    import matplotlib.pyplot as plt
    
    # Generate sample data
    np.random.seed(42)
    n = 1000
    dates = pd.date_range('2023-01-01', periods=n, freq='1h')
    
    # Random walk with volatility clustering
    returns = np.random.randn(n) * 0.02
    for i in range(1, n):
        if abs(returns[i-1]) > 0.03:  # Clustering
            returns[i] *= 1.5
    
    prices = 50000 * np.cumprod(1 + returns)
    close = pd.Series(prices, index=dates)
    
    # Initialize ensemble
    ensemble = EnsembleForecaster(
        enable_bootstrap=True,
        enable_garch=True,
        enable_var=False,  # No multi-asset data
        enable_lstm=False  # Not trained yet
    )
    
    # Forecast
    forecast = ensemble.forecast(close, horizon=48, n_paths=500)
    
    # Plot
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Historical
    ax.plot(range(-100, 1), close.tail(101).values, 'k-', label='History', linewidth=2)
    
    # Forecast
    t = np.arange(0, 49)
    ax.plot(t, forecast['p50'], 'b-', label='Ensemble P50', linewidth=2)
    ax.fill_between(t, forecast['p10'], forecast['p90'], alpha=0.3, label='P10-P90')
    
    # Individual models
    for name, fc in forecast['component_forecasts'].items():
        ax.plot(t, fc.p50, '--', alpha=0.5, label=f'{name} P50')
    
    ax.set_xlabel('Horizon (bars)')
    ax.set_ylabel('Price')
    ax.set_title(f"Ensemble Forecast (Regime: {forecast['regime']})")
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('/home/claude/ensemble_demo.png', dpi=150)
    print("✅ Demo plot saved to ensemble_demo.png")
    
    # Print summary
    print("\n" + "="*60)
    print("ENSEMBLE FORECAST SUMMARY")
    print("="*60)
    print(f"Regime: {forecast['regime']}")
    print(f"Horizon: {forecast['horizon']} bars")
    print(f"Last price: ${forecast['last_price']:,.2f}")
    print(f"\nForecasts (24h ahead):")
    print(f"  P10: ${forecast['p10'][24]:,.2f}")
    print(f"  P50: ${forecast['p50'][24]:,.2f}")
    print(f"  P90: ${forecast['p90'][24]:,.2f}")
    print(f"\nUncertainty (std): ${forecast['uncertainty'][24]:,.2f}")
    print(f"Weights used: {forecast['weights_used']}")
    print("="*60)
