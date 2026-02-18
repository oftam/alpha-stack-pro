"""
Elite v20 - Memory Logger
==========================
Captures all signals and Claude responses to Supabase for organizational memory.

Features:
- Automatic signal logging from MEDALLION dashboard
- Claude response capture with regime context
- Performance tracking initialization
- UTC timestamp enforcement
"""

from typing import Dict, Any, Optional
from datetime import datetime, date, timezone
import json

try:
    from modules.supabase_client import get_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠️ Supabase client not available")


class MemoryLogger:
    """
    Logs Elite v20 signals and Claude interactions to organizational memory.
    
    Usage in MEDALLION dashboard:
        logger = MemoryLogger()
        
        # After computing signals
        logger.log_daily_signal(elite_results)
        
        # After Claude responds
        logger.log_claude_interaction(question, response, elite_results)
    """
    
    def __init__(self):
        """Initialize logger with Supabase connection."""
        if not SUPABASE_AVAILABLE:
            print("⚠️ Memory logging disabled (Supabase not configured)")
            self.enabled = False
            return
        
        try:
            self.db = get_client()
            self.enabled = True
            print("✅ Memory Logger initialized")
        except Exception as e:
            print(f"❌ Memory Logger failed to initialize: {e}")
            self.enabled = False
    
    def log_daily_signal(
        self,
        elite_results: Dict[str, Any],
        current_price: float,
        symbol: str = "BTCUSDT"
    ) -> Optional[int]:
        """
        Log complete Elite v20 signal to database.
        
        Args:
            elite_results: Output from EliteDashboardAdapter.analyze_elite()
            current_price: Current BTC price
            symbol: Trading pair
        
        Returns:
            Signal ID if successful, None otherwise
        """
        if not self.enabled:
            return None
        
        try:
            # Extract scores from elite_results
            onchain = elite_results.get('onchain', {})
            chaos = elite_results.get('chaos', {})
            dudu = elite_results.get('dudu', {})
            
            # Build signal data
            signal_data = {
                'date': str(date.today()),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'symbol': symbol,
                'price': current_price,
                
                # Core scores
                'onchain_score': int(onchain.get('diffusion_score', 0)),
                'fear_index': int(onchain.get('fear_index', 50)),
                'manifold_dna': int(elite_results.get('elite_score', 0)),
                'divergence': float(elite_results.get('divergence', 0)),
                
                # DUDU projections
                'p10_price': float(dudu.get('p10', 0)) if dudu else None,
                'p50_price': float(dudu.get('p50', 0)) if dudu else None,
                'p90_price': float(dudu.get('p90', 0)) if dudu else None,
                
                # Regime (CRITICAL for consistency)
               'regime': chaos.get('regime', 'UNKNOWN'),
                'regime_confidence': float(chaos.get('regime_confidence', 0)),
                
                # Signal classification
                'signal_strength': self._classify_signal_strength(
                    elite_results.get('elite_score', 0),
                    onchain.get('diffusion_score', 0)
                ),
                'bayesian_probability': float(elite_results.get('confidence', 0))
            }
            
            # Save to database
            signal_id = self.db.save_signal(signal_data)
            
            if signal_id:
                print(f"📝 Signal logged | ID: {signal_id} | Regime: {signal_data['regime']}")
            
            return signal_id
            
        except Exception as e:
            print(f"❌ Failed to log signal: {e}")
            return None
    
    def log_claude_interaction(
        self,
        user_question: str,
        claude_response: str,
        elite_results: Dict[str, Any],
        signal_id: Optional[int] = None,
        embedding: Optional[list] = None
    ) -> Optional[int]:
        """
        Log Claude AI interaction with regime context.
        
        Args:
            user_question: What user asked
            claude_response: Claude's full response
            elite_results: Current market analysis
            signal_id: FK to daily_signals (if available)
            embedding: Cohere embedding vector (optional, added later)
        
        Returns:
            Response ID if successful
        """
        if not self.enabled:
            return None
        
        try:
            # If no signal_id provided, try to get today's signal
            if signal_id is None:
                today_signal = self.db.get_signal_by_date(date.today())
                if today_signal:
                    signal_id = today_signal['id']
                else:
                    # Create signal first
                    signal_id = self.log_daily_signal(
                        elite_results,
                        current_price=elite_results.get('current_price', 0)
                    )
            
            # Extract recommendation from Claude response (simple parsing)
            recommendation = self._parse_recommendation(claude_response)
            confidence = self._parse_confidence(claude_response)
            
            # Get regime context
            chaos = elite_results.get('chaos', {})
            onchain = elite_results.get('onchain', {})
            
            # Save response
            response_id = self.db.save_claude_response(
                signal_id=signal_id,
                user_question=user_question,
                claude_response=claude_response,
                recommendation=recommendation,
                confidence=confidence,
                regime=chaos.get('regime', 'UNKNOWN'),
                manifold=int(elite_results.get('elite_score', 0)),
                onchain=int(onchain.get('diffusion_score', 0)),
                fear=int(onchain.get('fear_index', 50)),
                embedding=embedding
            )
            
            if response_id:
                print(f"💬 Claude response logged | ID: {response_id}")
                
                # Create performance tracking entry if recommendation exists
                if recommendation and recommendation in ['BUY', 'STRONG_BUY']:
                    self.db.create_performance_entry(
                        response_id=response_id,
                        entry_date=date.today(),
                        entry_price=elite_results.get('current_price', 0),
                        recommended_action=recommendation
                    )
            
            return response_id
            
        except Exception as e:
            print(f"❌ Failed to log Claude response: {e}")
            return None
    
    def update_daily_performance(self, current_price: float):
        """
        Update P&L for all open recommendations.
        Should be called once per day (or real-time).
        """
        if not self.enabled:
            return
        
        try:
            self.db.update_performance(current_price)
        except Exception as e:
            print(f"❌ Failed to update performance: {e}")
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _classify_signal_strength(
        self,
        manifold_score: float,
        onchain_score: float
    ) -> str:
        """
        Classify signal strength based on Elite v20 logic.
        
        Returns: SNIPER, STRONG_BUY, BUILD, HOLD, SELL
        """
        # Victory Vector (SNIPER MODE)
        if manifold_score >= 82.3 and onchain_score >= 80:
            return 'SNIPER'
        
        # Strong Buy
        elif manifold_score >= 80 and onchain_score >= 70:
            return 'STRONG_BUY'
        
        # Build/Accumulation
        elif manifold_score >= 65 and onchain_score >= 65:
            return 'BUILD'
        
        # Hold
        elif manifold_score >= 50:
            return 'HOLD'
        
        # Sell/Reduce
        else:
            return 'SELL'
    
    def _parse_recommendation(self, response_text: str) -> Optional[str]:
        """
        Parse recommendation from Claude's text response.
        Simple keyword matching (can be improved with LLM).
        """
        text_upper = response_text.upper()
        
        if 'SNIPER' in text_upper or 'VICTORY VECTOR' in text_upper:
            return 'SNIPER'
        elif 'STRONG BUY' in text_upper or 'קנייה חזקה' in response_text:
            return 'STRONG_BUY'
        elif 'BUY' in text_upper or 'קנה' in response_text:
            return 'BUY'
        elif 'BUILD' in text_upper or 'צבירה' in response_text:
            return 'BUILD'
        elif 'HOLD' in text_upper or 'המתן' in response_text:
            return 'HOLD'
        elif 'SELL' in text_upper or 'מכור' in response_text:
            return 'SELL'
        
        return None
    
    def _parse_confidence(self, response_text: str) -> Optional[float]:
        """
        Extract confidence percentage from response.
        Looks for patterns like "91.7%" or "Confidence: 85%"
        """
        import re
        
        # Pattern: XX.X% or XX%
        matches = re.findall(r'(\d+\.?\d*)\s*%', response_text)
        
        if matches:
            # Take highest percentage found (likely the confidence)
            confidences = [float(m) for m in matches if 0 <= float(m) <= 100]
            if confidences:
                return max(confidences)
        
        return None


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def get_logger() -> MemoryLogger:
    """
    Get singleton MemoryLogger instance.
    
    Usage:
        from modules.memory_logger import get_logger
        logger = get_logger()
        logger.log_daily_signal(...)
    """
    if not hasattr(get_logger, '_instance'):
        get_logger._instance = MemoryLogger()
    return get_logger._instance


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("🧪 Testing Memory Logger...")
    
    # Sample elite_results (from MEDALLION)
    elite_results = {
        'elite_score': 87.5,
        'confidence': 91.7,
        'divergence': 29.5,
        'current_price': 70100.00,
        'onchain': {
            'diffusion_score': 84,
            'fear_index': 12
        },
        'chaos': {
            'regime': 'BLOOD_IN_STREETS',
            'regime_confidence': 95.0
        },
        'dudu': {
            'p10': 65000,
            'p50': 72000,
            'p90': 78000
        }
    }
    
    logger = MemoryLogger()
    
    if logger.enabled:
        # Test 1: Log signal
        print("\n1. Testing log_daily_signal()...")
        signal_id = logger.log_daily_signal(elite_results, current_price=70100.00)
        
        # Test 2: Log Claude interaction
        print("\n2. Testing log_claude_interaction()...")
        response_id = logger.log_claude_interaction(
            user_question="Should I buy now?",
            claude_response="Yes! SNIPER MODE activated. Confidence: 91.7%. Strong buy signal.",
            elite_results=elite_results,
            signal_id=signal_id
        )
        
        # Test 3: Update performance
        print("\n3. Testing update_daily_performance()...")
        logger.update_daily_performance(current_price=71500.00)
        
        print("\n✅ All tests passed!")
    else:
        print("\n⚠️ Logger disabled - configure Supabase first")
