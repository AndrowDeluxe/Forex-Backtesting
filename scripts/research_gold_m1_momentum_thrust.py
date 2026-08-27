"""Research script: M1 momentum-thrust Gold (XAUUSD) strategy - a genuinely
different entry logic from gold_trend_pullback_atr (which failed to beat
buy-and-hold on every one of 6 filters tested, see chat 2026-08-13/14), not
another filter on the same EMA-pullback core.

Uses M1 bars for entry-timing precision (catch the exact minute a real
thrust starts) but NOT for scalping-frequency holds: a chat viability check
found the average M1 bar range (~5bps at current Gold prices) is the same
order of magnitude as realistic round-trip cost (~4-8bps, from the "Top-
Tipps von Tradern" broker table), so "trade every bar" is cost-doomed by
construction. Stops/targets here are sized in ATR multiples wide enough
(several dollars) that cost is a small fraction of the target, and trades
hold for as many bars as it takes to hit stop/target - not a fixed 1-2 bar
scalp.

2-year window only (2024-08-01 to 2026-08-01, IS/OOS split 2025-08-01) -
M1 bar counts are large (~370k bars/year vs ~25k/year at M15), so a full
10-year fetch+sweep here would be far more expensive for likely limited
extra insight; disclosed as a real limitation, not hidden. Same discipline
as prior gold research in this repo: sweep IS -> pick best IS Sharpe -> OOS
validate untouched -> outlier check -> compare to buy-and-hold.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_m1_momentum_thrust.data import fetch_gold_m1
from gold_m1_momentum_thrust.pipeline import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0  # realistic round-trip cost at M1 (chat viability check), tighter than the 10bps M15-swing convention used elsewhere in this repo, wider than pure mid-spread
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
    print(f"Fetching GOLD M1 {START} -> {END} ... (this can take a while, M1 = a lot of bars)")
    df = fetch_gold_m1(START, END)
    print(f"{len(df)} M1 bars")

    print("\n" + "=" * 78)
    print(f"1. PARAMETER SWEEP - IS PERIOD ONLY (2024-08 to 2025-08), spread_bps={SPREAD_BPS}")
    print("=" * 78)
    is_df = df[df.index < SPLIT]
    rows = []
    for lookback in LOOKBACK_CANDIDATES:
        for mom_min in MOMENTUM_R_CANDIDATES:
            signaled = run_pipeline(is_df, lookback_bars=lookback, momentum_r_min=mom_min, atr_n=ATR_N)
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
        print(f"\nNo combo reaches {MIN_IS_TRADES} IS trades - stopping, material too thin to draw conclusions.")
        return
    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\nStandout combo (highest IS Sharpe, n>={MIN_IS_TRADES}):")
    print(f"  {best[['lookback', 'mom_min', 'stop_atr', 'tp_r']].to_dict()}")
    print(f"  {fmt(best.to_dict())}")

    lb, mm = int(best["lookback"]), float(best["mom_min"])
    sm, tr = float(best["stop_atr"]), float(best["tp_r"])

    print("\n" + "=" * 78)
    print(f"2. OOS VALIDATION - chosen params applied UNTOUCHED to 2025-08 to 2026-08")
    print("=" * 78)
    oos_df = df[df.index >= SPLIT]
    signaled_oos = run_pipeline(oos_df, lookback_bars=lb, momentum_r_min=mm, atr_n=ATR_N)
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
    print("5. EXIT REASON BREAKDOWN (OOS)")
    print("=" * 78)
    if not oos_trades.empty:
        print(oos_trades["exit_reason"].value_counts().to_string())


if __name__ == "__main__":
    main()
