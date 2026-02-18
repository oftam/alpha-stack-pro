#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚦 MODULE 4: EXECUTION GATES
Risk management layer - prevents bad trades in unfavorable conditions

Gates check:
- Volatility too high?
- Exposure limits exceeded?
- Drawdown too deep?
- Liquidity sufficient?
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class GateStatus(Enum):
    """Gate status"""
    OPEN = "OPEN"      # Safe to trade
    CAUTION = "CAUTION"  # Trade with care
    CLOSED = "CLOSED"  # Do not trade


@dataclass
class GateResult:
    """Result of gate check"""
    gate_name: str
    status: GateStatus
    score: float  # 0-100 (100 = fully open)
    reason: str


@dataclass
class Gate:
    """Individual execution gate"""
    name: str
    check_func: callable
    weight: float = 1.0


class ExecutionGates:
    """
    Multi-layer execution gates
    
    Gates:
    1. Volatility gate: Block trades in extreme volatility
    2. Exposure gate: Enforce position limits
    3. Drawdown gate: Stop trading after large losses
    4. Liquidity gate: Ensure sufficient market depth
    """
    
    def __init__(self,
                 max_exposure_pct: float = 100.0,
                 max_drawdown_pct: float = 20.0,
                 max_volatility_pct: float = 5.0):
        """
        Args:
            max_exposure_pct: Maximum portfolio exposure (%)
            max_drawdown_pct: Maximum drawdown before stopping (%)
            max_volatility_pct: Maximum acceptable volatility (%)
        """
        self.max_exposure = max_exposure_pct
        self.max_drawdown = max_drawdown_pct
        self.max_volatility = max_volatility_pct
        
        print("✅ Execution gates initialized")
        print(f"   Max exposure: {max_exposure_pct}%")
        print(f"   Max drawdown: {max_drawdown_pct}%")
    
    def check_volatility_gate(self, 
                              df: pd.DataFrame,
                              current_volatility: float) -> GateResult:
        """
        Gate 1: Volatility check
        
        CLOSED if volatility > max_volatility
        """
        if df.empty:
            return GateResult(
                gate_name="Volatility",
                status=GateStatus.OPEN,
                score=100.0,
                reason="No data - assuming OK"
            )
        
        # Calculate recent volatility
        returns = df['close'].pct_change().tail(20)
        volatility = returns.std() * np.sqrt(365) * 100 if len(returns) > 1 else 0.0
        
        # Score (inverse of volatility)
        if volatility == 0:
            score = 100.0
            status = GateStatus.OPEN
            reason = "Volatility normal"
        elif volatility < self.max_volatility * 0.5:
            score = 100.0
            status = GateStatus.OPEN
            reason = f"Low volatility ({volatility:.1f}%)"
        elif volatility < self.max_volatility:
            score = 70.0
            status = GateStatus.CAUTION
            reason = f"Elevated volatility ({volatility:.1f}%)"
        else:
            score = 30.0
            status = GateStatus.CLOSED
            reason = f"Extreme volatility ({volatility:.1f}% > {self.max_volatility}%)"
        
        return GateResult(
            gate_name="Volatility",
            status=status,
            score=score,
            reason=reason
        )
    
    def check_exposure_gate(self, 
                           current_exposure_pct: float,
                           proposed_action: str) -> GateResult:
        """
        Gate 2: Exposure check
        
        CLOSED if exposure would exceed max_exposure
        """
        # Estimate impact of action
        action_exposure = {
            'ADD_AGGRESSIVE': 20,
            'ADD_SMALL': 10,
            'HOLD': 0,
            'REDUCE_20': -20,
            'REDUCE_35': -35
        }
        
        impact = action_exposure.get(proposed_action, 0)
        projected_exposure = current_exposure_pct + impact
        
        # Score
        if projected_exposure <= self.max_exposure * 0.7:
            score = 100.0
            status = GateStatus.OPEN
            reason = f"Exposure OK ({projected_exposure:.0f}% / {self.max_exposure:.0f}%)"
        elif projected_exposure <= self.max_exposure:
            score = 70.0
            status = GateStatus.CAUTION
            reason = f"High exposure ({projected_exposure:.0f}% / {self.max_exposure:.0f}%)"
        else:
            score = 0.0
            status = GateStatus.CLOSED
            reason = f"Exposure limit exceeded ({projected_exposure:.0f}% > {self.max_exposure:.0f}%)"
        
        return GateResult(
            gate_name="Exposure",
            status=status,
            score=score,
            reason=reason
        )
    
    def check_drawdown_gate(self, current_drawdown_pct: float) -> GateResult:
        """
        Gate 3: Drawdown check
        
        CLOSED if drawdown > max_drawdown
        """
        # Score (inverse of drawdown)
        if current_drawdown_pct <= self.max_drawdown * 0.5:
            score = 100.0
            status = GateStatus.OPEN
            reason = f"Drawdown normal ({current_drawdown_pct:.1f}%)"
        elif current_drawdown_pct <= self.max_drawdown:
            score = 60.0
            status = GateStatus.CAUTION
            reason = f"Elevated drawdown ({current_drawdown_pct:.1f}%)"
        else:
            score = 0.0
            status = GateStatus.CLOSED
            reason = f"Max drawdown exceeded ({current_drawdown_pct:.1f}% > {self.max_drawdown:.0f}%)"
        
        return GateResult(
            gate_name="Drawdown",
            status=status,
            score=score,
            reason=reason
        )
    
    def check_liquidity_gate(self, df: pd.DataFrame) -> GateResult:
        """
        Gate 4: Liquidity check
        
        CAUTION if volume is low
        """
        if df.empty or 'volume' not in df.columns:
            return GateResult(
                gate_name="Liquidity",
                status=GateStatus.OPEN,
                score=100.0,
                reason="No volume data - assuming OK"
            )
        
        # Calculate recent volume
        recent_vol = df['volume'].tail(20).mean()
        long_term_vol = df['volume'].tail(100).mean()
        
        if long_term_vol == 0:
            return GateResult(
                gate_name="Liquidity",
                status=GateStatus.CAUTION,
                score=70.0,
                reason="No historical volume"
            )
        
        vol_ratio = recent_vol / long_term_vol
        
        # Score
        if vol_ratio > 0.8:
            score = 100.0
            status = GateStatus.OPEN
            reason = f"Normal liquidity ({vol_ratio:.1%} of average)"
        elif vol_ratio > 0.5:
            score = 70.0
            status = GateStatus.CAUTION
            reason = f"Low liquidity ({vol_ratio:.1%} of average)"
        else:
            score = 40.0
            status = GateStatus.CLOSED
            reason = f"Very low liquidity ({vol_ratio:.1%} of average)"
        
        return GateResult(
            gate_name="Liquidity",
            status=status,
            score=score,
            reason=reason
        )
    
    def check_all_gates(self,
                       df: pd.DataFrame,
                       current_exposure_pct: float = 0,
                       current_drawdown_pct: float = 0,
                       proposed_action: str = 'HOLD',
                       current_volatility: float = 0) -> Dict:
        """
        Check all execution gates
        
        Returns:
            Dict with gate results and overall status
        """
        gates = [
            self.check_volatility_gate(df, current_volatility),
            self.check_exposure_gate(current_exposure_pct, proposed_action),
            self.check_drawdown_gate(current_drawdown_pct),
            self.check_liquidity_gate(df)
        ]
        
        # Overall status
        if any(g.status == GateStatus.CLOSED for g in gates):
            overall_status = GateStatus.CLOSED
            overall_score = 0.0
        elif any(g.status == GateStatus.CAUTION for g in gates):
            overall_status = GateStatus.CAUTION
            overall_score = np.mean([g.score for g in gates])
        else:
            overall_status = GateStatus.OPEN
            overall_score = np.mean([g.score for g in gates])
        
        return {
            'overall_status': overall_status,
            'overall_score': overall_score,
            'gates': gates,
            'can_trade': overall_status != GateStatus.CLOSED
        }


# Example usage
if __name__ == '__main__':
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='1H')
    
    df = pd.DataFrame({
        'close': 100 + np.cumsum(np.random.randn(100)),
        'high': 100 + np.cumsum(np.random.randn(100)) + 1,
        'low': 100 + np.cumsum(np.random.randn(100)) - 1,
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates)
    
    # Test gates
    gates = ExecutionGates(
        max_exposure_pct=100,
        max_drawdown_pct=20,
        max_volatility_pct=5.0
    )
    
    result = gates.check_all_gates(
        df=df,
        current_exposure_pct=60,
        current_drawdown_pct=5,
        proposed_action='ADD_SMALL'
    )
    
    print(f"\n🚦 Execution Gates Check:")
    print(f"  Overall Status: {result['overall_status'].value}")
    print(f"  Overall Score: {result['overall_score']:.1f}/100")
    print(f"  Can Trade: {result['can_trade']}")
    print(f"\n  Gate Details:")
    for gate in result['gates']:
        print(f"    {gate.gate_name}: {gate.status.value} ({gate.score:.0f}/100) - {gate.reason}")
