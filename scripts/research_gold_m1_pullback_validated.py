"""Follow-up to research_gold_m1_pullback.py: plain momentum/fade/pullback
all failed near-identically on M1 Gold (win rate ~23-26% regardless of
direction hypothesis - chat 2026-08-14), pointing at whipsaw around the
entry (elevated volatility right after a thrust hits a tight symmetric ATR
stop before it hits the target) rather than a directional problem. Two
changes tested here, both from that diagnosis:

1. EXIT: sweep take_profit_r more widely and add BacktestConfig's
   breakeven_trigger_r (move stop to entry once price is far enough in
   favor) - if whipsaw is really the issue, locking in breakeven earlier
   or requiring a bigger target relative to the same stop should show up
   as an improvement even on the unfiltered entry.

2. ENTRY VALIDATION: gate the existing pullback entry on evidence of a
   real support test in the last few bars - SMC-style inducement (liquidity
   sweep + rejection), Nadaraya-Watson lower-band touch, or Bollinger
   lower-band touch (gold_m1_momentum_thrust/validation.py) - instead of
   firing the moment the raw pullback_r threshold is crossed.

Entry params for the base pullback signal are FIXED at the prior script's
own IS-chosen combo (lookback_bars=15, momentum_r_min=3.0, post_thrust_
window=30, pullback_r_min=0.5) - not re-tuned here, to isolate what the
exit/validation changes alone contribute. Same window/discipline as the
other M1 scripts: 2024-08-01 to 2026-08-01, IS/OOS split 2025-08-01,
spread_bps=8.0, sweep IS -> pick best IS Sharpe -> OOS validate untouched
-> outlier check -> buy-and-hold.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_m1_momentum_thrust.data import fetch_gold_m1
from gold_m1_momentum_thrust.pipeline import run_pipeline_pullback
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0
MIN_IS_TRADES = 15  # lower than prior scripts - validation filters cut trade count hard by design

FIXED_LOOKBACK, FIXED_MOM_MIN, FIXED_WINDOW, FIXED_PB_MIN = 15, 3.0, 30, 0.5
FIXED_STOP_ATR = 2.5
TP_CANDIDATES = [1.5, 2.0, 3.0, 4.0]
BE_CANDIDATES = [None, 0.5, 1.0]

FILTER_VARIANTS = {
    "none": dict(),
    "inducement": dict(require_inducement=True),
    "nw_support": dict(require_nw_support=True),
    "bb_touch": dict(require_bb_touch=True),
    "all_three": dict(require_inducement=True, require_nw_support=True, require_bb_touch=True),
}


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return (
        f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  "
        f"Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"
    )


def main():
    print(f"Fetching GOLD M1 {START} -> {END} ...")
    df = fetch_gold_m1(START, END)
    print(f"{len(df)} M1 bars")
    is_df = df[df.index < SPLIT]
    oos_df = df[df.index >= SPLIT]

    all_rows = []
    for variant_name, variant_kwargs in FILTER_VARIANTS.items():
        print("\n" + "=" * 78)
        print(f"VALIDATION VARIANT: {variant_name}  (IS sweep over TP x breakeven)")
        print("=" * 78)
        signaled_is = run_pipeline_pullback(
            is_df, lookback_bars=FIXED_LOOKBACK, momentum_r_min=FIXED_MOM_MIN,
            post_thrust_window=FIXED_WINDOW, pullback_r_min=FIXED_PB_MIN, **variant_kwargs,
        )
        n_signals = int((signaled_is["signal"] != 0).sum())
        print(f"  raw signal count (IS): {n_signals}")

        for tp_r in TP_CANDIDATES:
            for be in BE_CANDIDATES:
                cfg = BacktestConfig(
                    spread_bps=SPREAD_BPS, stop_atr_mult=FIXED_STOP_ATR, use_vwap_target=False,
                    take_profit_r=tp_r, breakeven_trigger_r=be,
                )
                trades = simulate_trades(signaled_is, cfg)
                s = summarize(trades, signaled_is.index)
                all_rows.append({"variant": variant_name, "tp_r": tp_r, "be": be, **s})
                print(f"  tp={tp_r} be={str(be):<5}  {fmt(s)}")

    sweep = pd.DataFrame(all_rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    if eligible.empty:
        print(f"\nNo combo reaches {MIN_IS_TRADES} IS trades anywhere - stopping.")
        return

    print("\n" + "=" * 78)
    print("BEST COMBO PER VALIDATION VARIANT (by IS Sharpe)")
    print("=" * 78)
    chosen_per_variant = {}
    for variant_name in FILTER_VARIANTS:
        sub = eligible[eligible["variant"] == variant_name]
        if sub.empty:
            print(f"  {variant_name:<12} no combo reached {MIN_IS_TRADES} IS trades")
            continue
        best = sub.loc[sub["sharpe"].idxmax()]
        chosen_per_variant[variant_name] = best
        print(f"  {variant_name:<12} tp={best['tp_r']} be={best['be']}  {fmt(best.to_dict())}")

    print("\n" + "=" * 78)
    print("OOS VALIDATION - each variant's own IS-chosen config, applied UNTOUCHED")
    print("=" * 78)
    daily_close = oos_df["close"].resample("1D").last().dropna()
    daily_ret = daily_close.pct_change().fillna(0.0)
    daily_ret.iloc[0] -= SPREAD_BPS / 2 / 1e4
    bh_sharpe, bh_cagr, bh_mdd = annualized_sharpe(daily_ret), cagr(daily_ret), max_drawdown(daily_ret)
    print(f"Buy & hold Gold (same OOS window): Sharpe={bh_sharpe:.2f}  CAGR={bh_cagr:+.1%}  MaxDD={bh_mdd:.1%}")

    leaderboard = []
    for variant_name, best in chosen_per_variant.items():
        variant_kwargs = FILTER_VARIANTS[variant_name]
        signaled_oos = run_pipeline_pullback(
            oos_df, lookback_bars=FIXED_LOOKBACK, momentum_r_min=FIXED_MOM_MIN,
            post_thrust_window=FIXED_WINDOW, pullback_r_min=FIXED_PB_MIN, **variant_kwargs,
        )
        be_val = None if pd.isna(best["be"]) else float(best["be"])
        cfg = BacktestConfig(
            spread_bps=SPREAD_BPS, stop_atr_mult=FIXED_STOP_ATR, use_vwap_target=False,
            take_profit_r=float(best["tp_r"]), breakeven_trigger_r=be_val,
        )
        oos_trades = simulate_trades(signaled_oos, cfg)
        oos_stats = summarize(oos_trades, signaled_oos.index)
        print(f"\n  {variant_name} (tp={best['tp_r']}, be={be_val}): {fmt(oos_stats)}")

        robust = False
        if not oos_trades.empty:
            sorted_ret = oos_trades["return_pct"].sort_values(ascending=False)
            without_best = oos_trades.drop(index=sorted_ret.index[0])
            s_wo = summarize(without_best, signaled_oos.index)
            robust = s_wo["profit_factor"] > 1.0
            print(f"    outlier check: PF {oos_stats['profit_factor']:.3f} -> {s_wo['profit_factor']:.3f} without best trade")

        beats_bh = oos_stats["n_trades"] > 0 and oos_stats["sharpe"] > bh_sharpe and oos_stats["cagr"] > bh_cagr
        print(f"    beats buy-and-hold? {'YES' if beats_bh else 'no'}   outlier-robust? {'yes' if robust else 'no/n-a'}")
        leaderboard.append({
            "variant": variant_name, "tp_r": best["tp_r"], "be": be_val, "oos_n": oos_stats["n_trades"],
            "oos_sharpe": oos_stats["sharpe"], "oos_pf": oos_stats["profit_factor"], "oos_cagr": oos_stats["cagr"],
            "beats_buyhold": beats_bh, "outlier_robust": robust,
        })

    print("\n" + "=" * 78)
    print("LEADERBOARD")
    print("=" * 78)
    lb = pd.DataFrame(leaderboard)
    print(lb.to_string(index=False))
    if lb["beats_buyhold"].any():
        print(f"\n>>> Variant(s) that beat buy-and-hold OOS: {lb[lb['beats_buyhold']]['variant'].tolist()}")
    else:
        print("\n>>> Still no variant beats buy-and-hold OOS.")


if __name__ == "__main__":
    main()
