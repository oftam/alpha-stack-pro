#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validation Framework - Backtest & Performance Metrics
Tests ensemble forecaster on historical data
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from forecasting.ensemble import EnsembleForecaster


class ForecastValidator:
    """
    Comprehensive validation for forecasting models
    
    Metrics:
    - MAE (Mean Absolute Error)
    - RMSE (Root Mean Squared Error)
    - Coverage (% of actuals within P10-P90)
    - Sharpness (width of P10-P90)
    - Bias (systematic over/under prediction)
    - Directional accuracy (did we get direction right?)
    """
    
    def __init__(self):
        self.results = []
    
    def backtest(self,
                df: pd.DataFrame,
                start_date: str,
                end_date: str,
                horizon: int = 24,
                step: int = 24,
                enable_garch: bool = True,
                enable_var: bool = False,
                enable_lstm: bool = False) -> pd.DataFrame:
        """
        Run backtest on historical data
        
        Args:
            df: Historical OHLCV DataFrame
            start_date: Start of test period
            end_date: End of test period
            horizon: Forecast horizon
            step: Step size between forecasts
            enable_*: Which models to test
            
        Returns:
            DataFrame with results for each forecast
        """
        
        print("=" * 60)
        print("BACKTESTING ENSEMBLE FORECASTER")
        print("=" * 60)
        
        # Initialize ensemble
        ensemble = EnsembleForecaster(
            enable_bootstrap=True,
            enable_garch=enable_garch,
            enable_var=enable_var,
            enable_lstm=enable_lstm
        )
        
        # Extract close series
        close = df['close'] if 'close' in df.columns else df['Close']
        
        # Find date indices
        start_idx = close.index.get_indexer([start_date], method='nearest')[0]
        end_idx = close.index.get_indexer([end_date], method='nearest')[0]
        
        # Iterate through test period
        results = []
        n_forecasts = 0
        n_success = 0
        
        for i in range(start_idx, end_idx - horizon, step):
            forecast_date = close.index[i]
            
            # Training data (everything before this point)
            train_close = close.iloc[:i]
            
            # Actual future (what really happened)
            actual_future = close.iloc[i:i + horizon + 1].values
            
            if len(actual_future) < horizon + 1:
                break  # Not enough future data
            
            try:
                # Generate forecast
                forecast = ensemble.forecast(
                    train_close,
                    horizon=horizon,
                    n_paths=500
                )
                
                # Compute metrics
                p50_forecast = forecast['p50']
                p10_forecast = forecast['p10']
                p90_forecast = forecast['p90']
                
                # Errors
                mae = np.mean(np.abs(actual_future - p50_forecast))
                rmse = np.sqrt(np.mean((actual_future - p50_forecast) ** 2))
                
                # Relative errors (%)
                mae_pct = mae / actual_future[0] * 100
                rmse_pct = rmse / actual_future[0] * 100
                
                # Coverage: % of actuals within P10-P90
                within_bounds = ((actual_future >= p10_forecast) & 
                                (actual_future <= p90_forecast))
                coverage = within_bounds.mean() * 100
                
                # Sharpness: average width of prediction interval
                interval_width = p90_forecast - p10_forecast
                sharpness = np.mean(interval_width / actual_future * 100)
                
                # Bias: average forecast - actual
                bias = np.mean(p50_forecast - actual_future)
                bias_pct = bias / actual_future[0] * 100
                
                # Directional accuracy (24h ahead)
                if horizon >= 24:
                    actual_direction = np.sign(actual_future[24] - actual_future[0])
                    forecast_direction = np.sign(p50_forecast[24] - p50_forecast[0])
                    direction_correct = (actual_direction == forecast_direction)
                else:
                    direction_correct = None
                
                results.append({
                    'date': forecast_date,
                    'actual_price': actual_future[0],
                    'forecast_p50': p50_forecast[24] if horizon >= 24 else p50_forecast[-1],
                    'mae': mae,
                    'rmse': rmse,
                    'mae_pct': mae_pct,
                    'rmse_pct': rmse_pct,
                    'coverage': coverage,
                    'sharpness': sharpness,
                    'bias': bias,
                    'bias_pct': bias_pct,
                    'direction_correct': direction_correct,
                    'regime': forecast['regime'],
                    'n_models': len(forecast['component_forecasts'])
                })
                
                n_success += 1
                
            except Exception as e:
                print(f"  Failed at {forecast_date}: {e}")
                continue
            
            n_forecasts += 1
            
            if n_forecasts % 10 == 0:
                print(f"  Progress: {n_forecasts} forecasts completed")
        
        print(f"\n✅ Backtest complete: {n_success}/{n_forecasts} successful")
        
        results_df = pd.DataFrame(results)
        self.results = results_df
        
        return results_df
    
    def print_summary(self, results: pd.DataFrame = None):
        """Print summary statistics"""
        
        if results is None:
            results = self.results
        
        if len(results) == 0:
            print("No results to summarize")
            return
        
        print("\n" + "=" * 60)
        print("BACKTEST SUMMARY")
        print("=" * 60)
        
        print(f"\nNumber of forecasts: {len(results)}")
        print(f"Date range: {results['date'].min()} to {results['date'].max()}")
        
        print(f"\n📊 Forecast Accuracy:")
        print(f"  MAE: ${results['mae'].mean():,.2f} ({results['mae_pct'].mean():.2f}%)")
        print(f"  RMSE: ${results['rmse'].mean():,.2f} ({results['rmse_pct'].mean():.2f}%)")
        print(f"  Bias: ${results['bias'].mean():,.2f} ({results['bias_pct'].mean():.2f}%)")
        
        print(f"\n📏 Prediction Intervals:")
        print(f"  Coverage (P10-P90): {results['coverage'].mean():.1f}% (target: 80%)")
        print(f"  Sharpness: {results['sharpness'].mean():.1f}%")
        
        if results['direction_correct'].notna().any():
            direction_acc = results['direction_correct'].mean() * 100
            print(f"\n🎯 Directional Accuracy: {direction_acc:.1f}%")
        
        print(f"\n🌍 By Regime:")
        for regime in results['regime'].unique():
            regime_results = results[results['regime'] == regime]
            print(f"  {regime}:")
            print(f"    Count: {len(regime_results)}")
            print(f"    MAE: {regime_results['mae_pct'].mean():.2f}%")
            print(f"    Coverage: {regime_results['coverage'].mean():.1f}%")
        
        print("=" * 60)
    
    def plot_results(self, results: pd.DataFrame = None, save_path: str = None):
        """Plot backtest results"""
        
        if results is None:
            results = self.results
        
        import matplotlib.pyplot as plt
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 1. Forecast error over time
        ax = axes[0, 0]
        ax.plot(results['date'], results['mae_pct'], label='MAE %', alpha=0.7)
        ax.axhline(results['mae_pct'].mean(), color='red', linestyle='--', label='Mean')
        ax.set_title('Forecast Error Over Time')
        ax.set_ylabel('MAE (%)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 2. Coverage over time
        ax = axes[0, 1]
        ax.plot(results['date'], results['coverage'], alpha=0.7)
        ax.axhline(80, color='green', linestyle='--', label='Target (80%)')
        ax.axhline(results['coverage'].mean(), color='red', linestyle='--', label='Mean')
        ax.set_title('Prediction Interval Coverage')
        ax.set_ylabel('Coverage (%)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 3. Error distribution
        ax = axes[1, 0]
        ax.hist(results['mae_pct'], bins=30, alpha=0.7, edgecolor='black')
        ax.axvline(results['mae_pct'].mean(), color='red', linestyle='--', label='Mean')
        ax.axvline(results['mae_pct'].median(), color='green', linestyle='--', label='Median')
        ax.set_title('Distribution of Forecast Errors')
        ax.set_xlabel('MAE (%)')
        ax.set_ylabel('Frequency')
        ax.legend()
        
        # 4. Actual vs Forecast scatter
        ax = axes[1, 1]
        ax.scatter(results['actual_price'], results['forecast_p50'], alpha=0.5)
        
        # Perfect prediction line
        min_val = min(results['actual_price'].min(), results['forecast_p50'].min())
        max_val = max(results['actual_price'].max(), results['forecast_p50'].max())
        ax.plot([min_val, max_val], [min_val, max_val], 'r--', label='Perfect prediction')
        
        ax.set_title('Actual vs Forecast Price')
        ax.set_xlabel('Actual Price')
        ax.set_ylabel('Forecast Price')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"✅ Plot saved to {save_path}")
        else:
            plt.show()


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == '__main__':
    # This script runs a backtest validation
    
    print("Loading historical data...")
    
    # You would load your real data here
    # For demo, generate synthetic
    np.random.seed(42)
    n = 2000
    dates = pd.date_range('2023-01-01', periods=n, freq='1h')
    
    # Create realistic price data with regime changes
    returns = np.random.randn(n) * 0.02
    
    # Add some regime structure
    returns[500:800] *= 2  # High vol period
    returns[1200:1500] += 0.001  # Trending period
    
    prices = 50000 * np.cumprod(1 + returns)
    
    df = pd.DataFrame({
        'close': prices,
        'volume': np.random.randint(100, 1000, n)
    }, index=dates)
    
    print(f"Data: {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    
    # Initialize validator
    validator = ForecastValidator()
    
    # Run backtest
    results = validator.backtest(
        df,
        start_date='2023-08-01',
        end_date='2023-12-01',
        horizon=24,
        step=24,
        enable_garch=True,
        enable_var=False,  # No multi-asset data
        enable_lstm=False
    )
    
    # Print summary
    validator.print_summary(results)
    
    # Plot results
    validator.plot_results(results, save_path='/home/claude/backtest_results.png')
    
    # Save detailed results
    results.to_csv('/home/claude/backtest_results.csv', index=False)
    print("\n✅ Detailed results saved to backtest_results.csv")
