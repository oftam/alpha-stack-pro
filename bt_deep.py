import requests, pandas as pd, numpy as np
from scipy import stats
from datetime import datetime

print('Fetching deep history...')
start = int(datetime(2017, 8, 1).timestamp() * 1000)
end = int(datetime.now().timestamp() * 1000)
klines = []
while start < end:
    d = requests.get('https://api.binance.com/api/v3/klines',
        params={'symbol':'BTCUSDT','interval':'1d','startTime':start,'limit':1000}).json()
    if not d: break
    klines.extend(d)
    start = int(d[-1][6]) + 1
    print(f'  Got {len(klines)} candles...', end='\r')

df = pd.DataFrame(klines)
closes = df[4].astype(float).values
dates = pd.to_datetime(df[0].astype(int), unit='ms').dt.date.values
print(f'\nCandles: {len(df)} | {dates[0]} to {dates[-1]}')

fg = requests.get('https://api.alternative.me/fng/?limit=0&format=json').json()
fg_dict = {datetime.fromtimestamp(int(x['timestamp'])).date(): int(x['value']) for x in fg['data']}
print(f'Fear days: {len(fg_dict)}')

fear_aligned, idx_aligned = [], []
for i, d in enumerate(dates):
    if d in fg_dict:
        fear_aligned.append(fg_dict[d])
        idx_aligned.append(i)

results, details = [], []
for i in range(5, len(idx_aligned)-30):
    w = fear_aligned[i-5:i]
    pw = fear_aligned[i-6:i-1]
    if all(f < 15 for f in w) and not all(f < 15 for f in pw):
        idx = idx_aligned[i]
        ret = (closes[min(idx+30, len(closes)-1)] - closes[idx]) / closes[idx]
        results.append(ret)
        details.append((dates[idx], closes[idx], ret))

total = len(results)
print(f'\n=== DEEP BACKTEST: Fear<15, 5 days consecutive ===')
print(f'Signals: {total}')
if total > 0:
    wins = sum(1 for r in results if r > 0)
    pval = stats.binomtest(wins, total, p=0.55, alternative='greater').pvalue
    print(f'Win Rate: {wins/total:.1%}')
    print(f'Avg Return: {np.mean(results):+.1%}')
    print(f'p-value: {pval:.4f}')
    print(f'Edge: {"REAL" if pval < 0.05 else "RANDOM"}')
    for d, p, r in details:
        print(f'  {d} | {p:,.0f} | {r:+.1%} {"✅" if r > 0 else "❌"}')
else:
    print('No signals in full history.')
