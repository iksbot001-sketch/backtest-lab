# TASK_calc_fwd — 선행 PER 3건 독립 재계산 (Antigravity)
목적: out/fpe_stats.csv 를 **src/ 를 읽지 않고** PREREG.md 3·4·8절 정의만으로 재계산·대조. 코드 calc3/, 결과 calc3/out/ 에만. 다른 파일 수정 금지.
데이터: data/agy/fwdpe_img1_sox.csv(→ data/yh_SOX.json), fwdpe_img2.csv(→ yh_NDX.json), fwdpe_img3.csv(→ yh_GSPC.json). 주간 date,fwd_pe.
계산: (1) rolling5y: 주간 z=(v−직전 260주 평균)/σ(ddof=1, 최소 156주, 당일 포함), fixed: 전체 평균·σ. 월말 z. (2) 월말 신호→다음 달 첫 거래일 종가 체결, h개월 수익률 = 체결가[t+1+h]/체결가[t+1]−1.
(3) NW t: log(1+r12)~z lag12, log(1+r3)~z lag3, 후반부(신호월 수//2 이후) t. (4) 순열 p: z 순환 이동(12≤k≤n−12)한 NW t 중 실제 t 이하 비율(미확정 수익률 제외 후).
(5) 비중첩 12개월 OLS t 12개 오프셋 중앙·최소·최대. (6) 비중 전략(PREREG 비중표, 편도 5bp) Sharpe, 상수60% Sharpe, 순환 이동 플라시보 백분위. (7) 12개월 수익률 확정 월만으로 과열(z≥1)·저평가(z≤−1) 에피소드(6개월 내 재진입=같은 에피소드).
산출: calc3/out/recalc.csv, calc3/out/diff.md (|차이| >0.1 t·Sharpe, >1%p 수익률·확률, 에피소드 정수차 → 원인 추정). 판정(J1~J4, Bonferroni |t|≥2.64)도 독립적으로 내려 비교.
