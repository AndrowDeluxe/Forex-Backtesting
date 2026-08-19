"""Research script: the Continuation ("trade WITH the trend") strategy
from gold_smc_htf_ltf/continuation.py - H4 (invalidation) -> H1
(trend-filtered BOS) -> M5 (entry, 2 variants), per the user's mentor
example set (chat 2026-08-14/15, "CTL Beispeil.pdf").

Sweeps: trend_indicator x trend_timeframe x entry_variant x tp_mode (24
combos). stop_atr_mult is FIXED at 1.0 (a reasonable middle value from
earlier gold_smc_htf_ltf sweeps) rather than also swept, to keep this
first pass tractable given how much heavier this pipeline already is
(5 timeframes fetched/merged per combo) than earlier single-timeframe
gold scripts - a follow-up can sweep stop_atr_mult once a promising
trend_indicator/timeframe/variant combo is found here.

tp_mode "h4_level": BacktestConfig(use_vwap_target=True) - the literal H4
opposing liquidity level (see continuation.py). tp_mode "atr":
BacktestConfig(use_vwap_target=False, take_profit_r=3.0) - a flat 3R
target instead, so the two TP philosophies the user asked to compare
("H4 Swing High/Low oder ein variabler ATR-Wert") are directly comparable
side by side.

max_hold_bars=htf_valid_bars*12 (H1->M5 bar ratio) on every config -
mandatory per continuation.py's own docstring (a bug found via smoke
test: h1_target can jump to the wrong side mid-trade if a new H1 context
starts while an M5 trade from the old one is still open).

Same discipline as every other gold script this session: 2024-08-01 to
2026-08-01, IS/OOS split 2025-08-01, sweep IS -> pick best IS Sharpe ->
OOS validate untouched -> outlier check -> buy-and-hold comparison.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_smc_htf_ltf.continuation import run_pipeline
from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m5, fetch_gold_m15, fetch_gold_m30
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0
MIN_IS_TRADES = 15

HTF_VALID_BARS = 24  # H1 bars
STOP_ATR_MULT = 1.0
TREND_INDICATORS = ["ema_cross", "adx_di", "donchian"]
TREND_TIMEFRAMES = ["M15", "M30"]
ENTRY_VARIANTS = ["direct", "double"]
TP_MODES = ["h4_level", "atr"]


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return (
        f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  "
        f"Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"
    )


def build_cfg(tp_mode: str) -> BacktestConfig:
    max_hold = HTF_VALID_BARS * 12
    if tp_mode == "h4_level":
        return BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=STOP_ATR_MULT, use_vwap_target=True, max_hold_bars=max_hold)
    return BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=STOP_ATR_MULT, use_vwap_target=False, take_profit_r=3.0, max_hold_bars=max_hold)


def main():
    print(f"Fetching GOLD H4/H1/M30/M15/M5 {START} -> {END} ...")
    h4 = fetch_gold_h4(START, END)
    h1 = fetch_gold_h1(START, END)
    m30 = fetch_gold_m30(START, END)
    m15 = fetch_gold_m15(START, END)
    m5 = fetch_gold_m5(START, END)
    print(f"H4={len(h4)} H1={len(h1)} M30={len(m30)} M15={len(m15)} M5={len(m5)}")
    trend_frames = {"M15": m15, "M30": m30}

    print("\nRunning pipeline once per (trend_indicator, trend_timeframe, entry_variant) ...")
    signaled_by_key = {}
    for ti in TREND_INDICATORS:
        for tf in TREND_TIMEFRAMES:
            for variant in ENTRY_VARIANTS:
                signaled = run_pipeline(
                    h4, h1, m5, trend_df=trend_frames[tf], trend_indicator=ti,
                    htf_valid_bars=HTF_VALID_BARS, entry_variant=variant,
                )
                signaled_by_key[(ti, tf, variant)] = signaled
                n_sig = int((signaled["signal"] != 0).sum())
                print(f"  {ti:<10} {tf:<4} {variant:<7}: {n_sig} raw signals (full period)")

    print("\n" + "=" * 78)
    print(f"1. SWEEP - IS PERIOD ONLY (2024-08 to 2025-08), spread_bps={SPREAD_BPS}, stop_atr={STOP_ATR_MULT}")
    print("=" * 78)
    rows = []
    for ti in TREND_INDICATORS:
        for tf in TREND_TIMEFRAMES:
            for variant in ENTRY_VARIANTS:
                signaled = signaled_by_key[(ti, tf, variant)]
                signaled_is = signaled[signaled.index < SPLIT]
                for tp_mode in TP_MODES:
                    cfg = build_cfg(tp_mode)
                    trades = simulate_trades(signaled_is, cfg)
                    s = summarize(trades, signaled_is.index)
                    rows.append({"trend_indicator": ti, "trend_tf": tf, "entry_variant": variant, "tp_mode": tp_mode, **s})
                    print(f"  {ti:<10} {tf:<4} {variant:<7} tp={tp_mode:<8}  {fmt(s)}")

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    if eligible.empty:
        print(f"\nNo combo reaches {MIN_IS_TRADES} IS trades - stopping.")
        return
    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\nStandout combo (highest IS Sharpe, n>={MIN_IS_TRADES}):")
    print(f"  {best[['trend_indicator', 'trend_tf', 'entry_variant', 'tp_mode']].to_dict()}")
    print(f"  {fmt(best.to_dict())}")

    ti, tf, variant, tp_mode = best["trend_indicator"], best["trend_tf"], best["entry_variant"], best["tp_mode"]

    print("\n" + "=" * 78)
    print("2. OOS VALIDATION - chosen config applied UNTOUCHED to 2025-08 to 2026-08")
    print("=" * 78)
    signaled_full = signaled_by_key[(ti, tf, variant)]
    signaled_oos = signaled_full[signaled_full.index >= SPLIT]
    cfg = build_cfg(tp_mode)
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
    oos_m5 = m5[m5.index >= SPLIT]
    daily_close = oos_m5["close"].resample("1D").last().dropna()
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
