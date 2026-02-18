"""
Elite v20 - Memory Engine
==========================
Retrieves relevant historical context for Claude injection.

Provides Claude with:
- Last 7 days of signals
- Top 5 similar past scenarios (regime-aware)
- Performance stats
"""

from typing import List, Dict, Optional
from datetime import date, timedelta

try:
    from modules.supabase_client import get_client
    from modules.cohere_embeddings import get_embedder
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False
    print("⚠️ Dependencies not available")


class MemoryEngine:
    """
    Builds context for Claude from organizational memory.
    
    Usage:
        engine = MemoryEngine()
        context = engine.build_context_for_claude(current_signal)
        
        # Inject into Claude prompt
        prompt = f"{context}\n\nUser question: {user_question}"
    """
    
    def __init__(self):
        """Initialize with database and embeddings access."""
        if not DEPENDENCIES_AVAILABLE:
            print("⚠️ Memory Engine disabled (dependencies missing)")
            self.enabled = False
            return
        
        try:
            self.db = get_client()
            self.embedder = get_embedder()
            self.enabled = True
            print("✅ Memory Engine initialized")
        except Exception as e:
            print(f"❌ Memory Engine failed to initialize: {e}")
            self.enabled = False
    
    def build_context_for_claude(
        self,
        current_signal: Dict,
        include_recent: int = 7,
        include_similar: int = 5,
        include_failures: bool = True  # PRO ENHANCEMENT
    ) -> str:
        """
        Build complete memory context for Claude (PRO VERSION).
        
        Args:
            current_signal: Current market conditions
            include_recent: Days of recent history to include
            include_similar: Number of similar scenarios to find
            include_failures: Include known failure patterns (PRO)
        
        Returns:
            Formatted context string for Claude prompt
        """
        if not self.enabled:
            return ""
        
        try:
            parts = ["=== ORGANIZATIONAL MEMORY ===\n"]
            
            # Part 1: Recent history (last N days)
            recent_context = self._get_recent_history(days=include_recent)
            if recent_context:
                parts.append("📊 RECENT HISTORY (Last 7 Days):")
                parts.append(recent_context)
                parts.append("")
            
            # Part 2: Similar scenarios
            similar_context = self._get_similar_scenarios(
                current_signal,
                top_k=include_similar
            )
            if similar_context:
                parts.append("🔍 SIMILAR PAST SCENARIOS:")
                parts.append(similar_context)
                parts.append("")
            
            # Part 3: Performance stats
            stats_context = self._get_performance_stats()
            if stats_context:
                parts.append("📈 PERFORMANCE STATS:")
                parts.append(stats_context)
                parts.append("")
            
            # PRO ENHANCEMENT Part 4: Failure Patterns
            if include_failures:
                failure_context = self._get_failure_patterns(current_signal)
                if failure_context:
                    parts.append("🚨 KNOWN FAILURE PATTERNS (Learn from mistakes):")
                    parts.append(failure_context)
                    parts.append("")
            
            parts.append("=== END MEMORY ===\n")
            
            return "\n".join(parts)
            
        except Exception as e:
            print(f"❌ Failed to build context: {e}")
            return ""
    
    def _get_recent_history(self, days: int = 7) -> str:
        """Get last N days of signals and recommendations."""
        try:
            signals = self.db.get_recent_signals(days=days)
            
            if not signals:
                return "No recent history available."
            
            lines = []
            for sig in signals:
                date_str = sig.get('date', 'Unknown')
                price = sig.get('price', 0)
                manifold = sig.get('manifold_dna', 0)
                onchain = sig.get('onchain_score', 0)
                fear = sig.get('fear_index', 50)
                regime = sig.get('regime', 'UNKNOWN')
                signal_strength = sig.get('signal_strength', 'N/A')
                
                lines.append(
                    f"• {date_str}: ${price:,.0f} | "
                    f"Manifold: {manifold} | OnChain: {onchain} | Fear: {fear} | "
                    f"Regime: {regime} | Signal: {signal_strength}"
                )
            
            return "\n".join(lines)
            
        except Exception as e:
            print(f"⚠️ Failed to get recent history: {e}")
            return ""
    
    def _get_similar_scenarios(self, current_signal: Dict, top_k: int = 5) -> str:
        """Find and format similar past scenarios."""
        try:
            # Get current conditions
            manifold = current_signal.get('manifold_dna', 0)
            onchain = current_signal.get('onchain_score', 0)
            fear = current_signal.get('fear_index', 50)
            regime = current_signal.get('regime', 'UNKNOWN')
            
            # Create embedding
            current_vector = self.embedder.embed_signal(
                manifold=manifold,
                onchain=onchain,
                fear=fear,
                regime=regime
            )
            
            # Find similar
            similar = self.db.find_similar_responses(
                embedding=current_vector,
                regime=regime,
                top_k=top_k
            )
            
            if not similar:
                return f"No similar scenarios found in {regime} regime."
            
            lines = []
            for i, scenario in enumerate(similar, 1):
                timestamp = scenario.get('timestamp', 'Unknown')
                recommendation = scenario.get('recommendation', 'N/A')
                confidence = scenario.get('confidence', 0)
                reasoning = scenario.get('reasoning', '')[:100]  # First 100 chars
                
                lines.append(
                    f"{i}. {timestamp}: Recommended {recommendation} "
                    f"(Confidence: {confidence:.0f}%)\n"
                    f"   Reasoning: {reasoning}..."
                )
            
            return "\n".join(lines)
            
        except Exception as e:
            print(f"⚠️ Failed to find similar scenarios: {e}")
            return ""
    
    def _get_performance_stats(self, days: int = 30) -> str:
        """Get win rate and performance metrics."""
        try:
            stats = self.db.get_win_rate(days=days)
            
            win_rate = stats.get('win_rate', 0)
            avg_pnl = stats.get('avg_pnl', 0)
            total_trades = stats.get('total_trades', 0)
            
            return (
                f"Win Rate (30d): {win_rate:.1f}% ({total_trades} trades)\n"
                f"Average P&L: {avg_pnl:+.1f}%"
            )
            
        except Exception as e:
            print(f"⚠️ Failed to get performance stats: {e}")
            return ""
    
    def _get_failure_patterns(self, current_signal: Dict) -> str:
        """
        PRO ENHANCEMENT: Get relevant failure patterns to warn Claude.
        
        Returns formatted list of past failures in similar setups.
        """
        try:
            regime = current_signal.get('regime', 'UNKNOWN')
            
            # TODO: Implement after SQL deployment
            # For now, return placeholder
            # failures = self.db.get_failure_patterns(regime=regime, limit=3)
            
            # Placeholder response
            return ""
            
            # Future implementation:
            # if not failures:
            #     return f"No known failure patterns in {regime} regime."
            # 
            # lines = []
            # for i, failure in enumerate(failures, 1):
            #     setup = failure.get('signal_setup', 'Unknown')[:80]
            #     reason = failure.get('failure_reason', 'Unknown')[:100]
            #     lesson = failure.get('lesson_learned', 'Unknown')[:120]
            #     loss = failure.get('loss_amount_pct', 0)
            #     
            #     lines.append(
            #         f"{i}. Setup: {setup}...\n"
            #         f"   Failed because: {reason}\n"
            #         f"   Loss: {loss:.1f}%\n"
            #         f"   Lesson: {lesson}..."
            #     )
            # 
            # return "\n\n".join(lines)
            
        except Exception as e:
            print(f"⚠️ Failed to get failure patterns: {e}")
            return ""


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def get_engine() -> MemoryEngine:
    """
    Get singleton MemoryEngine instance.
    
    Usage:
        from modules.memory_engine import get_engine
        engine = get_engine()
        context = engine.build_context_for_claude(signal)
    """
    if not hasattr(get_engine, '_instance'):
        get_engine._instance = MemoryEngine()
    return get_engine._instance


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("🧪 Testing Memory Engine...")
    
    engine = MemoryEngine()
    
    if engine.enabled:
        # Test build_context
        print("\n1. Testing build_context_for_claude()...")
        
        current_signal = {
            'manifold_dna': 87,
            'onchain_score': 84,
            'fear_index': 12,
            'regime': 'BLOOD_IN_STREETS'
        }
        
        context = engine.build_context_for_claude(current_signal)
        
        print("\n" + "="*60)
        print(context)
        print("="*60)
        
        print("\n✅ All tests passed!")
    else:
        print("\n⚠️ Engine disabled - configure Supabase and Cohere first")
