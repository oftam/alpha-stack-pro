"""
Final Arbiter - The Commander
Provides definitive GO/NO-GO decisions based on hierarchy of signals

Military-grade decision making:
- Intelligence gathered (modules)
- Analysis complete (decision support)
- FINAL CALL made here
"""

from typing import Dict, Literal
from dataclasses import dataclass


@dataclass
class FinalDecision:
    """Final executable decision"""
    action: Literal['BUY', 'SELL', 'HOLD']
    size_multiplier: float
    confidence: float
    reason: str
    override_applied: bool = False
    override_reason: str = ""


class FinalArbiter:
    """
    The buck stops here.
    
    Hierarchy of decision making:
    1. Safety (Gates) - VETO power
    2. Extreme Regimes - OVERRIDE power  
    3. Signal Validation - CONFIRMATION power
    4. Decision Support - EXECUTION power
    """
    
    def __init__(self):
        # Thresholds for extreme conditions
        self.extreme_fear_threshold = 20  # F&G < 20 = extreme
        self.extreme_greed_threshold = 80  # F&G > 80 = extreme
        self.extreme_onchain_threshold = 80  # On-chain > 80 = strong
        self.minimum_confidence = 0.7  # 70% minimum to act
        
    def decide(self, 
               elite_results: Dict,
               decision_summary: Dict) -> FinalDecision:
        """
        Make final GO/NO-GO decision
        
        Args:
            elite_results: Full results from analyze_elite()
            decision_summary: Output from generate_decision_summary()
            
        Returns:
            FinalDecision with clear action
        """
        
        # Extract key signals
        gates = elite_results.get('gates', {})
        allow_trade = gates.get('allow_trade', False)
        
        regime_info = elite_results.get('regime', {})
        regime = regime_info.get('regime', 'unknown')
        regime_conf = regime_info.get('confidence', 0.0)
        
        onchain = elite_results.get('onchain', {})
        diffusion_score = onchain.get('diffusion_score', 50)
        # Fear & Greed comes as nested dict {'value': X, 'classification': ...}
        fg_data = onchain.get('fear_greed', {})
        fg_index = fg_data.get('value', 50) if isinstance(fg_data, dict) else 50
        
        stabilizer = elite_results.get('stabilized', {})
        validation = stabilizer.get('validation_periods', 0) if stabilizer else 0
        
        confidence = elite_results.get('confidence', 0.0)
        
        decision_dir = decision_summary.get('direction', 'HOLD')
        decision_size = decision_summary.get('size_multiplier', 0.0)
        
        # LEVEL 1: Safety Gates (VETO)
        if not allow_trade:
            return FinalDecision(
                action='HOLD',
                size_multiplier=0.0,
                confidence=confidence,
                reason="🚫 Execution gates FAILED - safety veto",
                override_applied=False
            )
        
        # LEVEL 2: Extreme Regimes (OVERRIDE)
        override = self._check_extreme_override(
            regime, regime_conf, fg_index, diffusion_score
        )
        
        if override['should_override']:
            return FinalDecision(
                action=override['action'],
                size_multiplier=override['size'],
                confidence=confidence,
                reason=override['reason'],
                override_applied=True,
                override_reason="Extreme market conditions bypass normal confirmation"
            )
        
        # LEVEL 3: Signal Validation (CONFIRMATION)
        if decision_dir != 'HOLD':
            # Non-extreme conditions require stabilizer confirmation
            if validation < 2:
                return FinalDecision(
                    action='HOLD',
                    size_multiplier=0.0,
                    confidence=confidence,
                    reason=f"⏸️ Awaiting signal confirmation ({validation}/2 periods)",
                    override_applied=False
                )
        
        # LEVEL 4: Execute Decision Support (NORMAL)
        if confidence < self.minimum_confidence:
            return FinalDecision(
                action='HOLD',
                size_multiplier=0.0,
                confidence=confidence,
                reason=f"⚠️ Confidence too low ({confidence:.0%} < {self.minimum_confidence:.0%})",
                override_applied=False
            )
        
        # All checks passed - execute
        return FinalDecision(
            action=decision_dir,
            size_multiplier=decision_size,
            confidence=confidence,
            reason=f"✅ All systems GO - {decision_summary.get('reasoning', '')}",
            override_applied=False
        )
    
    def _check_extreme_override(self, regime: str, regime_conf: float, 
                                fg_index: float, diffusion_score: float) -> Dict:
        """
        Check if extreme conditions warrant override of normal rules
        
        Returns dict with:
        - should_override: bool
        - action: str
        - size: float
        - reason: str
        """
        
        # Blood in Streets: Extreme fear + strong accumulation
        if regime == 'blood_in_streets' and regime_conf > 0.8:
            if fg_index < self.extreme_fear_threshold and diffusion_score > self.extreme_onchain_threshold:
                return {
                    'should_override': True,
                    'action': 'BUY',
                    'size': 1.5,  # Aggressive sizing
                    'reason': f"🩸 BLOOD IN STREETS: F&G={fg_index:.0f}, On-chain={diffusion_score:.0f} - EXECUTE IMMEDIATELY"
                }
        
        # Capitulation: Extreme fear but weak accumulation
        if regime == 'capitulation' and regime_conf > 0.8:
            if fg_index < self.extreme_fear_threshold:
                return {
                    'should_override': True,
                    'action': 'BUY',
                    'size': 1.0,  # Normal sizing (less conviction)
                    'reason': f"😰 CAPITULATION: F&G={fg_index:.0f} - Accumulation weak, moderate buy"
                }
        
        # Distribution Top: Extreme greed + distribution
        if regime == 'distribution_top' and regime_conf > 0.8:
            if fg_index > self.extreme_greed_threshold:
                return {
                    'should_override': True,
                    'action': 'SELL',
                    'size': 1.2,
                    'reason': f"📤 DISTRIBUTION TOP: F&G={fg_index:.0f} - SELL IMMEDIATELY"
                }
        
        # Deleveraging: Funding crisis
        if regime == 'deleveraging' and regime_conf > 0.8:
            return {
                'should_override': True,
                'action': 'HOLD',
                'size': 0.0,
                'reason': "⚡ DELEVERAGING: Systemic risk - STAND DOWN"
            }
        
        # Squeeze risks: No override, let normal process handle
        # Normal: No override
        
        return {
            'should_override': False,
            'action': 'HOLD',
            'size': 0.0,
            'reason': ''
        }
    
    def format_decision(self, decision: FinalDecision) -> str:
        """
        Format decision as clear GO/NO-GO order
        
        Military-style formatting:
        - Clear action
        - Clear reasoning
        - Clear parameters
        """
        
        lines = []
        lines.append("=" * 60)
        lines.append("🎯  FINAL DECISION")
        lines.append("=" * 60)
        
        # Action line
        if decision.action == 'BUY':
            emoji = "📈"
            status = "🟢 GO"
        elif decision.action == 'SELL':
            emoji = "📉"
            status = "🔴 GO"
        else:
            emoji = "⏸️"
            status = "🟡 NO-GO"
        
        lines.append(f"\n{status} - {emoji} {decision.action}")
        
        # Size
        if decision.size_multiplier > 0:
            lines.append(f"Size: {decision.size_multiplier:.2f}x")
        
        # Confidence
        conf_emoji = "🟢" if decision.confidence >= 0.9 else "🟡" if decision.confidence >= 0.7 else "🔴"
        lines.append(f"Confidence: {conf_emoji} {decision.confidence:.0%}")
        
        # Reason
        lines.append(f"\nReason: {decision.reason}")
        
        # Override notice
        if decision.override_applied:
            lines.append(f"\n⚠️ OVERRIDE: {decision.override_reason}")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)


# Example usage
if __name__ == "__main__":
    # Simulate current market condition
    elite_results = {
        'gates': {'allow_trade': True},
        'regime': {
            'regime': 'blood_in_streets',
            'confidence': 1.0
        },
        'onchain': {
            'diffusion_score': 100,
            'fear_greed_index': 11
        },
        'stabilized': {
            'validation_periods': 0
        },
        'confidence': 0.98
    }
    
    decision_summary = {
        'direction': 'BUY',
        'size_multiplier': 1.5,
        'reasoning': 'Elite score strong + positive manifold'
    }
    
    arbiter = FinalArbiter()
    decision = arbiter.decide(elite_results, decision_summary)
    
    print(arbiter.format_decision(decision))
