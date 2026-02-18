#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎨 DUDU PROGRESSION - FULL PSYCHOLOGICAL CYCLE
14 Phases from Angola (Capitulation) to Euphoria (Top)

Market Psychology Cycle:
1. Angola (Despair/Capitulation) - Bottom
2. Purgatory (Recovery begins)
3. Disbelief (Doubt phase)
4. Hope (Early rally)
5. Optimism (Momentum builds)
6. Belief (Conviction)
7. Thrill (Acceleration)
8. Euphoria (Top/Peak)
9. Complacency (Denial)
10. Anxiety (First doubt)
11. Denial (Hope fades)
12. Panic (Fear takes over)
13. Capitulation (Forced selling)
14. Despair (Final low)

Then cycle repeats: Despair → Angola → Purgatory → ...
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class PsychologicalPhase:
    """Represents a phase in the market psychology cycle"""
    name: str
    hebrew_name: str
    description: str
    target_pct: float  # % change from current price
    color: str
    emoji: str
    sentiment_score: float  # -100 to +100
    volatility_multiplier: float  # How much vol expected


# Define all 14 phases
PSYCHOLOGICAL_PHASES = [
    # Bottom - Extreme Fear
    PsychologicalPhase(
        name="Angola",
        hebrew_name="אנגולה",
        description="Capitulation low - Maximum despair",
        target_pct=-40.0,
        color="#8B0000",  # Dark red
        emoji="💀",
        sentiment_score=-100,
        volatility_multiplier=2.0
    ),
    PsychologicalPhase(
        name="Purgatory",
        hebrew_name="טַהֲרָה",
        description="Recovery begins - Cleansing phase",
        target_pct=-25.0,
        color="#DC143C",  # Crimson
        emoji="🔥",
        sentiment_score=-75,
        volatility_multiplier=1.8
    ),
    PsychologicalPhase(
        name="Disbelief",
        hebrew_name="חוסר אמון",
        description="Rally starts but nobody believes",
        target_pct=-10.0,
        color="#FF4500",  # Orange red
        emoji="🤔",
        sentiment_score=-50,
        volatility_multiplier=1.5
    ),
    PsychologicalPhase(
        name="Hope",
        hebrew_name="תקווה",
        description="Early rally - Maybe it's real",
        target_pct=5.0,
        color="#FFA500",  # Orange
        emoji="🌱",
        sentiment_score=-20,
        volatility_multiplier=1.3
    ),
    PsychologicalPhase(
        name="Optimism",
        hebrew_name="אופטימיות",
        description="Momentum builds - Things look good",
        target_pct=20.0,
        color="#FFD700",  # Gold
        emoji="😊",
        sentiment_score=20,
        volatility_multiplier=1.2
    ),
    PsychologicalPhase(
        name="Belief",
        hebrew_name="אמונה",
        description="Conviction - This is the trend",
        target_pct=40.0,
        color="#ADFF2F",  # Green yellow
        emoji="💪",
        sentiment_score=40,
        volatility_multiplier=1.1
    ),
    PsychologicalPhase(
        name="Thrill",
        hebrew_name="התרגשות",
        description="Acceleration - Profits mounting",
        target_pct=65.0,
        color="#00FF00",  # Lime
        emoji="🚀",
        sentiment_score=70,
        volatility_multiplier=1.3
    ),
    # Top - Extreme Greed
    PsychologicalPhase(
        name="Euphoria",
        hebrew_name="אופוריה",
        description="Peak - Maximum greed, everyone buying",
        target_pct=100.0,
        color="#00FFFF",  # Cyan
        emoji="🎉",
        sentiment_score=100,
        volatility_multiplier=1.5
    ),
    # Decline begins
    PsychologicalPhase(
        name="Complacency",
        hebrew_name="שאננות",
        description="Denial - Just a pullback",
        target_pct=80.0,
        color="#1E90FF",  # Dodger blue
        emoji="😌",
        sentiment_score=60,
        volatility_multiplier=1.4
    ),
    PsychologicalPhase(
        name="Anxiety",
        hebrew_name="חרדה",
        description="First doubt - Something feels off",
        target_pct=50.0,
        color="#4169E1",  # Royal blue
        emoji="😰",
        sentiment_score=20,
        volatility_multiplier=1.6
    ),
    PsychologicalPhase(
        name="Denial",
        hebrew_name="הכחשה",
        description="Hope fades - Maybe I should sell",
        target_pct=20.0,
        color="#0000CD",  # Medium blue
        emoji="🙈",
        sentiment_score=-20,
        volatility_multiplier=1.7
    ),
    PsychologicalPhase(
        name="Panic",
        hebrew_name="פאניקה",
        description="Fear takes over - Get me out!",
        target_pct=-10.0,
        color="#8B008B",  # Dark magenta
        emoji="😱",
        sentiment_score=-60,
        volatility_multiplier=2.0
    ),
    PsychologicalPhase(
        name="Capitulation",
        hebrew_name="כניעה",
        description="Forced selling - I give up",
        target_pct=-30.0,
        color="#800080",  # Purple
        emoji="🏳️",
        sentiment_score=-85,
        volatility_multiplier=2.2
    ),
    PsychologicalPhase(
        name="Despair",
        hebrew_name="ייאוש",
        description="Final low - All hope lost",
        target_pct=-40.0,
        color="#4B0082",  # Indigo
        emoji="😭",
        sentiment_score=-100,
        volatility_multiplier=2.0
    ),
]


