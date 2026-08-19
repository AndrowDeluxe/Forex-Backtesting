"""Follow-up to research_gold_smc_continuation.py: that sweep found the
first genuinely positive, outlier-robust result all session - adx_di
trend filter on M15, entry_variant="direct", tp_mode="h4_level" (IS
Sharpe=0.85, OOS Sharpe=1.41, OOS PF=2.589, doesn't collapse without the
best trade). Base signal (trend_indicator/trend_tf/entry_variant) is
FIXED at that winner here - this script "nach Playbook" (chat 2026-08-15)
optimizes the EXIT side: stop_atr_mult, breakeven_trigger_r, and TP
(both modes - h4_level's own min_target_distance_atr, and atr's
take_profit_r).

Two TP-mode sub-sweeps (min_target_distance_atr affects entry filtering,
so it needs its own pipeline recomputation per candidate; stop/BE don't
affect the signal at all, only simulate_trades, so they're swept cheaply
within a fixed signaled frame):
  A) tp_mode=h4_level: min_target_distance_atr x stop_atr_mult x
     breakeven_trigger_r
  B) tp_mode=atr: take_profit_r x stop_atr_mult x breakeven_trigger_r
     (min_target_distance_atr fixed at 1.0 - it's just an entry-quality
     gate here, not the TP mechanism itself)

max_hold_bars stays fixed at htf_valid_bars*12 on every config (mandatory
per continuation.py's docstring - vwap/h1_target can drift mid-trade
otherwise). Same discipline as every other gold script this session:
2024-08-01 to 2026-08-01, IS/OOS split 2025-08-01, sweep IS -> pick best
IS Sharpe -> OOS validate untouched -> outlier check -> buy-and-hold.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_smc_htf_ltf.continuation import run_pipeline
from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m5, fetch_gold_m15
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0
MIN_IS_TRADES = 15

HTF_VALID_BARS = 24  # H1 bars
MAX_HOLD_BARS = HTF_VALID_BARS * 12
TREND_INDICATOR, TREND_TF, ENTRY_VARIANT = "adx_di", "M15", "direct"

STOP_ATR_CANDIDATES = [0.5, 1.0, 1.5, 2.0, 3.0]
BE_CANDIDATES = [None, 0.5, 1.0, 1.5]
MIN_TARGET_DIST_CANDIDATES = [0.5, 1.0, 2.0]  # h4_level mode only
TP_R_CANDIDATES = [2.0, 3.0, 4.0, 5.0]  # atr mode only
FIXED_MIN_TARGET_DIST_FOR_ATR_MODE = 1.0


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return (
        f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  "
        f"Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"
    )


def main():
    print(f"Fetching GOLD H4/H1/M15/M5 {START} -> {END} ...")
    h4 = fetch_gold_h4(START, END)
    h1 = fetch_gold_h1(START, END)
    m15 = fetch_gold_m15(START, END)
    m5 = fetch_gold_m5(START, END)
    print(f"H4={len(h4)} H1={len(h1)} M15={len(m15)} M5={len(m5)}")

    rows = []

    # --- A) tp_mode=h4_level ---
    print("\n" + "=" * 78)
    print("A) TP MODE = h4_level  -  IS sweep (2024-08 to 2025-08)")
    print("=" * 78)
    signaled_by_mtd = {}
    for mtd in MIN_TARGET_DIST_CANDIDATES:
        signaled = run_pipeline(
            h4, h1, m5, trend_df=m15, trend_indicator=TREND_INDICATOR,
            htf_valid_bars=HTF_VALID_BARS, entry_variant=ENTRY_VARIANT, min_target_distance_atr=mtd,
        )
        signaled_by_mtd[mtd] = signaled
        print(f"  min_target_distance_atr={mtd}: {int((signaled['signal'] != 0).sum())} raw signals (full period)")

    for mtd in MIN_TARGET_DIST_CANDIDATES:
        signaled_is = signaled_by_mtd[mtd][signaled_by_mtd[mtd].index < SPLIT]
        for stop_mult in STOP_ATR_CANDIDATES:
            for be in BE_CANDIDATES:
                cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
                trades = simulate_trades(signaled_is, cfg)
                s = summarize(trades, signaled_is.index)
                rows.append({"tp_mode": "h4_level", "mtd": mtd, "tp_r": None, "stop_atr": stop_mult, "be": be, **s})
                print(f"  mtd={mtd} stop={stop_mult} be={str(be):<5}  {fmt(s)}")

    # --- B) tp_mode=atr ---
    print("\n" + "=" * 78)
    print("B) TP MODE = atr  -  IS sweep (2024-08 to 2025-08)")
    print("=" * 78)
    signaled_atr = run_pipeline(
        h4, h1, m5, trend_df=m15, trend_indicator=TREND_INDICATOR,
        htf_valid_bars=HTF_VALID_BARS, entry_variant=ENTRY_VARIANT, min_target_distance_atr=FIXED_MIN_TARGET_DIST_FOR_ATR_MODE,
    )
    signaled_atr_is = signaled_atr[signaled_atr.index < SPLIT]
    print(f"  {int((signaled_atr['signal'] != 0).sum())} raw signals (full period)")

    for tp_r in TP_R_CANDIDATES:
        for stop_mult in STOP_ATR_CANDIDATES:
            for be in BE_CANDIDATES:
                cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=False, take_profit_r=tp_r, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
                trades = simulate_trades(signaled_atr_is, cfg)
                s = summarize(trades, signaled_atr_is.index)
                rows.append({"tp_mode": "atr", "mtd": FIXED_MIN_TARGET_DIST_FOR_ATR_MODE, "tp_r": tp_r, "stop_atr": stop_mult, "be": be, **s})
                print(f"  tp_r={tp_r} stop={stop_mult} be={str(be):<5}  {fmt(s)}")

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    if eligible.empty:
        print(f"\nNo combo reaches {MIN_IS_TRADES} IS trades - stopping.")
        return
    best = eligible.loc[eligible["sharpe"].idxmax()]
    print("\n" + "=" * 78)
    print(f"Standout combo (highest IS Sharpe, n>={MIN_IS_TRADES}):")
    print("=" * 78)
    print(f"  {best[['tp_mode', 'mtd', 'tp_r', 'stop_atr', 'be']].to_dict()}")
    print(f"  {fmt(best.to_dict())}")

    tp_mode = best["tp_mode"]
    stop_mult, be = float(best["stop_atr"]), (None if pd.isna(best["be"]) else float(best["be"]))

    print("\n" + "=" * 78)
    print("OOS VALIDATION - chosen config applied UNTOUCHED to 2025-08 to 2026-08")
    print("=" * 78)
    if tp_mode == "h4_level":
        mtd = float(best["mtd"])
        signaled_full = signaled_by_mtd[mtd]
        cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
    else:
        tp_r = float(best["tp_r"])
        signaled_full = signaled_atr
        cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=False, take_profit_r=tp_r, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)

    signaled_oos = signaled_full[signaled_full.index >= SPLIT]
    oos_trades = simulate_trades(signaled_oos, cfg)
    oos_stats = summarize(oos_trades, signaled_oos.index)
    print(f"  OOS: {fmt(oos_stats)}")

    print("\n" + "=" * 78)
    print("OUTLIER-SENSITIVITY CHECK ON OOS (drop single best trade)")
    print("=" * 78)
    if oos_trades.empty:
        print("  No OOS trades - cannot check.")
    else:
        sorted_ret = oos_trades["return_pct"].sort_values(ascending=False)
        without_best = oos_trades.drop(index=sorted_ret.index[0])
        s_wo = summarize(without_best, signaled_oos.index)
        print(f"  OOS PF with best trade:    {oos_stats['profit_factor']:.3f}  (Sharpe {oos_stats['sharpe']:.2f})")
        print(f"  OOS PF without best trade: {s_wo['profit_factor']:.3f}  (Sharpe {s_wo['sharpe']:.2f})")
        print("  -> " + ("OOS PF stays above 1.0 without the single best trade." if s_wo["profit_factor"] > 1.0 else "OOS edge collapses without the single best trade: not robust."))

    print("\n" + "=" * 78)
    print("BUY & HOLD COMPARISON (same OOS window, same instrument)")
    print("=" * 78)
    oos_m5 = m5[m5.index >= SPLIT]
    daily_close = oos_m5["close"].resample("1D").last().dropna()
    daily_ret = daily_close.pct_change().fillna(0.0)
    daily_ret.iloc[0] -= SPREAD_BPS / 2 / 1e4
    bh_sharpe, bh_cagr, bh_mdd = annualized_sharpe(daily_ret), cagr(daily_ret), max_drawdown(daily_ret)
    print(f"  Buy & hold Gold:  Sharpe={bh_sharpe:.2f}  CAGR={bh_cagr:+.1%}  MaxDD={bh_mdd:.1%}")
    print(f"  Strategy (OOS):   Sharpe={oos_stats['sharpe']:.2f}  CAGR={oos_stats['cagr']:+.1%}  MaxDD={oos_stats['max_drawdown']:.1%}  n_trades={oos_stats['n_trades']}")
    beats_sharpe = oos_stats["n_trades"] > 0 and oos_stats["sharpe"] > bh_sharpe
    beats_both = beats_sharpe and oos_stats["cagr"] > bh_cagr
    print(f"\n  Beats buy-and-hold on Sharpe? {'YES' if beats_sharpe else 'no'}   On both Sharpe and CAGR? {'YES' if beats_both else 'no'}")

    print("\n" + "=" * 78)
    print("EXIT REASON + DIRECTION BREAKDOWN (OOS)")
    print("=" * 78)
    if not oos_trades.empty:
        print(oos_trades["exit_reason"].value_counts().to_string())
        print()
        print(oos_trades["direction"].value_counts().to_string())


if __name__ == "__main__":
    main()
