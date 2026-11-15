# 추세 템플릿 + 기준가 돌파 시나리오 백테스트 명세 (Claude Code 작성, 2026-10-28)

구현자는 이 명세를 그대로 코드로 옮긴다. 규칙을 바꾸거나 "개선"하지 않는다. 애매하면 추측하지 말고 `QUESTIONS.md`에 적는다.
작업 폴더: 이 실행 폴더(`runs/adhoc_20261028_trend_breakout/`)에만 쓴다. `lib/`, `gates.py`, `data/trial_registry.jsonl` 등 심판 코드는 읽기만 한다.
파이썬: `~/agent-fund/venv/bin/python` (pandas, numpy, pyarrow 있음). 코드는 `src/bt.py` 하나.

## 1. 데이터
- 가격: `~/agent-fund-data/prices/kr/{code}.parquet` (columns date, open, high, low, close, volume, 수정주가, 네이버 출처 = lib/fund.kr 과 같은 출처). 읽기만.
- 종목 목록: `~/agent-fund-data/prices/meta/universe.parquet` (code, name, mkt, kind, ...).
- 대상: `kind in ('거래소','코스닥')` 그리고 `code` 가 정규식 `^\d{5}0$` 그리고 name 에 '스팩' 또는 '기업인수목적' 없음 → 약 2,525개 보통주.
- 벤치마크: 코스피·코스닥 지수. 네이버 `https://api.finance.naver.com/siseJson.naver?symbol=KOSPI&requestType=1&startTime=19900101&endTime=20261028&timeframe=day` (KOSDAQ 도 같은 방식). 받은 원문은 `data/` 하위에 저장해 재사용.
- 1994-01-01 이후만 쓴다(지표 워밍업 포함). 마지막 날은 2026-10-27.

## 2. 행렬 구성
- 마스터 거래일 = 전 종목 날짜 합집합. 종목별로 wide 행렬(날짜×종목) O, H, L, C, V 를 만든다.
- `traded[t,s]` = 원본에 그 날 봉이 있음(거래정지일은 원본에 없다).
- 지표 계산용으로만 C 를 종목별 ffill(상장 전 NaN 유지). 거래정지일의 H, L 은 ffill 된 C 로 채운다. **체결은 traded 인 날에만.**
- 상장 후 봉 수 `nbar[t,s]` (traded 누적).

## 3. 종목 선정 (screener/trend_template_kr.py 와 동일, t일 종가 기준)
t일 유니버스 = traded 이고 거래대금(C×V)>0 이고 nbar ≥ 221 인 종목.
- ema20 = C.ewm(span=20, adjust=False), sma50/150/200 = 단순이평, sma200_20 = sma200 을 20거래일 shift
- hi52/lo52 = 최근 252거래일 H 최고 / L 최저, hi20/lo20 = 최근 20거래일 H 최고 / L 최저
- rs_raw(lag) = 0.4·r(63) + 0.2·(r(126)+r(189)+r(252)), r(k) = C[t−lag]/C[t−lag−k] − 1. 데이터 부족이면 NaN.
- RS0/RS1/RS3 = t일 유니버스 안에서 rs_raw(0)/rs_raw(21)/rs_raw(63) 의 백분위 `rank(pct=True)*99` 를 반올림. NaN 은 NaN(조건 실패).
- 조건 8개 모두 참이면 통과:
  1. C > ema20 > sma50 > sma150 > sma200
  2. sma200 > sma200_20
  3. C ≥ lo52 × 1.30
  4. C ≥ hi52 × 0.75
  5. C ≥ (hi20 + lo20)/2
  6. RS0 ≥ 90
  7. RS0 > RS1 그리고 RS0 > RS3
  8. C < sma200 × 2
- 모든 지표는 t일까지의 값만 쓴다(미래정보 금지). 롤링 창에 NaN 이 섞이면 min_periods 를 창 길이로 둬서 NaN.

## 4. 매매 시나리오 (책 규칙)
- ATR14 = TR(=max(H−L, |H−C₋₁|, |L−C₋₁|)) 의 14일 단순평균, t일까지.
- **기준가 ref = hi52 + ATR14** (52주 최고가 날의 고가 + 1ATR). t일 통과 종목마다 t+1일용 매수 대기 주문(역지정가)을 건다. t+1일에 그 종목이 통과 목록에 없으면(=t일 미통과) 주문 없음. 매일 다시 계산.
- **매수 체결 (t+1일, traded 인 날만):** O ≥ ref 이면 시가 O 에 체결(갭 상승). 아니면 H ≥ ref 이면 ref 에 체결. 아니면 미체결.
- 이미 보유 중인 종목은 추가 매수 안 함. 같은 날 매도된 종목은 그날 재매수 안 함(다음 날부터는 재진입 허용).
- **청산 규칙** (진입가 E):
  - 손절가 S 초기값 = E × 0.93
  - 하루 처리 순서(보수적): ① 그날 시작 시점의 S 로 손절 확인: O ≤ S 면 시가 청산, 아니면 L ≤ S 면 S 에 청산(남은 수량 전부). ② 아직 반 익절 전이면 목표 T = E×1.25: O ≥ T 면 시가에, 아니면 H ≥ T 면 T 에 보유의 절반(내림, 최소 1주) 매도하고 S = max(S, E). ③ 장 마감 후 H ≥ E×1.15 였던 적이 있으면 S = max(S, E) (다음 날부터 적용).
  - 반 익절 후에는 매일 S = max(E, 전일 20일 단순이평) 로 ①에서 확인한다(전일 20일선 이탈 시 나머지 매도). "전일 20일선" = t−1일 종가까지의 sma20.
  - **진입 당일**: 시가 체결(갭)이면 L ≤ S 일 때 S 에 손절, 장중 돌파 체결이면 종가 ≤ S 일 때만 종가에 손절(당일 저가는 돌파 전 값일 수 있음 — 2026-10-28 Claude Code 수정, 처음 명세는 L ≤ S 로 손절해 거의 모든 거래가 당일 손절되는 오류). ②와 반 익절은 하지 않는다, ③은 적용(다음 날부터).
  - 손절과 목표가 같은 날 둘 다 닿으면 손절이 먼저(①이 먼저).
  - 거래정지일(traded 아님)은 아무것도 하지 않고 평가는 ffill 종가로.
  - 기간 마지막 날 보유분은 종가로 평가만(강제 청산은 통계용으로 별도 표시 `open_at_end`).

