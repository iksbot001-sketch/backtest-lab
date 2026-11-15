"""터틀 트레이딩 장기 전략(System 2: 55일 돌파 진입·20일 저가 청산·2N 손절) — 미국 S&P500(^GSPC)·나스닥100(^NDX) 36년 검증 (1990~2026)
대표 지시 2026-10-26 (BRIEF.md). 한국 편(runs/adhoc_20261026_1224_quant/backtest/backtest.py)과 동일한 엔진·규칙·표 양식으로 비교.

규칙 및 비용:
  - 원문 파라미터 고정: 진입 55일 최고가 돌파 / 청산 20일 최저가 이탈 / 손절 진입가 - 2N (N=20일 Wilder ATR, 진입 시 고정).
  - 롱 온리, 1포지션, 피라미딩 없음, 미보유 현금 이자 0% (보조안으로 현금 2.5% 및 ^IRX T-bill 이자 버전 별도 계산).
  - 체결: (a) 종가 신호 → 다음 날 시가 체결, (b) 장중 돌파가(max(돌파가, 시가)) 매수 / 장중 이탈가(min(청산기준가, 시가)) 매도.
  - 비용: 미국 ETF 수수료+스프레드 가정 편도 0.05% (한국 편 엔진의 proxy=1.0 경로가 정확히 편도 0.05% * cost_mult 를 차감하므로 그대로 재사용).
  - 기간: 1990-01-02 ~ 마지막 날 (GSPC 2026-10-20, NDX 2026-10-21; 지표 워밍업은 1980/1985년 원천 데이터부터 계산 후 1990-01-02부터 매매).
  - 가격지수(^GSPC, ^NDX)이므로 배당 미반영(S&P500 배당 연 ~2%, NDX 연 ~0.6% 수준 — 보고서에 명시).

실행: ~/agent-fund/venv/bin/python backtest/backtest.py
"""
import sys, json, math, time, importlib.util
from pathlib import Path

sys.path.insert(0, '~/agent-fund/lib')
import fund, validate
import numpy as np, pandas as pd

OUT = Path(__file__).resolve().parent
RUN = OUT.parent
DATA = RUN / 'data'
KR_RUN = Path('~/agent-fund/runs/adhoc_20261026_1224_quant')

# 한국 편 엔진 재사용 (파일 수정 없이 import)
_spec = importlib.util.spec_from_file_location('kr_bt', str(KR_RUN / 'backtest' / 'backtest.py'))
kr_bt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kr_bt)

turtle = kr_bt.turtle
trade_stats = kr_bt.trade_stats
period_metrics = kr_bt.period_metrics
yearly = kr_bt.yearly
dd_info = kr_bt.dd_info
BASE = dict(kr_bt.BASE)  # {'entry': 55, 'exit': 20, 'stop_n': 2.0, 'atr_n': 20}

START_DATE = '1990-01-02'
SUBS_TEMPLATE = [
    ('sub1', '1990-01-02', '2002-10-11'),
    ('sub2', '2002-10-14', '2015-09-30'),
    ('sub3', '2015-10-01', None),
]
OOS_SPLIT = '2002-10-14'  # 한국 편 KODEX200 상장일과 동일 기준선
COST_ONEWAY = 0.0005      # 미국 ETF 편도 0.05%

LOG = []


# ================================================================ 데이터 로드
def load_us():
    irx_df = fund._yh_json(json.load(open(DATA / 'yh_IRX.json')))
    fund._cash = irx_df['close']  # 표준 엔진 무위험수익률(^IRX)을 로컬 파일로 고정

    out = {'IRX': irx_df}
    for sym in ('GSPC', 'NDX', 'IXIC'):
        df = fund._yh_json(json.load(open(DATA / f'yh_{sym}.json')))
        # OHLC 무결성 보정 (고가=max, 저가=min)
        df['high'] = df[['open', 'high', 'low', 'close']].max(axis=1)
        df['low'] = df[['open', 'high', 'low', 'close']].min(axis=1)
        df['adj'] = df['close']
        for c in ('open', 'high', 'low'):
            df['a' + c] = df[c]
        # proxy=1.0 으로 설정하면 kr_bt.turtle 내부에서 편도 PROXY_COST(0.05%) * cost_mult 를 정확히 적용함
        df['proxy'] = 1.0
        df.attrs['market'] = 'US'
        out[sym] = df
    return out


def log_trial(name, p, extra, sr):
    validate.registry_log(str(OUT), name, dict(p, **extra), sr)
    LOG.append(dict(name=name, params=p, **extra))


_BH = {}
def bh(sym, data, start=START_DATE):
    key = (sym, start)
    if key not in _BH:
        px = data[sym]
        W = pd.DataFrame(1.0, index=px.index, columns=[sym])
        _BH[key] = fund.run({sym: px}, W, start=start)[0]
    return _BH[key]


