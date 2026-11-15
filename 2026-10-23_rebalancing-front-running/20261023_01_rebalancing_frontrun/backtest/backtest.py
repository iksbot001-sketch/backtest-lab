"""연기금 60/40 리밸런싱 선행매매 백테스트 (spec.json 구현).

원문: Harvey, Mazzoleni, Melone (2025/2026) NBER WP 33554.
실행: ~/agent-fund/venv/bin/python backtest.py

체결: fund.run (t 종가 결정 → t+1 시가 체결, 편도 0.07% + $0.01 틱).
신호는 t 종가까지의 수정종가 수익률만 사용한다 (아래 각 단계에 lookahead 점검 주석).
진단용 종가→종가(원문 타이밍) 결과는 fund.run_returns 로 따로 계산하며 판정에는 쓰지 않는다.
"""
import sys, json, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '~/agent-fund/lib')
import fund
import numpy as np, pandas as pd
from pathlib import Path
from pandas.tseries.holiday import USFederalHolidayCalendar

RUN = Path('~/agent-fund/runs/20261023_01_rebalancing_frontrun')
OUT = RUN / 'backtest'
SPEC = json.load(open(RUN / 'spec.json'))
START = SPEC['sample']['start']            # 2002-09-03
OOS = SPEC['oos_start']                     # 2023-03-20
IS_END = '2023-03-17'
INIT = pd.Timestamp('2002-07-31')           # 가상 포트폴리오 w=0.60 시작일 (월말 마지막 거래일)
TARGET = 0.60
BASE = dict(deltas=('0.0', '2.5'), scale=0.015, window=5, first_leg=+1, bond='IEF', cap=None,
            component='both')
SUBS = {'H1_2002-09~2012-12': ('2002-09-03', '2012-12-31'),
        'H2_2013-01~2023-03-17': ('2013-01-01', IS_END),
        'OOS_2023-03-20~': (OOS, None)}
CRISIS = [('2008-09-01', '2009-03-31'), ('2020-03-01', '2020-03-31')]

PX = {t: fund.us(t) for t in ['SPY', 'IEF', 'TLT']}


# ------------------------------------------------------------------ 달력
def month_positions(idx):
    """각 거래일의 '월 안에서 끝에서 몇 번째(0=마지막 거래일)'와 '처음에서 몇 번째(0=첫 거래일)'.
    거래일 달력은 SPY 인덱스. 데이터 마지막 달(2026-10)은 아직 끝나지 않았으므로 미국 연방공휴일
    달력으로 남은 영업일을 보충해 '마지막 5거래일'을 잘못 표시하지 않게 한다(사전에 알 수 있는 달력 정보)."""
    last = idx[-1]
    me = last + pd.offsets.MonthEnd(0)
    hol = USFederalHolidayCalendar().holidays(last, me + pd.Timedelta(days=1))
    fut = pd.bdate_range(last + pd.Timedelta(days=1), me)
    fut = fut[~fut.isin(hol)]
    ext = idx.append(fut)
    s = pd.Series(1, index=ext); ym = ext.to_period('M')
    from_end = s.groupby(ym).cumcount(ascending=False)
    from_start = s.groupby(ym).cumcount()
    return from_end.reindex(idx), from_start.reindex(idx)


# ------------------------------------------------------------------ 신호
def drift(w, rs, rb):
    return w * (1 + rs) / (w * (1 + rs) + (1 - w) * (1 + rb))


