"""Follow-up to research_gold_smc_continuation_trendline.py (chat
2026-08-19, "weiter mit der Entry Validierung im Continuation Fenster").
Mirrors the h1_bos_min investigation already done for the reversal
cascade: continuation.py's H1 confirmation currently requires only a
SINGLE trend-aligned BOS (h1_bos_min=1, unchanged default). This tests
whether requiring 2 or 3 consecutive same-direction BOS events (a
stronger, rarer confirmation) improves on the standing-best "direct"
entry_variant config (mtd=0.5, stop=0.5, be=None -> OOS Sharpe 1.62).
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

BOS_MIN_CANDIDATES = [1, 2, 3]
STOP_ATR_CANDIDATES = [0.5, 1.0, 1.5, 2.0, 3.0]
BE_CANDIDATES = [None, 0.5, 1.0, 1.5]
MTD_CANDIDATES = [0.5, 1.0]


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

    print("\nRunning pipeline once per (h1_bos_min, mtd) ...")
    signaled_by_key = {}
    for bos_min in BOS_MIN_CANDIDATES:
        for mtd in MTD_CANDIDATES:
            sig = run_pipeline(h4, h1, m5, trend_df=m15, trend_indicator="adx_di", htf_valid_bars=HTF_VALID_BARS, entry_variant="direct", min_target_distance_atr=mtd, h1_bos_min=bos_min)
            signaled_by_key[(bos_min, mtd)] = sig
            print(f"  bos_min={bos_min} mtd={mtd}: {int((sig['signal'] != 0).sum())} raw signals")

    print("\n" + "=" * 78)
    print(f"1. SWEEP - IS PERIOD ONLY, spread_bps={SPREAD_BPS}")
    print("=" * 78)
    rows = []
    for (bos_min, mtd), sig in signaled_by_key.items():
        sig_is = sig[sig.index < SPLIT]
        for stop_mult in STOP_ATR_CANDIDATES:
            for be in BE_CANDIDATES:
                cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
                trades = simulate_trades(sig_is, cfg)
                s = summarize(trades, sig_is.index)
                rows.append({"bos_min": bos_min, "mtd": mtd, "stop_atr": stop_mult, "be": be, **s})

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    print(f"\n{len(sweep)} combos tested, {len(eligible)} reach n>={MIN_IS_TRADES} IS trades")
    if eligible.empty:
        print("Stopping.")
        return
    top15 = eligible.sort_values("sharpe", ascending=False).head(15)
    print("\nTop 15 combos by IS Sharpe:")
    print(top15[["bos_min", "mtd", "stop_atr", "be", "n_trades", "win_rate", "profit_factor", "sharpe", "cagr"]].to_string(index=False))

    print("\nBest combo PER bos_min (by IS Sharpe, n>=15):")
    for bos_min in BOS_MIN_CANDIDATES:
        sub = eligible[eligible["bos_min"] == bos_min]
        if sub.empty:
            print(f"  bos_min={bos_min}: no combo reaches n>={MIN_IS_TRADES}")
            continue
        b = sub.loc[sub["sharpe"].idxmax()]
        print(f"  bos_min={bos_min} mtd={b['mtd']} stop={b['stop_atr']} be={b['be']}  {fmt(b.to_dict())}")

        sig_full = signaled_by_key[(bos_min, float(b["mtd"]))]
        sig_oos = sig_full[sig_full.index >= SPLIT]
        be_val = None if pd.isna(b["be"]) else float(b["be"])
        cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=float(b["stop_atr"]), use_vwap_target=True, breakeven_trigger_r=be_val, max_hold_bars=MAX_HOLD_BARS)
        oos_trades = simulate_trades(sig_oos, cfg)
        oos_stats = summarize(oos_trades, sig_oos.index)
        print(f"    -> OOS: {fmt(oos_stats)}")

    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\nStandout combo overall (highest IS Sharpe, n>={MIN_IS_TRADES}):")
    print(f"  bos_min={best['bos_min']} mtd={best['mtd']} stop={best['stop_atr']} be={best['be']}")
    print(f"  {fmt(best.to_dict())}")

    bos_min, mtd = int(best["bos_min"]), float(best["mtd"])
    stop_mult = float(best["stop_atr"])
    be = None if pd.isna(best["be"]) else float(best["be"])

    print("\n" + "=" * 78)
    print("2. OOS VALIDATION - chosen config applied UNTOUCHED to 2025-08 to 2026-08")
    print("=" * 78)
    sig_full = signaled_by_key[(bos_min, mtd)]
    sig_oos = sig_full[sig_full.index >= SPLIT]
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
    oos_trades = simulate_trades(sig_oos, cfg)
    oos_stats = summarize(oos_trades, sig_oos.index)
    print(f"  OOS: {fmt(oos_stats)}")

    print("\n" + "=" * 78)
    print("3. OUTLIER-SENSITIVITY CHECK ON OOS (drop single best trade)")
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
    print("4. BUY & HOLD COMPARISON (same OOS window)")
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
