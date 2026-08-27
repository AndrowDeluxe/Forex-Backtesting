"""Follow-up to scripts/research_gold_trend_pullback_atr.py: that full-period
sweep found no combo with a real edge (best PF=0.991, Sharpe=-0.04 at
trend_ema=100/fast_ema=10/stop_atr=3.0/tp_r=3.0 - the params fixed here as
FIXED_* below) but a regime decomposition showed trades clustering in
high-ADX + mid/high-volatility bars perform better than quiet/choppy ones.

This script tests that regime-filter idea PROPERLY:
  - entry/exit params are the ones already fixed by the prior full-period
    sweep (a real limitation, disclosed up front, not re-tuned here)
  - the filter itself (adx_min, and a causal rolling-ATR-quantile vol floor)
    is swept and selected ONLY on the IS period (2016-2022)
  - the selected filter is then applied UNTOUCHED to OOS (2023-2026) - no
    peeking, no re-selection
  - outlier-sensitivity check on the OOS result, since a small OOS trade
    count is exactly where one lucky/unlucky trade can flip the sign

This is the same discipline as scripts/research_gold_pullback_ma_strategy.py
(sweep -> IS/OOS -> outlier check), just applied to a filter instead of the
core signal.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from asian_range_breakout.data import fetch_gold_m15
from gold_trend_pullback_atr.pipeline import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-01-01", "2026-08-01"
SPLIT = pd.Timestamp("2023-01-01", tz="America/New_York")
SPREAD_BPS = 10.0

# Fixed from the prior full-period sweep (research_gold_trend_pullback_atr.py) -
# NOT re-tuned here. Re-tuning them together with the filter on the same data
# would compound the multiple-testing/overfitting risk even further.
FIXED_TREND_EMA = 100
FIXED_FAST_EMA = 10
FIXED_STOP_ATR = 3.0
FIXED_TP_R = 3.0

ADX_MIN_CANDIDATES = [None, 15, 20, 25, 30, 35]
VOL_CANDIDATES = [(None, None), (1000, 0.33), (1000, 0.5), (2000, 0.33), (2000, 0.5)]
MIN_IS_TRADES = 20


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return (
        f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  "
        f"Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"
    )


def main():
    print(f"Fetching GOLD M15 {START} -> {END} ...")
    df = fetch_gold_m15(START, END)
    print(f"{len(df)} M15 bars")

    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=FIXED_STOP_ATR, use_vwap_target=False, take_profit_r=FIXED_TP_R)

    print("\n" + "=" * 78)
    print("0. BASELINE - no regime filter (for reference)")
    print("=" * 78)
    base_signaled = run_pipeline(df, trend_ema=FIXED_TREND_EMA, fast_ema=FIXED_FAST_EMA)
    base_trades = simulate_trades(base_signaled, cfg)
    base_is = base_trades[base_trades["entry_time"] < SPLIT]
    base_oos = base_trades[base_trades["entry_time"] >= SPLIT]
    print(f"  Full: {fmt(summarize(base_trades, base_signaled.index))}")
    print(f"  IS  : {fmt(summarize(base_is, base_signaled[base_signaled.index < SPLIT].index))}")
    print(f"  OOS : {fmt(summarize(base_oos, base_signaled[base_signaled.index >= SPLIT].index))}")

    print("\n" + "=" * 78)
    print("1. FILTER SWEEP - IS PERIOD ONLY (2016-2022)")
    print("=" * 78)
    rows = []
    for adx_min in ADX_MIN_CANDIDATES:
        for vol_window, vol_quantile in VOL_CANDIDATES:
            signaled = run_pipeline(
                df, trend_ema=FIXED_TREND_EMA, fast_ema=FIXED_FAST_EMA,
                adx_min=adx_min, vol_window=vol_window, vol_quantile=vol_quantile,
            )
            is_mask = signaled.index < SPLIT
            trades = simulate_trades(signaled[is_mask], cfg)
            s = summarize(trades, signaled[is_mask].index)
            rows.append({"adx_min": adx_min, "vol_window": vol_window, "vol_quantile": vol_quantile, **s})
            print(f"  adx_min={str(adx_min):>4} vol_window={str(vol_window):>4} vol_q={str(vol_quantile):>4}  {fmt(s)}")

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    if eligible.empty:
        print(f"\nNo filter combo reaches {MIN_IS_TRADES} IS trades - stopping.")
        return
    best = eligible.loc[eligible["sharpe"].idxmax()]
    chosen_adx = None if pd.isna(best["adx_min"]) else float(best["adx_min"])
    chosen_vw = None if pd.isna(best["vol_window"]) else int(best["vol_window"])
    chosen_vq = None if pd.isna(best["vol_quantile"]) else float(best["vol_quantile"])
    print(f"\nChosen filter (best IS Sharpe, n>={MIN_IS_TRADES}): adx_min={chosen_adx}, vol_window={chosen_vw}, vol_quantile={chosen_vq}")
    print(f"  IS with chosen filter: {fmt(best.to_dict())}")

    print("\n" + "=" * 78)
    print("2. OOS VALIDATION - filter applied UNTOUCHED to 2023-2026")
    print("=" * 78)
    signaled = run_pipeline(
        df, trend_ema=FIXED_TREND_EMA, fast_ema=FIXED_FAST_EMA,
        adx_min=chosen_adx, vol_window=chosen_vw, vol_quantile=chosen_vq,
    )
    oos_mask = signaled.index >= SPLIT
    oos_trades = simulate_trades(signaled[oos_mask], cfg)
    oos_stats = summarize(oos_trades, signaled[oos_mask].index)
    print(f"  OOS with chosen filter: {fmt(oos_stats)}")
    print(f"  OOS baseline (no filter, from step 0): {fmt(summarize(base_oos, base_signaled[base_signaled.index >= SPLIT].index))}")

    print("\n" + "=" * 78)
    print("3. OUTLIER-SENSITIVITY CHECK ON OOS (drop single best trade)")
    print("=" * 78)
    if oos_trades.empty:
        print("  No OOS trades with this filter - cannot check.")
    else:
        sorted_ret = oos_trades["return_pct"].sort_values(ascending=False)
        without_best = oos_trades.drop(index=sorted_ret.index[0])
        s_full = summarize(oos_trades, signaled[oos_mask].index)
        s_wo = summarize(without_best, signaled[oos_mask].index)
        print(f"  OOS PF with best trade:    {s_full['profit_factor']:.3f}  (Sharpe {s_full['sharpe']:.2f})")
        print(f"  OOS PF without best trade: {s_wo['profit_factor']:.3f}  (Sharpe {s_wo['sharpe']:.2f})")
        if s_wo["profit_factor"] <= 1.0:
            print("  -> OOS edge collapses without the single best trade: not robust.")
        else:
            print("  -> OOS PF stays above 1.0 without the single best trade.")

    print("\n" + "=" * 78)
    print("4. FULL PERIOD WITH CHOSEN FILTER (for reference only, NOT a validation)")
    print("=" * 78)
    full_trades = simulate_trades(signaled, cfg)
    print(f"  {fmt(summarize(full_trades, signaled.index))}")
    print(f"  Exit reasons: {full_trades['exit_reason'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
