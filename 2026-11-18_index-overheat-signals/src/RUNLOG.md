# RUNLOG (Antigravity, TASK_data)

BLOCKED: 인터넷이 막힌 샌드박스이고, data/ 에 요청 대상 4종(KOSDAQ PER/PBR, NDX 밸류에이션, 선행 PER, Fear&Greed)의 원자료가 없다. 
- 확인: CNN F&G 공식 엔드포인트 요청 시 HTTP 418(차단 응답). 우회 금지 지침에 따라 재시도·헤더 위장 안 함.
- data/ 에 있는 것: kospi_per_pbr_krx.csv, spx_pe_m/spx_cape_m/spx_pbr_q, yh_*.json(지수 가격), fred_*. 요청 항목 1~4에 해당하는 PER/PBR/F&G 자료는 없음.
- 값 추정·보간으로 만들지 않음. data/agy/ 에 산출물 없음.
- LESSON HIT: 해당 없음(수집만 하는 과제, 백테스트 설계 없음).
- 요청: 호출자가 KRX [11007] KOSDAQ PER/PBR, NDX 밸류에이션, 선행 PER, CNN F&G를 data/ 에 넣어 주면 재개.
# RUNLOG (calc)
- 재계산 완료: calc/recalc.py, calc/out/{recalc,recalc_zones,recalc_overlay}.csv, diff.md. src 미열람.
- 결론: NW t·전략 지표·r12 일치. up12 정의 불일치(Claude 분모 오류 의심) 보고.
- LESSON HIT: 확률 분모에 미완결 선행수익 포함 금지.

# RUNLOG (review, Antigravity)
- 검토 범위: `PREREG.md`, `RESULTS.md`, `src/{core,overlay}.py`, `out/*.csv`, `out/research.md`, `calc/out/diff.md`, `data/*`. 기존 파일 수정 없이 `review/REVIEW.md`만 작성.
- LESSON HIT:
  - **시계열 정합·지연(`spx_pe_m` 보간 누출, `spx_pbr_q` 3분기 결측)**: `spx_pe_m.csv`는 Shiller 분기 EPS 선형보간이라 `+1m` 지연으로 부족(`SP500 PER` 후반부 t: lag1 `+2.82` → lag4 `+0.79`). `spx_pbr_q.csv`는 `2026-03/06/09` 결측으로 9개월 `5.39` 동결.
  - **에피소드 군집(`SP500 PBR z<=-1 & VIX>=30`)**: 3회로 집계됐으나 실제 `2008-09~2011-12` 단일 거시 국면에 전량 집중(최근 15년 0회).
  - **LOYO·변환 민감도(`KOSPI PBR`)**: 전체 `nw_t=-1.52`이나 2025 제외 시 `-3.13`, 원수준 회귀 시 `-2.76`. 반면 비중 전략은 `c60` 대비 CAGR·MDD 모두 열위.
  - **가격 vs 총수익·무위험 0%**: 현금 0% 가정 및 배당 제외 확인(DFF 반영 초과수익 Sharpe 재검산 완료).
- 주요 수치 불일치 적발: `RESULTS.md:40` S&P500 `FF-10y>=+1%p` `up12` `66%` 오기(실제 `out/overlay.csv` `76.1%`), `RESULTS.md:38` `FF 수준` 범위에서 `KOSDAQ -0.766` 누락, `RESULTS.md:21·43` `2026-11-04` KRX(`z=+1.07`)와 `2026-11-18` 지수(`5,060`) 혼용(`5,060` 기준 내재 PBR `z=+0.56` 중립), `PREREG`의 `2016~2026` 별도 하위기간 누락.
- 결론: `review/REVIEW.md` 마지막 줄 `PASS_WITH_NOTES`.

## Claude 2026-11-18
- 1차: core.py(PER/PBR z 4건), overlay.py(VIX·F&G·FF). 지연 +1 민감도.
- 재계산(Antigravity bt_calc): t·전략 일치. up12 분모 버그 발견 → 수정. LESSON HIT(신규): 확률 지표 분모에 미완결 선행수익 포함 금지.
- 레드팀(Antigravity bt_review): PASS_WITH_NOTES. RESULTS 수치 3건 정정(66%→76%, KOSDAQ t 범위, 현재 KOSPI 기준일), 사후 검정 추가.
- 시도 장부: 1차 4건 + 지연 4건 + 사후(원수준 4, ex-2025 4, 2016~ 4, SPX PER 지연 4종, VIX 위기제외 3, F&G 공식구간 3) — 사후는 판정에 쓰지 않음.

