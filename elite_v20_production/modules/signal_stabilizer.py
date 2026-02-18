#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🛡️ SIGNAL STABILIZER - Anti-Whipsaw Protection
Prevents action flip-flopping when on-chain data goes LIVE

Problems solved:
1. Score volatility (on-chain 20→85 swings)
2. Action whipsawing (ADD→REDUCE→ADD)
3. Low conviction trades

Methods:
- EMA smoothing (reduce noise)
- Hysteresis bands (require significant change)
- Validation period (N consecutive signals)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from collections import deque
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SignalHistory:
    """Track signal history for smoothing"""
    timestamps: deque
    scores: deque
    actions: deque
    
    def __init__(self, maxlen: int = 20):
        self.timestamps = deque(maxlen=maxlen)
        self.scores = deque(maxlen=maxlen)
        self.actions = deque(maxlen=maxlen)
    
    def add(self, score: float, action: str):
        self.timestamps.append(datetime.now())
        self.scores.append(score)
        self.actions.append(action)


class SignalStabilizer:
    """
    Stabilizes Elite signals to prevent whipsawing
    
    Key features:
    - EMA smoothing (configurable alpha)
    - Hysteresis bands (action zones)
    - Validation period (N consecutive)
    """
    
    def __init__(self,
                 ema_alpha: float = 0.3,
                 hysteresis_threshold: float = 10.0,
                 validation_periods: int = 2):
        """
        Args:
            ema_alpha: EMA smoothing factor (0-1, higher=more responsive)
            hysteresis_threshold: Points change needed to flip action
            validation_periods: Consecutive periods required to change action
        """
        self.ema_alpha = ema_alpha
        self.hysteresis = hysteresis_threshold
        self.validation_periods = validation_periods
        
        # State
        self.history = SignalHistory(maxlen=50)
        self.ema_score = None
        self.last_action = 'HOLD'
        self.action_candidate = None
        self.validation_count = 0
        
        print(f"🛡️  Signal stabilizer initialized (alpha={ema_alpha}, hysteresis={hysteresis_threshold})")
    
    # =========================================================================
    # SMOOTHING
    # =========================================================================
    
    def smooth_score(self, raw_score: float) -> float:
        """
        Apply EMA smoothing to score
        
        EMA = alpha * raw + (1 - alpha) * prev_EMA
        """
        if self.ema_score is None:
            # Initialize with first value
            self.ema_score = raw_score
            return raw_score
        
        # Update EMA
        self.ema_score = (self.ema_alpha * raw_score + 
                         (1 - self.ema_alpha) * self.ema_score)
        
        return self.ema_score
    
    # =========================================================================
    # ACTION MAPPING (with hysteresis)
    # =========================================================================
    
    def score_to_action(self, score: float) -> str:
        """
        Map score to action with hysteresis bands
        
        Zones (with hysteresis):
        - 80+: ADD_AGGRESSIVE
        - 65-79: ADD_SMALL
        - 45-64: HOLD
        - 30-44: REDUCE_20
        - <30: REDUCE_35
        
        Hysteresis: Need to cross threshold + hysteresis to change
        """
        
        # Define action zones
        if score >= 80:
            action = 'ADD_AGGRESSIVE'
        elif score >= 65:
            action = 'ADD_SMALL'
        elif score >= 45:
            action = 'HOLD'
        elif score >= 30:
            action = 'REDUCE_20'
        else:
            action = 'REDUCE_35'
        
        return action
    
    def apply_hysteresis(self, 
                        current_score: float,
                        proposed_action: str) -> str:
        """
        Apply hysteresis to prevent small-change flip-flops
        
        Only change action if score moved significantly
        """
        
        # Get last smoothed score
        if not self.history.scores:
            return proposed_action  # First call
        
        prev_score = self.history.scores[-1]
        score_change = abs(current_score - prev_score)
        
        # If action changed but score change < threshold → keep old action
        if proposed_action != self.last_action:
            if score_change < self.hysteresis:
                # Not enough change - keep old action
                return self.last_action
        
        return proposed_action
    
    # =========================================================================
    # VALIDATION PERIOD
    # =========================================================================
    
    def validate_action(self, proposed_action: str) -> str:
        """
        Require N consecutive periods of same action before changing
        
        Prevents single-bar whipsaws
        """
        
        # If same as last action, reset validation
        if proposed_action == self.last_action:
            self.action_candidate = None
            self.validation_count = 0
            return self.last_action
        
        # New action proposed
        if proposed_action == self.action_candidate:
            # Same candidate - increment count
            self.validation_count += 1
        else:
            # Different candidate - reset
            self.action_candidate = proposed_action
            self.validation_count = 1
        
        # Check if validated
        if self.validation_count >= self.validation_periods:
            # Validated - change action
            self.validation_count = 0
            self.action_candidate = None
            return proposed_action
        else:
            # Not validated yet - keep old action
            return self.last_action
    
    # =========================================================================
    # MAIN INTERFACE
    # =========================================================================
    
    def stabilize(self, 
                 raw_score: float,
                 raw_action: str,
                 confidence: float) -> Dict:
        """
        Complete stabilization pipeline
        
        Returns:
            Dict with stabilized score, action, and metadata
        """
        
        # 1. Smooth score
        smoothed_score = self.smooth_score(raw_score)
        
        # 2. Map to action
        proposed_action = self.score_to_action(smoothed_score)
        
        # 3. Apply hysteresis
        hysteresis_action = self.apply_hysteresis(smoothed_score, proposed_action)
        
        # 4. Validate (require N consecutive)
        final_action = self.validate_action(hysteresis_action)
        
        # 5. Update history
        self.history.add(smoothed_score, final_action)
        self.last_action = final_action
        
        # 6. Calculate conviction (how stable is signal?)
        conviction = self._calculate_conviction()
        
        return {
            'raw_score': raw_score,
            'smoothed_score': smoothed_score,
            'raw_action': raw_action,
            'proposed_action': proposed_action,
            'final_action': final_action,
            'confidence': confidence,
            'conviction': conviction,
            'validation_progress': f"{self.validation_count}/{self.validation_periods}",
            'action_changed': final_action != self.last_action,
            'score_change': smoothed_score - self.history.scores[-2] if len(self.history.scores) >= 2 else 0
        }
    
    def _calculate_conviction(self) -> float:
        """
        Calculate signal conviction (0.0-1.0)
        
        High conviction = consistent recent signals
        Low conviction = volatile/changing signals
        """
        
        if len(self.history.actions) < 5:
            return 0.5  # Neutral when not enough history
        
        # Check recent action consistency
        recent_actions = list(self.history.actions)[-5:]
        action_changes = sum(1 for i in range(1, len(recent_actions)) 
                           if recent_actions[i] != recent_actions[i-1])
        
        # Check score volatility
        recent_scores = list(self.history.scores)[-10:]
        score_std = np.std(recent_scores) if len(recent_scores) > 1 else 0
        
        # Combine
        action_stability = 1.0 - (action_changes / 4)  # 0-4 changes → 1.0-0.0
        score_stability = 1.0 / (1.0 + score_std / 10)  # Lower std = higher stability
        
        conviction = (action_stability * 0.6 + score_stability * 0.4)
        
        return max(0.0, min(1.0, conviction))
    
    # =========================================================================
    # DIAGNOSTICS
    # =========================================================================
    
    def get_summary(self) -> str:
        """Human-readable summary"""
        
        if not self.history.scores:
            return "No history yet"
        
        lines = []
        lines.append(f"Current EMA Score: {self.ema_score:.1f}")
        lines.append(f"Current Action: {self.last_action}")
        
        if self.action_candidate:
            lines.append(f"Candidate Action: {self.action_candidate} ({self.validation_count}/{self.validation_periods})")
        
        conviction = self._calculate_conviction()
        lines.append(f"Conviction: {conviction:.1%}")
        
        # Recent history
        if len(self.history.scores) >= 5:
            recent_scores = list(self.history.scores)[-5:]
            lines.append(f"Recent scores: {[f'{s:.1f}' for s in recent_scores]}")
        
        return "\n".join(lines)


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == '__main__':
    stabilizer = SignalStabilizer(
        ema_alpha=0.3,
        hysteresis_threshold=10.0,
        validation_periods=2
    )
    
    print("\n" + "="*60)
    print("SIGNAL STABILIZER - WHIPSAW PREVENTION")
    print("="*60)
    
    # Simulate volatile on-chain scores
    scenarios = [
        (62, 'HOLD', 0.81),
        (35, 'REDUCE_20', 0.81),   # Sudden drop
        (30, 'REDUCE_35', 0.81),   # Still low
        (65, 'ADD_SMALL', 0.81),   # Sudden jump
        (70, 'ADD_SMALL', 0.81),   # Confirmed high
        (60, 'HOLD', 0.81),        # Back to neutral
        (58, 'HOLD', 0.81),
    ]
    
    for i, (raw_score, raw_action, conf) in enumerate(scenarios, 1):
        result = stabilizer.stabilize(raw_score, raw_action, conf)
        
        print(f"\n📊 Period {i}:")
        print(f"  Raw: {raw_score:.0f} → {raw_action}")
        print(f"  Smoothed: {result['smoothed_score']:.1f}")
        print(f"  Final: {result['final_action']} (conviction: {result['conviction']:.1%})")
        if result['action_changed']:
            print(f"  ⚠️  ACTION CHANGED")
    
    print("\n" + "="*60)
    print(stabilizer.get_summary())
    print("="*60)
