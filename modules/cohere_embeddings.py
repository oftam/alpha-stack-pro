"""
Elite v20 - Cohere Embeddings Module
=====================================
Vector embeddings for regime-aware similarity search.

Uses Cohere's embed-english-v3.0 model (1024 dimensions, free tier).
"""

import os
from typing import List, Dict, Optional, Any
import json

try:
    import cohere
    COHERE_AVAILABLE = True
except ImportError:
    COHERE_AVAILABLE = False
    print("⚠️ cohere not installed. Run: pip install cohere")


class CohereEmbeddings:
    """
    Generate vector embeddings for market conditions and Claude responses.
    
    Usage:
        embedder = CohereEmbeddings()
        vector = embedder.embed_signal(manifold=87, onchain=84, fear=12, regime='BLOOD_IN_STREETS')
        similar = embedder.find_similar(vector, regime_filter='BLOOD_IN_STREETS')
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Cohere client.
        
        Args:
            api_key: Cohere API key (or from .env)
        """
        if not COHERE_AVAILABLE:
            raise ImportError("cohere required. Install: pip install cohere")
        
        self.api_key = api_key or os.getenv('COHERE_API_KEY')
        
        if not self.api_key:
            raise ValueError("COHERE_API_KEY missing! Set in .env or pass to constructor")
        
        self.client = cohere.Client(self.api_key)
        self.model = "embed-english-v3.0"  # 1024 dimensions, multilingual
        
        print(f"✅ Cohere Embeddings initialized | Model: {self.model}")
    
    def embed_signal(
        self,
        manifold: int,
        onchain: int,
        fear: int,
        regime: str,
        price: Optional[float] = None,
        divergence: Optional[float] = None
    ) -> List[float]:
        """
        Create embedding vector for market signal.
        
        Args:
            manifold: Manifold DNA score (0-100)
            onchain: OnChain diffusion score (0-100)
            fear: Fear & Greed index (0-100)
            regime: Market regime (BLOOD_IN_STREETS, NORMAL, etc.)
            price: Current BTC price (optional)
            divergence: Price vs OnChain divergence (optional)
        
        Returns:
            1024-dim embedding vector
        """
        # Create descriptive text representation
        text = self._signal_to_text(manifold, onchain, fear, regime, price, divergence)
        
        # Generate embedding
        try:
            response = self.client.embed(
                texts=[text],
                model=self.model,
                input_type="search_document"  # For indexing
            )
            
            return response.embeddings[0]
            
        except Exception as e:
            print(f"❌ Embedding failed: {e}")
            # Return zero vector as fallback
            return [0.0] * 1024
    
    def embed_response(self, claude_response: str, regime: str) -> List[float]:
        """
        Create embedding for Claude's response (for similarity search).
        
        Args:
            claude_response: Full Claude text response
            regime: Regime at time of response
        
        Returns:
            1024-dim embedding vector
        """
        # Prepend regime for context-aware embedding
        text = f"[REGIME: {regime}] {claude_response[:500]}"  # First 500 chars
        
        try:
            response = self.client.embed(
                texts=[text],
                model=self.model,
                input_type="search_document"
            )
            
            return response.embeddings[0]
            
        except Exception as e:
            print(f"❌ Embedding failed: {e}")
            return [0.0] * 1024
    
    def embed_query(self, question: str, regime: Optional[str] = None) -> List[float]:
        """
        Create embedding for user query (for finding similar past scenarios).
        
        Args:
            question: User's question
            regime: Optional regime filter
        
        Returns:
            1024-dim embedding vector
        """
        text = question
        if regime:
            text = f"[REGIME: {regime}] {question}"
        
        try:
            response = self.client.embed(
                texts=[text],
                model=self.model,
                input_type="search_query"  # For search queries
            )
            
            return response.embeddings[0]
            
        except Exception as e:
            print(f"❌ Embedding failed: {e}")
            return [0.0] * 1024
    
    def _signal_to_text(
        self,
        manifold: int,
        onchain: int,
        fear: int,
        regime: str,
        price: Optional[float],
        divergence: Optional[float]
    ) -> str:
        """
        Convert signal metrics to descriptive text for embedding.
        
        This creates a semantic representation that captures market conditions.
        """
        parts = [
            f"Market regime: {regime}",
            f"Manifold DNA: {manifold}/100",
            f"OnChain diffusion: {onchain}/100",
            f"Fear index: {fear}/100"
        ]
        
        if price:
            parts.append(f"Bitcoin price: ${price:,.0f}")
        
        if divergence:
            parts.append(f"Divergence: {divergence:+.1f}")
        
        # Add semantic interpretation
        if manifold >= 82:
            parts.append("Signal strength: SNIPER MODE (Victory Vector)")
        elif manifold >= 80:
            parts.append("Signal strength: STRONG BUY")
        elif manifold >= 65:
            parts.append("Signal strength: BUILD/ACCUMULATION")
        else:
            parts.append("Signal strength: HOLD/WAIT")
        
        if regime == "BLOOD_IN_STREETS":
            parts.append("Market condition: Extreme fear, potential bottom")
        elif regime == "BULL_RUN":
            parts.append("Market condition: Strong uptrend, high momentum")
        
        return ". ".join(parts) + "."
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Returns:
            Similarity score (0-1, higher = more similar)
        """
        import numpy as np
        
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def get_embedder() -> CohereEmbeddings:
    """
    Get singleton CohereEmbeddings instance.
    
    Usage:
        from modules.cohere_embeddings import get_embedder
        embedder = get_embedder()
        vector = embedder.embed_signal(...)
    """
    if not hasattr(get_embedder, '_instance'):
        get_embedder._instance = CohereEmbeddings()
    return get_embedder._instance


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("🧪 Testing Cohere Embeddings...")
    
    try:
        embedder = CohereEmbeddings()
        
        # Test 1: Embed market signal
        print("\n1. Testing embed_signal()...")
        vector1 = embedder.embed_signal(
            manifold=87,
            onchain=84,
            fear=12,
            regime='BLOOD_IN_STREETS',
            price=68500,
            divergence=29.5
        )
        print(f"Generated vector: {len(vector1)} dimensions")
        print(f"First 5 values: {vector1[:5]}")
        
        # Test 2: Embed similar signal
        print("\n2. Testing similarity...")
        vector2 = embedder.embed_signal(
            manifold=89,
            onchain=86,
            fear=10,
            regime='BLOOD_IN_STREETS',
            price=69000,
            divergence=31.0
        )
        
        similarity = embedder.cosine_similarity(vector1, vector2)
        print(f"Similarity between similar signals: {similarity:.3f}")
        
        # Test 3: Embed different regime
        vector3 = embedder.embed_signal(
            manifold=55,
            onchain=45,
            fear=65,
            regime='NORMAL',
            price=75000
        )
        
        similarity_diff = embedder.cosine_similarity(vector1, vector3)
        print(f"Similarity between different regimes: {similarity_diff:.3f}")
        
        print("\n✅ All tests passed!")
        print(f"✅ Similar signals: {similarity:.1%} similar")
        print(f"✅ Different regimes: {similarity_diff:.1%} similar")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("\n💡 Make sure COHERE_API_KEY is set in .env")