## Claude — KOSDAQ 추가 (2026-11-18)
- KRX [11007] 개별지수 코스닥, 사용자 Chrome 로그인 세션에서 연도별 JSON 조회 → data/agy/kosdaq_per_pbr.csv (월말 254행, 2005-10~2026-11-17). Yahoo KQ11 월말 종가와 1% 이상 차이 0건(11월 부분월 제외).
- KOSDAQ PER 2010-08 이전 제외(결측·수백 배). core.py 0/1개월 지연, overlay.py 재실행. 기존 4개 결과 불변 확인.
- 1차 판정 시도 +2(KOSDAQ PER/PBR, PREREG 8개 중 남은 2개). KOSDAQ PBR: t −4.31/−4.22, 후반 −2.62, Sharpe 0.31>0.23, 플라시보 82% → 참고지표.

## Antigravity calc_disp 2026-11-18
- 이격도 독립 재계산(calc2/, src/ 미열람). 핵심 t·Sharpe·CAGR 일치, 차이는 표본 첫 달/절반 분할 경계 1개월. SOX 차트 5.8/+24.3/−12.7/−7.4% 재현. 상세 calc2/out/diff.md. LESSON HIT: 없음(신규: 표본 시작월·절반 분할 규칙을 PREREG에 명시).
- 전략 월수익은 out/returns 규칙 대신 calc2/out/ret_<시장>_<모드>.csv (date,ret 월간). 격자 시험 없음(파라미터 고정).

## Antigravity digitize 2026-11-18
- 사진 차트 4종 디지털화 완료: [digitize.py](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/digitize/digitize.py), [REPORT.md](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/digitize/REPORT.md).
- 출력(W-FRI, 520행 `2016-11-25~2026-11-06`): `data/agy/fwdpe_img1_sox.csv`, `data/agy/fwdpe_img2.csv`, `data/agy/fwdpe_img3.csv`, 검증 `digitize/out/fwdpe_img4_sox_check.csv`.
- 보정·검증 결과: 격자 RMS `0.032~0.071x`, 연도 눈금 최대 잔차 `3.8~5.8일`, 독립 기준선(`+1σ/평균/−1σ`) 잔차 `≤0.07x`. `img1` vs `img4` 겹침 520주 상관 `0.99531`, 평균 오차 `+0.0469x`(RMS `0.412x`).
- ±0.5배 초과 항목(2건): `img1` 마지막 값(`14.937 @ 2026-11-06` vs `14.4 @ 2026-11-17`, `+0.537`)·`img2` 마지막 값(`19.454 @ 2026-11-06` vs `18.9 @ 2026-11-09`, `+0.554`) — 모두 말단 급락 구간 일자 차이 및 녹색 마커 가림 때문이며, 녹색 점 중심 자체는 각각 `14.357`, `18.877`로 표기값과 0.05x 이내 일치.
- LESSON HIT: 임의 스케일 조정 금지 및 독립 기준선·교차 사진(`img4`) 검증 준수; 2D 사영 호모그래피에서 좌/우 수직선 동시 제약 미적용 시 `img3`의 `h3[1]` 왜곡(20일 시차) 발생을 확인하고 우측 화면 베젤 직선 결합으로 해결.
- 판정: 사용 가능 (img1: SOX) / 사용 가능 (img2) / 사용 가능 (img3).


