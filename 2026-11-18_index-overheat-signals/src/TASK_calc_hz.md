# TASK_calc_hz — 수평선 1/3/6/9개월 독립 재계산 (Antigravity)
목적: out/horizons_stats.csv 를 **src/ 를 읽지 않고** PREREG.md 3·4·11절만으로 재계산·대조. 코드 calc7/, 결과 calc7/out/. 다른 파일 수정 금지.
입력: 신호 z는 기존 패널의 'z' 열을 그대로 쓴다(인덱스 YYYY-MM): out/panel_KOSPI_PER.csv, panel_KOSPI_PBR.csv, panel_SP500_PER_SH_lag3.csv, panel_SP500_PBR.csv, panel_KOSDAQ_PER.csv, panel_KOSDAQ_PBR.csv, panel_{SP500,NASDAQ100,SOX,KOSPI,KOSDAQ}_DISP_rolling.csv, panel_FPE_{SOX,NDX,GSPC}_rolling5y.csv. 가격: data/yh_{KS11,GSPC,KQ11,NDX,SOX}.json (조합별 해당 지수).
계산: 체결가 = 각 월 첫 거래일 종가. 신호월 t의 r_h = 체결가[t+1+h]/체결가[t+1] − 1, h=1,3,6,9,12. NW t: log(1+r_h) ~ z, Bartlett lag h. 후반부 t(확정 표본을 시간순 반으로, 뒤 절반, 같은 lag). 비중첩 t(h개 오프셋 OLS t 중앙값, 오프셋당 관측 ≥8). 확정 월만으로 과열(z≥1)/저평가(z≤−1) 에피소드(6개월 내 재진입=같은 에피소드).
판정(h=1,3,6,9): J1 t≤−2 & |t|≥3.32, J2 에피소드 각 ≥3, J3는 판정에 영향 없을 정도면 생략 가능(대신 J1 통과 행만 보고), J4 후반부 t<0. J1·J4 & J2 실패 = 판정 보류.
산출: calc7/out/recalc.csv, diff.md (|Δt| > 0.05, 에피소드 정수차 → 원인).
