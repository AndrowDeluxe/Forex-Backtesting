"""Final re-check of Continuation's M5 entry_variant options (chat
2026-08-20: "teste noch ein letztes mal die Entry Logik im M5 mit den
Trendfiltern im HTF wie gehabt"). All 5 entry variants (direct, double,
zone, repeat_sweep, trendline) were tested and direct won - but that was
under the OLD adx_di/M15 trend filter, before ema_adx_combo/M15 was
found to be a real upgrade (OOS Sharpe 1.62 -> 1.95). Since the trend
filter change alters the underlying H1 signal set entirely, this gives
zone/repeat_sweep/trendline a fair re-check against the NEW trend filter,
each with its own exit sweep (not just reusing direct's tuned exits -
the same mistake corrected for the H1/H4 trend-tf check).
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
MTD_CANDIDATES = [0.5, 1.0]
ZONE_ATR_CANDIDATES = [0.15, 0.3, 0.5]

STOP_ATR_CANDIDATES = [0.5, 1.0, 1.5, 3.0]
BE_CANDIDATES = [None, 0.5, 1.0]
TP_VARIANTS = [("h4_level", None)] + [("atr", tp_r) for tp_r in (2.0, 3.0, 5.0)]

CHAMPION_OOS_SHARPE = 1.95


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"


def build_cfg(tp_mode: str, tp_r, stop: float, be) -> BacktestConfig:
    if tp_mode == "h4_level":
        return BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
    return BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop, use_vwap_target=False, take_profit_r=tp_r, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)


def main():
    print(f"Fetching GOLD H4/H1/M15/M5 {START} -> {END} ...")
    h4 = fetch_gold_h4(START, END)
    h1 = fetch_gold_h1(START, END)
    m15 = fetch_gold_m15(START, END)
    m5 = fetch_gold_m5(START, END)
    print(f"H4={len(h4)} H1={len(h1)} M15={len(m15)} M5={len(m5)}")

    print("\nRunning pipeline once per (entry_variant, mtd[, zone_atr]) with trend_indicator=ema_adx_combo/M15 ...")
    signaled_by_key = {}
    for mtd in MTD_CANDIDATES:
        for variant in ("direct", "repeat_sweep", "trendline"):
            sig = run_pipeline(h4, h1, m5, trend_df=m15, trend_indicator="ema_adx_combo", htf_valid_bars=HTF_VALID_BARS, entry_variant=variant, min_target_distance_atr=mtd)
            signaled_by_key[(variant, mtd, None)] = sig
            print(f"  {variant:<13} mtd={mtd}: {int((sig['signal'] != 0).sum())} raw signals")
        for zone_atr in ZONE_ATR_CANDIDATES:
            sig = run_pipeline(h4, h1, m5, trend_df=m15, trend_indicator="ema_adx_combo", htf_valid_bars=HTF_VALID_BARS, entry_variant="zone", min_target_distance_atr=mtd, zone_atr=zone_atr)
            signaled_by_key[("zone", mtd, zone_atr)] = sig
            print(f"  {'zone':<13} mtd={mtd} zone_atr={zone_atr}: {int((sig['signal'] != 0).sum())} raw signals")

    print("\n" + "=" * 78)
    print(f"SWEEP - IS PERIOD ONLY, spread_bps={SPREAD_BPS}, both TP modes")
    print("=" * 78)
    rows = []
    for (variant, mtd, zone_atr), sig in signaled_by_key.items():
        sig_is = sig[sig.index < SPLIT]
        for tp_mode, tp_r in TP_VARIANTS:
            for stop in STOP_ATR_CANDIDATES:
                for be in BE_CANDIDATES:
                    cfg = build_cfg(tp_mode, tp_r, stop, be)
                    s = summarize(simulate_trades(sig_is, cfg), sig_is.index)
                    rows.append({"variant": variant, "mtd": mtd, "zone_atr": zone_atr, "tp_mode": tp_mode, "tp_r": tp_r, "stop_atr": stop, "be": be, **s})
        print(f"  {variant} mtd={mtd} zone_atr={zone_atr} done")

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    print(f"\n{len(sweep)} combos tested, {len(eligible)} reach n>={MIN_IS_TRADES} IS trades")
    if eligible.empty:
        print("Stopping.")
        return
    top15 = eligible.sort_values("sharpe", ascending=False).head(15)
    print("\nTop 15 combos by IS Sharpe:")
    print(top15[["variant", "mtd", "zone_atr", "tp_mode", "tp_r", "stop_atr", "be", "n_trades", "win_rate", "profit_factor", "sharpe", "cagr"]].to_string(index=False))

    print("\nBest combo PER entry_variant (by IS Sharpe, n>=15):")
    for variant in ("direct", "zone", "repeat_sweep", "trendline"):
        sub = eligible[eligible["variant"] == variant]
        if sub.empty:
            print(f"  {variant:<13}: no combo reaches n>={MIN_IS_TRADES}")
            continue
        b = sub.loc[sub["sharpe"].idxmax()]
        print(f"  {variant:<13} mtd={b['mtd']} zone_atr={b['zone_atr']} tp={b['tp_mode']}/{b['tp_r']} stop={b['stop_atr']} be={b['be']}  {fmt(b.to_dict())}")

        variant_sig_full = signaled_by_key[(variant, float(b["mtd"]), None if pd.isna(b["zone_atr"]) else float(b["zone_atr"]))]
        variant_sig_oos = variant_sig_full[variant_sig_full.index >= SPLIT]
        be_val = None if pd.isna(b["be"]) else float(b["be"])
        tp_r_val = None if pd.isna(b["tp_r"]) else float(b["tp_r"])
        variant_cfg = build_cfg(b["tp_mode"], tp_r_val, float(b["stop_atr"]), be_val)
        variant_oos_trades = simulate_trades(variant_sig_oos, variant_cfg)
        print(f"    -> OOS: {fmt(summarize(variant_oos_trades, variant_sig_oos.index))}")

    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\nStandout combo overall (highest IS Sharpe, n>={MIN_IS_TRADES}):")
    print(f"  {best[['variant', 'mtd', 'zone_atr', 'tp_mode', 'tp_r', 'stop_atr', 'be']].to_dict()}")
    print(f"  {fmt(best.to_dict())}")

    variant, mtd = best["variant"], float(best["mtd"])
    zone_atr = None if pd.isna(best["zone_atr"]) else float(best["zone_atr"])
    tp_mode, tp_r = best["tp_mode"], (None if pd.isna(best["tp_r"]) else float(best["tp_r"]))
    stop, be = float(best["stop_atr"]), (None if pd.isna(best["be"]) else float(best["be"]))

    print("\n" + "=" * 78)
    print("OOS VALIDATION - chosen config applied UNTOUCHED to 2025-08 to 2026-08")
    print("=" * 78)
    sig_full = signaled_by_key[(variant, mtd, zone_atr)]
    sig_oos = sig_full[sig_full.index >= SPLIT]
    cfg = build_cfg(tp_mode, tp_r, stop, be)
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
    print(f"\n  Beats current champion (direct, OOS Sharpe={CHAMPION_OOS_SHARPE})? {'YES' if oos_stats['n_trades'] > 0 and oos_stats['sharpe'] > CHAMPION_OOS_SHARPE else 'no'}")
    print(f"  Beats buy-and-hold on Sharpe? {'YES' if oos_stats['n_trades'] > 0 and oos_stats['sharpe'] > bh_sharpe else 'no'}")


if __name__ == "__main__":
    main()