## Antigravity review2 2026-11-18
- 검토 범위: `PREREG.md`(4·7절), `src/{disparity,fwdpe,report_data}.py`, `src/report_template.html`, `out/disp_*.csv`, `out/fwdpe_*.csv`, `out/report.json`, `out/panel_KOSDAQ_PBR.csv`, `calc2/out/diff.md`, `digitize/REPORT.md`, `RESULTS.md`. 기존 파일 수정 없이 [REVIEW.md](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/review2/REVIEW.md)만 작성.
- LESSON HIT:
  - **겹치는 12개월 수익률·유한표본 NW 편향(`KOSDAQ PBR`)**: 유효 `r12` 146개월(12.2년)에서 NW `t=-4.31`이나, 비중첩 12개월 OLS t값(12개 오프셋)은 `-1.32~-2.43`(중앙 `-2.02`, 0/12 Bonferroni 통과).
  - **에피소드 부족·미완결 포함(`KOSDAQ PBR`, `fwdpe`)**: `KOSDAQ PBR` 저평가 `3회` 중 `2026-07` 이후 `r12=NaN`으로 완결 에피소드는 2건(`2022-09`, `2024-09`), `z <= -2` 0회. `SOX` 선행 PER `z >= 1` 1회.
  - **다중 비교·선택적 판정(`report_data.py`)**: `best = min(ts)`로 이격도 12·3개월 중 더 음수 쪽만 선택(`SP500_DISP` `+0.76` 선택 및 `J4 실패: 후반부 t -0.74` 문구 모순), `'판정 보류'` 분기 누락, `2016~2026` 이격도 하위기간 누락, `core.py` 절반 분할(`len(res)//2`)이 `r12=NaN` 13개월을 포함해 비대칭 분할.
  - **미완결 부분월·기준일 혼용**: `2026-11` 부분월이 `zones` 월수 합계에 들어가 `n_months`와 2개월 불일치; `report.html` 헤더(`11-18`) 아래 `KOSPI`(`11-04` KRX)·`KOSDAQ`(`11-17` KRX) 시점 혼재; `fwd` 카드 `note`와 `desc` `z_now` 불일치; `SOX_DISP` `note`의 비공개 `15.6%/22.1%` 수치 불일치; `RESULTS.md`에 v2 미반영.
- 결론: `review2/REVIEW.md` `Verdict: CONDITIONAL`, 마지막 줄 `PASS_WITH_NOTES`.

## Claude — v2 (2026-11-18 저녁)
- PREREG 7절 추가(결과 전): H5 이격도 5지수×2수평선=10건, H6 선행 PER 디지털화 서술, H7 SOX 밸류 검증 불가.
- src/disparity.py(0·1개월 지연), src/fwdpe.py, src/report_data.py, src/report_template.html → report.html 게시.
- Antigravity: TASK_digitize(사용 가능 3/3), TASK_calc_disp(일치), TASK_review2(PASS_WITH_NOTES) → KOSDAQ PBR 참고지표→판정 보류, 판정 로직·문구 수정.
- 시도 +10(이격도 1차) +2(지연) +2(고정 방식 비교) +3(선행 PER 서술) +1(SOX 일간 이벤트 탐색).

## Antigravity review3 2026-11-18
- 검토 범위: `PREREG.md` 8절, `src/fwdpe_test.py`, `src/report_data.py`, `out/fpe_stats*.csv`, `out/panel_FPE_*.csv`, `out/report.json`, `digitize/REPORT.md`, `digitize/out/fwdpe_img4_sox_check.csv`. 기존 파일 수정 없이 [REVIEW.md](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/review3/REVIEW.md)만 작성.
- LESSON HIT:
  - **겹치는 12개월 수익률·소표본 Bartlett NW 분산 붕괴**: `core.py`의 `half=2023-05`(미확정 13개월 포함 분할)로 인해 후반부 `n=30`개월(`d1` `n=29`)에서 `lag=12` NW 분산이 미보정 OLS 분산보다 작아지며(`SOX V12/V0=0.551`, `NDX d1 V12/V0=0.441`) `t_second_half=-7.750`으로 과장됨. `2022-11~2025-10` 36개월 재계산 시 `-4.453`이며, `report_data.py:99`의 `36개월` 표기 오기 적발.
  - **사후 고정 기준선 누출(`NDX fixed` 플라시보 92.6%)**: `2020~2021` 버블을 포함한 10년 고정 평균(`23.69x`)으로 `2016~2019`를 사후 저평가(`avg_w=0.70~0.80`) 분류해 발생한 착시(`2017 +6.72%p`, `2019 +8.81%p`). `2019-12~2026-10` 동일 구간 절단 시 `Sharpe 0.903 < 0.908`, 플라시보 `61.0%`로 소멸.
  - **롤링 창·디지털화 잡음·절단·비용 2배 민감도**: 2·3·4·5·7년·확장 창 10종·`ERP`, `img4` 치환, `±0.3x`/`AR(1)` 잡음 1,200회, `2023-06-30` 절단(`max|dz|=0.0`), `+1개월` 지연, 비용 2배(`10bp`) 모두에서 3건 기각 결론 불변(`J1`/`J3` 통과 0건).
- 결론: `review3/REVIEW.md` `Verdict: PASS`, 마지막 줄 `PASS_WITH_NOTES`.


