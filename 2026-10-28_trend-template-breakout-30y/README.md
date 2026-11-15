# 2026-10-28 Trend Template 52-Week High Breakout 30-Year Backtest

## Summary
Tested the Trend Template + 52-week high breakout strategy from 『투자 말고 트레이딩』 (*Trade Like a Stock Market Wizard*) on 30 years of daily bars for roughly 2,500 Korean common stocks (`2,525`, `src/RUNLOG.md`).
Using the book's rules as-is yielded a 30-year CAGR of -13.0% and MDD of -98.9%, leading to rejection (`src/out/summary.csv`, private note (not published)), and the improved variants also failed to clear the pre-registered pass criteria (`src/RUNLOG.md`).

## Why (purpose and context)
The owner had been screening stocks daily after market close using these conditions and receiving them via Telegram (private note (not published)).
The question was: "How much would it actually have made if we had bought and sold strictly by the book?" (private note (not published)).
The book cites SK Hynix as a success case, and the goal was to check what happens when isolating the rules and running them over the entire period (private note (not published)).
Later, the owner asked one additional question (`src/PREREG_erc.md`).
It was how returns, MDD, and Sharpe (return per unit of volatility) change when overlaying the fund's risk management rules (E·R·CR = Exposure, Risk, Current Exposure) (`src/PREREG_erc.md`).
The Obsidian note recorded this result as evidence for the principle: "Any technical signal must go through a backtest before being used as a trading rule" (private note (not published)).

## What was tested
- Question/Hypothesis: Is mechanically trading every 52-week high breakout signal from the book profitable, and do rules revised after diagnosing the loss causes beat holding the index (KOSPI) (private note (not published), `src/PREREG_improve.md`)?
- Market & Assets: 2,525 Korean KOSPI and KOSDAQ common stocks, excluding SPACs (`src/RUNLOG.md`, `src/SPEC.md` Section 1).
- Periods: 5-year (from 2021-10-28), 10-year (from 2016-10-28), 20-year (from 2006-10-27), and 30-year (from 1996-10-28), all ending on 2026-10-27, with each period starting fresh at 100M KRW (`src/SPEC.md` Section 6).
- Data Source: Naver adjusted daily prices (`~/agent-fund-data/prices/kr/`) and Naver KOSPI/KOSDAQ indices; raw data is not included in this folder (`src/SPEC.md` Section 1, private source list).
- Rules (entry, exit, sizing, costs — key points only, `src/SPEC.md`, private note (not published)):
  - Stock selection: Checked daily at close against 8 conditions including aligned moving averages (Close > 20-day > 50-day > 150-day > 200-day), rising 200-day MA, ≥ +30% above 52-week low, within -25% of 52-week high, and top 10% relative strength (RS).
  - Entry: Reference price = 52-week high + 1× daily Average True Range (ATR); buy the next day if price exceeds the reference price.
  - If the open price is above the reference price on entry, fill at the open.
  - Exit: Initial stop-loss at -7%; move stop to entry price upon reaching +15%; sell half at +25% and sell the remainder on a break below the 20-day MA.
  - Sizing: 1% account risk per trade, 3% total open-risk cap, 100M KRW starting NAV, and 0% interest on cash.
  - Costs: 0.015% one-way commission and 1-tick adverse slippage; Variant B adds 0.20% sell tax, Variant C adds a 20-day average trading value ≥ 1B KRW filter on top of B, and Variant A has no sell tax.
- Pre-registered pass criteria (`src/PREREG_improve.md`): The 8 improved configurations must beat both the book rules and KOSPI out-of-sample (OOS, 2021-10-28 to 2026-10-27) and outperform the book rules in-sample (IS, prior to 2021-10-28).

