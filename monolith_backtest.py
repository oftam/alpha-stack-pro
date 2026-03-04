#!/usr/bin/env python3
"""
🚀 MONOLITH BACKTEST ENGINE - Elite v20
========================================
The definitive validation engine for the Medallion system.
Unlike simple backtesters, this runs the ACTUAL EliteDashboardAdapter
over historical slices, simulating real-time TQFT/Quantum/HMM logic.

Features:
- Victory Protocol validation (82 DNA / 91% Confidence)
- Dynamic Kelly Sizing (Risk Engine integration)
- Institutional Metrics (CAGR, Sortino, Max Drawdown)
- Proxy-aware simulation (Volume Divergence proxy for historical on-chain)
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
import time
from tqdm import tqdm

from dashboard_adapter import EliteDashboardAdapter, DataTier
from backtest_sniper_v2 import compute_onchain_proxy, fetch_btc_daily, fetch_fear_greed_history

class MonolithBacktestEngine:
    """
    Orchestrates historical simulation using the full monolithic engine suite.
    """
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        # Start with default proxy adapter (no keys needed for backtest)
        self.adapter = EliteDashboardAdapter()
        
        # Set BACKTEST mode to relax strict execution filters (Phase 14.1 fix)
        if hasattr(self.adapter, 'gates'):
            self.adapter.gates.mode = "BACKTEST"
            
        self.results = []
        self.equity_curve = []
        
    def run_simulation(self, 
                       df: pd.DataFrame, 
                       lookback_period: int = 100,
                       start_offset: int = 200) -> Dict:
        """
        Runs the simulation loop.
        
        Args:
            df: Full historical DataFrame with OHLCV
            lookback_period: Data window passed to adapter for each slice
            start_offset: Where to start simulation (to allow MA/HMM warm-up)
        """
        print(f"🧬 Initiating Monolithic Simulation ({len(df) - start_offset} steps)...")
        
        # Ensure we have the on-chain proxy in the data
        if 'onchain_proxy' not in df.columns:
            df = compute_onchain_proxy(df)
            
        capital = self.initial_capital
        position = 0.0 # BTC amount
        trades = []
        history = []
        
        # Simulation Loop
        for i in tqdm(range(start_offset, len(df))):
            # 1. Slice the window (The 'Now' moment for the engine)
            current_df = df.iloc[i-lookback_period : i+1].copy()
            current_price = float(current_df['close'].iloc[-1])
            ts = current_df.index[-1] if hasattr(current_df.index, 'iloc') else i
            
            # 2. Run the FULL ADAPTER (The expensive part)
            # We mock the 'On-chain' result to use our proxy data
            results = self.adapter.analyze_elite(
                df=current_df,
                exposure_pct=(position * current_price / capital) * 100 if capital > 0 else 0,
                drawdown_pct=0, # Simplified for backtest
                base_action='HOLD'
            )
            
            # 3. Strategy Logic (Victory Protocol)
            action = results.get('final_action', 'HOLD')
            elite_score = results.get('elite_score', 50)
            confidence = results.get('confidence', 0.5)
            
            # Risk Sizing (Fractional Kelly)
            risk_guidance = results.get('risk_guidance', {})
            opt_size_pct = risk_guidance.get('optimal_position_pct', 5.0) / 100.0
            
            # Entry/Exit Logic (compounding)
            trade_executed = False
            if action in ['SNIPER_BUY', 'BUY', 'ADD_AGGRESSIVE'] and position == 0:
                # 🎯 ENTRY: "Victory Protocol" alignment
                pos_size_usd = capital * opt_size_pct
                position = pos_size_usd / current_price
                capital -= pos_size_usd
                trades.append({
                    'type': 'BUY',
                    'price': current_price,
                    'time': ts,
                    'elite_score': elite_score,
                    'reason': f"VICTORY PROTOCOL ENTRY (DNA: {elite_score:.1f}, Confidence: {confidence:.2%})"
                })
                trade_executed = True
                
            elif action in ['REDUCE_35', 'SELL', 'EXIT'] and position > 0:
                # 🛑 EXIT: Risk Mitigation
                proceeds = position * current_price
                capital += proceeds
                position = 0.0
                trades.append({
                    'type': 'SELL',
                    'price': current_price,
                    'time': ts,
                    'elite_score': elite_score,
                    'reason': f"PROTOCOL EXIT (DNA: {elite_score:.1f})"
                })
                trade_executed = True
            
            # Phase 14.1: Log skipped trades for debugging (Veto check)
            if action in ['SNIPER_BUY', 'BUY', 'ADD_AGGRESSIVE'] and not trade_executed:
                gates_info = results.get('gates', {})
                failed = gates_info.get('failed_gate', 'Unknown')
                # Optional: log rejections for diagnostics
                # print(f"Skipped trade at {ts} | Veto: {failed}")
            
            # 5. Record State
            total_equity = capital + (position * current_price)
            history.append({
                'timestamp': ts,
                'price': current_price,
                'equity': total_equity,
                'elite_score': elite_score,
                'confidence': confidence,
                'action': action,
                'position': position
            })
            
        # Compile Metrics
        final_history = pd.DataFrame(history)
        metrics = self._calculate_metrics(final_history)
        
        return {
            'metrics': metrics,
            'history': final_history,
            'trades': trades
        }

    def _calculate_metrics(self, history_df: pd.DataFrame) -> Dict:
        """Professional institutional performance metrics"""
        if history_df.empty: return {}
        
        returns = history_df['equity'].pct_change().dropna()
        total_return_pct = (history_df['equity'].iloc[-1] / history_df['equity'].iloc[0] - 1) * 100
        
        # CAGR (simplified for daily data)
        days = len(history_df)
        cagr = ((history_df['equity'].iloc[-1] / history_df['equity'].iloc[0]) ** (365/days) - 1) * 100 if days > 0 else 0
        
        # Volatility & Sortino
        vol = returns.std() * np.sqrt(365)
        downside_vol = returns[returns < 0].std() * np.sqrt(365)
        sortino = (cagr / downside_vol) if downside_vol > 0 else 0
        
        # Drawdown
        rolling_max = history_df['equity'].cummax()
        drawdown = (history_df['equity'] - rolling_max) / rolling_max
        max_dd = float(drawdown.min() * 100)
        
        return {
            'total_return_pct': float(total_return_pct),
            'cagr_pct': float(cagr),
            'max_drawdown_pct': max_dd,
            'sortino_ratio': float(sortino),
            'volatility_ann': float(vol * 100),
            'win_rate': 0.0, # To be calculated from trades
            'sharpe_ratio': (cagr / vol) if vol > 0 else 0
        }

if __name__ == "__main__":
    # Test script
    print("🧪 Testing Monolith Backtest Engine...")
    
    # 1. Fetch historical data
    price_df = fetch_btc_daily(days=365)
    
    if not price_df.empty:
        engine = MonolithBacktestEngine(initial_capital=100000)
        results = engine.run_simulation(price_df, start_offset=200)
        
        metrics = results['metrics']
        print("\n" + "="*40)
        print("🏛️ INSTITUTIONAL BACKTEST VERDICT")
        print("="*40)
        print(f"Total Return:   {metrics['total_return_pct']:+.1f}%")
        print(f"CAGR:           {metrics['cagr_pct']:+.1f}%")
        print(f"Max Drawdown:   {metrics['max_drawdown_pct']:.1f}%")
        print(f"Sortino:        {metrics['sortino_ratio']:.2f}")
        print("="*40)
    else:
        print("❌ Failed to fetch test data")
