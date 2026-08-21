"""BTC-eigene Optimierung der Reversal-Kaskade (chat 2026-08-21) - der
einzige Cross-Market-Fund, der IS+OOS konsistent positiv war (Golds
Parameter unveraendert: Voll +0.40, IS +0.48, OOS +0.32), aber noch NICHT
selbst fuer BTC optimiert. Gleiche Disziplin wie die gesamte Gold-Arbeit:
Sweep auf IS -> Auswahl per IS-Sharpe (n>=15-Guard) -> unangetastete
OOS-Validierung -> Outlier-Check -> Vergleich mit Buy&Hold.

H4/H1-Struktur (h4_confirm_bars=30, h1_valid_bars=24) bleibt auf den
Gold-Standardwerten (Bar-basiert, nicht kalenderabhaengig - BTC hat keine
Wochenend-Luecke, die Bar-Zaehlung ist also strukturell vergleichbar);
LTF-Entry-Variante + komplette Exit-Konfiguration wird eigenstaendig fuer
BTC gesweept, nicht von Gold uebernommen."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from auction_playbook.data import fetch_klines
from gold_smc_htf_ltf.reversal_cascade import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0
MIN_IS_TRADES = 15

H4_CONFIRM_BARS, H1_VALID_BARS = 30, 24
ENTRY_MODES = ["sweep", "repeat_sweep", "ema_cross", "ema_touch", "trendline"]
MTD_CANDIDATES = [0.5, 1.0]
MAX_HOLD_H_CANDIDATES = [24, 48, 96, 168]
MAX_HOLD_CANDIDATES = [h * 4 for h in MAX_HOLD_H_CANDIDATES]  # M15-Bars
STOP_ATR_CANDIDATES = [0.5, 1.0, 1.5, 2.0, 3.0]
BE_CANDIDATES = [None, 0.5, 1.0]
TP_VARIANTS = [("h4_level", None)] + [("atr", tp_r) for tp_r in (2.0, 3.0, 4.0, 5.0)]


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:>6.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"


def build_cfg(tp_mode: str, tp_r, stop: float, be, max_hold: int) -> BacktestConfig:
    if tp_mode == "h4_level":
        return BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=max_hold)
    return BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop, use_vwap_target=False, take_profit_r=tp_r, breakeven_trigger_r=be, max_hold_bars=max_hold)


def main():
    print(f"Fetching BTC H4/H1/M15 {START} -> {END} ...")
    h4 = fetch_klines("BTCUSDT", "4h", START, END)
    h1 = fetch_klines("BTCUSDT", "1h", START, END)
    m15 = fetch_klines("BTCUSDT", "15m", START, END)
    for df in (h4, h1, m15):
        df.index = df.index.tz_localize("UTC").tz_convert("America/New_York") if df.index.tz is None else df.index.tz_convert("America/New_York")
    print(f"H4={len(h4)} H1={len(h1)} M15={len(m15)}")

    print("\nRunning pipeline once per (entry_mode, mtd) ...")
    signaled_by_key = {}
    for mode in ENTRY_MODES:
        for mtd in MTD_CANDIDATES:
            sig = run_pipeline(h4, h1, m15, h4_confirm_bars=H4_CONFIRM_BARS, h1_valid_bars=H1_VALID_BARS, min_target_distance_atr=mtd, require_ema_reject=True, m15_entry_mode=mode)
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
    sweep.to_csv(Path(__file__).resolve().parents[1] / "gold_smc_htf_ltf" / "_btc_reversal_sweep.csv", index=False)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    print(f"\n{len(sweep)} combos tested, {len(eligible)} reach n>={MIN_IS_TRADES} IS trades")
    if eligible.empty:
        print("Stopping - kein Kandidat erreicht den Trade-Mindestwert.")
        return

    top15 = eligible.sort_values("sharpe", ascending=False).head(15)
    print("\nTop 15 combos by IS Sharpe:")
    print(top15[["mode", "mtd", "max_hold_h", "tp_mode", "tp_r", "stop_atr", "be", "n_trades", "win_rate", "profit_factor", "sharpe", "cagr"]].to_string(index=False))

    print("\nBest combo PER entry mode (by IS Sharpe, n>=15):")
    for mode in ENTRY_MODES:
        sub = eligible[eligible["mode"] == mode]
        if sub.empty:
            print(f"  {mode:<13}: no combo reaches n>={MIN_IS_TRADES}")
            continue
        b = sub.loc[sub["sharpe"].idxmax()]
        print(f"  {mode:<13} mtd={b['mtd']} max_hold={b['max_hold_h']}h tp={b['tp_mode']}/{b['tp_r']} stop={b['stop_atr']} be={b['be']}  {fmt(b.to_dict())}")

        sig_full = signaled_by_key[(mode, float(b["mtd"]))]
        sig_oos = sig_full[sig_full.index >= SPLIT]
        be_val = None if pd.isna(b["be"]) else float(b["be"])
        tp_r_val = None if pd.isna(b["tp_r"]) else float(b["tp_r"])
        cfg = build_cfg(b["tp_mode"], tp_r_val, float(b["stop_atr"]), be_val, int(b["max_hold_h"]) * 4)
        oos_trades = simulate_trades(sig_oos, cfg)
        oos_stats = summarize(oos_trades, sig_oos.index)
        print(f"    -> OOS: {fmt(oos_stats)}")

    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\nStandout combo overall (highest IS Sharpe, n>={MIN_IS_TRADES}):")
    print(f"  {best[['mode', 'mtd', 'max_hold_h', 'tp_mode', 'tp_r', 'stop_atr', 'be']].to_dict()}")
    print(f"  {fmt(best.to_dict())}")

    mode, mtd = best["mode"], float(best["mtd"])
    max_hold = int(best["max_hold_h"]) * 4
    tp_mode, tp_r = best["tp_mode"], (None if pd.isna(best["tp_r"]) else float(best["tp_r"]))
    stop, be = float(best["stop_atr"]), (None if pd.isna(best["be"]) else float(best["be"]))

    print("\n" + "=" * 78)
    print("OOS VALIDATION - chosen config applied UNTOUCHED to 2025-08 to 2026-08")
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

    m15_oos = m15[m15.index >= SPLIT]
    daily_close = m15_oos["close"].resample("1D").last().dropna()
    daily_ret = daily_close.pct_change().fillna(0.0)
    daily_ret.iloc[0] -= SPREAD_BPS / 2 / 1e4
    bh_sharpe, bh_cagr, bh_mdd = annualized_sharpe(daily_ret), cagr(daily_ret), max_drawdown(daily_ret)
    print(f"  Buy & hold BTC:  Sharpe={bh_sharpe:.2f}  CAGR={bh_cagr:+.1%}  MaxDD={bh_mdd:.1%}")
    print(f"\n  Beats Gold-Parameter-Baseline (OOS Sharpe=0.32)? {'YES' if oos_stats['n_trades'] > 0 and oos_stats['sharpe'] > 0.32 else 'no'}")
    print(f"  Beats buy-and-hold on Sharpe? {'YES' if oos_stats['n_trades'] > 0 and oos_stats['sharpe'] > bh_sharpe else 'no'}")


if __name__ == "__main__":
    main()
