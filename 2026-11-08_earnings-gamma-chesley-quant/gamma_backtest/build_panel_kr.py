"""DART 주요계정 raw → 분기 패널(한국, 연결 우선). 각 공시 한 건에서 분기값 x_t 와 전년 동기 x_{t-4}를 함께 얻는다.
Q1=11013(3개월), Q2=11012(3개월=thstrm), Q3=11014(3개월=thstrm), Q4 = 사업보고서(연간) − 3분기 누적(add).
공시일 = rcept_no 앞 8자리(주의: API가 정정본 접수번호를 줄 수 있어 분포를 점검한다).
스케일: 직전 사업연도말 자산총계(보고서 안 frmtrm 값; 공시 시점에 알려진 값)."""
import pandas as pd, numpy as np
S = '~/agent-fund-data/dart/'
d = pd.read_parquet(S + 'raw_all.parquet')
for c in ['thstrm_amount', 'thstrm_add_amount', 'frmtrm_amount', 'frmtrm_add_amount']:
    d[c] = pd.to_numeric(d[c].astype(str).str.replace(',', '').str.replace('-', '', regex=False).replace('', np.nan), errors='coerce')
# 음수 부호 복원: '-' 제거로 음수가 양수가 되지 않도록 원본으로 다시 처리
raw = pd.read_parquet(S + 'raw_all.parquet')
for c in ['thstrm_amount', 'thstrm_add_amount', 'frmtrm_amount', 'frmtrm_add_amount']:
    d[c] = pd.to_numeric(raw[c].astype(str).str.replace(',', ''), errors='coerce')
d['fy'] = d.bsns_year.astype(int)
# 연결 우선
has_cfs = d[d.fs_div == 'CFS'].groupby(['corp_code', 'fy', 'reprt_code']).size().rename('n').reset_index()
d = d.merge(has_cfs[['corp_code', 'fy', 'reprt_code']].assign(cfs=1), how='left', on=['corp_code', 'fy', 'reprt_code'])
d = d[(d.fs_div == 'CFS') | d.cfs.isna()]
d = d.drop_duplicates(['corp_code', 'fy', 'reprt_code', 'account_nm', 'sj_div'])
key = {'매출액': 'sales', '영업이익': 'op', '당기순이익(손실)': 'ni', '법인세차감전 순이익': 'pbt', '자산총계': 'assets', '자본총계': 'equity'}
d['acc'] = d.account_nm.map(key)
rows = []
for rc, q in (('11013', 1), ('11012', 2), ('11014', 3)):
    x = d[d.reprt_code == rc]
    p = x.pivot_table(index=['corp_code', 'stock_code', 'fy', 'rcept_no'], columns='acc', values=['thstrm_amount', 'frmtrm_amount'], aggfunc='first')
    p.columns = [f'{a[:2]}_{b}' for a, b in p.columns]; p = p.reset_index(); p['q'] = q; rows.append(p)
# Q4
fyr = d[d.reprt_code == '11011'].pivot_table(index=['corp_code', 'stock_code', 'fy', 'rcept_no'], columns='acc', values=['thstrm_amount', 'frmtrm_amount'], aggfunc='first')
fyr.columns = [f'{a[:2]}_{b}' for a, b in fyr.columns]; fyr = fyr.reset_index()
q3 = d[(d.reprt_code == '11014') & d.acc.isin(['sales', 'op', 'ni', 'pbt'])].pivot_table(index=['corp_code', 'fy'], columns='acc', values=['thstrm_add_amount', 'frmtrm_add_amount'], aggfunc='first')
q3.columns = [f'{"c" if a.startswith("th") else "p"}9_{b}' for a, b in q3.columns]; q3 = q3.reset_index()
fyr = fyr.merge(q3, how='left', on=['corp_code', 'fy'])
for a in ['sales', 'op', 'ni', 'pbt']:
    if f'th_{a}' in fyr:
        fyr[f'th_{a}'] = fyr[f'th_{a}'] - fyr.get(f'c9_{a}'); fyr[f'fr_{a}'] = fyr[f'fr_{a}'] - fyr.get(f'p9_{a}')
fyr['q'] = 4; rows.append(fyr[[c for c in fyr.columns if not c.startswith(('c9_', 'p9_'))]])
P = pd.concat(rows, ignore_index=True)
P = P.rename(columns={'th_sales': 'sales', 'fr_sales': 'sales_ly', 'th_op': 'op', 'fr_op': 'op_ly', 'th_ni': 'ni', 'fr_ni': 'ni_ly',
                      'th_pbt': 'pbt', 'th_assets': 'assets', 'fr_assets': 'assets0'})
P['filed'] = pd.to_datetime(P.rcept_no.str[:8], format='%Y%m%d', errors='coerce')
P['tq'] = P.fy * 4 + P.q
P = P.sort_values(['corp_code', 'tq']).reset_index(drop=True)
P['g_ni'] = (P.ni - P.ni_ly) / P.assets0.abs()
P['g_sales'] = (P.sales - P.sales_ly) / P.assets0.abs()
P['g_op'] = (P.op - P.op_ly) / P.assets0.abs()
for g in ['g_ni', 'g_sales', 'g_op']:
    prev = P.groupby('corp_code')[g].shift(1); consec = P.groupby('corp_code')['tq'].diff() == 1
    P['a_' + g[2:]] = np.where(consec, P[g] - prev, np.nan)
P.to_parquet(S + 'panel_kr.parquet', index=False)
print(P.shape, P.corp_code.nunique())
print(P.groupby(['fy', 'q']).size().unstack().tail(14))
print('filed month by q:'); print(P.assign(m=P.filed.dt.month).groupby(['q', 'm']).size().unstack(0).fillna(0).astype(int).to_string())
print(P[['a_ni', 'a_sales', 'a_op']].describe().to_string())
