"""미국 S1(s1_exit_kr.py를 미국용으로 바꾼 것): 가속도 상위 10분위 진입 후 청산 규칙 비교 (롱온리, 비용 반영, 동일가중 포트폴리오).
규칙: F21/F63/F126/F252 = 고정 보유(거래일) / A = 다음 공시 가속도 ≤0 청산 / B = 가속도 2회 연속 하락 청산 / D = 가속도 ≤0 이면서 순위 상위 30% 밖.
모든 변형은 최대 252거래일 보유, 진입 = 공시 후 2번째 거래일 종가, 청산 = 해당 공시 후 2번째 거래일 종가(고정 보유는 N일 뒤).
비용: 수수료 0.015%/편도 + 1틱 슬리피지/편도 + 매도 거래세(기본 0.20%, 민감도 0.30%; 세율은 연도별로 다르며 기억 기반 가정이라 확인 필요).
사용: python s1_exit_kr.py a_op [tax=0.0020]"""
import sys, glob, json, time
import numpy as np, pandas as pd
from pathlib import Path
S = Path.home() / 'agent-fund-data'
sig = sys.argv[1] if len(sys.argv) > 1 else 'eap'
basis = sys.argv[4] if len(sys.argv) > 4 else 'filed'
TAX = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
NOCOST = len(sys.argv) > 3 and sys.argv[3] == 'nocost'
FEE = 0 if NOCOST else 0.00015
E = pd.read_parquet(S / f'events_us_{sig}_{basis}.parquet').sort_values(['stock_code', 'tq']).reset_index(drop=True)
E['filed'] = E['filed_entry']
E = E[E.stock_code.notna()]
px = {}
for f in glob.glob(str(S / 'prices' / 'us' / '*.parquet')):
    d = pd.read_parquet(f, columns=['date', 'close']); d = d[d.close > 0]
    if len(d): px[Path(f).stem] = d.set_index('date').close
px = pd.DataFrame(px).sort_index(); px.index = pd.to_datetime(px.index); px = px[px.index >= '2008-01-01']
# 거래정지 등으로 가격이 비는 날은 직전 가격을 이월(재개일에 한꺼번에 반영). 마지막 거래일 이후(상폐)는 비워 둔다.
_last = px.apply(lambda c: c.last_valid_index()); px = px.ffill()
for _c, _d in _last.items():
    if _d is not None and not pd.isna(_d): px.loc[px.index > _d, _c] = np.nan
cal = px.index; codes = {c: i for i, c in enumerate(px.columns)}
V = px.values; ret = np.vstack([np.full((1, V.shape[1]), np.nan), V[1:] / V[:-1] - 1])
univ = [c for c in E.stock_code.unique() if c in codes]
mk = np.nan_to_num(ret[:, codes['SPY']])   # 시장 = SPY(시가총액가중)
MAXH = 252
def tick(p):
    return 0.01
def _tick_kr(p):
    return 1 if p < 2000 else 5 if p < 5000 else 10 if p < 20000 else 50 if p < 50000 else 100 if p < 200000 else 500 if p < 500000 else 1000
def last_valid(c, i0, i1):
    col = V[i0:i1 + 1, c]; ok = np.where(np.isfinite(col))[0]
    return i0 + ok[-1] if len(ok) else i0
def run(rule):
    trades = []
    for code, g in E.groupby('stock_code'):
        if code not in codes: continue
        c = codes[code]; g = g.reset_index(drop=True); busy_until = -1
        for k in range(len(g)):
            r = g.iloc[k]
            if r.dec != 10 or not np.isfinite(r[sig]): continue
            i0 = cal.searchsorted(r.filed) + 2
            if i0 >= len(cal) or i0 <= busy_until: continue
            p0 = V[i0, c]
            if not np.isfinite(p0) or p0 < 5: continue
            iend = min(i0 + MAXH, len(cal) - 1)
            if rule.startswith('F'): ix = min(i0 + int(rule[1:]), len(cal) - 1)
            else:
                ix = iend
                a_hist = [r[sig]]
                for kk in range(k + 1, len(g)):
                    n = g.iloc[kk]
                    if n.tq != g.iloc[kk - 1].tq + 1: continue
                    j = cal.searchsorted(n.filed) + 2
                    if j > iend: break
                    a_hist.append(n[sig]); hit = False
                    if rule == 'A': hit = n[sig] <= 0
                    elif rule == 'D': hit = n[sig] <= 0 and n.dec <= 7
                    elif rule == 'B': hit = len(a_hist) >= 3 and a_hist[-1] < a_hist[-2] < a_hist[-3]
                    if hit: ix = j; break
            ix = min(ix, len(cal) - 1)
            ix = last_valid(c, i0, ix)                      # 상장폐지 등으로 가격이 끊기면 마지막 가격에서 청산
            p1 = V[ix, c]
            if ix <= i0 or not np.isfinite(p1): continue
            cb = FEE + (0 if NOCOST else tick(p0) / p0); cs = FEE + (0 if NOCOST else tick(p1) / p1 + TAX)
            trades.append((code, c, i0, ix, p1 / p0 - 1, cb + cs, cm_ratio(i0, ix)))
            busy_until = ix
    return pd.DataFrame(trades, columns=['code', 'c', 'i0', 'i1', 'gross', 'cost', 'mkt'])
