#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VAR Forecaster - Vector Autoregression for Multi-Asset Dynamics

Why VAR:
- Your bootstrap looks at BTC alone
- Reality: BTC/ETH/SOL influence each other
- VAR models these cross-asset dynamics explicitly

Model: VAR(p)
y_t = c + A1·y_{t-1} + A2·y_{t-2} + ... + Ap·y_{t-p} + ε_t

Where:
- y_t = [BTC_return, ETH_return, SOL_return, ...]
- A matrices capture cross-asset effects
- Example: ETH lagged return → BTC current return

Key insight: If ETH rallies → BTC often follows (or vice versa)
VAR captures these leads/lags automatically
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional
try:
    from statsmodels.tsa.api import VAR as VARModel
    VAR_AVAILABLE = True
except ImportError:
    VAR_AVAILABLE = False
    print("⚠️ Warning: statsmodels not installed. VAR will use fallback.")

from .ensemble import ForecastOutput


class VARForecaster:
    """
    Vector Autoregression for multi-asset forecasting
    
    Process:
    1. Collect returns for multiple assets (BTC, ETH, SOL, etc.)
    2. Fit VAR(p) model (auto-select optimal p)
    3. Forecast joint distribution of returns
    4. Simulate correlated return paths
    5. Convert to price paths
    """
    
    def __init__(self,
                 max_lags: int = 5,
                 ic: str = 'aic'):  # Information criterion: 'aic', 'bic', 'hqic'
        """
        Initialize VAR forecaster
        
        Args:
            max_lags: Maximum lag order to consider
            ic: Information criterion for lag selection
        """
        self.max_lags = max_lags
        self.ic = ic
        self.fitted_model = None
        self.asset_names = None
    
    def _prepare_data(self,
                     primary_close: pd.Series,
                     multi_asset: Dict[str, pd.Series]) -> pd.DataFrame:
        """
        Prepare multi-asset returns DataFrame
        
        Args:
            primary_close: Main asset (e.g., BTC)
            multi_asset: Dict of other assets {'ETH': series, 'SOL': series}
            
        Returns:
            DataFrame with aligned returns
        """
        # Combine all assets
        all_closes = {'PRIMARY': primary_close}
        all_closes.update(multi_asset)
        
        # Create DataFrame
        df = pd.DataFrame(all_closes)
        
        # Compute returns
        returns = df.pct_change().dropna()
        
        # Remove extreme outliers (can break VAR)
        for col in returns.columns:
            q01 = returns[col].quantile(0.01)
            q99 = returns[col].quantile(0.99)
            returns[col] = returns[col].clip(q01, q99)
        
        return returns
    
    def _fit_var(self, returns: pd.DataFrame) -> Optional[object]:
        """
        Fit VAR model with automatic lag selection
        
        Returns:
            Fitted VAR model results
        """
        if not VAR_AVAILABLE:
            return None
        
        try:
            # Build model
            model = VARModel(returns)
            
            # Select optimal lag order
            lag_order_results = model.select_order(maxlags=self.max_lags)
            optimal_lag = getattr(lag_order_results, self.ic)
            
            print(f"    VAR optimal lag: {optimal_lag} (by {self.ic.upper()})")
            
            # Fit with optimal lag
            fitted = model.fit(optimal_lag)
            
            return fitted
            
        except Exception as e:
            print(f"    VAR fit failed: {e}")
            return None
    
    def _simulate_var_paths(self,
                           fitted_model,
                           returns: pd.DataFrame,
                           horizon: int,
                           n_paths: int) -> Dict[str, np.ndarray]:
        """
        Simulate multivariate return paths using fitted VAR
        
        Returns:
            Dict of paths for each asset
        """
        if not VAR_AVAILABLE or fitted_model is None:
            raise ValueError("VAR simulation requires fitted model")
        
        # Get last observations (for initialization)
        last_obs = returns.tail(fitted_model.k_ar).values
        
        # Simulate paths
        simulated = fitted_model.simulate_paths(
            steps=horizon,
            nsimulations=n_paths,
            initial_values=last_obs
        )
        
        # simulated shape: (horizon, n_paths, n_assets)
        # Transpose to (n_assets, n_paths, horizon)
        simulated = simulated.transpose(2, 1, 0)
        
        # Create dict
        paths_dict = {}
        for i, asset in enumerate(returns.columns):
            paths_dict[asset] = simulated[i]  # (n_paths, horizon)
        
        return paths_dict
    
    def _fallback_correlated_paths(self,
                                   returns: pd.DataFrame,
                                   horizon: int,
                                   n_paths: int) -> Dict[str, np.ndarray]:
        """
        Fallback: Simulate with empirical correlation (no VAR)
        
        Uses Cholesky decomposition of correlation matrix
        """
        # Compute correlation matrix
        corr_matrix = returns.corr().values
        
        # Cholesky decomposition
        try:
            L = np.linalg.cholesky(corr_matrix)
        except np.linalg.LinAlgError:
            # If not positive definite, use identity
            print("    Correlation matrix not positive definite, using independence")
            L = np.eye(len(returns.columns))
        
        # Compute std for each asset
        stds = returns.std().values
        
        # Simulate uncorrelated shocks
        n_assets = len(returns.columns)
        uncorrelated = np.random.randn(n_paths, horizon, n_assets)
        
        # Apply correlation structure: z = L @ uncorrelated
        correlated = np.einsum('ij,klj->kli', L, uncorrelated)
        
        # Scale by std
        returns_sim = correlated * stds[None, None, :]
        
        # Create dict
        paths_dict = {}
        for i, asset in enumerate(returns.columns):
            paths_dict[asset] = returns_sim[:, :, i]  # (n_paths, horizon)
        
        return paths_dict
    
    def forecast(self,
                 primary_close: pd.Series,
                 multi_asset: Dict[str, pd.Series],
                 horizon: int = 48,
                 n_paths: int = 1000) -> ForecastOutput:
        """
        Generate VAR forecast
        
        Args:
            primary_close: Main asset price series (BTC)
            multi_asset: Other assets {'ETH': series, 'SOL': series, ...}
            horizon: Forecast horizon
            n_paths: Number of Monte Carlo paths
            
        Returns:
            ForecastOutput for primary asset
        """
        # Prepare returns
        returns = self._prepare_data(primary_close, multi_asset)
        self.asset_names = returns.columns.tolist()
        
        last_prices = {
            'PRIMARY': float(primary_close.iloc[-1]),
            **{k: float(v.iloc[-1]) for k, v in multi_asset.items()}
        }
        
        # Fit VAR
        if VAR_AVAILABLE:
            fitted = self._fit_var(returns.tail(500))  # Use last 500 obs
            
            if fitted is not None:
                self.fitted_model = fitted
                
                # Simulate with VAR
                try:
                    returns_paths = self._simulate_var_paths(
                        fitted, returns, horizon, n_paths
                    )
                    use_fallback = False
                except Exception as e:
                    print(f"    VAR simulation failed: {e}, using fallback")
                    use_fallback = True
            else:
                use_fallback = True
        else:
            use_fallback = True
        
        # Fallback if VAR unavailable
        if use_fallback:
            returns_paths = self._fallback_correlated_paths(
                returns, horizon, n_paths
            )
        
        # Convert returns → price paths for primary asset
        primary_returns = returns_paths['PRIMARY']  # (n_paths, horizon)
        
        paths = np.zeros((n_paths, horizon + 1))
        paths[:, 0] = last_prices['PRIMARY']
        
        for t in range(1, horizon + 1):
            paths[:, t] = paths[:, t-1] * (1 + primary_returns[:, t-1])
        
        # Compute percentiles
        p10 = np.percentile(paths, 10, axis=0)
        p50 = np.percentile(paths, 50, axis=0)
        p90 = np.percentile(paths, 90, axis=0)
        mean = np.mean(paths, axis=0)
        std = np.std(paths, axis=0)
        
        # Confidence: based on model fit quality
        if self.fitted_model is not None:
            # R-squared for primary equation
            r2 = self.fitted_model.rsquared['PRIMARY']
            confidence = float(r2)
        else:
            confidence = 0.4  # Lower confidence for fallback
        
        return ForecastOutput(
            p10=p10,
            p50=p50,
            p90=p90,
            mean=mean,
            std=std,
            paths=paths,
            model_name='VAR',
            confidence=confidence,
            metadata={
                'method': f'VAR({self.fitted_model.k_ar})' if self.fitted_model else 'Correlated_fallback',
                'n_assets': len(returns.columns),
                'assets': list(returns.columns),
                'n_obs_used': len(returns),
                'rsquared': self.fitted_model.rsquared if self.fitted_model else None
            }
        )