## Results
The baseline is Variant B (realistic costs, including sell tax), and the figures in the blog post are also Variant B (`src/PREREG_improve.md`, private note (not published)).
- Book rules 30-year: CAGR -13.0%, MDD -98.9%, Sharpe -0.477, total return -98.4%, 3,228 trades, win rate 19.4%, payoff ratio 3.74, expectancy -0.087R per trade (R = amount risked per stop-loss) (`src/out/summary.csv`).
- The blog draft title's "100M KRW became 1.57M KRW" matches the CSV's -98.4% total return (private note (not published), `src/out/summary.csv`).
- Book rules 5-year: CAGR +15.2%, MDD -47.4%, Sharpe 0.467; over the same period, KOSPI had CAGR +13.7%, MDD -40.0% (`src/out/summary.csv`).
- Book rules 10-year: CAGR -13.3%, MDD -88.8%; over the same period, KOSPI had CAGR +11.1%, MDD -43.9% (`src/out/summary.csv`).
- Book rules 20-year: CAGR -12.6%, MDD -98.0%; over the same period, KOSPI had CAGR +7.5%, MDD -54.5% (`src/out/summary.csv`).
- KOSPI 30-year buy-and-hold: CAGR +6.9%, MDD -64.7% (`src/out/summary.csv`). (The blog draft wrote 6.8%, private note (not published).)
- Improved rules (C2: stop-loss max(7%, 2×ATR), reference price within +5% of close, no buying on gap-up) 30-year: CAGR +4.4%, MDD -27.5%, Sharpe 0.247, 770 trades (`src/out/improve/summary.csv`).
- Improved rules (C2) 5-year: CAGR +7.3%, MDD -22.1%, failing to beat KOSPI (+13.7%) over the same period (`src/out/improve/summary.csv`).
- Improved rules (C2) split periods (30-year basis): IS CAGR +3.4% (MDD -27.5%), OOS CAGR +9.9% (MDD -21.8%) (`src/out/improve/summary.csv`).
- Volatility filter only (S1, ATR ≤ 4.5%) 30-year: CAGR +6.5%, MDD -29.3%, Sharpe 0.353; the 4.5% threshold was chosen after inspecting diagnostic results (`src/out/improve/summary.csv`, `src/PREREG_improve.md`).
- No gap-up buying only (S3): 5-year CAGR +28.1%, but IS was -16.5%; volume confirmation (S4) was negative across all periods (`src/RUNLOG.md`, `src/out/improve/summary.csv`).
- Risk management overlay (30-year, `src/RUNLOG.md`, `src/out/improve/summary_erc.csv`): C2 4.4% / -27.5% / Sharpe 0.25, C2E 3.5% / -23.0% / 0.21, C2E1 2.5% / -16.2% / 0.07, book rules B0E -1.9% / -56.3%.

## Verdict and reasons
The verdict is rejected (private note (not published)).
- The book rules have a win rate around 20% and a payoff ratio around 3.9, so after costs the expectancy is zero or negative (`src/RUNLOG.md`, private note (not published)).
- About 20% of trades stopped out on the entry day, half of gap-filled trades stopped out the same day, and the average stop-loss was -8.3% (`src/RUNLOG.md`, private note (not published)).
- Losses were heavy in high-volatility stocks and stocks with distant reference prices, and a market filter (buying only when the index is above its 200-day MA) had no effect (private note (not published)).
- None of the 8 pre-registered improved configurations passed the criteria (beating both book rules and KOSPI in OOS, and beating book rules in IS) (`src/RUNLOG.md`).
- While the improved variants reduced losses and drawdowns, there is no evidence they outperform the index, and risk-adjusted return (Sharpe) was similar to KOSPI (private note (not published)).
- The risk management overlay improved MDD across all 4 configurations, but failed to improve risk-adjusted returns in all 4 (`src/RUNLOG.md`).
- This was because the drawdown brake (triggered at -10%, released at -5%) remained active for 54–99% of the period, blocking recovery (`src/RUNLOG.md`).

