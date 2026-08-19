"""Research script: the Mean-Reversion strategy from gold_smc_htf_ltf/
mean_reversion.py - a single-timeframe "double BOS then fade" signal,
tested on both M5 and M15 (per the user's instruction), with an optional
H1 ADX trend-strength gate testing the hypothesis "die Wahrscheinlichkeit
für ein M5/M15 Reversal ist höher, wenn wir im HTF einen stabilen Trend
haben" (chat 2026-08-14/15).

Smoke test (chat) found most trades exiting via max_hold rather than
stop/target at the default stop=1.0/tp_r=2.0 - max_hold_bars is fixed
here (200, ~1.4 days on M15 / ~16.7h on M5 - long enough for the
snap-back thesis to play out, short enough that "hasn't happened yet"
should mean "probably won't") while stop_atr_mult/take_profit_r/
breakeven_trigger_r are swept properly to find combos that actually
resolve via stop/target instead.

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
HTF_ADX_MIN_CANDIDATES = [None, 20.0, 25.0]
STOP_ATR_CANDIDATES = [0.5, 1.0, 1.5]
TP_R_CANDIDATES = [1.5, 2.0, 3.0]
BE_CANDIDATES = [None, 0.5, 1.0]


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

    print("\nRunning pipeline once per (timeframe, htf_adx_min) ...")
    signaled_by_key = {}
    for tf in TIMEFRAMES:
        for adx_min in HTF_ADX_MIN_CANDIDATES:
            signaled = run_pipeline(ltf_frames[tf], htf_df=h1 if adx_min else None, htf_adx_min=adx_min)
            signaled_by_key[(tf, adx_min)] = signaled
            n_sig = int((signaled["signal"] != 0).sum())
            print(f"  {tf:<4} htf_adx_min={adx_min}: {n_sig} raw signals (full period)")

    print("\n" + "=" * 78)
    print(f"1. SWEEP - IS PERIOD ONLY (2024-08 to 2025-08), spread_bps={SPREAD_BPS}, max_hold_bars={MAX_HOLD_BARS}")
    print("=" * 78)
    rows = []
    for tf in TIMEFRAMES:
        for adx_min in HTF_ADX_MIN_CANDIDATES:
            signaled_is = signaled_by_key[(tf, adx_min)]
            signaled_is = signaled_is[signaled_is.index < SPLIT]
            for stop_mult in STOP_ATR_CANDIDATES:
                for tp_r in TP_R_CANDIDATES:
                    for be in BE_CANDIDATES:
                        cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=False, take_profit_r=tp_r, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
                        trades = simulate_trades(signaled_is, cfg)
                        s = summarize(trades, signaled_is.index)
                        rows.append({"tf": tf, "htf_adx_min": adx_min, "stop_atr": stop_mult, "tp_r": tp_r, "be": be, **s})
        print(f"  {tf} sweep done ({len(HTF_ADX_MIN_CANDIDATES) * len(STOP_ATR_CANDIDATES) * len(TP_R_CANDIDATES) * len(BE_CANDIDATES)} combos)")

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    if eligible.empty:
        print(f"\nNo combo reaches {MIN_IS_TRADES} IS trades - stopping.")
        return
    top10 = eligible.sort_values("sharpe", ascending=False).head(10)
    print("\nTop 10 combos by IS Sharpe:")
    print(top10[["tf", "htf_adx_min", "stop_atr", "tp_r", "be", "n_trades", "win_rate", "profit_factor", "sharpe", "cagr", "max_drawdown"]].to_string(index=False))

    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\nStandout combo (highest IS Sharpe, n>={MIN_IS_TRADES}):")
    print(f"  {best[['tf', 'htf_adx_min', 'stop_atr', 'tp_r', 'be']].to_dict()}")
    print(f"  {fmt(best.to_dict())}")

    tf, adx_min = best["tf"], best["htf_adx_min"]
    stop_mult, tp_r = float(best["stop_atr"]), float(best["tp_r"])
    be = None if pd.isna(best["be"]) else float(best["be"])

    print("\n" + "=" * 78)
    print("2. OOS VALIDATION - chosen config applied UNTOUCHED to 2025-08 to 2026-08")
    print("=" * 78)
    signaled_full = signaled_by_key[(tf, adx_min)]
    signaled_oos = signaled_full[signaled_full.index >= SPLIT]
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=False, take_profit_r=tp_r, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
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