## Antigravity calc_fwd 2026-11-18
- 선행 PER 3건 독립 재계산 완료(`src/` 미열람): [recalc.py](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/calc3/recalc.py), [recalc.csv](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/calc3/out/recalc.csv), [diff.md](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/calc3/out/diff.md).
- 일치: 전체 12m/3m `nw_beta`, `nw_t`, `nw_t3`, `perm_p12`, `perm_p3`, `nov_t_*`, `c60_*`, `bh_*`, `placebo_pct`, `ep_*_res` 오차 ≤ 1e-12로 완전 일치.
- 차이(`|Δt|>0.1`·정수차): (1) 전/후반 분할 시점 차이 — `out/fpe_stats.csv`는 `r12=NaN` 12개월을 포함한 전체 신호월//2(`2023-05` / `2021-11`)로 분할해 `SOX rolling5y` 후반 t가 `-7.75` vs `-4.45`, (2) `SOX fixed` `ep_cold` `4` vs `3` — 미완결 부분월 `2026-11`(`z=-1.018`) 포함 여부(`ep_cold_res`는 양쪽 모두 `3`으로 일치).
- 독립 판정(Bonferroni `|t|≥2.64`): 1차(`rolling5y`) 3종 모두 J1·J2·J3 미통과 → **판정 보류(에피소드<3)**(실질 기각).
- LESSON HIT:
  - **미확정 수익률·부분월 포함 금지**: `out/fpe_stats.csv`의 절반 분할(`2023-05`/`2021-11`)이 `r12=NaN` 월을 포함해 비대칭 분할했고, `SOX fixed` `ep_cold`에 `2026-11` 부분월이 포함됨 → 재계산은 유효 확정 표본(`n_res//2`)과 완결 신호월만 사용.
  - **겹치는 12m 수익률 + 에피소드 부족**: NW t, 순열 p, 비중첩 OLS 중앙 t(`-0.22~+0.07`) 모두 비유의, 확정 에피소드 `< 3`으로 판정 보류.

## Claude — v3 (2026-11-18 밤)
- PREREG 8절(결과 전) → src/fwdpe_test.py: 선행 PER 3건 5년 롤링 z, 6건 Bonferroni 2.64 → 3건 기각. calc3 일치, review3 PASS.
- core.py/disparity.py/fwdpe_test.py 전·후반 분할을 확정 수익률 기준으로 수정(레드팀 2·3차) → 전 조합 재실행, 판정 불변.
- 시도 +6(선행 PER 1차) +6(지연·고정 비교).

## Antigravity calc_daily 2026-11-18
- 일간·단기 검증 독립 재계산 완료(`src/` 미열람): [recalc.py](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/calc4/recalc.py), [recalc_events.csv](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/calc4/out/recalc_events.csv), [recalc_strategy.csv](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/calc4/out/recalc_strategy.csv), [recalc_pbr_approx_check.csv](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/calc4/out/recalc_pbr_approx_check.csv), [diff.md](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/calc4/out/diff.md).
- 대조 결과: 임계치(`|Δ|>0.2%p` 수익, `>0.02` p, `>0.05` Sharpe, 이벤트 수 차이) 초과 불일치 **0건**.
  - `daily_pbr_approx_check.csv` 5개 지표(`n=6040`, `mape=0.007056`, `p95=0.026223`, `z_corr=0.997584`, `z_mae=0.054621`) 오차 `0.0`.
  - `daily_events_test.csv` 84행 `n/first/last/mean/base/excess/hit/excess_2nd` 완전 일치(`0.0`), `p` 최대 차이 `0.0140`(10,000회 무작위 추출 시드 차이).
  - `daily_strategy.csv` 7개 지표 `Sharpe` 최대 차이 `2.0e-5`, `placebo` 최대 차이 `0.0`(5bp) / `0.0038`(10bp), `KOSDAQ_PBR` `z_now` 차이 `+0.0111`.
- 독립 판정(D1~D4, `p < 0.0036`, `n ≥ 8`): 1차 14건 중 D1·D3 통과 0건 → **12건 기각, 2건 판정 보류(`KOSPI_PBR sell` n=4, `KOSDAQ_PBR buy` n=7)**.
- LESSON HIT:
  - **겹치는 수익률·미확정 수익률 제외·직전 월말 엄격 적용**: 이벤트 60거래일 독립화 및 `t+1+h < N` 미완결 제외, 월말 PBR/종가 비율의 엄격한 직전 월말(`date < d`) 적용을 확인.
  - **노출 일치 벤치마크·순환 이동 플라시보·회전율×비용 점검**: 7개 일간 전략 모두 회전율 1.96~3.27x/yr(연 비용 9.8~16.4bp) 수준이나, 상수 노출 벤치마크 및 순환 이동 플라시보 90% 기준을 모두 미달.

