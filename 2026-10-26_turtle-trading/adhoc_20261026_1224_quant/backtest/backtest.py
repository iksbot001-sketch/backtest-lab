"""터틀 트레이딩 장기 전략(System 2: 55일 돌파 진입·20일 저가 청산·2N 손절) — KODEX200·KODEX코스닥150, 지수 대용 1990~2026
대표 지시 2026-10-26 (research/turtle_review_20261026/BRIEF.md). 원문 파라미터 고정(55/20/2N, N=20일 Wilder ATR).

체결 모델 — fund.run 으로 표현 불가한 부분이 있어 직접 계산한다(근거):
  (a) 다음 날 시가 체결: t 종가로 신호(종가 > 직전 55일 최고가 / 종가 < 직전 20일 최저가 / 종가 < 손절가) → t+1 시가 체결.
      fund.run 과 같은 시점 구조지만, fund.run 의 한국 비용은 주식 호가단위(kr_tick: 10k~50k KRW 10원, 50,000 KRW↑ 50원)를 써서
      ETF 호가(5원)보다 비용이 3~10배 크다. 지시서 비용(ETF 편도 0.015%+5원, 지수 대용 구간 편도 0.05%)을 쓰려고 직접 계산했다.
      교차검증으로 fund.run 결과도 함께 보고(cross_check).
  (b) 장중 돌파 체결: 고가가 직전 55일 최고가를 넘으면 그날 max(돌파가, 시가)에 매수(갭 상승이면 시가).
      보유 중 저가가 max(직전 20일 최저가, 손절가) 이하면 그날 min(그 가격, 시가)에 매도(갭 하락이면 시가).
      진입 당일 저가가 손절가 이하면 당일 손절로 본다(보수적, 봉 안의 순서를 모름). 청산한 날은 재진입하지 않는다.
  비용(편도): ETF 구간 = 수수료 0.015% + 1틱(5원)/체결가, 지수 대용 구간 = 0.05%(수수료+슬리피지 상당, 지시서 가정). cost_mult 배.
  N = 20일 TR 의 Wilder 평균(ewm alpha=1/20). 진입 신호 시점에 이미 확정된 N 을 고정((a) t일 N, (b) t-1일 N).
  채널: 직전 55일 고가 최고 = high.rolling(55).max().shift(1), 직전 20일 저가 최저 = low.rolling(20).min().shift(1) (오늘 제외).

데이터: data/nv_*.txt (네이버 siseJson, 2026-10-26 수집), 229200 은 ~/vol-harvest-daily/data/229200_D.csv(대신증권, OHLC 일관).
  KODEX200 대용 = KOSPI 종합지수(1990-01-04~2002-10-11) × 비율 → 069500(2002-10-14~). 코스닥150 대용 = KOSDAQ 종합(1997-01-03~2015-09-30) × 비율 → 229200(2015-10-01~).
  1996년 KOSDAQ 은 138일이 O=H=L=C(고저 없음)라 ATR 이 왜곡 → 1997-01-03부터 사용. 2007-03-02 지수 시가 0 등 OHLC 모순 6일은 H=max, L=min 으로 보정.
  지수 대용 구간은 분배금 미반영. 069500 가격의 분배금 반영 여부는 KPI200 과 비교해 보고서에 기록.

실행: venv/bin/python backtest.py [all|base|sens|validate|vh|report]
"""
import sys, re, json, math, time, argparse
from pathlib import Path
sys.path.insert(0, '~/agent-fund/lib')
import fund, validate
import numpy as np, pandas as pd

OUT = Path(__file__).resolve().parent
RUN = OUT.parent
DATA = RUN / 'data'
END = '2026-10-23'
FEE = 0.00015; TICK = 5.0; PROXY_COST = 0.0005
SPLICE = {'K200': '2002-10-14', 'KQ150': '2015-10-01'}
START = {'K200': '1990-01-04', 'KQ150': '1997-01-03'}
SUBS = {'K200': [('1990-01-04', '2002-10-11'), ('2002-10-14', '2015-09-30'), ('2015-10-01', END)],
        'KQ150': [('1997-01-03', '2002-10-11'), ('2002-10-14', '2015-09-30'), ('2015-10-01', END)]}
BASE = dict(entry=55, exit=20, stop_n=2.0, atr_n=20)
LOG = []


