#!/usr/bin/env python3
"""
BACKTEST: SNIPER MODE Null Hypothesis Test
==========================================
Validates: "When Fear < 15 and the market dips, does buying actually work?"

This script answers the REAL question:
- Out of all historical "Extreme Fear" events, how many led to positive returns?
- What is the ACTUAL Win Rate (not the Bayesian estimate)?

Usage:
    python backtest_sniper.py
"""

import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import ccxt
import json


def fetch_fear_greed_history(days: int = 365) -> pd.DataFrame:
    """
    Fetch historical Fear & Greed Index from alternative.me
    Free API: up to 365 days of daily history
    """
    print(f"📊 Fetching Fear & Greed history ({days} days)...")
    url = f"https://api.alternative.me/fng/?limit={days}&format=json"
    
    try:
        r = requests.get(url, timeout=15)
        data = r.json()['data']
        
        df = pd.DataFrame(data)
        df['value'] = df['value'].astype(int)
        df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='s')
        df = df[['timestamp', 'value', 'value_classification']].sort_values('timestamp').reset_index(drop=True)
        df.columns = ['date', 'fear_greed', 'classification']
        
        print(f"   ✅ Got {len(df)} days of F&G data")
        return df
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return pd.DataFrame()


def fetch_btc_price_history(days: int = 365) -> pd.DataFrame:
    """
    Fetch historical BTC daily prices from exchange
    Uses multi-exchange fallback
    """
    print(f"📊 Fetching BTC price history ({days} days)...")
    
    for ex_name in ['bybit', 'kraken', 'okx', 'binance']:
        try:
            exchange = getattr(ccxt, ex_name)()
            since = exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
            ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1d', since=since, limit=days)
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.normalize()
            df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
            
            print(f"   ✅ Got {len(df)} days from {ex_name}")
            return df
        except Exception as e:
            print(f"   ⚠️ {ex_name} failed: {e}")
            continue
    
    print("   ❌ All exchanges failed!")
    return pd.DataFrame()


