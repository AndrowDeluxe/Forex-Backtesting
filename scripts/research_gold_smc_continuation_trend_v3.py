"""Follow-up to research_gold_smc_continuation_trend_v2.py (chat
2026-08-20). Two new ideas from the same conversation:
  1. trend_indicator="ema_adx_combo" (trend.py) - EMA-cross direction,
     ADX-strength-gated (isolates whether adx_di's edge over ema_cross/
     donchian in v2 was its DI-based direction or just its ability to say
     "no clear trend").
  2. require_h4_manipulation (continuation.py) - derived from the user's
     own real trade chart ("Entry durch H4 Manipulation bestaetigt im
     H4"): an H4-level sweep-and-reject in the trend direction, mirroring
     reversal_cascade.py's H4 phase but read as continuation confirmation
     instead of a fade trigger - a formal H4 gate that was missing.

Re-runs the trend_indicator x trend_tf sweep with ema_adx_combo added,
then tests require_h4_manipulation on/off on top of whichever trend
config wins, at a few confirm_bars candidates. Exits fixed at the
already-validated best (stop=0.5, mtd=0.5, be=None) throughout, same as
v2 - only re-checked at the very end on the final structural winner.
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

TREND_INDICATORS = ["adx_di", "ema_cross", "donchian", "ema_adx_combo"]
TREND_TFS = ["M15", "M30", "H1", "H4"]
H4_MANIP_CONFIRM_CANDIDATES = [10, 20, 40]
STOP_ATR_CANDIDATES = [0.5, 1.0, 1.5]
BE_CANDIDATES = [None, 0.5, 1.0]

FIXED_STOP, FIXED_MTD, FIXED_BE, FIXED_HVB = 0.5, 0.5, None, 24


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"


def eval_signal(sig: pd.DataFrame, stop: float, be, max_hold: int) -> tuple[dict, dict]:
    sig_is, sig_oos = sig[sig.index < SPLIT], sig[sig.index >= SPLIT]
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=max_hold)
    s_is = summarize(simulate_trades(sig_is, cfg), sig_is.index)
    s_oos = summarize(simulate_trades(sig_oos, cfg), sig_oos.index)
    return s_is, s_oos


def main():
    print(f"Fetching GOLD H4/H1/M30/M15/M5 {START} -> {END} ...")
    h4 = fetch_gold_h4(START, END)
    h1 = fetch_gold_h1(START, END)
    m30 = fetch_gold_m30(START, END)
    m15 = fetch_gold_m15(START, END)
    m5 = fetch_gold_m5(START, END)
    print(f"H4={len(h4)} H1={len(h1)} M30={len(m30)} M15={len(m15)} M5={len(m5)}")
    trend_frames = {"M15": m15, "M30": m30, "H1": h1, "H4": h4}

    print("\n" + "=" * 78)
    print("A) TREND_INDICATOR x TREND_TF SWEEP (incl. ema_adx_combo)")
    print("=" * 78)
    rows_a = []
    for ti in TREND_INDICATORS:
        for tf in TREND_TFS:
            sig = run_pipeline(h4, h1, m5, trend_df=trend_frames[tf], trend_indicator=ti, htf_valid_bars=FIXED_HVB, entry_variant="direct", min_target_distance_atr=FIXED_MTD)
            s_is, s_oos = eval_signal(sig, FIXED_STOP, FIXED_BE, FIXED_HVB * 12)
            rows_a.append({"trend_indicator": ti, "trend_tf": tf, **s_is})
            print(f"  {ti:<14} {tf:<4}: IS {fmt(s_is)}   OOS {fmt(s_oos)}")

    sweep_a = pd.DataFrame(rows_a)
    eligible_a = sweep_a[sweep_a["n_trades"] >= MIN_IS_TRADES]
    if eligible_a.empty:
        print("No trend combo reaches the IS trade threshold - stopping.")
        return
    best_a = eligible_a.loc[eligible_a["sharpe"].idxmax()]
    ti, tf = best_a["trend_indicator"], best_a["trend_tf"]
    print(f"\nStage A winner: trend_indicator={ti} trend_tf={tf}  IS {fmt(best_a.to_dict())}")

    print("\n" + "=" * 78)
    print(f"B) require_h4_manipulation on {ti}/{tf} (on/off x confirm_bars)")
    print("=" * 78)
    rows_b = []
    sig_off = run_pipeline(h4, h1, m5, trend_df=trend_frames[tf], trend_indicator=ti, htf_valid_bars=FIXED_HVB, entry_variant="direct", min_target_distance_atr=FIXED_MTD, require_h4_manipulation=False)
    s_is_off, s_oos_off = eval_signal(sig_off, FIXED_STOP, FIXED_BE, FIXED_HVB * 12)
    rows_b.append({"require_h4_manip": False, "confirm_bars": None, **s_is_off})
    print(f"  off                : IS {fmt(s_is_off)}   OOS {fmt(s_oos_off)}")

    signaled_by_cb = {}
    for cb in H4_MANIP_CONFIRM_CANDIDATES:
        sig_on = run_pipeline(h4, h1, m5, trend_df=trend_frames[tf], trend_indicator=ti, htf_valid_bars=FIXED_HVB, entry_variant="direct", min_target_distance_atr=FIXED_MTD, require_h4_manipulation=True, h4_manip_confirm_bars=cb)
        signaled_by_cb[cb] = sig_on
        s_is_on, s_oos_on = eval_signal(sig_on, FIXED_STOP, FIXED_BE, FIXED_HVB * 12)
        rows_b.append({"require_h4_manip": True, "confirm_bars": cb, **s_is_on})
        print(f"  on, confirm_bars={cb:>3}: IS {fmt(s_is_on)}   OOS {fmt(s_oos_on)}")

    sweep_b = pd.DataFrame(rows_b)
    eligible_b = sweep_b[sweep_b["n_trades"] >= MIN_IS_TRADES]
    if eligible_b.empty:
        print("\nNo h4_manipulation variant reaches the IS trade threshold - keeping it OFF.")
        use_manip, cb_final = False, None
        sig_final = sig_off
    else:
        best_b = eligible_b.loc[eligible_b["sharpe"].idxmax()]
        use_manip = bool(best_b["require_h4_manip"])
        cb_final = None if pd.isna(best_b["confirm_bars"]) else int(best_b["confirm_bars"])
        print(f"\nStage B winner: require_h4_manipulation={use_manip} confirm_bars={cb_final}  IS {fmt(best_b.to_dict())}")
        sig_final = signaled_by_cb[cb_final] if use_manip else sig_off

    print("\n" + "=" * 78)
    print(f"C) LIGHT STOP/BE RE-CHECK on final structural config")
    print("=" * 78)
    sig_final_is = sig_final[sig_final.index < SPLIT]
    rows_c = []
    for stop in STOP_ATR_CANDIDATES:
        for be in BE_CANDIDATES:
            cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=FIXED_HVB * 12)
            s = summarize(simulate_trades(sig_final_is, cfg), sig_final_is.index)
            rows_c.append({"stop_atr": stop, "be": be, **s})
    sweep_c = pd.DataFrame(rows_c)
    eligible_c = sweep_c[sweep_c["n_trades"] >= MIN_IS_TRADES]
    print(sweep_c[["stop_atr", "be", "n_trades", "win_rate", "profit_factor", "sharpe", "cagr"]].to_string(index=False))
    if eligible_c.empty:
        stop_final, be_final = FIXED_STOP, FIXED_BE
    else:
        best_c = eligible_c.loc[eligible_c["sharpe"].idxmax()]
        stop_final = float(best_c["stop_atr"])
        be_final = None if pd.isna(best_c["be"]) else float(best_c["be"])
    print(f"\nStage C winner: stop_atr={stop_final} be={be_final}")

    print("\n" + "=" * 78)
    print(f"FINAL CONFIG: trend_indicator={ti} trend_tf={tf} require_h4_manipulation={use_manip} confirm_bars={cb_final} stop={stop_final} be={be_final}")
    print("=" * 78)
    sig_oos = sig_final[sig_final.index >= SPLIT]
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_final, use_vwap_target=True, breakeven_trigger_r=be_final, max_hold_bars=FIXED_HVB * 12)
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
    print(f"\n  Beats existing champion (OOS Sharpe=1.62)? {'YES' if oos_stats['n_trades'] > 0 and oos_stats['sharpe'] > 1.62 else 'no'}")
    print(f"  Beats buy-and-hold on Sharpe? {'YES' if oos_stats['n_trades'] > 0 and oos_stats['sharpe'] > bh_sharpe else 'no'}")

    if not oos_trades.empty:
        print("\nExit reasons (OOS):")
        print(oos_trades["exit_reason"].value_counts().to_string())


if __name__ == "__main__":
    main()