# ================================================================ 데이터
def _nv(s):
    rows = re.findall(r'\["(\d{8})",\s*([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*(\d+)', (DATA / f'nv_{s}.txt').read_text())
    df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close', 'volume']); df['date'] = pd.to_datetime(df['date'])
    return df.set_index('date').astype(float)


def _clean(d):
    d = d[(d.index <= END)].copy()
    z = d['open'] <= 0
    d.loc[z, ['open', 'high', 'low']] = np.nan
    for c in ('open', 'high', 'low'): d[c] = d[c].fillna(d['close'])
    d['high'] = d[['open', 'high', 'low', 'close']].max(axis=1); d['low'] = d[['open', 'high', 'low', 'close']].min(axis=1)
    return d


def _px(d, market='KR'):
    d = d.copy(); d['adj'] = d['close']
    for c in ('open', 'high', 'low'): d['a' + c] = d[c]
    d.attrs['market'] = market
    return d


def load():
    kospi, kpi200, e200, kosdaq = (_clean(_nv(s)) for s in ('KOSPI', 'KPI200', '069500', 'KOSDAQ'))
    m = pd.read_csv('~/vol-harvest-daily/data/229200_D.csv'); m['date'] = pd.to_datetime(m['date'].astype(str))
    e150 = _clean(m.set_index('date')[['open', 'high', 'low', 'close', 'volume']].astype(float))
    out = {}
    for name, idx, etf, s0 in (('K200', kospi, e200, START['K200']), ('KQ150', kosdaq, e150, START['KQ150'])):
        sp = pd.Timestamp(SPLICE[name]); ratio = etf['close'].loc[sp] / idx['close'].loc[sp]
        pre = idx[(idx.index >= s0) & (idx.index < sp)][['open', 'high', 'low', 'close']] * ratio
        pre['volume'] = np.nan; pre['proxy'] = 1.0
        post = etf[etf.index >= sp].copy(); post['proxy'] = 0.0
        S = pd.concat([pre, post]); S.attrs['ratio'] = float(ratio)
        out[name] = _px(S)
    out['raw'] = dict(KOSPI=kospi, KPI200=kpi200, E200=e200, KOSDAQ=kosdaq, E150=e150)
    out['KQidx'] = _px(kosdaq.drop(columns=['volume']))       # 변동성 수확 신호 A 용 코스닥 지수
    return out


