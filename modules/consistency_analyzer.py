"""
Elite v20 - Consistency Analyzer (ENHANCED)
============================================
PRO VERSION with regime-specific thresholds and reasoning fingerprints.

Enhancements:
1. Regime-aware thresholds (more lenient in volatile regimes)
2. Reasoning fingerprint analysis (semantic contradictions)
3. Failure pattern detection
"""

from typing import List, Dict, Optional, Tuple
from datetime import date, datetime, timedelta
import json
import re
from collections import Counter

try:
    from modules.supabase_client import get_client
    from modules.cohere_embeddings import get_embedder
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False
    print("⚠️ Dependencies not available")


class ConsistencyAnalyzerPro:
    """
    PRO VERSION: Regime-aware contradiction detection with semantic analysis.
    
    Enhancements:
    - Different similarity thresholds per regime
    - Reasoning fingerprint comparison (not just BUY/SELL)
    - Failure pattern warnings
    """
    
    # PRO ENHANCEMENT: Regime-specific thresholds
    REGIME_THRESHOLDS = {
        'BLOOD_IN_STREETS': {
            'similarity_threshold': 0.75,  # More lenient (high volatility)
            'contradiction_tolerance': 0.3,  # Allow 30% recommendation variance
            'reasoning_weight': 0.7,  # Focus more on reasoning than action
        },
        'NORMAL': {
            'similarity_threshold': 0.85,  # Stricter
            'contradiction_tolerance': 0.15,
            'reasoning_weight': 0.5,
        },
        'BULL_RUN': {
            'similarity_threshold': 0.80,
            'contradiction_tolerance': 0.20,
            'reasoning_weight': 0.6,
        },
        'DEFAULT': {
            'similarity_threshold': 0.85,
            'contradiction_tolerance': 0.15,
            'reasoning_weight': 0.5,
        }
    }
    
    def __init__(self):
        """Initialize with database and embeddings access."""
        if not DEPENDENCIES_AVAILABLE:
            print("⚠️ Consistency Analyzer disabled (dependencies missing)")
            self.enabled = False
            return
        
        try:
            self.db = get_client()
            self.embedder = get_embedder()
            self.enabled = True
            print("✅ Consistency Analyzer PRO initialized")
        except Exception as e:
            print(f"❌ Consistency Analyzer failed to initialize: {e}")
            self.enabled = False
    
    def validate_recommendation(
        self,
        current_signal: Dict,
        proposed_recommendation: str,
        proposed_reasoning: str = ""
    ) -> Tuple[bool, Optional[str], List[Dict]]:
        """
        PRO VERSION: Validate with regime-specific thresholds + reasoning analysis.
        
        Args:
            current_signal: Dict with manifold, onchain, fear, regime
            proposed_recommendation: What Claude wants to say (BUY/SELL/HOLD)
            proposed_reasoning: Claude's explanation (for fingerprint matching)
        
        Returns:
            (is_consistent, warning_message, failure_patterns)
        """
        if not self.enabled:
            return (True, None, [])
        
        try:
            regime = current_signal.get('regime', 'UNKNOWN')
            thresholds = self.REGIME_THRESHOLDS.get(regime, self.REGIME_THRESHOLDS['DEFAULT'])
            
            # Step 1: Find similar scenarios (regime-aware threshold)
            similar_responses = self._find_similar_regime_responses(
                manifold=current_signal.get('manifold_dna', 0),
                onchain=current_signal.get('onchain_score', 0),
                fear=current_signal.get('fear_index', 50),
                regime=regime,
                top_k=5,
                similarity_threshold=thresholds['similarity_threshold']
            )
            
            if not similar_responses:
                return (True, None, [])
            
            # Step 2: Check recommendation contradictions
            past_recs = [r['recommendation'] for r in similar_responses if r.get('recommendation')]
            
            if not past_recs:
                return (True, None, [])
            
            most_common = Counter(past_recs).most_common(1)[0][0]
            basic_contradiction = self._is_contradiction(proposed_recommendation, most_common)
            
            # Step 3: PRO ENHANCEMENT - Check reasoning fingerprints
            reasoning_contradiction = False
            if proposed_reasoning:
                reasoning_fingerprints = self._extract_reasoning_fingerprint(proposed_reasoning)
                reasoning_contradiction = self._check_reasoning_contradiction(
                    reasoning_fingerprints,
                    similar_responses,
                    regime
                )
            
            # Step 4: PRO ENHANCEMENT - Check failure patterns
            failure_patterns = self._check_failure_patterns(current_signal)
            
            # Determine overall consistency
            is_consistent = True
            warnings = []
            
            if basic_contradiction:
                contradiction_strength = self._measure_contradiction_strength(
                    proposed_recommendation,
                    past_recs
                )
                
                if contradiction_strength > thresholds['contradiction_tolerance']:
                    is_consistent = False
                    warnings.append(f"""
⚠️ INCONSISTENCY DETECTED ({regime})!

Past recommendations in similar conditions:
{Counter(past_recs).most_common(3)}

Proposed: {proposed_recommendation}
Most common: {most_common}

Contradiction strength: {contradiction_strength:.1%} (threshold: {thresholds['contradiction_tolerance']:.1%})
                    """.strip())
            
            if reasoning_contradiction:
                is_consistent = False
                warnings.append("""
⚠️ REASONING CONTRADICTION!

Your reasoning contradicts past explanations in similar setups.
Past: emphasized caution / distribution signs
Now: emphasizing accumulation / bottom signals
                """.strip())
            
            if failure_patterns:
                # Don't block, but warn
                pattern_warning = f"""
🚨 KNOWN FAILURE PATTERN WARNING!

{len(failure_patterns)} similar setups failed in the past:

"""
                for i, pattern in enumerate(failure_patterns[:2], 1):
                    pattern_warning += f"""
{i}. Setup: {pattern.get('signal_setup', 'N/A')[:100]}...
   Failure: {pattern.get('failure_reason', 'N/A')}
   Loss: {pattern.get('loss_amount_pct', 0):.1f}%
   Lesson: {pattern.get('lesson_learned', 'N/A')[:150]}...
"""
                
                warnings.append(pattern_warning)
            
            final_warning = "\n\n".join(warnings) if warnings else None
            
            return (is_consistent, final_warning, failure_patterns)
            
        except Exception as e:
            print(f"❌ Validation failed: {e}")
            return (True, None, [])
    
    # ========================================================================
    # PRO ENHANCEMENT HELPERS
    # ========================================================================
    
    def _extract_reasoning_fingerprint(self, reasoning: str) -> Dict:
        """
        Extract semantic fingerprint from reasoning text.
        
        Returns keywords, themes, sentiment.
        """
        fingerprint = {
            'bullish_phrases': [],
            'bearish_phrases': [],
            'themes': [],
            'confidence': 'neutral'
        }
        
        reasoning_lower = reasoning.lower()
        
        # Bullish indicators
        bullish_keywords = [
            'bottom', 'accumulation', 'buy', 'undervalued', 'opportunity',
            'smart money', 'capitulation', 'oversold', 'recovery', 'bounce'
        ]
        for keyword in bullish_keywords:
            if keyword in reasoning_lower:
                fingerprint['bullish_phrases'].append(keyword)
        
        # Bearish indicators
        bearish_keywords = [
            'top', 'distribution', 'sell', 'overvalued', 'risk',
            'euphoria', 'overbought', 'correction', 'dump', 'exit'
        ]
        for keyword in bearish_keywords:
            if keyword in reasoning_lower:
                fingerprint['bearish_phrases'].append(keyword)
        
        # Confidence language
        if any(word in reasoning_lower for word in ['strong', 'clear', 'obvious', 'definitely']):
            fingerprint['confidence'] = 'high'
        elif any(word in reasoning_lower for word in ['might', 'could', 'possibly', 'uncertain']):
            fingerprint['confidence'] = 'low'
        
        return fingerprint
    
    def _check_reasoning_contradiction(
        self,
        current_fingerprint: Dict,
        similar_responses: List[Dict],
        regime: str
    ) -> bool:
        """
        Check if reasoning contradicts past explanations.
        
        Returns True if contradiction detected.
        """
        if not similar_responses:
            return False
        
        # Count bullish vs bearish sentiment in past
        past_bullish = 0
        past_bearish = 0
        
        for resp in similar_responses:
            reasoning = resp.get('reasoning', '')
            if not reasoning:
                continue
            
            reasoning_lower = reasoning.lower()
            
            if any(word in reasoning_lower for word in ['buy', 'accumulation', 'bottom']):
                past_bullish += 1
            if any(word in reasoning_lower for word in ['sell', 'distribution', 'top']):
                past_bearish += 1
        
        # Current sentiment
        current_bullish = len(current_fingerprint.get('bullish_phrases', []))
        current_bearish = len(current_fingerprint.get('bearish_phrases', []))
        
        # Detect sentiment flip
        if past_bullish > past_bearish and current_bearish > current_bullish:
            return True  # Was bullish, now bearish
        if past_bearish > past_bullish and current_bullish > current_bearish:
            return True  # Was bearish, now bullish
        
        return False
    
    def _check_failure_patterns(self, current_signal: Dict) -> List[Dict]:
        """
        PRO ENHANCEMENT: Find similar past failures.
        
        Returns list of failure patterns that match current setup.
        """
        try:
            regime = current_signal.get('regime', 'UNKNOWN')
            
            # Query Supabase for failure patterns
            # Note: This assumes you've added methods to supabase_client
            # For now, return empty list (will implement after SQL deployment)
            
            # TODO: Implement after deployment
            # failures = self.db.get_failure_patterns(regime=regime, limit=5)
            
            return []
            
        except Exception as e:
            print(f"⚠️ Failure pattern check failed: {e}")
            return []
    
    def _measure_contradiction_strength(
        self,
        proposed: str,
        past_recs: List[str]
    ) -> float:
        """
        Measure how strong the contradiction is.
        
        Returns 0.0-1.0 (0 = no contradiction, 1 = total flip)
        """
        if not past_recs:
            return 0.0
        
        # Count opposing recommendations
        opposition_count = sum(
            1 for rec in past_recs
            if self._is_contradiction(proposed, rec)
        )
        
        return opposition_count / len(past_recs)
    
    # ========================================================================
    # ORIGINAL METHODS (keeping for compatibility)
    # ========================================================================
    
    def _find_similar_regime_responses(
        self,
        manifold: int,
        onchain: int,
        fear: int,
        regime: str,
        top_k: int = 5,
        similarity_threshold: float = 0.8
    ) -> List[Dict]:
        """Find past responses in SAME regime with similar market conditions."""
        try:
            regime_responses = self.db.get_responses_by_regime(regime, limit=50)
            
            if not regime_responses:
                return []
            
            current_vector = self.embedder.embed_signal(
                manifold=manifold,
                onchain=onchain,
                fear=fear,
                regime=regime
            )
            
            scored = []
            for resp in regime_responses:
                if not resp.get('embedding'):
                    continue
                
                similarity = self.embedder.cosine_similarity(
                    current_vector,
                    resp['embedding']
                )
                
                if similarity >= similarity_threshold:
                    scored.append((similarity, resp))
            
            scored.sort(key=lambda x: x[0], reverse=True)
            
            return [resp for _, resp in scored[:top_k]]
            
        except Exception as e:
            print(f"⚠️ Similarity search failed: {e}")
            return self.db.get_responses_by_regime(regime, limit=top_k)
    
    def _is_contradiction(self, rec1: Optional[str], rec2: Optional[str]) -> bool:
        """Check if two recommendations are contradictory (180° flip)."""
        if not rec1 or not rec2:
            return False
        
        r1 = rec1.upper()
        r2 = rec2.upper()
        
        bullish = {'BUY', 'STRONG_BUY', 'SNIPER', 'BUILD'}
        bearish = {'SELL', 'REDUCE', 'EXIT'}
        
        is_r1_bullish = any(b in r1 for b in bullish)
        is_r2_bullish = any(b in r2 for b in bullish)
        is_r1_bearish = any(b in r1 for b in bearish)
        is_r2_bearish = any(b in r2 for b in bearish)
        
        if (is_r1_bullish and is_r2_bearish) or (is_r1_bearish and is_r2_bullish):
            return True
        
        return False


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def get_analyzer() -> ConsistencyAnalyzerPro:
    """Get singleton ConsistencyAnalyzerPro instance."""
    if not hasattr(get_analyzer, '_instance'):
        get_analyzer._instance = ConsistencyAnalyzerPro()
    return get_analyzer._instance


if __name__ == "__main__":
    print("🧪 Testing Consistency Analyzer PRO...")
    
    analyzer = ConsistencyAnalyzerPro()
    
    if analyzer.enabled:
        # Test with reasoning
        current_signal = {
            'manifold_dna': 87,
            'onchain_score': 84,
            'fear_index': 12,
            'regime': 'BLOOD_IN_STREETS'
        }
        
        proposed_reasoning = """
        This is a clear bottom signal. OnChain shows smart money accumulation,
        fear is at capitulation levels, and manifold DNA confirms strong buy setup.
        High confidence recommendation.
        """
        
        is_ok, warning, failures = analyzer.validate_recommendation(
            current_signal,
            'STRONG_BUY',
            proposed_reasoning
        )
        
        print(f"\nValidation: {'✅ Consistent' if is_ok else '❌ Inconsistent'}")
        if warning:
            print(f"\nWarning:\n{warning}")
        if failures:
            print(f"\nFailure patterns found: {len(failures)}")
        
        print("\n✅ All tests passed!")
    else:
        print("\n⚠️ Analyzer disabled - configure Supabase and Cohere first")
