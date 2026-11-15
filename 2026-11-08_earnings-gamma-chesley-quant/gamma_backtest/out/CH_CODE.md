<!-- CODE · 모델 gemini-4-argon-medium · 대체 True · 1.8분 -->
```python
"""체슬리투자자문 퀀트 전략 사전등록 시험(CHESLEY_PREREG.md). 사용: python chesley.py <candidates|run>"""
import sys, json, time, gzip, glob, warnings, re
import numpy as np, pandas as pd
from pathlib import Path

warnings.filterwarnings('ignore')
sys.path.insert(0, str(Path.home() / 'agent-fund/lib'))
from dist_report import summary, text

S = Path.home() / 'agent-fund-data'
OUT = S / 'chesley'
OUT.mkdir(parents=True, exist_ok=True)
MODE = sys.argv[1] if len(sys.argv) > 1 else 'run'

# 1. 유니버스 구성 (보통주 필터: 끝자리 0, 스팩·ETF·ETN·리츠 제외)
u = pd.read_parquet(S / 'prices/meta/universe.parquet')
delist = pd.read_parquet(S / 'dart/kind_delisted.parquet')
u_codes = set(u.code.astype(str).str.zfill(6)) | set(delist.code.astype(str).str.zfill(6))

bad_codes = set()
for _, r in u.iterrows():
    c = str(r.code).zfill(6)
    nm = str(r.get('name', ''))
    kd = str(r.get('kind', '')).upper()
    if c[-1] != '0' or '스팩' in nm or '기업인수목적' in nm or any(x in kd for x in ['ETF', 'ETN', 'REIT', '리츠', '스팩', '우']):
        bad_codes.add(c)
for _, r in delist.iterrows():
    c = str(r.code).zfill(6)
    nm = str(r.get('회사명', ''))
    if c[-1] != '0' or '스팩' in nm or '기업인수목적' in nm:
        bad_codes.add(c)

valid_codes = sorted(u_codes - bad_codes)

# 2. 가격 로드 및 상폐 거래정지(volume==0 & open==0) 제거
bm_df = pd.read_parquet(S / 'prices/kr/069500.parquet')
bm_df['date'] = pd.to_datetime(bm_df.date)
bm_df = bm_df[bm_df.close > 0].sort_values('date').set_index('date')
cal = bm_df.index
bm_s = bm_df.close

px_dict = {}
first_dt = {}
last_dt = {}

for c in valid_codes:
    p1 = S / f'prices/kr/{c}.parquet'
    p2 = S / f'prices/kr_delisted/{c}.parquet'
    p = p1 if p1.exists() else (p2 if p2.exists() else None)
    if p is None:
        continue
    d = pd.read_parquet(p)
    if len(d) == 0:
        continue
    d['date'] = pd.to_datetime(d.date)
    d = d.sort_values('date')
    # 거래정지/상폐 직전 정상 거래일까지만 유효 처리
    valid_mask = ~((d['open'] == 0) & (d['volume'] == 0)) & (d['close'] > 0)
    d = d[valid_mask]
    if len(d) == 0:
        continue
    s = d.set_index('date')['close']
    s = s[~s.index.duplicated(keep='last')]
    first_dt[c] = s.index[0]
    last_dt[c] = s.index[-1]
    px_dict[c] = s

px_raw = pd.DataFrame(px_dict).reindex(cal)
# 직전 252거래일 최고가 (당일 포함 252거래일 rolling max, 최소 200거래일)
rmax252 = px_raw.ffill().rolling(252, min_periods=200).max()
is_high_day = (px_raw >= rmax252) & px_raw.notna()

# 거래 불능일에도 직전 정상 종가로 청산 가능하도록 ffill 유지
px = px_raw.ffill()
dates = px.index

# 월별 마지막 거래일 인덱스 매핑
ym_s = pd.Series(dates.strftime('%Y-%m'), index=dates)
me_dates = dates.to_series().groupby(ym_s).last()
all_yms = sorted(me_dates.index)
eval_yms = [ym for ym in all_yms if '2017-01' <= ym <= '2026-10']

# 월중 신고가 달성 여부 (그 달에 실제 거래가 1번 이상 있고 252일 신고가 기록)
high_m = is_high_day.groupby(ym_s).any()

# 3. 재무 데이터 정리 (최초 공시일 filed 기준 point-in-time)
pan = pd.read_parquet(S / 'dart/panel_kr.parquet')
pan['code'] = pan.stock_code.astype(str).str.zfill(6)
pan['filed'] = pd.to_datetime(pan.filed.astype(str), errors='coerce')
pan = pan.dropna(subset=['code', 'fy', 'q', 'filed', 'sales', 'op'])
pan['tq'] = pan.fy.astype(int) * 4 + pan.q.astype(int) - 1
pan = pan.sort_values('filed').drop_duplicates(['code', 'tq'], keep='first')
pan_by_code = {c: g.sort_values('tq').reset_index(drop=True) for c, g in pan.groupby('code')}

# 4. 발행주식수 로드 (EODHD dateFormatted + 60일 <= t)
sh_by_code = {}
for c in px.columns:
    for ext in ['KO', 'KQ']:
        fp = S / f'eodhd/fund/{c}.{ext}.json.gz'
        if fp.exists():
            try:
                with gzip.open(fp, 'rt', encoding='utf-8') as f:
                    js = json.load(f)
                qsh = js.get('outstandingShares', {}).get('quarterly', {})
                recs = []
                for v in qsh.values():
                    dt, sh = v.get('dateFormatted'), v.get('shares')
                    if dt and sh and sh > 0:
                        recs.append((pd.to_datetime(dt) + pd.Timedelta(days=60), float(sh)))
                if recs:
                    recs.sort(key=lambda x: x[0])
                    sh_by_code[c] = recs
            except Exception:
                pass
            break

def get_shares(c, t):
    recs = sh_by_code.get(c)
    if not recs:
        return np.nan
    val = np.nan
    for dt, sh in recs:
        if dt <= t:
            val = sh
        else:
            break
    return val

# 5. 월별 1차 필터 (신고가·상장기간·시총·재무) 및 6개 성장률 계산
cand_rows = []
step_counts = []

for ym in eval_yms:
    t_end = me_dates[ym]
    c_high = high_m.loc[ym]
    high_codes = c_high[c_high].index.tolist()
    n_high, n_age, n_mcap, n_fin = len(high_codes), 0, 0, 0
    for c in high_codes:
        # 월말 시점 이미 상폐된 종목 제외
        if last_dt.get(c, pd.Timestamp.min) < t_end:
            continue
        # 상장 후 5분기(456일) 경과
        if (t_end - first_dt.get(c, t_end)).days < 456:
            continue
        n_age += 1
        # 시가총액 5,000억 이상
        p_close = px.at[t_end, c]
        sh = get_shares(c, t_end)
        if not np.isfinite(p_close) or not np.isfinite(sh) or (p_close * sh) < 5e11:
            continue
        n_mcap += 1
        # 재무 조건 (공시일 <= t_end 인 분기 중 최신 분기 q 기준 연속 5분기 확인)
        g = pan_by_code.get(c)
        if g is None:
            continue
        avail = g[g.filed <= t_end]
        if len(avail) < 5:
            continue
        latest_tq = avail.tq.max()
        sub = avail.set_index('tq')
        if not all((latest_tq - k) in sub.index for k in range(5)):
            continue
        s0, o0 = sub.at[latest_tq, 'sales'], sub.at[latest_tq, 'op']
        s1, o1 = sub.at[latest_tq - 1, 'sales'], sub.at[latest_tq - 1, 'op']
        s4, o4 = sub.at[latest_tq - 4, 'sales'], sub.at[latest_tq - 4, 'op']
        # 최근 5분기 매출·영업이익 적자 없음(> 0) 및 YoY·QoQ 증가
        if any(sub.at[latest_tq - k, 'sales'] <= 0 or sub.at[latest_tq - k, 'op'] <= 0 for k in range(5)):
            continue
        if not (s0 > s4 and o0 > o4 and s0 > s1 and o0 > o1):
            continue
        n_fin += 1
        opm0, opm1, opm4 = o0 / s0, o1 / s1, o4 / s4
        cand_rows.append(dict(
            ym=ym, code=c,
            s_qoq=s0 / s1 - 1, s_yoy=s0 / s4 - 1,
            o_qoq=o0 / o1 - 1, o_yoy=o0 / o4 - 1,
            m_qoq=opm0 - opm1, m_yoy=opm0 - opm4
        ))
    step_counts.append(dict(ym=ym, high=n_high, age=n_age, mcap=n_mcap, fin=n_fin))

cand_df = pd.DataFrame(cand_rows)
step_df = pd.DataFrame(step_counts).set_index('ym')

if MODE == 'candidates':
    cand_df[['ym', 'code']].to_parquet(OUT / 'candidates.parquet', index=False)
    print(f"고유 후보 종목 수: {cand_df.code.nunique()} (총 월별 통과 건수: {len(cand_df)})")
    print(step_df.describe().round(1))
    sys.exit(0)

# 6. DART 공시 필터 (CB/BW, 최대주주변경, 자사주 매입·소각) 및 정정 공시 중복 제거
disc = pd.read_parquet(OUT / 'disclosures.parquet')
disc['code'] = disc.code.astype(str).str.zfill(6)
disc['dt'] = pd.to_datetime(disc.rcept_dt.astype(str), format='%Y%m%d', errors='coerce')
disc = disc.dropna(subset=['code', 'dt', 'report_nm']).sort_values('dt')

def classify_kw(nm):
    nm_clean = re.sub(r'\[.*?\]', '', str(nm)).strip()
    if '전환사채권발행결정' in nm_clean:
        return 'CB'
    if '신주인수권부사채권발행결정' in nm_clean:
        return 'BW'
    if '최대주주변경' in nm_clean:
        return 'SH'
    if '자기주식취득결정' in nm_clean or '소각' in nm_clean:
        return 'TS_BUY' if '자기주식취득결정' in nm_clean else 'TS_BURN'
    return ''

disc['kw'] = disc.report_nm.map(classify_kw)
disc = disc[disc.kw != ''].copy()

# 정정 공시 등 같은 code·같은 핵심어 30일 이내 중복 제거 (최초 공시일 유지)
dedup_rows = []
for (c, kw), g in disc.groupby(['code', 'kw']):
    last_d = None
    for r in g.itertuples():
        if last_d is None or (r.dt - last_d).days > 30:
            dedup_rows.append(r)
            last_d = r.dt
disc_clean = pd.DataFrame(dedup_rows) if dedup_rows else pd.DataFrame(columns=disc.columns)

cbbw_sh = disc_clean[disc_clean.kw.isin(['CB', 'BW', 'SH'])]
ts_disc = disc_clean[disc_clean.kw.isin(['TS_BUY', 'TS_BURN'])]
cbbw_by_code = {c: g.dt.values for c, g in cbbw_sh.groupby('code')}
ts_by_code = {c: sorted(g.dt.tolist()) for c, g in ts_disc.groupby('code')}

# 7. Q1·Q2 월별 최종 종목 선정 (13종목 초과 시 6개 항목 순위 백분위 합 & 동점 규칙 ①~③)
q1_sel = {}
q2_sel = {}
step_df['q1_pass'] = 0
step_df['q1_pick'] = 0
step_df['q2_pick'] = 0

cols_6 = ['s_qoq', 's_yoy', 'o_qoq', 'o_yoy', 'm_qoq', 'm_yoy']
cols_4 = ['s_qoq', 's_yoy', 'o_qoq', 'o_yoy']

for ym, g in cand_df.groupby('ym'):
    t_end = me_dates[ym]
    t_m365 = t_end - pd.Timedelta(days=365)
    t_m5y = t_end - pd.Timedelta(days=365 * 5)
    
    # 최근 1년 CB·BW·최대주주변경 제외
    keep = []
    for r in g.itertuples():
        dts = cbbw_by_code.get(r.code, [])
        if any((t_m365 < pd.Timestamp(d) <= t_end) for d in dts):
            continue
        keep.append(r.Index)
    g1 = g.loc[keep].copy()
    step_df.at[ym, 'q1_pass'] = len(g1)
    
    if len(g1) > 13:
        ranks = g1[cols_6].rank(pct=True, ascending=True)
        g1['score6'] = ranks.sum(axis=1)
        # 동점 규칙 ① 영업이익률 YoY·QoQ 하락 여부 ② 이익률 제외 4개 항목 점수 합 ③ 매출·영업이익 성장률 합
        g1['tie1'] = ((g1.m_qoq >= 0) & (g1.m_yoy >= 0)).astype(int)
        g1['tie2'] = ranks[cols_4].sum(axis=1)
        g1['tie3'] = g1[cols_4].sum(axis=1)
        g1 = g1.sort_values(['score6', 'tie1', 'tie2', 'tie3'], ascending=False).head(13)
    
    q1_codes = g1.code.tolist()
    q1_sel[ym] = q1_codes
    step_df.at[ym, 'q1_pick'] = len(q1_codes)
    
    # Q2: Q1 통과(점수 컷 전 Q1 조건 충족) 종목 중 최근 5년간 자사주 매입·소각 공시 3회 이상
    q2_codes = []
    for c in g.loc[keep, 'code']:
        tdts = ts_by_code.get(c, [])
        if sum(t_m5y < d <= t_end for d in tdts) >= 3:
            q2_codes.append(c)
    q2_sel[ym] = q2_codes
    step_df.at[ym, 'q2_pick'] = len(q2_codes)

print("=== 월별 단계별 통과 종목 수 요약 (평균 / 중앙값 / 최대) ===")
print(step_df.agg(['mean', 'median', 'max']).round(2))

# 8. 수익률 시뮬레이션 함수 (Q1 시점 A/B, 신고가 전체, 무작위 대조, Q2 7개월 보유·연장)
def run_monthly_port(sel_dict, timing='A', cm=1.0):
    cost_rt = 2 * 0.0025 * cm
    m_rets, tr_list = [], []
    for ym in eval_yms:
        idx_m = all_yms.index(ym)
        idx_in = idx_m + 1 if timing == 'A' else idx_m
        idx_out = idx_in + 1
        if idx_out >= len(all_yms):
            continue
        ym_in, ym_out = all_yms[idx_in], all_yms[idx_out]
        d_in, d_out = me_dates[ym_in], me_dates[ym_out]
        rm = bm_s.at[d_out] / bm_s.at[d_in] - 1
        codes = [c for c in sel_dict.get(ym, []) if last_dt.get(c, pd.Timestamp.min) >= d_in and np.isfinite(px.at[d_in, c]) and px.at[d_in, c] > 0]
        if not codes:
            m_rets.append((ym_out, 0.0, rm, 0))
            continue
        rs_list = []
        for c in codes:
            p0, p1 = px.at[d_in, c], px.at[d_out, c]
            rs = p1 / p0 - 1
            net_r = rs - cost_rt
            rs_list.append(net_r)
            tr_list.append(dict(ym=ym, ym_ret=ym_out, code=c, d_in=d_in, d_out=d_out, p0=p0, p1=p1, rs=rs, rm=rm, cost=cost_rt, net=net_r, ex=net_r - rm))
        m_rets.append((ym_out, float(np.mean(rs_list)), rm, len(codes)))
    return pd.DataFrame(m_rets, columns=['ym', 'ret', 'bm', 'n']).set_index('ym'), pd.DataFrame(tr_list)

def run_q2(cm=1.0):
    cost_one = 0.0025 * cm
    # 시점 A 편입: 월 M 선정 -> 월 M+1 말일 종가 매수 -> 147거래일 뒤 또는 연장일(공시일+147거래일) 매도
    active = {}  # code -> dict(i_in, i_out, d_in, p0, ym_sel)
    tr_list = []
    daily_ret = np.zeros(len(dates))
    daily_n = np.zeros(len(dates))
    
    # 월말 인덱스 -> 편입 후보 매핑
    entry_map = {}
    for ym in eval_yms:
        idx_m = all_yms.index(ym)
        if idx_m + 1 < len(all_yms):
            d_in = me_dates[all_yms[idx_m + 1]]
            i_in = dates.get_loc(d_in)
            entry_map[i_in] = (ym, q2_sel.get(ym, []))
            
    for i in range(len(dates)):
        d_cur = dates[i]
        # 1) 보유 종목 일별 수익 반영 및 연장/만기 체크
        if active:
            r_day = []
            to_remove = []
            for c, pos in list(active.items()):
                # 당일 새 자사주 공시 확인 (d_in < 공시일 <= d_cur)
                for td in ts_by_code.get(c, []):
                    if pos['d_in'] < td <= d_cur:
                        i_td = dates.searchsorted(td)
                        pos['i_out'] = max(pos['i_out'], min(i_td + 147, len(dates) - 1))
                p_prev = px.iat[i - 1, px.columns.get_loc(c)]
                p_cur = px.iat[i, px.columns.get_loc(c)]
                r_c = (p_cur / p_prev - 1) if (np.isfinite(p_prev) and p_prev > 0 and np.isfinite(p_cur)) else 0.0
                if i == pos['i_out'] or d_cur >= last_dt.get(c, pd.Timestamp.max):
                    r_c -= cost_one
                    p1 = p_cur
                    rs = p1 / pos['p0'] - 1
                    rm = bm_s.iat[i] / bm_s.iat[pos['i_in']] - 1
                    cost_rt = 2 * cost_one
                    tr_list.append(dict(ym=pos['ym_sel'], ym_ret=d_cur.strftime('%Y-%m'), code=c, d_in=pos['d_in'], d_out=d_cur,
                                        p0=pos['p0'], p1=p1, rs=rs, rm=rm, cost=cost_rt, net=rs - cost_rt, ex=rs - cost_rt - rm))
                    to_remove.append(c)
                r_day.append(r_c)
            daily_ret[i] = float(np.mean(r_day))
            daily_n[i] = len(active)
            for c in to_remove:
                del active[c]
                
        # 2) 월말 종가 신규 편입 (이미 보유 중인 종목 제외)
        if i in entry_map:
            ym_sel, cand_c = entry_map[i]
            new_c = [c for c in cand_c if c not in active and last_dt.get(c, pd.Timestamp.min) > d_cur and np.isfinite(px.at[d_cur, c]) and px.at[d_cur, c] > 0]
            if new_c and i + 1 < len(dates):
                for c in new_c:
                    active[c] = dict(i_in=i, i_out=min(i + 147, len(dates) - 1), d_in=d_cur, p0=px.at[d_cur, c], ym_sel=ym_sel)
                # 신규 편입 비용을 익일 시초에 동일비중 기준으로 반영
                daily_ret[i + 1] -= cost_one * (len(new_c) / len(active))

    # 일별 수익률을 월말 기준으로 묶어 월 수익 계산
    df_d = pd.DataFrame({'ret': daily_ret, 'n': daily_n}, index=dates)
    m_rows = []
    for idx_m in range(len(eval_yms)):
        ym = eval_yms[idx_m]
        idx_in = all_yms.index(ym) + 1
        idx_out = idx_in + 1
        if idx_out >= len(all_yms):
            continue
        ym_in, ym_out = all_yms[idx_in], all_yms[idx_out]
        d_in, d_out = me_dates[ym_in], me_dates[ym_out]
        seg = df_d.loc[(df_d.index > d_in) & (df_d.index <= d_out)]
        r_m = float(np.prod(1 + seg.ret) - 1) if len(seg) else 0.0
        rm = bm_s.at[d_out] / bm_s.at[d_in] - 1
        m_rows.append((ym_out, r_m, rm, float(seg.n.mean()) if len(seg) else 0.0))
    return pd.DataFrame(m_rows, columns=['ym', 'ret', 'bm', 'n']).set_index('ym'), pd.DataFrame(tr_list)

# 9. 비교 기준 및 무작위 대조군 구성
high_all_sel = {ym: high_m.loc[ym][high_m.loc[ym]].index.tolist() for ym in eval_yms}

rng = np.random.default_rng(42)
rand_sel = {}
for ym in eval_yms:
    pool = [c for c in high_all_sel[ym] if last_dt.get(c, pd.Timestamp.min) >= me_dates[ym]]
    k = len(q1_sel.get(ym, []))
    rand_sel[ym] = rng.choice(pool, size=min(k, len(pool)), replace=False).tolist() if (k > 0 and len(pool) > 0) else []

# 10. 포트폴리오 지표 계산 함수
def calc_metrics(name, mdf, trdf):
    r = mdf.ret.values
    b = mdf.bm.values
    ex = r - b
    n_m = len(r)
    cum = np.cumprod(1 + r)
    cagr = cum[-1] ** (12.0 / n_m) - 1 if n_m > 0 and cum[-1] > 0 else np.nan
    mdd = (cum / np.maximum.accumulate(cum) - 1).min() if n_m > 0 else np.nan
    vol = np.std(r, ddof=1) * np.sqrt(12) if n_m > 1 else np.nan
    sharpe = (np.mean(r) * 12) / vol if (vol and vol > 0) else np.nan
    beta = np.cov(r, b, ddof=1)[0, 1] / np.var(b, ddof=1) if n_m > 1 and np.var(b, ddof=1) > 0 else np.nan
    t_ex = np.mean(ex) / (np.std(ex, ddof=1) / np.sqrt(n_m)) if n_m > 1 and np.std(ex, ddof=1) > 0 else np.nan
    
    def sub_stat(mask):
        sub_ex = ex[mask]
        sub_r = r[mask]
        if len(sub_ex) < 2:
            return np.nan, np.nan
        c_sub = np.prod(1 + sub_r) ** (12.0 / len(sub_r)) - 1 if np.prod(1 + sub_r) > 0 else np.nan
        t_sub = np.mean(sub_ex) / (np.std(sub_ex, ddof=1) / np.sqrt(len(sub_ex))) if np.std(sub_ex, ddof=1) > 0 else np.nan
        return c_sub, t_sub

    m_pre = mdf.index <= '2021-12'
    m_post = mdf.index >= '2022-01'
    cagr_pre, t_pre = sub_stat(m_pre)
    cagr_post, t_post = sub_stat(m_post)
    ex_pre = float(np.mean(ex[m_pre]) * 12) if m_pre.sum() else np.nan
    ex_post = float(np.mean(ex[m_post]) * 12) if m_post.sum() else np.nan

    top1_cut = np.nanpercentile(trdf.ex, 99) if len(trdf) > 0 else np.nan
    tr_ex_trim1 = float(trdf.ex[trdf.ex <= top1_cut].mean()) if len(trdf) > 0 else np.nan

    return dict(
        variant=name, n_months=n_m, avg_pos=float(mdf.n.mean()), n_trades=len(trdf),
        cagr=cagr, mdd=mdd, sharpe=sharpe, vol=vol, beta=beta,
        ex_ann=float(np.mean(ex) * 12), t_ex=t_ex,
        cagr_17_21=cagr_pre, ex_17_21=ex_pre, t_17_21=t_pre,
        cagr_22_26=cagr_post, ex_22_26=ex_post, t_22_26=t_post,
        tr_mean_ex=float(trdf.ex.mean()) if len(trdf) else np.nan,
        tr_trim1_ex=tr_ex_trim1
    )

# 11. 8개 사전등록 시험 + 무작위 대조 실행
variants = [
    ('Q1_A_1x', lambda: run_monthly_port(q1_sel, 'A', 1.0)),
    ('Q1_A_2x', lambda: run_monthly_port(q1_sel, 'A', 2.0)),
    ('Q1_B_1x', lambda: run_monthly_port(q1_sel, 'B', 1.0)),
    ('Q1_B_2x', lambda: run_monthly_port(q1_sel, 'B', 2.0)),
    ('Q2_A_1x', lambda: run_q2(1.0)),
    ('Q2_A_2x', lambda: run_q2(2.0)),
    ('BM_HIGH_A_1x', lambda: run_monthly_port(high_all_sel, 'A', 1.0)),
    ('BM_KODEX200', None),
    ('RAND_HIGH_A_1x', lambda: run_monthly_port(rand_sel, 'A', 1.0)),
]

res_rows = []
m_series = {}

for vname, fn in variants:
    if vname == 'BM_KODEX200':
        base_m = m_series['Q1_A_1x']
        mdf = pd.DataFrame({'ret': base_m.bm, 'bm': base_m.bm, 'n': 1.0}, index=base_m.index)
        trdf = pd.DataFrame(columns=['ym', 'ym_ret', 'code', 'd_in', 'd_out', 'p0', 'p1', 'rs', 'rm', 'cost', 'net', 'ex'])
    else:
        mdf, trdf = fn()
        trdf.to_parquet(OUT / f'tr_{vname}.parquet', index=False)
    m_series[vname] = mdf
    row = calc_metrics(vname, mdf, trdf)
    res_rows.append(row)
    if len(trdf) > 0:
        print(f"\n--- [{vname}] 편입 건별 초과수익(ex) 분포 (dist_report) ---")
        try:
            st = summary(trdf.ex.dropna().values)
            print(text(st) if callable(text) else st)
        except Exception as e:
            print(trdf.ex.describe())

# 월별 수익률 시계열 저장 및 결과 CSV 저장
ret_panel = pd.DataFrame({k: v.ret for k, v in m_series.items()})
ret_panel.to_parquet(OUT / 'monthly_returns.parquet')

res_df = pd.DataFrame(res_rows)
res_df.to_csv(OUT / 'chesley.csv', index=False)

# trial_registry 기록 (8건 + 무작위 대조)
reg_path = Path.home() / 'agent-fund/data/trial_registry.jsonl'
reg_path.parent.mkdir(parents=True, exist_ok=True)
with open(reg_path, 'a', encoding='utf-8') as f:
    for x in res_rows:
        rec = {
            'ts': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'study': 'gamma_backtest',
            'trial': f'CHESLEY_{x["variant"]}',
            **{k: (round(float(v), 4) if isinstance(v, (float, np.floating)) and np.isfinite(v) else (None if isinstance(v, (float, np.floating)) else v)) for k, v in x.items()}
        }
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')

pd.set_option('display.width', 260)
pd.set_option('display.max_columns', 25)
disp = res_df.copy()
for c in ['cagr', 'mdd', 'vol', 'ex_ann', 'cagr_17_21', 'ex_17_21', 'cagr_22_26', 'ex_22_26', 'tr_mean_ex', 'tr_trim1_ex']:
    disp[c] = (disp[c] * 100).round(2)
for c in ['sharpe', 'beta', 't_ex', 't_17_21', 't_22_26', 'avg_pos']:
    disp[c] = disp[c].round(2)
print("\n=== 체슬리 퀀트 전략 백테스트 요약 (%) ===")
print(disp.to_string(index=False))
```

### 구현 요약
- **모드 분리**: `python chesley.py candidates` 실행 시 신고가·상장일(456일)·시가총액(5,000억, EODHD 60일 지연)·재무(DART 최초 공시일 기준 5분기 흑자 및 YoY/QoQ 증가) 통과 종목을 `candidates.parquet`에 저장하고, `python chesley.py run` 실행 시 공시 필터와 백테스트 전체를 수행합니다.
- **상장폐지·거래정지 처리**: `volume == 0 & open == 0`인 행을 제거하고 직전 정상 종가를 유지(`ffill`)하여 보유 중 거래정지·상폐 시 마지막 정상 종가로 청산되도록 구현했습니다.
- **공시 중복 제거 및 Q2 연장**: `[기재정정]` 등 접두어를 제거한 핵심어 기준으로 동일 종목·동일 사건 30일 이내 공시를 1건으로 합쳤으며, Q2는 시점 A 편입 후 147거래일 보유 및 보유 중 신규 자사주 매입·소각 공시 발생 시 해당 공시일+147거래일로 만기를 연장해 일별 동일비중 수익률을 월말 기준으로 집계합니다.
