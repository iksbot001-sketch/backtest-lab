<!-- CODET · 모델 gemini-4-argon-medium · 대체 True · 1.3분 -->
```python
"""CAN SLIM 시험 사전 등록(CANSLIM_PREREG.md) 구현. 사용: python canslim.py
중소형주(ml_pred_M1fast_SURP_sm.parquet) 대상 S1 단독·글자 빼기·비용 2배 변형 및 S2 필터 평가."""
import sys, json, time, warnings
import numpy as np, pandas as pd
from pathlib import Path
from pxclean import clean
sys.path.insert(0, str(Path.home() / 'agent-fund/lib'))
from dist_report import summary, text
warnings.filterwarnings('ignore')

S = Path.home() / 'agent-fund-data'; OUT = S / 'canslim'; OUT.mkdir(exist_ok=True)
T = pd.read_parquet(S / 'ml_pred_M1fast_SURP_sm.parquet').sort_values(['tk', 'T']).reset_index(drop=True)
T['mom'] = T.mom.replace([np.inf, -np.inf], np.nan)

mk = pd.read_parquet(S / 'prices/eodhd/IWM.US.parquet'); mk['date'] = pd.to_datetime(mk.date); mk = mk.set_index('date').adjusted_close
cal = mk.index[mk.index >= '2005-01-01']

px = {}; hi_d = {}; vr_d = {}
for tk, g in T.groupby('tk'):
    p = S / f'prices/eodhd/{tk}.US.parquet'
    if not p.exists(): continue
    d = pd.read_parquet(p); d['date'] = pd.to_datetime(d.date); d = d.set_index('date')
    c = clean(d.adjusted_close)[0]; px[tk] = c
    c_cal = c.reindex(cal); v_cal = d.volume.reindex(cal)
    hi_s = (c_cal / c_cal.rolling(252, min_periods=200).max()).shift(1).values
    vr_s = (v_cal.rolling(20).mean() / v_cal.rolling(120).mean()).shift(1).values
    ie = g.i_fast.values.astype(int); ok = (ie >= 0) & (ie < len(cal))
    hi_d[tk] = np.where(ok, hi_s[np.clip(ie, 0, len(cal) - 1)], np.nan)
    vr_d[tk] = np.where(ok, vr_s[np.clip(ie, 0, len(cal) - 1)], np.nan)

px = pd.DataFrame(px).reindex(cal); px['MKT'] = mk.reindex(cal)
last = px.apply(lambda c: c.last_valid_index()); px = px.ffill()
for c, d in last.items():
    if d is not None and not pd.isna(d): px.loc[px.index > d, c] = np.nan
dates = px.index; N = len(px); col = {c: j for j, c in enumerate(px.columns)}; P = px.values
R = np.vstack([np.full(P.shape[1], np.nan), P[1:] / P[:-1] - 1]); mret = R[:, col['MKT']]; M = P[:, col['MKT']]
T = T[T.tk.isin(col)].reset_index(drop=True)

# 1) C·A·N·S·L·M 플래그 계산 (진입 전날 정보만 사용)
T['hi'] = np.concatenate([hi_d[tk] for tk, _ in T.groupby('tk', sort=False)])
T['vr'] = np.concatenate([vr_d[tk] for tk, _ in T.groupby('tk', sort=False)])

m_s = pd.Series(M, index=dates)
m_ok = (m_s > m_s.rolling(200, min_periods=180).mean()).shift(1).fillna(False).values
ie_all = T.i_fast.values.astype(int)
T['M'] = np.where((ie_all >= 0) & (ie_all < N), m_ok[np.clip(ie_all, 0, N - 1)], False)

cut_L = {tq: np.nanpercentile(g.mom, 80) for tq, g in T.groupby('tq') if g.mom.notna().sum() >= 50}
T['L'] = np.array([np.isfinite(v) and (t - 1) in cut_L and v >= cut_L[t - 1] for t, v in zip(T.tq, T.mom)], dtype=bool)
T['C'] = ((T.gR0 >= 0.22) & (T.acc0 > 0)).fillna(False).values
T['A'] = ((T.gR1 > 0) & (T.gR2 > 0) & (T.gR3 > 0) & (T[['gR0', 'gR1', 'gR2', 'gR3']].mean(axis=1, skipna=False) >= 0.22)).fillna(False).values
T['N'] = (T.hi >= 0.85).fillna(False).values
T['S'] = (T.vr >= 1.2).fillna(False).values

LETTERS = ['C', 'A', 'N', 'S', 'L', 'M']
T['ALL'] = T[LETTERS].all(axis=1)

# 5) 연도별 각 글자 통과 이벤트 수와 전체 통과 수 표 출력
T['year'] = T.tq // 4
T10 = T[T.year >= 2010]
yr_tbl = T10.groupby('year')[LETTERS + ['ALL']].sum()
yr_tbl['N_events'] = T10.groupby('year').size()
yr_tbl = yr_tbl[['N_events'] + LETTERS + ['ALL']]
yr_tbl.loc['Total'] = yr_tbl.sum()
print('=== 연도별 CAN SLIM 각 글자 및 전체 통과 이벤트 수 ===')
print(yr_tbl.to_string(), '\n', flush=True)

# 무작위 대조군용 분기별 유효 진입일(p0 >= 5) 사전 구축
valid_ie = {}
for tq, g in T10.groupby('tq'):
    ies = g.i_fast.values.astype(int)
    js = [col[tk] for tk in g.tk.values]
    ok_i = [i for i, j in zip(ies, js) if 0 <= i < N and np.isfinite(P[i, j]) and P[i, j] >= 5]
    if ok_i: valid_ie[tq] = (np.array(ok_i), np.array([j for i, j in zip(ies, js) if 0 <= i < N and np.isfinite(P[i, j]) and P[i, j] >= 5]))

def make_null(t, seed=0):
    rng = np.random.default_rng(seed); out = []
    for r in t.itertuples():
        if r.tq not in valid_ie: continue
        ies, js = valid_ie[r.tq]; idx = rng.integers(len(ies))
        i0, j = int(ies[idx]), int(js[idx]); i1 = min(i0 + int(r.d), N - 1)
        seg = P[i0:i1 + 1, j]; okp = np.where(np.isfinite(seg))[0]
        if not len(okp): continue
        i1 = i0 + int(okp[-1])
        out.append((P[i1, j] / P[i0, j] - 1) - (M[i1] / M[i0] - 1) - r.cost)
    return np.array(out)

# 2) 거래 루프 (refine.py run() 구조)
def run(letters=LETTERS, exit_mode='E1', H=252, cm=1.0, start=2010):
    ok = T[list(letters)].all(axis=1).values
    c_ok = T['C'].values; a_ok = T['A'].values
    tr = []
    for tk, idx in T.groupby('tk').indices.items():
        g = T.iloc[idx]; okg = ok[idx]; cg = c_ok[idx]; ag = a_ok[idx]
        ie = g.i_fast.values.astype(int); j = col[tk]; s = P[:, j]; k = 0
        while k < len(g):
            if not okg[k] or g.tq.values[k] // 4 < start: k += 1; continue
            i0 = ie[k]; p0 = s[i0] if i0 < N else np.nan
            if not np.isfinite(p0) or p0 < 5: k += 1; continue
            i1 = min(i0 + H, N - 1); kk = k + 1; why = 'max'
            while kk < len(g) and ie[kk] <= i1:
                if not (cg[kk] and ag[kk]): i1 = ie[kk]; why = 'CA'; break
                kk += 1
            seg = s[i0:i1 + 1]; okp = np.where(np.isfinite(seg))[0]; i1 = i0 + okp[-1]
            if i1 < min(i0 + H, N - 1) and why == 'max': why = 'delist'
            if exit_mode in ('E2', 'E3'):
                rel = s[i0:i1 + 1] / p0 - 1
                hit_sl = np.where(rel <= -0.08)[0]
                t_sl = hit_sl[0] if len(hit_sl) else H + 1
                t_tp = H + 1
                if exit_mode == 'E3':
                    hit_tp = np.where(rel >= 0.25)[0]
                    if len(hit_tp): t_tp = hit_tp[0]
                t_hit = min(t_sl, t_tp)
                if i0 + t_hit + 1 < i1:
                    i1 = i0 + t_hit + 1
                    why = 'stop' if t_sl <= t_tp else 'tp'
                while i1 > i0 and not np.isfinite(s[i1]): i1 -= 1
            p1 = s[i1]; rs, rm = p1 / p0 - 1, M[i1] / M[i0] - 1
            cost = cm * 2 * (0.001 if g.liq.values[k] == 'H' else 0.003)
            r = g.iloc[k]
            tr.append(dict(tk=tk, tq=r.tq, i0=i0, i1=i1, d=i1 - i0, why=why, rs=rs, rm=rm, cost=cost, ex=rs - rm - cost,
                           px=p0, dvol=r.get('dvol', np.nan), vol63=r.vol63, mom=r.mom, ear=r.ear, gR0=r.gR0, acc0=r.acc0, sur0=r.sur0, gvol8=r.gvol8, n_an=r.n_an, liq=r.get('liq', '')))
            while kk < len(g) and ie[kk] <= i1: kk += 1
            k = max(kk, k + 1)
    return pd.DataFrame(tr)

def calendar(t, w=False):
    num = np.zeros(N); den = np.zeros(N)
    for r in t.itertuples():
        a, b = r.i0 + 1, r.i1 + 1; j = col[r.tk]
        if a >= N: continue
        ww = 1 / max(r.vol63, 0.005) if w else 1.0
        x = np.nan_to_num(R[a:b, j]); num[a:b] += ww * x; den[a:b] += ww; num[a] -= ww * r.cost
    live = den > 0
    if not live.any():
        return dict(ann=np.nan, ir=np.nan, tcal=np.nan, mdd=np.nan, ann_pre=np.nan, t_pre=np.nan, ann_post=np.nan, t_post=np.nan, npos=0.0), pd.Series(dtype=float), pd.Series(dtype=float)
    ex = np.where(live, num / np.where(live, den, 1) - np.nan_to_num(mret), 0.0)
    first = np.argmax(live); ex = ex[first:]; dd = dates[first:]
    cum = np.cumprod(1 + ex); mdd = (cum / np.maximum.accumulate(cum) - 1).min()
    yr = pd.Series(ex, index=dd).groupby(dd.year).apply(lambda s: np.prod(1 + s) - 1)
    sub = lambda m: (ex[m].mean() * 252, ex[m].mean() / ex[m].std() * np.sqrt(m.sum())) if m.sum() > 2 and ex[m].std() > 0 else (np.nan, np.nan)
    a1, t1 = sub(dd.year < 2019); a2, t2 = sub(dd.year >= 2019)
    return dict(ann=ex.mean() * 252, ir=ex.mean() / ex.std() * np.sqrt(252), tcal=ex.mean() / ex.std() * np.sqrt(len(ex)), mdd=mdd,
                ann_pre=a1, t_pre=t1, ann_post=a2, t_post=t2, npos=den[first:][live[first:]].mean() if not w else np.nan), pd.Series(ex, index=dd), yr

tt = lambda s: s.mean() / s.std(ddof=1) * np.sqrt(len(s)) if len(s) > 2 else np.nan
def summ(t):
    if len(t) == 0:
        return dict(n=0, hold=np.nan, mean=np.nan, med=np.nan, win=np.nan, t_trade=np.nan, top10=np.nan, skew=np.nan, kurt=np.nan, stop=np.nan)
    q = t.groupby('tq').ex.mean(); top = t.ex.sort_values(ascending=False)
    return dict(n=len(t), hold=round(t.d.mean()), mean=t.ex.mean(), med=t.ex.median(), win=(t.ex > 0).mean(), t_trade=tt(q),
                top10=top.head(10).sum() / t.ex.sum() if t.ex.sum() > 0 else np.nan, skew=t.ex.skew(), kurt=t.ex.kurt(), stop=(t.why == 'stop').mean())

# 3) S1 변형 실행·저장·기록
VAR = [
    ('S1_E1', dict(letters=LETTERS, exit_mode='E1')),
    ('S1_E2', dict(letters=LETTERS, exit_mode='E2')),
    ('S1_E3', dict(letters=LETTERS, exit_mode='E3')),
    ('noC', dict(letters=[x for x in LETTERS if x != 'C'], exit_mode='E1')),
    ('noA', dict(letters=[x for x in LETTERS if x != 'A'], exit_mode='E1')),
    ('noN', dict(letters=[x for x in LETTERS if x != 'N'], exit_mode='E1')),
    ('noS', dict(letters=[x for x in LETTERS if x != 'S'], exit_mode='E1')),
    ('noL', dict(letters=[x for x in LETTERS if x != 'L'], exit_mode='E1')),
    ('noM', dict(letters=[x for x in LETTERS if x != 'M'], exit_mode='E1')),
    ('S1_E1_x2', dict(letters=LETTERS, exit_mode='E1', cm=2.0)),
]

rows = []; series = {}; reg_trials = []
print('=== S1 변형별 백테스트 및 분포 요약 ===')
for v, kw in VAR:
    t = run(**kw); t.to_parquet(OUT / f'tr_{v}.parquet', index=False)
    c, ser, yr = calendar(t); series[v] = ser
    row = dict(v=v, **summ(t), **c); rows.append(row); reg_trials.append((v, row))
    print(v, 'n', len(t), 'mean %.2f%%' % (t.ex.mean() * 100), 'ann %.1f%% IR %.2f t %.2f' % (c['ann'] * 100, c['ir'], c['tcal']), flush=True)
    if len(t):
        s_dist = summary(t.ex, groups=t.tq, null=make_null(t))
        print(text(s_dist, name=v), '\n', flush=True)

r_df = pd.DataFrame(rows); r_df.to_csv(OUT / 'canslim.csv', index=False); pd.DataFrame(series).to_parquet(OUT / 'cal_canslim.parquet')
pd.set_option('display.width', 250); fm = r_df.copy()
for c in ['mean', 'med', 'win', 'top10', 'ann', 'mdd', 'ann_pre', 'ann_post', 'stop']: fm[c] = (fm[c] * 100).round(1)
for c in ['t_trade', 'skew', 'kurt', 'ir', 'tcal', 't_pre', 't_post', 'npos']: fm[c] = fm[c].round(2)
print('=== S1 요약 표 ===')
print(fm.to_string(index=False), '\n', flush=True)

# 4) S2 필터: 기존 거래(tr_sm_acc0_V0, tr_sm_p_ridge_V0) 중 S1 통과 vs 나머지 비교
s1_keys = set(zip(T.loc[T.ALL, 'tk'], T.loc[T.ALL, 'i_fast'].astype(int)))
print('=== S2 기존 거래 S1 필터 비교 ===')
for name in ['tr_sm_acc0_V0', 'tr_sm_p_ridge_V0']:
    tr_b = pd.read_parquet(S / 'refine' / f'{name}.parquet')
    is_s1 = np.array([(tk, int(i0)) in s1_keys for tk, i0 in zip(tr_b.tk, tr_b.i0)], dtype=bool)
    t_pass = tr_b[is_s1].reset_index(drop=True); t_rest = tr_b[~is_s1].reset_index(drop=True)
    for sub_nm, sub_t in [(f'{name}_S1_pass', t_pass), (f'{name}_S1_rest', t_rest)]:
        if len(sub_t):
            s_sub = summary(sub_t.ex, groups=sub_t.tq, null=make_null(sub_t))
            print(text(s_sub, name=sub_nm), flush=True)
        else:
            print(f'[{sub_nm}] n=0', flush=True)
    c_p, _, _ = calendar(t_pass) if len(t_pass) else (dict(ann=np.nan, ir=np.nan, tcal=np.nan, mdd=np.nan), None, None)
    reg_trials.append((f'S2_{name}', dict(v=f'S2_{name}', **summ(t_pass), **c_p, n_rest=len(t_rest), mean_rest=float(t_rest.ex.mean()) if len(t_rest) else np.nan)))
    print()

with open(Path.home() / 'agent-fund' / 'data' / 'trial_registry.jsonl', 'a') as f:
    for v_nm, x in reg_trials:
        f.write(json.dumps({'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), 'study': 'gamma_backtest', 'trial': f'CANSLIM_{v_nm}',
                            **{k: (round(float(val), 4) if isinstance(val, (float, np.floating)) else (int(val) if isinstance(val, np.integer) else val)) for k, val in x.items()}}, ensure_ascii=False) + '\n')
```

- **구현 요약**: `CANSLIM_PREREG.md`의 사전 등록 명세와 `refine.py`·`wfeat.py`·`dist_report.py` 구조를 그대로 따라 작성했습니다.
- **시점 및 특징(1)**: 가격(`clean()`)과 거래량을 `IWM` 달력(2005~)에 맞추고, `hi`(252일 최고가 대비, `min_periods=200`)·`vr`(20일/120일 평균 거래량)·`M`(IWM > 200일선) 모두 `.shift(1)`로 `i_fast` 전날 값만 참조합니다. `L`은 직전 분기(`tq-1`) `mom` 80분위 컷을 적용했습니다.
- **청산·변형·S2(2~5)**: 종목별 비중복 루프에서 다음 발표 시점 `C` 또는 `A` 미달 시 `i_fast` 청산(E1), −8% 종가 다음 날 손절(E2), +25% 종가 다음 날 익절(E3)을 구현하고, S1 10개 변형과 S2 2개 필터 비교를 수행해 `canslim.csv`, 거래 파케이, `trial_registry.jsonl`(총 12건)에 기록합니다.