# ================================================================ 터틀 엔진
def turtle(px, p=BASE, cost_mult=1.0, mode='a', sizing='full', cash_rate=0.0, start=None):
    d = px; i_start = 0 if start is None else int(np.searchsorted(px.index.values, np.datetime64(pd.Timestamp(start))))   # 지표는 전체 이력, 매매는 start 부터
    O, H, L, C = (d[k].values.astype(float) for k in ('open', 'high', 'low', 'close'))
    prox = d['proxy'].values if 'proxy' in d else np.zeros(len(d))
    hs, ls, cs = pd.Series(H), pd.Series(L), pd.Series(C)
    ch_in = hs.rolling(int(p['entry'])).max().shift(1).values
    ch_out = ls.rolling(int(p['exit'])).min().shift(1).values
    tr = pd.concat([hs - ls, (hs - cs.shift()).abs(), (ls - cs.shift()).abs()], axis=1).max(axis=1)
    N = tr.ewm(alpha=1 / p['atr_n'], adjust=False).mean().values
    idx = d.index; n = len(d)
    gap = np.r_[0, (idx[1:] - idx[:-1]).days]

    def rate(t, price):
        return cost_mult * (PROXY_COST if prox[t] else FEE + TICK / price)

    cash = 1.0; sh = 0.0; eq = np.empty(n); held = np.zeros(n, bool); turn = np.zeros(n)
    trades = []; cur = None; pend = None                    # pend = ('buy', N) | ('sell', reason)
    for t in range(n):
        if t < i_start:
            eq[t] = 1.0; continue
        if cash_rate and t > i_start: cash *= (1 + cash_rate) ** (gap[t] / 365)
        exited = False
        if mode == 'a' and pend is not None:
            if pend[0] == 'buy':
                px_ = O[t]; rt = rate(t, px_); e0 = cash + sh * px_
                frac = 1.0 if sizing == 'full' else min(1.0, 0.01 / (pend[1] / px_))   # 원전 사이징: 1N 움직임 = 포트폴리오 1%
                inv = e0 * frac; sh = inv / (px_ * (1 + rt)); cash -= inv; turn[t] += frac
                cur = dict(entry_date=idx[t], entry_px=px_, entry_eff=px_ * (1 + rt), N=pend[1], stop=px_ - p['stop_n'] * pend[1], frac=frac, i0=t)
            else:
                px_ = O[t]; rt = rate(t, px_); e_pre = cash + sh * px_
                cash += sh * px_ * (1 - rt); turn[t] += sh * px_ / e_pre
                cur.update(exit_date=idx[t], exit_px=px_, exit_eff=px_ * (1 - rt), reason=pend[1], i1=t); trades.append(cur); cur = None; sh = 0.0
                exited = True
            pend = None
        if mode == 'b':
            if cur is not None and t > cur['i0']:
                lvl = max(ch_out[t], cur['stop']) if not np.isnan(ch_out[t]) else cur['stop']
                if L[t] <= lvl:
                    px_ = min(lvl, O[t]); rt = rate(t, px_); e_pre = cash + sh * O[t]
                    cash += sh * px_ * (1 - rt); turn[t] += sh * px_ / max(e_pre, 1e-12)
                    cur.update(exit_date=idx[t], exit_px=px_, exit_eff=px_ * (1 - rt), reason='stop' if cur['stop'] >= (ch_out[t] if not np.isnan(ch_out[t]) else -1) else 'low20', i1=t)
                    trades.append(cur); cur = None; sh = 0.0; exited = True
            if cur is None and not exited and t >= max(1, i_start) and not np.isnan(ch_in[t]) and H[t] > ch_in[t]:
                px_ = max(ch_in[t], O[t]); Ne = N[t - 1]; rt = rate(t, px_); e0 = cash
                frac = 1.0 if sizing == 'full' else min(1.0, 0.01 / (Ne / px_))
                inv = e0 * frac; sh = inv / (px_ * (1 + rt)); cash -= inv; turn[t] += frac
                cur = dict(entry_date=idx[t], entry_px=px_, entry_eff=px_ * (1 + rt), N=Ne, stop=px_ - p['stop_n'] * Ne, frac=frac, i0=t)
                if L[t] <= cur['stop']:                              # 진입 당일 손절(보수적)
                    sp = cur['stop']; rt = rate(t, sp); cash += sh * sp * (1 - rt); turn[t] += frac
                    cur.update(exit_date=idx[t], exit_px=sp, exit_eff=sp * (1 - rt), reason='stop_same_day', i1=t); trades.append(cur); cur = None; sh = 0.0
        eq[t] = cash + sh * C[t]; held[t] = sh > 0
        if mode == 'a':                                              # t 종가로 다음 날 주문 결정
            if cur is not None:
                if C[t] < cur['stop']: pend = ('sell', 'stop')
                elif not np.isnan(ch_out[t]) and C[t] < ch_out[t]: pend = ('sell', 'low20')
            elif not np.isnan(ch_in[t]) and C[t] > ch_in[t]:
                pend = ('buy', N[t])
    if cur is not None:
        cur.update(exit_date=idx[-1], exit_px=C[-1], exit_eff=C[-1] * (1 - rate(n - 1, C[-1])), reason='open_at_end', i1=n - 1); trades.append(cur)
    sl = slice(i_start, None)
    e = pd.Series(eq, index=idx)[sl]; r = e.pct_change(); r.iloc[0] = e.iloc[0] - 1
    return dict(r=r, eq=e, held=pd.Series(held, index=idx).astype(float)[sl], turnover=pd.Series(turn, index=idx)[sl], trades=trades, mode=mode)


def strategy_factory(mode):
    def strategy(params, px, cost_mult=1.0):
        """validate.run_all 용. px={'X': 이어붙인 일봉}. (a) 보유(종가 기준)는 전일까지 정보로 결정 → 그대로.
        (b) 는 장중 체결이라 그날 데이터로 바뀌므로 pos = 전일 마감 보유(그날 아침 보유)로 넘긴다(누설 검사 정의와 맞춤)."""
        k = next(iter(px)); s = turtle(px[k], params, cost_mult, mode, start=params.get('start'))
        pos = s['held'] if mode == 'a' else s['held'].shift(1).fillna(0.0)
        return s['r'], pos, s['turnover']
    return strategy


# ================================================================ 지표
_BH = {}


def bh(name, data, start=None):
    key = (name, start)
    if key not in _BH:
        px = data[name]; W = pd.DataFrame(1.0, index=px.index, columns=[name])
        _BH[key] = fund.run({name: px}, W, start=start or START[name])[0]
    return _BH[key]


