"""Follow-up to research_gold_smc_continuation_trend_v3.py (chat
2026-08-20): "den Trendfilter im HTF anwenden, die Entry Logik aber im
M5 nach dem H1 Liq Sweep, um ggf SL und TP zu optimieren". Every prior
trend_indicator x trend_tf sweep (v2, v3) reused the exits already tuned
for M15 (stop=0.5, h4_level TP, be=None) for EVERY trend_tf candidate,
including H1/H4 - the same mistake that hid the reversal cascade's
repeat_sweep breakthrough until it got its own independent exit sweep.
This gives trend_tf in {H1, H4} (the genuine HTF options, not M15/M30)
a FULL, independent SL/TP(both modes)/BE sweep, for all 4 trend
indicators, entry_variant="direct" (M5 sweep-and-reject of the H1
liquidity level, unchanged) and htf_valid_bars=24 (already confirmed
optimal) held fixed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_smc_htf_ltf.continuation import run_pipeline
from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m5
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0
MIN_IS_TRADES = 15
HTF_VALID_BARS = 24
MAX_HOLD_BARS = HTF_VALID_BARS * 12
MTD = 0.5

TREND_INDICATORS = ["adx_di", "ema_cross", "donchian", "ema_adx_combo"]
TREND_TFS = ["H1", "H4"]
STOP_ATR_CANDIDATES = [0.5, 1.0, 1.5, 2.0, 3.0]
BE_CANDIDATES = [None, 0.5, 1.0, 1.5]
TP_R_CANDIDATES = [1.5, 2.0, 3.0, 4.0, 5.0]

# reference: current M15 champion
CHAMPION_OOS_SHARPE = 1.95


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"


def main():
    print(f"Fetching GOLD H4/H1/M5 {START} -> {END} ...")
    h4 = fetch_gold_h4(START, END)
    h1 = fetch_gold_h1(START, END)
    m5 = fetch_gold_m5(START, END)
    print(f"H4={len(h4)} H1={len(h1)} M5={len(m5)}")
    trend_frames = {"H1": h1, "H4": h4}

    print("\nRunning pipeline once per (trend_indicator, trend_tf) ...")
    signaled_by_key = {}
    for ti in TREND_INDICATORS:
        for tf in TREND_TFS:
            sig = run_pipeline(h4, h1, m5, trend_df=trend_frames[tf], trend_indicator=ti, htf_valid_bars=HTF_VALID_BARS, entry_variant="direct", min_target_distance_atr=MTD)
            signaled_by_key[(ti, tf)] = sig
            print(f"  {ti:<14} {tf}: {int((sig['signal'] != 0).sum())} raw signals")

    print("\n" + "=" * 78)
    print(f"SWEEP - IS PERIOD ONLY, spread_bps={SPREAD_BPS}, both TP modes")
    print("=" * 78)
    rows = []
    for (ti, tf), sig in signaled_by_key.items():
        sig_is = sig[sig.index < SPLIT]
        for stop in STOP_ATR_CANDIDATES:
            for be in BE_CANDIDATES:
                cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
                s = summarize(simulate_trades(sig_is, cfg), sig_is.index)
                rows.append({"trend_indicator": ti, "trend_tf": tf, "tp_mode": "h4_level", "tp_r": None, "stop_atr": stop, "be": be, **s})
        for tp_r in TP_R_CANDIDATES:
            for stop in STOP_ATR_CANDIDATES:
                for be in BE_CANDIDATES:
                    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop, use_vwap_target=False, take_profit_r=tp_r, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
                    s = summarize(simulate_trades(sig_is, cfg), sig_is.index)
                    rows.append({"trend_indicator": ti, "trend_tf": tf, "tp_mode": "atr", "tp_r": tp_r, "stop_atr": stop, "be": be, **s})
        print(f"  {ti}/{tf} done")

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    print(f"\n{len(sweep)} combos tested, {len(eligible)} reach n>={MIN_IS_TRADES} IS trades")
    if eligible.empty:
        print("Stopping.")
        return
    top20 = eligible.sort_values("sharpe", ascending=False).head(20)
    print("\nTop 20 combos by IS Sharpe:")
    print(top20[["trend_indicator", "trend_tf", "tp_mode", "tp_r", "stop_atr", "be", "n_trades", "win_rate", "profit_factor", "sharpe", "cagr"]].to_string(index=False))

    print("\nBest combo PER (trend_indicator, trend_tf) (by IS Sharpe, n>=15):")
    for (ti, tf) in signaled_by_key:
        sub = eligible[(eligible["trend_indicator"] == ti) & (eligible["trend_tf"] == tf)]
        if sub.empty:
            print(f"  {ti:<14} {tf}: no combo reaches n>={MIN_IS_TRADES}")
            continue
        b = sub.loc[sub["sharpe"].idxmax()]
        print(f"  {ti:<14} {tf} tp={b['tp_mode']}/{b['tp_r']} stop={b['stop_atr']} be={b['be']}  {fmt(b.to_dict())}")

    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\nStandout combo overall (highest IS Sharpe, n>={MIN_IS_TRADES}):")
    print(f"  {best[['trend_indicator', 'trend_tf', 'tp_mode', 'tp_r', 'stop_atr', 'be']].to_dict()}")
    print(f"  {fmt(best.to_dict())}")

    ti, tf, tp_mode = best["trend_indicator"], best["trend_tf"], best["tp_mode"]
    tp_r = None if pd.isna(best["tp_r"]) else float(best["tp_r"])
    stop = float(best["stop_atr"])
    be = None if pd.isna(best["be"]) else float(best["be"])

    print("\n" + "=" * 78)
    print("OOS VALIDATION - chosen config applied UNTOUCHED to 2025-08 to 2026-08")
    print("=" * 78)
    sig_full = signaled_by_key[(ti, tf)]
    sig_oos = sig_full[sig_full.index >= SPLIT]
    if tp_mode == "h4_level":
        cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
    else:
        cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop, use_vwap_target=False, take_profit_r=tp_r, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
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
    print(f"\n  Beats current M15 champion (OOS Sharpe={CHAMPION_OOS_SHARPE})? {'YES' if oos_stats['n_trades'] > 0 and oos_stats['sharpe'] > CHAMPION_OOS_SHARPE else 'no'}")
    print(f"  Beats buy-and-hold on Sharpe? {'YES' if oos_stats['n_trades'] > 0 and oos_stats['sharpe'] > bh_sharpe else 'no'}")

    if not oos_trades.empty:
        print("\nExit reasons (OOS):")
        print(oos_trades["exit_reason"].value_counts().to_string())


if __name__ == "__main__":
    main()
