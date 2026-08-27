"""Research script: M1 Gold (XAUUSD) long-only PULLBACK-AFTER-THRUST
strategy - "buy the dip after the spike", not "buy the breakout" (that
failed, see research_gold_m1_momentum_thrust.py) and not short-selling
(that's the separate research_gold_m1_fade.py). Stays long-only, matching
the original "Smart Gold Hunter"-inspired convention this whole family of
strategies started from (chat 2026-08-13).

Two params are FIXED rather than swept to keep the grid tractable given M1
bar counts (lookback_bars=15, stop_atr_mult=2.5 - both reasonable
mid-range values from the momentum/fade sweeps' own candidate sets) -
disclosed scope-control decision, not a hidden assumption. The genuinely
new dimensions this strategy introduces (post_thrust_window, pullback_r_min)
plus momentum_r_min and tp_r are swept.

Same window/discipline as the other two M1 scripts: 2024-08-01 to
2026-08-01, IS/OOS split 2025-08-01, spread_bps=8.0, sweep IS -> pick best
IS Sharpe -> OOS validate untouched -> outlier check -> buy-and-hold.
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
MIN_IS_TRADES = 20

FIXED_LOOKBACK = 15
FIXED_STOP_ATR = 2.5
MOMENTUM_R_CANDIDATES = [3.0, 4.0]
POST_THRUST_WINDOW_CANDIDATES = [30, 60]
PULLBACK_R_CANDIDATES = [0.5, 1.0, 1.5]
TP_R_CANDIDATES = [2.0, 3.0]
ATR_N = 30


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

    print("\n" + "=" * 78)
    print(f"1. PARAMETER SWEEP - IS PERIOD ONLY (2024-08 to 2025-08), spread_bps={SPREAD_BPS}")
    print(f"   (fixed: lookback_bars={FIXED_LOOKBACK}, stop_atr_mult={FIXED_STOP_ATR})")
    print("=" * 78)
    is_df = df[df.index < SPLIT]
    rows = []
    for mom_min in MOMENTUM_R_CANDIDATES:
        for window in POST_THRUST_WINDOW_CANDIDATES:
            for pb_min in PULLBACK_R_CANDIDATES:
                signaled = run_pipeline_pullback(
                    is_df, lookback_bars=FIXED_LOOKBACK, momentum_r_min=mom_min,
                    post_thrust_window=window, pullback_r_min=pb_min, atr_n=ATR_N,
                )
                for tp_r in TP_R_CANDIDATES:
                    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=FIXED_STOP_ATR, use_vwap_target=False, take_profit_r=tp_r)
                    trades = simulate_trades(signaled, cfg)
                    s = summarize(trades, signaled.index)
                    rows.append({"mom_min": mom_min, "window": window, "pb_min": pb_min, "tp_r": tp_r, **s})
                    print(f"  mom_min={mom_min} window={window:>2} pb_min={pb_min} tp={tp_r}  {fmt(s)}")

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    if eligible.empty:
        print(f"\nNo combo reaches {MIN_IS_TRADES} IS trades - stopping.")
        return
    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\nStandout combo (highest IS Sharpe, n>={MIN_IS_TRADES}):")
    print(f"  {best[['mom_min', 'window', 'pb_min', 'tp_r']].to_dict()}")
    print(f"  {fmt(best.to_dict())}")

    mm, window, pb_min, tr = float(best["mom_min"]), int(best["window"]), float(best["pb_min"]), float(best["tp_r"])

    print("\n" + "=" * 78)
    print("2. OOS VALIDATION - chosen params applied UNTOUCHED to 2025-08 to 2026-08")
    print("=" * 78)
    oos_df = df[df.index >= SPLIT]
    signaled_oos = run_pipeline_pullback(
        oos_df, lookback_bars=FIXED_LOOKBACK, momentum_r_min=mm,
        post_thrust_window=window, pullback_r_min=pb_min, atr_n=ATR_N,
    )
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=FIXED_STOP_ATR, use_vwap_target=False, take_profit_r=tr)
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
    print("4. BUY & HOLD COMPARISON (same OOS window, same instrument)")
    print("=" * 78)
    daily_close = oos_df["close"].resample("1D").last().dropna()
    daily_ret = daily_close.pct_change().fillna(0.0)
    daily_ret.iloc[0] -= SPREAD_BPS / 2 / 1e4
    bh_sharpe, bh_cagr, bh_mdd = annualized_sharpe(daily_ret), cagr(daily_ret), max_drawdown(daily_ret)
    total_return = (1 + daily_ret).prod() - 1
    print(f"  Buy & hold Gold:  Sharpe={bh_sharpe:.2f}  CAGR={bh_cagr:+.1%}  MaxDD={bh_mdd:.1%}  total_return={total_return:+.1%}")
    print(f"  Strategy (OOS):   Sharpe={oos_stats['sharpe']:.2f}  CAGR={oos_stats['cagr']:+.1%}  MaxDD={oos_stats['max_drawdown']:.1%}  n_trades={oos_stats['n_trades']}")
    beats = oos_stats["n_trades"] > 0 and oos_stats["sharpe"] > bh_sharpe and oos_stats["cagr"] > bh_cagr
    print(f"\n  Beats buy-and-hold on both Sharpe and CAGR? {'YES' if beats else 'no'}")

    print("\n" + "=" * 78)
    print("5. EXIT REASON BREAKDOWN (OOS)")
    print("=" * 78)
    if not oos_trades.empty:
        print(oos_trades["exit_reason"].value_counts().to_string())


if __name__ == "__main__":
    main()
