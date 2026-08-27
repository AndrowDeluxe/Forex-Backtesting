"""Cleanly tests EVERY filter built in gold_trend_pullback_atr/{pipeline,filters}.py
(RSI, Bollinger, MACD, session-time, real yield, COT sentiment - the "Top-
Tipps von Tradern" article's ideas, see chat 2026-08-13) ONE AT A TIME,
each with the same IS-tune / OOS-validate discipline already used for the
ADX regime filter (scripts/research_gold_trend_pullback_atr_regime_filter.py):
  - entry/exit params fixed from the original full-period sweep (disclosed
    limitation, not re-tuned here - see that script's docstring)
  - each filter's own threshold is swept and selected on IS (2016-2022) ONLY
  - the selected threshold is applied UNTOUCHED to OOS (2023-2026)
  - outlier-sensitivity check (drop single best trade) on the OOS result
  - final leaderboard compares every filter's OOS Sharpe/PF against the
    no-filter baseline AND the buy-and-hold benchmark (research_gold_
    trend_pullback_atr_vs_buyhold.py: Sharpe=1.11, CAGR=+19.5%) - a filter
    only "wins" if it beats buy-and-hold, not just Sharpe=0.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from asian_range_breakout.cot import fetch_cot_gold, wang_sentiment_index
from asian_range_breakout.data import fetch_gold_m15
from bond_yield_indicator.fred import fetch_us_real_yield
from gold_trend_pullback_atr.filters import apply_cot_sentiment_filter, apply_real_yield_filter
from gold_trend_pullback_atr.pipeline import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 160)

START, END = "2016-01-01", "2026-08-01"
SPLIT = pd.Timestamp("2023-01-01", tz="America/New_York")
SPREAD_BPS = 10.0
MIN_IS_TRADES = 20

FIXED_TREND_EMA, FIXED_FAST_EMA = 100, 10
FIXED_STOP_ATR, FIXED_TP_R = 3.0, 3.0
CFG = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=FIXED_STOP_ATR, use_vwap_target=False, take_profit_r=FIXED_TP_R)

BUYHOLD_OOS = {"sharpe": 1.11, "cagr": 0.195, "max_drawdown": -0.286}  # from research_gold_trend_pullback_atr_vs_buyhold.py

leaderboard = []


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4} WR={s['win_rate']:.1%} PF={s['profit_factor']:.3f} Sharpe={s['sharpe']:.2f} CAGR={s['cagr']:+.1%} MaxDD={s['max_drawdown']:.1%}"


def evaluate_pipeline_filter(name: str, df: pd.DataFrame, candidates: list, apply_kwargs_fn):
    """IS sweep -> pick best IS Sharpe -> OOS validate -> outlier check, for a
    filter implemented as extra kwargs to run_pipeline (per-bar filter)."""
    print(f"\n{'=' * 78}\n{name} - IS sweep\n{'=' * 78}")
    rows = []
    for cand in candidates:
        kwargs = apply_kwargs_fn(cand)
        signaled = run_pipeline(df, trend_ema=FIXED_TREND_EMA, fast_ema=FIXED_FAST_EMA, **kwargs)
        is_mask = signaled.index < SPLIT
        trades = simulate_trades(signaled[is_mask], CFG)
        s = summarize(trades, signaled[is_mask].index)
        rows.append({"cand": cand, **s})
        print(f"  {str(cand):<30} {fmt(s)}")

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    if eligible.empty:
        print(f"  No candidate reaches {MIN_IS_TRADES} IS trades - skipping OOS.")
        leaderboard.append({"filter": name, "chosen": "n/a", "oos_n": 0, "oos_sharpe": float("nan"), "oos_pf": float("nan"), "oos_cagr": float("nan"), "beats_buyhold": False})
        return

    best_row = eligible.loc[eligible["sharpe"].idxmax()]
    chosen = best_row["cand"]
    print(f"  Chosen (best IS Sharpe, n>={MIN_IS_TRADES}): {chosen}  {fmt(best_row.to_dict())}")

    kwargs = apply_kwargs_fn(chosen)
    signaled = run_pipeline(df, trend_ema=FIXED_TREND_EMA, fast_ema=FIXED_FAST_EMA, **kwargs)
    oos_mask = signaled.index >= SPLIT
    oos_trades = simulate_trades(signaled[oos_mask], CFG)
    oos_stats = summarize(oos_trades, signaled[oos_mask].index)
    print(f"  OOS with chosen filter: {fmt(oos_stats)}")
    _outlier_check_and_record(name, chosen, oos_trades, oos_stats, signaled[oos_mask].index)


def evaluate_posthoc_filter(name: str, base_trades_is: pd.DataFrame, base_trades_oos: pd.DataFrame, is_index, oos_index, candidates: list, apply_fn):
    """IS sweep -> pick best IS Sharpe -> OOS validate -> outlier check, for a
    filter implemented as a post-hoc trade-level drop (real yield / COT)."""
    print(f"\n{'=' * 78}\n{name} - IS sweep\n{'=' * 78}")
    rows = []
    for cand in candidates:
        trades = apply_fn(base_trades_is, cand)
        s = summarize(trades, is_index)
        rows.append({"cand": cand, **s})
        print(f"  {str(cand):<30} {fmt(s)}")

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    if eligible.empty:
        print(f"  No candidate reaches {MIN_IS_TRADES} IS trades - skipping OOS.")
        leaderboard.append({"filter": name, "chosen": "n/a", "oos_n": 0, "oos_sharpe": float("nan"), "oos_pf": float("nan"), "oos_cagr": float("nan"), "beats_buyhold": False})
        return

    best_row = eligible.loc[eligible["sharpe"].idxmax()]
    chosen = best_row["cand"]
    print(f"  Chosen (best IS Sharpe, n>={MIN_IS_TRADES}): {chosen}  {fmt(best_row.to_dict())}")

    oos_trades = apply_fn(base_trades_oos, chosen)
    oos_stats = summarize(oos_trades, oos_index)
    print(f"  OOS with chosen filter: {fmt(oos_stats)}")
    _outlier_check_and_record(name, chosen, oos_trades, oos_stats, oos_index)


def _outlier_check_and_record(name, chosen, oos_trades, oos_stats, oos_index):
    if oos_trades.empty:
        print("  No OOS trades - cannot outlier-check.")
        robust = False
    else:
        sorted_ret = oos_trades["return_pct"].sort_values(ascending=False)
        without_best = oos_trades.drop(index=sorted_ret.index[0])
        s_wo = summarize(without_best, oos_index)
        print(f"  Outlier check: PF {oos_stats['profit_factor']:.3f} -> {s_wo['profit_factor']:.3f} without best trade")
        robust = s_wo["profit_factor"] > 1.0

    beats_buyhold = (oos_stats["n_trades"] > 0) and (oos_stats["sharpe"] > BUYHOLD_OOS["sharpe"]) and (oos_stats["cagr"] > BUYHOLD_OOS["cagr"])
    print(f"  Beats buy-and-hold (Sharpe {BUYHOLD_OOS['sharpe']}, CAGR {BUYHOLD_OOS['cagr']:+.1%})? {'YES' if beats_buyhold else 'no'}   Outlier-robust? {'yes' if robust else 'no/n-a'}")
    leaderboard.append({
        "filter": name, "chosen": str(chosen), "oos_n": oos_stats["n_trades"],
        "oos_sharpe": oos_stats["sharpe"], "oos_pf": oos_stats["profit_factor"],
        "oos_cagr": oos_stats["cagr"], "beats_buyhold": beats_buyhold, "outlier_robust": robust,
    })


def main():
    print(f"Fetching GOLD M15 {START} -> {END} ...")
    df = fetch_gold_m15(START, END)
    print(f"{len(df)} M15 bars")

    # --- Baseline (no filter), for reference ---
    base_signaled = run_pipeline(df, trend_ema=FIXED_TREND_EMA, fast_ema=FIXED_FAST_EMA)
    base_trades = simulate_trades(base_signaled, CFG)
    base_is = base_trades[base_trades["entry_time"] < SPLIT]
    base_oos = base_trades[base_trades["entry_time"] >= SPLIT]
    is_index = base_signaled[base_signaled.index < SPLIT].index
    oos_index = base_signaled[base_signaled.index >= SPLIT].index
    print(f"\nBaseline (no filter): Full={fmt(summarize(base_trades, base_signaled.index))}")
    print(f"  IS={fmt(summarize(base_is, is_index))}  OOS={fmt(summarize(base_oos, oos_index))}")

    # --- 1. RSI (avoid overbought) ---
    evaluate_pipeline_filter(
        "RSI (rsi_max)", df,
        candidates=[None, 60.0, 65.0, 70.0, 75.0, 80.0],
        apply_kwargs_fn=lambda c: {"rsi_max": c} if c is not None else {},
    )

    # --- 2. Bollinger not-overbought ---
    evaluate_pipeline_filter(
        "Bollinger (not overbought)", df,
        candidates=[False, True],
        apply_kwargs_fn=lambda c: {"bb_require_not_overbought": c},
    )

    # --- 3. MACD bullish confirmation ---
    evaluate_pipeline_filter(
        "MACD (require bullish)", df,
        candidates=[False, True],
        apply_kwargs_fn=lambda c: {"macd_require_bullish": c},
    )

    # --- 4. Trading session (NY-local hour windows) ---
    evaluate_pipeline_filter(
        "Session (NY-local hours)", df,
        candidates=[None, (2, 8), (8, 12), (8, 17), (12, 17)],
        apply_kwargs_fn=lambda c: {"session_start_hour": c[0], "session_end_hour": c[1]} if c is not None else {},
    )

    # --- 5. Real yield (macro backdrop) ---
    print("\nFetching US real yield (FRED DFII10) ...")
    real_yield = fetch_us_real_yield()
    evaluate_posthoc_filter(
        "Real yield (yield_max)", base_is, base_oos, is_index, oos_index,
        candidates=[None, 0.5, 1.0, 1.5, 2.0, 2.5],
        apply_fn=lambda trades, c: apply_real_yield_filter(trades, real_yield, yield_max=c) if c is not None else trades,
    )

    # --- 6. COT sentiment (avoid crowded-long extremes) ---
    print("\nFetching CFTC COT Gold positioning ...")
    cot = fetch_cot_gold("2010-01-01", END)
    si = wang_sentiment_index(cot["noncomm_net"])
    evaluate_posthoc_filter(
        "COT sentiment (si_max)", base_is, base_oos, is_index, oos_index,
        candidates=[None, 0.3, 0.5, 0.7, 0.8, 0.9],
        apply_fn=lambda trades, c: apply_cot_sentiment_filter(trades, si, si_max=c) if c is not None else trades,
    )

    # --- Leaderboard ---
    print("\n" + "=" * 78)
    print("LEADERBOARD - OOS results, chosen purely from IS, vs. buy-and-hold")
    print(f"Buy & hold benchmark: Sharpe={BUYHOLD_OOS['sharpe']}, CAGR={BUYHOLD_OOS['cagr']:+.1%}, MaxDD={BUYHOLD_OOS['max_drawdown']:.1%}")
    print("=" * 78)
    lb = pd.DataFrame(leaderboard)
    print(lb.to_string(index=False))
    if lb["beats_buyhold"].any():
        winners = lb[lb["beats_buyhold"]]["filter"].tolist()
        print(f"\n>>> Filter(s) that beat buy-and-hold on OOS: {winners}")
    else:
        print("\n>>> No filter beats buy-and-hold on OOS. Consistent with the ADX-filter finding: none of these")
        print("    filters turn this entry into something with a real, standalone edge over simply holding Gold.")


if __name__ == "__main__":
    main()
