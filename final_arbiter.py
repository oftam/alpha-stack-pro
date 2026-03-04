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

# ── Nature Events Engine (geopolitical black-swan prior adjustment) ──
try:
    from nature_events_engine import NatureEventsEngine
    _NATURE_ARBITER_AVAILABLE = True
except ImportError:
    _NATURE_ARBITER_AVAILABLE = False


@dataclass
class FinalDecision:
    """Final executable decision"""
    action: Literal['BUY', 'SELL', 'HOLD', 'SNIPER_BUY']
    size_multiplier: float
    confidence: float
    reason: str
    override_applied: bool = False
    override_reason: str = ""
    order_type: str = "MARKET"        # MARKET or LIMIT
    limit_price: float = 0.0          # P10 target for SNIPER_BUY


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
        # 🎯 VICTORY PROTOCOL THRESHOLDS
        self.extreme_fear_threshold = 20  
        self.extreme_onchain_threshold = 85  # Institutional baseline
        self.topological_invariant_min = 90  # Simons' Invariant Floor
        self.victory_vector_threshold = 82.3 # The 82.3 Manifold barrier
        self.minimum_confidence = 0.917      # Bayesian Collapse floor
        self.extreme_greed_threshold = 80    # Distribution-top greed ceiling
        self.dca_kill_switch_min = 50        # Kill Switch floor for aggressive DCA
        self.dca_kill_switch_max = 60        # Kill Switch ceiling for aggressive DCA
        # 🌍 Nature Events Engine — Prior suppression on black-swan events
        self._nature_engine = None
        if _NATURE_ARBITER_AVAILABLE:
            try:
                self._nature_engine = NatureEventsEngine()
            except Exception:
                pass
        
    def decide(self, 
               elite_results: Dict,
               decision_summary: Dict) -> FinalDecision:
        """
        Make final GO/NO-GO decision based on the Victory Protocol.
        """
        
        # ── Core decision inputs from upstream ─────────────────────────────
        confidence   = float(elite_results.get('confidence',
                             decision_summary.get('confidence', 0.5)))
        decision_dir  = str(decision_summary.get('direction', 'HOLD')).upper()
        decision_size = float(decision_summary.get('size_multiplier', 0.0))

        # ── 🌍 NATURE EVENTS PRIOR ADJUSTMENT ────────────────────────────────
        # Critical geopolitical events (Bushehr quake, Hormuz blockade) deduct
        # 5-10% from confidence, making it harder to open longs during a
        # black-swan unless OnChain divergence overrides it.
        _nature_prior_adj = 0.0
        if self._nature_engine is not None:
            try:
                self._nature_engine.refresh()
                _nature_prior_adj = self._nature_engine.get_prior_adjustment()
                if _nature_prior_adj != 0.0:
                    confidence = max(0.0, confidence + _nature_prior_adj)
            except Exception:
                pass

        # Extract key signals
        gates = elite_results.get('gates', {})
        allow_trade = gates.get('allow_trade', False)
        
        regime_info = elite_results.get('regime', {})
        regime = regime_info.get('regime', 'unknown').lower()
        
        onchain = elite_results.get('onchain', {})
        diffusion_score = onchain.get('diffusion_score', 0)
        fg_data = onchain.get('fear_greed', {})
        fg_index = fg_data.get('value', 50) if isinstance(fg_data, dict) else 50
        
        manifold_score = elite_results.get('manifold', {}).get('score', 0)
        divergence = elite_results.get('divergence', {}).get('spread', 0)
        
        # DUDU Overlay (Physics)
        dudu = elite_results.get('dudu_overlay', {})
        p10 = dudu.get('p10', 0)
        p50 = dudu.get('p50', 0)
        current_price = elite_results.get('price', 0)
        
        # ── NAOR GENE INJECTION ──────────────────────────────────────────────
        # Boost manifold score with MVRV Topological Invariant before any gate check
        try:
            from modules.module_1_onchain_diffusion import inject_naor_gene
            manifold_score = inject_naor_gene(manifold_score)
        except Exception:
            pass  # Gene unavailable → neutral (no change)

        # ── NAOR BYPASS (pre-Gate exception) ──────────────────────────────────
        # PATH A: chaos raw penalty < 0.35 + whales > 25% + manifold > 82
        # PATH B: DUDU violence multiplier < 3.5x + windows > 100 + whales > 25%
        chaos_val     = elite_results.get('chaos', {}).get('violence_score',
                        elite_results.get('chaos_penalty', 1.0))
        whale_score   = elite_results.get('onchain', {}).get('components', {}).get('whale', 0)

        dudu_overlay  = elite_results.get('dudu_overlay', {})
        violence_mult = float(dudu_overlay.get('violence_multiplier',
                        dudu_overlay.get('violence_x', 9.9)))   # default=9.9 → no bypass
        dudu_windows  = int(dudu_overlay.get('windows_used',
                        dudu_overlay.get('n_windows', 0)))

        bypass_path_a = (
            float(chaos_val)      < 0.35 and
            float(whale_score)    > 25.0 and
            float(manifold_score) > 82.0
        )
        bypass_path_b = (
            violence_mult         < 3.5  and   # elevated but NOT systemic
            dudu_windows          > 100  and   # statistically valid (451 > 100 ✓)
            float(whale_score)    > 25.0       # whales still accumulating
        )
        naor_bypass_active = bypass_path_a or bypass_path_b

        if naor_bypass_active and not allow_trade:
            path_label = "A:Chaos" if bypass_path_a else "B:Violence"
            return FinalDecision(
                action='BUY',
                size_multiplier=0.05,
                confidence=min(1.0, confidence + 0.10),
                reason=(
                    f"🧬 NAOR BYPASS [{path_label}]: "
                    f"Violence={violence_mult:.1f}x | Windows={dudu_windows} | "
                    f"Whales={float(whale_score):.0f}% | Manifold={manifold_score:.1f} | "
                    f"Gate overridden → Kelly 5% DCA"
                ),
                override_applied=True,
                override_reason="Naor Topological Invariant — Violence is Local, not Systemic"
            )

        # ── STREET SMART BYPASS (Sprint 10 — Whale Liquidation Hunt) ─────
        # If chaos is EXTREME (>2.0) but whales are accumulating (diffusion>=90)
        # AND physics boundary is ready (price near P10), this is a manufactured
        # panic dip. Override stress gate veto → SNIPER_BUY @ LIMIT P10.
        manipulation_flag = gates.get('manipulation_flag', False)
        if not manipulation_flag:
            # Manual check if gates didn't pass it through
            chaos_score_raw = elite_results.get('chaos', {}).get('violence_score', 0)
            manipulation_flag = (float(chaos_score_raw) > 2.0 and diffusion_score >= 90)

        if manipulation_flag and is_physics_ready and not allow_trade:
            return FinalDecision(
                action='SNIPER_BUY',
                size_multiplier=0.5,
                confidence=min(1.0, confidence + 0.05) if isinstance(confidence, (int, float)) else 0.5,
                reason=(
                    f"🎯 STREET SMART BYPASS: Chaos Spike (>{2.0}) + "
                    f"Whales Accumulating ({diffusion_score}/100) @P10={p10:,.0f}"
                ),
                override_applied=True,
                override_reason="Whale Liquidation Hunt Detected — STRICT LIMIT AT P10",
                order_type="LIMIT",
                limit_price=p10
            )

        # LEVEL 1: Safety Gates (VETO)
        if not allow_trade:
            # Gene Silencing: Confidence cannot exceed 50% if gates are closed
            suppressed_confidence = min(confidence, 0.5)
            return FinalDecision(
                action='HOLD',
                size_multiplier=0.0,
                confidence=suppressed_confidence,
                reason=f"🚫 EXECUTION GATES CLOSED: Safety veto active. Confidence suppressed to {suppressed_confidence:.1%}.",
                override_applied=False
            )
        
        # LEVEL 2: The Victory Protocol (Execution Trigger)
        # "Only when all conditions align, the status changes to EXECUTE"
        
        # Physics Boundary: current_price < p10 + (p50 - p10) * 0.3
        p10_limit = p10 + (p50 - p10) * 0.3 if p50 > p10 else 0
        is_physics_ready = current_price < p10_limit if p10_limit > 0 else False
        
        # Operational Override: Operator DCA (Aggressive Accumulation in White Noise)
        # Triggered by On-chain = 100/100 despite HOLD regime
        if diffusion_score == 100 and abs(divergence) >= 15 and is_physics_ready:
            # Check Kill Switch
            if diffusion_score <= self.dca_kill_switch_max:
                return FinalDecision(
                    action='HOLD',
                    size_multiplier=0.0,
                    confidence=confidence,
                    reason="🛑 DCA KILL SWITCH TRIPPED: Whale accumulation retreating.",
                    override_applied=True,
                    override_reason="Liquidity Invariant Breach"
                )
            
            return FinalDecision(
                action='BUY',
                size_multiplier=1.25, # Operator DCA multiplier
                confidence=confidence,
                reason=f"🏹 OPERATOR DCA ACTIVE: High On-chain Divergence (100) vs Static Regime.",
                override_applied=True,
                override_reason="Whale X-Ray Divergence Overprice"
            )
            
        # 🪐 TOPOLOGICAL INVARIANT BUY (Simons' TQFT Rule)
        # On-chain Invariant >= 90 + Bullish Divergence = "Buy despite falling price"
        if diffusion_score >= self.topological_invariant_min and divergence >= 10:
             return FinalDecision(
                action='BUY',
                size_multiplier=1.35, 
                confidence=confidence,
                reason=f"🪐 TOPOLOGICAL INVARIANT: Invariant {diffusion_score} >= {self.topological_invariant_min}% (Whales Stable, Price Noise).",
                override_applied=True,
                override_reason="Chern-Simons Invariant Alignment"
            )

        # The Core Victory Vector Check
        if (regime == 'blood_in_streets' and 
            manifold_score >= self.victory_vector_threshold and
            diffusion_score >= self.extreme_onchain_threshold and
            abs(divergence) >= 10 and
            is_physics_ready and
            confidence >= self.minimum_confidence):
            
            return FinalDecision(
                action='BUY',
                size_multiplier=1.5,
                confidence=confidence,
                reason=f"🎯 VICTORY VECTOR TRIGGERED: Manifold {manifold_score:.1f}, Confidence {confidence:.1%}",
                override_applied=True,
                override_reason="Victory Protocol Simultaneous Threshold Crossing"
            )

        # LEVEL 3: Topological Exit Rule
        # "Stop only if Topology breaks" (Exit logic)
        if decision_dir == 'SELL' or decision_dir == 'HOLD':
            # If we have an existing position, check if topology is still intact
            # If On-chain > 85, we HOLD even if price is oscillating or "stop loss" hit
            if diffusion_score >= self.extreme_onchain_threshold:
                 return FinalDecision(
                    action='HOLD',
                    size_multiplier=0.0,
                    confidence=confidence,
                    reason=f"🏛️ TOPOLOGICAL HOLD: Topology is stable ({diffusion_score} >= {self.extreme_onchain_threshold}). Noise ignored.",
                    override_applied=True,
                    override_reason="Simons' Invariant Stay-In Rule"
                )

        # LEVEL 4: Standard Confirmation & Gene Silencing
        if confidence < self.minimum_confidence:
            return FinalDecision(
                action='HOLD',
                size_multiplier=0.0,
                confidence=confidence,
                reason=f"🧬 GENE SILENCING: Bayesian confidence below collapse threshold ({confidence:.1%} < {self.minimum_confidence:.1%})",
                override_applied=False
            )
        
        # Final Fallback
        valid_action = decision_dir if decision_dir in ('BUY', 'SELL', 'HOLD') else 'HOLD'
        return FinalDecision(
            action=valid_action if confidence >= self.minimum_confidence else 'HOLD',  # type: ignore[arg-type]
            size_multiplier=decision_size if confidence >= self.minimum_confidence else 0.0,
            confidence=confidence,
            reason=f"📋 REGULAR MODE: {decision_summary.get('reasoning', 'Awaiting clear signals.')}",
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
        elif decision.action == 'SNIPER_BUY':
            emoji = "🎯"
            status = "🟢 SNIPER GO"
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
        
        # SNIPER_BUY: enforce LIMIT order at P10
        if decision.action == 'SNIPER_BUY' and decision.limit_price > 0:
            lines.append(f"\n📍 ORDER TYPE: LIMIT @ ${decision.limit_price:,.0f} (P10 Floor)")
            lines.append("⚠️ NO MARKET ORDERS — Whale Slippage Protection Active")
        
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
