#!/usr/bin/env python3
"""
BACKTEST V2: Fear + OnChain Proxy (Volume Divergence)
=====================================================
Tests the REAL Elite v20 hypothesis:
  "Fear < 15 ALONE has no edge (proven in v1).
   Fear < 15 + Whale Accumulation = Edge?"

Since CryptoQuant Free = only 7 days history, we use a FREE PROXY:
  Volume Divergence = OBV rising while price drops = Smart Money buying the dip

This is the SAME signal the Diffusion Layer tries to detect,
approximated from publicly available data.

Usage:
    python backtest_sniper_v2.py
"""

import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import ccxt
from scipy import stats


def fetch_fear_greed_history(days: int = 500) -> pd.DataFrame:
    """Fetch historical Fear & Greed Index"""
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
        print(f"   ✅ Got {len(df)} days")
        return df
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return pd.DataFrame()


def fetch_btc_daily(days: int = 500) -> pd.DataFrame:
    """Fetch BTC daily OHLCV with multi-exchange fallback"""
    print(f"📊 Fetching BTC daily data ({days} days)...")
    for ex_name in ['bybit', 'kraken', 'okx', 'binance']:
        try:
            exchange = getattr(ccxt, ex_name)()
            since = exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
            ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1d', since=since, limit=days)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.normalize()
            print(f"   ✅ Got {len(df)} days from {ex_name}")
            return df
        except Exception as e:
            print(f"   ⚠️ {ex_name} failed: {e}")
    return pd.DataFrame()


