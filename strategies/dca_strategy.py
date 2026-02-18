"""
Elite v20 - DCA Strategy
Long-term accumulation strategy (2030 target)

Allocation: 60% of capital
Target: $600k-$1M BTC by 2030
Protocol: Buy & HOLD (no stop loss)
"""

from datetime import datetime
from typing import Dict, Optional
import pandas as pd


class DCAStrategy:
    """
    Dollar Cost Averaging strategy for long-term accumulation.
    
    Philosophy:
    - "Success = Responsibility + Discipline + Accountability"
    - Ignore short-term noise
    - Focus on smart money (whales)
    - HOLD through volatility
    
    Triggers:
    - Blood in Streets (Manifold Score >80)
    - Supply Shock events
    - Whale accumulation
    - Major dips (-15%+)
    
    Exit:
    - NONE until 2030 target ($600k-$1M)
    """
    
    def __init__(self):
        """Initialize DCA strategy."""
        self.name = "DCA_STRATEGIC"
        self.allocation_pct = 60.0
        self.target_year = 2030
        self.target_price_min = 600000  # $600k
        self.target_price_max = 1000000  # $1M
        
        # Entry thresholds
        self.min_manifold_score = 80.0  # Top 2% events
        self.min_diffusion_score = 90.0  # Strong whale accumulation
        self.max_fear_greed = 25  # Extreme fear
        
        # Tracking
        self.entries = []
        self.last_entry_time = None
        self.cooldown_hours = 24  # Minimum time between entries
    
    def check_entry_signal(
        self,
        manifold_score: float,
        regime: str,
        diffusion_score: float,
        fear_greed: int,
        current_price: float,
        sma200: float
    ) -> Dict:
        """
        Check if DCA entry conditions are met.
        
        Conditions:
        1. Manifold Score >80 (Top 2% event)
        2. Regime = BLOOD_IN_STREETS
        3. Diffusion Score >90 (Whales accumulating)
        4. Fear & Greed <25 (Extreme fear)
        5. Price below SMA200 (technical confirmation)
        6. Cooldown period passed
        
        Args:
            manifold_score: Manifold DNA score (0-100)
            regime: Current market regime
            diffusion_score: On-chain diffusion score (0-100)
            fear_greed: Fear & Greed Index (0-100)
            current_price: Current BTC price
            sma200: 200-period Simple Moving Average
            
        Returns:
            Dict with signal status and details
        """
        conditions = {
            'manifold_high': manifold_score >= self.min_manifold_score,
            'blood_in_streets': regime == 'BLOOD_IN_STREETS',
            'whales_accumulating': diffusion_score >= self.min_diffusion_score,
            'extreme_fear': fear_greed <= self.max_fear_greed,
            'below_sma200': current_price < sma200,
            'cooldown_passed': self._check_cooldown()
        }
        
        # Count met conditions
        met_conditions = sum(conditions.values())
        total_conditions = len(conditions)
        
        # Signal strength
        signal_strength = met_conditions / total_conditions
        
        # Strong signal if 5/6 conditions met
        strong_signal = met_conditions >= 5
        
        return {
            'signal': strong_signal,
            'signal_strength': signal_strength,
            'conditions': conditions,
            'conditions_met': met_conditions,
            'conditions_total': total_conditions,
            'manifold_score': manifold_score,
            'diffusion_score': diffusion_score,
            'fear_greed': fear_greed,
            'regime': regime,
            'current_price': current_price,
            'sma200': sma200,
            'below_sma200_pct': ((sma200 - current_price) / sma200) * 100
        }
    
    def _check_cooldown(self) -> bool:
        """
        Check if cooldown period has passed since last entry.
        
        Returns:
            True if cooldown passed or no previous entry
        """
        if self.last_entry_time is None:
            return True
        
        hours_since_last = (datetime.now() - self.last_entry_time).total_seconds() / 3600
        return hours_since_last >= self.cooldown_hours
    
    def calculate_dca_amount(
        self,
        available_capital: float,
        manifold_score: float,
        diffusion_score: float
    ) -> float:
        """
        Calculate DCA purchase amount.
        
        Strategy:
        - Base: Use 100% of available DCA capital
        - Adjustment: Increase if signals are extremely strong
        
        Args:
            available_capital: Available DCA capital
            manifold_score: Manifold score
            diffusion_score: Diffusion score
            
        Returns:
            Recommended DCA amount in USD
        """
        # Base amount (use all available capital)
        base_amount = available_capital
        
        # Strength multiplier (1.0-1.2x based on signal strength)
        # If both scores >95 (extreme signals), use 1.2x
        strength_bonus = 0.0
        if manifold_score >= 95 and diffusion_score >= 95:
            strength_bonus = 0.2
        elif manifold_score >= 90 or diffusion_score >= 95:
            strength_bonus = 0.1
        
        multiplier = 1.0 + strength_bonus
        
        # Final amount (capped at available capital for safety)
        dca_amount = min(base_amount * multiplier, available_capital)
        
        return dca_amount
    
    def record_entry(
        self,
        btc_price: float,
        usd_amount: float,
        btc_amount: float,
        manifold_score: float,
        diffusion_score: float,
        fear_greed: int,
        regime: str
    ) -> None:
        """
        Record DCA entry for tracking.
        
        Args:
            btc_price: Entry price
            usd_amount: USD spent
            btc_amount: BTC purchased
            manifold_score: Manifold score at entry
            diffusion_score: Diffusion score at entry
            fear_greed: Fear & Greed at entry
            regime: Market regime at entry
        """
        entry = {
            'timestamp': datetime.now(),
            'price': btc_price,
            'usd_amount': usd_amount,
            'btc_amount': btc_amount,
            'manifold_score': manifold_score,
            'diffusion_score': diffusion_score,
            'fear_greed': fear_greed,
            'regime': regime,
            'target_min': self.target_price_min,
            'target_max': self.target_price_max,
            'target_year': self.target_year
        }
        
        self.entries.append(entry)
        self.last_entry_time = datetime.now()
    
    def get_position_status(
        self,
        current_price: float,
        total_btc_held: float,
        avg_entry_price: float,
        capital_invested: float
    ) -> Dict:
        """
        Get DCA position status and progress to 2030 target.
        
        Args:
            current_price: Current BTC price
            total_btc_held: Total BTC accumulated
            avg_entry_price: Average entry price
            capital_invested: Total capital invested
            
        Returns:
            Position status with 2030 projection
        """
        # Current value
        current_value = total_btc_held * current_price
        unrealized_pnl = current_value - capital_invested
        unrealized_pct = (unrealized_pnl / capital_invested * 100) if capital_invested > 0 else 0
        
        # 2030 projection
        value_at_target_min = total_btc_held * self.target_price_min
        value_at_target_max = total_btc_held * self.target_price_max
        
        profit_at_target_min = value_at_target_min - capital_invested
        profit_at_target_max = value_at_target_max - capital_invested
        
        return_at_target_min = (profit_at_target_min / capital_invested * 100) if capital_invested > 0 else 0
        return_at_target_max = (profit_at_target_max / capital_invested * 100) if capital_invested > 0 else 0
        
        # Years to target
        years_to_target = self.target_year - datetime.now().year
        
        return {
            'strategy': self.name,
            'current': {
                'btc_held': total_btc_held,
                'avg_entry': avg_entry_price,
                'current_price': current_price,
                'capital_invested': capital_invested,
                'current_value': current_value,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_pct': unrealized_pct
            },
            'target_2030': {
                'target_year': self.target_year,
                'years_remaining': years_to_target,
                'target_price_min': self.target_price_min,
                'target_price_max': self.target_price_max,
                'value_at_target_min': value_at_target_min,
                'value_at_target_max': value_at_target_max,
                'profit_at_target_min': profit_at_target_min,
                'profit_at_target_max': profit_at_target_max,
                'return_at_target_min': return_at_target_min,
                'return_at_target_max': return_at_target_max
            },
            'entries_count': len(self.entries),
            'last_entry': self.last_entry_time.isoformat() if self.last_entry_time else None,
            'cooldown_hours': self.cooldown_hours,
            'can_enter_now': self._check_cooldown()
        }
    
    def get_entry_history(self) -> pd.DataFrame:
        """
        Get DCA entry history as DataFrame.
        
        Returns:
            DataFrame of all DCA entries
        """
        if not self.entries:
            return pd.DataFrame()
        
        return pd.DataFrame(self.entries)
    
    def should_hold(self, current_price: float) -> Dict:
        """
        Determine if should continue holding (always True for DCA).
        
        Args:
            current_price: Current BTC price
            
        Returns:
            Dict with hold recommendation
        """
        # DCA ALWAYS holds - no exits until 2030 target
        target_reached = current_price >= self.target_price_min
        
        return {
            'hold': True,
            'reason': 'DCA strategy - HOLD until 2030 target',
            'target_reached': target_reached,
            'target_price': self.target_price_min,
            'current_price': current_price,
            'upside_to_target': ((self.target_price_min / current_price) - 1) * 100 if current_price > 0 else 0
        }
    
    def generate_dca_plan(
        self,
        signal_data: Dict,
        available_capital: float
    ) -> Dict:
        """
        Generate complete DCA plan.
        
        Args:
            signal_data: Signal check data from check_entry_signal()
            available_capital: Available DCA capital
            
        Returns:
            Complete DCA plan
        """
        if not signal_data['signal']:
            return {
                'execute': False,
                'reason': 'DCA conditions not met',
                'signal_strength': signal_data['signal_strength'],
                'conditions': signal_data['conditions']
            }
        
        # Calculate DCA amount
        dca_amount = self.calculate_dca_amount(
            available_capital,
            signal_data['manifold_score'],
            signal_data['diffusion_score']
        )
        
        # BTC amount
        btc_amount = dca_amount / signal_data['current_price']
        
        return {
            'execute': True,
            'strategy': self.name,
            'signal_strength': signal_data['signal_strength'],
            'entry': {
                'price': signal_data['current_price'],
                'usd_amount': dca_amount,
                'btc_amount': btc_amount
            },
            'context': {
                'manifold_score': signal_data['manifold_score'],
                'diffusion_score': signal_data['diffusion_score'],
                'fear_greed': signal_data['fear_greed'],
                'regime': signal_data['regime'],
                'below_sma200_pct': signal_data['below_sma200_pct']
            },
            'target': {
                'year': self.target_year,
                'price_min': self.target_price_min,
                'price_max': self.target_price_max,
                'upside_min': ((self.target_price_min / signal_data['current_price']) - 1) * 100,
                'upside_max': ((self.target_price_max / signal_data['current_price']) - 1) * 100
            },
            'risk': {
                'stop_loss': None,  # No stop loss for DCA
                'time_horizon': f"{self.target_year - datetime.now().year} years",
                'strategy': 'HOLD through volatility'
            }
        }