# ================================================================ 50/200 골든크로스 (동일 체결·동일 비용 0.05%)
def golden_cross(px, fast=50, slow=200, cost_mult=1.0, cash_rate=0.0, start=START_DATE):
    """종가 50일선 > 200일선이면 보유, 다음 날 시가 체결.
    터틀 (a)와 100% 동일한 포트폴리오·체결·비용(편도 0.05% * cost_mult, 미보유 현금 이자 cash_rate) 구조."""
    d = px
    i_start = 0 if start is None else int(np.searchsorted(d.index.values, np.datetime64(pd.Timestamp(start))))
    O = d['open'].values.astype(float)
    C = d['close'].values.astype(float)
    cs = pd.Series(C, index=d.index)
    ma_f = cs.rolling(fast).mean().values
    ma_s = cs.rolling(slow).mean().values
    idx = d.index
    n = len(d)
    gap = np.r_[0, (idx[1:] - idx[:-1]).days]
    rt_base = COST_ONEWAY * cost_mult

    cash = 1.0
    sh = 0.0
    eq = np.empty(n)
    held = np.zeros(n, bool)
    turn = np.zeros(n)
    trades = []
    cur = None
    pend = None

    for t in range(n):
        if t < i_start:
            eq[t] = 1.0
            continue
        if cash_rate and t > i_start:
            cash *= (1 + cash_rate) ** (gap[t] / 365.0)
        if pend == 'buy' and cur is None:
            px_ = O[t]
            e0 = cash + sh * px_
            sh = e0 / (px_ * (1 + rt_base))
            cash = 0.0
            turn[t] += 1.0
            cur = dict(entry_date=idx[t], entry_px=px_, entry_eff=px_ * (1 + rt_base), i0=t)
            pend = None
        elif pend == 'sell' and cur is not None:
            px_ = O[t]
            e_pre = cash + sh * px_
            cash += sh * px_ * (1 - rt_base)
            turn[t] += (sh * px_) / max(e_pre, 1e-12)
            cur.update(exit_date=idx[t], exit_px=px_, exit_eff=px_ * (1 - rt_base), reason='dead_cross', i1=t)
            trades.append(cur)
            cur = None
            sh = 0.0
            pend = None

        eq[t] = cash + sh * C[t]
        held[t] = sh > 0

        # t일 종가로 t+1일 시가 주문 결정
        if not np.isnan(ma_f[t]) and not np.isnan(ma_s[t]):
            want = ma_f[t] > ma_s[t]
            if want and cur is None:
                pend = 'buy'
            elif (not want) and cur is not None:
                pend = 'sell'

    if cur is not None:
        cur.update(exit_date=idx[-1], exit_px=C[-1], exit_eff=C[-1] * (1 - rt_base), reason='open_at_end', i1=n - 1)
        trades.append(cur)

    sl = slice(i_start, None)
    e = pd.Series(eq, index=idx)[sl]
    r = e.pct_change()
    r.iloc[0] = e.iloc[0] - 1.0
    return dict(
        r=r,
        eq=e,
        held=pd.Series(held, index=idx).astype(float)[sl],
        turnover=pd.Series(turn, index=idx)[sl],
        trades=trades,
    )


# ================================================================ 기본 실행 (GSPC, NDX, IXIC)
def run_base(data):
    res = {}
    for sym in ('GSPC', 'NDX', 'IXIC'):
        end_dt = str(data[sym].index[-1].date())
        bench = bh(sym, data, start=START_DATE)
        res[sym] = {}
        periods = {
            'full': (START_DATE, end_dt),
            'post2002': (OOS_SPLIT, end_dt),
        }
        for k, a, b in SUBS_TEMPLATE:
            periods[k] = (a, b or end_dt)

        for mode in ('a', 'b'):
            for tag, kw in (
                ('base', {}),
                ('cost2x', dict(cost_mult=2.0)),
                ('turtle_sizing', dict(sizing='turtle')),
                ('cash2.5%', dict(cash_rate=0.025)),
            ):
                s = turtle(data[sym], BASE, mode=mode, start=START_DATE, **kw)
                log_trial(f'turtle_{sym}_{mode}', BASE, dict(product=sym, mode=mode, variant=tag), validate.sharpe(s['r']))
                res[sym][f'{mode}_{tag}'] = dict(
                    periods={k: period_metrics(s['r'], s['held'], s['trades'], bench, a, b) for k, (a, b) in periods.items()},
                    yearly=yearly(s['r'], bench) if tag == 'base' else None,
                    trades=[{k: (str(v.date()) if hasattr(v, 'date') else v) for k, v in x.items()} for x in s['trades']] if tag == 'base' else None,
                )
                if tag == 'base':
                    res[sym][f'_sim_{mode}'] = s
                if tag == 'cost2x':
                    res[sym][f'_sim2_{mode}'] = s

        # fund.run 교차검증 (a): 같은 보유 신호를 표준 엔진에 넣었을 때 (현금에 ^IRX 이자 반영)
        s_a = res[sym]['_sim_a']
        W = s_a['held'].shift(-1).fillna(s_a['held'].iloc[-1]).to_frame(sym)
        r_f, _, _ = fund.run({sym: data[sym]}, W, start=START_DATE)
        res[sym]['cross_check_fund_run_a'] = dict(
            own=fund.metrics(s_a['r'], bench, s_a['held']),
            fund_run=fund.metrics(r_f, bench, s_a['held']),
            corr=float(np.corrcoef(s_a['r'].fillna(0), r_f.reindex(s_a['r'].index).fillna(0))[0, 1]),
        )
    return res


