"""
Elite v20 - Risk Management Engine
Kelly Criterion + Dynamic Stop Loss + Position Sizing
Based on: QC-AI_2030_Architecture.pdf

Iron Rules (Top 0.001% Psychology):
1. Never Risk >5% per trade
2. Kelly capped at 1.5x (conservative)
3. Stop loss based on 2σ volatility
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional


class RiskManagementEngine:
    """
    Professional risk management system.
    
    Key Features:
    - Kelly Criterion for optimal position sizing
    - Dynamic stop loss (2σ volatility-based)
    - Maximum 5% risk per trade (IRON RULE)
    - T1/T2 target calculation
    - Confidence-adjusted sizing
    """
    
    def __init__(self, max_risk_pct: float = 5.0):
        """
        Initialize risk engine.
        
        Args:
            max_risk_pct: Maximum risk per trade (default 5%)
        """
        self.max_risk_pct = max_risk_pct
        self.kelly_cap = 1.5  # Conservative Kelly cap
        
        # Historical performance (from backtests)
        self.win_rate = 0.857  # 85.7% win rate
        self.avg_win_loss_ratio = 5.7  # R:R ratio
        
    def calculate_kelly_fraction(
        self,
        win_rate: Optional[float] = None,
        win_loss_ratio: Optional[float] = None
    ) -> float:
        """
        Calculate Kelly Criterion optimal position size.
        
        Formula: f* = (p*b - q) / b
        Where:
        - p = win probability
        - q = loss probability (1-p)
        - b = win/loss ratio
        
        Args:
            win_rate: Win probability (uses default if None)
            win_loss_ratio: Average win/loss ratio (uses default if None)
            
        Returns:
            Kelly fraction (capped at 1.5x for safety)
        """
        p = win_rate if win_rate is not None else self.win_rate
        q = 1 - p
        b = win_loss_ratio if win_loss_ratio is not None else self.avg_win_loss_ratio
        
        # Kelly formula
        kelly = (p * b - q) / b
        
        # Cap at 1.5x for conservative trading
        kelly_capped = min(kelly, self.kelly_cap)
        
        return max(0, kelly_capped)  # Never negative
    
    def calculate_dynamic_stop_loss(
        self,
        df: pd.DataFrame,
        current_price: float,
        lookback: int = 20,
        num_std: float = 2.0
    ) -> Tuple[float, float]:
        """
        Calculate dynamic stop loss based on volatility.
        
        Uses 2σ (2 standard deviations) of recent price action.
        
        Args:
            df: Price DataFrame with 'close' column
            current_price: Current market price
            lookback: Number of periods for volatility calculation
            num_std: Number of standard deviations (default 2.0)
            
        Returns:
            Tuple of (stop_loss_price, stop_loss_pct)
        """
        if len(df) < lookback:
            lookback = len(df)
        
        # Calculate returns
        returns = df['close'].pct_change().tail(lookback)
        
        # Calculate volatility (standard deviation)
        volatility = returns.std()
        
        # Stop loss distance (2σ below current price)
        stop_distance_pct = volatility * num_std
        stop_loss_price = current_price * (1 - stop_distance_pct)
        stop_loss_pct = stop_distance_pct * 100
        
        return stop_loss_price, stop_loss_pct
    
    def calculate_position_size(
        self,
        capital_available: float,
        current_price: float,
        stop_loss_price: float,
        confidence: float,
        kelly_fraction: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate optimal position size.
        
        Formula:
        Position = Base × min(1.5, Kelly×0.25) × Confidence
        
        IRON RULE: Maximum 5% of capital at risk
        
        Args:
            capital_available: Available trading capital
            current_price: Current BTC price
            stop_loss_price: Stop loss price
            confidence: System confidence (0.0-1.0)
            kelly_fraction: Kelly fraction (calculated if None)
            
        Returns:
            Dict with position sizing details
        """
        if kelly_fraction is None:
            kelly_fraction = self.calculate_kelly_fraction()
        
        # Base position (100% of available capital)
        base_position_usd = capital_available
        
        # Kelly adjustment (conservative: Kelly × 0.25)
        kelly_multiplier = min(self.kelly_cap, kelly_fraction * 0.25)
        
        # Confidence adjustment
        confidence_multiplier = confidence
        
        # Combined multiplier
        total_multiplier = kelly_multiplier * confidence_multiplier
        
        # Position size in USD
        position_size_usd = base_position_usd * total_multiplier
        
        # Calculate risk per unit
        risk_per_btc = current_price - stop_loss_price
        risk_pct = (risk_per_btc / current_price) * 100
        
        # Apply IRON RULE: Max 5% capital at risk
        max_risk_usd = capital_available * (self.max_risk_pct / 100)
        max_btc_from_risk = max_risk_usd / risk_per_btc if risk_per_btc > 0 else 0
        max_position_from_risk = max_btc_from_risk * current_price
        
        # Final position (limited by risk)
        final_position_usd = min(position_size_usd, max_position_from_risk)
        final_btc = final_position_usd / current_price
        
        # Actual risk
        actual_risk_usd = final_btc * risk_per_btc
        actual_risk_pct = (actual_risk_usd / capital_available) * 100
        
        return {
            'position_size_usd': final_position_usd,
            'position_size_btc': final_btc,
            'kelly_fraction': kelly_fraction,
            'kelly_multiplier': kelly_multiplier,
            'confidence_multiplier': confidence_multiplier,
            'total_multiplier': total_multiplier,
            'stop_loss_price': stop_loss_price,
            'risk_per_btc': risk_per_btc,
            'risk_pct': risk_pct,
            'actual_risk_usd': actual_risk_usd,
            'actual_risk_pct': actual_risk_pct,
            'max_risk_usd': max_risk_usd,
            'max_risk_pct': self.max_risk_pct,
            'risk_within_limits': actual_risk_pct <= self.max_risk_pct
        }
    
    def calculate_targets(
        self,
        entry_price: float,
        t1_pct: float = 5.0,
        t2_pct: float = 12.0,
        trail_stop_pct: float = 3.0
    ) -> Dict[str, float]:
        """
        Calculate T1 (validation) and T2 (harvest) targets.
        
        Protocol:
        - T1: +5% → Exit 50%, move stop to breakeven
        - T2: +12% → Trail stop 3%
        
        Args:
            entry_price: Entry price
            t1_pct: T1 target percentage (default 5%)
            t2_pct: T2 target percentage (default 12%)
            trail_stop_pct: Trailing stop percentage (default 3%)
            
        Returns:
            Dict with T1/T2 targets and trailing stop
        """
        t1_price = entry_price * (1 + t1_pct / 100)
        t2_price = entry_price * (1 + t2_pct / 100)
        
        # Trailing stop (starts at T2)
        trail_stop_from_t2 = t2_price * (1 - trail_stop_pct / 100)
        
        return {
            't1_target': t1_price,
            't1_pct': t1_pct,
            't1_gain_usd_per_btc': t1_price - entry_price,
            't2_target': t2_price,
            't2_pct': t2_pct,
            't2_gain_usd_per_btc': t2_price - entry_price,
            'trail_stop_pct': trail_stop_pct,
            'trail_stop_from_t2': trail_stop_from_t2,
            'entry_price': entry_price
        }
    
    def calculate_risk_reward_ratio(
        self,
        entry_price: float,
        stop_loss_price: float,
        target_price: float
    ) -> float:
        """
        Calculate risk/reward ratio.
        
        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            target_price: Target price (T1 or T2)
            
        Returns:
            Risk/Reward ratio (e.g., 5.7 means 5.7:1)
        """
        risk = entry_price - stop_loss_price
        reward = target_price - entry_price
        
        if risk <= 0:
            return 0.0
        
        return reward / risk
    
    def validate_trade_setup(
        self,
        entry_price: float,
        stop_loss_price: float,
        t1_price: float,
        t2_price: float,
        position_size_usd: float,
        capital_available: float
    ) -> Dict[str, any]:
        """
        Validate complete trade setup against risk rules.
        
        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            t1_price: T1 target price
            t2_price: T2 target price
            position_size_usd: Position size in USD
            capital_available: Available capital
            
        Returns:
            Dict with validation results and warnings
        """
        # Calculate R:R ratios
        rr_t1 = self.calculate_risk_reward_ratio(entry_price, stop_loss_price, t1_price)
        rr_t2 = self.calculate_risk_reward_ratio(entry_price, stop_loss_price, t2_price)
        
        # Calculate risk
        btc_amount = position_size_usd / entry_price
        risk_per_btc = entry_price - stop_loss_price
        total_risk = btc_amount * risk_per_btc
        risk_pct = (total_risk / capital_available) * 100
        
        # Validation checks
        checks = {
            'risk_within_limit': risk_pct <= self.max_risk_pct,
            'rr_t1_acceptable': rr_t1 >= 2.0,  # Minimum 2:1 for T1
            'rr_t2_acceptable': rr_t2 >= 4.0,  # Minimum 4:1 for T2
            'stop_below_entry': stop_loss_price < entry_price,
            'targets_above_entry': t1_price > entry_price and t2_price > entry_price,
            't2_above_t1': t2_price > t1_price
        }
        
        # Overall validation
        all_checks_pass = all(checks.values())
        
        # Warnings
        warnings = []
        if not checks['risk_within_limit']:
            warnings.append(f"⚠️ Risk {risk_pct:.2f}% exceeds maximum {self.max_risk_pct}%")
        if not checks['rr_t1_acceptable']:
            warnings.append(f"⚠️ T1 R:R {rr_t1:.2f} below minimum 2:1")
        if not checks['rr_t2_acceptable']:
            warnings.append(f"⚠️ T2 R:R {rr_t2:.2f} below minimum 4:1")
        if not checks['stop_below_entry']:
            warnings.append("⚠️ Stop loss must be below entry")
        if not checks['targets_above_entry']:
            warnings.append("⚠️ Targets must be above entry")
        if not checks['t2_above_t1']:
            warnings.append("⚠️ T2 must be above T1")
        
        return {
            'valid': all_checks_pass,
            'checks': checks,
            'warnings': warnings,
            'risk_pct': risk_pct,
            'risk_usd': total_risk,
            'rr_t1': rr_t1,
            'rr_t2': rr_t2,
            'btc_amount': btc_amount
        }
    
    def generate_trade_plan(
        self,
        capital_available: float,
        current_price: float,
        df: pd.DataFrame,
        confidence: float,
        strategy: str = 'TACTICAL'
    ) -> Dict:
        """
        Generate complete trade plan with all risk parameters.
        
        Args:
            capital_available: Available trading capital
            current_price: Current BTC price
            df: Price DataFrame for volatility calculation
            confidence: System confidence (0.0-1.0)
            strategy: Strategy type ('TACTICAL' or 'DCA')
            
        Returns:
            Complete trade plan with entry, stops, targets, sizing
        """
        # Calculate stop loss
        stop_loss_price, stop_loss_pct = self.calculate_dynamic_stop_loss(
            df, current_price
        )
        
        # Calculate position size
        position = self.calculate_position_size(
            capital_available,
            current_price,
            stop_loss_price,
            confidence
        )
        
        # Calculate targets (only for TACTICAL)
        if strategy == 'TACTICAL':
            targets = self.calculate_targets(current_price)
        else:
            targets = {
                't1_target': None,
                't2_target': None,
                'entry_price': current_price
            }
        
        # Validate setup (only for TACTICAL)
        if strategy == 'TACTICAL' and targets['t1_target']:
            validation = self.validate_trade_setup(
                current_price,
                stop_loss_price,
                targets['t1_target'],
                targets['t2_target'],
                position['position_size_usd'],
                capital_available
            )
        else:
            validation = {'valid': True, 'warnings': []}
        
        return {
            'strategy': strategy,
            'entry_price': current_price,
            'stop_loss': {
                'price': stop_loss_price,
                'pct': stop_loss_pct,
                'distance_usd': current_price - stop_loss_price
            },
            'targets': targets,
            'position': position,
            'validation': validation,
            'capital_available': capital_available,
            'confidence': confidence,
            'timestamp': pd.Timestamp.now()
        }
