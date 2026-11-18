# TASK_calc_disp — 이격도 독립 재계산 (Antigravity)

목적: Claude 결과 out/disp_stats.csv, out/disp_zones.csv 를 **src/ 를 읽지 않고** PREREG.md 3·4·7절(H5) 정의만으로 다시 계산해 대조.
코드 `calc2/`, 결과 `calc2/out/` 에만. 다른 파일 수정 금지. 인터넷 불필요.

데이터: data/yh_{GSPC,NDX,SOX,KS11,KQ11}.json (Yahoo chart JSON: timestamp(UTC초, 날짜로 정규화), indicators.quote[0].close; null 제거, 같은 날짜 중복은 마지막 값).

계산:
1. D = 종가/200일 단순이동평균 − 1 (일간, 200일 미만 구간 제외).
2. rolling: z = (D − 직전 2,520거래일 평균)/표준편차(ddof=1, 최소 2,000일, 당일 포함). fixed: 전체 표본 평균·σ.
3. 월말 z 값 → 다음 달 첫 거래일 종가 체결. h개월 수익률 = 체결가[t+1+h]/체결가[t+1] − 1.
4. NW t: log(1+r12)~z (lag 12), log(1+r3)~z (lag 3). 후반부(표본 절반 이후) t.
5. 구간별 월 수·12개월 평균·상승확률(미확정 수익률은 분모 제외).
6. 비중 전략(PREREG 비중표, 편도 5bp) Sharpe·CAGR, 상수 60% 비교.
7. SOX 차트 검증: 1995-10-16~2026-11-09 D 평균·σ, 2026-11-09 D (차트: 5.8%, ±1σ +24.3%/−12.7%, 현재 −7.5%).

산출: calc2/out/recalc.csv, calc2/out/diff.md (|차이| > 1%p 수익률 또는 > 0.1 t·Sharpe 이면 원인 추정). 모호하면 가정 명시.
