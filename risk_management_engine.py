"""
⚖️ RISK MANAGEMENT ENGINE - Kelly & Monte Carlo
==============================================
Ensures mathematical ruin prevention and optimal sizing.
Replaces fixed percentages with probability-driven allocation.

Inspired by the Math Team's discipline for ELITE v20.
"""

import numpy as np
from typing import Dict, List, Any
from datetime import datetime

class RiskManagementEngine:
    """
    Manages allocation using the Kelly Criterion and Monte Carlo simulations.
    
    Principles:
    1. Kelly Criterion: Allocation = (bp - q) / b (where b is odds, p is P_win, q is 1-p).
    2. Monte Carlo Ruin Check: Simulating thousands of equity curves to find Drawdown probability.
    3. Fractional Kelly: Reducing allocation for safety (0.25 - 0.5x Kelly).
    """
    
    def __init__(self, account_balance: float = 10000.0, max_drawdown: float = 0.2):
        self.account_balance = account_balance
        self.max_drawdown = max_drawdown
        
    def calculate_kelly_fraction(self, p_win: float, reward_to_risk: float) -> float:
        """
        Calculates the optimal Kelly position size.
        """
        # Kelly % = (p * (b + 1) - 1) / b
        # where b is the decimal odds (Profit/Loss ratio)
        b = reward_to_risk
        if b <= 0: return 0.0
        
        kelly_pct = (p_win * (b + 1) - 1) / b
        
        # Renaissance Rule: Fractional Kelly (0.2x) for extreme safety
        return float(np.clip(kelly_pct * 0.2, 0, 0.2)) # Max 20% per trade

    def monte_carlo_ruin_simulation(self, p_win: float, r_to_r: float, n_trades: int = 100) -> Dict:
        """
        Predicts the probability of reaching max drawdown over N future trades.
        """
        n_sims = 5000
        ruin_count = 0
        final_balances = []
        
        for _ in range(n_sims):
            balance = 1.0 # Normalized
            kelly_size = self.calculate_kelly_fraction(p_win, r_to_r)
            
            for _ in range(n_trades):
                outcome = 1 if np.random.random() < p_win else -1
                if outcome == 1:
                    balance *= (1 + (kelly_size * r_to_r))
                else:
                    balance *= (1 - kelly_size)
                
                if balance < (1 - self.max_drawdown):
                    ruin_count += 1
                    break
            final_balances.append(balance)
            
        prob_ruin = ruin_count / n_sims
        expected_growth = np.mean(final_balances) - 1.0
        
        return {
            'prob_ruin': float(prob_ruin),
            'expected_growth_100_trades': float(expected_growth),
            'risk_status': "SECURE" if prob_ruin < 0.01 else "FRAGILE" if prob_ruin < 0.1 else "HIGH RISK"
        }

    def get_allocation_guidance(self, results: Dict) -> Dict:
        """
        Main entry point for calculating professional position sizing.
        """
        p_win = results.get('monolith_score', 50.0) / 100.0
        r_to_r = results.get('rr_ratio', 2.0)
        
        kelly_size = self.calculate_kelly_fraction(p_win, r_to_r)
        monte_carlo = self.monte_carlo_ruin_simulation(p_win, r_to_r)
        
        return {
            'optimal_position_pct': kelly_size * 100,
            'max_notional_usd': self.account_balance * kelly_size,
            'ruin_probability': monte_carlo['prob_ruin'],
            'risk_status': monte_carlo['risk_status'],
            'timestamp': datetime.now().isoformat()
        }

    def get_snapshot(self) -> Dict:
        return {
            "methodology": "Fractional Kelly + Monte Carlo",
            "threshold_drawdown": self.max_drawdown,
            "simulations_n": 5000
        }
