import requests, numpy as np
from scipy import stats

data = requests.get('https://api.binance.com/api/v3/klines', params={'symbol':'BTCUSDT','interval':'1d','limit':1000}).json()
closes = [float(d[4]) for d in data]
volumes = [float(d[5]) for d in data]

fg = requests.get('https://api.alternative.me/fng/?limit=1000&format=json').json()
fear_values = [int(x['value']) for x in fg['data']][::-1]

min_len = min(len(closes)-30, len(fear_values))
results = []

for i in range(20, min_len-30):
    fear_ok = fear_values[i] < 25
    ma20 = np.mean(closes[i-20:i])
    price_below_ma = closes[i] < ma20 * 0.92
    vol_spike = volumes[i] > np.mean(volumes[i-10:i]) * 1.5

    if fear_ok and price_below_ma and vol_spike:
        ret = (closes[i+30] - closes[i]) / closes[i]
        results.append(ret)

total = len(results)
if total > 0:
    wins = sum(1 for r in results if r > 0)
    pval = stats.binomtest(wins, total, p=0.5).pvalue
    print('Signals:', total)
    print('Win Rate:', round(wins/total*100,1), '%')
    print('Avg Return:', round(np.mean(results)*100,1), '%')
    print('p-value:', round(pval,4))
    print('Edge:', 'REAL p<0.05' if pval < 0.05 else 'RANDOM')
else:
    print('No signals')
