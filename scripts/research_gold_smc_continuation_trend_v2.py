"""Follow-up to research_gold_smc_continuation.py (chat 2026-08-20):
the original trend_indicator/trend_tf choice (adx_di/M15) was picked at
the very START of the continuation research, with stop_atr FIXED at an
arbitrary 1.0 before the exit side (stop=0.5, mtd=0.5, be=None) or any
entry-variant/h1_bos_min work happened. User: "Sweepe gerne nochmal den
trendindikator evtl auch mit der Ema Logik auf M15, H1 oder H4 und
optimiere dabei auch nochmal die H1-H4 Strukturbestaetigung" - re-sweeps
trend_indicator x trend_tf (now including H1/H4, not just M15/M30) AND
htf_valid_bars (the H1 context window - never swept before, always fixed
at 24) together, on top of the already-validated best exit (stop=0.5,
mtd=0.5, be=None, entry_variant="direct").

Three stages, each IS-selected before moving to the next (avoids a
combinatorial explosion while still covering the real interactions):
  A) trend_indicator x trend_tf (12 combos), htf_valid_bars=24 fixed
  B) htf_valid_bars sweep on stage A's winner
  C) light stop/be re-check on the final structural config (confirms the
     existing exit choice still holds, or finds a new one)
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

TREND_INDICATORS = ["adx_di", "ema_cross", "donchian"]
TREND_TFS = ["M15", "M30", "H1", "H4"]
HTF_VALID_BARS_CANDIDATES = [12, 18, 24, 36, 48]
STOP_ATR_CANDIDATES = [0.5, 1.0, 1.5]
BE_CANDIDATES = [None, 0.5, 1.0]

FIXED_STOP, FIXED_MTD, FIXED_BE = 0.5, 0.5, None


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
    print("A) TREND_INDICATOR x TREND_TF SWEEP (htf_valid_bars=24, exits fixed at stop=0.5/mtd=0.5/be=None)")
    print("=" * 78)
    rows_a = []
    for ti in TREND_INDICATORS:
        for tf in TREND_TFS:
            sig = run_pipeline(h4, h1, m5, trend_df=trend_frames[tf], trend_indicator=ti, htf_valid_bars=24, entry_variant="direct", min_target_distance_atr=FIXED_MTD)
            s_is, s_oos = eval_signal(sig, FIXED_STOP, FIXED_BE, 24 * 12)
            rows_a.append({"trend_indicator": ti, "trend_tf": tf, **s_is})
            print(f"  {ti:<10} {tf:<4}: IS {fmt(s_is)}   OOS {fmt(s_oos)}")

    sweep_a = pd.DataFrame(rows_a)
    eligible_a = sweep_a[sweep_a["n_trades"] >= MIN_IS_TRADES]
    if eligible_a.empty:
        print("No trend combo reaches the IS trade threshold - stopping.")
        return
    best_a = eligible_a.loc[eligible_a["sharpe"].idxmax()]
    ti, tf = best_a["trend_indicator"], best_a["trend_tf"]
    print(f"\nStage A winner: trend_indicator={ti} trend_tf={tf}  IS {fmt(best_a.to_dict())}")

    print("\n" + "=" * 78)
    print(f"B) htf_valid_bars SWEEP on {ti}/{tf} (exits still fixed at stop=0.5/mtd=0.5/be=None)")
    print("=" * 78)
    rows_b = []
    signaled_by_hvb = {}
    for hvb in HTF_VALID_BARS_CANDIDATES:
        sig = run_pipeline(h4, h1, m5, trend_df=trend_frames[tf], trend_indicator=ti, htf_valid_bars=hvb, entry_variant="direct", min_target_distance_atr=FIXED_MTD)
        signaled_by_hvb[hvb] = sig
        s_is, s_oos = eval_signal(sig, FIXED_STOP, FIXED_BE, hvb * 12)
        rows_b.append({"htf_valid_bars": hvb, **s_is})
        print(f"  htf_valid_bars={hvb:>3}: IS {fmt(s_is)}   OOS {fmt(s_oos)}")

    sweep_b = pd.DataFrame(rows_b)
    eligible_b = sweep_b[sweep_b["n_trades"] >= MIN_IS_TRADES]
    if eligible_b.empty:
        print("No htf_valid_bars reaches the IS trade threshold - keeping htf_valid_bars=24.")
        hvb_best = 24
    else:
        best_b = eligible_b.loc[eligible_b["sharpe"].idxmax()]
        hvb_best = int(best_b["htf_valid_bars"])
        print(f"\nStage B winner: htf_valid_bars={hvb_best}  IS {fmt(best_b.to_dict())}")

    print("\n" + "=" * 78)
    print(f"C) LIGHT STOP/BE RE-CHECK on {ti}/{tf}, htf_valid_bars={hvb_best}")
    print("=" * 78)
    sig_final = run_pipeline(h4, h1, m5, trend_df=trend_frames[tf], trend_indicator=ti, htf_valid_bars=hvb_best, entry_variant="direct", min_target_distance_atr=FIXED_MTD)
    sig_final_is = sig_final[sig_final.index < SPLIT]
    rows_c = []
    for stop in STOP_ATR_CANDIDATES:
        for be in BE_CANDIDATES:
            cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=hvb_best * 12)
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
    print(f"FINAL CONFIG: trend_indicator={ti} trend_tf={tf} htf_valid_bars={hvb_best} stop={stop_final} be={be_final} mtd={FIXED_MTD}")
    print("=" * 78)
    sig_oos = sig_final[sig_final.index >= SPLIT]
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_final, use_vwap_target=True, breakeven_trigger_r=be_final, max_hold_bars=hvb_best * 12)
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
    print(f"\n  Beats existing champion (direct/adx_di/M15/htf_valid_bars=24, OOS Sharpe=1.62)? {'YES' if oos_stats['n_trades'] > 0 and oos_stats['sharpe'] > 1.62 else 'no'}")
    print(f"  Beats buy-and-hold on Sharpe? {'YES' if oos_stats['n_trades'] > 0 and oos_stats['sharpe'] > bh_sharpe else 'no'}")

    if not oos_trades.empty:
        print("\nExit reasons (OOS):")
        print(oos_trades["exit_reason"].value_counts().to_string())


if __name__ == "__main__":
    main()
