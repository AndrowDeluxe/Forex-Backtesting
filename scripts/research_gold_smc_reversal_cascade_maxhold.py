"""Follow-up to research_gold_smc_reversal_cascade_v9.py (chat 2026-08-19,
"testen wir eine weitere max Hold Zeit oder kuerzen max Hold gaenzlich").
The winning repeat_sweep/ATR-5R config (stop=3.0, tp_r=5.0, mtd=1.0)
showed max_hold as its MOST profitable exit bucket (65.9% of trades,
81.5% win rate, but capped by the 24h/96-bar window before reaching the
full 5R target) - diagnosed as a real optimization lever, not a bug
(gold_smc_htf_ltf max_hold integrity re-check, chat 2026-08-19). This
sweeps max_hold_bars itself (shorter AND longer than the current 96) on
top of the already-fixed entry/exit config, IS-selected, OOS-validated.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m15
from gold_smc_htf_ltf.reversal_cascade import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0
MIN_IS_TRADES = 15
H4_CONFIRM_BARS, H1_VALID_BARS = 30, 24

# M15 bars <-> hours: 4 bars/hour
MAX_HOLD_CANDIDATES_H = [6, 12, 18, 24, 36, 48, 72, 96]  # hours
MAX_HOLD_CANDIDATES = [h * 4 for h in MAX_HOLD_CANDIDATES_H]


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"


def main():
    print(f"Fetching GOLD H4/H1/M15 {START} -> {END} ...")
    h4 = fetch_gold_h4(START, END)
    h1 = fetch_gold_h1(START, END)
    m15 = fetch_gold_m15(START, END)
    print(f"H4={len(h4)} H1={len(h1)} M15={len(m15)}")

    # signal/entry generation doesn't depend on max_hold_bars at all -
    # compute the (fixed) winning entry once, only re-simulate per candidate
    sig = run_pipeline(h4, h1, m15, h4_confirm_bars=H4_CONFIRM_BARS, h1_valid_bars=H1_VALID_BARS, min_target_distance_atr=1.0, require_ema_reject=True, m15_entry_mode="repeat_sweep")
    sig_is = sig[sig.index < SPLIT]
    sig_oos = sig[sig.index >= SPLIT]
    print(f"{int((sig['signal'] != 0).sum())} raw signals (full period)")

    print("\n" + "=" * 78)
    print(f"1. SWEEP max_hold_bars - IS PERIOD ONLY, spread_bps={SPREAD_BPS}, stop=3.0, tp_r=5.0, be=None fixed")
    print("=" * 78)
    rows = []
    for max_hold, hours in zip(MAX_HOLD_CANDIDATES, MAX_HOLD_CANDIDATES_H):
        cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=3.0, use_vwap_target=False, take_profit_r=5.0, breakeven_trigger_r=None, max_hold_bars=max_hold)
        trades = simulate_trades(sig_is, cfg)
        s = summarize(trades, sig_is.index)
        rows.append({"max_hold_bars": max_hold, "hours": hours, **s})
        print(f"  max_hold={hours:>3}h ({max_hold:>3} bars): {fmt(s)}")

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    print(f"\n{len(eligible)}/{len(sweep)} combos reach n>={MIN_IS_TRADES} IS trades")
    if eligible.empty:
        print("Stopping.")
        return
    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\nBest max_hold_bars (highest IS Sharpe): {best['hours']}h ({int(best['max_hold_bars'])} bars)")
    print(f"  {fmt(best.to_dict())}")

    chosen_max_hold = int(best["max_hold_bars"])

    print("\n" + "=" * 78)
    print("2. OOS VALIDATION - chosen max_hold_bars applied UNTOUCHED to 2025-08 to 2026-08")
    print("=" * 78)
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=3.0, use_vwap_target=False, take_profit_r=5.0, breakeven_trigger_r=None, max_hold_bars=chosen_max_hold)
    oos_trades = simulate_trades(sig_oos, cfg)
    oos_stats = summarize(oos_trades, sig_oos.index)
    print(f"  OOS: {fmt(oos_stats)}")

    print("\n" + "=" * 78)
    print("3. OUTLIER-SENSITIVITY CHECK ON OOS")
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
    print("4. BUY & HOLD COMPARISON")
    print("=" * 78)
    m15_oos = m15[m15.index >= SPLIT]
    daily_close = m15_oos["close"].resample("1D").last().dropna()
    daily_ret = daily_close.pct_change().fillna(0.0)
    daily_ret.iloc[0] -= SPREAD_BPS / 2 / 1e4
    bh_sharpe, bh_cagr, bh_mdd = annualized_sharpe(daily_ret), cagr(daily_ret), max_drawdown(daily_ret)
    print(f"  Buy & hold Gold:  Sharpe={bh_sharpe:.2f}  CAGR={bh_cagr:+.1%}  MaxDD={bh_mdd:.1%}")
    print(f"  Strategy (OOS):   {fmt(oos_stats)}")
    print(f"  Beats buy-and-hold on Sharpe? {'YES' if oos_stats['n_trades'] > 0 and oos_stats['sharpe'] > bh_sharpe else 'no'}")

    print("\n" + "=" * 78)
    print("5. EXIT REASON BREAKDOWN (OOS) - has max_hold's share/quality changed?")
    print("=" * 78)
    if not oos_trades.empty:
        print(oos_trades["exit_reason"].value_counts().to_string())
        for reason, grp in oos_trades.groupby("exit_reason"):
            print(f"  {reason}: WR={((grp['return_pct'] > 0).mean()):.1%}  avg_ret={grp['return_pct'].mean() * 100:+.3f}%")

    print("\n" + "=" * 78)
    print("6. REFERENCE - current baseline (max_hold=96, 24h) OOS for direct comparison")
    print("=" * 78)
    cfg_base = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=3.0, use_vwap_target=False, take_profit_r=5.0, breakeven_trigger_r=None, max_hold_bars=96)
    oos_base = simulate_trades(sig_oos, cfg_base)
    print(f"  OOS (max_hold=96/24h): {fmt(summarize(oos_base, sig_oos.index))}")


if __name__ == "__main__":
    main()
