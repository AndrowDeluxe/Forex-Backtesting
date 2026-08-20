"""Follow-up to research_gold_smc_continuation_v2.py (chat 2026-08-19,
"Hast du fuer die Continuation auch den LTF Ansatz getestet wie im
Reversal?"). The first repeat_sweep test for Continuation used a
narrower exit grid (stop 0.5-1.5, h4_level TP only) than what turned out
to be the winning combination for the reversal cascade's own repeat_sweep
(stop up to 3.0 ATR + a flat ATR-R target, not the literal H4 level).
This gives Continuation's repeat_sweep the SAME thorough treatment
(both TP modes, stop up to 3.0, tp_r up to 5.0) before concluding it
doesn't work there - matching research_gold_smc_continuation_exit_sweep.
py's two-TP-mode structure.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_smc_htf_ltf.continuation import run_pipeline
from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m5, fetch_gold_m15
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0
MIN_IS_TRADES = 15
HTF_VALID_BARS = 24
MAX_HOLD_BARS = HTF_VALID_BARS * 12

STOP_ATR_CANDIDATES = [0.5, 1.0, 1.5, 2.0, 3.0]
BE_CANDIDATES = [None, 0.5, 1.0, 1.5]
TP_R_CANDIDATES = [1.5, 2.0, 3.0, 4.0, 5.0]
MTD_FOR_ATR_MODE = 1.0


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"


def main():
    print(f"Fetching GOLD H4/H1/M15/M5 {START} -> {END} ...")
    h4 = fetch_gold_h4(START, END)
    h1 = fetch_gold_h1(START, END)
    m15 = fetch_gold_m15(START, END)
    m5 = fetch_gold_m5(START, END)
    print(f"H4={len(h4)} H1={len(h1)} M15={len(m15)} M5={len(m5)}")

    sig = run_pipeline(h4, h1, m5, trend_df=m15, trend_indicator="adx_di", htf_valid_bars=HTF_VALID_BARS, entry_variant="repeat_sweep", min_target_distance_atr=MTD_FOR_ATR_MODE)
    sig_is = sig[sig.index < SPLIT]
    print(f"repeat_sweep: {int((sig['signal'] != 0).sum())} raw signals (full period)")

    print("\n" + "=" * 78)
    print(f"A) TP MODE = h4_level - IS sweep, spread_bps={SPREAD_BPS}")
    print("=" * 78)
    rows = []
    for stop_mult in STOP_ATR_CANDIDATES:
        for be in BE_CANDIDATES:
            cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
            trades = simulate_trades(sig_is, cfg)
            s = summarize(trades, sig_is.index)
            rows.append({"tp_mode": "h4_level", "tp_r": None, "stop_atr": stop_mult, "be": be, **s})

    print("\n" + "=" * 78)
    print(f"B) TP MODE = atr - IS sweep, spread_bps={SPREAD_BPS}")
    print("=" * 78)
    for tp_r in TP_R_CANDIDATES:
        for stop_mult in STOP_ATR_CANDIDATES:
            for be in BE_CANDIDATES:
                cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=False, take_profit_r=tp_r, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
                trades = simulate_trades(sig_is, cfg)
                s = summarize(trades, sig_is.index)
                rows.append({"tp_mode": "atr", "tp_r": tp_r, "stop_atr": stop_mult, "be": be, **s})

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    print(f"\n{len(sweep)} combos tested, {len(eligible)} reach n>={MIN_IS_TRADES} IS trades")
    if eligible.empty:
        print("Stopping.")
        return
    top15 = eligible.sort_values("sharpe", ascending=False).head(15)
    print("\nTop 15 combos by IS Sharpe:")
    print(top15[["tp_mode", "tp_r", "stop_atr", "be", "n_trades", "win_rate", "profit_factor", "sharpe", "cagr"]].to_string(index=False))

    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\nStandout combo (highest IS Sharpe, n>={MIN_IS_TRADES}):")
    print(f"  {best[['tp_mode', 'tp_r', 'stop_atr', 'be']].to_dict()}")
    print(f"  {fmt(best.to_dict())}")

    tp_mode = best["tp_mode"]
    stop_mult = float(best["stop_atr"])
    be = None if pd.isna(best["be"]) else float(best["be"])

    print("\n" + "=" * 78)
    print("OOS VALIDATION - chosen config applied UNTOUCHED to 2025-08 to 2026-08")
    print("=" * 78)
    sig_oos = sig[sig.index >= SPLIT]
    if tp_mode == "h4_level":
        cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
    else:
        cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=False, take_profit_r=float(best["tp_r"]), breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
    oos_trades = simulate_trades(sig_oos, cfg)
    oos_stats = summarize(oos_trades, sig_oos.index)
    print(f"  OOS: {fmt(oos_stats)}")

    print("\n" + "=" * 78)
    print("OUTLIER-SENSITIVITY CHECK ON OOS")
    print("=" * 78)
    if oos_trades.empty:
        print("  No OOS trades.")
    else:
        sorted_ret = oos_trades["return_pct"].sort_values(ascending=False)
        without_best = oos_trades.drop(index=sorted_ret.index[0])
        s_wo = summarize(without_best, sig_oos.index)
        print(f"  OOS PF with best trade:    {oos_stats['profit_factor']:.3f}  (Sharpe {oos_stats['sharpe']:.2f})")
        print(f"  OOS PF without best trade: {s_wo['profit_factor']:.3f}  (Sharpe {s_wo['sharpe']:.2f})")

    print("\n" + "=" * 78)
    print("BUY & HOLD COMPARISON")
    print("=" * 78)
    m5_oos = m5[m5.index >= SPLIT]
    daily_close = m5_oos["close"].resample("1D").last().dropna()
    daily_ret = daily_close.pct_change().fillna(0.0)
    daily_ret.iloc[0] -= SPREAD_BPS / 2 / 1e4
    bh_sharpe, bh_cagr, bh_mdd = annualized_sharpe(daily_ret), cagr(daily_ret), max_drawdown(daily_ret)
    print(f"  Buy & hold Gold:  Sharpe={bh_sharpe:.2f}  CAGR={bh_cagr:+.1%}  MaxDD={bh_mdd:.1%}")
    print(f"  Strategy (OOS):   {fmt(oos_stats)}")
    print(f"  Beats buy-and-hold on Sharpe? {'YES' if oos_stats['n_trades'] > 0 and oos_stats['sharpe'] > bh_sharpe else 'no'}")


if __name__ == "__main__":
    main()