def dd_info(r):
    e = (1 + r.fillna(0)).cumprod(); peak = e.cummax(); dd = e / peak - 1
    t1 = dd.idxmin(); t0 = e.loc[:t1].idxmax()
    rec = e.loc[t1:][e.loc[t1:] >= peak.loc[t1]]
    t2 = rec.index[0] if len(rec) else None
    return dict(mdd=float(dd.min()), peak=str(t0.date()), trough=str(t1.date()), recovered=str(t2.date()) if t2 is not None else '미회복',
                recovery_days=int((t2 - t1).days) if t2 is not None else None,
                recovery_tdays=int(len(e.loc[t1:t2]) - 1) if t2 is not None else None,
                underwater_days=int((t2 - t0).days) if t2 is not None else int((e.index[-1] - t0).days))


def trade_stats(trades, a=None, b=None):
    T = [x for x in trades if (a is None or x['entry_date'] >= pd.Timestamp(a)) and (b is None or x['entry_date'] <= pd.Timestamp(b))]
    if not T: return dict(n=0)
    ret = np.array([x['exit_eff'] / x['entry_eff'] - 1 for x in T])
    R = np.array([(x['exit_eff'] - x['entry_eff']) / (2 * x['N']) for x in T])        # R = 2N (진입 시 손절폭)
    hold = np.array([x['i1'] - x['i0'] for x in T])
    w, l = ret[ret > 0], ret[ret <= 0]
    streak = mx = 0
    for v in ret:
        streak = streak + 1 if v <= 0 else 0; mx = max(mx, streak)
    W = len(w) / len(ret); payoff = (w.mean() / abs(l.mean())) if len(w) and len(l) else np.nan
    kelly = W - (1 - W) / payoff if payoff == payoff and payoff > 0 else np.nan
    by = {}
    for rs in ('low20', 'stop', 'stop_same_day', 'open_at_end'):
        m = np.array([x['reason'] == rs for x in T])
        if m.any(): by[rs] = dict(n=int(m.sum()), win_rate=float((ret[m] > 0).mean()), avg_ret=float(ret[m].mean()), avg_R=float(R[m].mean()))
    return dict(n=len(T), win_rate=W, avg_win=float(w.mean()) if len(w) else None, avg_loss=float(l.mean()) if len(l) else None, payoff=payoff,
                expectancy_pct=float(ret.mean()), expectancy_R=float(R.mean()), max_consec_loss=int(mx), avg_hold_days=float(hold.mean()),
                kelly=kelly, half_kelly=kelly / 2 if kelly == kelly else np.nan, avg_risk_2N_pct=float(np.mean([2 * x['N'] / x['entry_px'] for x in T])),
                best=float(ret.max()), worst=float(ret.min()), by_reason=by,
                open_at_end=int(sum(x['reason'] == 'open_at_end' for x in T)))


def period_metrics(r, held, trades, bench, a, b):
    m = (r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b)); rr = r[m]
    out = fund.metrics(rr, bench, held[m]); out.update(dd=dd_info(rr), exposure_days=float(held[m].mean()))
    out['trades'] = trade_stats(trades, a, b)
    bb = bench[(bench.index >= pd.Timestamp(a)) & (bench.index <= pd.Timestamp(b))]
    out['BH'] = fund.metrics(bb); out['BH']['dd'] = dd_info(bb)
    return out


def yearly(r, bench):
    y = pd.DataFrame({'strat': (1 + r).groupby(r.index.year).prod() - 1, 'bh': (1 + bench.reindex(r.index).fillna(0)).groupby(r.index.year).prod() - 1})
    return {int(k): dict(strat=float(v.strat), bh=float(v.bh)) for k, v in y.iterrows()}


def log_trial(name, p, extra, sr):
    validate.registry_log(str(OUT), name, dict(p, **extra), sr)
    LOG.append(dict(name=name, params=p, **extra))


