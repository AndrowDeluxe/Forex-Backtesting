"""Follow-up to research_gold_smc_reversal_cascade_v2.py, after the
stop-loss bug was fixed and the corrected result showed no edge (chat
2026-08-19). While reviewing the trade chart, the user noticed far fewer
trades than they'd visually expect ("viel zu wenig Trades im Vergleich zu
denen die ich habe"). Funnel diagnostic confirmed: of 381 H4 sweep-and-
reject events over 2 years, only 59 qualified as a "double sweep of the
EXACT SAME level" - the single biggest bottleneck in the whole cascade.

Two relaxations, approved to test in parallel rather than picking one:
  1. level_tolerance_atr on the existing double-sweep requirement (still
     TWO sweeps, but within a zone, not an exact float match).
  2. sweep_mode="single" - drop the second-sweep requirement entirely,
     any single sweep-and-reject of erl_high/erl_low is exhaustion.

Both were added to reversal_cascade.py (compute_h4_exhaustion,
detect_double_sweep). This sweeps sweep_mode/level_tolerance_atr x
confirmation variant (none/ema_reject - dropped h4_trend/both, they never
won and cut frequency further, working against the goal here) x exit
params, same IS/OOS discipline as every prior round.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m15
from gold_smc_htf_ltf.reversal_cascade import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0
MIN_IS_TRADES = 15
H4_CONFIRM_BARS, H1_VALID_BARS = 30, 24
MAX_HOLD_BARS = H1_VALID_BARS * 4

SWEEP_CONFIGS = {
    "double_tol0": dict(sweep_mode="double", level_tolerance_atr=0.0),
    "double_tol0.5": dict(sweep_mode="double", level_tolerance_atr=0.5),
    "double_tol1.0": dict(sweep_mode="double", level_tolerance_atr=1.0),
    "single": dict(sweep_mode="single"),
}
VARIANTS = {"none": dict(), "ema_reject": dict(require_ema_reject=True)}
MTD_CANDIDATES = [0.5, 1.0]
STOP_ATR_CANDIDATES = [0.5, 1.0, 1.5]
BE_CANDIDATES = [None, 0.5, 1.0]


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"


def main():
    print(f"Fetching GOLD H4/H1/M15 {START} -> {END} ...")
    h4 = fetch_gold_h4(START, END)
    h1 = fetch_gold_h1(START, END)
    m15 = fetch_gold_m15(START, END)
    print(f"H4={len(h4)} H1={len(h1)} M15={len(m15)}")

    print("\nRunning pipeline once per (sweep_config, variant, mtd) ...")
    signaled_by_key = {}
    for sname, skwargs in SWEEP_CONFIGS.items():
        for vname, vkwargs in VARIANTS.items():
            for mtd in MTD_CANDIDATES:
                signaled = run_pipeline(h4, h1, m15, h4_confirm_bars=H4_CONFIRM_BARS, h1_valid_bars=H1_VALID_BARS, min_target_distance_atr=mtd, **skwargs, **vkwargs)
                signaled_by_key[(sname, vname, mtd)] = signaled
                n_sig = int((signaled["signal"] != 0).sum())
                print(f"  {sname:<14} {vname:<11} mtd={mtd}: {n_sig} raw signals (full period)")

    print("\n" + "=" * 78)
    print(f"1. SWEEP - IS PERIOD ONLY, spread_bps={SPREAD_BPS}, max_hold_bars={MAX_HOLD_BARS}")
    print("=" * 78)
    rows = []
    for (sname, vname, mtd), signaled in signaled_by_key.items():
        signaled_is = signaled[signaled.index < SPLIT]
        for stop_mult in STOP_ATR_CANDIDATES:
            for be in BE_CANDIDATES:
                cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
                trades = simulate_trades(signaled_is, cfg)
                s = summarize(trades, signaled_is.index)
                rows.append({"sweep_cfg": sname, "variant": vname, "mtd": mtd, "stop_atr": stop_mult, "be": be, **s})

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    print(f"\n{len(sweep)} combos tested, {len(eligible)} reach n>={MIN_IS_TRADES} IS trades")
    if eligible.empty:
        print("Stopping.")
        return
    top15 = eligible.sort_values("sharpe", ascending=False).head(15)
    print("\nTop 15 combos by IS Sharpe:")
    print(top15[["sweep_cfg", "variant", "mtd", "stop_atr", "be", "n_trades", "win_rate", "profit_factor", "sharpe", "cagr"]].to_string(index=False))

    # Also show best-per-sweep_cfg, to see whether looser signal classes carry ANY edge at all
    print("\nBest combo PER sweep_cfg (by IS Sharpe, n>=15):")
    for sname in SWEEP_CONFIGS:
        sub = eligible[eligible["sweep_cfg"] == sname]
        if sub.empty:
            print(f"  {sname}: no combo reaches n>={MIN_IS_TRADES}")
            continue
        b = sub.loc[sub["sharpe"].idxmax()]
        print(f"  {sname:<14} variant={b['variant']:<11} mtd={b['mtd']} stop={b['stop_atr']} be={b['be']}  {fmt(b.to_dict())}")

    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\nStandout combo overall (highest IS Sharpe, n>={MIN_IS_TRADES}):")
    print(f"  {best[['sweep_cfg', 'variant', 'mtd', 'stop_atr', 'be']].to_dict()}")
    print(f"  {fmt(best.to_dict())}")

    sname, vname, mtd = best["sweep_cfg"], best["variant"], float(best["mtd"])
    stop_mult = float(best["stop_atr"])
    be = None if pd.isna(best["be"]) else float(best["be"])

    print("\n" + "=" * 78)
    print("2. OOS VALIDATION - chosen config applied UNTOUCHED to 2025-08 to 2026-08")
    print("=" * 78)
    signaled_full = signaled_by_key[(sname, vname, mtd)]
    signaled_oos = signaled_full[signaled_full.index >= SPLIT]
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
    oos_trades = simulate_trades(signaled_oos, cfg)
    oos_stats = summarize(oos_trades, signaled_oos.index)
    print(f"  OOS: {fmt(oos_stats)}")

    print("\n" + "=" * 78)
    print("3. OUTLIER-SENSITIVITY CHECK ON OOS (drop single best trade)")
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
    print("4. BUY & HOLD COMPARISON (same OOS window)")
    print("=" * 78)
    m15_oos = m15[m15.index >= SPLIT]
    daily_close = m15_oos["close"].resample("1D").last().dropna()
    daily_ret = daily_close.pct_change().fillna(0.0)
    daily_ret.iloc[0] -= SPREAD_BPS / 2 / 1e4
    bh_sharpe, bh_cagr, bh_mdd = annualized_sharpe(daily_ret), cagr(daily_ret), max_drawdown(daily_ret)
    print(f"  Buy & hold Gold:  Sharpe={bh_sharpe:.2f}  CAGR={bh_cagr:+.1%}  MaxDD={bh_mdd:.1%}")
    print(f"  Strategy (OOS):   Sharpe={oos_stats['sharpe']:.2f}  CAGR={oos_stats['cagr']:+.1%}  MaxDD={oos_stats['max_drawdown']:.1%}  n_trades={oos_stats['n_trades']}")
    beats_sharpe = oos_stats["n_trades"] > 0 and oos_stats["sharpe"] > bh_sharpe
    beats_both = beats_sharpe and oos_stats["cagr"] > bh_cagr
    print(f"\n  Beats buy-and-hold on Sharpe? {'YES' if beats_sharpe else 'no'}   On both Sharpe and CAGR? {'YES' if beats_both else 'no'}")

    print("\n" + "=" * 78)
    print("5. EXIT REASON + DIRECTION BREAKDOWN (OOS)")
    print("=" * 78)
    if not oos_trades.empty:
        print(oos_trades["exit_reason"].value_counts().to_string())
        print()
        print(oos_trades["direction"].value_counts().to_string())


if __name__ == "__main__":
    main()