def base_signals(bond):
    """Threshold^δ 행렬과 Calendar 신호. 모두 t 종가까지의 수익률만 사용(t-1 가중치 + t 수익률)."""
    idx = PX['SPY'].index[PX['SPY'].index >= INIT]
    idx = idx[idx.isin(PX[bond].index)]
    rs = PX['SPY']['adj'].reindex(idx).pct_change().values
    rb = PX[bond]['adj'].reindex(idx).pct_change().values
    from_end, from_start = month_positions(idx)
    is_last = (from_end.values == 0)
    deltas = np.round(np.arange(0, 26) * 0.001, 4)        # 0.0% ~ 2.5%
    n = len(idx)
    TH = np.full((n, len(deltas)), np.nan); CAL = np.full(n, np.nan)
    wt = np.full(len(deltas), TARGET); wc = TARGET        # 2002-07-31 (i=0) 에 60% 로 시작
    for i in range(1, n):
        d = drift(wt, rs[i], rb[i]); s = d - TARGET
        TH[i] = s                                          # 리셋 전 이탈치 (B.1)
        wt = np.where(np.abs(s) >= deltas, TARGET, d)      # δ=0 은 매일 리셋
        dc = drift(wc, rs[i], rb[i]); CAL[i] = dc - TARGET # (B.2)
        wc = TARGET if is_last[i] else dc
    TH = pd.DataFrame(TH, index=idx, columns=[f'{d:.3f}' for d in deltas])
    return dict(idx=idx, TH=TH, CAL=pd.Series(CAL, index=idx), from_end=from_end, from_start=from_start,
                rs=pd.Series(rs, index=idx), rb=pd.Series(rb, index=idx))


SIG = {b: base_signals(b) for b in ['IEF', 'TLT']}


def weights(p, sig=None):
    """S1 목표 순노출 w_t (t 종가 기준). 반환: w, wT, wC (모두 t 정보까지만)."""
    sig = sig or SIG[p['bond']]
    lo, hi = p['deltas']
    cols = [c for c in sig['TH'].columns if float(lo) / 100 - 1e-9 <= float(c) <= float(hi) / 100 + 1e-9]
    thr = sig['TH'][cols].mean(1)                                  # 식 (2) 단순평균
    wT = -thr / p['scale']
    cal = sig['CAL']
    win = sig['from_end'] < p['window']                            # 마지막 N 거래일 (마지막날 포함)
    first = sig['from_start'] == 0
    wC = pd.Series(0.0, index=cal.index)
    wC[win] = -np.sign(cal[win])
    # 첫 거래일 다리: 4거래일 전(전월 끝에서 4번째 거래일) Calendar 부호. shift(4) = 과거 값 → lookahead 없음
    wC[first & ~win] = p['first_leg'] * np.sign(cal.shift(4)[first & ~win])
    wC = wC.where(cal.notna(), np.nan)
    if p.get('qe') == 'only':
        wC[~cal.index.to_period('M').month.isin([3, 6, 9, 12]) & ~first] = 0
        wC[first & ~cal.index.to_period('M').month.isin([1, 4, 7, 10])] = 0
    elif p.get('qe') == 'non':
        wC[cal.index.to_period('M').month.isin([3, 6, 9, 12]) & ~first] = 0
        wC[first & cal.index.to_period('M').month.isin([1, 4, 7, 10])] = 0
    if p.get('uncond') is not None:                                # 무조건 창 롱/숏 (TOM 비교용)
        wC = pd.Series(0.0, index=cal.index); wC[win] = p['uncond']; wC[first & ~win] = -p['uncond']
    if p['component'] == 'threshold': w = wT / 2
    elif p['component'] == 'calendar': w = wC / 2
    else: w = (wT + wC) / 2                                        # w_C=0 인 날도 2로 나눔 (문자 그대로)
    if p['cap']: w = w.clip(-p['cap'], p['cap'])
    return w, wT, wC


def W_s1(w, bond):
    return pd.DataFrame({'SPY': w, bond: -w}).fillna(0.0)


def run_engine(W, cost_mult=1.0):
    px = {t: PX[t] for t in W.columns}
    return fund.run(px, W, start=START, cost_mult=cost_mult)