class DuduProgression:
    """
    Full Dudu Progression with psychological cycle mapping
    
    Features:
    - 14 psychological phases
    - Vol cone projections
    - Current phase detection
    - Target price annotations
    - Visual progression chart
    """
    
    def __init__(self):
        self.phases = PSYCHOLOGICAL_PHASES
        
    def detect_current_phase(self,
                            price_change_pct: float,
                            fear_greed: int,
                            volatility_percentile: float) -> PsychologicalPhase:
        """
        Detect which psychological phase we're currently in
        
        Args:
            price_change_pct: % change from recent low/high
            fear_greed: Fear & Greed index (0-100)
            volatility_percentile: Current vol percentile (0-100)
            
        Returns:
            Current psychological phase
        """
        
        # Score each phase based on inputs
        phase_scores = []
        
        for phase in self.phases:
            score = 0
            
            # Match price movement to phase target
            price_diff = abs(price_change_pct - phase.target_pct)
            price_score = max(0, 100 - price_diff)
            score += price_score * 0.4
            
            # Match sentiment
            sentiment_diff = abs(fear_greed - 50 - phase.sentiment_score / 2)
            sentiment_score = max(0, 100 - sentiment_diff * 2)
            score += sentiment_score * 0.4
            
            # Match volatility
            vol_diff = abs(volatility_percentile - (phase.volatility_multiplier - 1) * 50)
            vol_score = max(0, 100 - vol_diff)
            score += vol_score * 0.2
            
            phase_scores.append((phase, score))
        
        # Return best match
        best_phase = max(phase_scores, key=lambda x: x[1])
        return best_phase[0]
    
    def calculate_targets(self,
                         current_price: float,
                         base_phase: Optional[PsychologicalPhase] = None) -> Dict[str, float]:
        """
        Calculate target prices for all phases
        
        Args:
            current_price: Current BTC price
            base_phase: If provided, calculate from this phase, else use Angola as base
            
        Returns:
            Dict of {phase_name: target_price}
        """
        
        if base_phase is None:
            # Use Angola (capitulation) as base
            base_phase = self.phases[0]
        
        # Calculate Angola price first (our zero point)
        if base_phase.target_pct == -40.0:
            # We're at Angola
            angola_price = current_price
        else:
            # Calculate what Angola would be from current position
            # If we're at +20% (Hope), Angola is current / (1 + 0.20) * (1 - 0.40)
            angola_price = current_price / (1 + base_phase.target_pct / 100) * (1 - 0.40)
        
        targets = {}
        
        for phase in self.phases:
            # Calculate from Angola base
            if phase.target_pct >= 0:
                # Upside phases
                target = angola_price * (1 + (0.40 + phase.target_pct / 100))
            else:
                # Downside phases (Angola is -40%)
                target = angola_price * (1 + (0.40 + phase.target_pct / 100))
            
            targets[phase.name] = target
        
        return targets
    
    def build_vol_cone(self,
                      close: pd.Series,
                      current_phase: PsychologicalPhase,
                      horizon: int = 48) -> Dict:
        """
        Build volatility cone adjusted for psychological phase
        
        Args:
            close: Price series
            current_phase: Current psychological phase
            horizon: Periods to project
            
        Returns:
            Dict with bands adjusted for phase
        """
        
        # Calculate base volatility
        returns = close.pct_change().dropna()
        base_vol = returns.std()
        
        # Adjust for phase volatility multiplier
        phase_vol = base_vol * current_phase.volatility_multiplier
        
        current_price = close.iloc[-1]
        t = np.arange(0, horizon + 1)
        
        # Build cone
        bands = {}
        for sigma in [1, 2, 3]:
            spread = phase_vol * sigma * np.sqrt(t)
            upper = current_price * (1 + spread)
            lower = current_price * (1 - spread)
            bands[sigma] = (lower, upper)
        
        return {
            'current_price': current_price,
            'base_vol': base_vol,
            'phase_vol': phase_vol,
            'horizon': horizon,
            'bands': bands
        }
    
    def generate_progression_chart_data(self,
                                        current_price: float,
                                        current_phase: PsychologicalPhase,
                                        horizon_days: int = 365) -> pd.DataFrame:
        """
        Generate data for progression chart
        
        Returns DataFrame with columns:
        - date
        - phase
        - target_price
        - sentiment
        - color
        """
        
        targets = self.calculate_targets(current_price, current_phase)
        
        # Find current phase index
        current_idx = next(i for i, p in enumerate(self.phases) if p.name == current_phase.name)
        
        # Create progression assuming we move through phases over time
        # Simple model: each phase lasts ~30 days on average
        days_per_phase = horizon_days / len(self.phases)
        
        data = []
        base_date = datetime.now()
        
        for i, phase in enumerate(self.phases):
            # Start date for this phase
            phase_start = base_date + timedelta(days=i * days_per_phase)
            
            # Add entry for this phase
            data.append({
                'date': phase_start,
                'phase': phase.name,
                'hebrew_name': phase.hebrew_name,
                'target_price': targets[phase.name],
                'sentiment': phase.sentiment_score,
                'color': phase.color,
                'emoji': phase.emoji,
                'is_current': (i == current_idx)
            })
        
        return pd.DataFrame(data)
    
    def get_phase_summary(self, phase: PsychologicalPhase) -> str:
        """Generate human-readable summary of a phase"""
        
        return f"""
{phase.emoji} **{phase.name}** ({phase.hebrew_name})

**Description:** {phase.description}

**Characteristics:**
- Target: {phase.target_pct:+.0f}% from Angola
- Sentiment: {phase.sentiment_score:+.0f}/100
- Volatility: {phase.volatility_multiplier:.1f}x normal

**Investor Behavior:**
{self._get_behavior_description(phase)}
"""
    
    def _get_behavior_description(self, phase: PsychologicalPhase) -> str:
        """Get typical investor behavior for each phase"""
        
        behaviors = {
            "Angola": "Everyone has capitulated. Nobody wants crypto. Maximum despair. Smart money accumulating.",
            "Purgatory": "Some brave souls start buying. Most still skeptical. 'Dead cat bounce' narrative.",
            "Disbelief": "Rally continues but dismissed as temporary. 'It's going back down.'",
            "Hope": "Maybe this is real? Early adopters getting confident. Shorts starting to hurt.",
            "Optimism": "Trend is clear. FOMO begins. 'I should have bought more at the bottom.'",
            "Belief": "Strong conviction. HODLers vindicated. New money flowing in.",
            "Thrill": "Parabolic moves. Everyone profitable. Leverage increasing.",
            "Euphoria": "Taxi drivers giving crypto tips. Everyone's a genius. Peak greed.",
            "Complacency": "Small dip but 'we'll recover'. 'Buy the dip' still working.",
            "Anxiety": "Larger correction. 'Is this the top?' Doubt creeping in.",
            "Denial": "'This is just a healthy correction.' HODLers refusing to sell.",
            "Panic": "Cascading selloff. Margin calls. 'Get me out at any price!'",
            "Capitulation": "Forced selling. Giving up. 'I'll never touch crypto again.'",
            "Despair": "Total hopelessness. Market 'dead'. Perfect accumulation zone for next cycle."
        }
        
        return behaviors.get(phase.name, "Unknown phase")