# ================================================================ 공정 비교 3가지 (CRO 지적 반영)
def run_fair_comparisons(data, tres):
    """1. 같은 평균 노출의 단순 보유(지수 x% + 현금) vs 터틀
    2. 소수 사건 의존: 연도별 수익 상위 1~2년(및 3·5년, 매매 상위 1·3·5개) 제외 시 CAGR/ROI
    3. 50/200일 골든크로스(종가 50일선 > 200일선, 다음 날 시가, 같은 비용 0.05%) 비교"""
    out = {'same_exposure_bh': {}, 'outlier_dependency': {}, 'golden_cross': {}}

    for sym in ('GSPC', 'NDX', 'IXIC'):
        end_dt = str(data[sym].index[-1].date())
        bench = bh(sym, data, start=START_DATE)
        periods = {
            'full': (START_DATE, end_dt),
            'sub1': ('1990-01-02', '2002-10-11'),
            'sub2': ('2002-10-14', '2015-09-30'),
            'sub3': ('2015-10-01', end_dt),
            'post2002': (OOS_SPLIT, end_dt),
        }

        # 1) 같은 평균 노출 단순 보유 (매일 x% 지수 + (1-x)% 무이자 현금, 및 ^IRX 이자 현금)
        out['same_exposure_bh'][sym] = {}
        for mode in ('a', 'b'):
            s = tres[sym][f'_sim_{mode}']
            out['same_exposure_bh'][sym][mode] = {}
            for pk, (a, b) in periods.items():
                m = (s['r'].index >= pd.Timestamp(a)) & (s['r'].index <= pd.Timestamp(b))
                rt = s['r'][m]
                ht = s['held'][m]
                bt_r = bench.reindex(rt.index).fillna(0)
                x_expo = float(ht.mean())
                r_const_cash0 = x_expo * bt_r
                cd = fund.cash_daily(rt.index)
                r_const_tbill = x_expo * bt_r + (1.0 - x_expo) * cd

                tm = fund.metrics(rt, bt_r, ht)
                tm['dd'] = dd_info(rt)
                tm['sharpe_rf0'] = float(rt.mean() / rt.std() * np.sqrt(252)) if rt.std() > 0 else np.nan

                cm0 = fund.metrics(r_const_cash0, bt_r)
                cm0['dd'] = dd_info(r_const_cash0)
                cm0['sharpe_rf0'] = float(r_const_cash0.mean() / r_const_cash0.std() * np.sqrt(252)) if r_const_cash0.std() > 0 else np.nan

                cmt = fund.metrics(r_const_tbill, bt_r)
                cmt['dd'] = dd_info(r_const_tbill)

                out['same_exposure_bh'][sym][mode][pk] = dict(
                    exposure=x_expo,
                    turtle=tm,
                    const_bh_cash0=cm0,
                    const_bh_tbill=cmt,
                )

        # 2) 소수 사건 의존 (상위 1·2·3·5개 연도 및 상위 1·3·5개 매매 제외)
        out['outlier_dependency'][sym] = {}
        for mode in ('a', 'b'):
            s = tres[sym][f'_sim_{mode}']
            yr_dict = tres[sym][f'{mode}_base']['yearly']
            yr_s = pd.Series({int(k): v['strat'] for k, v in yr_dict.items()})
            yr_bh = pd.Series({int(k): v['bh'] for k, v in yr_dict.items()})
            yr_sorted = yr_s.sort_values(ascending=False)
            bh_sorted = yr_bh.sort_values(ascending=False)
            n_years = len(s['r']) / 252.0

            def _yr_rem(ser_sorted, k):
                rem = ser_sorted.iloc[k:]
                roi = float((1.0 + rem).prod() - 1.0)
                yrs_rem = max(n_years - k, 1.0)
                cagr_full_span = float((1.0 + roi) ** (1.0 / n_years) - 1.0) if roi > -1 else -1.0
                cagr_rem_span = float((1.0 + roi) ** (1.0 / yrs_rem) - 1.0) if roi > -1 else -1.0
                return dict(
                    removed_years=[int(y) for y in ser_sorted.iloc[:k].index],
                    removed_rets_pct=[round(float(v) * 100, 2) for v in ser_sorted.iloc[:k].values],
                    roi=roi,
                    cagr_over_36y=cagr_full_span,
                    cagr_over_rem_years=cagr_rem_span,
                )

            t_list = s['trades']
            rets = np.array([x['exit_eff'] / x['entry_eff'] - 1.0 for x in t_list])
            order = np.argsort(rets)[::-1]
            sorted_rets = rets[order]

            def _tr_rem(k):
                rem = sorted_rets[k:]
                roi = float(np.prod(1.0 + rem) - 1.0)
                cagr = float((1.0 + roi) ** (1.0 / n_years) - 1.0) if roi > -1 else -1.0
                return dict(
                    roi=roi,
                    cagr=cagr,
                    removed_trades=[
                        dict(
                            entry_date=str(t_list[idx_t]['entry_date'].date()),
                            exit_date=str(t_list[idx_t]['exit_date'].date()),
                            ret=float(rets[idx_t]),
                            reason=t_list[idx_t]['reason'],
                        )
                        for idx_t in order[:k]
                    ],
                )

            out['outlier_dependency'][sym][mode] = dict(
                base_cagr=float(fund.metrics(s['r'])['CAGR']),
                base_roi=float(fund.metrics(s['r'])['ROI']),
                top_years_removed={f'top{k}': _yr_rem(yr_sorted, k) for k in (1, 2, 3, 5)},
                bh_top_years_removed={f'top{k}': _yr_rem(bh_sorted, k) for k in (1, 2, 3)},
                top_trades_removed={f'top{k}': _tr_rem(k) for k in (1, 3, 5)},
            )

        # 3) 50/200 골든크로스 (동일 비용 0.05%, 현금 이자 0%)
        gc = golden_cross(data[sym], fast=50, slow=200, cost_mult=1.0, cash_rate=0.0, start=START_DATE)
        gc_2x = golden_cross(data[sym], fast=50, slow=200, cost_mult=2.0, cash_rate=0.0, start=START_DATE)
        log_trial(f'gc50_200_{sym}', dict(fast=50, slow=200), dict(product=sym, variant='golden_cross_compare'), validate.sharpe(gc['r']))
        gc_periods = {}
        for pk, (a, b) in periods.items():
            m = (gc['r'].index >= pd.Timestamp(a)) & (gc['r'].index <= pd.Timestamp(b))
            rg = gc['r'][m]
            hg = gc['held'][m]
            bt_r = bench.reindex(rg.index).fillna(0)
            gm = fund.metrics(rg, bt_r, hg)
            gm['dd'] = dd_info(rg)
            gm['exposure_days'] = float(hg.mean())
            T_sub = [x for x in gc['trades'] if x['entry_date'] >= pd.Timestamp(a) and x['entry_date'] <= pd.Timestamp(b)]
            if T_sub:
                g_rets = np.array([x['exit_eff'] / x['entry_eff'] - 1.0 for x in T_sub])
                gw, gl = g_rets[g_rets > 0], g_rets[g_rets <= 0]
                gm['trade_summary'] = dict(
                    n=len(T_sub),
                    win_rate=float(len(gw) / len(g_rets)),
                    payoff=float(gw.mean() / abs(gl.mean())) if len(gw) and len(gl) else np.nan,
                    expectancy_pct=float(g_rets.mean()),
                    avg_hold_days=float(np.mean([x['i1'] - x['i0'] for x in T_sub])),
                )
            else:
                gm['trade_summary'] = dict(n=0)
            gc_periods[pk] = gm

        s_a = tres[sym]['_sim_a']
        common = s_a['r'].index.intersection(gc['r'].index)
        out['golden_cross'][sym] = dict(
            periods=gc_periods,
            cost2x_full=fund.metrics(gc_2x['r'], bench, gc_2x['held']),
            yearly=yearly(gc['r'], bench),
            corr_with_turtle_a=float(s_a['r'].loc[common].corr(gc['r'].loc[common])),
            pos_agreement_with_turtle_a=float(((s_a['held'].loc[common] > 0) == (gc['held'].loc[common] > 0)).mean()),
            _sim=gc,
        )

    # 대표 실운용 포트폴리오 대응: GSPC + NDX 50:50 골든크로스 vs 50:50 터틀(a) vs 50:50 B&H
    r_gc_g = out['golden_cross']['GSPC']['_sim']['r']
    r_gc_n = out['golden_cross']['NDX']['_sim']['r']
    h_gc_g = out['golden_cross']['GSPC']['_sim']['held']
    h_gc_n = out['golden_cross']['NDX']['_sim']['held']
    idx_c = r_gc_g.index.intersection(r_gc_n.index)

    r_gc_5050 = 0.5 * r_gc_g.loc[idx_c] + 0.5 * r_gc_n.loc[idx_c]
    h_gc_5050 = 0.5 * h_gc_g.loc[idx_c] + 0.5 * h_gc_n.loc[idx_c]
    r_tu_5050 = 0.5 * tres['GSPC']['_sim_a']['r'].loc[idx_c] + 0.5 * tres['NDX']['_sim_a']['r'].loc[idx_c]
    h_tu_5050 = 0.5 * tres['GSPC']['_sim_a']['held'].loc[idx_c] + 0.5 * tres['NDX']['_sim_a']['held'].loc[idx_c]
    r_bh_5050 = 0.5 * bh('GSPC', data).loc[idx_c] + 0.5 * bh('NDX', data).loc[idx_c]

    out['portfolio_5050_gspc_ndx'] = {}
    for pk, (a, b) in {
        'full': (START_DATE, str(idx_c[-1].date())),
        'post2002': (OOS_SPLIT, str(idx_c[-1].date())),
        'sub3': ('2015-10-01', str(idx_c[-1].date())),
    }.items():
        m = (idx_c >= pd.Timestamp(a)) & (idx_c <= pd.Timestamp(b))
        out['portfolio_5050_gspc_ndx'][pk] = dict(
            turtle_a_5050=dict(fund.metrics(r_tu_5050[m], r_bh_5050[m]), dd=dd_info(r_tu_5050[m]), avg_exposure=float(h_tu_5050[m].mean())),
            gc_50_200_5050=dict(fund.metrics(r_gc_5050[m], r_bh_5050[m]), dd=dd_info(r_gc_5050[m]), avg_exposure=float(h_gc_5050[m].mean())),
            bh_5050=dict(fund.metrics(r_bh_5050[m]), dd=dd_info(r_bh_5050[m]), avg_exposure=1.0),
        )
    return out