cm = np.cumprod(1 + mk)
def cm_ratio(i0, i1): return cm[i1] / cm[i0] - 1
def portfolio(T):
    n = len(cal); s = np.zeros(n); cnt = np.zeros(n)
    for c, i0, i1, cost in zip(T.c, T.i0, T.i1, T.cost):
        seg = np.nan_to_num(ret[i0 + 1:i1 + 1, c]); s[i0 + 1:i1 + 1] += seg; cnt[i0 + 1:i1 + 1] += 1; s[i1] -= cost
    r = np.where(cnt > 0, s / np.maximum(cnt, 1), 0.0)
    return pd.Series(r, index=cal), pd.Series(cnt, index=cal)
def stats(r, cnt, m, lo, hi):
    mask = (r.index >= lo) & (r.index < hi) & (cnt.values > 0)
    x = r[mask]; mm = pd.Series(m, index=cal)[mask]
    if len(x) < 60: return None
    yrs = len(x) / 252
    eq = (1 + x).prod(); eqm = (1 + mm).prod()
    mdd = ((1 + x).cumprod() / (1 + x).cumprod().cummax() - 1).min()
    ex = x - mm
    beta = np.cov(x, mm)[0, 1] / np.var(mm, ddof=1)
    return dict(CAGR=eq ** (1 / yrs) - 1, mktCAGR=eqm ** (1 / yrs) - 1, vol=x.std() * np.sqrt(252), sharpe=x.mean() / x.std() * np.sqrt(252),
                MDD=mdd, exCAGR=eq ** (1 / yrs) - eqm ** (1 / yrs), beta=beta, te_t=ex.mean() / ex.std(ddof=1) * np.sqrt(len(ex)), days=len(x), avgN=0)
rows = []; reg = []
for rule in ['F21', 'F63', 'F126', 'F252', 'A', 'B', 'D']:
    T = run(rule); r, cnt = portfolio(T)
    T['net'] = T.gross - T.cost; T['ex'] = T.net - T.mkt; hold = (T.i1 - T.i0)
    T.assign(date0=cal[T.i0.values], date1=cal[T.i1.values]).to_parquet(S / f'trades_us_{sig}_{basis}_{rule}{"_nocost" if NOCOST else ""}.parquet', index=False)
    msk_ = cnt.values > 0; dx = (r - pd.Series(mk, index=cal))[msk_]
    print(rule, '일평균 초과(연환산 산술) %.2f%%' % (dx.mean() * 252 * 100), '| 거래 단순평균 초과/거래 %.2f%% | 일수가중 %.2f%%' % (T.ex.mean() * 100, np.average(T.ex, weights=T.i1 - T.i0) * 100), flush=True)
    for lab, lo, hi in (('전체', '2009-01-01', '2100-01-01'), ('IS 2009-17', '2009-01-01', '2018-01-01'), ('OOS 2018-', '2018-01-01', '2100-01-01')):
        s = stats(r, cnt, mk, lo, hi)
        if s:
            msk = (T.i0 >= cal.searchsorted(pd.Timestamp(lo))) & (T.i0 < cal.searchsorted(pd.Timestamp(hi)) if hi != '2100-01-01' else True)
            Tm = T[msk]
            rows.append(dict(rule=rule, period=lab, trades=len(Tm), avg_hold=round(float((Tm.i1 - Tm.i0).mean()), 0), avgN=round(float(cnt[(cnt.index >= lo) & (cnt.index < hi) & (cnt > 0)].mean()), 0),
                             win_ex=round(float((Tm.ex > 0).mean()), 3), net_ex_trade=round(float(Tm.ex.mean()) * 100, 2), cost_pct=round(float(Tm.cost.mean()) * 100, 2), **{k: round(v, 3) for k, v in s.items() if k != 'avgN'}))
    reg.append({'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), 'run': 'gamma_backtest', 'name': f'US S1 exit {basis} {sig} {rule} tax{TAX}{" nocost" if NOCOST else ""}', 'params': {'sig': sig, 'rule': rule, 'tax': TAX}, 'sharpe': rows[-3]['sharpe'] if len(rows) >= 3 else None})
R = pd.DataFrame(rows)
pd.set_option('display.width', 250)
print(f'== {sig}, 거래세 {TAX*100:.2f}%')
print(R.to_string(index=False))
R.to_csv(S / f'exit_results_us_{sig}_{basis}_{int(TAX*10000)}{"_nocost" if NOCOST else ""}.csv', index=False)
with open(Path.home() / 'agent-fund' / 'data' / 'trial_registry.jsonl', 'a') as f:
    for x in reg: f.write(json.dumps(x, ensure_ascii=False) + '\n')