def compute_onchain_proxy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute OnChain Proxy Score (0-100) using FREE data only.
    
    This approximates what CryptoQuant Netflow + Whale Activity would show,
    using volume analysis patterns:
    
    1. OBV Divergence: Price drops but OBV rises = accumulation (whales buying)
    2. Volume Spike: Abnormally high volume on red candles = capitulation selling
    3. Price vs MA200: Below MA200 = oversold territory
    
    Combined score mimics the Diffusion Layer's logic.
    """
    result = df.copy()
    
    # 1. OBV (On-Balance Volume)
    obv = [0]
    for i in range(1, len(df)):
        if df['close'].iloc[i] > df['close'].iloc[i-1]:
            obv.append(obv[-1] + df['volume'].iloc[i])
        elif df['close'].iloc[i] < df['close'].iloc[i-1]:
            obv.append(obv[-1] - df['volume'].iloc[i])
        else:
            obv.append(obv[-1])
    result['obv'] = obv
    
    # 2. OBV Divergence Score (7-day)
    # Price going down + OBV going up = accumulation signal
    result['price_change_7d'] = result['close'].pct_change(7)
    result['obv_change_7d'] = result['obv'].diff(7)
    
    # Score: higher when price drops but OBV rises
    obv_div_score = []
    for i in range(len(result)):
        pc = result['price_change_7d'].iloc[i]
        oc = result['obv_change_7d'].iloc[i]
        
        if pd.isna(pc) or pd.isna(oc):
            obv_div_score.append(50)  # neutral
        elif pc < -0.03 and oc > 0:
            # Price down > 3% but OBV up = strong accumulation
            obv_div_score.append(85)
        elif pc < 0 and oc > 0:
            # Price down, OBV up = mild accumulation
            obv_div_score.append(70)
        elif pc > 0 and oc > 0:
            # Both up = normal bull
            obv_div_score.append(60)
        elif pc < 0 and oc < 0:
            # Both down = real selling, no accumulation
            obv_div_score.append(30)
        else:
            obv_div_score.append(50)
    
    result['obv_div_score'] = obv_div_score
    
    # 3. Volume Spike (capitulation detector)
    result['vol_ma20'] = result['volume'].rolling(20).mean()
    result['vol_ratio'] = result['volume'] / result['vol_ma20']
    
    # High volume on red candle = capitulation (bullish contrarian)
    vol_spike_score = []
    for i in range(len(result)):
        vr = result['vol_ratio'].iloc[i]
        is_red = result['close'].iloc[i] < result['open'].iloc[i]
        
        if pd.isna(vr):
            vol_spike_score.append(50)
        elif vr > 2.0 and is_red:
            vol_spike_score.append(90)  # Panic selling = perfect buy
        elif vr > 1.5 and is_red:
            vol_spike_score.append(75)
        elif vr > 1.5 and not is_red:
            vol_spike_score.append(65)  # High vol green = breakout
        else:
            vol_spike_score.append(50)
    
    result['vol_spike_score'] = vol_spike_score
    
    # 4. MA200 position
    result['ma200'] = result['close'].rolling(200).mean()
    result['below_ma200'] = (result['close'] < result['ma200']).astype(int) * 20
    
    # 5. Combined OnChain Proxy Score (0-100)
    # Weights: OBV Divergence 50%, Volume Spike 30%, MA200 20%
    result['onchain_proxy'] = (
        result['obv_div_score'] * 0.50 + 
        result['vol_spike_score'] * 0.30 + 
        result['below_ma200'].fillna(0) * 0.5 + 40 * 0.20  # base
    ).clip(0, 100)
    
    return result


def run_backtest_v2(fear_threshold: int = 15,
                    onchain_threshold: int = 70,
                    hold_days: int = 30,
                    data_days: int = 500) -> dict:
    """
    Backtest V2: Fear + OnChain Proxy
    
    Tests 3 strategies:
      A) Fear < 15 only (v1 baseline — already proven: no edge)
      B) OnChain Proxy > threshold only
      C) Fear < 15 AND OnChain Proxy > threshold (the Elite v20 hypothesis)
    """
    
    print("=" * 70)
    print("🔬 BACKTEST V2: Fear + OnChain Proxy (Volume Divergence)")
    print("=" * 70)
    print(f"   Fear threshold:   < {fear_threshold}")
    print(f"   OnChain threshold: > {onchain_threshold}")
    print(f"   Hold period:      {hold_days} days")
    print()
    
    # Fetch data
    fg_df = fetch_fear_greed_history(data_days)
    price_df = fetch_btc_daily(data_days)
    
    if fg_df.empty or price_df.empty:
        return {'error': 'Insufficient data'}
    
    # Compute OnChain proxy
    print("🧬 Computing OnChain proxy (OBV Divergence + Volume Spike)...")
    price_df = compute_onchain_proxy(price_df)
    
    # Merge
    fg_df['date'] = fg_df['date'].dt.normalize()
    price_df['date'] = price_df['date'].dt.normalize()
    merged = pd.merge(fg_df, price_df, on='date', how='inner').sort_values('date').reset_index(drop=True)
    
    print(f"   📊 Merged: {len(merged)} days ({merged['date'].iloc[0].strftime('%Y-%m-%d')} → {merged['date'].iloc[-1].strftime('%Y-%m-%d')})")
    
    # =========================================================================
    # TEST 3 STRATEGIES
    # =========================================================================
    strategies = {
        'A: Fear Only': lambda r: r['fear_greed'] < fear_threshold,
        'B: OnChain Only': lambda r: r['onchain_proxy'] > onchain_threshold,
        'C: Fear + OnChain': lambda r: r['fear_greed'] < fear_threshold and r['onchain_proxy'] > onchain_threshold,
    }
    
    # Random baseline
    all_returns = []
    for i in range(len(merged) - hold_days):
        r = (merged.iloc[i + hold_days]['close'] / merged.iloc[i]['close'] - 1) * 100
        all_returns.append(r)
    random_avg = np.mean(all_returns)
    random_wr = sum(1 for r in all_returns if r > 0) / len(all_returns) * 100
    
    print(f"\n📉 Random Baseline ({hold_days}d): WR={random_wr:.1f}%, Avg={random_avg:+.1f}%")
    
    results = {}
    
    for name, condition in strategies.items():
        signals = []
        for i in range(len(merged) - hold_days):
            row = merged.iloc[i]
            if condition(row):
                entry = row['close']
                exit_p = merged.iloc[i + hold_days]['close']
                ret = (exit_p / entry - 1) * 100
                signals.append({
                    'date': row['date'],
                    'fear_greed': row['fear_greed'],
                    'onchain_proxy': round(row['onchain_proxy'], 1),
                    'entry': entry,
                    'exit': exit_p,
                    'return_pct': ret,
                    'win': ret > 0
                })
        
        if not signals:
            print(f"\n{'='*70}")
            print(f"📊 {name}: NO SIGNALS FOUND")
            results[name] = {'total': 0, 'win_rate': 0, 'avg_return': 0, 'p_value': 1.0}
            continue
        
        sdf = pd.DataFrame(signals)
        total = len(sdf)
        wins = int(sdf['win'].sum())
        losses = total - wins
        wr = wins / total * 100
        avg_ret = sdf['return_pct'].mean()
        med_ret = sdf['return_pct'].median()
        best = sdf['return_pct'].max()
        worst = sdf['return_pct'].min()
        
        p_val = stats.binomtest(wins, total, 0.5, alternative='greater').pvalue
        edge = avg_ret - random_avg
        
        print(f"\n{'='*70}")
        print(f"📊 {name}")
        print(f"{'='*70}")
        print(f"   Signals:     {total}")
        print(f"   Win Rate:    {wr:.1f}%  ({wins}W / {losses}L)")
        print(f"   Avg Return:  {avg_ret:+.1f}%")
        print(f"   Median:      {med_ret:+.1f}%")
        print(f"   Best/Worst:  {best:+.1f}% / {worst:+.1f}%")
        print(f"   p-value:     {p_val:.4f}")
        print(f"   Edge:        {edge:+.1f}% vs random")
        
        if p_val < 0.01:
            print(f"   ✅ SIGNIFICANT (p < 0.01)")
        elif p_val < 0.05:
            print(f"   ⚠️ Marginally significant (p < 0.05)")
        else:
            print(f"   ❌ NOT significant")
        
        print(f"\n   Trades:")
        for _, s in sdf.iterrows():
            e = "✅" if s['win'] else "❌"
            print(f"     {s['date'].strftime('%Y-%m-%d')} | F&G:{s['fear_greed']:3d} | "
                  f"OC:{s['onchain_proxy']:5.1f} | "
                  f"${s['entry']:,.0f}→${s['exit']:,.0f} | "
                  f"{s['return_pct']:+.1f}% {e}")
        
        results[name] = {
            'total': total,
            'wins': wins,
            'losses': losses,
            'win_rate': round(wr, 1),
            'avg_return': round(avg_ret, 1),
            'median_return': round(med_ret, 1),
            'p_value': round(p_val, 4),
            'edge': round(edge, 1),
            'signals': signals
        }
    
    # =========================================================================
    # COMPARISON TABLE
    # =========================================================================
    print(f"\n{'='*70}")
    print("📊 STRATEGY COMPARISON")
    print(f"{'='*70}")
    print(f"{'Strategy':<25} | {'Signals':>8} | {'Win Rate':>9} | {'Avg Ret':>8} | {'p-value':>8} | {'Edge':>6}")
    print("-" * 75)
    print(f"{'Random (any day)':<25} | {len(all_returns):>8} | {random_wr:>8.1f}% | {random_avg:>+7.1f}% | {'N/A':>8} | {'0.0%':>6}")
    
    for name, r in results.items():
        if r['total'] > 0:
            sig = "✅" if r['p_value'] < 0.05 else "❌"
            print(f"{name:<25} | {r['total']:>8} | {r['win_rate']:>8.1f}% | {r['avg_return']:>+7.1f}% | {r['p_value']:>7.4f} | {r['edge']:>+5.1f}% {sig}")
        else:
            print(f"{name:<25} | {'NONE':>8} | {'N/A':>9} | {'N/A':>8} | {'N/A':>8} | {'N/A':>6}")
    
    # Verdict
    print(f"\n{'='*70}")
    c = results.get('C: Fear + OnChain', {})
    if c.get('total', 0) == 0:
        print("🟡 VERDICT: Not enough combined signals to test the Elite v20 hypothesis")
        print("   Need more historical data (Glassnode/CryptoQuant Premium)")
    elif c.get('p_value', 1) < 0.05 and c.get('avg_return', 0) > 0:
        print("🟢 VERDICT: Fear + OnChain HAS a statistically validated edge!")
        print("   The Elite v20 Diffusion Layer ADDS value over Fear alone")
    elif c.get('win_rate', 0) > 60 and c.get('avg_return', 0) > 0:
        print("🟡 VERDICT: Promising but not statistically significant (need more data)")
    else:
        print("🔴 VERDICT: Fear + OnChain proxy does NOT show edge")
        print("   Consider: proxy may not capture true whale flows")
    print(f"{'='*70}")
    
    return results


if __name__ == '__main__':
    # Run the 3-way comparison
    results = run_backtest_v2(
        fear_threshold=15,
        onchain_threshold=70,
        hold_days=30
    )
