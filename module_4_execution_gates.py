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


# ─────────────────────────────────────────────────────────────────────────────
# STANDALONE: Naor Violence Bypass — Kelly adjuster
# Usage: from modules.module_4_execution_gates import apply_chaos_adjustment
# ─────────────────────────────────────────────────────────────────────────────

def apply_chaos_adjustment(base_kelly_fraction: float,
                           violence: float,
                           num_windows: int) -> float:
    """
    Applies the Naor Violence Bypass to a Kelly position size.

    If statistical robustness is high (windows > 100) and violence is
    manageable (< 3.5x), bypass the standard chaos penalty and allow
    up to the 5% iron-rule cap unchanged.

    Args:
        base_kelly_fraction: Raw Kelly output (0–1)
        violence:            DUDU violence multiplier (e.g. 3.0)
        num_windows:         Number of DUDU windows used (e.g. 451)

    Returns:
        Adjusted Kelly fraction capped at 5%.

    Examples:
        apply_chaos_adjustment(0.08, 3.0, 451) → 0.05  (bypass active, capped)
        apply_chaos_adjustment(0.08, 5.0, 451) → 0.08 × 0.70 = 0.056 → 0.05
        apply_chaos_adjustment(0.08, 7.0,  50) → 0.08 × 0.30 = 0.024
    """
    MAX_POSITION_CAP = 0.05  # 5% Iron Rule

    if violence < 3.5 and num_windows > 100:
        # BYPASS ACTIVE: High statistical confidence overrides local chaos
        return min(base_kelly_fraction, MAX_POSITION_CAP)
    else:
        # Standard anti-fragile chaos penalty (Medallion-style dampening)
        chaos_penalty = max(0.0, 1.0 - 0.5 * (violence / 5.0))
        return min(base_kelly_fraction * chaos_penalty, MAX_POSITION_CAP)



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
                 max_exposure_pct: float = 5.0,  # Strict 5% Risk Barrier
                 max_drawdown_pct: float = 2.0,  # 2% Capital Protection
                 max_volatility_pct: float = 5.0):
        """
        Execution Gates initialized with Medallion-standard safety buffers.
        """
        self.max_exposure = max_exposure_pct
        self.max_drawdown = max_drawdown_pct
        self.max_volatility = max_volatility_pct
        self.chaos_threshold = 0.6  # Chaos/Entropy Gate Caution
        self.chaos_limit = 0.8      # Chaos/Entropy Gate Hard Veto
        
        # Simulation Mode override (if specifically requested)
        self.mode = "LIVE"
        
        print(f"🚦 Execution gates ACTIVE (Max Exposure: {max_exposure_pct}%, Chaos Limit: {self.chaos_limit})")
    
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
        
        # Simulation Mode Override: Relax strictness for signal testing
        effective_limit = self.max_volatility if self.mode != "BACKTEST" else 100.0
        
        # Score (inverse of volatility)
        if volatility == 0:
            score = 100.0
            status = GateStatus.OPEN
            reason = "Volatility normal"
        elif volatility < effective_limit * 0.5:
            score = 100.0
            status = GateStatus.OPEN
            reason = f"Low volatility ({volatility:.1f}%)"
        elif volatility < effective_limit:
            score = 70.0
            status = GateStatus.CAUTION
            reason = f"Elevated volatility ({volatility:.1f}%)"
        else:
            score = 30.0
            status = GateStatus.CLOSED
            reason = f"Extreme volatility ({volatility:.1f}% > {effective_limit}%)"
        
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
        if projected_exposure <= self.max_exposure:
            score = 100.0
            status = GateStatus.OPEN
            reason = f"Exposure OK ({projected_exposure:.0f}% / {self.max_exposure:.0f}%)"
        elif projected_exposure <= self.max_exposure + 1.0: # 1% Grace Buffer for Institutional Scaling
            score = 60.0
            status = GateStatus.CAUTION
            reason = f"Exposure Buffer utilized ({projected_exposure:.1f}% / {self.max_exposure:.0f}%)"
        else:
            score = 0.0
            status = GateStatus.CLOSED
            reason = f"Exposure limit exceeded ({projected_exposure:.1f}% > {self.max_exposure:.0f}%)"
        
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
    
    def check_chaos_gate(self, chaos_score: float,
                          violence_mult: float = 9.9,
                          dudu_windows: int = 0) -> GateResult:
        """
        Gate 5: Chaos/Entropy check — with Naor Violence Bypass.

        If statistical robustness is high (windows > 100) and violence is
        manageable (< 3.5x), the gate is held at CAUTION instead of CLOSED,
        preserving the 5% DCA allocation.
        """
        naor_bypass = violence_mult < 3.5 and dudu_windows > 100

        if chaos_score < self.chaos_threshold:
            return GateResult(
                gate_name="Chaos",
                status=GateStatus.OPEN,
                score=100.0,
                reason=f"Chaos suppressed ({chaos_score:.2f} < {self.chaos_threshold})"
            )
        elif chaos_score < self.chaos_limit:
            return GateResult(
                gate_name="Chaos",
                status=GateStatus.CAUTION,
                score=50.0,
                reason=f"Chaos elevated ({chaos_score:.2f} < {self.chaos_limit})"
            )
        elif naor_bypass:
            # Violence is high but NOT systemic — DUDU has 100+ windows → CAUTION not CLOSED
            return GateResult(
                gate_name="Chaos",
                status=GateStatus.CAUTION,
                score=40.0,
                reason=(
                    f"🧬 Naor Bypass ACTIVE: Violence={violence_mult:.1f}x < 3.5 | "
                    f"Windows={dudu_windows} > 100 → Chaos={chaos_score:.2f} overridden to CAUTION"
                )
            )
        else:
            return GateResult(
                gate_name="Chaos",
                status=GateStatus.CLOSED,
                score=0.0,
                reason=f"Extreme Chaos detected ({chaos_score:.2f} > {self.chaos_limit})"
            )

    def check_all_gates(self,
                       df: pd.DataFrame,
                       current_exposure_pct: float = 0,
                       current_drawdown_pct: float = 0,
                       proposed_action: str = 'HOLD',
                       current_volatility: float = 0,
                       chaos_score: float = 1.0,
                       violence_mult: float = 9.9,
                       dudu_windows: int = 0,
                       diffusion_score: float = 0) -> Dict:
        """
        Check all execution gates including the Victory Chaos Gate.
        violence_mult and dudu_windows enable the Naor Violence Bypass
        inside check_chaos_gate().
        """
        gates = [
            self.check_volatility_gate(df, current_volatility),
            self.check_exposure_gate(current_exposure_pct, proposed_action),
            self.check_drawdown_gate(current_drawdown_pct),
            self.check_liquidity_gate(df),
            self.check_chaos_gate(chaos_score, violence_mult, dudu_windows)
        ]
        
        # Overall status
        failed_gate = None
        for g in gates:
            if g.status == GateStatus.CLOSED:
                failed_gate = g.gate_name
                break

        if failed_gate:
            overall_status = GateStatus.CLOSED
            overall_score = 0.0
        elif any(g.status == GateStatus.CAUTION for g in gates):
            overall_status = GateStatus.CAUTION
            overall_score = float(np.mean([g.score for g in gates]))
        else:
            overall_status = GateStatus.OPEN
            overall_score = float(np.mean([g.score for g in gates]))
        
        # ── MANIPULATION FLAG (Sprint 10 — Street Smart Bypass) ──────────
        # Chaos extreme + Whales still accumulating = likely liquidation hunt
        manipulation_flag = (chaos_score > 2.0 and diffusion_score >= 90)
        
        return {
            'overall_status': overall_status,
            'overall_score': overall_score,
            'gates': gates,
            'can_trade': overall_status != GateStatus.CLOSED,
            'failed_gate': failed_gate,
            'manipulation_flag': manipulation_flag
        }

    def debug_gates(self, df: pd.DataFrame, chaos_score: float = 0.0):
        """🩺 Clinical diagnostic for Gate behavior"""
        print("\n" + "="*40)
        print("🚦 GATE DIAGNOSTIC OVERRIDE")
        print("="*40)
        
        vol_res = self.check_volatility_gate(df, 0.0)
        chaos_res = self.check_chaos_gate(chaos_score)
        
        print(f"VOLATILITY: {vol_res.status.value} (Score: {vol_res.score}) - {vol_res.reason}")
        print(f"CHAOS:      {chaos_res.status.value} (Score: {chaos_res.score}) - {chaos_res.reason}")
        print("="*40 + "\n")


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
