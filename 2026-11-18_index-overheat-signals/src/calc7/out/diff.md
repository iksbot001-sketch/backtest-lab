# diff: recalc vs horizons_stats.csv

- KOSDAQ PER h=1: t_second_half -0.022→-0.459 (Δ-0.437)
- KOSDAQ PER h=3: t_second_half -0.309→-0.608 (Δ-0.299)
- KOSDAQ PER h=9: t_second_half -1.198→-1.403 (Δ-0.206)
- KOSDAQ PBR h=1: t_second_half -1.831→-1.642 (Δ0.189)
- SOX 선행PER h=9: t_second_half -4.883→-5.879 (Δ-0.996)
- SOX 선행PER h=12: nov_t nan→nan (Δnan)
- NASDAQ100 선행PER h=1: t_second_half -0.607→-0.672 (Δ-0.064)
- NASDAQ100 선행PER h=3: t_second_half -1.755→-1.824 (Δ-0.069)
- NASDAQ100 선행PER h=9: t_second_half -4.767→-4.527 (Δ0.240)
- NASDAQ100 선행PER h=12: nov_t nan→nan (Δnan)
- S&P500 선행PER h=3: t_second_half -2.442→-2.325 (Δ0.117)
- S&P500 선행PER h=9: t_second_half -2.332→-2.983 (Δ-0.652)
- S&P500 선행PER h=12: nov_t nan→nan (Δnan)

총 70행, 차이 행 13

## 원인 분석
- 기준 정의(뒤 절반 = floor(n/2)개 관측): 차이 13행은 전부 `t_second_half`(최대 |Δ|≈1.0)와 nov_t 의 nan 표기(비교 도구상 nan≠nan, 실제 일치)뿐.
- 원인: 확정 표본 n이 홀수일 때 '뒤 절반'의 경계. 본 재계산 recalc.csv는 뒤 floor(n/2)개, 기존은 뒤 ceil(n/2)개(중간 관측 포함). 후자로 바꿔 돌린 `recalc_alt_halfsplit.csv`(diff_alt_halfsplit.md)는 nan 표기 3행 외 **전 열 |Δ|≤0.05 일치**.
- PREREG 문구('시간순 반으로 뒤 절반')는 홀수 n 처리를 정하지 않음 → 사전등록 모호성. 결론(판정)은 두 방식에서 동일(verdict 열 불일치 0, n·beta·nw_t·nov_t·에피소드 정수 전부 일치).
- 에피소드 정의: 구간 마지막 체류 월로부터 6개월 초과 후 재진입을 새 에피소드로 셈 → 기존과 정수 전부 일치.
- 가격: 월 첫 거래일 종가, 가격지수. (재계산 중 내 코드의 gmtoffset 단위 버그(시간 vs 초)를 발견·수정함; 최종본은 수정 후.)
- J1 통과 행(nw_t≤−2 & |t|≥3.32): 없음(KOSDAQ PBR h=9 는 J1 통과·J4 통과·J2 실패 → 기존과 같이 '판정 보류'). 
