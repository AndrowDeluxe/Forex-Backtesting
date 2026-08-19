"""Research script: the 3-timeframe REVERSAL cascade from gold_smc_htf_ltf/
reversal_cascade.py - H4 double-manipulation exhaustion -> H1 double-BOS
confirmation -> M15 entry, from the user's own live-chart examples (chat
2026-08-18). Smoke test (chat) already showed a big behavioral
improvement over the single-confirmation mean-reversion attempt (target
exits now 40-73% of trades, not 4% dominated by max_hold) - this is the
proper IS/OOS test.

Sweeps 4 confirmation-layer variants (none / ema_reject / ribbon_stretch /
both) x exit params (stop_atr_mult, breakeven_trigger_r, tp_mode). Real
yield + COT sentiment (chat 2026-08-15/18 request) are applied
POST-HOC as an additional validation layer on the winning config's OOS
trades - reusing gold_trend_pullback_atr.filters directly (already
generic, no need to duplicate).

max_hold_bars = h1_valid_bars(24) * 4 (H1->M15 bar ratio) on every config -
mandatory per continuation.py/reversal_cascade.py's own documented
target-drift bug (vwap/h1_target read fresh each bar by simulate_trades).

Same discipline as every other gold script this session: 2024-08-01 to
2026-08-01, IS/OOS split 2025-08-01, sweep IS -> pick best IS Sharpe ->
OOS validate untouched -> outlier check -> buy-and-hold comparison.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from asian_range_breakout.cot import fetch_cot_gold, wang_sentiment_index
from bond_yield_indicator.fred import fetch_us_real_yield
from gold_smc_htf_ltf.data import fetch_gold_d1, fetch_gold_h1, fetch_gold_h4, fetch_gold_m15, fetch_gold_w1
from gold_smc_htf_ltf.reversal_cascade import run_pipeline
from gold_trend_pullback_atr.filters import apply_cot_sentiment_filter, apply_real_yield_filter
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0
MIN_IS_TRADES = 15
H1_VALID_BARS = 24
MAX_HOLD_BARS = H1_VALID_BARS * 4  # H1 -> M15 bar ratio

STOP_ATR_CANDIDATES = [0.5, 1.0, 1.5]
BE_CANDIDATES = [None, 0.5, 1.0]
TP_R_CANDIDATES = [2.0, 3.0]  # atr mode only, coarse check

VARIANTS = {
    "none": dict(),
    "ema_reject": dict(require_ema_reject=True),
    "ribbon_stretch": dict(require_ribbon_stretch=True),  # d1_df/w1_df injected in main()
    "both": dict(require_ema_reject=True, require_ribbon_stretch=True),
}


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return (
        f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  "
        f"Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"
    )


def main():
    print(f"Fetching GOLD H4/H1/M15/D1/W1 {START} -> {END} ...")
    h4 = fetch_gold_h4(START, END)
    h1 = fetch_gold_h1(START, END)
    m15 = fetch_gold_m15(START, END)
    d1 = fetch_gold_d1(START, END)
    w1 = fetch_gold_w1(START, END)
    print(f"H4={len(h4)} H1={len(h1)} M15={len(m15)} D1={len(d1)} W1={len(w1)}")

    print("\nRunning pipeline once per confirmation-layer variant ...")
    signaled_by_variant = {}
    for name, kwargs in VARIANTS.items():
        if kwargs.get("require_ribbon_stretch"):
            kwargs = {**kwargs, "d1_df": d1, "w1_df": w1}
        signaled = run_pipeline(h4, h1, m15, h1_valid_bars=H1_VALID_BARS, **kwargs)
        signaled_by_variant[name] = signaled
        print(f"  {name:<15}: {int((signaled['signal'] != 0).sum())} raw signals (full period)")

    print("\n" + "=" * 78)
    print(f"1. SWEEP - IS PERIOD ONLY (2024-08 to 2025-08), spread_bps={SPREAD_BPS}, max_hold_bars={MAX_HOLD_BARS}")
    print("=" * 78)
    rows = []
    for name, signaled in signaled_by_variant.items():
        signaled_is = signaled[signaled.index < SPLIT]
        for stop_mult in STOP_ATR_CANDIDATES:
            for be in BE_CANDIDATES:
                cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
                trades = simulate_trades(signaled_is, cfg)
                s = summarize(trades, signaled_is.index)
                rows.append({"variant": name, "tp_mode": "h4_level", "tp_r": None, "stop_atr": stop_mult, "be": be, **s})
        for tp_r in TP_R_CANDIDATES:
            cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=1.0, use_vwap_target=False, take_profit_r=tp_r, max_hold_bars=MAX_HOLD_BARS)
            trades = simulate_trades(signaled_is, cfg)
            s = summarize(trades, signaled_is.index)
            rows.append({"variant": name, "tp_mode": "atr", "tp_r": tp_r, "stop_atr": 1.0, "be": None, **s})
        print(f"  {name} sweep done")

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    if eligible.empty:
        print(f"\nNo combo reaches {MIN_IS_TRADES} IS trades - stopping.")
        return
    top10 = eligible.sort_values("sharpe", ascending=False).head(10)
    print("\nTop 10 combos by IS Sharpe:")
    print(top10[["variant", "tp_mode", "tp_r", "stop_atr", "be", "n_trades", "win_rate", "profit_factor", "sharpe", "cagr", "max_drawdown"]].to_string(index=False))

    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\nStandout combo (highest IS Sharpe, n>={MIN_IS_TRADES}):")
    print(f"  {best[['variant', 'tp_mode', 'tp_r', 'stop_atr', 'be']].to_dict()}")
    print(f"  {fmt(best.to_dict())}")

    variant, tp_mode = best["variant"], best["tp_mode"]
    stop_mult = float(best["stop_atr"])
    be = None if pd.isna(best["be"]) else float(best["be"])

    print("\n" + "=" * 78)
    print("2. OOS VALIDATION - chosen config applied UNTOUCHED to 2025-08 to 2026-08")
    print("=" * 78)
    signaled_full = signaled_by_variant[variant]
    signaled_oos = signaled_full[signaled_full.index >= SPLIT]
    if tp_mode == "h4_level":
        cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
    else:
        cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=False, take_profit_r=float(best["tp_r"]), max_hold_bars=MAX_HOLD_BARS)
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

    print("\n" + "=" * 78)
    print("6. MACRO VALIDATION LAYER (post-hoc, on top of the OOS trades above)")
    print("=" * 78)
    if oos_trades.empty:
        print("  No OOS trades - skipping.")
        return
    print("Fetching real yield + COT ...")
    real_yield = fetch_us_real_yield()
    cot = fetch_cot_gold("2010-01-01", END)
    si = wang_sentiment_index(cot["noncomm_net"])

    for yield_max in [1.0, 2.0]:
        filtered = apply_real_yield_filter(oos_trades, real_yield, yield_max=yield_max)
        s = summarize(filtered, signaled_oos.index)
        print(f"  real_yield <= {yield_max}: {fmt(s)}")
    for si_max in [0.5, 0.8]:
        filtered = apply_cot_sentiment_filter(oos_trades, si, si_max=si_max)
        s = summarize(filtered, signaled_oos.index)
        print(f"  cot_sentiment <= {si_max}: {fmt(s)}")


if __name__ == "__main__":
    main()