# ================================================================ 추세 지속성 및 하락장 구조 분석 (Why US Differs)
def run_market_structure_analysis(data, tres, fcomp):
    # 한국 데이터 로드 (runs/adhoc_20261026_1224_quant/data/nv_*.txt)
    kospi = kr_bt._clean(kr_bt._nv('KOSPI'))
    e200 = kr_bt._clean(kr_bt._nv('069500'))
    kosdaq = kr_bt._clean(kr_bt._nv('KOSDAQ'))
    e150 = kr_bt._clean(kr_bt._nv('229200'))

    def _splice(idx_df, etf_df, sp_str, s0):
        sp = pd.Timestamp(sp_str)
        ratio = etf_df['close'].loc[sp] / idx_df['close'].loc[sp]
        pre = idx_df[(idx_df.index >= s0) & (idx_df.index < sp)][['open', 'high', 'low', 'close']] * ratio
        post = etf_df[etf_df.index >= sp][['open', 'high', 'low', 'close']].copy()
        return pd.concat([pre, post])

    k200_df = _splice(kospi, e200, '2002-10-14', '1990-01-04')
    kq150_df = _splice(kosdaq, e150, '2015-10-01', '1997-01-03')

    series_map = [
        ('K200', k200_df, '1990-01-04'),
        ('KQ150', kq150_df, '1997-01-03'),
        ('GSPC', data['GSPC'], '1990-01-02'),
        ('NDX', data['NDX'], '1990-01-02'),
        ('IXIC', data['IXIC'], '1990-01-02'),
    ]

    trend_stats = {}
    for name, df, s0 in series_map:
        d = df.loc[s0:].copy()
        c = d['close']
        h = d['high']
        l = d['low']
        r1 = c.pct_change()
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        atr20 = tr.ewm(alpha=1 / 20, adjust=False).mean()

        ch55 = h.rolling(55).max().shift(1)
        ch20_low = l.rolling(20).min().shift(1)
        brk = c > ch55
        first_brk = brk & (~brk.shift(1, fill_value=False))

        fwd5 = (c.shift(-5) / c - 1.0)
        fwd20 = (c.shift(-20) / c - 1.0)
        fwd60 = (c.shift(-60) / c - 1.0)

        # 첫 55일 돌파 후 20거래일 안에 종가가 (돌파종가 - 2N) 또는 20일 저가를 하향 이탈하는 비율 (whipsaw 비율)
        brk_indices = np.where(first_brk.values)[0]
        whipsaw_20d = 0
        valid_brk = 0
        for idx_i in brk_indices:
            if idx_i + 20 >= len(c):
                continue
            valid_brk += 1
            entry_c = c.iloc[idx_i]
            stop_lvl = entry_c - 2.0 * atr20.iloc[idx_i]
            future_lows = l.iloc[idx_i + 1 : idx_i + 21]
            future_ch20 = ch20_low.iloc[idx_i + 1 : idx_i + 21]
            if (future_lows <= stop_lvl).any() or (future_lows <= future_ch20).any():
                whipsaw_20d += 1

        trend_stats[name] = dict(
            autocorr_1d=float(r1.autocorr(1)),
            autocorr_5d=float(c.pct_change(5).autocorr(5)),
            autocorr_20d=float(c.pct_change(20).autocorr(20)),
            n_first_breakouts_55d=int(first_brk.sum()),
            brk55_fwd5d_mean=float(fwd5[first_brk].dropna().mean()),
            brk55_fwd20d_mean=float(fwd20[first_brk].dropna().mean()),
            brk55_fwd60d_mean=float(fwd60[first_brk].dropna().mean()),
            uncond_fwd20d_mean=float(fwd20.dropna().mean()),
            uncond_fwd60d_mean=float(fwd60.dropna().mean()),
            edge_fwd20d_vs_uncond=float(fwd20[first_brk].dropna().mean() - fwd20.dropna().mean()),
            edge_fwd60d_vs_uncond=float(fwd60[first_brk].dropna().mean() - fwd60.dropna().mean()),
            whipsaw_within_20d_rate=float(whipsaw_20d / max(valid_brk, 1)),
            avg_2N_pct_of_price=float((2.0 * atr20 / c).dropna().mean()),
            up_days_ratio=float((r1 > 0).mean()),
        )

    # 주요 위기·회복 및 장세 구간별 성과 (2000~2002 닷컴붕괴, 2008 금융위기, 2009~2019 장기강세, 2020 코로나 V자, 2022 금리인상, 2023~2026 AI강세)
    episodes = [
        ('2000_2002_dotcom_bust', '2000-03-24', '2002-10-09'),
        ('2003_2007_recovery', '2002-10-10', '2007-10-09'),
        ('2008_gfc', '2007-10-10', '2009-03-09'),
        ('2009_2019_long_bull', '2009-03-10', '2019-12-31'),
        ('2020_covid_v_shock', '2020-01-02', '2020-12-31'),
        ('2022_rate_hike_bear', '2022-01-03', '2022-12-30'),
        ('2023_2026_ai_bull', '2023-01-03', '2026-10-20'),
    ]
    ep_res = {}
    for sym in ('GSPC', 'NDX'):
        ep_res[sym] = {}
        ra = tres[sym]['_sim_a']['r']
        rb = tres[sym]['_sim_b']['r']
        rg = fcomp['golden_cross'][sym]['_sim']['r']
        rbh = bh(sym, data)
        ha = tres[sym]['_sim_a']['held']
        hg = fcomp['golden_cross'][sym]['_sim']['held']
        for ep_name, a, b in episodes:
            m = (ra.index >= pd.Timestamp(a)) & (ra.index <= pd.Timestamp(b))
            def _ep_stat(r_s, h_s=None):
                roi = float((1.0 + r_s[m]).prod() - 1.0)
                mdd_v = float(dd_info(r_s[m])['mdd'])
                expo_v = float(h_s[m].mean()) if h_s is not None else 1.0
                return dict(roi=roi, mdd=mdd_v, exposure=expo_v)
            ep_res[sym][ep_name] = dict(
                start=a,
                end=b,
                turtle_a=_ep_stat(ra, ha),
                turtle_b=_ep_stat(rb, tres[sym]['_sim_b']['held']),
                gc_50_200=_ep_stat(rg, hg),
                bh=_ep_stat(rbh, None),
            )

    return dict(trend_persistence=trend_stats, episodes=ep_res)


