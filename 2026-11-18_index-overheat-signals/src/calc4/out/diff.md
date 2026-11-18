# 일간·단기 검증 독립 재계산 대조 보고서 (calc4)

- 기준: `PREREG.md` 3·9절 정의만으로 독립 구현([recalc.py](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/calc4/recalc.py)), `src/` 미열람.
- 대조 대상:
  - [daily_events_test.csv](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/out/daily_events_test.csv) vs [recalc_events.csv](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/calc4/out/recalc_events.csv)
  - [daily_strategy.csv](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/out/daily_strategy.csv) vs [recalc_strategy.csv](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/calc4/out/recalc_strategy.csv)
  - [daily_pbr_approx_check.csv](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/out/daily_pbr_approx_check.csv) vs [recalc_pbr_approx_check.csv](file://~/agent-fund/runs/adhoc_20261118_valuation_signals/calc4/out/recalc_pbr_approx_check.csv)

## 1. 임계치 초과 불일치 요약

| 항목 | 기준 | 초과 건수 | 최대 `|Δ|` | 비고 |
|---|---|---|---|---|
| 이벤트 수 (`n`, `first`, `last`) | 차이 > 0 | **0 / 84** | 0 | 84행 전수 일치 |
| 이벤트 수익 (`mean`, `base`, `excess`, `excess_2nd`) | `|Δ|` > 0.2%p | **0 / 84** | 0.000000 | 부동소수점 정밀도 수준 완전 일치 |
| 이벤트 한쪽 p (`p`) | `|Δ|` > 0.02 | **0 / 84** | 0.0140 | `KOSPI_DISP -2 buy h=5` (`0.4126` vs `0.3986`), 10,000회 무작위 추출 시드 차이 범위 내 |
| 전략 Sharpe (`sharpe`, `sharpe_10bp`) | `|Δ|` > 0.05 | **0 / 7** | 0.000020 (5bp) / 0.000039 (10bp) | 첫날 진입 비용(`dw[0]`) 처리 차이로 인한 극소 차이 |
| KOSPI PBR 근사 검증 | — | **0 / 5** | 0.000000 | `n=6040`, `mape=0.007056`, `p95=0.026223`, `z_corr=0.997584`, `z_mae=0.054621` 완전 일치 |

### 미세 차이(임계치 미만) 원인
1. **전략 `turnover` (최대 `|Δ|=0.00635`)·`sharpe` (최대 `|Δ|=0.00002`)**: 재계산은 첫 유효일 `dw[0]=0`(`prepend=w[0]`)으로 처리했고, 원본은 초기 진입 `|w[0]-0|` 또는 `|w[0]-0.6|` 등을 반영한 것으로 추정. 성과·판정에 영향 없음.
2. **`KOSDAQ_PBR` `z_now` (`-1.725022` vs `-1.713954`, `Δ=+0.011067`)**: `data/agy/kosdaq_per_pbr.csv` 말단 부분월 행(`2026-11-17`)을 직전 월말(`date < d`)로 참조하는지 여부의 차이. 비중·이벤트·판정에 영향 없음.
3. **월말 비율 적용 경계**: `KOSDAQ_PBR` 및 `KOSPI` 근사 검증에서 월말 당일이 아닌 **직전 월말(`date < d`, `allow_exact_matches=False`)**을 적용해야 `n=6040` 및 `start=2013-11-15`와 정확히 일치함.

## 2. 독립 판정 (D1~D4)

- 기준(PREREG 9절): 1차 검정 14건(7지표 × 2방향 × `h=20`, `lvl=±1`), 한쪽 `p < 0.0036`, `n ≥ 8`, `D3`: `sharpe > const_sharpe` AND `placebo ≥ 0.90`, `D4`: 후반부 초과수익 부호 유지.

| 지표 | 방향 | n | 초과수익(bp) | p | 후반부(bp) | Sharpe (상수) | 플라시보 | D1 | D2 | D3 | D4 | 독립 판정 |
|---|---|---:|---:|---:|---:|---:|---:|---|---|---|---|---|
| SP500_DISP | buy | 24 | -162.7 | 0.9505 | -235.2 | 0.362 (0.460) | 0.070 | F | T | F | F | **기각** |
| SP500_DISP | sell | 25 | +87.8 | 0.8339 | +90.0 | 0.362 (0.460) | 0.070 | F | T | F | F | **기각** |
| NASDAQ100_DISP | buy | 17 | -32.0 | 0.5848 | -123.9 | 0.387 (0.528) | 0.022 | F | T | F | F | **기각** |
| NASDAQ100_DISP | sell | 24 | +215.5 | 0.9424 | +189.7 | 0.387 (0.528) | 0.022 | F | T | F | F | **기각** |
| SOX_DISP | buy | 18 | -40.0 | 0.5950 | -56.0 | 0.585 (0.626) | 0.271 | F | T | F | F | **기각** |
| SOX_DISP | sell | 29 | +95.1 | 0.7430 | +236.3 | 0.585 (0.626) | 0.271 | F | T | F | F | **기각** |
| KOSPI_DISP | buy | 19 | +34.3 | 0.4114 | -92.6 | 0.267 (0.408) | 0.027 | F | T | F | F | **기각** |
| KOSPI_DISP | sell | 13 | -157.6 | 0.1758 | -136.5 | 0.267 (0.408) | 0.027 | F | T | F | T | **기각** |
| KOSDAQ_DISP | buy | 17 | -306.7 | 0.9680 | -472.0 | 0.153 (0.178) | 0.326 | F | T | F | F | **기각** |
| KOSDAQ_DISP | sell | 11 | +41.5 | 0.5782 | +72.9 | 0.153 (0.178) | 0.326 | F | T | F | F | **기각** |
| KOSPI_PBR | buy | 17 | +0.3 | 0.5014 | -97.5 | 0.461 (0.467) | 0.556 | F | T | F | F | **기각** |
| KOSPI_PBR | sell | 4 | +43.8 | 0.5693 | +274.0 | 0.461 (0.467) | 0.556 | F | F | F | F | **판정 보류** (`n<8`) |
| KOSDAQ_PBR | buy | 7 | +467.0 | 0.0284 | +173.1 | 0.293 (0.209) | 0.836 | F | F | F | T | **판정 보류** (`n<8`) |
| KOSDAQ_PBR | sell | 12 | +241.5 | 0.8883 | -19.0 | 0.293 (0.209) | 0.836 | F | T | F | T | **기각** |

- 결론: 1차 14건 중 D1 통과 0건, D3 통과 0건. **12건 기각, 2건 판정 보류(`KOSPI_PBR sell` n=4, `KOSDAQ_PBR buy` n=7)**.
