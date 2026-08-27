"""Research script: M1 Gold (XAUUSD) FADE strategy - short after an
outsized up-thrust, long after an outsized down-thrust. Mirror of
scripts/research_gold_m1_momentum_thrust.py's continuation bet, which
failed catastrophically (Sharpe -5 to -17 across all 36 combos, both IS
and OOS) with a win rate consistently near 20-30% against a ~1:1 R:R -
itself evidence the opposite direction wins more often on this timeframe.
Tested directly here rather than just inferred (chat 2026-08-14).

Same window/discipline as the momentum script: 2024-08-01 to 2026-08-01,
IS/OOS split 2025-08-01, spread_bps=8.0 (M1-realistic round-trip cost),
sweep IS -> pick best IS Sharpe -> OOS validate untouched -> outlier check
-> compare to buy-and-hold.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_m1_momentum_thrust.data import fetch_gold_m1
from gold_m1_momentum_thrust.pipeline import run_pipeline_fade
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0
MIN_IS_TRADES = 20

LOOKBACK_CANDIDATES = [5, 15, 30]
MOMENTUM_R_CANDIDATES = [2.0, 3.0, 4.0]
STOP_ATR_CANDIDATES = [2.0, 3.0]
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
    print("=" * 78)
    is_df = df[df.index < SPLIT]
    rows = []
    for lookback in LOOKBACK_CANDIDATES:
        for mom_min in MOMENTUM_R_CANDIDATES:
            signaled = run_pipeline_fade(is_df, lookback_bars=lookback, momentum_r_min=mom_min, atr_n=ATR_N)
            for stop_mult in STOP_ATR_CANDIDATES:
                for tp_r in TP_R_CANDIDATES:
                    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=False, take_profit_r=tp_r)
                    trades = simulate_trades(signaled, cfg)
                    s = summarize(trades, signaled.index)
                    rows.append({"lookback": lookback, "mom_min": mom_min, "stop_atr": stop_mult, "tp_r": tp_r, **s})
                    print(f"  lookback={lookback:>2} mom_min={mom_min} stop={stop_mult} tp={tp_r}  {fmt(s)}")

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    if eligible.empty:
        print(f"\nNo combo reaches {MIN_IS_TRADES} IS trades - stopping.")
        return
    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\nStandout combo (highest IS Sharpe, n>={MIN_IS_TRADES}):")
    print(f"  {best[['lookback', 'mom_min', 'stop_atr', 'tp_r']].to_dict()}")
    print(f"  {fmt(best.to_dict())}")

    lb, mm = int(best["lookback"]), float(best["mom_min"])
    sm, tr = float(best["stop_atr"]), float(best["tp_r"])

    print("\n" + "=" * 78)
    print("2. OOS VALIDATION - chosen params applied UNTOUCHED to 2025-08 to 2026-08")
    print("=" * 78)
    oos_df = df[df.index >= SPLIT]
    signaled_oos = run_pipeline_fade(oos_df, lookback_bars=lb, momentum_r_min=mm, atr_n=ATR_N)
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=sm, use_vwap_target=False, take_profit_r=tr)
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
    print("5. EXIT REASON + DIRECTION BREAKDOWN (OOS)")
    print("=" * 78)
    if not oos_trades.empty:
        print(oos_trades["exit_reason"].value_counts().to_string())
        print()
        print(oos_trades["direction"].value_counts().to_string())


if __name__ == "__main__":
    main()