## Caveats and limitations
- Survivorship bias: Delisted stocks are absent from the data, so all results are likely overstated compared to reality (private note (not published)).
- Even so, the book rules lost money (`src/RUNLOG.md`).
- Multiple comparisons: 8 improved configurations plus 4 risk management overlays make 12 tests in total, so picking the best one could be due to chance (`src/PREREG_improve.md`, `src/PREREG_erc.md`).
- Data snooping: S1's 4.5% ATR threshold was selected from diagnostics that included OOS data, whereas C2 relies mostly on external pre-specified rules and is relatively clean (`src/RUNLOG.md`, `src/PREREG_improve.md`).
- Specification bug: The initial spec triggered a stop-loss if the entry day's low ≤ stop price, causing nearly all trades to stop out on day one (9% win rate, -99% MDD); Claude Code fixed this during review (`src/RUNLOG.md`, `src/SPEC.md` Section 4).
- Instability: The 5-year window diverged sharply depending on path—Variant A -1.4% vs. Variant B +15.2% (noted as +15.3% in RUNLOG)—and is driven by a handful of big winners (e.g., Sungho Electronics +746%) (`src/RUNLOG.md`, `src/out/summary.csv`).
- Sample period: Over the recent 5 years, KOSPI was very strong at 13.7% annualized, setting a high benchmark (private note (not published)).
- Mechanical vs. discretionary trading: The book's author likely selected trades visually from charts, which differs from mechanically buying every signal (private note (not published)).
- SK Hynix unverified: Over 30 years, SK Hynix was bought only twice (2010 and 2017, both stopped out) and never in 2024–26; the reason was not verified (private note (not published)).
- Post-hoc exploration: The brake-free variant in the risk management overlay (C2En) was post-hoc exploration, not pre-registered (`src/RUNLOG.md`).
- Not reproducible as-is: Raw price data is not in this folder, so the backtest cannot be re-run from this folder alone (private source list).

## What happened next
- Decided not to mechanically trade the book rules as-is (private note (not published)).
- Updated the daily stock alert to use the improved rules (private note (not published)).
- Among stocks passing the 8 conditions, only those with a reference price within +5% of close are listed as "buy watchlist for tomorrow," sent alongside reference price, stop price, half-profit target, position size based on 100M KRW, and a low-liquidity warning (private note (not published)).
- On the first day after switching (Oct 27 close), 19 passed the screen and 1 made the buy watchlist (26M KRW daily trading value) (private note (not published)).
- Wrote a blog post titled "What if you traded 52-week high breakouts by the book for 30 years—100M KRW to 1.57M KRW?", though actual publication is unconfirmed (private note (not published)).
- Follow-up checks previewed in the blog (holding a KOSPI ETF instead of cash, adding a trading-value filter to the improved rules, and why SK Hynix was not triggered in 2024–26) have no execution results confirmed in this folder (private note (not published)).
- Recorded as rejected in the Obsidian note `신고가돌파_261028` (private note (not published)).

## File guide
- `README.md`: This document.
- private note (not published): Blog draft; summarizes rules, diagnostics, improvements, and limitations most readably.
- private note (not published): Obsidian strategy-log note; records the verdict (rejected) and lessons learned.
- `src/SPEC.md`: Rule specification written by Claude Code, incorporating the entry-day stop-loss fix.
- `src/RUNLOG.md`: Self-verification, review fixes, and summary of improved and risk-management results.
- `src/PREREG_improve.md`: Pre-registration document for the 8 improved variants and pass criteria.
- `src/PREREG_erc.md`: Pre-registration document for the 4 risk management (E·R·CR) overlays.
- `src/out/summary.csv`: Summary of book-rule results across periods × variants (A, B, C).
- `src/out/improve/summary.csv`, `summary_erc.csv`, `summary_erc_nobrake.csv`: Summaries for improved variants, risk management overlays, and brake-free runs.
- `src/out/{period}_{variant}/`, `src/out/improve/` subfolders: Daily NAV (`daily.csv`), trade logs (`trades.csv`), metrics (`metrics.json`), and equity curves (`equity.png`) per configuration.
- `src/out/signals_daily.csv`, `diag_30y_A.csv`, `src/diag.py`: Daily signals and 30-year trade diagnostics.
- `src/src/bt.py`: Backtest engine; `bt_before_improve.py` and `bt_before_erc.py` are pre-edit backups, and `bt_improve.py` and `bt_erc.py` are runners.
- `src/WEB_RESEARCH.md`, `research.py`, `dispatch.py`, `*.log.json`, `*.out`: External research and AI agent delegation logs.