## Antigravity review4 2026-11-18
- 검토 범위: `PREREG.md` 9절, `src/daily.py`, `src/report_data.py`, `out/daily_*.csv`, `data/*`. 기존 파일 수정 없이 [REVIEW.md](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/review4/REVIEW.md)만 작성.
- LESSON HIT:
  - **변동성 군집·i.i.d. 귀무분포 과소추정**: `daily.py` 무작위 날짜 추출(`p_iid`)은 `-1σ/-2σ` 이벤트의 고변동 국면 집중(`ev_sd/pool_sd = 1.12~2.29x`)을 무시함. 이벤트 표본 `t`검정·블록 부트스트랩(`b=60·252`)·변동성 분위 매칭 재계산 시 `KOSDAQ_PBR -1 buy (n=7)` `p=0.0293 → 0.060~0.087`, `SOX_DISP -2 (n=7)` `0.0133 → 0.055~0.170`.
  - **임의 `GAP=60` 경계 및 미확정 손실 누락(`KOSDAQ_PBR`)**: `2026-07-20` 이후 58거래일째인 `2026-10-15`(`r20=-12.75%`)가 `GAP=60`에 2일 차이로 제외되고 5일 뒤 `2026-10-22`(11-18까지 `-12.82%`, `r20=NaN`)가 잡혀 `n=7` 통계에서 누락(`GAP=20` 시 `+0.79%p, p=0.371`). `LOEO`에서도 7건 중 4건에서 1건만 빼면 `p>0.05`.
  - **미래 정보·체결 시차·근사 점검**: `2023-06-30` 절단 재계산 전 지표 `max|dz|=0.0`, `KOSDAQ_PBR` 월말 비율 근사(`M-1`) 누출 없음(`KOSPI` 교차 검증에선 근사가 실제 일간 PBR 대비 Sharpe `0.469→0.496`, `-1 buy` `+1.01%p` 미화). `daily.py:63` `tc`의 `shift(-1)` 시차 오기 적발(판정 영향 `0`).
  - **비용·회전율·반대 방향 추세 지속**: 무비용(`0bp`)에서도 6/7 지표가 `const_sharpe` 열위(`trades` `53~62%`가 5일 내 경계 왕복). `+1σ` 매도 반대 방향 상승(`NASDAQ100_DISP h=20 +2.15%p`)도 `1-p_iid=0.056`으로 Bonferroni(`0.0036`) 비유의 및 `2020`·`1999` 의존(`KOSPI_DISP`는 `-1.58%p`).
- 결론: `review4/REVIEW.md` `Verdict: PASS`, 마지막 줄 `PASS_WITH_NOTES`.

## Claude — v4 일간 (2026-11-18 밤)
- PREREG 9절(결과 전) → src/daily.py. 1차 14건 통과 0. calc4 일치, review4 PASS_WITH_NOTES → '추세 지속' 해석 완화, KOSDAQ PBR 매수 p 0.029 단일 사건 의존 명시.
- 시도 +14(1차) +70(2차: h 5·60, ±2σ) +7(10bp).

## Antigravity review5 2026-11-18
- 검토 범위: `PREREG.md` 10절, `src/spx_pe_shiller.py`, `out/spx_pe_shiller_*.csv`, `out/panel_SP500_PER_SH_*.csv`, `out/panel_SP500_PER.csv`, `data/spdji/shiller_ie_data*.xls`, `data/spx_{pe,cape}_m.csv`, `RESULTS.md`. 기존 파일 수정 없이 [REVIEW.md](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/review5/REVIEW.md)만 작성.
- LESSON HIT:
  - **분기 말 실측·발표 지연(`lag=3`) 및 판본 수정 검증**: `shiller_ie_data.xls`(2023-09 판) vs `shiller_ie_data_2026.xls`(2026-11 판) 대조 시 1871~2023-03 1,827개월 `E` 수정 `0`건(`2023-06`만 `-0.16`, `-0.088%`). `2026-09` 추정/잠정치(`295.5184`)는 `lag=3`에서 `2026-12` 적용이라 현 백테스트(`~2026-11`) 미포함(`lag=2`는 사용). `lag=0~6`, `delay=0~1` 모두 기각 불변.
  - **`multpl` 출처 및 상관 `0.764`·차이 `4.04`배 원인**: `spx_pe_m.csv`는 `shiller` 월간 보간 `P/E`와 상관 `0.9997`(차이 `0.056`배)인 동일 계열이며, `lag=1` 보간 vs `lag=3` 계단 지체 차이(`2008~2010` GFC 기간 `2009-11` `103.77`배 차, 제외 시 상관 `0.903`·차이 `1.95`배)가 주원인. 보간 제거 시 기존 `multpl`의 `0.666 > 0.633` 전략 우위와 후반부 `+2.60` 착시가 소멸(`0.471 < 0.516`, `+0.12`).
  - **대안 지표·장기 월평균가(`Working 1960`) 한계**: `Operating PER`은 `data/` 부재로 검증 불가. `CAPE`/`TR_CAPE`/`-E/P`/`log(PER)`/`PER<=50`/일드갭, `1990~` 워밍업, `1908~` 장기(가격지수·총수익 `nw_t=-1.01`, `0.691<0.744`) 모두 기각. `PER_SH_long`은 월평균가 평활화(1개월 자기상관 `+0.197`, 변동성 `-21.7%`) 및 `dd12=NaN` 한계 존재.
  - **에피소드 수·문구 정정**: `PER_SH_lag3` 확정 저평가 에피소드 `2회 < 3`(J2 미충족) 병기 및 `RESULTS.md`/`report_data.py`의 구버전 `+2.82`·`multpl` 서술 전면 교체 필요.
