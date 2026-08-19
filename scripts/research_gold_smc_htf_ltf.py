"""Research script: the HTF (H4) -> LTF (M1) SMC entry from the user's
mentor material (CTTNL, chat 2026-08-14) - see gold_smc_htf_ltf/pipeline.py
for the full mechanics (External Range Liquidity, Inducement sweep,
CHoCH/BOS, "trade from liquidity to liquidity" price-level targets).

Genuinely different from every prior gold_m1_momentum_thrust variant this
session: bidirectional (long+short), entries gated by a two-timeframe
liquidity-structure argument instead of a raw momentum/pullback trigger,
and the target is a literal opposing structural price level, not a fixed
R-multiple.

k_htf/k_ltf (fractal lookback) and ltf_shift_confirm_bars are FIXED at
reasonable values from the chat's own smoke test, not swept - the M1
fractal/ERL computation is the expensive part of this pipeline (a Python
loop over the full M1 series) and re-deriving it per sweep combo would
make this script far slower for limited extra insight. htf_valid_bars,
min_target_distance_atr, and stop_atr_mult are swept.

2026-08-14 fix: htf_target used to stay frozen at the price captured on
the H4 signal bar for the whole htf_valid_bars window, so a much-later M1
entry could find the "target" already nearly reached (or already passed)
- the first backtest showed 43% of trades exiting via "target" but only
11% win rate, a dead giveaway. gold_smc_htf_ltf/pipeline.py now expires
the HTF context immediately once its own target is reached, and this
script additionally requires a minimum entry-to-target distance
(min_target_distance_atr) - "no eng. LIQ in target = no A+ Setup."

Same discipline as every other gold script this session: 2024-08-01 to
2026-08-01, IS/OOS split 2025-08-01, sweep IS -> pick best IS Sharpe ->
OOS validate untouched -> outlier check -> buy-and-hold comparison.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_smc_htf_ltf.data import fetch_gold_h4, fetch_gold_m1
from gold_smc_htf_ltf.pipeline import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0
MIN_IS_TRADES = 20

K_HTF, K_LTF, LTF_SHIFT_CONFIRM_BARS = 2, 2, 10
HTF_VALID_BARS_CANDIDATES = [8, 12, 20]
MIN_TARGET_DISTANCE_CANDIDATES = [0.5, 1.0, 2.0]
STOP_ATR_CANDIDATES = [0.3, 0.5, 1.0, 1.5, 2.0]


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return (
        f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  "
        f"Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"
    )


def main():
    print(f"Fetching GOLD H4 {START} -> {END} ...")
    h4 = fetch_gold_h4(START, END)
    print(f"{len(h4)} H4 bars")
    print(f"Fetching GOLD M1 {START} -> {END} ...")
    m1 = fetch_gold_m1(START, END)
    print(f"{len(m1)} M1 bars")

    print("\nRunning HTF/LTF pipeline once per (htf_valid_bars, min_target_distance_atr) candidate ...")
    signaled_by_key = {}
    for hvb in HTF_VALID_BARS_CANDIDATES:
        for mtd in MIN_TARGET_DISTANCE_CANDIDATES:
            signaled = run_pipeline(
                h4, m1, k_htf=K_HTF, k_ltf=K_LTF, htf_valid_bars=hvb,
                ltf_shift_confirm_bars=LTF_SHIFT_CONFIRM_BARS, min_target_distance_atr=mtd,
            )
            signaled_by_key[(hvb, mtd)] = signaled
            n_sig = int((signaled["signal"] != 0).sum())
            print(f"  htf_valid_bars={hvb} min_target_distance_atr={mtd}: {n_sig} raw signals (full period)")

    print("\n" + "=" * 78)
    print(f"1. PARAMETER SWEEP - IS PERIOD ONLY (2024-08 to 2025-08), spread_bps={SPREAD_BPS}")
    print("=" * 78)
    rows = []
    for hvb in HTF_VALID_BARS_CANDIDATES:
        for mtd in MIN_TARGET_DISTANCE_CANDIDATES:
            signaled = signaled_by_key[(hvb, mtd)]
            is_mask = signaled.index < SPLIT
            signaled_is = signaled[is_mask]
            for stop_mult in STOP_ATR_CANDIDATES:
                cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=True)
                trades = simulate_trades(signaled_is, cfg)
                s = summarize(trades, signaled_is.index)
                rows.append({"htf_valid_bars": hvb, "min_target_distance_atr": mtd, "stop_atr": stop_mult, **s})
                print(f"  htf_valid_bars={hvb:>2} min_target_distance_atr={mtd} stop_atr={stop_mult}  {fmt(s)}")

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    if eligible.empty:
        print(f"\nNo combo reaches {MIN_IS_TRADES} IS trades - stopping.")
        return
    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\nStandout combo (highest IS Sharpe, n>={MIN_IS_TRADES}):")
    print(f"  htf_valid_bars={best['htf_valid_bars']}, min_target_distance_atr={best['min_target_distance_atr']}, stop_atr={best['stop_atr']}  {fmt(best.to_dict())}")

    hvb, mtd, sm = int(best["htf_valid_bars"]), float(best["min_target_distance_atr"]), float(best["stop_atr"])

    print("\n" + "=" * 78)
    print("2. OOS VALIDATION - chosen params applied UNTOUCHED to 2025-08 to 2026-08")
    print("=" * 78)
    signaled_full = signaled_by_key[(hvb, mtd)]
    oos_mask = signaled_full.index >= SPLIT
    signaled_oos = signaled_full[oos_mask]
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=sm, use_vwap_target=True)
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
    oos_m1 = m1[m1.index >= SPLIT]
    daily_close = oos_m1["close"].resample("1D").last().dropna()
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
