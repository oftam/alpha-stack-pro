import requests, numpy as np
from scipy import stats

# 1. Fetch Price Data
data = requests.get('https://api.binance.com/api/v3/klines', params={'symbol':'BTCUSDT','interval':'1d','limit':1000}).json()
closes = [float(d[1]) for d in data]

# 2. Fetch Fear Data
fg = requests.get('https://api.alternative.me/fng/?limit=1000&format=json').json()
fear_values = [int(x['value']) for x in fg['data']][::-1]

# Align lengths
min_len = min(len(closes), len(fear_values))
closes = closes[-min_len:]
fear_values = fear_values[-min_len:]

results = []
signals_count = 0

# 3. The Logic: Consecutive Fear Days
CONSECUTIVE_DAYS = 5
FEAR_THRESHOLD = 15

for i in range(CONSECUTIVE_DAYS, len(closes)-30):
    # Check if past N days were ALL below threshold
    is_sustained_fear = all(f < FEAR_THRESHOLD for f in fear_values[i-CONSECUTIVE_DAYS:i])
    
    if is_sustained_fear:
        # Avoid overlapping signals (buy only once per cluster)
        # Check if yesterday was ALSO a signal (if so, we are already in)
        prev_sustained = all(f < FEAR_THRESHOLD for f in fear_values[i-CONSECUTIVE_DAYS-1:i-1])
        
        if not prev_sustained: # Only trigger on the FIRST day it hits 5 days
            entry = closes[i]
            exit_price = closes[i+30]
            ret = (exit_price - entry) / entry
            results.append(ret)
            signals_count += 1

total = len(results)
wins = sum(1 for r in results if r > 0)

print(f'\n--- RESULTS (Fear < {FEAR_THRESHOLD} for {CONSECUTIVE_DAYS}+ days) ---')
print(f'Signals Found: {total}')
if total > 0:
    print(f'Win Rate: {round(wins/total*100, 1)}%')
    print(f'Avg Return: {round(np.mean(results)*100, 1)}%')
    
    # Calculate p-value
    pval = stats.binomtest(wins, total, p=0.55).pvalue # Assuming 55% base win rate for BTC
    print(f'p-value: {round(pval, 4)}')
    print(f'Conclusion: {"EDGE FOUND" if pval < 0.05 else "NO EDGE / NOT ENOUGH DATA"}')
else:
    print('No signals matched criteria')