## 5. 포트폴리오·자금 관리 (펀드 규칙)
- 시작 NAV 1억 원. 현금 이자 0.
- 1회 거래 위험 = 직전 종가 기준 NAV × 1% (= 0.5R, R=NAV×2%). 수량 = floor(위험금액 / (E − E×0.93)) → 대략 NAV의 14.3%.
- 총 열린 위험 한도 = NAV × 3% (=1.5R). 열린 위험 = Σ 수량 × max(0, 진입가 − 현재 S).
- 같은 날 여러 종목이 체결 조건을 만족하면 t일 RS0 높은 순으로 처리. 체결 시점에 (열린 위험 + 새 위험) ≤ 한도 그리고 매수금액+비용 ≤ 현금 이어야 체결, 아니면 건너뜀(기록 `skipped_cap`).
- 비용(lib/fund.py 기준): 매수 체결가 + 1틱, 매도 체결가 − 1틱, 수수료 편도 0.015%. 틱은 `lib.fund.kr_tick`.
- 변형 B: 위 + 매도 시 증권거래세 0.20%.
- 변형 C: 변형 B + 유동성 필터(t일까지 20일 평균 거래대금 C×V ≥ 10억 원인 종목만 주문).

## 6. 기간
같은 규칙으로 각 기간을 **1억에서 새로 시작**해 따로 돌린다. 끝은 모두 2026-10-27.
- 5년 2021-10-28~, 10년 2016-10-28~, 20년 2006-10-27~, 30년 1996-10-28~ (시작일 이전 첫 거래일 이후).
- 지표 워밍업은 시작일 이전 데이터 사용 가능(포지션만 시작일부터).

## 7. 산출물 (이 폴더 안)
- `src/bt.py` — `python src/bt.py` 한 번에 전부 실행. 무작위성 없음.
- 기간×변형(A,B,C)마다 `out/{period}_{variant}/`:
  - `trades.csv`: code, name, mkt, signal_date, entry_date, entry, exit_date, exit_px(가중평균), qty, half_sold(bool), exit_reason(stop/breakeven/ma20/half+ma20/open_at_end), ret(비용 포함), R(=ret/0.07), hold_days, rs0
  - `daily.csv`: date, nav, cash, n_pos, open_risk
  - `metrics.json`: `lib.fund.evaluate(name, r, pos, bench_r, oos_start='2021-10-28', outdir=...)` 결과. r = nav 일수익률, pos = 주식 비중(평가액/nav), bench_r = KOSPI 지수 일수익률. extra 에 거래 통계: n_trades, win_rate, avg_win, avg_loss, payoff, expectancy_R, avg_hold, 반 익절 도달 비율, exit_reason 분포, skipped_cap 수, 연평균 거래 수, 켈리 f* = W − (1−W)/payoff.
- `out/summary.csv`: 행=기간×변형, 열 = CAGR, ROI, MDD, Sharpe, Sortino, vol, n_trades, win_rate, payoff, expectancy_R, exposure, KOSPI CAGR/MDD, KOSDAQ CAGR/MDD (같은 기간).
- `out/signals_daily.csv`: date, n_pass(통과 종목 수) — 검증용.
- `RUNLOG.md`: 실행 시간, 경고, 이상한 점.

## 8. 자체 검증 (구현자가 반드시 돌리고 RUNLOG에 결과 기록)
1. 2026-10-27 통과 목록을 `data/screens/trend_template/pass_20261027.csv` 와 비교(코드 집합 겹침 비율). 키움 600봉 vs 네이버 장기 데이터 차이로 완전 일치는 아닐 수 있다 → 차이 종목 몇 개의 이유를 적는다.
2. 2026-10-27 KT&G(033780) ref 가 201,000 근처인지(이전 계산: 52주 고점일 고가 + ATR14).
3. 무작위 거래 3건을 일봉과 대조해 진입·청산 가격이 규칙대로인지 RUNLOG에 적는다.
4. 미래정보 점검: 신호는 t일 값, 체결은 t+1일 값만 쓰는지 코드에서 확인.