# ================================================================ 단계
def run_base(data):
    res = {}
    for name in ('K200', 'KQ150'):
        bench = bh(name, data); res[name] = {}
        for mode in ('a', 'b'):
            for tag, kw in (('base', {}), ('cost2x', dict(cost_mult=2.0)), ('turtle_sizing', dict(sizing='turtle')), ('cash2.5%', dict(cash_rate=0.025))):
                s = turtle(data[name], BASE, mode=mode, **kw)
                log_trial(f'turtle_{name}_{mode}', BASE, dict(product=name, mode=mode, variant=tag), validate.sharpe(s['r']))
                periods = {'full': (START[name], END), 'etf': (SPLICE[name], END)}
                for i, (a, b) in enumerate(SUBS[name]): periods[f'sub{i + 1}'] = (a, b)
                res[name][f'{mode}_{tag}'] = dict(periods={k: period_metrics(s['r'], s['held'], s['trades'], bench, a, b) for k, (a, b) in periods.items()},
                                                 yearly=yearly(s['r'], bench) if tag == 'base' else None,
                                                 trades=[{k: (str(v.date()) if hasattr(v, 'date') else v) for k, v in x.items()} for x in s['trades']] if tag == 'base' else None)
                if tag == 'base': res[name][f'_sim_{mode}'] = s
                if tag == 'cost2x': res[name][f'_sim2_{mode}'] = s
        # fund.run 교차검증 (a): 같은 보유 신호를 표준 엔진에 넣으면(비용 = fund 의 주식 호가단위)
        s = res[name]['_sim_a']; W = s['held'].shift(-1).fillna(s['held'].iloc[-1]).to_frame(name)   # held[t+1] 를 t 종가에 결정
        r_f, _, _ = fund.run({name: data[name]}, W, start=START[name])
        res[name]['cross_check_fund_run_a'] = dict(own=fund.metrics(s['r']), fund_run=fund.metrics(r_f), corr=float(np.corrcoef(s['r'].fillna(0), r_f.reindex(s['r'].index).fillna(0))[0, 1]))
    return res


def run_sens(data):
    rows = []
    for name in ('K200', 'KQ150'):
        bench = bh(name, data)
        for mode in ('a', 'b'):
            for en in (40, 55, 70):
                for ex in (10, 20, 30):
                    for sn in (1.5, 2.0, 3.0):
                        p = dict(BASE, entry=en, exit=ex, stop_n=sn); s = turtle(data[name], p, mode=mode)
                        mf = fund.metrics(s['r']); me = fund.metrics(s['r'][s['r'].index >= SPLICE[name]])
                        ts = trade_stats(s['trades'])
                        rows.append(dict(product=name, mode=mode, entry=en, exit=ex, stop_n=sn, base=(en, ex, sn) == (55, 20, 2.0),
                                         full_CAGR=mf['CAGR'], full_MDD=mf['MDD'], full_Sharpe=mf['Sharpe'], etf_CAGR=me['CAGR'], etf_MDD=me['MDD'], etf_Sharpe=me['Sharpe'],
                                         n_trades=ts['n'], win_rate=ts.get('win_rate'), payoff=ts.get('payoff'), exp_R=ts.get('expectancy_R')))
                        log_trial(f'turtle_{name}_{mode}', p, dict(product=name, mode=mode, variant='sensitivity'), mf['Sharpe'])
    df = pd.DataFrame(rows); df.to_csv(OUT / 'sensitivity.csv', index=False, encoding='utf-8-sig')
    return df