# ================================================================ 한국 vs 미국 한 표 생성용 요약
def build_kr_us_comparison(data, tres, fcomp):
    kr_res = json.load(open(KR_RUN / 'backtest' / 'results.json'))
    kr_cro = json.load(open('~/agent-fund/runs/adhoc_20261026_1235_cro/backtest/cro_checks/cro_audit_results.json'))

    # KQ150 전체 구간 동일 노출 단순 보유 계산
    kosdaq = kr_bt._clean(kr_bt._nv('KOSDAQ'))
    e150 = kr_bt._clean(kr_bt._nv('229200'))
    sp_kq = pd.Timestamp('2015-10-01')
    ratio_kq = e150['close'].loc[sp_kq] / kosdaq['close'].loc[sp_kq]
    pre_kq = kosdaq[(kosdaq.index >= '1997-01-03') & (kosdaq.index < sp_kq)][['open', 'high', 'low', 'close']] * ratio_kq
    post_kq = e150[e150.index >= sp_kq][['open', 'high', 'low', 'close']].copy()
    px_kq = kr_bt._px(pd.concat([pre_kq, post_kq]))
    bh_kq = fund.run({'KQ150': px_kq}, pd.DataFrame(1.0, index=px_kq.index, columns=['KQ150']), start='1997-01-03')[0]
    expo_kq_a = kr_res['turtle']['KQ150']['a_base']['periods']['full']['exposure_days']
    r_kq_const0 = expo_kq_a * bh_kq
    r_kq_const_tb = expo_kq_a * bh_kq + (1.0 - expo_kq_a) * fund.cash_daily(bh_kq.index)

    # K200 전체 구간 동일 노출 단순 보유
    kospi = kr_bt._clean(kr_bt._nv('KOSPI'))
    e200 = kr_bt._clean(kr_bt._nv('069500'))
    sp_k2 = pd.Timestamp('2002-10-14')
    ratio_k2 = e200['close'].loc[sp_k2] / kospi['close'].loc[sp_k2]
    pre_k2 = kospi[(kospi.index >= '1990-01-04') & (kospi.index < sp_k2)][['open', 'high', 'low', 'close']] * ratio_k2
    post_k2 = e200[e200.index >= sp_k2][['open', 'high', 'low', 'close']].copy()
    px_k2 = kr_bt._px(pd.concat([pre_k2, post_k2]))
    bh_k2 = fund.run({'K200': px_k2}, pd.DataFrame(1.0, index=px_k2.index, columns=['K200']), start='1990-01-04')[0]
    expo_k2_a = kr_res['turtle']['K200']['a_base']['periods']['full']['exposure_days']
    r_k2_const0 = expo_k2_a * bh_k2
    r_k2_const_tb = expo_k2_a * bh_k2 + (1.0 - expo_k2_a) * fund.cash_daily(bh_k2.index)

    # KQ150 50/200 골든크로스
    gc_k2_pos = (px_k2['close'].rolling(50).mean() > px_k2['close'].rolling(200).mean()).shift(1, fill_value=False).astype(float)
    r_gc_k2 = (gc_k2_pos * bh_k2).loc['1990-01-04':]
    gc_kq_pos = (px_kq['close'].rolling(50).mean() > px_kq['close'].rolling(200).mean()).shift(1, fill_value=False).astype(float)
    r_gc_kq = (gc_kq_pos * bh_kq).loc['1997-01-03':]

    table = {}
    for mkt, k_dict, const0_r, const_tb_r, gc_r in [
        ('K200_1990_2026', kr_res['turtle']['K200'], r_k2_const0, r_k2_const_tb, r_gc_k2),
        ('KQ150_1997_2026', kr_res['turtle']['KQ150'], r_kq_const0, r_kq_const_tb, r_gc_kq),
    ]:
        pa = k_dict['a_base']['periods']['full']
        pb = k_dict['b_base']['periods']['full']
        table[mkt] = dict(
            turtle_a=dict(
                CAGR=pa['CAGR'], ROI=pa['ROI'], MDD=pa['MDD'], Sharpe=pa['Sharpe'],
                win_rate=pa['trades']['win_rate'], payoff=pa['trades']['payoff'],
                exp_pct=pa['trades']['expectancy_pct'], exp_R=pa['trades']['expectancy_R'],
                exposure=pa['exposure_days'], n_trades=pa['trades']['n'],
            ),
            turtle_b=dict(
                CAGR=pb['CAGR'], ROI=pb['ROI'], MDD=pb['MDD'], Sharpe=pb['Sharpe'],
                win_rate=pb['trades']['win_rate'], payoff=pb['trades']['payoff'],
                exp_pct=pb['trades']['expectancy_pct'], exp_R=pb['trades']['expectancy_R'],
                exposure=pb['exposure_days'], n_trades=pb['trades']['n'],
            ),
            bh=dict(CAGR=pa['BH']['CAGR'], ROI=pa['BH']['ROI'], MDD=pa['BH']['MDD'], Sharpe=pa['BH']['Sharpe']),
            same_expo_bh_cash0=dict(
                CAGR=validate.ann_ret(const0_r), MDD=validate.mdd(const0_r),
                Sharpe_irx=validate.sharpe(const0_r),
                Sharpe_rf0=float(const0_r.mean() / const0_r.std() * np.sqrt(252)),
            ),
            same_expo_bh_tbill=dict(
                CAGR=validate.ann_ret(const_tb_r), MDD=validate.mdd(const_tb_r),
                Sharpe_irx=validate.sharpe(const_tb_r),
            ),
            gc_50_200=dict(
                CAGR=validate.ann_ret(gc_r), MDD=validate.mdd(gc_r),
                Sharpe_irx=validate.sharpe(gc_r),
            ),
        )

    for sym in ('GSPC', 'NDX', 'IXIC'):
        pa = tres[sym]['a_base']['periods']['full']
        pb = tres[sym]['b_base']['periods']['full']
        se = fcomp['same_exposure_bh'][sym]['a']['full']
        gc_p = fcomp['golden_cross'][sym]['periods']['full']
        table[f'{sym}_1990_2026'] = dict(
            turtle_a=dict(
                CAGR=pa['CAGR'], ROI=pa['ROI'], MDD=pa['MDD'], Sharpe=pa['Sharpe'],
                win_rate=pa['trades']['win_rate'], payoff=pa['trades']['payoff'],
                exp_pct=pa['trades']['expectancy_pct'], exp_R=pa['trades']['expectancy_R'],
                exposure=pa['exposure_days'], n_trades=pa['trades']['n'],
            ),
            turtle_b=dict(
                CAGR=pb['CAGR'], ROI=pb['ROI'], MDD=pb['MDD'], Sharpe=pb['Sharpe'],
                win_rate=pb['trades']['win_rate'], payoff=pb['trades']['payoff'],
                exp_pct=pb['trades']['expectancy_pct'], exp_R=pb['trades']['expectancy_R'],
                exposure=pb['exposure_days'], n_trades=pb['trades']['n'],
            ),
            bh=dict(CAGR=pa['BH']['CAGR'], ROI=pa['BH']['ROI'], MDD=pa['BH']['MDD'], Sharpe=pa['BH']['Sharpe']),
            same_expo_bh_cash0=dict(
                CAGR=se['const_bh_cash0']['CAGR'], MDD=se['const_bh_cash0']['MDD'],
                Sharpe_irx=se['const_bh_cash0']['Sharpe'], Sharpe_rf0=se['const_bh_cash0']['sharpe_rf0'],
            ),
            same_expo_bh_tbill=dict(
                CAGR=se['const_bh_tbill']['CAGR'], MDD=se['const_bh_tbill']['MDD'],
                Sharpe_irx=se['const_bh_tbill']['Sharpe'],
            ),
            gc_50_200=dict(
                CAGR=gc_p['CAGR'], MDD=gc_p['MDD'], Sharpe_irx=gc_p['Sharpe'],
            ),
        )
    return table