def run_backtest(fear_threshold: int = 15, 
                 hold_days: int = 30,
                 min_days: int = 365) -> dict:
    """
    Null Hypothesis Test:
    H0: "Buying when Fear < threshold has no edge over random"
    
    Args:
        fear_threshold: Buy when F&G drops below this (default 15 = Extreme Fear)
        hold_days: How many days to hold after signal (default 30)
        min_days: Minimum data needed (default 365)
    
    Returns:
        dict with backtest results
    """
    
    print("=" * 60)
    print("🔬 SNIPER MODE BACKTEST — Null Hypothesis Test")
    print("=" * 60)
    print(f"   Fear threshold: < {fear_threshold}")
    print(f"   Hold period: {hold_days} days")
    print()
    
    # 1. Fetch data
    fg_df = fetch_fear_greed_history(min_days)
    price_df = fetch_btc_price_history(min_days)
    
    if fg_df.empty or price_df.empty:
        print("❌ Cannot run backtest — insufficient data")
        return {'error': 'Insufficient data'}
    
    # 2. Merge on date
    fg_df['date'] = fg_df['date'].dt.normalize()
    price_df['date'] = price_df['date'].dt.normalize()
    merged = pd.merge(fg_df, price_df, on='date', how='inner')
    merged = merged.sort_values('date').reset_index(drop=True)
    
    print(f"\n📊 Merged dataset: {len(merged)} days")
    print(f"   Date range: {merged['date'].iloc[0].strftime('%Y-%m-%d')} → {merged['date'].iloc[-1].strftime('%Y-%m-%d')}")
    
    # 3. Find all "Extreme Fear" signals
    signals = []
    
    for i in range(len(merged) - hold_days):
        row = merged.iloc[i]
        
        if row['fear_greed'] < fear_threshold:
            entry_price = row['close']
            exit_price = merged.iloc[i + hold_days]['close']
            return_pct = (exit_price / entry_price - 1) * 100
            
            signals.append({
                'date': row['date'],
                'fear_greed': row['fear_greed'],
                'classification': row['classification'],
                'entry_price': entry_price,
                'exit_price': exit_price,
                'return_pct': return_pct,
                'win': return_pct > 0
            })
    
    if not signals:
        print(f"\n⚠️ No signals found with Fear < {fear_threshold}")
        return {'error': f'No signals found with Fear < {fear_threshold}'}
    
    signals_df = pd.DataFrame(signals)
    
    # 4. Calculate statistics
    total = len(signals_df)
    wins = signals_df['win'].sum()
    losses = total - wins
    win_rate = wins / total * 100
    avg_return = signals_df['return_pct'].mean()
    median_return = signals_df['return_pct'].median()
    best = signals_df['return_pct'].max()
    worst = signals_df['return_pct'].min()
    
    # 5. Binomial test: is win rate significantly > 50%?
    from scipy import stats
    p_value = stats.binomtest(int(wins), total, 0.5, alternative='greater').pvalue
    
    # 6. Compare to random baseline
    all_returns = []
    for i in range(len(merged) - hold_days):
        r = (merged.iloc[i + hold_days]['close'] / merged.iloc[i]['close'] - 1) * 100
        all_returns.append(r)
    
    random_avg = np.mean(all_returns)
    random_win_rate = sum(1 for r in all_returns if r > 0) / len(all_returns) * 100
    
    # 7. Print results
    print("\n" + "=" * 60)
    print("📊 BACKTEST RESULTS")
    print("=" * 60)
    
    print(f"\n🎯 Signals Found: {total}")
    print(f"   (Days where Fear & Greed < {fear_threshold})")
    
    print(f"\n📈 SNIPER MODE Performance ({hold_days}-day hold):")
    print(f"   Win Rate:      {win_rate:.1f}%  ({wins}W / {losses}L)")
    print(f"   Avg Return:    {avg_return:+.1f}%")
    print(f"   Median Return: {median_return:+.1f}%")
    print(f"   Best Trade:    {best:+.1f}%")
    print(f"   Worst Trade:   {worst:+.1f}%")
    
    print(f"\n📉 Random Baseline ({hold_days}-day hold, any day):")
    print(f"   Win Rate:      {random_win_rate:.1f}%")
    print(f"   Avg Return:    {random_avg:+.1f}%")
    
    print(f"\n🔬 Statistical Significance:")
    print(f"   p-value:       {p_value:.4f}")
    if p_value < 0.01:
        print(f"   Result:        ✅ SIGNIFICANT (p < 0.01) — Edge is REAL")
    elif p_value < 0.05:
        print(f"   Result:        ⚠️ MARGINALLY significant (p < 0.05)")
    else:
        print(f"   Result:        ❌ NOT significant (p ≥ 0.05) — No proven edge")
    
    # Edge over random
    edge = avg_return - random_avg
    print(f"\n💡 Edge over Random: {edge:+.1f}% per trade")
    
    print("\n" + "-" * 60)
    print("📋 All Signals:")
    print("-" * 60)
    for _, s in signals_df.iterrows():
        emoji = "✅" if s['win'] else "❌"
        print(f"   {s['date'].strftime('%Y-%m-%d')} | F&G: {s['fear_greed']:2d} | "
              f"${s['entry_price']:,.0f} → ${s['exit_price']:,.0f} | "
              f"{s['return_pct']:+.1f}% {emoji}")
    
    print("\n" + "=" * 60)
    
    # Quick verdict
    if win_rate > 70 and p_value < 0.05 and avg_return > random_avg:
        print("🟢 VERDICT: SNIPER MODE has a statistically validated edge!")
    elif win_rate > 50 and avg_return > 0:
        print("🟡 VERDICT: SNIPER MODE shows positive returns but needs more data")
    else:
        print("🔴 VERDICT: SNIPER MODE does NOT show a significant edge")
    
    print("=" * 60)
    
    return {
        'total_signals': total,
        'wins': int(wins),
        'losses': int(losses),
        'win_rate': round(win_rate, 1),
        'avg_return': round(avg_return, 1),
        'median_return': round(median_return, 1),
        'best_trade': round(best, 1),
        'worst_trade': round(worst, 1),
        'p_value': round(p_value, 4),
        'random_win_rate': round(random_win_rate, 1),
        'random_avg_return': round(random_avg, 1),
        'edge': round(edge, 1),
        'signals': signals
    }


# ============================================================================
# MULTI-THRESHOLD ANALYSIS
# ============================================================================

def run_sensitivity_analysis():
    """
    Test multiple fear thresholds and hold periods
    to find the optimal SNIPER parameters
    """
    print("\n" + "=" * 60)
    print("🧪 SENSITIVITY ANALYSIS")
    print("   (Which Fear threshold + Hold period gives best results?)")
    print("=" * 60)
    
    results = []
    for threshold in [10, 15, 20, 25]:
        for hold in [7, 14, 30, 60]:
            try:
                r = run_backtest(fear_threshold=threshold, hold_days=hold)
                if 'error' not in r:
                    results.append({
                        'threshold': threshold,
                        'hold_days': hold,
                        **r
                    })
            except Exception as e:
                print(f"   ⚠️ Skipping threshold={threshold}, hold={hold}: {e}")
    
    if results:
        print("\n📊 SENSITIVITY MATRIX:")
        print(f"{'Threshold':>10} | {'Hold':>6} | {'Signals':>8} | {'Win Rate':>9} | {'Avg Return':>11} | {'p-value':>8}")
        print("-" * 70)
        for r in sorted(results, key=lambda x: x['avg_return'], reverse=True):
            sig = "✅" if r['p_value'] < 0.05 else "❌"
            print(f"{r['threshold']:>10} | {r['hold_days']:>6} | {r['total_signals']:>8} | "
                  f"{r['win_rate']:>8.1f}% | {r['avg_return']:>+10.1f}% | {r['p_value']:>7.4f} {sig}")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Basic backtest with default parameters
    results = run_backtest(fear_threshold=15, hold_days=30)
    
    # Optionally run sensitivity analysis
    # run_sensitivity_analysis()
