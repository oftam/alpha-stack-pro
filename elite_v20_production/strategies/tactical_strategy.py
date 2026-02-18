"""
Elite v20 - Tactical Strategy
Short-term trading strategy (T1/T2 protocol)

Allocation: 40% of capital
Targets: T1 (+5%), T2 (+12%)
Protocol: Active management with stops
"""

from datetime import datetime
from typing import Dict, Optional, Tuple
import pandas as pd


class TacticalStrategy:
    """
    Tactical trading strategy for active profit capture.
    
    Entry Triggers:
    - Manifold Score >80 (Top 2% event)
    - Regime shift detection
    - Phase transition points
    - Override protocol activation
    
    Exit Protocol:
    - T1 (+5%): Exit 50%, move stop to breakeven
    - T2 (+12%): Trail stop 3%
    - Stop Loss: Dynamic 2σ volatility-based
    
    Risk Management:
    - Kelly Criterion (capped 1.5x)
    - Never risk >5% per trade
    - Confidence-adjusted sizing
    """
    
    def __init__(self):
        """Initialize Tactical strategy."""
        self.name = "TACTICAL_ACTIVE"
        self.allocation_pct = 40.0
        
        # Entry thresholds
        self.min_manifold_score = 80.0
        self.min_confidence = 0.80  # 80%
        
        # Target percentages
        self.t1_pct = 5.0  # +5%
        self.t2_pct = 12.0  # +12%
        self.trail_stop_pct = 3.0  # 3% trail
        
        # Active positions
        self.positions = []
        self.closed_positions = []
        
        # Performance tracking
        self.wins = 0
        self.losses = 0
        self.total_pnl = 0.0
    
    def check_entry_signal(
        self,
        manifold_score: float,
        confidence: float,
        regime: str,
        phase_transition: bool = False
    ) -> Dict:
        """
        Check if Tactical entry conditions are met.
        
        Conditions:
        1. Manifold Score >80 (Top 2%)
        2. Confidence >80%
        3. Regime suitable (BLOOD_IN_STREETS or transition)
        4. No conflicting positions
        
        Args:
            manifold_score: Manifold DNA score
            confidence: System confidence (0.0-1.0)
            regime: Current market regime
            phase_transition: Whether phase transition detected
            
        Returns:
            Dict with signal status and details
        """
        # Check conditions
        conditions = {
            'manifold_high': manifold_score >= self.min_manifold_score,
            'confidence_high': confidence >= self.min_confidence,
            'regime_suitable': regime in ['BLOOD_IN_STREETS', 'CHAOS'] or phase_transition,
            'no_conflict': len(self.positions) == 0  # Only one position at a time
        }
        
        # Signal strength
        met_conditions = sum(conditions.values())
        signal_strength = met_conditions / len(conditions)
        
        # Strong signal if all conditions met
        strong_signal = all(conditions.values())
        
        return {
            'signal': strong_signal,
            'signal_strength': signal_strength,
            'conditions': conditions,
            'manifold_score': manifold_score,
            'confidence': confidence,
            'regime': regime,
            'phase_transition': phase_transition
        }
    
    def open_position(
        self,
        entry_price: float,
        position_size_usd: float,
        position_size_btc: float,
        stop_loss_price: float,
        t1_target: float,
        t2_target: float,
        manifold_score: float,
        confidence: float,
        regime: str
    ) -> str:
        """
        Open new Tactical position.
        
        Args:
            entry_price: Entry price
            position_size_usd: Position size in USD
            position_size_btc: Position size in BTC
            stop_loss_price: Initial stop loss price
            t1_target: T1 target price
            t2_target: T2 target price
            manifold_score: Manifold score at entry
            confidence: Confidence at entry
            regime: Regime at entry
            
        Returns:
            Position ID
        """
        position_id = f"TAC_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        position = {
            'id': position_id,
            'status': 'OPEN',
            'entry_time': datetime.now(),
            'entry_price': entry_price,
            'position_size_usd': position_size_usd,
            'position_size_btc': position_size_btc,
            'initial_size_btc': position_size_btc,
            'stop_loss': stop_loss_price,
            't1_target': t1_target,
            't2_target': t2_target,
            't1_hit': False,
            't2_hit': False,
            'trail_stop_active': False,
            'trail_stop_price': None,
            'manifold_score': manifold_score,
            'confidence': confidence,
            'regime': regime,
            'highest_price': entry_price,
            'exits': []
        }
        
        self.positions.append(position)
        return position_id
    
    def update_position(
        self,
        position_id: str,
        current_price: float
    ) -> Dict:
        """
        Update position and check for exits.
        
        Args:
            position_id: Position ID
            current_price: Current BTC price
            
        Returns:
            Dict with position status and actions
        """
        position = self._get_position(position_id)
        if not position:
            return {'error': 'Position not found'}
        
        # Update highest price
        if current_price > position['highest_price']:
            position['highest_price'] = current_price
        
        actions = []
        
        # Check T1 hit
        if not position['t1_hit'] and current_price >= position['t1_target']:
            actions.append({
                'type': 'T1_HIT',
                'action': 'EXIT_50_PCT',
                'price': current_price
            })
            position['t1_hit'] = True
            # Move stop to breakeven
            position['stop_loss'] = position['entry_price']
        
        # Check T2 hit
        if position['t1_hit'] and not position['t2_hit'] and current_price >= position['t2_target']:
            actions.append({
                'type': 'T2_HIT',
                'action': 'ACTIVATE_TRAIL',
                'price': current_price
            })
            position['t2_hit'] = True
            position['trail_stop_active'] = True
            # Set initial trail stop
            position['trail_stop_price'] = current_price * (1 - self.trail_stop_pct / 100)
        
        # Update trail stop
        if position['trail_stop_active']:
            new_trail = current_price * (1 - self.trail_stop_pct / 100)
            if new_trail > position['trail_stop_price']:
                position['trail_stop_price'] = new_trail
        
        # Check stop loss hit
        stop_price = position['trail_stop_price'] if position['trail_stop_active'] else position['stop_loss']
        if current_price <= stop_price:
            actions.append({
                'type': 'STOP_HIT',
                'action': 'EXIT_ALL',
                'price': current_price,
                'stop_type': 'TRAIL' if position['trail_stop_active'] else 'FIXED'
            })
        
        # Calculate unrealized P&L
        unrealized_pnl = (current_price - position['entry_price']) * position['position_size_btc']
        unrealized_pct = ((current_price / position['entry_price']) - 1) * 100
        
        return {
            'position_id': position_id,
            'status': position['status'],
            'current_price': current_price,
            'entry_price': position['entry_price'],
            'position_size_btc': position['position_size_btc'],
            'stop_loss': stop_price,
            't1_hit': position['t1_hit'],
            't2_hit': position['t2_hit'],
            'trail_active': position['trail_stop_active'],
            'unrealized_pnl': unrealized_pnl,
            'unrealized_pct': unrealized_pct,
            'actions': actions
        }
    
    def execute_exit(
        self,
        position_id: str,
        exit_type: str,
        exit_price: float,
        exit_pct: float = 100.0
    ) -> Dict:
        """
        Execute position exit (T1, T2, or Stop).
        
        Args:
            position_id: Position ID
            exit_type: Exit type ('T1', 'T2', 'STOP', 'TRAIL')
            exit_price: Exit price
            exit_pct: Percentage to exit (50% for T1, 100% for others)
            
        Returns:
            Dict with exit details and P&L
        """
        position = self._get_position(position_id)
        if not position:
            return {'error': 'Position not found'}
        
        # Calculate exit
        btc_to_exit = position['position_size_btc'] * (exit_pct / 100)
        usd_proceeds = btc_to_exit * exit_price
        usd_cost = btc_to_exit * position['entry_price']
        realized_pnl = usd_proceeds - usd_cost
        realized_pct = ((exit_price / position['entry_price']) - 1) * 100
        
        # Record exit
        exit_record = {
            'time': datetime.now(),
            'type': exit_type,
            'price': exit_price,
            'btc_amount': btc_to_exit,
            'usd_proceeds': usd_proceeds,
            'realized_pnl': realized_pnl,
            'realized_pct': realized_pct
        }
        position['exits'].append(exit_record)
        
        # Update position
        position['position_size_btc'] -= btc_to_exit
        position['position_size_usd'] -= usd_cost
        
        # Update performance tracking
        self.total_pnl += realized_pnl
        if realized_pnl > 0:
            self.wins += 1
        else:
            self.losses += 1
        
        # Close position if fully exited
        if position['position_size_btc'] <= 0.0001:  # Close to zero
            position['status'] = 'CLOSED'
            position['close_time'] = datetime.now()
            position['final_pnl'] = sum(e['realized_pnl'] for e in position['exits'])
            position['final_pct'] = ((exit_price / position['entry_price']) - 1) * 100
            
            self.closed_positions.append(position)
            self.positions = [p for p in self.positions if p['id'] != position_id]
        
        return {
            'position_id': position_id,
            'exit_type': exit_type,
            'exit_price': exit_price,
            'btc_exited': btc_to_exit,
            'usd_proceeds': usd_proceeds,
            'realized_pnl': realized_pnl,
            'realized_pct': realized_pct,
            'remaining_btc': position['position_size_btc'],
            'position_closed': position['status'] == 'CLOSED'
        }
    
    def _get_position(self, position_id: str) -> Optional[Dict]:
        """Get position by ID."""
        for position in self.positions:
            if position['id'] == position_id:
                return position
        return None
    
    def get_active_positions(self) -> list:
        """Get all active positions."""
        return self.positions.copy()
    
    def get_closed_positions(self) -> pd.DataFrame:
        """Get closed positions as DataFrame."""
        if not self.closed_positions:
            return pd.DataFrame()
        return pd.DataFrame(self.closed_positions)
    
    def get_performance_stats(self) -> Dict:
        """
        Get strategy performance statistics.
        
        Returns:
            Dict with win rate, P&L, R:R ratio
        """
        total_trades = self.wins + self.losses
        win_rate = (self.wins / total_trades) if total_trades > 0 else 0
        
        # Calculate average win/loss
        closed_df = self.get_closed_positions()
        if not closed_df.empty:
            winners = closed_df[closed_df['final_pnl'] > 0]
            losers = closed_df[closed_df['final_pnl'] < 0]
            
            avg_win = winners['final_pnl'].mean() if len(winners) > 0 else 0
            avg_loss = abs(losers['final_pnl'].mean()) if len(losers) > 0 else 1
            
            rr_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        else:
            avg_win = 0
            avg_loss = 0
            rr_ratio = 0
        
        return {
            'total_trades': total_trades,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate': win_rate,
            'win_rate_pct': win_rate * 100,
            'total_pnl': self.total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'rr_ratio': rr_ratio,
            'active_positions': len(self.positions)
        }
    
    def generate_tactical_plan(
        self,
        signal_data: Dict,
        risk_plan: Dict
    ) -> Dict:
        """
        Generate complete Tactical trade plan.
        
        Args:
            signal_data: Signal check data from check_entry_signal()
            risk_plan: Risk plan from RiskManagementEngine
            
        Returns:
            Complete Tactical plan
        """
        if not signal_data['signal']:
            return {
                'execute': False,
                'reason': 'Tactical conditions not met',
                'signal_strength': signal_data['signal_strength'],
                'conditions': signal_data['conditions']
            }
        
        if not risk_plan['validation']['valid']:
            return {
                'execute': False,
                'reason': 'Risk validation failed',
                'warnings': risk_plan['validation']['warnings']
            }
        
        return {
            'execute': True,
            'strategy': self.name,
            'signal_strength': signal_data['signal_strength'],
            'entry': {
                'price': risk_plan['entry_price'],
                'position_size_usd': risk_plan['position']['position_size_usd'],
                'position_size_btc': risk_plan['position']['position_size_btc']
            },
            'stop_loss': {
                'price': risk_plan['stop_loss']['price'],
                'pct': risk_plan['stop_loss']['pct']
            },
            'targets': {
                't1': {
                    'price': risk_plan['targets']['t1_target'],
                    'pct': risk_plan['targets']['t1_pct'],
                    'action': 'EXIT 50%, STOP TO BE'
                },
                't2': {
                    'price': risk_plan['targets']['t2_target'],
                    'pct': risk_plan['targets']['t2_pct'],
                    'action': f"TRAIL STOP {risk_plan['targets']['trail_stop_pct']}%"
                }
            },
            'risk': {
                'risk_usd': risk_plan['validation']['risk_usd'],
                'risk_pct': risk_plan['validation']['risk_pct'],
                'rr_t1': risk_plan['validation']['rr_t1'],
                'rr_t2': risk_plan['validation']['rr_t2']
            },
            'context': {
                'manifold_score': signal_data['manifold_score'],
                'confidence': signal_data['confidence'],
                'regime': signal_data['regime']
            },
            'edge': {
                'win_probability': risk_plan['position']['kelly_fraction'],
                'confidence': signal_data['confidence']
            }
        }