# ================================================================ 민감도 분석 (40·55·70 × 10·20·30 × 1.5·2·3N)
def run_sens(data):
    rows = []
    for sym in ('GSPC', 'NDX'):
        for mode in ('a', 'b'):
            for en in (40, 55, 70):
                for ex in (10, 20, 30):
                    for sn in (1.5, 2.0, 3.0):
                        p = dict(BASE, entry=en, exit=ex, stop_n=sn)
                        s = turtle(data[sym], p, mode=mode, start=START_DATE)
                        mf = fund.metrics(s['r'])
                        mp = fund.metrics(s['r'][s['r'].index >= OOS_SPLIT])
                        ms3 = fund.metrics(s['r'][s['r'].index >= '2015-10-01'])
                        ts = trade_stats(s['trades'])
                        rows.append(dict(
                            product=sym, mode=mode, entry=en, exit=ex, stop_n=sn,
                            base=(en, ex, sn) == (55, 20, 2.0),
                            full_CAGR=mf['CAGR'], full_MDD=mf['MDD'], full_Sharpe=mf['Sharpe'],
                            post2002_CAGR=mp['CAGR'], post2002_MDD=mp['MDD'], post2002_Sharpe=mp['Sharpe'],
                            sub3_CAGR=ms3['CAGR'], sub3_MDD=ms3['MDD'], sub3_Sharpe=ms3['Sharpe'],
                            n_trades=ts['n'], win_rate=ts.get('win_rate'), payoff=ts.get('payoff'), exp_R=ts.get('expectancy_R'),
                        ))
                        log_trial(f'turtle_{sym}_{mode}', p, dict(product=sym, mode=mode, variant='sensitivity'), mf['Sharpe'])
    df = pd.DataFrame(rows)
    df.to_csv(OUT / 'sensitivity.csv', index=False, encoding='utf-8-sig')
    return df