def run_vh(data, tres):
    """변동성 수확(균형형 + 간격 하한 3% [+ 코스닥 신호 A 매집 구간]) 일봉 엔진 = runs/adhoc_20261026_0915_quant/backtest/backtest.py 재사용."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('vh_review', '~/agent-fund/runs/adhoc_20261026_0915_quant/backtest/backtest.py')
    VH = importlib.util.module_from_spec(spec); spec.loader.exec_module(VH)
    out = {}
    for name in ('K200', 'KQ150'):
        bench = bh(name, data); res = {}
        cfgs = {'균형형+하한3%': dict(VH.BASE, dip=False)}
        if name == 'KQ150': cfgs['균형형+하한3%+신호A 매집(현행)'] = dict(VH.BASE)
        for cn, p in cfgs.items():
            p = dict(p, v_start=START[name])
            sim = VH.simulate(p, 'v', None, px_override={'229200': data[name][['open', 'high', 'low', 'close']], 'KOSDAQ': data['KQidx']})
            r = sim['r'].reindex(data[name].index[data[name].index >= START[name]]).fillna(0); held = (sim['expo'] > 0).astype(float).reindex(r.index).fillna(0)
            log_trial(f'vh_{name}', {k: v for k, v in p.items()}, dict(product=name, variant='vh_compare'), validate.sharpe(r))
            periods = {'full': (START[name], END), 'etf': (SPLICE[name], END)}
            for i, (a, b) in enumerate(SUBS[name]): periods[f'sub{i + 1}'] = (a, b)
            pm = {}
            for k, (a, b) in periods.items():
                m = (r.index >= a) & (r.index <= b); x = fund.metrics(r[m], bench); x['dd'] = dd_info(r[m]); x['avg_invested'] = float(sim['expo'].reindex(r.index)[m].mean()); pm[k] = x
            res[cn] = dict(periods=pm, yearly=yearly(r, bench), r=r, invested=sim['expo'])
        # 상관·50:50 (터틀 (a) 기준안 vs 변동성 수확 기본)
        tr = tres[name]['_sim_a']['r']; vn = '균형형+하한3%+신호A 매집(현행)' if name == 'KQ150' else '균형형+하한3%'
        vr = res[vn]['r']; j = pd.concat([tr, vr], axis=1, keys=['t', 'v']).dropna()
        combo = {}
        for k, (a, b) in {'full': (START[name], END), 'etf': (SPLICE[name], END)}.items():
            jj = j[(j.index >= a) & (j.index <= b)]; c = 0.5 * jj.t + 0.5 * jj.v                    # 매일 50:50 재조정(재조정 비용 미반영)
            # 월말 재조정 버전
            eqm = []; wt = wv = 0.5; v_ = 1.0; last_m = None
            for dt_, row in jj.iterrows():
                if last_m is not None and dt_.month != last_m: wt, wv = 0.5 * v_, 0.5 * v_
                wt *= 1 + row.t; wv *= 1 + row.v; v_ = wt + wv; eqm.append(v_); last_m = dt_.month
            cm = pd.Series(eqm, index=jj.index).pct_change().fillna(pd.Series(eqm, index=jj.index).iloc[0] - 1)
            combo[k] = dict(corr=float(jj.t.corr(jj.v)), turtle=fund.metrics(jj.t), vh=fund.metrics(jj.v), daily_5050=fund.metrics(c), monthly_5050=fund.metrics(cm),
                            daily_5050_dd=dd_info(c), monthly_5050_dd=dd_info(cm))
        res['_combo'] = combo; res['_combo_vh'] = vn
        out[name] = res
    return out


def run_fresh(data):
    """ETF 상장일에 두 전략을 새로 시작(사다리는 경로 의존적이라 1990/1997년부터 이어 돌린 상태가 상장 이후 성과를 좌우하므로).
    터틀 지표는 상장 전 이력으로 미리 계산, 매매는 상장일부터. 사다리도 지표는 전체 이력, 포트폴리오는 상장일에 빈 상태로 시작."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('vh_review2', '~/agent-fund/runs/adhoc_20261026_0915_quant/backtest/backtest.py')
    VH = importlib.util.module_from_spec(spec); spec.loader.exec_module(VH)
    out = {}
    for name in ('K200', 'KQ150'):
        sp = SPLICE[name]; bench = bh(name, data, start=sp); res = {}
        for mode in ('a', 'b'):
            s = turtle(data[name], BASE, mode=mode, start=sp)
            log_trial(f'turtle_{name}_{mode}', BASE, dict(product=name, mode=mode, variant='fresh_etf_start'), validate.sharpe(s['r']))
            m = fund.metrics(s['r'], bench, s['held']); m['dd'] = dd_info(s['r']); m['trades'] = trade_stats(s['trades']); m['exposure_days'] = float(s['held'].mean())
            res[f'turtle_{mode}'] = dict(metrics=m, r=s['r'])
        vp = dict(VH.BASE, dip=(name == 'KQ150'), v_start=sp)
        sim = VH.simulate(vp, 'v', None, px_override={'229200': data[name][['open', 'high', 'low', 'close']], 'KOSDAQ': data['KQidx']})
        r = sim['r']; log_trial(f'vh_{name}', vp, dict(product=name, variant='fresh_etf_start'), validate.sharpe(r))
        m = fund.metrics(r, bench); m['dd'] = dd_info(r); m['avg_invested'] = float(sim['expo'].mean())
        res['vh'] = dict(metrics=m, r=r, name='균형형+하한3%' + ('+신호A 매집(현행)' if name == 'KQ150' else ''))
        j = pd.concat([res['turtle_a']['r'], r], axis=1, keys=['t', 'v']).dropna(); c = 0.5 * j.t + 0.5 * j.v
        res['combo'] = dict(corr=float(j.t.corr(j.v)), daily_5050=fund.metrics(c), daily_5050_dd=dd_info(c))
        res['BH'] = fund.metrics(bench); res['BH']['dd'] = dd_info(bench)
        out[name] = res
    return out