- 결론: `review5/REVIEW.md` `Verdict: PASS`, 마지막 줄 `PASS_WITH_NOTES`.

## 2026-11-18 20:45 TASK_calc_spx (Antigravity)
- calc5/recalc.py 로 PREREG 3·4·10절만으로 독립 재계산 → calc5/out/recalc.csv, diff.md. src/ 미열람.
- LESSON HIT: 미확정 12개월 수익률 달을 에피소드 수에서 제외 → Claude ep_hot가 1씩 많음(미확정 2026 과열월 포함). 확정 기준 5/6/4/19.
- LESSON HIT: 지연(+1개월) 변형, 순환 이동 플라시보, 노출 일치(상수 60%) 벤치마크 모두 재현.
- 결과: NW t·Sharpe·CAGR·MDD·z 전부 일치(|Δ|<1e-6). 라벨(start/n_months/half) 1개월, n_placebo 1개 차이만(diff.md). 판정 5행 모두 기각, Claude와 동일 결론.
- 모호점·가정은 calc5/out/diff.md 에 기재(QUESTIONS_calc.md는 수정 금지라 건드리지 않음).

## Claude — v5 S&P500 PER 출처 교체 (2026-11-18 밤)
- S&P DJI EPS 파일 404(로그인 후 포함), buyback 파일 13개 분기 → shillerdata.com ie_data.xls. PREREG 10절 → src/spx_pe_shiller.py. 기각 유지. calc5 일치, review5 PASS_WITH_NOTES → 문구 교체.
- 리포트/블로그 가운데점(·) 전부 쉼표·슬래시로(사용자 지시).
- 시도 +1(1차 대체) +4(지연·장기).
- 탐색: hindsight_compare.py (고정 vs 롤링 14개, 판정 아님). 시도 +14.

## Antigravity calc_hindsight 2026-11-18
- 독립 재계산(calc6/, src/ 미열람): 6조합 × {rolling, fixed, fixed_cut, fixed_cutstats, expanding}. 산출 calc6/out/{recalc.csv,diff.md,table.md,kospi_pbr_diag.txt,ret_*.csv}. 격자 시험 없음(파라미터 고정, 변형 5방식 전부 recalc.csv).
- src 대조: 12행 NW t·후반부 t·에피소드·판정 전부 일치. 플라시보만 ≤0.019 차(원인 미확정, 판정 불변). KOSPI 체결가는 ^KS11이어야 일치(KRX 종가는 t 0.01 차).
- 결론: fixed KOSPI PBR은 J1~J4 모두 통과 재현. 그러나 같은 시작월로 자르면 J2 실패(과열 에피소드 1) → 판정 보류. t 증가(−1.5→−2.8)는 미래 정보가 아니라 추세 비제거(expanding도 −2.82). J1 여유 0.03.
- LESSON HIT: 표본 시작월·워밍업 차이가 판정을 바꿈(에피소드 수 의존); 롤링 vs 고정은 디트렌딩 정의 차이로 확인; 과열/저평가 에피소드는 정의에 민감 → 에피소드 <3은 판정 보류 원칙 유지; J1 경계(−2.76 vs 2.73) 근처는 시그널 주장 금지.
- 탐색: expanding_compare.py, Antigravity calc6(고정·잘린 고정·누적 평균). 시도 +18+32.

