#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GARCH Forecaster - Volatility Clustering
Captures: Large moves cluster in time (GARCH effect)

Why GARCH:
- Your bootstrap assumes constant volatility
- Reality: Vol changes over time and clusters
- After big move → expect more big moves (short term)
- GARCH models this explicitly

Model: GARCH(1,1) - industry standard
σ²_t = ω + α·ε²_{t-1} + β·σ²_{t-1}

Where:
- σ²_t = forecasted variance
- ε²_{t-1} = last period's squared return (shock)
- α = how much recent shock matters (0.05-0.15 typical)
- β = how much past variance persists (0.80-0.95 typical)
"""

import numpy as np
import pandas as pd
from typing import Optional
try:
    from arch import arch_model
    ARCH_AVAILABLE = True
except ImportError:
    ARCH_AVAILABLE = False
    print("⚠️ Warning: arch library not installed. GARCH will use fallback.")

from .ensemble import ForecastOutput


class GARCHForecaster:
    """
    GARCH(1,1) volatility forecaster with Monte Carlo simulation
    
    Process:
    1. Fit GARCH model to historical returns
    2. Forecast volatility path (σ_t for t=1..horizon)
    3. Simulate return paths using forecasted vol
    4. Convert returns → price paths
    """
    
    def __init__(self,
                 p: int = 1,     # GARCH lag order
                 q: int = 1,     # ARCH lag order
                 mean_model: str = 'Constant',  # 'Constant' | 'Zero' | 'AR'
                 vol_model: str = 'GARCH'):     # 'GARCH' | 'EGARCH' | 'GJR-GARCH'
        """
        Initialize GARCH forecaster
        
        Args:
            p: GARCH term (persistence)
            q: ARCH term (shock response)
            mean_model: Mean return model
            vol_model: Volatility model type
        """
        self.p = p
        self.q = q
        self.mean_model = mean_model
        self.vol_model = vol_model
        self.fitted_model = None
    
    def _fit_garch(self, returns: pd.Series) -> Optional[object]:
        """
        Fit GARCH model to returns
        
        Returns:
            Fitted model object (or None if failed)
        """
        if not ARCH_AVAILABLE:
            return None
        
        try:
            # Remove extreme outliers (can break GARCH)
            returns_clean = returns.copy()
            returns_clean = returns_clean.clip(
                lower=returns_clean.quantile(0.01),
                upper=returns_clean.quantile(0.99)
            )
            
            # Scale to percentages (improves numerical stability)
            returns_pct = returns_clean * 100
            
            # Build and fit model
            model = arch_model(
                returns_pct,
                mean=self.mean_model,
                vol=self.vol_model,
                p=self.p,
                q=self.q,
                rescale=False
            )
            
            fitted = model.fit(disp='off', show_warning=False)
            
            return fitted
            
        except Exception as e:
            print(f"GARCH fit failed: {e}")
            return None
    
    def _fallback_ewma_vol(self, returns: pd.Series, span: int = 20) -> float:
        """
        Fallback: EWMA volatility if GARCH fails
        
        EWMA = Exponentially Weighted Moving Average
        Recent returns weighted more than old ones
        """
        return returns.ewm(span=span).std().iloc[-1]
    
    def _simulate_paths_with_garch(self,
                                   fitted_model,
                                   last_price: float,
                                   horizon: int,
                                   n_paths: int) -> np.ndarray:
        """
        Simulate price paths using GARCH volatility forecast
        
        Steps:
        1. Forecast σ_t for t=1..horizon
        2. Draw random returns: r_t ~ N(μ, σ_t)
        3. Build paths: P_t = P_{t-1} * (1 + r_t)
        """
        if not ARCH_AVAILABLE or fitted_model is None:
            raise ValueError("GARCH simulation requires fitted model")
        
        # Forecast volatility
        vol_forecast = fitted_model.forecast(horizon=horizon, method='simulation', simulations=n_paths)
        
        # Extract forecasted variance
        variance = vol_forecast.variance.values  # Shape: (n_paths, horizon)
        
        # Convert back from percentage scale
        sigma = np.sqrt(variance) / 100
        
        # Get mean return from model
        mu = fitted_model.params.get('mu', 0) / 100  # Also scale back
        
        # Simulate returns
        random_shocks = np.random.randn(n_paths, horizon)
        returns = mu + sigma * random_shocks
        
        # Convert to price paths
        paths = np.zeros((n_paths, horizon + 1))
        paths[:, 0] = last_price
        
        for t in range(1, horizon + 1):
            paths[:, t] = paths[:, t-1] * (1 + returns[:, t-1])
        
        return paths
    
    def _simulate_paths_fallback(self,
                                 returns: pd.Series,
                                 last_price: float,
                                 horizon: int,
                                 n_paths: int) -> np.ndarray:
        """
        Fallback simulation without arch library
        
        Uses rolling volatility with mean reversion
        """
        # Estimate current vol
        vol_current = self._fallback_ewma_vol(returns, span=20)
        vol_long_term = returns.std()
        
        # Mean reversion parameter (vol reverts to long-term)
        kappa = 0.1  # Speed of reversion
        
        # Simulate vol path (Ornstein-Uhlenbeck process)
        vol_paths = np.zeros((n_paths, horizon))
        vol_paths[:, 0] = vol_current
        
        vol_vol = vol_current * 0.3  # Volatility of volatility
        
        for t in range(1, horizon):
            dW = np.random.randn(n_paths) * np.sqrt(1)
            vol_paths[:, t] = (
                vol_paths[:, t-1] + 
                kappa * (vol_long_term - vol_paths[:, t-1]) +
                vol_vol * dW
            )
            vol_paths[:, t] = np.maximum(vol_paths[:, t], 0.001)  # Floor
        
        # Simulate returns with time-varying vol
        mu = returns.mean()
        random_shocks = np.random.randn(n_paths, horizon)
        returns_sim = mu + vol_paths * random_shocks
        
        # Convert to price paths
        paths = np.zeros((n_paths, horizon + 1))
        paths[:, 0] = last_price
        
        for t in range(1, horizon + 1):
            paths[:, t] = paths[:, t-1] * (1 + returns_sim[:, t-1])
        
        return paths
    
    def forecast(self,
                 close: pd.Series,
                 horizon: int = 48,
                 n_paths: int = 1000) -> ForecastOutput:
        """
        Generate GARCH forecast
        
        Args:
            close: Price series
            horizon: Forecast horizon
            n_paths: Number of Monte Carlo paths
            
        Returns:
            ForecastOutput with paths and percentiles
        """
        # Compute returns
        returns = close.pct_change().dropna()
        last_price = float(close.iloc[-1])
        
        # Fit GARCH
        if ARCH_AVAILABLE:
            fitted = self._fit_garch(returns.tail(500))  # Use last 500 obs
            
            if fitted is not None:
                self.fitted_model = fitted
                
                # Simulate with GARCH
                try:
                    paths = self._simulate_paths_with_garch(
                        fitted, last_price, horizon, n_paths
                    )
                    use_fallback = False
                except Exception as e:
                    print(f"GARCH simulation failed: {e}, using fallback")
                    use_fallback = True
            else:
                use_fallback = True
        else:
            use_fallback = True
        
        # Fallback if GARCH unavailable or failed
        if use_fallback:
            paths = self._simulate_paths_fallback(
                returns, last_price, horizon, n_paths
            )
        
        # Compute percentiles
        p10 = np.percentile(paths, 10, axis=0)
        p50 = np.percentile(paths, 50, axis=0)
        p90 = np.percentile(paths, 90, axis=0)
        mean = np.mean(paths, axis=0)
        std = np.std(paths, axis=0)
        
        # Confidence: how well GARCH fits
        if self.fitted_model is not None:
            # Use AIC as confidence proxy (lower = better fit)
            aic = self.fitted_model.aic
            confidence = 1.0 / (1.0 + aic / 1000)  # Normalize
        else:
            confidence = 0.5  # Medium confidence for fallback
        
        return ForecastOutput(
            p10=p10,
            p50=p50,
            p90=p90,
            mean=mean,
            std=std,
            paths=paths,
            model_name='GARCH',
            confidence=confidence,
            metadata={
                'method': 'GARCH(1,1)' if self.fitted_model else 'EWMA_fallback',
                'n_obs_used': len(returns),
                'current_vol': float(returns.tail(20).std()),
                'forecast_vol_24h': float(std[24]) / last_price if horizon >= 24 else None
            }
        )


# =============================================================================
# VALIDATION - Compare GARCH vs Simple Bootstrap
# =============================================================================

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    
    # Generate data with volatility clustering
    np.random.seed(42)
    n = 1000
    returns = np.zeros(n)
    vol = np.zeros(n)
    vol[0] = 0.02
    
    # GARCH data generating process
    omega = 0.00001
    alpha = 0.10  # Shock response
    beta = 0.85   # Persistence
    
    for t in range(1, n):
        # GARCH(1,1) volatility
        vol[t] = np.sqrt(omega + alpha * returns[t-1]**2 + beta * vol[t-1]**2)
        # Return with time-varying vol
        returns[t] = vol[t] * np.random.randn()
    
    prices = 50000 * np.cumprod(1 + returns)
    dates = pd.date_range('2023-01-01', periods=n, freq='1h')
    close = pd.Series(prices, index=dates)
    
    # Forecast with GARCH
    forecaster = GARCHForecaster()
    forecast = forecaster.forecast(close, horizon=48, n_paths=500)
    
    # Plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Price forecast
    ax1.plot(range(-100, 1), close.tail(101).values, 'k-', label='History', linewidth=2)
    t = np.arange(0, 49)
    ax1.plot(t, forecast.p50, 'r-', label='GARCH P50', linewidth=2)
    ax1.fill_between(t, forecast.p10, forecast.p90, alpha=0.3, color='red', label='P10-P90')
    ax1.set_title('GARCH Price Forecast')
    ax1.set_xlabel('Horizon (bars)')
    ax1.set_ylabel('Price')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Volatility forecast
    vol_forecast = forecast.std / close.iloc[-1]  # Normalize
    ax2.plot(t, vol_forecast, 'b-', label='Forecasted Vol', linewidth=2)
    ax2.axhline(vol[-20:].mean(), color='gray', linestyle='--', label='Historical Vol (20d)')
    ax2.set_title('GARCH Volatility Forecast')
    ax2.set_xlabel('Horizon (bars)')
    ax2.set_ylabel('Volatility (fraction)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('/home/claude/garch_demo.png', dpi=150)
    print("✅ GARCH demo saved to garch_demo.png")
    
    # Print summary
    print("\n" + "="*60)
    print("GARCH FORECAST SUMMARY")
    print("="*60)
    print(f"Model: {forecast.metadata['method']}")
    print(f"Confidence: {forecast.confidence:.2%}")
    print(f"Current vol: {forecast.metadata['current_vol']:.2%}")
    print(f"Forecast vol (24h): {forecast.metadata.get('forecast_vol_24h', 0):.2%}")
    print(f"\n24h ahead:")
    print(f"  P10: ${forecast.p10[24]:,.2f}")
    print(f"  P50: ${forecast.p50[24]:,.2f}")
    print(f"  P90: ${forecast.p90[24]:,.2f}")
    print("="*60)