def run_cc(w, bond, with_cost):
    """진단용: 원문 타이밍(t 종가 신호 → t+1 종가-종가 수익). 실제로는 체결 불가능한 상한.
    비용(with_cost): 매일 두 다리의 |Δw| × (편도 0.07% + $0.01/종가) — 엔진과 같은 비용 모형을 종가 체결에 적용."""
    sig = SIG[bond]; idx = sig['idx']
    wp = w.shift(1).fillna(0)
    r = wp * (sig['rs'] - sig['rb']).fillna(0) + fund.cash_daily(idx)   # 달러중립 → 현금 100% 이자
    if with_cost:
        dw = (wp - w.shift(2).fillna(0)).abs()
        cs = PX['SPY']['close'].reindex(idx); cb = PX[bond]['close'].reindex(idx)
        r = r - dw * (0.0007 + 0.01 / cs) - dw * (0.0007 + 0.01 / cb)
    r = r[r.index >= START].copy(); r.iloc[0] = 0
    return fund.run_returns(r, wp[wp.index >= START])


# ------------------------------------------------------------------ 지표 헬퍼
def m(r, bench=None, pos=None):
    return fund.metrics(r, bench, pos)


def slice_(r, a, b):
    s = r[r.index >= pd.Timestamp(a)]
    return s[s.index <= pd.Timestamp(b)] if b else s


def ex_crisis(r):
    mask = pd.Series(True, index=r.index)
    for a, b in CRISIS: mask &= ~((r.index >= a) & (r.index <= b))
    return r[mask]


def brief(r):
    d = m(r)
    return {k: d.get(k) for k in ['Sharpe', 'CAGR', 'MDD', 'vol']} if d else {}


def summary(r):
    out = {'full': brief(r), 'IS': brief(slice_(r, START, IS_END)), 'OOS': brief(slice_(r, OOS, None))}
    for k, (a, b) in SUBS.items(): out[k] = brief(slice_(r, a, b))
    out['ex_crisis_full'] = brief(ex_crisis(r))
    return out


def ols_hc1(y, X):
    X = np.column_stack([np.ones(len(y)), X]); b = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ b; n, k = X.shape
    XtXi = np.linalg.inv(X.T @ X)
    V = XtXi @ (X.T * e ** 2) @ X @ XtXi * n / (n - k)
    se = np.sqrt(np.diag(V)); r2 = 1 - (e @ e) / ((y - y.mean()) @ (y - y.mean()))
    return dict(coef=b.tolist(), se=se.tolist(), t=(b / se).tolist(), n=int(n),
                adj_r2=float(1 - (1 - r2) * (n - 1) / (n - k)))


