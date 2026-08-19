"""Follow-up to research_gold_smc_reversal_cascade_v5.py (chat 2026-08-19,
"wie sieht der neue EMA Filter als Entry Logik aus? Ein Cross oder Touch
des Kurses an die EMA"). Every prior EMA usage in this module
(require_ema_reject, require_h4_trend_confirm) was a STATE condition (is
price/EMA currently on the right side), not a genuine entry-triggering
EVENT - user asked to test EMA cross/touch as the actual M15 ENTRY
mechanism, replacing the sweep-and-reject of h1_ref_level (new
m15_entry_mode param on reversal_cascade.run_pipeline).

Structural axis: "sweep" (baseline, unchanged) vs. "ema_cross" (3 fast/
slow pairs) vs. "ema_touch" (2 lengths x 3 tolerance bands) - h4/h1 stage
fixed at the standing-best config (h4_confirm=30, h1_valid=24, ema_reject
require on H4, sweep_mode=double/tol=0, h1_bos_min=2, no inducement/
magnitude/volume/age - none of those improved on the baseline per v3-v5).
Crossed with the usual exit-param sweep.
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

STRUCT_CONFIGS = {
    "sweep": dict(m15_entry_mode="sweep"),
    "ema_cross_12_26": dict(m15_entry_mode="ema_cross", m15_ema_fast=12, m15_ema_slow=26),
    "ema_cross_8_21": dict(m15_entry_mode="ema_cross", m15_ema_fast=8, m15_ema_slow=21),
    "ema_cross_20_50": dict(m15_entry_mode="ema_cross", m15_ema_fast=20, m15_ema_slow=50),
    "ema_touch_20_0.2": dict(m15_entry_mode="ema_touch", m15_ema_length=20, m15_ema_touch_atr=0.2),
    "ema_touch_20_0.3": dict(m15_entry_mode="ema_touch", m15_ema_length=20, m15_ema_touch_atr=0.3),
    "ema_touch_50_0.2": dict(m15_entry_mode="ema_touch", m15_ema_length=50, m15_ema_touch_atr=0.2),
    "ema_touch_50_0.3": dict(m15_entry_mode="ema_touch", m15_ema_length=50, m15_ema_touch_atr=0.3),
    "ema_touch_50_0.5": dict(m15_entry_mode="ema_touch", m15_ema_length=50, m15_ema_touch_atr=0.5),
}
STOP_ATR_CANDIDATES = [0.5, 1.0, 1.5, 3.0]
BE_CANDIDATES = [None, 0.5, 1.0]
MTD = 0.5


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

    print("\nRunning pipeline once per struct_cfg ...")
    signaled_by_key = {}
    for sname, skwargs in STRUCT_CONFIGS.items():
        sig = run_pipeline(h4, h1, m15, h4_confirm_bars=H4_CONFIRM_BARS, h1_valid_bars=H1_VALID_BARS, min_target_distance_atr=MTD, require_ema_reject=True, **skwargs)
        signaled_by_key[sname] = sig
        n = int((sig["signal"] != 0).sum())
        print(f"  {sname:<20}: {n} raw signals")

    print("\n" + "=" * 78)
    print(f"1. SWEEP - IS PERIOD ONLY, spread_bps={SPREAD_BPS}, max_hold_bars={MAX_HOLD_BARS}")
    print("=" * 78)
    rows = []
    for sname, sig in signaled_by_key.items():
        sig_is = sig[sig.index < SPLIT]
        for stop_mult in STOP_ATR_CANDIDATES:
            for be in BE_CANDIDATES:
                cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
                trades = simulate_trades(sig_is, cfg)
                s = summarize(trades, sig_is.index)
                rows.append({"struct": sname, "stop_atr": stop_mult, "be": be, **s})

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    print(f"\n{len(sweep)} combos tested, {len(eligible)} reach n>={MIN_IS_TRADES} IS trades")
    if eligible.empty:
        print("Stopping.")
        return
    top15 = eligible.sort_values("sharpe", ascending=False).head(15)
    print("\nTop 15 combos by IS Sharpe:")
    print(top15[["struct", "stop_atr", "be", "n_trades", "win_rate", "profit_factor", "sharpe", "cagr"]].to_string(index=False))

    print("\nBest combo PER struct config (by IS Sharpe, n>=15):")
    for sname in STRUCT_CONFIGS:
        sub = eligible[eligible["struct"] == sname]
        if sub.empty:
            print(f"  {sname:<20}: no combo reaches n>={MIN_IS_TRADES}")
            continue
        b = sub.loc[sub["sharpe"].idxmax()]
        print(f"  {sname:<20} stop={b['stop_atr']} be={b['be']}  {fmt(b.to_dict())}")

    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\nStandout combo overall (highest IS Sharpe, n>={MIN_IS_TRADES}):")
    print(f"  struct={best['struct']}  stop={best['stop_atr']}  be={best['be']}")
    print(f"  {fmt(best.to_dict())}")

    sname = best["struct"]
    stop_mult = float(best["stop_atr"])
    be = None if pd.isna(best["be"]) else float(best["be"])

    print("\n" + "=" * 78)
    print("2. OOS VALIDATION - chosen config applied UNTOUCHED to 2025-08 to 2026-08")
    print("=" * 78)
    sig_full = signaled_by_key[sname]
    sig_oos = sig_full[sig_full.index >= SPLIT]
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
    oos_trades = simulate_trades(sig_oos, cfg)
    oos_stats = summarize(oos_trades, sig_oos.index)
    print(f"  OOS: {fmt(oos_stats)}")

    print("\n" + "=" * 78)
    print("3. OUTLIER-SENSITIVITY CHECK ON OOS (drop single best trade)")
    print("=" * 78)
    if oos_trades.empty:
        print("  No OOS trades - cannot check.")
    else:
        sorted_ret = oos_trades["return_pct"].sort_values(ascending=False)
        without_best = oos_trades.drop(index=sorted_ret.index[0])
        s_wo = summarize(without_best, sig_oos.index)
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
