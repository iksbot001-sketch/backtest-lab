import json, numpy as np, pandas as pd
D='~/work/quant_us/data/'
def yh(t):
    j=json.load(open(D+f'yh_{t}.json'))['chart']['result'][0]
    q=j['indicators']['quote'][0]
    idx=pd.to_datetime(j['timestamp'],unit='s').normalize()
    df=pd.DataFrame({'open':q['open'],'high':q['high'],'low':q['low'],'close':q['close'],'volume':q['volume']},index=idx)
    ac=j['indicators'].get('adjclose')
    df['adj']=ac[0]['adjclose'] if ac else df['close']
    df=df.dropna(subset=['close']); df=df[~df.index.duplicated(keep='last')]
    # adjusted OHLC (total-return basis)
    k=df['adj']/df['close']
    for c in ['open','high','low']: df['a'+c]=df[c]*k
    return df
