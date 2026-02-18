#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💰 ELITE v20 - RISK CALCULATOR PRO
Advanced position sizing with Monte Carlo simulation

BONUS #3 - Professional risk management
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from scipy import stats
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class RiskCalculatorPro:
    """
    Advanced risk management calculator
    
    Features:
    - Kelly Criterion with Monte Carlo
    - Portfolio heat analysis
    - Correlation-adjusted sizing
    - Drawdown protection
    - Risk/Reward optimization
    """
    
    def __init__(self, capital: float = 10000):
        self.capital = capital
        self.max_risk_pct = 5.0  # IRON RULE
        self.positions = []
    
    # =========================================================================
    # KELLY CRITERION WITH MONTE CARLO
    # =========================================================================
    
    def calculate_kelly_with_monte_carlo(self,
                                        win_rate: float,
                                        avg_win: float,
                                        avg_loss: float,
                                        simulations: int = 10000,
                                        confidence_level: float = 0.95) -> Dict:
        """
        Calculate Kelly Criterion with Monte Carlo confidence intervals
        
        Args:
            win_rate: Historical win rate (0-1)
            avg_win: Average winning return (%)
            avg_loss: Average losing return (%)
            simulations: Number of Monte Carlo runs
            confidence_level: Confidence level for bounds
            
        Returns:
            Kelly size with confidence intervals
        """
        
        # Standard Kelly
        if avg_win == 0:
            kelly_pct = 0
        else:
            kelly_pct = (win_rate * avg_win - (1 - win_rate) * abs(avg_loss)) / avg_win
        
        # Monte Carlo simulation
        kelly_samples = []
        
        for _ in range(simulations):
            # Add noise to parameters
            sim_win_rate = np.clip(
                np.random.normal(win_rate, win_rate * 0.1),
                0, 1
            )
            sim_avg_win = np.random.normal(avg_win, avg_win * 0.2)
            sim_avg_loss = np.random.normal(avg_loss, abs(avg_loss) * 0.2)
            
            # Calculate Kelly for this simulation
            if sim_avg_win > 0:
                sim_kelly = (
                    sim_win_rate * sim_avg_win - 
                    (1 - sim_win_rate) * abs(sim_avg_loss)
                ) / sim_avg_win
            else:
                sim_kelly = 0
            
            kelly_samples.append(sim_kelly)
        
        # Calculate confidence intervals
        kelly_samples = np.array(kelly_samples)
        lower_bound = np.percentile(kelly_samples, (1 - confidence_level) / 2 * 100)
        upper_bound = np.percentile(kelly_samples, (1 + confidence_level) / 2 * 100)
        median = np.median(kelly_samples)
        
        # Conservative Kelly (use lower bound)
        conservative_kelly = max(lower_bound, 0.01)
        conservative_kelly = min(conservative_kelly, self.max_risk_pct / 100)
        
        return {
            'kelly_pct': kelly_pct * 100,
            'median': median * 100,
            'lower_bound': lower_bound * 100,
            'upper_bound': upper_bound * 100,
            'conservative_kelly': conservative_kelly * 100,
            'recommended_size': self.capital * conservative_kelly,
            'samples': kelly_samples,
            'interpretation': self._interpret_kelly_mc(
                kelly_pct, conservative_kelly, lower_bound, upper_bound
            )
        }
    
    def _interpret_kelly_mc(self,
                           kelly: float,
                           conservative: float,
                           lower: float,
                           upper: float) -> str:
        """Interpret Monte Carlo Kelly results"""
        
        spread = upper - lower
        
        if spread < 0.05:
            uncertainty = "Low uncertainty"
        elif spread < 0.15:
            uncertainty = "Moderate uncertainty"
        else:
            uncertainty = "High uncertainty"
        
        return (
            f"{uncertainty} in Kelly estimate\n"
            f"Full Kelly: {kelly*100:.1f}%\n"
            f"Conservative (95% CI): {conservative*100:.1f}%\n"
            f"→ Using conservative estimate for safety"
        )
    
    # =========================================================================
    # PORTFOLIO HEAT
    # =========================================================================
    
    def calculate_portfolio_heat(self,
                                open_positions: List[Dict]) -> Dict:
        """
        Calculate total portfolio risk exposure
        
        Args:
            open_positions: List of dicts with 'size', 'entry', 'stop'
            
        Returns:
            Total risk metrics
        """
        
        total_risk = 0
        position_risks = []
        
        for pos in open_positions:
            size = pos['size']
            entry = pos['entry']
            stop = pos['stop']
            
            # Calculate risk per position
            risk_per_share = abs(entry - stop)
            risk_pct = (risk_per_share / entry) * 100
            risk_amount = size * risk_per_share
            
            position_risks.append({
                'symbol': pos.get('symbol', 'BTC'),
                'size': size,
                'risk_pct': risk_pct,
                'risk_amount': risk_amount
            })
            
            total_risk += risk_amount
        
        # Portfolio heat
        portfolio_heat_pct = (total_risk / self.capital) * 100
        
        # Risk status
        if portfolio_heat_pct < 3:
            status = "🟢 LOW"
            recommendation = "Safe to add positions"
        elif portfolio_heat_pct < 5:
            status = "🟡 MODERATE"
            recommendation = "Approaching limit - be selective"
        elif portfolio_heat_pct < 7:
            status = "🟠 HIGH"
            recommendation = "⚠️ At risk limit - no new positions"
        else:
            status = "🔴 CRITICAL"
            recommendation = "🚨 OVER LIMIT - reduce exposure immediately"
        
        return {
            'total_risk_amount': total_risk,
            'portfolio_heat_pct': portfolio_heat_pct,
            'status': status,
            'recommendation': recommendation,
            'position_risks': position_risks,
            'num_positions': len(open_positions),
            'available_risk': max(
                self.capital * (self.max_risk_pct / 100) - total_risk,
                0
            )
        }
    
    # =========================================================================
    # CORRELATION-ADJUSTED SIZING
    # =========================================================================
    
    def calculate_correlation_adjusted_size(self,
                                           base_size: float,
                                           new_position_correlation: float,
                                           existing_positions: List[Dict]) -> Dict:
        """
        Adjust position size based on correlation with existing positions
        
        High correlation = reduce size to avoid concentration risk
        """
        
        if not existing_positions:
            return {
                'adjusted_size': base_size,
                'adjustment_factor': 1.0,
                'rationale': "No existing positions - full size OK"
            }
        
        # Calculate correlation impact
        avg_correlation = new_position_correlation
        
        if abs(avg_correlation) < 0.3:
            adjustment = 1.0  # Low correlation - no adjustment
            rationale = "Low correlation - full size OK"
        elif abs(avg_correlation) < 0.6:
            adjustment = 0.75  # Moderate correlation - reduce 25%
            rationale = "Moderate correlation - reduced 25%"
        elif abs(avg_correlation) < 0.8:
            adjustment = 0.50  # High correlation - reduce 50%
            rationale = "High correlation - reduced 50%"
        else:
            adjustment = 0.25  # Very high correlation - reduce 75%
            rationale = "Very high correlation - reduced 75%"
        
        adjusted_size = base_size * adjustment
        
        return {
            'base_size': base_size,
            'adjusted_size': adjusted_size,
            'adjustment_factor': adjustment,
            'correlation': avg_correlation,
            'rationale': rationale,
            'risk_reduction': base_size - adjusted_size
        }
    
    # =========================================================================
    # DRAWDOWN PROTECTION
    # =========================================================================
    
    def calculate_drawdown_adjusted_size(self,
                                        base_size: float,
                                        current_drawdown_pct: float,
                                        max_acceptable_dd: float = 20.0) -> Dict:
        """
        Reduce position size during drawdowns to protect capital
        
        Args:
            base_size: Calculated position size
            current_drawdown_pct: Current drawdown from peak (%)
            max_acceptable_dd: Maximum drawdown before full stop (%)
            
        Returns:
            Adjusted size with drawdown protection
        """
        
        if current_drawdown_pct <= 0:
            return {
                'adjusted_size': base_size,
                'adjustment_factor': 1.0,
                'status': "🟢 NO DRAWDOWN",
                'rationale': "At or above peak equity - full size"
            }
        
        # Calculate reduction factor
        dd_ratio = current_drawdown_pct / max_acceptable_dd
        
        if dd_ratio < 0.25:
            # 0-5% DD: no adjustment
            adjustment = 1.0
            status = "🟢 MILD"
            rationale = f"{current_drawdown_pct:.1f}% DD - full size OK"
        
        elif dd_ratio < 0.50:
            # 5-10% DD: reduce 25%
            adjustment = 0.75
            status = "🟡 MODERATE"
            rationale = f"{current_drawdown_pct:.1f}% DD - reduced 25%"
        
        elif dd_ratio < 0.75:
            # 10-15% DD: reduce 50%
            adjustment = 0.50
            status = "🟠 SIGNIFICANT"
            rationale = f"{current_drawdown_pct:.1f}% DD - reduced 50%"
        
        else:
            # >15% DD: reduce 75% or stop
            adjustment = 0.25
            status = "🔴 SEVERE"
            rationale = f"{current_drawdown_pct:.1f}% DD - reduced 75% or STOP"
        
        adjusted_size = base_size * adjustment
        
        return {
            'base_size': base_size,
            'adjusted_size': adjusted_size,
            'adjustment_factor': adjustment,
            'drawdown_pct': current_drawdown_pct,
            'status': status,
            'rationale': rationale
        }
    
    # =========================================================================
    # RISK/REWARD OPTIMIZATION
    # =========================================================================
    
    def optimize_risk_reward(self,
                            entry: float,
                            target1: float,
                            target2: float,
                            stop: float,
                            capital: float) -> Dict:
        """
        Calculate optimal position size based on R:R ratio
        
        Better R:R = can risk more capital
        """
        
        # Calculate R:R ratios
        risk_per_unit = abs(entry - stop)
        reward_t1 = target1 - entry
        reward_t2 = target2 - entry
        
        rr_t1 = reward_t1 / risk_per_unit if risk_per_unit > 0 else 0
        rr_t2 = reward_t2 / risk_per_unit if risk_per_unit > 0 else 0
        
        # Position sizing based on R:R
        if rr_t1 < 1.5:
            size_multiplier = 0.5  # Poor R:R - reduce size
            quality = "🔴 POOR"
        elif rr_t1 < 2.0:
            size_multiplier = 0.75  # Acceptable R:R
            quality = "🟡 ACCEPTABLE"
        elif rr_t1 < 3.0:
            size_multiplier = 1.0  # Good R:R
            quality = "🟢 GOOD"
        else:
            size_multiplier = 1.2  # Excellent R:R - can increase size
            quality = "💎 EXCELLENT"
        
        # Calculate sizes
        risk_amount = capital * (self.max_risk_pct / 100)
        base_position_size = risk_amount / risk_per_unit
        optimized_size = base_position_size * size_multiplier
        
        return {
            'rr_t1': rr_t1,
            'rr_t2': rr_t2,
            'risk_per_unit': risk_per_unit,
            'risk_pct': (risk_per_unit / entry) * 100,
            'quality': quality,
            'base_size': base_position_size,
            'optimized_size': optimized_size,
            'size_multiplier': size_multiplier,
            'recommendation': self._generate_rr_recommendation(rr_t1, quality)
        }
    
    def _generate_rr_recommendation(self, rr: float, quality: str) -> str:
        """Generate R:R recommendation"""
        
        if rr < 1.5:
            return (
                f"⚠️ R:R too low ({rr:.2f}:1)\n"
                "Consider:\n"
                "  • Tighter stop\n"
                "  • Higher targets\n"
                "  • Skip this trade"
            )
        elif rr < 2.0:
            return (
                f"Acceptable R:R ({rr:.2f}:1)\n"
                "Proceed with reduced size"
            )
        elif rr < 3.0:
            return (
                f"✅ Good R:R ({rr:.2f}:1)\n"
                "Full position size recommended"
            )
        else:
            return (
                f"💎 Excellent R:R ({rr:.2f}:1)\n"
                "High-probability setup\n"
                "Consider increased size"
            )
    
    # =========================================================================
    # COMPREHENSIVE REPORT
    # =========================================================================
    
    def generate_risk_report(self,
                            signal_data: Dict,
                            open_positions: List[Dict] = None) -> str:
        """
        Generate complete risk analysis report
        """
        
        open_positions = open_positions or []
        
        report = []
        report.append("=" * 70)
        report.append("💰 RISK CALCULATOR PRO - COMPREHENSIVE ANALYSIS")
        report.append("=" * 70)
        report.append(f"Capital: ${self.capital:,.2f}")
        report.append(f"Max Risk: {self.max_risk_pct}% (IRON RULE)")
        report.append("")
        
        # Kelly with Monte Carlo
        kelly_mc = self.calculate_kelly_with_monte_carlo(
            win_rate=signal_data.get('win_rate', 0.6),
            avg_win=signal_data.get('avg_win', 5.0),
            avg_loss=signal_data.get('avg_loss', -2.5)
        )
        
        report.append("📊 KELLY CRITERION (Monte Carlo):")
        report.append(f"  Full Kelly: {kelly_mc['kelly_pct']:.2f}%")
        report.append(f"  95% CI: [{kelly_mc['lower_bound']:.2f}%, {kelly_mc['upper_bound']:.2f}%]")
        report.append(f"  Conservative: {kelly_mc['conservative_kelly']:.2f}%")
        report.append(f"  Position Size: ${kelly_mc['recommended_size']:,.2f}")
        report.append("")
        
        # Portfolio Heat
        heat = self.calculate_portfolio_heat(open_positions)
        
        report.append("🔥 PORTFOLIO HEAT:")
        report.append(f"  Total Risk: ${heat['total_risk_amount']:,.2f}")
        report.append(f"  Portfolio Heat: {heat['portfolio_heat_pct']:.2f}%")
        report.append(f"  Status: {heat['status']}")
        report.append(f"  Available Risk: ${heat['available_risk']:,.2f}")
        report.append(f"  → {heat['recommendation']}")
        report.append("")
        
        # R:R Optimization
        if 'entry' in signal_data:
            rr_opt = self.optimize_risk_reward(
                entry=signal_data['entry'],
                target1=signal_data.get('target1', signal_data['entry'] * 1.05),
                target2=signal_data.get('target2', signal_data['entry'] * 1.12),
                stop=signal_data.get('stop', signal_data['entry'] * 0.98),
                capital=self.capital
            )
            
            report.append("⚖️ RISK/REWARD OPTIMIZATION:")
            report.append(f"  R:R T1: {rr_opt['rr_t1']:.2f}:1")
            report.append(f"  R:R T2: {rr_opt['rr_t2']:.2f}:1")
            report.append(f"  Quality: {rr_opt['quality']}")
            report.append(f"  Optimized Size: {rr_opt['optimized_size']:.4f} BTC")
            report.append("")
        
        report.append("=" * 70)
        report.append("✅ FINAL RECOMMENDATION:")
        report.append(f"  Position Size: ${kelly_mc['recommended_size']:,.2f}")
        report.append(f"  Risk Amount: ${kelly_mc['recommended_size'] * 0.02:,.2f}")
        report.append(f"  → Execute if portfolio heat < 5%")
        report.append("=" * 70)
        
        return '\n'.join(report)


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == '__main__':
    calculator = RiskCalculatorPro(capital=10000)
    
    # Example signal
    signal_data = {
        'entry': 98000,
        'target1': 102900,  # +5%
        'target2': 109760,  # +12%
        'stop': 96040,  # -2%
        'win_rate': 0.65,
        'avg_win': 5.5,
        'avg_loss': -2.2
    }
    
    # Generate report
    report = calculator.generate_risk_report(signal_data, open_positions=[])
    
    print(report)