## calc7 (TASK_calc_hz, Antigravity)
- LESSON HIT: 수평선 다중 비교(56 검정, |t|≥3.32), 겹침 수익률(NW lag=h), 미확정 수익률 제외 → 반영함.
- 코드 calc7/recalc7.py (src/ 미열람), 결과 calc7/out/recalc.csv, diff.md. 기존 horizons_stats.csv 와 70행 대조: n·beta·nw_t·비중첩t·에피소드·판정 일치. 차이는 홀수 n 에서 '뒤 절반' 경계(floor vs ceil)뿐, ceil 로 맞추면 전부 일치(recalc_alt_halfsplit.csv).


## Antigravity review6 2026-11-18
- 검토 범위: `PREREG.md` 11절, `src/horizons.py`, `out/horizons_stats.csv`, `out/horizons_zones.csv`, `out/panel_*.csv`, `data/yh_*.json`. 기존 파일 수정 없이 [REVIEW.md](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/review6/REVIEW.md)만 작성.
- LESSON HIT:
  - **경계 통과·비중첩 OLS·LOYO 취약성(`KOSDAQ PBR h=9`)**: `nw_t=-3.354`는 정규분포 56건 보정(`3.322`)에만 0.032 차이로 걸쳤고, `df=147` Student-t 임계치(`3.392`), 비중첩 9개 오프셋(`-2.254 ~ -1.553`, 중앙 `-1.864`, 0/9 통과), 14개 연도 LOYO 중 9개 연도 단독 제외(`-2.690 ~ -3.279`), 단일 군집 제외(`-2.973 ~ -3.256`), Hansen-Hodrick(`-3.110`), 연구 전체 누적 다중검정(`3.384 ~ 3.464`)에서 모두 미달하며 `J2`(2회 < 3)·`J3`(82% < 90%)도 실패.
  - **비유의 단기 양수 `t` 과장 금지 및 분모 왜곡**: 밸류 6종×`h=1,3,6` 18건 중 `|t| >= 2.0`은 0건(최대 `KOSPI PER h=3: +1.931, p=0.054`), 전체 42건 중에서도 `NASDAQ100 이격도 h=6`(`+2.292`, BH `q=0.409`) 1건뿐임. `KOSPI PER`·`S&P500 PER` 단기 양수 `t`는 각각 `2020`(`+1.82/+1.93/+1.76 -> +0.86/+0.48/-0.00`)과 `2009`(`+1.51/+1.16 -> +0.37/+0.42`) TTM 이익 급감기 분모 왜곡에 의존.
  - **소표본 후반부 Bartlett NW 분산 붕괴**: `t_second_half`에서 `SOX 선행PER h=6`(`n2=39`, `lag=6`)이 `V_NW/V_OLS=0.192`로 분산이 80.8% 축소되며 `-8.143`으로 과장됨(`NASDAQ100 선행PER h=9`도 `0.463`, `-4.767`).
  - **체결·미래정보·다중비교 점검**: 전 70행 오차 `<= 2.22e-16` 일치, 미확정 수익률·부분월(`2026-11`) 제외 및 시가 체결(`max|Δt|=0.206`)·`+1`개월 지연(`KOSDAQ PBR h=9 -3.437`, 타 조합 3.32 통과 0건) 확인. 유효 독립 검정 수 `M_eff=38~43`(Li-Ji/Nyholt)에서도 통과 건수 변화 없음.
- 결론: `review6/REVIEW.md` `Verdict: PASS`, 마지막 줄 `PASS_WITH_NOTES`.

## Claude — v6 수평선 (2026-11-18 밤)
- PREREG 11절(결과 전) → src/horizons.py. 56건 중 판정 보류 1, 기각 55. calc7 일치, review6 PASS_WITH_NOTES → 경계 통과·단기 양수 t 문구 완화. 리포트에 수평선 표 추가.
- 시도 +56(1차) +14(12개월 비교).


