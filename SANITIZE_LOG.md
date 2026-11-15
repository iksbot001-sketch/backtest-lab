# Sanitization & Verification Log

Generated on 2026-11-15 when preparing `public/` (`backtest-lab`) from the private `backtest-archive`.

## Exclusions Applied
- Excluded files/folders: `README.ko.md`, `SOURCES*.txt`, `_refs/`, `data/`, `panel*.csv`, `*.log.json`, `__pycache__/`, `.DS_Store`.
- Filtered `CORRECTIONS.md` to include only entries for the 6 published studies.
- Excluded private/live studies (`2026-10-17`, `2026-10-21`, `2026-10-22`, `2026-10-24`, `2026-11-04`, `2026-11-06`, `2026-11-15_trend-x-valuation-combo`), `RESULTS*.csv`, `metrics/`, and `docs/`.

## Replacement Summary

| What | Total Replacements |
|---|---|
| Local path (/Users/iksbot/ -> ~/) | 2688 |
| Account term (계좌 -> 포트폴리오) | 132 |
| News headline name (이억원 -> 이OO) | 1 |
| Deposit unit (3천만원 -> 30M KRW) | 3 |
| Unit amount (1만원 -> 10,000 KRW) | 5 |
| Price tier (30만원대 -> 300,000 KRW대) | 2 |
| Capital unit (1억원 -> 100M KRW) | 23 |
| Idiom (만원 버스 -> 혼잡한 버스) | 1 |
| Tick tier (1만~5만원 -> 10k~50k KRW) | 1 |
| Tick tier (5만원 -> 50,000 KRW) | 1 |
| Env key check (EODHD_API_KEY=) | 1 |
| Path(~) .expanduser() fix | 2 |
| Env key check (NASDAQ_DATA_LINK_API_KEY=) | 1 |
| Doc URL token param (token=YOUR_TOKEN) | 1 |

## Detailed Replacements (File, What, Count)