def charts(data, tres, vres):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    plt.rcParams['font.family'] = 'AppleGothic'; plt.rcParams['axes.unicode_minus'] = False
    for name, lab in (('K200', 'KODEX200 (1990~2002 KOSPI 대용)'), ('KQ150', 'KODEX코스닥150 (1997~2015 KOSDAQ 대용)')):
        bench = bh(name, data); ra = tres[name]['_sim_a']['r']; rb = tres[name]['_sim_b']['r']
        vn = vres[name]['_combo_vh']; rv = vres[name][vn]['r']
        S = {'터틀 (a) 다음날 시가': ra, '터틀 (b) 장중 돌파': rb, f'변동성 수확 ({vn})': rv, 'Buy&Hold': bench.reindex(ra.index).fillna(0)}
        col = {'터틀 (a) 다음날 시가': '#1f4e79', '터틀 (b) 장중 돌파': '#5b9bd5', f'변동성 수확 ({vn})': '#c55a11', 'Buy&Hold': '#888'}
        fig, ax = plt.subplots(3, 1, figsize=(12, 11), gridspec_kw=dict(height_ratios=[3, 1.6, 1.8]))
        for k, x in S.items():
            e = (1 + x).cumprod(); ax[0].plot(e, label=k, color=col[k], lw=1.1)
            ax[1].plot(e / e.cummax() - 1, color=col[k], lw=.9)
        ax[0].set_yscale('log'); ax[0].axvline(pd.Timestamp(SPLICE[name]), color='#c00', ls='--', lw=.8); ax[0].legend(fontsize=9)
        ax[0].set_title(f'{lab} — 누적 수익(로그), 빨간 점선 = ETF 연결 시점'); ax[1].set_title('낙폭')
        ax[1].axvline(pd.Timestamp(SPLICE[name]), color='#c00', ls='--', lw=.8)
        y = pd.DataFrame({k: (1 + x).groupby(x.index.year).prod() - 1 for k, x in S.items() if k != '터틀 (b) 장중 돌파'})
        xs = np.arange(len(y)); w = 0.27
        for i, k in enumerate(y.columns): ax[2].bar(xs + (i - 1) * w, y[k] * 100, w, label=k, color=col[k])
        ax[2].set_xticks(xs); ax[2].set_xticklabels(y.index, rotation=90, fontsize=7); ax[2].axhline(0, color='k', lw=.5); ax[2].set_title('연도별 수익률(%)'); ax[2].legend(fontsize=8)
        fig.tight_layout(); fig.savefig(OUT / f'chart_{name}.png', dpi=110); plt.close(fig)


def strip(res):
    return {k: v for k, v in res.items() if not str(k).startswith('_')}


def dump(o, f):
    json.dump(o, open(OUT / f, 'w'), ensure_ascii=False, indent=1, default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else (None if x is None else str(x)))