# =============================================================================
# VALIDATION - VAR vs Independent Forecasts
# =============================================================================

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    
    # Generate correlated asset data
    np.random.seed(42)
    n = 1000
    
    # Correlation structure
    rho = 0.7  # BTC-ETH correlation
    
    # Generate correlated returns
    btc_returns = np.random.randn(n) * 0.02
    eth_returns = rho * btc_returns + np.sqrt(1 - rho**2) * np.random.randn(n) * 0.025
    
    # Prices
    btc_prices = 50000 * np.cumprod(1 + btc_returns)
    eth_prices = 3000 * np.cumprod(1 + eth_returns)
    
    dates = pd.date_range('2023-01-01', periods=n, freq='1h')
    btc_close = pd.Series(btc_prices, index=dates)
    eth_close = pd.Series(eth_prices, index=dates)
    
    # Forecast with VAR
    forecaster = VARForecaster()
    forecast = forecaster.forecast(
        btc_close,
        {'ETH': eth_close},
        horizon=48,
        n_paths=500
    )
    
    # Plot
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Historical
    ax.plot(range(-100, 1), btc_close.tail(101).values, 'k-', label='BTC History', linewidth=2)
    
    # Forecast
    t = np.arange(0, 49)
    ax.plot(t, forecast.p50, 'g-', label='VAR P50 (BTC)', linewidth=2)
    ax.fill_between(t, forecast.p10, forecast.p90, alpha=0.3, color='green', label='VAR P10-P90')
    
    ax.set_title('VAR Multi-Asset Forecast (BTC conditioned on ETH)')
    ax.set_xlabel('Horizon (bars)')
    ax.set_ylabel('BTC Price')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('/home/claude/var_demo.png', dpi=150)
    print("✅ VAR demo saved to var_demo.png")
    
    # Print summary
    print("\n" + "="*60)
    print("VAR FORECAST SUMMARY")
    print("="*60)
    print(f"Model: {forecast.metadata['method']}")
    print(f"Assets: {forecast.metadata['assets']}")
    print(f"Confidence (R²): {forecast.confidence:.2%}")
    print(f"\nBTC 24h ahead:")
    print(f"  P10: ${forecast.p10[24]:,.2f}")
    print(f"  P50: ${forecast.p50[24]:,.2f}")
    print(f"  P90: ${forecast.p90[24]:,.2f}")
    if forecast.metadata['rsquared']:
        print(f"\nR-squared by equation:")
        for eq, r2 in forecast.metadata['rsquared'].items():
            print(f"  {eq}: {r2:.3f}")
    print("="*60)
