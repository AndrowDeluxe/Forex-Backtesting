"""Test the "CLS Advanced" settlement-window breakout/hold framework
(strategy/cls_advanced.py) on real Dukascopy M15 data, restricted to the 6
major FX pairs and the last 4 weeks (per the source material's own
"Hausaufgabe: 10 Tage testen" - this is a short first look, not a
multi-year walk-forward like the other research_*.py scripts here; treat
all results as descriptive/directional only, not a validated edge).

Reports two things separately:
1. Classification stats: of the days with a 06:00-09:00 Asia-range
   breakout, how often does it hold at the 09:15 test vs. fail - and does
   the cross-pair confirmation actually predict that. This is the
   framework's core empirical question ("wann haelt der Move und wann
   nicht"), independent of any specific trade rule.
2. A backtest of the two trade models the decision tree implies:
   continuation (enter with a held+confirmed break) and reversal (fade an
   unheld break), both exiting by 12:00 Berlin (the source's "Funding
   Ziel") or on an ATR-based invalidation stop, whichever comes first.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dukascopy_python
import numpy as np
import pandas as pd

from strategy.backtest import BacktestConfig, simulate_trades
from strategy.cls_advanced import PAIRS, build_backtest_frame, compute_cross_confirmation, compute_daily_features
from strategy.metrics import trade_stats
from strategy.real_data import fetch_pair_history

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2026-07-01", "2026-07-29"  # last 4 weeks
LONG_START, LONG_END = "2016-07-28", "2026-07-28"  # full Dukascopy depth, same window other modules here use
# 09:30 Berlin entry -> 12:00 Berlin time-exit is 2.5h = 10 M15 bars.
CONFIG = BacktestConfig(spread_bps=0.3, stop_atr_mult=0.5, max_hold_bars=10, use_vwap_target=False)


def classification_table(daily: dict, confirm: dict) -> pd.DataFrame:
    rows = []
    for pair in PAIRS:
        d = daily[pair].copy()
        d["confirmed"] = confirm[pair].reindex(d.index)
        broke = d[d["direction"] != 0]
        n_confirmed = int(broke["confirmed"].sum())
        n_unconfirmed = len(broke) - n_confirmed
        rows.append(
            {
                "pair": pair, "tage": len(d), "breakouts": len(broke),
                "davon_confirmed": n_confirmed, "davon_unconfirmed": n_unconfirmed,
                "hold_rate_gesamt": broke["holds_0915"].mean(),
                "hold_rate_confirmed": broke.loc[broke["confirmed"] == True, "holds_0915"].mean() if n_confirmed else np.nan,  # noqa: E712
                "hold_rate_unconfirmed": broke.loc[broke["confirmed"] == False, "holds_0915"].mean() if n_unconfirmed else np.nan,  # noqa: E712
                "post_settle_continuation_rate": broke["realized_continuation"].mean(),
            }
        )
    return pd.DataFrame(rows).set_index("pair")


def backtest_table(bars: dict, daily: dict, confirm: dict, mode: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, all_trades = [], []
    for pair in PAIRS:
        signaled = build_backtest_frame(bars[pair], daily[pair], confirm[pair], mode=mode)
        trades = simulate_trades(signaled, CONFIG)
        if not trades.empty:
            trades.insert(0, "pair", pair)
            all_trades.append(trades)
        stats = trade_stats(trades)
        stats.pop("exit_reason_counts", None)
        rows.append({"pair": pair, **stats})
    pooled = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    return pd.DataFrame(rows).set_index("pair"), pooled


def yearly_breakdown(bars: dict, daily: dict, confirm: dict, mode: str) -> pd.DataFrame:
    """Per-calendar-year pooled stats across all 6 pairs (same walk-forward
    spirit as research_cls_squeeze.py's yearly_walk_forward, adapted to this
    signal's day-level granularity instead of bar-level)."""
    all_trades = []
    for pair in PAIRS:
        signaled = build_backtest_frame(bars[pair], daily[pair], confirm[pair], mode=mode)
        trades = simulate_trades(signaled, CONFIG)
        if not trades.empty:
            trades.insert(0, "pair", pair)
            all_trades.append(trades)
    if not all_trades:
        return pd.DataFrame()
    pooled = pd.concat(all_trades, ignore_index=True)
    pooled["year"] = pooled["entry_time"].dt.year
    rows = []
    for year, g in pooled.groupby("year"):
        stats = trade_stats(g)
        stats.pop("exit_reason_counts", None)
        rows.append({"year": year, **stats})
    return pd.DataFrame(rows).set_index("year")


def run_period(bars: dict, label: str):
    daily = {pair: compute_daily_features(df) for pair, df in bars.items()}
    confirm = compute_cross_confirmation(daily)

    print(f"\n{'=' * 90}\n=== {label} ===\n{'=' * 90}")

    print("\n--- Klassifikation: wann haelt der Move, wann nicht? ---\n")
    class_df = classification_table(daily, confirm)
    print(class_df.to_string(float_format=lambda x: f"{x:.2f}"))
    agg = class_df[["tage", "breakouts", "davon_confirmed"]].sum()
    print(f"\nGesamt: {agg['tage']} Pair-Tage, {agg['breakouts']} Breakouts, {agg['davon_confirmed']} davon cross-confirmed.")

    for mode, title in [("continuation", "Continuation-Modell (Break haelt + cross-confirmed)"), ("reversal", "Reversal-Modell (Break haelt NICHT -> Fade)")]:
        print(f"\n--- Backtest: {title} ---\n")
        per_pair, pooled = backtest_table(bars, daily, confirm, mode)
        print(per_pair.to_string(float_format=lambda x: f"{x:.4f}"))
        if not pooled.empty:
            stats = trade_stats(pooled)
            print(f"\nGepoolt (alle Paare): n={stats['n_trades']}, win_rate={stats['win_rate']:.2%}, "
                  f"profit_factor={stats['profit_factor']:.3f}, avg_return={stats['avg_return_pct'] * 1e4:.2f} bps")
        if label.startswith("LANG"):
            print("\nJahres-Aufschluesselung (gepoolt, alle Paare):")
            print(yearly_breakdown(bars, daily, confirm, mode).to_string(float_format=lambda x: f"{x:.4f}"))

    return daily, confirm


def main():
    print("Lade Kurzzeitraum (letzte 4 Wochen)...")
    bars_short = {pair: fetch_pair_history(pair, START, END, interval=dukascopy_python.INTERVAL_MIN_15) for pair in PAIRS}
    run_period(bars_short, f"KURZ: {START} bis {END} (letzte 4 Wochen)")

    print("\nLade Langzeitraum (10 Jahre)...")
    bars_long = {pair: fetch_pair_history(pair, LONG_START, LONG_END, interval=dukascopy_python.INTERVAL_MIN_15) for pair in PAIRS}
    run_period(bars_long, f"LANG: {LONG_START} bis {LONG_END} (10 Jahre)")


if __name__ == "__main__":
    main()
