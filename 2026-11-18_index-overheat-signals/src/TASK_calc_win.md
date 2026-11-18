# TASK_calc_win — z 기준 기간 3년/5년 독립 재계산 (Antigravity)
목적: out/windows_stats.csv 를 **src/ 를 읽지 않고** PREREG.md 3·4·10·12절만으로 재계산·대조. 코드 calc8/, 결과 calc8/out/. 다른 파일 수정 금지.
데이터: data/kospi_per_pbr_krx.csv, data/agy/kosdaq_per_pbr.csv(PER은 2010-08 이후), data/spdji/shiller_ie_data_2026.xls(S&P PER: 분기 말 E만, 분기 말+3개월부터, Yahoo 월말 종가÷E), data/spx_pbr_q.csv(+3개월 지연), data/yh_*.json, data/agy/fwdpe_img{1_sox,2,3}.csv.
창: 밸류 월간 36(최소 29)/60(최소 48)/120(최소 96). 이격도 = 종가/200일 SMA−1, 일간 756(605)/1260(1008)/2520(2000)일 롤링 z → 월말. 선행 PER 주간 156(104)/260(156)주 → 월말.
평가(PREREG 3·4절): 월말 신호→다음 달 첫 거래일 종가 체결, NW t(log 12개월 lag12, 3개월 lag3), 후반부 t(확정 표본 반), 비중표 전략 편도 5bp Sharpe vs 상수 60%, 순환 플라시보, 확정 에피소드. 판정 J1 t≤−2 & |t|≥3.21 (이격도·선행 PER은 12/3개월 중 하나라도) 등.
보조: 짧은 창 결과를 10년 창(선행 PER은 5년 창) 시작월로 잘라 다시 계산.
특히 확인: KOSDAQ PBR 3년 창 t −3.33 '참고지표'가 재현되는지, 같은 시작월이면 기각되는지.
산출: calc8/out/recalc.csv, diff.md.
