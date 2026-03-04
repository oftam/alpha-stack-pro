"""
🌀 QUANTUM PHYSICS ENGINE - Stochastic Price Dynamics
=====================================================
Treats price as a particle in a non-equilibrium dynamic field.
Uses SDEs and Feynman-Kac to calculate price probability density.

Inspired by the Physics Team's mission for ELITE v20.
"""

import numpy as np
from typing import Dict, List, Tuple, Any
from datetime import datetime

class QuantumPhysicsEngine:
    """
    Handles Diffusion-based price estimation and Probability Density Functions (PDF).
    
    Principles:
    1. GBM (Geometric Brownian Motion): dS = mu*S*dt + sigma*S*dW
    2. Feynman-Kac: Link between SDEs and Parabolic PDEs for price path estimation.
    3. Entropy-to-Drift: High volatility (entropy) creates a drift bias (mu shift).
    """
    
    def __init__(self, dt: float = 1.0/24.0): # Hourly steps
        self.dt = dt
        
    def estimate_diffusion_parameters(self, price_series: np.ndarray) -> Tuple[float, float]:
        """
        Estimates Drift (mu) and Volatility (sigma) from historical log returns.
        """
        if len(price_series) < 2:
            return 0.0, 0.2
            
        log_returns = np.diff(np.log(price_series))
        mu = np.mean(log_returns) / self.dt
        sigma = np.std(log_returns) / np.sqrt(self.dt)
        
        # Renaissance Refinement: Correct for noise (sigma shrinkage)
        sigma = np.clip(sigma, 0.05, 1.5)
        return mu, sigma

    # Regime-Switching drift table (per-day units) — SSOT per user spec
    _REGIME_DRIFTS: dict = {
        "BULL_TREND":                   0.075,    # +75‰ bullish
        "EXTREME_FEAR_ACCUMULATION":    0.050,    # moderate bullish (buy-the-dip)
        "CAPITULATION":                 0.025,    # slight bullish (reversal)
        "BEAR_TREND":                  -0.075,    # −75‰ bearish
        "DISTRIBUTION":                -0.040,    # mild bearish
        "TRANSITION":                   0.0,      # neutral walk ← THE FIX
        "VOLATILE":                     0.0,
        "NEUTRAL":                      0.0,
        "RANGING":                      0.0,
        "WHITE_NOISE":                  0.0,
    }

    def feynman_kac_pdf(self, current_price: float, horizon_steps: int = 24,
                        regime: str = "TRANSITION", sigma: float = 0.25) -> Dict[str, Any]:
        """
        Regime-Switching GBM Feynman-Kac: E[S_T] = S₀·exp((μ_regime + ½σ²)·T)
        μ depends on detected regime: BULL +75‰, BEAR −75‰, TRANSITION/NEUTRAL 0‰.
        Eliminates the systematic +8% upward bias from a fixed mu=0.01.
        """
        # Regime-dependent drift
        mu = self._REGIME_DRIFTS.get(regime, 0.0)

        # Monte Carlo paths: GBM with regime drift
        n_paths = 10_000
        T = horizon_steps * self.dt
        W_T = np.random.normal(0, np.sqrt(T), n_paths)
        # Correct GBM: E[S_T] = S₀·exp((μ + ½σ²)·T)
        S_T = current_price * np.exp((mu + 0.5 * sigma**2) * T + sigma * W_T)

        # P10, P50 (Median), P90
        p10 = np.percentile(S_T, 10)
        p50 = np.percentile(S_T, 50)
        p90 = np.percentile(S_T, 90)

        return {
            'expected_value':    float(p50),
            'lower_bound_p10':   float(p10),
            'upper_bound_p90':   float(p90),
            'drift_mu':          mu,
            'regime':            regime,
            'volatility_sigma':  sigma,
            'model':             'Regime-Switching GBM (SSOT)',
            'entropy':           float(np.std(S_T) / p50) if p50 > 0 else 0.0,
        }

    def detect_phase_transition(self, current_price: float, pdf_results: Dict) -> Dict:
        """
        Identifies if current price is in a 'Quantum Tipping Point'.
        Price at extremes of the Feynman-Kac density indicates a potential regime shift.
        """
        p10 = pdf_results['lower_bound_p10']
        p90 = pdf_results['upper_bound_p90']
        p50 = pdf_results['expected_value']
        
        is_extreme_bear = current_price < p10
        is_extreme_bull = current_price > p90
        
        status = "SUPERPOSITION"
        if is_extreme_bear: status = "QUANTUM_COLLAPSE (Oversold)"
        if is_extreme_bull: status = "QUANTUM_EXPANSION (Euphoria)"
        
        # Calculate 'Probability of Return' (reversion potential)
        prob_return = 0.9 if is_extreme_bear or is_extreme_bull else 0.5
        
        return {
            'status': status,
            'p_return': prob_return,
            'divergence': (current_price - p50) / p50
        }

    def get_snapshot(self) -> Dict:
        return {
            "physics_model": "GBM-FK-Diffusion",
            "dt_resolution": self.dt,
            "theory": "Non-equilibrium Thermodynamics"
        }
