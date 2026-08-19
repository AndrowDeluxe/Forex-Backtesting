"""Follow-up to research_gold_smc_mean_reversion.py: that sweep found NO
profitable combo across 162 tests (best IS Sharpe was still -0.13,
OOS Sharpe -2.19, not outlier-robust) - a clean, thorough negative result
for the "double BOS then fade" mean-reversion signal, even with the HTF
trend-strength gate.

This script adds the volume-pressure confirmation from gold_smc_htf_ltf/
volume.py (chat 2026-08-15): require genuine counter-direction volume
pressure (not just any sweep) before fading - short fades need real
recent SELLING pressure, long fades need real recent BUYING pressure.
User's own framing: if this STILL comes back negative, the entry logic
itself needs rebuilding (e.g. anchoring off older historical ranges
instead of just the latest fractal swing), not just another filter.

breakeven_trigger_r is fixed at None (not swept) - every prior sweep this
session (M1 momentum family, continuation.py) found breakeven hurts
consistently, no reason to expect otherwise here. htf_adx_min trimmed to
{None, 20.0} (the prior sweep found the ADX gate made no real difference)
to keep this combined sweep tractable.

Same discipline as every other gold script this session: 2024-08-01 to
2026-08-01, IS/OOS split 2025-08-01, sweep IS -> pick best IS Sharpe ->
OOS validate untouched -> outlier check -> buy-and-hold comparison.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_m5, fetch_gold_m15
from gold_smc_htf_ltf.mean_reversion import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0
MIN_IS_TRADES = 15
MAX_HOLD_BARS = 200

TIMEFRAMES = ["M5", "M15"]
VOL_ZSCORE_CANDIDATES = [None, 0.5, 1.0, 1.5, 2.0]
HTF_ADX_MIN_CANDIDATES = [None, 20.0]
STOP_ATR_CANDIDATES = [1.0, 1.5]
TP_R_CANDIDATES = [2.0, 3.0]


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return (
        f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  "
        f"Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"
    )


def main():
    print(f"Fetching GOLD H1/M15/M5 {START} -> {END} ...")
    h1 = fetch_gold_h1(START, END)
    m15 = fetch_gold_m15(START, END)
    m5 = fetch_gold_m5(START, END)
    print(f"H1={len(h1)} M15={len(m15)} M5={len(m5)}")
    ltf_frames = {"M5": m5, "M15": m15}

    print("\nRunning pipeline once per (timeframe, vol_zscore_min, htf_adx_min) ...")
    signaled_by_key = {}
    for tf in TIMEFRAMES:
        for vz in VOL_ZSCORE_CANDIDATES:
            for adx_min in HTF_ADX_MIN_CANDIDATES:
                signaled = run_pipeline(ltf_frames[tf], htf_df=h1 if adx_min else None, htf_adx_min=adx_min, vol_zscore_min=vz)
                signaled_by_key[(tf, vz, adx_min)] = signaled
                n_sig = int((signaled["signal"] != 0).sum())
                print(f"  {tf:<4} vol_zscore_min={str(vz):<5} htf_adx_min={adx_min}: {n_sig} raw signals (full period)")

    print("\n" + "=" * 78)
    print(f"1. SWEEP - IS PERIOD ONLY (2024-08 to 2025-08), spread_bps={SPREAD_BPS}, max_hold_bars={MAX_HOLD_BARS}, be=None")
    print("=" * 78)
    rows = []
    for tf in TIMEFRAMES:
        for vz in VOL_ZSCORE_CANDIDATES:
            for adx_min in HTF_ADX_MIN_CANDIDATES:
                signaled_is = signaled_by_key[(tf, vz, adx_min)]
                signaled_is = signaled_is[signaled_is.index < SPLIT]
                for stop_mult in STOP_ATR_CANDIDATES:
                    for tp_r in TP_R_CANDIDATES:
                        cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=False, take_profit_r=tp_r, max_hold_bars=MAX_HOLD_BARS)
                        trades = simulate_trades(signaled_is, cfg)
                        s = summarize(trades, signaled_is.index)
                        rows.append({"tf": tf, "vol_z": vz, "htf_adx_min": adx_min, "stop_atr": stop_mult, "tp_r": tp_r, **s})
        print(f"  {tf} sweep done")

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    if eligible.empty:
        print(f"\nNo combo reaches {MIN_IS_TRADES} IS trades - stopping.")
        return
    top10 = eligible.sort_values("sharpe", ascending=False).head(10)
    print("\nTop 10 combos by IS Sharpe:")
    print(top10[["tf", "vol_z", "htf_adx_min", "stop_atr", "tp_r", "n_trades", "win_rate", "profit_factor", "sharpe", "cagr", "max_drawdown"]].to_string(index=False))

    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\nStandout combo (highest IS Sharpe, n>={MIN_IS_TRADES}):")
    print(f"  {best[['tf', 'vol_z', 'htf_adx_min', 'stop_atr', 'tp_r']].to_dict()}")
    print(f"  {fmt(best.to_dict())}")

    tf, vz, adx_min = best["tf"], best["vol_z"], best["htf_adx_min"]
    stop_mult, tp_r = float(best["stop_atr"]), float(best["tp_r"])

    print("\n" + "=" * 78)
    print("2. OOS VALIDATION - chosen config applied UNTOUCHED to 2025-08 to 2026-08")
    print("=" * 78)
    signaled_full = signaled_by_key[(tf, vz, adx_min)]
    signaled_oos = signaled_full[signaled_full.index >= SPLIT]
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=False, take_profit_r=tp_r, max_hold_bars=MAX_HOLD_BARS)
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
    ltf_oos = ltf_frames[tf]
    ltf_oos = ltf_oos[ltf_oos.index >= SPLIT]
    daily_close = ltf_oos["close"].resample("1D").last().dropna()
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