| File | What | How Many |
|---|---|---|
| `CONTRIBUTING.md` | Local path (/Users/iksbot/ -> ~/) | 5 |
| `2026-10-23_rebalancing-front-running/20261023_01_rebalancing_frontrun/head_review.json` | Account term (계좌 -> 포트폴리오) | 1 |
| `2026-10-23_rebalancing-front-running/20261023_01_rebalancing_frontrun/memo.json` | Account term (계좌 -> 포트폴리오) | 1 |
| `2026-10-23_rebalancing-front-running/20261023_01_rebalancing_frontrun/memo.md` | Account term (계좌 -> 포트폴리오) | 3 |
| `2026-10-23_rebalancing-front-running/20261023_01_rebalancing_frontrun/researcher_notes.md` | Local path (/Users/iksbot/ -> ~/) | 1 |
| `2026-10-23_rebalancing-front-running/20261023_01_rebalancing_frontrun/risk_review.json` | Account term (계좌 -> 포트폴리오) | 2 |
| `2026-10-23_rebalancing-front-running/20261023_01_rebalancing_frontrun/spec.json` | Local path (/Users/iksbot/ -> ~/) | 1 |
| `2026-10-23_rebalancing-front-running/20261023_01_rebalancing_frontrun/spec.json` | Account term (계좌 -> 포트폴리오) | 1 |
| `2026-10-23_rebalancing-front-running/20261023_01_rebalancing_frontrun/backtest/backtest.py` | Local path (/Users/iksbot/ -> ~/) | 3 |
| `2026-10-23_rebalancing-front-running/20261023_01_rebalancing_frontrun/backtest/quant_report.md` | Local path (/Users/iksbot/ -> ~/) | 2 |
| `2026-10-23_rebalancing-front-running/20261023_01_rebalancing_frontrun/backtest/quant_report.md` | Account term (계좌 -> 포트폴리오) | 1 |
| `2026-10-23_rebalancing-front-running/20261023_01_rebalancing_frontrun/backtest/cro_checks/cro_check.py` | Local path (/Users/iksbot/ -> ~/) | 2 |
| `2026-10-23_rebalancing-front-running/20261023_01_rebalancing_frontrun/backtest/cro_checks/cro_check2.py` | Local path (/Users/iksbot/ -> ~/) | 1 |
| `2026-10-23_rebalancing-front-running/20261023_02_letf_rebalance_korea/researcher_notes.md` | News headline name (이억원 -> 이OO) | 1 |
| `2026-10-23_rebalancing-front-running/20261023_02_letf_rebalance_korea/researcher_notes.md` | Deposit unit (3천만원 -> 30M KRW) | 1 |
| `2026-10-23_rebalancing-front-running/20261023_02_letf_rebalance_korea/researcher_notes.md` | Unit amount (1만원 -> 10,000 KRW) | 1 |
| `2026-10-23_rebalancing-front-running/20261023_02_letf_rebalance_korea/spec.json` | Deposit unit (3천만원 -> 30M KRW) | 2 |
| `2026-10-23_rebalancing-front-running/20261023_02_letf_rebalance_korea/spec.json` | Unit amount (1만원 -> 10,000 KRW) | 1 |
| `2026-10-23_rebalancing-front-running/20261023_02_letf_rebalance_korea/backtest/backtest.py` | Local path (/Users/iksbot/ -> ~/) | 3 |
| `2026-10-23_rebalancing-front-running/20261023_02_letf_rebalance_korea/backtest/backtest.py` | Unit amount (1만원 -> 10,000 KRW) | 1 |
| `2026-10-23_rebalancing-front-running/20261023_02_letf_rebalance_korea/backtest/loss_structure.json` | Unit amount (1만원 -> 10,000 KRW) | 1 |
| `2026-10-23_rebalancing-front-running/20261023_02_letf_rebalance_korea/backtest/cro_checks/cro_check.py` | Local path (/Users/iksbot/ -> ~/) | 1 |
| `2026-10-23_rebalancing-front-running/20261023_02_letf_rebalance_korea/backtest/cro_checks/cro_check2.json` | Price tier (30만원대 -> 300,000 KRW대) | 1 |
| `2026-10-23_rebalancing-front-running/20261023_02_letf_rebalance_korea/backtest/cro_checks/cro_check2.py` | Local path (/Users/iksbot/ -> ~/) | 1 |
| `2026-10-23_rebalancing-front-running/20261023_02_letf_rebalance_korea/backtest/cro_checks/cro_check2.py` | Unit amount (1만원 -> 10,000 KRW) | 1 |
| `2026-10-23_rebalancing-front-running/20261023_02_letf_rebalance_korea/backtest/cro_checks/cro_check2.py` | Price tier (30만원대 -> 300,000 KRW대) | 1 |
| `2026-10-23_rebalancing-front-running/20261023_02_letf_rebalance_korea/backtest/cro_checks/cro_check3.py` | Local path (/Users/iksbot/ -> ~/) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_0915_quant/trial_registry.jsonl` | Local path (/Users/iksbot/ -> ~/) | 1622 |
| `2026-10-26_turtle-trading/adhoc_20261026_0915_quant/backtest/backtest.py` | Local path (/Users/iksbot/ -> ~/) | 2 |
| `2026-10-26_turtle-trading/adhoc_20261026_0915_quant/backtest/backtest.py` | Account term (계좌 -> 포트폴리오) | 12 |
| `2026-10-26_turtle-trading/adhoc_20261026_0915_quant/backtest/quant_report.md` | Account term (계좌 -> 포트폴리오) | 19 |
| `2026-10-26_turtle-trading/adhoc_20261026_0915_quant/backtest/trial_registry.jsonl` | Local path (/Users/iksbot/ -> ~/) | 110 |
| `2026-10-26_turtle-trading/adhoc_20261026_0915_quant/backtest/validation.json` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_0915_quant/backtest/validation.md` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_0915_quant/backtest/validation_i30/validation.json` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_0915_quant/backtest/validation_i30/validation.md` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_0940_cro/risk_review.json` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_0940_cro/risk_review.json` | Account term (계좌 -> 포트폴리오) | 20 |
| `2026-10-26_turtle-trading/adhoc_20261026_0940_cro/risk_review.md` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_0940_cro/risk_review.md` | Idiom (만원 버스 -> 혼잡한 버스) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_0940_cro/risk_review.md` | Account term (계좌 -> 포트폴리오) | 37 |
| `2026-10-26_turtle-trading/adhoc_20261026_0940_cro/cro_checks/audit.py` | Local path (/Users/iksbot/ -> ~/) | 2 |
| `2026-10-26_turtle-trading/adhoc_20261026_1224_quant/trial_registry.jsonl` | Local path (/Users/iksbot/ -> ~/) | 330 |
| `2026-10-26_turtle-trading/adhoc_20261026_1224_quant/backtest/backtest.py` | Local path (/Users/iksbot/ -> ~/) | 4 |
| `2026-10-26_turtle-trading/adhoc_20261026_1224_quant/backtest/backtest.py` | Tick tier (1만~5만원 -> 10k~50k KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_1224_quant/backtest/backtest.py` | Tick tier (5만원 -> 50,000 KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_1224_quant/backtest/backtest.py` | Account term (계좌 -> 포트폴리오) | 2 |
| `2026-10-26_turtle-trading/adhoc_20261026_1224_quant/backtest/quant_report.md` | Account term (계좌 -> 포트폴리오) | 5 |
| `2026-10-26_turtle-trading/adhoc_20261026_1224_quant/backtest/trial_registry.jsonl` | Local path (/Users/iksbot/ -> ~/) | 210 |
| `2026-10-26_turtle-trading/adhoc_20261026_1224_quant/backtest/validation.json` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_1224_quant/backtest/validation.md` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_1224_quant/backtest/validation_K200_b/validation.json` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_1224_quant/backtest/validation_K200_b/validation.md` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_1224_quant/backtest/validation_KQ150_a/validation.json` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_1224_quant/backtest/validation_KQ150_a/validation.md` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_1224_quant/backtest/validation_KQ150_b/validation.json` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_1224_quant/backtest/validation_KQ150_b/validation.md` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_1235_cro/risk_review.json` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_1235_cro/risk_review.json` | Account term (계좌 -> 포트폴리오) | 4 |
| `2026-10-26_turtle-trading/adhoc_20261026_1235_cro/risk_review.md` | Account term (계좌 -> 포트폴리오) | 3 |
| `2026-10-26_turtle-trading/adhoc_20261026_1235_cro/backtest/cro_checks/cro_audit_results.json` | Local path (/Users/iksbot/ -> ~/) | 4 |
| `2026-10-26_turtle-trading/adhoc_20261026_1235_cro/backtest/cro_checks/run_cro_audit.py` | Local path (/Users/iksbot/ -> ~/) | 7 |
| `2026-10-26_turtle-trading/adhoc_20261026_1235_cro/backtest/cro_checks/run_cro_audit_part2.py` | Local path (/Users/iksbot/ -> ~/) | 5 |
| `2026-10-26_turtle-trading/adhoc_20261026_1341_quant_us_turtle/BRIEF.md` | Local path (/Users/iksbot/ -> ~/) | 3 |
| `2026-10-26_turtle-trading/adhoc_20261026_1341_quant_us_turtle/agy_log.json` | Local path (/Users/iksbot/ -> ~/) | 8 |
| `2026-10-26_turtle-trading/adhoc_20261026_1341_quant_us_turtle/run_argon.py` | Local path (/Users/iksbot/ -> ~/) | 5 |
| `2026-10-26_turtle-trading/adhoc_20261026_1341_quant_us_turtle/trial_registry.jsonl` | Local path (/Users/iksbot/ -> ~/) | 170 |
| `2026-10-26_turtle-trading/adhoc_20261026_1341_quant_us_turtle/backtest/backtest.py` | Local path (/Users/iksbot/ -> ~/) | 4 |
| `2026-10-26_turtle-trading/adhoc_20261026_1341_quant_us_turtle/backtest/backtest.py` | Account term (계좌 -> 포트폴리오) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_1341_quant_us_turtle/backtest/quant_report.md` | Local path (/Users/iksbot/ -> ~/) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_1341_quant_us_turtle/backtest/quant_report.md` | Account term (계좌 -> 포트폴리오) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_1341_quant_us_turtle/backtest/trial_registry.jsonl` | Local path (/Users/iksbot/ -> ~/) | 105 |
| `2026-10-26_turtle-trading/adhoc_20261026_1341_quant_us_turtle/backtest/validation.json` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_1341_quant_us_turtle/backtest/validation.md` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_1341_quant_us_turtle/backtest/validation_GSPC_b/validation.json` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_1341_quant_us_turtle/backtest/validation_GSPC_b/validation.md` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_1341_quant_us_turtle/backtest/validation_NDX_a/validation.json` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_1341_quant_us_turtle/backtest/validation_NDX_a/validation.md` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_1341_quant_us_turtle/backtest/validation_NDX_b/validation.json` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/adhoc_20261026_1341_quant_us_turtle/backtest/validation_NDX_b/validation.md` | Capital unit (1억원 -> 100M KRW) | 1 |
| `2026-10-26_turtle-trading/kq150_review_20261026/BRIEF.md` | Account term (계좌 -> 포트폴리오) | 5 |
| `2026-10-26_turtle-trading/turtle_review_20261026/BRIEF.md` | Account term (계좌 -> 포트폴리오) | 1 |
| `2026-10-28_trend-template-breakout-30y/README.md` | Local path (/Users/iksbot/ -> ~/) | 1 |
| `2026-10-28_trend-template-breakout-30y/src/PREREG_erc.md` | Account term (계좌 -> 포트폴리오) | 4 |
| `2026-10-28_trend-template-breakout-30y/src/SPEC.md` | Local path (/Users/iksbot/ -> ~/) | 3 |
| `2026-10-28_trend-template-breakout-30y/src/WEB_RESEARCH.md` | Account term (계좌 -> 포트폴리오) | 1 |
| `2026-10-28_trend-template-breakout-30y/src/diag.py` | Local path (/Users/iksbot/ -> ~/) | 1 |
| `2026-10-28_trend-template-breakout-30y/src/dispatch.out` | Local path (/Users/iksbot/ -> ~/) | 14 |
| `2026-10-28_trend-template-breakout-30y/src/dispatch.py` | Local path (/Users/iksbot/ -> ~/) | 2 |
| `2026-10-28_trend-template-breakout-30y/src/run.out` | Local path (/Users/iksbot/ -> ~/) | 1 |
| `2026-10-28_trend-template-breakout-30y/src/src/bt.py` | Local path (/Users/iksbot/ -> ~/) | 8 |
| `2026-10-28_trend-template-breakout-30y/src/src/bt_before_erc.py` | Local path (/Users/iksbot/ -> ~/) | 8 |
| `2026-10-28_trend-template-breakout-30y/src/src/bt_before_improve.py` | Local path (/Users/iksbot/ -> ~/) | 8 |
| `2026-11-08_earnings-gamma-chesley-quant/README.md` | Local path (/Users/iksbot/ -> ~/) | 13 |
| `2026-11-08_earnings-gamma-chesley-quant/gamma_backtest/FORECAST_SOURCES.md` | Account term (계좌 -> 포트폴리오) | 2 |
| `2026-11-08_earnings-gamma-chesley-quant/gamma_backtest/PLAN.md` | Account term (계좌 -> 포트폴리오) | 1 |
| `2026-11-08_earnings-gamma-chesley-quant/gamma_backtest/align_split.py` | Account term (계좌 -> 포트폴리오) | 1 |
| `2026-11-08_earnings-gamma-chesley-quant/gamma_backtest/build_panel_kr.py` | Local path (/Users/iksbot/ -> ~/) | 1 |
| `2026-11-08_earnings-gamma-chesley-quant/gamma_backtest/com.iksbot.gamma-snapshot.plist` | Local path (/Users/iksbot/ -> ~/) | 4 |
| `2026-11-08_earnings-gamma-chesley-quant/gamma_backtest/eod.py` | Local path (/Users/iksbot/ -> ~/) | 1 |
| `2026-11-08_earnings-gamma-chesley-quant/gamma_backtest/eod.py` | Env key check (EODHD_API_KEY=) | 1 |
| `2026-11-08_earnings-gamma-chesley-quant/gamma_backtest/eod.py` | Path(~) .expanduser() fix | 1 |
| `2026-11-08_earnings-gamma-chesley-quant/gamma_backtest/probe_zacks.py` | Local path (/Users/iksbot/ -> ~/) | 1 |
| `2026-11-08_earnings-gamma-chesley-quant/gamma_backtest/probe_zacks.py` | Env key check (NASDAQ_DATA_LINK_API_KEY=) | 1 |
| `2026-11-08_earnings-gamma-chesley-quant/gamma_backtest/probe_zacks.py` | Path(~) .expanduser() fix | 1 |
| `2026-11-08_earnings-gamma-chesley-quant/gamma_backtest/validate_kr_px.py` | Local path (/Users/iksbot/ -> ~/) | 1 |
| `2026-11-08_earnings-gamma-chesley-quant/gamma_backtest/out/CS_AUDIT.md` | Account term (계좌 -> 포트폴리오) | 3 |
| `2026-11-08_earnings-gamma-chesley-quant/gamma_backtest/out/G2_A2.md` | Account term (계좌 -> 포트폴리오) | 1 |
| `2026-11-08_earnings-gamma-chesley-quant/gamma_backtest/out/P2.md` | Doc URL token param (token=YOUR_TOKEN) | 1 |
| `2026-11-08_earnings-gamma-chesley-quant/gamma_backtest/out/collect_disc.log` | Local path (/Users/iksbot/ -> ~/) | 2 |
| `2026-11-08_earnings-gamma-chesley-quant/gamma_backtest/out/collect_shares.log` | Local path (/Users/iksbot/ -> ~/) | 2 |
| `2026-11-14_valuation-v2-calibration/src/TASK_A.md` | Local path (/Users/iksbot/ -> ~/) | 1 |
| `2026-11-15_valuation-v2-ex-ante-test/src/TASK.md` | Local path (/Users/iksbot/ -> ~/) | 2 |
| `2026-11-15_valuation-v2-ex-ante-test/src/src/build_inputs.py` | Local path (/Users/iksbot/ -> ~/) | 1 |

## Final Verification Checks

Command run (excluding `SANITIZE_LOG.md` from grep so pattern documentation does not self-match):
- **Total size (`du -sh public`):** `67M`
- **File count (`find public -type f | wc -l`):** `737` (including `SANITIZE_LOG.md`)

| Pattern (case-insensitive) | Matches in `public/` |
|---|---|
| `/Users/` | 0 |
| `@gmail` | 0 |
| `ikseong` | 0 |
| `api_key=` | 0 |
| `token=` | 0 |
| `계좌` | 0 |
| `만원` | 0 |
| `억원` | 0 |

## Second pass (Claude Code, 2026-11-15)
- Removed `com.*.gamma-snapshot.plist` (local scheduler config).
- Study READMEs: removed links to the Korean original and the private source list, removed the "Source locations" section, replaced citations of private notes with "private note (not published)".
- Replaced remaining local identifiers (`com.iksbot.`, `-Users-iksbot`).
- Re-ran the grep checks: zero matches for `/Users/`, `iksbot`, `ikseong`, `@gmail`, `README.ko`, `_refs/`, `SOURCES`.


## Added `2026-10-22_us-golden-cross-voo-qqq` (Antigravity, 2026-11-15)
- Added `2026-10-22_us-golden-cross-voo-qqq/` (36 files: `README.md`, `charts/`, `ladder/`, `out/`, `scripts/`).
- Removed `README.ko.md`, `SOURCES.txt`, `SOURCES.ko.txt`, `_refs/`, `kr/` (`sj_KOSPI.txt`, `sj_KOSDAQ.txt` raw price files), and `us-gc-daily/` (dropped because `us_gc_daily.py` and `run.sh` reference `TELEGRAM_CHAT_ID`/`telegram_chat_id`/`chat_id`, `@GFreportBot`, and local paths `~/report-digest`, `~/investment-bot`, `$HOME/us-gc-daily`).
- Sanitized `2026-10-22_us-golden-cross-voo-qqq/README.md`: removed the Korean original link and "Source locations" section, replaced `_refs/` and `SOURCES.txt` citations with `private note (not published)` / `private source list`, removed references to dropped `kr/` and `us-gc-daily/` files, and added the adopted-rule status notice at the top.
- Replaced `/Users/iksbot/` with `~/` across 13 files in `2026-10-22_us-golden-cross-voo-qqq/scripts/` (16 total replacements: `compare3.py` 1, `engine.py` 1, `idx.py` 1, `idx2.py` 1, `kelly.py` 1, `ladder.py` 1, `ladder_re.py` 1, `load.py` 1, `longrun.py` 1, `now.py` 2, `pe_gc.py` 2, `pe_gc2.py` 2, `tech.py` 1).
- Updated `public/README.md` to add `2026-10-22_us-golden-cross-voo-qqq` (Verdict: **Adopted**) and update the disclaimer to note that one public-knowledge adopted rule (50/200-day moving-average cross) is included without position sizing or account data.
- Re-ran case-insensitive grep checks over `public/` (excluding `.git/` and `SANITIZE_LOG.md`):
  - `2026-10-22_us-golden-cross-voo-qqq/`: 0 matches for all 13 patterns (`/Users/`, `iksbot`, `ikseong`, `@gmail`, `api_key=`, `token=`, `chat_id`, `계좌`, `만원`, `억원`, `README.ko`, `_refs/`, `SOURCES`).
  - Whole `public/`: 0 matches for `/Users/`, `iksbot`, `ikseong`, `@gmail`, `api_key=`, `token=`, `chat_id`, `계좌`, `만원`, `억원`, `_refs/`; `README.ko`: 3 (all in `templates/STUDY_README_TEMPLATE.md`); `SOURCES`: 15 (English word "sources" / `SOURCES` variable in `tools/extract_returns.py`, `README.md`, `templates/STUDY_README_TEMPLATE.md`, and existing study READMEs).
