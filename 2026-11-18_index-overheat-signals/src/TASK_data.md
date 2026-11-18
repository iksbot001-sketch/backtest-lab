# TASK_data — 누락 밸류에이션·심리 데이터 수집 (Antigravity)

작업 폴더 = 이 폴더. 결과는 `data/agy/` 아래에만 쓴다. 다른 파일은 고치지 않는다.
모호한 점은 임의로 정하지 말고 `QUESTIONS_data.md`에 적는다. 각 파일의 출처 URL·수집일·단위를 `data/agy/SOURCES.md`에 적는다.

## 수집 대상 (우선순위 순)
1. **KOSDAQ 지수 PER·PBR 일간** (KRX 정보데이터시스템 [11007] 또는 동등 공개 출처), 가능한 가장 이른 날부터 2026-11-17까지.
   → `data/agy/kosdaq_per_pbr.csv` 열: date,close,per,pbr
   - KOSPI도 2026-11-05 ~ 2026-11-17 구간을 같은 출처로 이어 붙여 `data/agy/kospi_per_pbr_ext.csv`.
2. **NASDAQ-100(또는 NASDAQ 종합) PER·PBR 시계열** (월간 이상, 2000년대부터 가능한 만큼). 출처 후보: 공개 웹 표, 논문 부록, 무료 API. 각 출처의 정의(TTM/선행, 가중 방식, 음수 이익 처리)를 적는다.
   → `data/agy/ndx_valuation.csv` 열: date,per_ttm,per_fwd,pbr (없는 칸은 비움)
3. **선행(fwd) PER 장기 시계열**: S&P500(예: 공개 PDF/표), KOSPI(12개월 선행 컨센서스). 무료로 10년 이상 확보 가능한지 조사.
   → 있으면 `data/agy/fwd_pe_<market>.csv` (date,fwd_pe). 없으면 SOURCES.md에 '확보 불가'와 이유.
4. **CNN Fear & Greed 지수 일간 시계열**: 공식 페이지/공개 저장소에서 정상적으로 받을 수 있는 범위만. 봇 차단 우회(헤더 위장 등) 금지.
   → `data/agy/fear_greed.csv` (date,fg)

## 금지
- 값을 추정·보간해 만들지 않는다. 빠진 날은 비워 둔다.
- 백테스트·통계 계산은 하지 않는다(Claude 담당).
- 최종 답: 파일별 행 수, 기간, 출처, 실패 항목과 이유.