# ================================================================ 검증 프로토콜 (validate.run_all)
def strategy_factory(mode):
    def strategy(params, px, cost_mult=1.0):
        k = next(iter(px))
        s = turtle(px[k], params, cost_mult=cost_mult, mode=mode, start=params.get('start', START_DATE))
        pos = s['held'] if mode == 'a' else s['held'].shift(1).fillna(0.0)
        return s['r'], pos, s['turnover']
    return strategy


def run_validate(data, n_trials):
    out = {}
    for sym in ('GSPC', 'NDX'):
        bench = bh(sym, data, start=START_DATE)
        for mode in ('a', 'b'):
            od = OUT if (sym, mode) == ('GSPC', 'a') else OUT / f'validation_{sym}_{mode}'
            p = dict(BASE, start=START_DATE)
            label = f'터틀 55/20/2N {sym} ({"다음날 시가" if mode == "a" else "장중 돌파"}) 1990~2026'
            res = validate.run_all(
                label, strategy_factory(mode), p, {sym: data[sym]}, bench,
                outdir=str(od), grid=None, n_trials=n_trials, source='paper', time_budget=900,
            )
            out[f'{sym}_{mode}'] = dict(
                verdict=res['auto_verdict'],
                dir=str(od.relative_to(RUN)),
                fails=[x['item'] for x in res['checklist'] if x['status'] == 'FAIL'],
                warns=[x['item'] for x in res['checklist'] if x['status'] == 'WARN'],
            )
            print(sym, mode, res['auto_verdict'])
    return out


# ================================================================ 차트 생성
def charts(data, tres, fcomp):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['font.family'] = 'AppleGothic'
    plt.rcParams['axes.unicode_minus'] = False

    labels = {
        'GSPC': 'S&P 500 (^GSPC, 1990~2026 가격지수)',
        'NDX': '나스닥 100 (^NDX, 1990~2026 가격지수)',
    }
    for sym, lab in labels.items():
        bench = bh(sym, data, start=START_DATE)
        ra = tres[sym]['_sim_a']['r']
        rb = tres[sym]['_sim_b']['r']
        rg = fcomp['golden_cross'][sym]['_sim']['r']
        S = {
            '터틀 (a) 다음날 시가': ra,
            '터틀 (b) 장중 돌파': rb,
            '50/200 골든크로스': rg,
            'Buy&Hold': bench.reindex(ra.index).fillna(0),
        }
        col = {
            '터틀 (a) 다음날 시가': '#1f4e79',
            '터틀 (b) 장중 돌파': '#5b9bd5',
            '50/200 골든크로스': '#c55a11',
            'Buy&Hold': '#888888',
        }
        fig, ax = plt.subplots(3, 1, figsize=(12, 11), gridspec_kw=dict(height_ratios=[3, 1.6, 1.8]))
        for k, x in S.items():
            e = (1.0 + x).cumprod()
            ax[0].plot(e, label=k, color=col[k], lw=1.15)
            ax[1].plot(e / e.cummax() - 1.0, color=col[k], lw=0.95)
        ax[0].set_yscale('log')
        ax[0].axvline(pd.Timestamp('2002-10-14'), color='#c00', ls='--', lw=0.8)
        ax[0].axvline(pd.Timestamp('2015-10-01'), color='#c00', ls=':', lw=0.8)
        ax[0].legend(fontsize=9)
        ax[0].set_title(f'{lab} — 누적 수익(로그), 점선 = 구간 경계(2002-10, 2015-10)')
        ax[1].set_title('낙폭 (Drawdown)')
        ax[1].axvline(pd.Timestamp('2002-10-14'), color='#c00', ls='--', lw=0.8)
        ax[1].axvline(pd.Timestamp('2015-10-01'), color='#c00', ls=':', lw=0.8)

        y = pd.DataFrame({k: (1.0 + x).groupby(x.index.year).prod() - 1.0 for k, x in S.items() if k != '터틀 (b) 장중 돌파'})
        xs = np.arange(len(y))
        w = 0.27
        for i, k in enumerate(y.columns):
            ax[2].bar(xs + (i - 1) * w, y[k] * 100.0, w, label=k, color=col[k])
        ax[2].set_xticks(xs)
        ax[2].set_xticklabels(y.index, rotation=90, fontsize=7)
        ax[2].axhline(0, color='k', lw=0.5)
        ax[2].set_title('연도별 수익률 (%)')
        ax[2].legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(OUT / f'chart_{sym}.png', dpi=110)
        plt.close(fig)


