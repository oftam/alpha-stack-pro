"""
Elite v20 - Capital Manager
Dynamic allocation between DCA (60%) and Tactical (40%) strategies
Based on: QC-AI_LITE_Biological_Quant_Architecture.pdf
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Tuple


class CapitalManager:
    """
    Manages dynamic capital allocation across dual strategy system.
    
    Architecture:
    - DCA Strategy: 60% allocation → 2030 accumulation
    - Tactical Strategy: 40% allocation → T1/T2 trading
    
    Capital adjusts based on P&L, liquidity, and market conditions.
    """
    
    def __init__(self, base_capital: float = 10000.0):
        """
        Initialize capital manager.
        
        Args:
            base_capital: Starting capital in USD (default $10,000)
        """
        self.base_capital = base_capital
        self.current_capital = base_capital
        self.pnl = 0.0
        self.pnl_history = []
        
        # Allocation ratios (adjustable)
        self.dca_allocation_pct = 0.60  # 60% to DCA
        self.tactical_allocation_pct = 0.40  # 40% to Tactical
        
        # Track positions
        self.dca_position = {
            'capital': 0.0,
            'btc_held': 0.0,
            'avg_entry': 0.0,
            'unrealized_pnl': 0.0
        }
        
        self.tactical_position = {
            'capital': 0.0,
            'btc_held': 0.0,
            'avg_entry': 0.0,
            'unrealized_pnl': 0.0,
            'realized_pnl': 0.0
        }
        
        # Transaction log
        self.transactions = []
    
    def update_from_pnl(self, realized_pnl: float) -> None:
        """
        Update capital from realized profit/loss.
        
        Args:
            realized_pnl: Realized P&L in USD (positive = profit, negative = loss)
        """
        self.pnl += realized_pnl
        self.current_capital = self.base_capital + self.pnl
        
        # Log P&L
        self.pnl_history.append({
            'timestamp': datetime.now(),
            'realized_pnl': realized_pnl,
            'cumulative_pnl': self.pnl,
            'capital': self.current_capital
        })
    
    def get_allocations(self) -> Dict[str, float]:
        """
        Calculate current capital allocations.
        
        Returns:
            Dict with DCA, Tactical, and Total capital
        """
        dca_capital = self.current_capital * self.dca_allocation_pct
        tactical_capital = self.current_capital * self.tactical_allocation_pct
        
        return {
            'total': self.current_capital,
            'dca': dca_capital,
            'dca_available': dca_capital - self.dca_position['capital'],
            'tactical': tactical_capital,
            'tactical_available': tactical_capital - self.tactical_position['capital'],
            'pnl': self.pnl,
            'pnl_pct': (self.pnl / self.base_capital) * 100 if self.base_capital > 0 else 0
        }
    
    def record_dca_entry(self, btc_amount: float, entry_price: float, usd_spent: float) -> None:
        """
        Record DCA strategy entry.
        
        Args:
            btc_amount: BTC purchased
            entry_price: Entry price per BTC
            usd_spent: USD capital used
        """
        # Update position
        total_btc = self.dca_position['btc_held'] + btc_amount
        total_cost = (self.dca_position['avg_entry'] * self.dca_position['btc_held']) + (entry_price * btc_amount)
        
        self.dca_position['btc_held'] = total_btc
        self.dca_position['avg_entry'] = total_cost / total_btc if total_btc > 0 else 0
        self.dca_position['capital'] += usd_spent
        
        # Log transaction
        self.transactions.append({
            'timestamp': datetime.now(),
            'strategy': 'DCA',
            'action': 'BUY',
            'btc_amount': btc_amount,
            'price': entry_price,
            'usd_amount': usd_spent,
            'position_btc': self.dca_position['btc_held'],
            'avg_entry': self.dca_position['avg_entry']
        })
    
    def record_tactical_entry(self, btc_amount: float, entry_price: float, usd_spent: float) -> None:
        """
        Record Tactical strategy entry.
        
        Args:
            btc_amount: BTC purchased
            entry_price: Entry price per BTC
            usd_spent: USD capital used
        """
        # Update position
        total_btc = self.tactical_position['btc_held'] + btc_amount
        total_cost = (self.tactical_position['avg_entry'] * self.tactical_position['btc_held']) + (entry_price * btc_amount)
        
        self.tactical_position['btc_held'] = total_btc
        self.tactical_position['avg_entry'] = total_cost / total_btc if total_btc > 0 else 0
        self.tactical_position['capital'] += usd_spent
        
        # Log transaction
        self.transactions.append({
            'timestamp': datetime.now(),
            'strategy': 'TACTICAL',
            'action': 'BUY',
            'btc_amount': btc_amount,
            'price': entry_price,
            'usd_amount': usd_spent,
            'position_btc': self.tactical_position['btc_held'],
            'avg_entry': self.tactical_position['avg_entry']
        })
    
    def record_tactical_exit(self, btc_amount: float, exit_price: float, exit_type: str = 'T1') -> float:
        """
        Record Tactical strategy exit (T1/T2/Stop).
        
        Args:
            btc_amount: BTC sold
            exit_price: Exit price per BTC
            exit_type: Type of exit (T1, T2, STOP)
            
        Returns:
            Realized P&L from this exit
        """
        if btc_amount > self.tactical_position['btc_held']:
            btc_amount = self.tactical_position['btc_held']
        
        # Calculate P&L
        cost_basis = self.tactical_position['avg_entry'] * btc_amount
        proceeds = exit_price * btc_amount
        realized_pnl = proceeds - cost_basis
        
        # Update position
        self.tactical_position['btc_held'] -= btc_amount
        self.tactical_position['capital'] -= cost_basis
        self.tactical_position['realized_pnl'] += realized_pnl
        
        # Update total capital
        self.update_from_pnl(realized_pnl)
        
        # Log transaction
        self.transactions.append({
            'timestamp': datetime.now(),
            'strategy': 'TACTICAL',
            'action': f'SELL_{exit_type}',
            'btc_amount': btc_amount,
            'price': exit_price,
            'usd_amount': proceeds,
            'realized_pnl': realized_pnl,
            'position_btc': self.tactical_position['btc_held'],
            'avg_entry': self.tactical_position['avg_entry']
        })
        
        return realized_pnl
    
    def update_unrealized_pnl(self, current_btc_price: float) -> Dict[str, float]:
        """
        Calculate unrealized P&L for both strategies.
        
        Args:
            current_btc_price: Current BTC market price
            
        Returns:
            Dict with unrealized P&L for each strategy
        """
        # DCA unrealized P&L
        dca_market_value = self.dca_position['btc_held'] * current_btc_price
        dca_unrealized = dca_market_value - self.dca_position['capital']
        self.dca_position['unrealized_pnl'] = dca_unrealized
        
        # Tactical unrealized P&L
        tactical_market_value = self.tactical_position['btc_held'] * current_btc_price
        tactical_unrealized = tactical_market_value - self.tactical_position['capital']
        self.tactical_position['unrealized_pnl'] = tactical_unrealized
        
        return {
            'dca_unrealized': dca_unrealized,
            'tactical_unrealized': tactical_unrealized,
            'total_unrealized': dca_unrealized + tactical_unrealized,
            'dca_unrealized_pct': (dca_unrealized / self.dca_position['capital'] * 100) if self.dca_position['capital'] > 0 else 0,
            'tactical_unrealized_pct': (tactical_unrealized / self.tactical_position['capital'] * 100) if self.tactical_position['capital'] > 0 else 0
        }
    
    def get_portfolio_status(self, current_btc_price: float) -> Dict:
        """
        Get complete portfolio status.
        
        Args:
            current_btc_price: Current BTC market price
            
        Returns:
            Complete portfolio snapshot
        """
        allocations = self.get_allocations()
        unrealized = self.update_unrealized_pnl(current_btc_price)
        
        total_value = allocations['total'] + unrealized['total_unrealized']
        total_pnl = self.pnl + unrealized['total_unrealized']
        
        return {
            'capital': {
                'base': self.base_capital,
                'current': self.current_capital,
                'total_value': total_value,
                'pnl_realized': self.pnl,
                'pnl_unrealized': unrealized['total_unrealized'],
                'pnl_total': total_pnl,
                'return_pct': (total_pnl / self.base_capital) * 100
            },
            'dca': {
                'allocation_pct': self.dca_allocation_pct * 100,
                'capital_allocated': allocations['dca'],
                'capital_used': self.dca_position['capital'],
                'capital_available': allocations['dca_available'],
                'btc_held': self.dca_position['btc_held'],
                'avg_entry': self.dca_position['avg_entry'],
                'current_price': current_btc_price,
                'unrealized_pnl': unrealized['dca_unrealized'],
                'unrealized_pct': unrealized['dca_unrealized_pct']
            },
            'tactical': {
                'allocation_pct': self.tactical_allocation_pct * 100,
                'capital_allocated': allocations['tactical'],
                'capital_used': self.tactical_position['capital'],
                'capital_available': allocations['tactical_available'],
                'btc_held': self.tactical_position['btc_held'],
                'avg_entry': self.tactical_position['avg_entry'],
                'current_price': current_btc_price,
                'unrealized_pnl': unrealized['tactical_unrealized'],
                'unrealized_pct': unrealized['tactical_unrealized_pct'],
                'realized_pnl': self.tactical_position['realized_pnl']
            },
            'risk': {
                'max_risk_per_trade_usd': total_value * 0.05,  # Max 5% risk
                'max_risk_per_trade_pct': 5.0
            }
        }
    
    def get_transaction_history(self) -> pd.DataFrame:
        """
        Get transaction history as DataFrame.
        
        Returns:
            DataFrame of all transactions
        """
        if not self.transactions:
            return pd.DataFrame()
        
        return pd.DataFrame(self.transactions)
    
    def export_state(self) -> Dict:
        """
        Export complete manager state for persistence.
        
        Returns:
            Complete state dictionary
        """
        return {
            'base_capital': self.base_capital,
            'current_capital': self.current_capital,
            'pnl': self.pnl,
            'pnl_history': self.pnl_history,
            'dca_position': self.dca_position,
            'tactical_position': self.tactical_position,
            'transactions': self.transactions,
            'allocations': {
                'dca_pct': self.dca_allocation_pct,
                'tactical_pct': self.tactical_allocation_pct
            }
        }
    
    def import_state(self, state: Dict) -> None:
        """
        Import manager state from saved data.
        
        Args:
            state: State dictionary from export_state()
        """
        self.base_capital = state['base_capital']
        self.current_capital = state['current_capital']
        self.pnl = state['pnl']
        self.pnl_history = state['pnl_history']
        self.dca_position = state['dca_position']
        self.tactical_position = state['tactical_position']
        self.transactions = state['transactions']
        self.dca_allocation_pct = state['allocations']['dca_pct']
        self.tactical_allocation_pct = state['allocations']['tactical_pct']