# ------------------------------------------------------------------ 메인
def main():
    p = dict(BASE)
    w, wT, wC = weights(p)
    W = W_s1(w, 'IEF')
    r1, _, to1 = run_engine(W, 1.0)
    r2, _, _ = run_engine(W, 2.0)
    pos_spy = W['SPY'].shift(1).fillna(0).reindex(r1.index)        # 보유 중인 SPY 순비중 (부호 포함)

    # 벤치마크: SPY 단순 보유 (같은 엔진). 참고용 60/40 정적 배분도 같은 엔진.
    bidx = W.index
    rb_spy, _, _ = run_engine(pd.DataFrame({'SPY': 1.0}, index=bidx))
    r6040, _, _ = run_engine(pd.DataFrame({'SPY': 0.6, 'IEF': 0.4}, index=bidx))
    rb_ief, _, _ = run_engine(pd.DataFrame({'IEF': 1.0}, index=bidx))

    # S2 / S3 (개인용 롱온리)
    W2 = pd.DataFrame({'SPY': (w >= 0).astype(float), 'IEF': (w < 0).astype(float)})
    W2.loc[w.isna()] = [1.0, 0.0]
    cal = SIG['IEF']['CAL']; win = SIG['IEF']['from_end'] < 5
    to_ief = win & (cal > 0)
    W3 = pd.DataFrame({'SPY': (~to_ief).astype(float), 'IEF': to_ief.astype(float)})
    rS2, _, toS2 = run_engine(W2); rS2c2, _, _ = run_engine(W2, 2.0)
    rS3, _, toS3 = run_engine(W3); rS3c2, _, _ = run_engine(W3, 2.0)

    # 진단: 종가→종가
    rcc_g, _ = run_cc(w, 'IEF', False)
    rcc_n, _ = run_cc(w, 'IEF', True)

    # ---------------- 회귀 / F1, TOM 통제, F7
    sig = SIG['IEF']
    y = (sig['rs'] - sig['rb']).shift(-1)                           # 다음 날 (SPY-IEF) 종가-종가 (종속변수만 미래)
    thr = sig['TH'].mean(1); calw = sig['CAL'] * (sig['from_end'] < 5)
    fe_next = sig['from_end'].shift(-1); fs_next = sig['from_start'].shift(-1)
    tom_next = ((fe_next == 0) | (fs_next <= 2)).astype(float)     # 수익일이 마지막 거래일~다음 달 3거래일
    D = pd.DataFrame({'y': y, 'thr': thr, 'calw': calw, 'tom': tom_next}).dropna()
    reg = {}
    for nm, (a, b) in {'IS': (START, IS_END), 'OOS': (OOS, None), 'full': (START, None)}.items():
        d = slice_(D, a, b)
        reg[nm] = ols_hc1(d['y'].values, d[['thr', 'calw']].values)
        reg[nm + '_with_TOM'] = ols_hc1(d['y'].values, d[['thr', 'calw', 'tom']].values)
    for k in reg: reg[k]['vars'] = ['const', 'Threshold', 'Calendar×week4'] + (['TOM_next'] if 'TOM' in k else [])
    dis = slice_(D, START, IS_END)
    dwin = dis[(sig['from_end'].reindex(dis.index) < 5)]
    cneg = dwin[sig['CAL'].reindex(dwin.index) < 0]['y']; cpos = dwin[sig['CAL'].reindex(dwin.index) > 0]['y']
    f7_diff = cneg.mean() - cpos.mean()
    f7_t = f7_diff / np.sqrt(cneg.var() / len(cneg) + cpos.var() / len(cpos))
    f7 = dict(mean_next_cal_neg=float(cneg.mean()), n_neg=int(len(cneg)), mean_next_cal_pos=float(cpos.mean()),
              n_pos=int(len(cpos)), diff=float(f7_diff), welch_t=float(f7_t),
              mean_next_window_all=float(dwin['y'].mean()), mean_next_outside=float(dis[~dis.index.isin(dwin.index)]['y'].mean()))

    # ---------------- 강건성 변형
    variants = {
        'base': {},
        'delta_0-2.0': dict(deltas=('0.0', '2.0')),
        'delta_0.1-2.5': dict(deltas=('0.1', '2.5')),
        'scale_0.012': dict(scale=0.012), 'scale_0.018': dict(scale=0.018),
        'window_4': dict(window=4), 'window_6': dict(window=6),
        'first_leg_0': dict(first_leg=0), 'first_leg_minus': dict(first_leg=-1),
        'bond_TLT': dict(bond='TLT'),
        'cap_1': dict(cap=1.0),
        'comp_threshold_only': dict(component='threshold'),
        'comp_calendar_only': dict(component='calendar'),
        'calendar_only_QE_months': dict(component='calendar', qe='only'),
        'calendar_only_nonQE_months': dict(component='calendar', qe='non'),
        'uncond_window_short_spread': dict(component='calendar', uncond=-1.0),
        'uncond_window_long_spread': dict(component='calendar', uncond=+1.0),
    }
    rob = {'note': SPEC['robustness_plan']['note'], 'variants': {}}
    vr = {}
    for k, ch in variants.items():
        pp = dict(BASE); pp.update(ch)
        wv, _, _ = weights(pp)
        rv, _, tov = run_engine(W_s1(wv, pp['bond']))
        vr[k] = rv
        d = summary(rv); d['params'] = {kk: (list(v) if isinstance(v, tuple) else v) for kk, v in pp.items()}
        d['annual_turnover'] = float(tov.sum() / (len(tov) / 252))
        d['avg_abs_w'] = float(wv[wv.index >= START].abs().mean())
        rob['variants'][k] = d
    rob['variants']['cost_mult_2'] = summary(r2)
    # 진단(판정 미사용): 엔진 타이밍 그대로 비용 0 → 비용 효과와 체결시점 효과를 분리
    r0, _, _ = run_engine(W, 0.0)
    rob['variants']['diag_engine_cost0'] = summary(r0)
    # 진단: 비용 0 엔진 수익을 야간(전일 종가→시가, w_{t-2})과 장중(시가→종가, w_{t-1})으로 분해
    O = pd.DataFrame({t: PX[t]['aopen'] for t in W.columns}).reindex(W.index)
    C = pd.DataFrame({t: PX[t]['adj'] for t in W.columns}).reindex(W.index)
    on = ((W.shift(2).fillna(0)) * (O / C.shift(1) - 1).fillna(0)).sum(1)
    intr = ((W.shift(1).fillna(0)) * (C / O - 1).fillna(0)).sum(1)
    on_cc = ((W.shift(1).fillna(0)) * (O / C.shift(1) - 1).fillna(0)).sum(1)   # 원문 타이밍의 야간 부분
    ann = lambda s: float(s[s.index >= START].mean() * 252)
    rob['diag_return_decomposition_annual_mean'] = dict(
        engine_overnight_w_t_minus2=ann(on), engine_intraday_w_t_minus1=ann(intr),
        cc_overnight_w_t_minus1=ann(on_cc), cc_intraday_w_t_minus1=ann(intr),
        engine_cost_drag=float((r0 - r1).mean() * 252))
    rob['variants']['timing_close_to_close_gross'] = summary(rcc_g)
    rob['variants']['timing_close_to_close_net'] = summary(rcc_n)
    rob['long_only'] = {'S2_full_switch': summary(rS2), 'S2_cost2': summary(rS2c2),
                        'S3_monthend_only': summary(rS3), 'S3_cost2': summary(rS3c2),
                        'SPY_buyhold': summary(rb_spy), '60_40_static': summary(r6040),
                        'IEF_buyhold': summary(rb_ief),
                        'S2_annual_turnover': float(toS2.sum() / (len(toS2) / 252)),
                        'S3_annual_turnover': float(toS3.sum() / (len(toS3) / 252)),
                        'S2_pct_days_IEF': float((W2['IEF'][W2.index >= START]).mean()),
                        'S3_pct_days_IEF': float((W3['IEF'][W3.index >= START]).mean())}
    # 분기말 vs 비분기말 월: S1 일수익을 월말 창 날짜 기준으로 나눠 본 것
    qe_mask = r1.index.month.isin([3, 6, 9, 12])
    rob['S1_returns_by_month_type'] = {'QE_months': brief(r1[qe_mask]), 'nonQE_months': brief(r1[~qe_mask])}
    rob['regression'] = reg
    rob['F7_turn_of_month'] = f7

    # ---------------- 반증 판정
    full = m(r1); oosm = m(slice_(r1, OOS, None)); c2 = m(r2); exc = m(ex_crisis(r1)); cc = m(rcc_g)
    ri = reg['IS']
    F = {}
    F['F1'] = dict(threshold_coef=ri['coef'][1], threshold_t=ri['t'][1], cal_coef=ri['coef'][2], cal_t=ri['t'][2],
                   rejected=bool(not (ri['coef'][1] < 0 and ri['t'][1] <= -2.0 and ri['coef'][2] < 0 and ri['t'][2] <= -2.0)))
    F['F2'] = dict(sharpe_full=full['Sharpe'], rejected=bool(full['Sharpe'] < 0.5))
    F['F3'] = dict(sharpe_oos=oosm['Sharpe'], rejected=bool(oosm['Sharpe'] <= 0))
    F['F4'] = dict(sharpe_cost2=c2['Sharpe'], rejected=bool(c2['Sharpe'] <= 0))
    F['F5'] = dict(sharpe_ex_crisis=exc['Sharpe'], rejected=bool(exc['Sharpe'] <= 0.3))
    F['F6'] = dict(sharpe_engine=full['Sharpe'], sharpe_cc_gross=cc['Sharpe'],
                   rejected=bool(full['Sharpe'] < cc['Sharpe'] / 3 and full['Sharpe'] <= 0.3))
    F['F7'] = dict(diff=f7['diff'], rejected=bool(f7['diff'] <= 0))
    spy_f, spy_o = m(rb_spy)['Sharpe'], m(slice_(rb_spy, OOS, None))['Sharpe']
    s2f, s2o = m(rS2)['Sharpe'], m(slice_(rS2, OOS, None))['Sharpe']
    s3f, s3o = m(rS3)['Sharpe'], m(slice_(rS3, OOS, None))['Sharpe']
    F['F8'] = dict(SPY=[spy_f, spy_o], S2=[s2f, s2o], S3=[s3f, s3o],
                   rejected=bool(not ((s2f > spy_f and s2o > spy_o) or (s3f > spy_f and s3o > spy_o))))
    ws = w[w.index >= START]
    sgn = np.sign(ws); episodes = int(((sgn != sgn.shift()) & (sgn != 0)).sum())
    F['gate'] = dict(n_direction_episodes=episodes, oos_years=round(len(slice_(r1, OOS, None)) / 252, 2))
    rob['falsification'] = F
    json.dump(rob, open(OUT / 'robustness.json', 'w'), ensure_ascii=False, indent=1, default=float)

    extra = dict(
        strategy='S1 SPY(+w)/IEF(-w) 달러중립 롱숏, w=(−Threshold/1.5% + 수정Calendar)/2, 레버리지 상한 없음',
        benchmark='SPY 100% 단순 보유 (같은 엔진). 60/40 정적 배분은 robustness.json long_only 참고',
        pos_definition='evaluate의 pos = 보유 중인 SPY 순비중(부호 포함). n_trades는 SPY 롱 구간(에피소드) 수만 센다. '
                       '방향(롱/숏) 전환 에피소드 전체 수는 n_direction_episodes.',
        n_direction_episodes=episodes,
        avg_abs_w=float(ws.abs().mean()), max_abs_w=float(ws.abs().max()),
        pct_days_abs_w_gt_1=float((ws.abs() > 1).mean()),
        pct_days_long_spy=float((ws > 0).mean()),
        close_to_close_gross=m(rcc_g), close_to_close_net=m(rcc_n),
        ex_crisis=exc, S2=m(rS2, rb_spy), S2_OOS=m(slice_(rS2, OOS, None), rb_spy),
        S3=m(rS3, rb_spy), S3_OOS=m(slice_(rS3, OOS, None), rb_spy),
        BH_60_40=m(r6040, rb_spy),
        falsification={k: v.get('rejected') for k, v in F.items() if isinstance(v, dict) and 'rejected' in v},
        skew_daily=float(r1.skew()))
    res = fund.evaluate('S1 리밸런싱 선행매매 (SPY/IEF 롱숏)', r1, pos_spy, rb_spy, OOS, to1, extra, OUT, r_cost2=r2)

    # 보조 그림: S1 / S2 / S3 / SPY / 종가-종가 진단
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    plt.rcParams['font.family'] = 'AppleGothic'; plt.rcParams['axes.unicode_minus'] = False
    fig, ax = plt.subplots(figsize=(10, 5))
    for nm, rr in [('S1 엔진', r1), ('S1 종가-종가 비용전(진단)', rcc_g), ('S2 롱온리', rS2), ('S3 월말롱온리', rS3),
                   ('SPY', rb_spy), ('60/40', r6040)]:
        ax.plot((1 + rr).cumprod(), label=nm)
    ax.set_yscale('log'); ax.axvline(pd.Timestamp(OOS), color='r', ls='--', lw=.8); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / 'equity_variants.png', dpi=110); plt.close(fig)

    print(json.dumps({'full': res['full'], 'OOS': res['OOS'], 'BH_full': res['BH_full'], 'BH_OOS': res['BH_OOS'],
                      'cost2': res.get('cost2x_full'), 'F': F}, indent=1, default=float, ensure_ascii=False))


if __name__ == '__main__':
    main()