def strip(res):
    return {k: v for k, v in res.items() if not str(k).startswith('_')}


def dump(o, f):
    p = OUT / f if not Path(f).is_absolute() else Path(f)
    json.dump(
        o, open(p, 'w'), ensure_ascii=False, indent=1,
        default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else (None if x is None else str(x)),
    )


def main():
    # 이전 실행의 trial_registry 초기화 (정확한 시도 수 집계 보장)
    for rf in (RUN / 'trial_registry.jsonl', OUT / 'trial_registry.jsonl'):
        if rf.exists():
            rf.unlink()

    data = load_us()
    for k in ('GSPC', 'NDX', 'IXIC'):
        print(k, data[k].index[0].date(), 'to', data[k].index[-1].date(), 'rows:', len(data[k]))

    tres = run_base(data)
    fcomp = run_fair_comparisons(data, tres)
    mstruct = run_market_structure_analysis(data, tres, fcomp)
    kr_us = build_kr_us_comparison(data, tres, fcomp)
    sens = run_sens(data)
    charts(data, tres, fcomp)

    # 표준 산출물: GSPC 터틀 (a) → backtest/metrics.json·equity.png, 나머지는 eval_<sym>_<mode>
    for sym in ('GSPC', 'NDX'):
        for mode in ('a', 'b'):
            s, s2 = tres[sym][f'_sim_{mode}'], tres[sym][f'_sim2_{mode}']
            od = OUT if (sym, mode) == ('GSPC', 'a') else OUT / f'eval_{sym}_{mode}'
            fund.evaluate(
                f'터틀 55/20/2N {sym} ({mode})', s['r'], s['held'], bh(sym, data, start=START_DATE),
                OOS_SPLIT, turnover=s['turnover'],
                extra=dict(note='파라미터 원문 고정(55/20/2N). oos_start=2002-10-14(한국 편 KODEX200 상장일 기준선과 통일).', trades=trade_stats(s['trades'])),
                outdir=od, r_cost2=s2['r'],
            )

    # 총 백테스트 평가 횟수: LOG 기록 수(135) + validate.run_all 내부 S() 평가(4개 조합 × 35회 = 140회) = 275회
    n_trials = len(LOG) + 4 * 35
    vals = run_validate(data, n_trials)

    # 실제 기록된 trial_registry 총 줄 수 확인
    reg_lines_run = len((RUN / 'trial_registry.jsonl').read_text().splitlines()) if (RUN / 'trial_registry.jsonl').exists() else 0
    reg_lines_bt = len((OUT / 'trial_registry.jsonl').read_text().splitlines()) if (OUT / 'trial_registry.jsonl').exists() else 0
    total_logged_trials = reg_lines_run + reg_lines_bt
    print(f'n_trials passed={n_trials}, total_logged_trials={total_logged_trials} (run={reg_lines_run}, bt={reg_lines_bt})')

    dump(vals, 'validation_summary.json')

    rob = dict(
        note='민감도(진입 40·55·70 × 청산 10·20·30 × 손절 1.5·2·3N)는 참고용. 기준안(55/20/2N)은 바꾸지 않았다.',
        sensitivity=sens.to_dict('records'),
        subperiods={sym: {m: {kk: tres[sym][f'{m}_base']['periods'][kk] for kk in ('sub1', 'sub2', 'sub3')} for m in ('a', 'b')} for sym in ('GSPC', 'NDX')},
        cost2x={sym: {m: tres[sym][f'{m}_cost2x']['periods'] for m in ('a', 'b')} for sym in ('GSPC', 'NDX')},
        slippage_note='연 2~3회 매매하는 장기 지수 추세 전략이라 슬리피지 +1~2틱 대신 편도 비용 2배(0.05% → 0.10%) 결과를 함께 수록함.',
    )
    dump(rob, 'robustness.json')

    fcomp_clean = {
        'same_exposure_bh': fcomp['same_exposure_bh'],
        'outlier_dependency': fcomp['outlier_dependency'],
        'golden_cross': {sym: strip(v) for sym, v in fcomp['golden_cross'].items()},
        'portfolio_5050_gspc_ndx': fcomp['portfolio_5050_gspc_ndx'],
    }

    full_results = dict(
        turtle={sym: strip(v) for sym, v in tres.items()},
        fair_comparisons=fcomp_clean,
        market_structure=mstruct,
        kr_vs_us_table=kr_us,
        validation=vals,
        n_trials=n_trials,
        total_logged_trials=total_logged_trials,
    )
    dump(full_results, 'results.json')
    dump(full_results, RUN / 'results.json')
    print('done')


if __name__ == '__main__':
    main()