def create_dudu_visualization(dudu: DuduProgression,
                              current_price: float,
                              current_phase: PsychologicalPhase,
                              df: pd.DataFrame) -> Dict:
    """
    Create complete visualization data for Dudu Progression
    
    Returns:
        Dict with all visualization components
    """
    
    # Calculate targets
    targets = dudu.calculate_targets(current_price, current_phase)
    
    # Build vol cone
    vol_cone = dudu.build_vol_cone(df['close'], current_phase, horizon=48)
    
    # Generate progression chart
    progression = dudu.generate_progression_chart_data(
        current_price, 
        current_phase,
        horizon_days=365
    )
    
    # Find key levels
    angola_price = targets['Angola']
    euphoria_price = targets['Euphoria']
    
    return {
        'current_phase': current_phase,
        'current_price': current_price,
        'targets': targets,
        'vol_cone': vol_cone,
        'progression': progression,
        'key_levels': {
            'angola': angola_price,
            'euphoria': euphoria_price,
            'range_pct': (euphoria_price / angola_price - 1) * 100
        }
    }


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == '__main__':
    # Example usage
    dudu = DuduProgression()
    
    # Detect current phase
    current_phase = dudu.detect_current_phase(
        price_change_pct=15.0,  # Up 15% from low
        fear_greed=45,          # Fear & Greed index
        volatility_percentile=60 # Elevated vol
    )
    
    print(f"Current Phase: [PHASE] {current_phase.name}")
    print(dudu.get_phase_summary(current_phase))
    
    # Calculate targets
    targets = dudu.calculate_targets(current_price=98000, base_phase=current_phase)
    
    print("\n" + "=" * 70)
    print("TARGET PRICES:")
    print("=" * 70)
    
    for phase in dudu.phases:
        target = targets[phase.name]
        change_pct = (target / 98000 - 1) * 100
        
        current_marker = " ← YOU ARE HERE" if phase.name == current_phase.name else ""
        
        print(f"[PHASE] {phase.name:15s}: ${target:>10,.0f} ({change_pct:+6.1f}%){current_marker}")