def run_validate(data, n_trials):
    out = {}
    for name in ('K200', 'KQ150'):
        bench = bh(name, data)
        for mode in ('a', 'b'):
            od = OUT if (name, mode) == ('K200', 'a') else OUT / f'validation_{name}_{mode}'
            p = dict(BASE, start=START[name])
            res = validate.run_all(f'터틀 55/20/2N {name} ({"다음날 시가" if mode == "a" else "장중 돌파"}) 1990~ 지수 대용 연결', strategy_factory(mode), p,
                                   {name: data[name]}, bench, outdir=str(od), grid=None, n_trials=n_trials, source='paper', time_budget=900)
            out[f'{name}_{mode}'] = dict(verdict=res['auto_verdict'], dir=str(od.relative_to(RUN)),
                                         fails=[x['item'] for x in res['checklist'] if x['status'] == 'FAIL'], warns=[x['item'] for x in res['checklist'] if x['status'] == 'WARN'])
            print(name, mode, res['auto_verdict'])
    dump(out, 'validation_summary.json')
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('stage', nargs='?', default='all'); a = ap.parse_args()
    data = load()
    for k in ('K200', 'KQ150'): print(k, data[k].index[0].date(), data[k].index[-1].date(), 'ratio', round(data[k].attrs['ratio'], 4))
    tres = run_base(data)
    sens = run_sens(data)
    vres = run_vh(data, tres)
    fres = run_fresh(data)
    charts(data, tres, vres)
    # 표준 산출물: KODEX200 터틀 (a) → backtest/metrics.json·equity.png, 나머지는 하위 폴더
    for name in ('K200', 'KQ150'):
        for mode in ('a', 'b'):
            s, s2 = tres[name][f'_sim_{mode}'], tres[name][f'_sim2_{mode}']
            od = OUT if (name, mode) == ('K200', 'a') else OUT / f'eval_{name}_{mode}'
            fund.evaluate(f'터틀 55/20/2N {name} ({mode})', s['r'], s['held'], bh(name, data), SPLICE[name], turnover=s['turnover'],
                          extra=dict(note='파라미터 원문 고정(최적화 없음). oos_start = ETF 상장일(지수 대용 구간과 구분용).', trades=trade_stats(s['trades'])),
                          outdir=od, r_cost2=s2['r'])
    vsum = {}
    for name in vres:
        vsum[name] = {k: ({kk: vv for kk, vv in v.items() if kk not in ('r', 'invested')} if isinstance(v, dict) and not k.startswith('_') else v) for k, v in vres[name].items()}
    # 지수 vs ETF 괴리 (069500 vs KPI200, 2006~)
    raw = data['raw']; j = pd.concat([raw['E200']['close'], raw['KPI200']['close']], axis=1, keys=['etf', 'idx']).dropna()
    yrs = (j.index[-1] - j.index[0]).days / 365.25
    track = dict(start=str(j.index[0].date()), etf_cagr=float((j.etf.iloc[-1] / j.etf.iloc[0]) ** (1 / yrs) - 1), idx_cagr=float((j.idx.iloc[-1] / j.idx.iloc[0]) ** (1 / yrs) - 1),
                 daily_corr=float(j.pct_change().corr().iloc[0, 1]))
    j2 = pd.concat([raw['E200']['close'], raw['KOSPI']['close']], axis=1, keys=['etf', 'kospi']).dropna()
    track['kospi_cagr_same'] = float((j2.kospi.iloc[-1] / j2.kospi.loc[j.index[0]]) ** (1 / yrs) - 1)
    j3 = pd.concat([raw['E150']['close'], raw['KOSDAQ']['close']], axis=1, keys=['etf', 'kq']).dropna()
    y3 = (j3.index[-1] - j3.index[0]).days / 365.25
    track['kq150_etf_cagr'] = float((j3.etf.iloc[-1] / j3.etf.iloc[0]) ** (1 / y3) - 1); track['kosdaq_cagr_same'] = float((j3.kq.iloc[-1] / j3.kq.iloc[0]) ** (1 / y3) - 1)
    track['kq_daily_corr'] = float(j3.pct_change().corr().iloc[0, 1])
    n_trials = len(LOG) + 4 * 17                                  # + validate 이웃 변형 등(보수적으로 더함)
    vals = run_validate(data, n_trials)
    rob = dict(note='민감도(진입 40·55·70 × 청산 10·20·30 × 손절 1.5·2·3N)는 참고용. 기준안(55/20/2N)은 바꾸지 않았다.',
               sensitivity=sens.to_dict('records'),
               subperiods={name: {k: {kk: tres[name][f'{k}_base']['periods'][kk] for kk in ('sub1', 'sub2', 'sub3')} for k in ('a', 'b')} for name in ('K200', 'KQ150')},
               cost2x={name: {m: tres[name][f'{m}_cost2x']['periods'] for m in ('a', 'b')} for name in ('K200', 'KQ150')},
               slippage_note='장기 추세 전략(연 수 회 매매)·대형 지수 ETF라 +1~2틱 별도 실험 대신 비용 2배(편도 0.03%+2틱, 대용 0.1%)로 대신함.')
    dump(rob, 'robustness.json')
    fsum = {n: {k: ({kk: vv for kk, vv in v.items() if kk != 'r'} if isinstance(v, dict) else v) for k, v in fres[n].items()} for n in fres}
    dump(dict(fresh_etf=fsum, turtle={n: strip(v) for n, v in tres.items()}, vh=vsum, tracking=track, validation=vals, n_trials=n_trials,
              splice={n: dict(date=SPLICE[n], ratio=data[n].attrs['ratio'], start=START[n]) for n in ('K200', 'KQ150')}), 'results.json')
    print('done n_trials', n_trials)


if __name__ == '__main__':
    main()
