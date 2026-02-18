#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 ELITE v20 - STRATEGY OPTIMIZER
Backtesting, timing analysis, and success rate calculator

BONUS #1 - Compensation for the morning confusion
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json


class StrategyOptimizer:
    """
    Analyzes Elite v20 signals and optimizes:
    - Entry timing
    - Position sizing
    - Success rates
    - Historical performance
    """
    
    def __init__(self):
        self.historical_signals = []
        self.performance_data = {
            'dca': {'wins': 0, 'losses': 0, 'total_pnl': 0},
            'tactical': {'wins': 0, 'losses': 0, 'total_pnl': 0}
        }
    
    # =========================================================================
    # HISTORICAL ANALYSIS
    # =========================================================================
    
    def analyze_historical_signals(self, 
                                   signals_df: pd.DataFrame,
                                   price_df: pd.DataFrame) -> Dict:
        """
        Backtest historical Elite signals
        
        Args:
            signals_df: DataFrame with columns [timestamp, signal_type, manifold, confidence]
            price_df: DataFrame with OHLCV data
            
        Returns:
            Performance metrics and success rates
        """
        
        results = {
            'total_signals': len(signals_df),
            'dca_signals': 0,
            'tactical_signals': 0,
            'wins': 0,
            'losses': 0,
            'avg_return': 0,
            'best_return': 0,
            'worst_return': 0,
            'success_rate': 0,
            'by_manifold_score': {},
            'by_regime': {}
        }
        
        if signals_df.empty or price_df.empty:
            return results
        
        returns = []
        
        for idx, signal in signals_df.iterrows():
            signal_time = signal['timestamp']
            signal_type = signal['signal_type']
            
            # Find entry price
            entry_price = price_df[price_df.index >= signal_time]['close'].iloc[0]
            
            # Calculate returns at different horizons
            if signal_type == 'DCA':
                # DCA: 30-day hold
                exit_time = signal_time + timedelta(days=30)
                results['dca_signals'] += 1
            else:
                # Tactical: 7-day hold (or T2 hit)
                exit_time = signal_time + timedelta(days=7)
                results['tactical_signals'] += 1
            
            # Find exit price
            exit_prices = price_df[price_df.index >= exit_time]['close']
            if len(exit_prices) == 0:
                continue
            
            exit_price = exit_prices.iloc[0]
            
            # Calculate return
            ret = (exit_price - entry_price) / entry_price * 100
            returns.append(ret)
            
            if ret > 0:
                results['wins'] += 1
            else:
                results['losses'] += 1
            
            # Track by manifold score
            manifold_bucket = int(signal['manifold'] / 10) * 10
            if manifold_bucket not in results['by_manifold_score']:
                results['by_manifold_score'][manifold_bucket] = {
                    'count': 0, 'wins': 0, 'avg_return': 0
                }
            
            results['by_manifold_score'][manifold_bucket]['count'] += 1
            if ret > 0:
                results['by_manifold_score'][manifold_bucket]['wins'] += 1
        
        # Calculate summary stats
        if returns:
            results['avg_return'] = np.mean(returns)
            results['best_return'] = np.max(returns)
            results['worst_return'] = np.min(returns)
            results['success_rate'] = results['wins'] / len(returns) * 100
            
            # Calculate by manifold
            for bucket in results['by_manifold_score']:
                bucket_data = results['by_manifold_score'][bucket]
                bucket_data['success_rate'] = (
                    bucket_data['wins'] / bucket_data['count'] * 100
                )
        
        return results
    
    # =========================================================================
    # TIMING OPTIMIZATION
    # =========================================================================
    
    def optimize_entry_timing(self,
                             signal_time: datetime,
                             price_df: pd.DataFrame,
                             window_hours: int = 24) -> Dict:
        """
        Find optimal entry timing within a window after signal
        
        Args:
            signal_time: When signal was generated
            price_df: Intraday price data
            window_hours: How long to wait for optimal entry
            
        Returns:
            Optimal entry time and expected improvement
        """
        
        # Get price action in the window
        window_start = signal_time
        window_end = signal_time + timedelta(hours=window_hours)
        
        window_prices = price_df[
            (price_df.index >= window_start) & 
            (price_df.index <= window_end)
        ]
        
        if window_prices.empty:
            return {
                'optimal_time': signal_time,
                'optimal_price': None,
                'improvement_pct': 0,
                'recommendation': 'Enter immediately'
            }
        
        # Find lowest price in window (best entry for long)
        lowest_idx = window_prices['low'].idxmin()
        lowest_price = window_prices.loc[lowest_idx, 'low']
        signal_price = window_prices.iloc[0]['close']
        
        improvement = (signal_price - lowest_price) / signal_price * 100
        
        # Time to optimal entry
        time_to_optimal = (lowest_idx - signal_time).total_seconds() / 3600
        
        recommendation = self._generate_timing_recommendation(
            improvement, time_to_optimal
        )
        
        return {
            'optimal_time': lowest_idx,
            'optimal_price': lowest_price,
            'signal_price': signal_price,
            'improvement_pct': improvement,
            'hours_to_optimal': time_to_optimal,
            'recommendation': recommendation
        }
    
    def _generate_timing_recommendation(self,
                                       improvement: float,
                                       hours: float) -> str:
        """Generate actionable recommendation"""
        
        if improvement < 0.5:
            return f"Enter immediately - minimal improvement expected ({improvement:.1f}%)"
        elif improvement < 2 and hours < 4:
            return f"Wait {hours:.0f}h for {improvement:.1f}% better entry"
        elif improvement > 2:
            return f"⚠️ Significant dip possible in {hours:.0f}h ({improvement:.1f}%)"
        else:
            return "Monitor for better entry, but don't wait too long"
    
    # =========================================================================
    # POSITION SIZE OPTIMIZATION
    # =========================================================================
    
    def optimize_position_size(self,
                               capital: float,
                               manifold_score: float,
                               confidence: float,
                               win_rate: float,
                               avg_win: float,
                               avg_loss: float) -> Dict:
        """
        Calculate optimal position size using Kelly + adjustments
        
        Args:
            capital: Available capital
            manifold_score: Current signal strength (0-100)
            confidence: System confidence (0-1)
            win_rate: Historical win rate (0-1)
            avg_win: Average winning return (%)
            avg_loss: Average losing return (%)
            
        Returns:
            Optimal position size and rationale
        """
        
        # Kelly Criterion
        if avg_loss == 0:
            kelly = 0.1  # Conservative default
        else:
            kelly = (win_rate * avg_win - (1 - win_rate) * abs(avg_loss)) / avg_win
        
        # Cap Kelly at 25% (aggressive max)
        kelly = min(kelly, 0.25)
        kelly = max(kelly, 0.01)  # Minimum 1%
        
        # Adjust for signal strength
        manifold_multiplier = manifold_score / 100
        confidence_multiplier = confidence
        
        # Final position size
        position_pct = kelly * manifold_multiplier * confidence_multiplier
        
        # Apply risk limits
        position_pct = max(position_pct, 0.01)  # Min 1%
        position_pct = min(position_pct, 0.05)  # Max 5% (IRON RULE)
        
        position_size = capital * position_pct
        
        return {
            'kelly_pct': kelly * 100,
            'manifold_adjustment': manifold_multiplier,
            'confidence_adjustment': confidence_multiplier,
            'recommended_pct': position_pct * 100,
            'position_size': position_size,
            'rationale': self._generate_sizing_rationale(
                kelly, manifold_score, confidence, position_pct
            )
        }
    
    def _generate_sizing_rationale(self,
                                   kelly: float,
                                   manifold: float,
                                   confidence: float,
                                   final_pct: float) -> str:
        """Explain position sizing decision"""
        
        if final_pct < 0.02:
            risk_level = "Conservative"
        elif final_pct < 0.04:
            risk_level = "Moderate"
        else:
            risk_level = "Aggressive (max allowed)"
        
        return (
            f"{risk_level} sizing:\n"
            f"  • Kelly base: {kelly*100:.1f}%\n"
            f"  • Manifold ({manifold:.0f}): {'Strong' if manifold > 70 else 'Moderate'} signal\n"
            f"  • Confidence ({confidence*100:.0f}%): {'High' if confidence > 0.8 else 'Medium'} conviction\n"
            f"  • Final: {final_pct*100:.1f}% of capital"
        )
    
    # =========================================================================
    # CONFLUENCE ANALYSIS
    # =========================================================================
    
    def analyze_signal_confluence(self,
                                  current_signal: Dict,
                                  timeframes: List[str] = ['1h', '4h', '1d']) -> Dict:
        """
        Check if multiple timeframes agree on the signal
        
        Strong confluence = higher probability of success
        """
        
        confluence_score = 0
        agreements = []
        
        for tf in timeframes:
            # This would check if signal exists on each timeframe
            # Placeholder - would integrate with actual multi-TF data
            tf_score = current_signal.get(f'manifold_{tf}', 50)
            
            if tf_score > 70:
                confluence_score += 1
                agreements.append(f"{tf}: {tf_score:.0f}")
        
        confluence_pct = confluence_score / len(timeframes) * 100
        
        if confluence_pct > 66:
            strength = "STRONG"
            recommendation = "High-probability setup - full position size"
        elif confluence_pct > 33:
            strength = "MODERATE"
            recommendation = "Partial agreement - consider reduced size"
        else:
            strength = "WEAK"
            recommendation = "Low confluence - wait for better setup"
        
        return {
            'confluence_score': confluence_score,
            'confluence_pct': confluence_pct,
            'strength': strength,
            'agreements': agreements,
            'recommendation': recommendation
        }
    
    # =========================================================================
    # REPORT GENERATION
    # =========================================================================
    
    def generate_optimization_report(self,
                                    current_signal: Dict,
                                    historical_data: pd.DataFrame,
                                    capital: float) -> str:
        """
        Generate complete optimization report for current signal
        """
        
        report = []
        report.append("=" * 70)
        report.append("🎯 STRATEGY OPTIMIZER REPORT")
        report.append("=" * 70)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Signal details
        report.append("📊 CURRENT SIGNAL:")
        report.append(f"  Type: {current_signal.get('type', 'N/A')}")
        report.append(f"  Manifold: {current_signal.get('manifold', 0):.1f}/100")
        report.append(f"  Confidence: {current_signal.get('confidence', 0)*100:.1f}%")
        report.append("")
        
        # Historical performance
        if not historical_data.empty:
            hist_perf = self.analyze_historical_signals(
                historical_data, historical_data
            )
            
            report.append("📈 HISTORICAL PERFORMANCE:")
            report.append(f"  Total signals: {hist_perf['total_signals']}")
            report.append(f"  Success rate: {hist_perf['success_rate']:.1f}%")
            report.append(f"  Average return: {hist_perf['avg_return']:.2f}%")
            report.append(f"  Best trade: {hist_perf['best_return']:.2f}%")
            report.append(f"  Worst trade: {hist_perf['worst_return']:.2f}%")
            report.append("")
        
        # Position sizing
        sizing = self.optimize_position_size(
            capital=capital,
            manifold_score=current_signal.get('manifold', 50),
            confidence=current_signal.get('confidence', 0.5),
            win_rate=0.60,  # Would use actual historical
            avg_win=5.0,
            avg_loss=-2.5
        )
        
        report.append("💰 OPTIMAL POSITION SIZE:")
        report.append(f"  Recommended: {sizing['recommended_pct']:.2f}% of capital")
        report.append(f"  Amount: ${sizing['position_size']:,.2f}")
        report.append(f"  Kelly base: {sizing['kelly_pct']:.1f}%")
        report.append("")
        report.append("  Rationale:")
        for line in sizing['rationale'].split('\n'):
            report.append(f"  {line}")
        report.append("")
        
        # Timing recommendation
        report.append("⏰ ENTRY TIMING:")
        report.append("  Recommendation: Monitor for dip within 2-4 hours")
        report.append("  Alternative: Enter immediately if manifold > 85")
        report.append("")
        
        report.append("=" * 70)
        
        return '\n'.join(report)


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == '__main__':
    optimizer = StrategyOptimizer()
    
    # Example signal
    current_signal = {
        'type': 'TACTICAL',
        'manifold': 82.5,
        'confidence': 0.88,
        'timestamp': datetime.now()
    }
    
    # Generate report
    report = optimizer.generate_optimization_report(
        current_signal=current_signal,
        historical_data=pd.DataFrame(),  # Would use real data
        capital=10000
    )
    
    print(report)
