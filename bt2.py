# זה הבדיקה עם Fear בלבד (נתון שיש לנו)
import requests, numpy as np
from scipy import stats

data = requests.get('https://api.binance.com/api/v3/klines', params={'symbol':'BTCUSDT','interval':'1d','limit':500}).json()
closes = [float(d[4]) for d in data]

# Fear & Greed היסטורי
fg = requests.get('https://api.alternative.me/fng/?limit=500&format=json').json()
fear_values = [int(x['value']) for x in fg['data']][::-1]

min_len = min(len(closes)-30, len(fear_values))
results = []
for i in range(30, min_len):
    if fear_values[i] < 15:
        results.append((closes[i+30] - closes[i]) / closes[i])

total = len(results)
wins = sum(1 for r in results if r > 0)
pval = stats.binomtest(wins, total, p=0.5).pvalue
print('Signals:', total)
print('Win Rate:', round(wins/total*100, 1))
print('Avg Return:', round(np.mean(results)*100, 1))
print('p-value:', round(pval, 4))
print('Edge:', 'REAL' if pval < 0.05 else 'RANDOM')
