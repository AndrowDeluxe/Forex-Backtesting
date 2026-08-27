"""asia_ote Stage 2 (chat 2026-08-21): voller Exit-Sweep auf die Top-3
Stage-1-Strukturkombinationen (Stage 1 war strukturell durchgehend
negativ, aber mit willkuerlichen Exit-Default-Werten gerechnet - hier
wird geprueft, ob eine bessere Exit-Konfiguration das rettet, bevor der
Befund als endgueltig gilt)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from asia_ote.data import fetch_eurusd_d1, fetch_eurusd_h1, fetch_eurusd_m15
from asia_ote.engine import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="Europe/Berlin")
SPREAD_BPS = 8.0
MIN_IS_TRADES = 15

# Top-3 aus Stage 1 (nach IS-Sharpe, trotz durchgehend negativ)
CANDIDATES = [
    dict(entry_variant="range_breakout", direction_mode="prev_asia", target_mode="monthly_pivot"),
    dict(entry_variant="candle_reaction", premium_ratio=0.86, direction_mode="trend_strength", target_mode="monthly_pivot"),
    dict(entry_variant="fib_limit", premium_ratio=0.568, direction_mode="trend_strength", target_mode="monthly_pivot"),
]

MTD_CANDIDATES = [0.0, 0.5, 1.0, 2.0]
WINDOW_END_CANDIDATES = [9.0, 12.0, 18.0, 24.0]
STOP_BUFFER_CANDIDATES = [0.0, 0.5, 1.0]
MAX_HOLD_H_CANDIDATES = [24, 96, 168, 336]
MAX_HOLD_CANDIDATES = [h * 4 for h in MAX_HOLD_H_CANDIDATES]
BE_CANDIDATES = [None, 0.5, 1.0]


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:>6.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"


def main():
    print(f"Fetching EURUSD M15/H1/D1 {START} -> {END} ...")
    m15 = fetch_eurusd_m15(START, END)
    h1 = fetch_eurusd_h1(START, END)
    d1 = fetch_eurusd_d1("2024-01-01", END)

    for cand in CANDIDATES:
        label = f"{cand['entry_variant']}/{cand.get('premium_ratio','-')}/{cand['direction_mode']}/{cand['target_mode']}"
        print(f"\n{'='*100}\n{label}\n{'='*100}")

        rows = []
        for mtd in MTD_CANDIDATES:
            for window_end in WINDOW_END_CANDIDATES:
                sig = run_pipeline(m15, d1, trend_df=h1, min_target_distance_atr=mtd, entry_window_end_hour=window_end, **cand)
                sig_is = sig[sig.index < SPLIT]
                for stop_buf in STOP_BUFFER_CANDIDATES:
                    for max_hold, hours in zip(MAX_HOLD_CANDIDATES, MAX_HOLD_H_CANDIDATES):
                        for be in BE_CANDIDATES:
                            cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_buf, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=max_hold)
                            s = summarize(simulate_trades(sig_is, cfg), sig_is.index)
                            rows.append({"mtd": mtd, "window_end": window_end, "stop_buf": stop_buf, "max_hold_h": hours, "be": be, **s})

        sweep = pd.DataFrame(rows)
        eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
        print(f"{len(sweep)} combos tested, {len(eligible)} reach n>={MIN_IS_TRADES} IS trades")
        if eligible.empty:
            print("Kein Kandidat erreicht den Trade-Mindestwert.")
            continue

        best = eligible.loc[eligible["sharpe"].idxmax()]
        print(f"Standout (IS Sharpe): mtd={best['mtd']} window_end={best['window_end']} stop_buf={best['stop_buf']} max_hold={best['max_hold_h']}h be={best['be']}")
        print(f"  IS: {fmt(best.to_dict())}")

        sig_full = run_pipeline(m15, d1, trend_df=h1, min_target_distance_atr=float(best["mtd"]), entry_window_end_hour=float(best["window_end"]), **cand)
        sig_oos = sig_full[sig_full.index >= SPLIT]
        be_val = None if pd.isna(best["be"]) else float(best["be"])
        cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=float(best["stop_buf"]), use_vwap_target=True, breakeven_trigger_r=be_val, max_hold_bars=int(best["max_hold_h"]) * 4)
        oos_trades = simulate_trades(sig_oos, cfg)
        oos_stats = summarize(oos_trades, sig_oos.index)
        print(f"  -> OOS: {fmt(oos_stats)}")
        if not oos_trades.empty and len(oos_trades) > 1:
            sorted_ret = oos_trades["return_pct"].sort_values(ascending=False)
            wo = oos_trades.drop(index=sorted_ret.index[0])
            s_wo = summarize(wo, sig_oos.index)
            print(f"     Outlier-Check: Sharpe {oos_stats['sharpe']:.2f} -> {s_wo['sharpe']:.2f}")

    daily_close = m15[m15.index >= SPLIT]["close"].resample("1D").last().dropna()
    daily_ret = daily_close.pct_change().fillna(0.0)
    daily_ret.iloc[0] -= SPREAD_BPS / 2 / 1e4
    print(f"\nBuy & Hold EURUSD (OOS): Sharpe={annualized_sharpe(daily_ret):.2f}  CAGR={cagr(daily_ret):+.1%}  MaxDD={max_drawdown(daily_ret):.1%}")


if __name__ == "__main__":
    main()
