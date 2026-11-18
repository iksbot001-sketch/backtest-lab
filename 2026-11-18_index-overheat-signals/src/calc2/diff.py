import pandas as pd, numpy as np
a=pd.read_csv('calc2/out/recalc.csv');b=pd.read_csv('out/disp_stats.csv')
m=a.merge(b,on=['market','mode'],suffixes=('_a','_c'))
cols=['nw_t','nw_t3','t_first_half','t_second_half','t3_second_half','strat_cagr','strat_sharpe','strat_mdd','c60_cagr','c60_sharpe','bh_cagr','bh_sharpe','avg_w','placebo_pct','n_months','n','D_now']
out=['# diff: 독립 재계산(calc2) vs Claude(out/disp_stats.csv, disp_zones.csv)\n','가정: 월별 비중=월말 z, 다음달 첫거래일 종가→그 다음달 첫거래일 종가 보유, 비용 편도5bp×|Δw|(초기 진입 포함), 현금 0%, Sharpe=월수익 평균/σ×√12. 절반=신호월 수//2 이후. 플라시보=비중열 순환이동(|이동|≥12개월) 후 Sharpe 분포 중 strat 미만 비율. NW=Bartlett, 소표본 보정 없음, 절편 포함.\n']
flag=[]
for _,r in m.iterrows():
    for c in cols:
        x,y=r[c+'_a'],r[c+'_c']
        d=x-y
        tol=0.1 if ('t' in c.split('_')[-1] or 'sharpe' in c or c in('nw_t','nw_t3')) else 0.01
        if c in('n_months','n'): tol=0.5
        if abs(d)>tol: flag.append((r['market'],r['mode'],c,x,y,d))
out.append(f'비교 {len(m)}행×{len(cols)}지표, 허용오차 초과 {len(flag)}건\n\n|시장|모드|지표|재계산|Claude|차이|\n|--|--|--|--|--|--|')
for f in flag: out.append('|%s|%s|%s|%.4f|%.4f|%+.4f|'%f)
za=pd.read_csv('calc2/out/recalc_zones.csv');zb=pd.read_csv('out/disp_zones.csv')
zm=za.merge(zb,on=['market','zone','mode'],suffixes=('_a','_c'))
zf=[]
for _,r in zm.iterrows():
    for c in ['months','episodes','r3','r6','r12','up12']:
        d=r[c+'_a']-r[c+'_c']
        if abs(d)>(0.5 if c in('months','episodes') else 0.01): zf.append((r['market'],r['mode'],r['zone'],c,r[c+'_a'],r[c+'_c'],d))
out.append(f'\n## 구간표 (months/episodes 정수차, 수익률·확률 1%p)\n비교 {len(zm)}행, 초과 {len(zf)}건\n\n|시장|모드|구간|지표|재계산|Claude|차이|\n|--|--|--|--|--|--|--|')
for f in zf: out.append('|%s|%s|%s|%s|%.4f|%.4f|%+.4f|'%f)
out.append('\n## SOX 차트 검증 (1995-10-16~2026-11-09)\n'+open('calc2/out/sox_check.json').read())
open('calc2/out/diff.md','w').write('\n'.join(out))
print('\n'.join(out))
