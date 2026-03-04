"""
🧬 MONOLITH ENGINE - Epigenetic Interference Mapping
===================================================
Transitioning ELITE v20 from modular "voting" to a single Monolithic Model.
Calculates how modules interact, amplify, or silence each other.

Inspired by Renaissance Technologies (Medallion Fund) architecture.
"""

from typing import Dict, List, Any
import numpy as np

class MonolithEngine:
    """
    Manages the Interference Matrix (Epigenetic Cross-Talk)
    
    Principles:
    1. Constructive Interference: Signals that amplify each other (e.g., Fear + Whale Accumulation).
    2. Destructive Interference: Signals that contradict (e.g., High Price Action + Low CVD).
    3. Gene Silencing: High Chaos/Volatility silences lagging indicators (Technicals).
    """
    
    def __init__(self):
        self.modules = ['onchain', 'microstructure', 'chaos', 'sentiment', 'technical']
        
    def calculate_interference_matrix(self, results: Dict[str, Any]) -> np.ndarray:
        """
        Calculates the interaction weights between modules.
        Returns a 5x5 matrix where [i,j] is the influence of module i on module j.
        """
        size = len(self.modules)
        matrix = np.zeros((size, size))
        
        # 1. Base identity (self-influence)
        for i in range(size):
            matrix[i, i] = 1.0
            
        # Extract base metrics for interference logic
        chaos_score = results.get('chaos', {}).get('violence_score', 0.5)
        onchain_score = results.get('onchain', {}).get('diffusion_score', 50) / 100.0
        fear_greed = results.get('sentiment', {}).get('fear_greed', 50) / 100.0
        
        # 2. Gene Silencing (Chaos suppresses others)
        if chaos_score > 0.7:
            # High chaos silences technicals and standard sentiment
            matrix[2, 4] = -0.8  # Chaos silences Technical
            matrix[2, 3] = -0.5  # Chaos silences Sentiment
        
        # 3. Constructive Interference (Victory Vector patterns)
        if fear_greed < 0.2 and onchain_score > 0.8:
            # Extreme fear + heavy accumulation = Maximum amplification
            matrix[3, 0] = 2.0  # Fear amplifies On-chain significance
            
        # 5. Scientific Coupling (Phase 6)
        hmm_regime = results.get('hmm_regime', '')
        if 'ACCUMULATION' in hmm_regime:
            matrix[0, 1] = 1.5 # Accumulation amplifies microstructure bullishness
            
        topology = results.get('topology', {})
        if topology.get('manifold_stability') == 'LOCKED':
            # Stable manifold reinforces technical signals
            matrix[4, 4] = 1.8 
        elif topology.get('manifold_stability') == 'DISTORTED':
            # Distorted manifold silences technicals
            matrix[4, 4] = 0.2
            
        # 4. Destructive Interference (Divergence patterns)
        # Price rising but CVD dropping
        micro = results.get('microstructure', {})
        cvd_imbalance = micro.get('trade_flow', {}).get('imbalance', 0)
        price_change = results.get('price_change_1h', 0)
        
        if price_change > 0 and cvd_imbalance < -0.1:
            matrix[1, 4] = -0.7  # Negative CVD contradicts positive Technicals
            
        return matrix

    def apply_monolithic_score(self, results: Dict[str, Any]) -> float:
        """
        Calculates the final consolidated score using the Interference Matrix.
        Replaces simple weighted average.
        """
        # Raw module scores (normalized 0-1)
        raw_scores = np.array([
            results.get('onchain', {}).get('diffusion_score', 50) / 100.0,
            (results.get('microstructure', {}).get('book_imbalance', 0) + 1) / 2.0, # -1,1 -> 0,1
            (1.0 - results.get('chaos', {}).get('violence_score', 0.5)), # Lower chaos is better score
            (100 - results.get('sentiment', {}).get('fear_greed', 50)) / 100.0, # Lower fear is better for buy
            results.get('technical', {}).get('p10_score', 50) / 100.0
        ])
        
        # Calculate matrix
        matrix = self.calculate_interference_matrix(results)
        
        # Linear combination: interference @ raw_scores
        # This is the "Epigenetic Shift" - modules influence each other's weights
        monolithic_vector = np.dot(matrix, raw_scores)
        
        # Normalized final output
        final_score = np.mean(monolithic_vector) * 100.0
        return float(np.clip(final_score, 0, 100))

    def get_interference_labels(self) -> List[str]:
        return [m.upper() for m in self.modules]