## Antigravity review7 2026-11-18
- 검토 범위: `PREREG.md` 12절, `src/windows.py`, `out/windows_stats.csv`, `out/windows_stats_d1.csv`, `src/core.py`, `data/*`. 기존 파일 수정 없이 [REVIEW.md](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/review7/REVIEW.md)만 작성.
- LESSON HIT:
  - **특정 위기·단일 군집 의존(`KOSDAQ PBR 3y`)**: `nw_t=-3.331`은 비중첩 12m OLS `t` 중앙값 `-1.558`(`0/12` 통과), `2008~2025` 18개년 LOYO 중 8개년 단독 제외 시 `3.21` 미달, `2008-06~2009-03` 단일 GFC 저평가 군집(`Z<=-2` 6개월 중 5개월) 제외 시 `-2.529` 붕괴, `+1m` 지연(`-3.2133`) `Student-t(211)`(`3.256`) 미달, 비용 2배(`10bp`) 시 전략 Sharpe(`0.1518 < 0.1521`) 역전.
  - **표본 시작월 효과 vs 특정 위기 편입 효과**: 동일 시작월(`2013-09~`)에서는 `10y(-4.31) > 5y(-2.83) > 3y(-2.64)`로 짧은 창이 단조 열위이며, `5y`(`2009-09~`)는 표본 연장에도 `-2.651`로 약화, `3y`도 `2009-09~` 절단 시 `-2.787`로 기각 → '2008년까지 표본 연장' 일반화가 아니라 `2008~2009` GFC 1개 에피소드 편입 효과임.
  - **짧은 창의 추세 추종·`sd` 붕괴·회전율 상승**: `3y`에서 `corr(z, v)`가 하락(`S&P500 PBR` `0.81->0.46`, `KOSPI PBR` `0.90->0.67`), `max/min sd`가 급증(`KOSPI PBR` `2.5x->12.1x`, `KOSDAQ PBR` `1.3x->6.1x`, `2010~2013` 박스권 뒤 `2011~2016` 38개월 가짜 과열 군집 유발), 전 14종 회전율 상승 및 `KOSDAQ PBR` Sharpe 반토막(`0.312->0.154`).
  - **다중 비교·코드 점검**: `2023-06-30` 절단 `max|dz|=0.00`, 시가체결 `max|Δt12|=0.126`으로 미래정보 없음. 단 `windows.py:17` `ep_hot/ep_cold`가 `t3` 검증 행에서도 `r12.notna()`로 집계되는 경미한 불일치 확인(판정 불변). `10y` 대조군 포함 `60`건(`3.342`, `Nyholt M_eff=41.0~50.0`) 및 연구 누적 `114~132`건(`3.516~3.613`)에서는 통과 0건.
- 결론: `review7/REVIEW.md` `Verdict: PASS`, 마지막 줄 `PASS_WITH_NOTES`.
## Claude — v7 창 길이 (2026-11-18 밤)
- PREREG 12절(결과 전) → src/windows.py(0·1개월 지연). 37 기각, 1 참고지표(KOSDAQ PBR 3년, 취약). review7 PASS_WITH_NOTES → 해석 수정. 시도 +38(1차) +38(같은 시작월·지연).

## Antigravity calc8 (TASK_calc_win) 2026-11-18
- 독립 재계산 완료(`src/` 미열람): [recalc8.py](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/calc8/recalc8.py), [recalc.csv](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/calc8/out/recalc.csv), [diff.md](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/calc8/out/diff.md).
- 대조 결과 (`out/windows_stats.csv` 64행): `start`, `n`, `verdict`, `ep_hot`, `ep_cold` 0건 불일치. `t12`, `t12_half`, `t3`, `t3_half`, `sh`, `c60`, `cagr`, `c60_cagr`, `z_now` 전부 최대 오차 `<= 7.11e-15`로 완전 일치. `placebo`만 최대 `0.0171` 차이(판정 불변).
- 핵심 확인: `KOSDAQ PBR` 3년 창(`same_start=False`, `2008-02~`) `t12=-3.3306` → `참고지표` 재현, 10년 창 동일 시작월(`same_start=True`, `2013-09~`) `t12=-2.6398` → `기각` 재현.
- LESSON HIT:
  - **다중 비교·창 길이 변경**: 3년/5년 창 38건 1차 검정에 Bonferroni `|t| >= 3.21` 적용 확인.
  - **표본 시작월 효과 분리**: 짧은 창(`3y/5y`)은 워밍업 단축으로 시작월이 앞당겨지므로 10년(선행PER은 5년) 시작월로 자른 `same_start=True` 대조로 `KOSDAQ PBR` 3년 창 `참고지표`가 표본 구간 효과임을 확인.
  - **미확정 수익률 제외·노출 일치 벤치마크·순환 플라시보**: `r12`/`r3` 확정 표본만 회귀·절반분할·에피소드 계산에 사용, 상수 60% 및 순환 이동 플라시보 대조 완료.
