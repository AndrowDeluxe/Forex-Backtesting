"""Reversal-Kaskade: LTF-Entry auf M5 statt M15 (chat 2026-08-20: "Ich bin
mir sicher, dass Ich dir gestern auch fuer die Reversal Kaskade den LTF M5
Hinweis gegeben hatte, holen wir fix nach").

gold_smc_htf_ltf.reversal_cascade.run_pipeline's third positional arg
(named "m15_df" only cosmetically) is fully timeframe-agnostic - every
internal shift/merge derives its offset from _bar_length(h1.index)/
_bar_length(h4.index), never a hardcoded M15 assumption - so passing an
M5 df there is a legitimate, structurally supported swap, not a hack.

H4/H1 cascade params stay at their already-validated values (h4_confirm_
bars=30, h1_valid_bars=24, require_ema_reject=True) - only the open
question (LTF granularity + its entry mechanic + exits) is swept here,
same "give each variant its own independent exit sweep" discipline as
research_gold_smc_continuation_entry_v3.py. Entry modes tested: "sweep"
(baseline) and "repeat_sweep" (the M15 champion) - both with their own
min_target_distance_atr x max_hold x stop x tp x be sweep. IS-select ->
OOS-validate -> outlier check -> compare to the M15 champion (single-
position OOS Sharpe=0.90) and to re-entry if the M5 config wins.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_smc_htf_ltf.concurrent_backtest import (
    equity_curve_to_daily_returns, simulate_account_reentry, simulate_trades_concurrent,
)
from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m5
from gold_smc_htf_ltf.reversal_cascade import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0
MIN_IS_TRADES = 15
H4_CONFIRM_BARS, H1_VALID_BARS = 30, 24

ENTRY_MODES = ["sweep", "repeat_sweep"]
MTD_CANDIDATES = [0.5, 1.0]
MAX_HOLD_H_CANDIDATES = [24, 48, 72, 96, 120, 144, 168]
MAX_HOLD_CANDIDATES = [h * 12 for h in MAX_HOLD_H_CANDIDATES]  # M5 bars (12/hour)
STOP_ATR_CANDIDATES = [0.5, 1.0, 1.5, 2.0, 3.0]
BE_CANDIDATES = [None, 0.5, 1.0]
TP_VARIANTS = [("h4_level", None)] + [("atr", tp_r) for tp_r in (2.0, 3.0, 4.0, 5.0)]

M15_SINGLE_POS_OOS_SHARPE = 0.90  # established champion, LTF=M15, entry=repeat_sweep


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"


def build_cfg(tp_mode: str, tp_r, stop_mult: float, be, max_hold: int) -> BacktestConfig:
    if tp_mode == "h4_level":
        return BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=max_hold)
    return BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=False, take_profit_r=tp_r, breakeven_trigger_r=be, max_hold_bars=max_hold)


def main():
    print(f"Fetching GOLD H4/H1/M5 {START} -> {END} ...")
    h4 = fetch_gold_h4(START, END)
    h1 = fetch_gold_h1(START, END)
    m5 = fetch_gold_m5(START, END)
    print(f"H4={len(h4)} H1={len(h1)} M5={len(m5)}")

    print("\nRunning pipeline once per (entry_mode, mtd) with LTF=M5 ...")
    signaled_by_key = {}
    for mode in ENTRY_MODES:
        for mtd in MTD_CANDIDATES:
            sig = run_pipeline(
                h4, h1, m5, h4_confirm_bars=H4_CONFIRM_BARS, h1_valid_bars=H1_VALID_BARS,
                min_target_distance_atr=mtd, require_ema_reject=True, m15_entry_mode=mode,
            )
            signaled_by_key[(mode, mtd)] = sig
            print(f"  {mode:<13} mtd={mtd}: {int((sig['signal'] != 0).sum())} raw signals")

    print("\n" + "=" * 78)
    print(f"SWEEP - IS PERIOD ONLY, spread_bps={SPREAD_BPS}")
    print("=" * 78)
    rows = []
    for (mode, mtd), sig in signaled_by_key.items():
        sig_is = sig[sig.index < SPLIT]
        for max_hold, hours in zip(MAX_HOLD_CANDIDATES, MAX_HOLD_H_CANDIDATES):
            for tp_mode, tp_r in TP_VARIANTS:
                for stop in STOP_ATR_CANDIDATES:
                    for be in BE_CANDIDATES:
                        cfg = build_cfg(tp_mode, tp_r, stop, be, max_hold)
                        s = summarize(simulate_trades(sig_is, cfg), sig_is.index)
                        rows.append({"mode": mode, "mtd": mtd, "max_hold_h": hours, "tp_mode": tp_mode, "tp_r": tp_r, "stop_atr": stop, "be": be, **s})
        print(f"  {mode} mtd={mtd} done ({len(rows)} rows so far)")

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    print(f"\n{len(sweep)} combos tested, {len(eligible)} reach n>={MIN_IS_TRADES} IS trades")
    if eligible.empty:
        print("Stopping - no combo reaches the min-trade guard.")
        return
    top15 = eligible.sort_values("sharpe", ascending=False).head(15)
    print("\nTop 15 combos by IS Sharpe:")
    print(top15[["mode", "mtd", "max_hold_h", "tp_mode", "tp_r", "stop_atr", "be", "n_trades", "win_rate", "profit_factor", "sharpe", "cagr"]].to_string(index=False))

    print("\nBest combo PER entry mode (by IS Sharpe, n>=15):")
    best_by_mode = {}
    for mode in ENTRY_MODES:
        sub = eligible[eligible["mode"] == mode]
        if sub.empty:
            print(f"  {mode:<13}: no combo reaches n>={MIN_IS_TRADES}")
            continue
        b = sub.loc[sub["sharpe"].idxmax()]
        best_by_mode[mode] = b
        print(f"  {mode:<13} mtd={b['mtd']} max_hold={b['max_hold_h']}h tp={b['tp_mode']}/{b['tp_r']} stop={b['stop_atr']} be={b['be']}  {fmt(b.to_dict())}")

        sig_full = signaled_by_key[(mode, float(b["mtd"]))]
        sig_oos = sig_full[sig_full.index >= SPLIT]
        be_val = None if pd.isna(b["be"]) else float(b["be"])
        tp_r_val = None if pd.isna(b["tp_r"]) else float(b["tp_r"])
        cfg = build_cfg(b["tp_mode"], tp_r_val, float(b["stop_atr"]), be_val, int(b["max_hold_h"]) * 12)
        oos_trades = simulate_trades(sig_oos, cfg)
        oos_stats = summarize(oos_trades, sig_oos.index)
        print(f"    -> OOS: {fmt(oos_stats)}")

    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\nStandout combo overall (highest IS Sharpe, n>={MIN_IS_TRADES}):")
    print(f"  {best[['mode', 'mtd', 'max_hold_h', 'tp_mode', 'tp_r', 'stop_atr', 'be']].to_dict()}")
    print(f"  {fmt(best.to_dict())}")

    mode, mtd = best["mode"], float(best["mtd"])
    max_hold = int(best["max_hold_h"]) * 12
    tp_mode, tp_r = best["tp_mode"], (None if pd.isna(best["tp_r"]) else float(best["tp_r"]))
    stop, be = float(best["stop_atr"]), (None if pd.isna(best["be"]) else float(best["be"]))

    print("\n" + "=" * 78)
    print("OOS VALIDATION (single-position) - chosen config applied UNTOUCHED to 2025-08 to 2026-08")
    print("=" * 78)
    sig_full = signaled_by_key[(mode, mtd)]
    sig_oos = sig_full[sig_full.index >= SPLIT]
    cfg = build_cfg(tp_mode, tp_r, stop, be, max_hold)
    oos_trades = simulate_trades(sig_oos, cfg)
    oos_stats = summarize(oos_trades, sig_oos.index)
    print(f"  OOS: {fmt(oos_stats)}")

    if not oos_trades.empty:
        sorted_ret = oos_trades["return_pct"].sort_values(ascending=False)
        without_best = oos_trades.drop(index=sorted_ret.index[0])
        s_wo = summarize(without_best, sig_oos.index)
        print(f"  Outlier check: PF {oos_stats['profit_factor']:.3f} -> {s_wo['profit_factor']:.3f}  Sharpe {oos_stats['sharpe']:.2f} -> {s_wo['sharpe']:.2f}")

    m5_oos = m5[m5.index >= SPLIT]
    daily_close = m5_oos["close"].resample("1D").last().dropna()
    daily_ret = daily_close.pct_change().fillna(0.0)
    daily_ret.iloc[0] -= SPREAD_BPS / 2 / 1e4
    bh_sharpe, bh_cagr, bh_mdd = annualized_sharpe(daily_ret), cagr(daily_ret), max_drawdown(daily_ret)
    print(f"  Buy & hold:  Sharpe={bh_sharpe:.2f}  CAGR={bh_cagr:+.1%}  MaxDD={bh_mdd:.1%}")
    print(f"\n  Beats M15-LTF single-position champion (OOS Sharpe={M15_SINGLE_POS_OOS_SHARPE})? {'YES' if oos_stats['n_trades'] > 0 and oos_stats['sharpe'] > M15_SINGLE_POS_OOS_SHARPE else 'no'}")
    print(f"  Beats buy-and-hold on Sharpe? {'YES' if oos_stats['n_trades'] > 0 and oos_stats['sharpe'] > bh_sharpe else 'no'}")

    print("\n" + "=" * 78)
    print("RE-ENTRY CHECK (same winning config, concurrent engine)")
    print("=" * 78)
    for max_conc in (1, 2, 3, 4, 5, None):
        raw = simulate_trades_concurrent(sig_oos, cfg)
        sim = simulate_account_reentry(raw, starting_equity=100_000.0, risk_pct=0.01, max_concurrent=max_conc)
        taken = sim["trades"]
        if taken.empty:
            print(f"  max_concurrent={max_conc}: n=0")
            continue
        daily = equity_curve_to_daily_returns(sim["equity_curve"], sig_oos.index)
        sh, cg, mdd = annualized_sharpe(daily), cagr(daily), max_drawdown(daily)
        total_ret = sim["final_equity"] / 100_000.0 - 1
        print(f"  max_concurrent={max_conc}: n={len(taken):>4} skipped={sim['n_skipped']:>4}  Sharpe={sh:.2f}  CAGR={cg:+.1%}  TotalReturn={total_ret:+.1%}  MaxDD={mdd:.1%}")


if __name__ == "__main__":
    main()
