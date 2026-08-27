"""asia_ote Stage 1 (chat 2026-08-21): structural sweep - entry_variant x
premium_ratio x direction_mode x target_mode - with exit params held at
reasonable defaults (min_target_distance_atr=1.0, entry_window_end_hour=
12.0, stop_buffer=0.0 exact Asia-extreme stop, max_hold=384 M15 bars/96h,
no breakeven). Same IS/OOS discipline as the rest of this repo: sweep on
IS only, pick by IS Sharpe (n>=15 guard), validate untouched on OOS.

Goal: narrow the open structural design choices (mentor's discretionary
material, several explicitly-flagged interpretation options) down to the
1-2 combinations worth a full exit-parameter sweep in stage 2, before
spending compute on exit-tuning a structurally-wrong setup."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from asia_ote.data import fetch_eurusd_d1, fetch_eurusd_h1, fetch_eurusd_h4, fetch_eurusd_m15
from asia_ote.engine import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="Europe/Berlin")
SPREAD_BPS = 8.0
MIN_IS_TRADES = 15

DEFAULT_CFG = dict(min_target_distance_atr=1.0, entry_window_end_hour=12.0)
BACKTEST_CFG = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=0.0, use_vwap_target=True, max_hold_bars=384)

ENTRY_VARIANTS = ["fib_limit", "candle_reaction", "range_breakout"]
PREMIUM_RATIOS = [0.568, 0.618, 0.718, 0.86]
DIRECTION_MODES = ["trend_strength", "prev_asia"]
TARGET_MODES = ["untested_asia", "monthly_pivot"]


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:>6.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"


def main():
    print(f"Fetching EURUSD M15/H1/D1 {START} -> {END} ...")
    m15 = fetch_eurusd_m15(START, END)
    h1 = fetch_eurusd_h1(START, END)
    d1 = fetch_eurusd_d1("2024-01-01", END)
    print(f"M15={len(m15)} H1={len(h1)} D1={len(d1)}")

    rows = []
    combos = []
    for entry_variant in ENTRY_VARIANTS:
        ratio_candidates = PREMIUM_RATIOS if entry_variant != "range_breakout" else [None]
        for premium_ratio in ratio_candidates:
            for direction_mode in DIRECTION_MODES:
                for target_mode in TARGET_MODES:
                    combos.append((entry_variant, premium_ratio, direction_mode, target_mode))

    print(f"\nRunning {len(combos)} structural combos ...")
    for entry_variant, premium_ratio, direction_mode, target_mode in combos:
        kwargs = dict(entry_variant=entry_variant, direction_mode=direction_mode, target_mode=target_mode, **DEFAULT_CFG)
        if premium_ratio is not None:
            kwargs["premium_ratio"] = premium_ratio
        try:
            sig = run_pipeline(m15, d1, trend_df=h1, **kwargs)
        except Exception as e:
            print(f"  FAILED {entry_variant}/{premium_ratio}/{direction_mode}/{target_mode}: {e}")
            continue

        sig_is = sig[sig.index < SPLIT]
        sig_oos = sig[sig.index >= SPLIT]
        is_trades = simulate_trades(sig_is, BACKTEST_CFG)
        is_stats = summarize(is_trades, sig_is.index)
        rows.append({
            "entry_variant": entry_variant, "premium_ratio": premium_ratio, "direction_mode": direction_mode, "target_mode": target_mode,
            "n_raw": int((sig["signal"] != 0).sum()), **is_stats,
        })

    sweep = pd.DataFrame(rows)
    sweep.to_csv(Path(__file__).resolve().parents[1] / "asia_ote" / "_stage1_structure_sweep.csv", index=False)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    print(f"\n{len(sweep)} combos tested, {len(eligible)} reach n>={MIN_IS_TRADES} IS trades")

    print("\nTop 15 by IS Sharpe:")
    top15 = eligible.sort_values("sharpe", ascending=False).head(15)
    print(top15[["entry_variant", "premium_ratio", "direction_mode", "target_mode", "n_trades", "win_rate", "profit_factor", "sharpe", "cagr"]].to_string(index=False))

    print("\nBest combo PER entry_variant (by IS Sharpe, n>=15):")
    for entry_variant in ENTRY_VARIANTS:
        sub = eligible[eligible["entry_variant"] == entry_variant]
        if sub.empty:
            print(f"  {entry_variant:<16}: no combo reaches n>={MIN_IS_TRADES}")
            continue
        b = sub.loc[sub["sharpe"].idxmax()]
        print(f"  {entry_variant:<16} ratio={b['premium_ratio']} dir={b['direction_mode']} target={b['target_mode']}  {fmt(b.to_dict())}")

        kwargs = dict(entry_variant=entry_variant, direction_mode=b["direction_mode"], target_mode=b["target_mode"], **DEFAULT_CFG)
        if pd.notna(b["premium_ratio"]):
            kwargs["premium_ratio"] = float(b["premium_ratio"])
        sig_full = run_pipeline(m15, d1, trend_df=h1, **kwargs)
        sig_oos = sig_full[sig_full.index >= SPLIT]
        oos_trades = simulate_trades(sig_oos, BACKTEST_CFG)
        oos_stats = summarize(oos_trades, sig_oos.index)
        print(f"    -> OOS: {fmt(oos_stats)}")

    daily_close = m15[m15.index >= SPLIT]["close"].resample("1D").last().dropna()
    daily_ret = daily_close.pct_change().fillna(0.0)
    daily_ret.iloc[0] -= SPREAD_BPS / 2 / 1e4
    print(f"\nBuy & Hold EURUSD (OOS): Sharpe={annualized_sharpe(daily_ret):.2f}  CAGR={cagr(daily_ret):+.1%}  MaxDD={max_drawdown(daily_ret):.1%}")


if __name__ == "__main__":
    main()
