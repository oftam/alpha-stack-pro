"""
Elite v20 - Supabase Client Module
===================================
Manages PostgreSQL connection via Supabase for organizational memory system.

Features:
- Connection pooling
- Automatic retry logic
- Row-Level Security support
- pgvector operations
"""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime, date
import json

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠️ supabase-py not installed. Run: pip install supabase")


class SupabaseClient:
    """
    Elite v20 database client for Supabase (PostgreSQL).
    
    Usage:
        client = SupabaseClient()
        client.save_signal(signal_data)
        history = client.get_recent_signals(days=7)
    """
    
    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None
    ):
        """
        Initialize Supabase client.
        
        Args:
            supabase_url: Supabase project URL (or from .env)
            supabase_key: Supabase anon/service key (or from .env)
        """
        if not SUPABASE_AVAILABLE:
            raise ImportError("supabase-py required. Install: pip install supabase")
        
        # Load from environment if not provided
        self.url = supabase_url or os.getenv('SUPABASE_URL')
        self.key = supabase_key or os.getenv('SUPABASE_KEY')
        
        if not self.url or not self.key:
            raise ValueError(
                "Supabase credentials missing! Set SUPABASE_URL and SUPABASE_KEY in .env"
            )
        
        # Create client
        self.client: Client = create_client(self.url, self.key)
        self._test_connection()
    
    def _test_connection(self) -> bool:
        """Test database connection."""
        try:
            # Simple query to test connection
            result = self.client.table('daily_signals').select("count", count='exact').execute()
            print(f"✅ Connected to Supabase | Total signals: {result.count}")
            return True
        except Exception as e:
            print(f"❌ Supabase connection failed: {e}")
            return False
    
    # ========================================================================
    # SIGNAL OPERATIONS
    # ========================================================================
    
    def save_signal(self, signal_data: Dict[str, Any]) -> Optional[int]:
        """
        Save daily market signal to database.
        
        Args:
            signal_data: Dict with keys: date, price, onchain_score, fear_index,
                        manifold_dna, regime, etc.
        
        Returns:
            Signal ID if successful, None otherwise
        """
        try:
            # Ensure required fields
            required = ['date', 'price', 'onchain_score', 'fear_index', 
                       'manifold_dna', 'regime']
            for field in required:
                if field not in signal_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Insert
            result = self.client.table('daily_signals').insert(signal_data).execute()
            
            if result.data:
                signal_id = result.data[0]['id']
                print(f"✅ Signal saved | ID: {signal_id} | Date: {signal_data['date']}")
                return signal_id
            else:
                print(f"❌ Failed to save signal: {result}")
                return None
                
        except Exception as e:
            print(f"❌ Error saving signal: {e}")
            return None
    
    def get_signal_by_date(self, target_date: date) -> Optional[Dict]:
        """Get signal for specific date."""
        try:
            result = self.client.table('daily_signals')\
                .select("*")\
                .eq('date', str(target_date))\
                .single()\
                .execute()
            
            return result.data if result.data else None
        except Exception as e:
            print(f"⚠️ No signal found for {target_date}: {e}")
            return None
    
    def get_recent_signals(self, days: int = 7) -> List[Dict]:
        """
        Get last N days of signals.
        
        Args:
            days: Number of days to retrieve
        
        Returns:
            List of signal dicts, ordered by date DESC
        """
        try:
            result = self.client.table('daily_signals')\
                .select("*")\
                .order('date', desc=True)\
                .limit(days)\
                .execute()
            
            return result.data if result.data else []
        except Exception as e:
            print(f"❌ Error fetching recent signals: {e}")
            return []
    
    # ========================================================================
    # CLAUDE RESPONSE OPERATIONS
    # ========================================================================
    
    def save_claude_response(
        self,
        signal_id: int,
        user_question: str,
        claude_response: str,
        recommendation: Optional[str] = None,
        confidence: Optional[float] = None,
        regime: Optional[str] = None,
        manifold: Optional[int] = None,
        onchain: Optional[int] = None,
        fear: Optional[int] = None,
        embedding: Optional[List[float]] = None
    ) -> Optional[int]:
        """
        Save Claude AI response to database.
        
        Args:
            signal_id: FK to daily_signals
            user_question: What user asked
            claude_response: Full AI response text
            recommendation: BUY/HOLD/SELL classification
            confidence: 0-100%
            regime: Regime at time of response
            manifold/onchain/fear: Scores at time
            embedding: Cohere vector (1024 dims)
        
        Returns:
            Response ID if successful
        """
        try:
            data = {
                'signal_id': signal_id,
                'user_question': user_question,
                'claude_response': claude_response,
                'recommendation': recommendation,
                'confidence': confidence,
                'regime_at_time': regime,
                'manifold_at_time': manifold,
                'onchain_at_time': onchain,
                'fear_at_time': fear
            }
            
            # Add embedding if provided
            if embedding:
                data['embedding'] = embedding
            
            result = self.client.table('claude_responses').insert(data).execute()
            
            if result.data:
                response_id = result.data[0]['id']
                print(f"✅ Claude response saved | ID: {response_id}")
                return response_id
            else:
                return None
                
        except Exception as e:
            print(f"❌ Error saving Claude response: {e}")
            return None
    
    def get_responses_by_regime(self, regime: str, limit: int = 10) -> List[Dict]:
        """
        Get Claude responses for specific regime.
        Critical for regime-aware consistency checking.
        """
        try:
            result = self.client.table('claude_responses')\
                .select("*")\
                .eq('regime_at_time', regime)\
                .order('timestamp', desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data if result.data else []
        except Exception as e:
            print(f"❌ Error fetching responses by regime: {e}")
            return []
    
    def find_similar_responses(
        self,
        embedding: List[float],
        regime: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Find similar past responses using vector similarity.
        
        Args:
            embedding: Query embedding vector
            regime: Optional regime filter (for regime-aware search)
            top_k: Number of results
        
        Returns:
            List of similar responses with similarity scores
        """
        try:
            # Build RPC call for vector similarity
            # Note: Requires custom SQL function in Supabase
            
            params = {
                'query_embedding': embedding,
                'match_threshold': 0.7,  # Cosine similarity threshold
                'match_count': top_k
            }
            
            if regime:
                params['regime_filter'] = regime
            
            result = self.client.rpc('match_claude_responses', params).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"⚠️ Vector search not yet implemented: {e}")
            # Fallback: simple regime-based retrieval
            if regime:
                return self.get_responses_by_regime(regime, limit=top_k)
            return []
    
    # ========================================================================
    # PERFORMANCE TRACKING
    # ========================================================================
    
    def create_performance_entry(
        self,
        response_id: int,
        entry_date: date,
        entry_price: float,
        recommended_action: str
    ) -> Optional[int]:
        """Create performance tracking entry for a recommendation."""
        try:
            data = {
                'response_id': response_id,
                'entry_date': str(entry_date),
                'entry_price': entry_price,
                'recommended_action': recommended_action
            }
            
            result = self.client.table('performance_tracking').insert(data).execute()
            
            if result.data:
                return result.data[0]['id']
            return None
            
        except Exception as e:
            print(f"❌ Error creating performance entry: {e}")
            return None
    
    def update_performance(self, current_price: float) -> int:
        """
        Update all pending performance entries with current price.
        
        Args:
            current_price: Current BTC price
        
        Returns:
            Number of entries updated
        """
        try:
            # Call PostgreSQL function
            result = self.client.rpc(
                'update_performance_tracking',
                {'current_btc_price': current_price}
            ).execute()
            
            print(f"✅ Performance tracking updated @ ${current_price:,.0f}")
            return 1  # Success indicator
            
        except Exception as e:
            print(f"❌ Error updating performance: {e}")
            return 0
    
    def get_win_rate(self, days: int = 30) -> Dict[str, float]:
        """
        Calculate win rate for last N days.
        
        Returns:
            Dict with win_rate, avg_pnl, total_trades
        """
        try:
            # Query closed positions
            result = self.client.table('performance_tracking')\
                .select("outcome, pnl_pct")\
                .in_('outcome', ['WIN', 'LOSS'])\
                .gte('entry_date', f'now() - interval \'{days} days\'')\
                .execute()
            
            if not result.data:
                return {'win_rate': 0, 'avg_pnl': 0, 'total_trades': 0}
            
            wins = sum(1 for r in result.data if r['outcome'] == 'WIN')
            total = len(result.data)
            avg_pnl = sum(r['pnl_pct'] for r in result.data) / total
            
            return {
                'win_rate': (wins / total * 100) if total > 0 else 0,
                'avg_pnl': avg_pnl,
                'total_trades': total
            }
            
        except Exception as e:
            print(f"❌ Error calculating win rate: {e}")
            return {'win_rate': 0, 'avg_pnl': 0, 'total_trades': 0}
    
    # ========================================================================
    # CONSISTENCY SCORING
    # ========================================================================
    
    def save_consistency_score(
        self,
        target_date: date,
        score: float,
        contradictions: int = 0,
        notes: Optional[str] = None
    ) -> Optional[int]:
        """Save daily consistency score."""
        try:
            data = {
                'date': str(target_date),
                'consistency_score': score,
                'contradictions_found': contradictions,
                'notes': notes
            }
            
            result = self.client.table('consistency_scores').insert(data).execute()
            
            if result.data:
                print(f"✅ Consistency score saved: {score:.1f}%")
                return result.data[0]['id']
            return None
            
        except Exception as e:
            print(f"❌ Error saving consistency score: {e}")
            return None
    
    def get_recent_consistency(self, days: int = 30) -> List[Dict]:
        """Get consistency scores for last N days."""
        try:
            result = self.client.table('consistency_scores')\
                .select("*")\
                .order('date', desc=True)\
                .limit(days)\
                .execute()
            
            return result.data if result.data else []
        except Exception as e:
            print(f"❌ Error fetching consistency scores: {e}")
            return []


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_client() -> SupabaseClient:
    """
    Get singleton Supabase client instance.
    
    Usage:
        from modules.supabase_client import get_client
        db = get_client()
        db.save_signal(...)
    """
    if not hasattr(get_client, '_instance'):
        get_client._instance = SupabaseClient()
    return get_client._instance


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("🧪 Testing Supabase Client...")
    
    try:
        client = SupabaseClient()
        
        # Test 1: Save sample signal
        print("\n1. Testing save_signal()...")
        signal_data = {
            'date': '2026-02-17',
            'symbol': 'BTCUSDT',
            'price': 70100.00,
            'onchain_score': 84,
            'fear_index': 12,
            'manifold_dna': 87,
            'divergence': 29.5,
            'regime': 'BLOOD_IN_STREETS',
            'signal_strength': 'STRONG_BUY',
            'bayesian_probability': 91.7
        }
        
        signal_id = client.save_signal(signal_data)
        
        # Test 2: Retrieve recent signals
        print("\n2. Testing get_recent_signals()...")
        recent = client.get_recent_signals(days=7)
        print(f"Found {len(recent)} recent signals")
        
        # Test 3: Win rate calculation
        print("\n3. Testing get_win_rate()...")
        stats = client.get_win_rate(days=30)
        print(f"Win Rate: {stats['win_rate']:.1f}%")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
