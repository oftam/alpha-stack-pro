"""
Regime Detection Engine
Identifies market regimes from multiple signals
"""

from dataclasses import dataclass
from typing import Dict, Optional
import numpy as np


@dataclass
class RegimeSignal:
    """Single regime score with confidence"""
    regime: str
    confidence: float  # 0.0-1.0
    contributing_factors: Dict[str, float]


class RegimeDetector:
    """
    Multi-dimensional regime detection
    
    Regimes identified:
    - blood_in_streets: Extreme fear + heavy outflows (BEST buy signal)
    - capitulation: Extreme fear + moderate outflows
    - short_squeeze_risk: Negative funding + price rising
    - long_squeeze_risk: Positive funding + price falling
    - distribution_top: Extreme greed + inflows to exchanges
    - normal: No extreme conditions
    """
    
    def __init__(self):
        # Regime thresholds (tunable)
        self.thresholds = {
            'fg_extreme_fear': 20,
            'fg_extreme_greed': 80,
            'funding_extreme': 0.01,  # 1% = extreme
            'netflow_strong': 2.0,    # z-score
        }
    
    def detect(self, features: Dict[str, float]) -> RegimeSignal:
        """
        Detect current market regime using EXPLICIT HIERARCHY
        
        Hierarchy (by priority):
        1. Extreme Fear (<20) → blood_in_streets or capitulation
        2. Extreme Funding (|1.5%+|) → deleveraging
        3. High Funding → squeeze_risk
        4. Extreme Greed (>80) + Netflow → distribution_top
        5. Normal
        
        Args:
            features: {
                'fg_index': 0-100,
                'funding_skew': float (typically -0.02 to +0.02),
                'netflow_z': z-score,
                'onchain_bias': -1 to +1,
                'price_change_1h': float (optional)
            }
        
        Returns:
            RegimeSignal with dominant regime and confidence
        """
        
        fg = features.get('fg_index', 50)
        funding = features.get('funding_skew', 0.0)
        netflow_z = features.get('netflow_z', 0.0)
        onchain_bias = features.get('onchain_bias', 0.0)
        price_change = features.get('price_change_1h', 0.0)
        
        # PRIORITY 1: Extreme Fear (overrides everything)
        if fg < self.thresholds['fg_extreme_fear']:
            fear_intensity = (self.thresholds['fg_extreme_fear'] - fg) / 20
            
            # Sub-classification: Blood in streets vs capitulation
            if netflow_z < -2:
                # Blood in streets = fear + accumulation
                accumulation_intensity = min(1.0, abs(netflow_z) / 3)
                confidence = min(1.0, (fear_intensity + accumulation_intensity) / 2)
                
                return RegimeSignal(
                    regime='blood_in_streets',
                    confidence=confidence,
                    contributing_factors={
                        'fear_greed': fg,
                        'funding': funding,
                        'netflow_z': netflow_z,
                        'onchain_bias': onchain_bias
                    }
                )
            else:
                # Capitulation without heavy accumulation yet
                return RegimeSignal(
                    regime='capitulation',
                    confidence=fear_intensity * 0.8,
                    contributing_factors={
                        'fear_greed': fg,
                        'funding': funding,
                        'netflow_z': netflow_z
                    }
                )
        
        # PRIORITY 2: Deleveraging Crisis (extreme funding)
        if abs(funding) > 0.015:  # 1.5%+ = systemic risk
            confidence = min(1.0, abs(funding) / 0.03)
            
            return RegimeSignal(
                regime='deleveraging',
                confidence=confidence,
                contributing_factors={
                    'funding': funding,
                    'fear_greed': fg,
                    'netflow_z': netflow_z
                }
            )
        
        # PRIORITY 3: Squeeze Risk (high funding but not crisis)
        if funding < -self.thresholds['funding_extreme']:
            # Short squeeze risk
            funding_intensity = min(1.0, abs(funding) / 0.02)
            price_boost = 1.2 if price_change > 0 else 1.0
            
            return RegimeSignal(
                regime='short_squeeze_risk',
                confidence=min(1.0, funding_intensity * price_boost),
                contributing_factors={
                    'funding': funding,
                    'price_change': price_change,
                    'fear_greed': fg
                }
            )
        
        if funding > self.thresholds['funding_extreme']:
            # Long squeeze risk
            funding_intensity = min(1.0, funding / 0.02)
            price_boost = 1.2 if price_change < 0 else 1.0
            
            return RegimeSignal(
                regime='long_squeeze_risk',
                confidence=min(1.0, funding_intensity * price_boost),
                contributing_factors={
                    'funding': funding,
                    'price_change': price_change,
                    'fear_greed': fg
                }
            )
        
        # PRIORITY 4: Distribution Top (greed + distribution)
        if fg > self.thresholds['fg_extreme_greed'] and netflow_z > 2:
            greed_intensity = (fg - self.thresholds['fg_extreme_greed']) / 20
            distribution_intensity = min(1.0, netflow_z / 3)
            
            return RegimeSignal(
                regime='distribution_top',
                confidence=min(1.0, (greed_intensity + distribution_intensity) / 2),
                contributing_factors={
                    'fear_greed': fg,
                    'netflow_z': netflow_z,
                    'onchain_bias': onchain_bias
                }
            )
        
        # PRIORITY 5: Normal (default)
        return RegimeSignal(
            regime='normal',
            confidence=1.0,
            contributing_factors={
                'fear_greed': fg,
                'funding': funding,
                'netflow_z': netflow_z
            }
        )
    
    def get_regime_weights(self, regime: str) -> Dict[str, float]:
        """
        Return optimal signal weights for each regime
        
        This is where regime detection adds value:
        Different market conditions → different signal importance
        """
        
        weights = {
            'blood_in_streets': {
                'onchain': 0.7,   # On-chain is king during capitulation
                'funding': 0.1,
                'fg': 0.1,
                'netflow': 0.1,
                'nlp': 0.0,       # Ignore noise during blood in streets
            },
            'capitulation': {
                'onchain': 0.6,
                'funding': 0.15,
                'fg': 0.15,
                'netflow': 0.1,
                'nlp': 0.0,
            },
            'short_squeeze_risk': {
                'funding': 0.6,   # Funding is key signal
                'onchain': 0.2,
                'fg': 0.1,
                'netflow': 0.05,
                'nlp': 0.05,
            },
            'long_squeeze_risk': {
                'funding': 0.6,
                'onchain': 0.2,
                'fg': 0.1,
                'netflow': 0.05,
                'nlp': 0.05,
            },
            'distribution_top': {
                'netflow': 0.4,   # Exchange flows matter most
                'onchain': 0.3,
                'fg': 0.2,
                'funding': 0.05,
                'nlp': 0.05,
            },
            'deleveraging': {
                'funding': 0.5,
                'onchain': 0.25,
                'netflow': 0.15,
                'fg': 0.05,
                'nlp': 0.05,
            },
            'normal': {
                'onchain': 0.35,
                'funding': 0.25,
                'fg': 0.2,
                'netflow': 0.15,
                'nlp': 0.05,
            }
        }
        
        return weights.get(regime, weights['normal'])


# Example usage
if __name__ == "__main__":
    detector = RegimeDetector()
    
    # Test scenario: Extreme fear + accumulation
    features = {
        'fg_index': 12,           # Extreme fear
        'funding_skew': -0.005,   # Slight negative
        'netflow_z': -2.8,        # Strong outflows from exchanges
        'onchain_bias': 0.6,      # Whales accumulating
        'price_change_1h': -0.02  # Price down 2%
    }
    
    regime = detector.detect(features)
    print(f"Regime: {regime.regime}")
    print(f"Confidence: {regime.confidence:.2%}")
    print(f"Optimal weights: {detector.get_regime_weights(regime.regime)}")
