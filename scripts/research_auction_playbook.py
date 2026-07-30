"""Backtest the rebuilt Fabio Valentini Auction Market Playbook reconstruction
(auction_playbook/, unified value-area-breakout state machine: a held
breakout -> Trend Continuation, a failed/reclaimed breakout -> Mean
Reversion) on real Binance crypto data, in several variants, and report
honest results.

Second-pass rebuild after the first draft was discarded: this version ties
both setups to the *same* previous-day value area reference (rather than an
invented ATR-displacement "balance" heuristic for Trend), and - after
testing showed the source's literal "target = previous balance POC" for
Trend Continuation is structurally almost always unreachable once a
continuation leg has genuinely formed (confirmed empirically: 41/46
candidate setups failed only on that check) - exits Trend Continuation on
counter-aggression instead, per the source's own worked example and the
user's explicit choice when this was flagged. Mean Reversion keeps its POC
target unchanged (no comparable contradiction there).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from auction_playbook.data import fetch_klines
from auction_playbook.metrics import trade_stats
from auction_playbook.signals import PlaybookConfig, generate_playbook_trades

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2025-08-01", "2026-07-29"


def run_variant(label: str, symbol: str, interval: str, cfg: PlaybookConfig):
    print(f"\n{'=' * 90}\n=== {label} ({symbol}, {interval}) ===\n{'=' * 90}")
    df = fetch_klines(symbol, interval, START, END)
    print(f"Bars: {len(df)}  ({df.index.min()} .. {df.index.max()})")

    trades = generate_playbook_trades(df, cfg)
    for setup in ["trend_continuation", "mean_reversion"]:
        sub = trades[trades["setup"] == setup] if not trades.empty else trades
        stats = trade_stats(sub)
        print(f"\n--- {setup} ---")
        print({k: v for k, v in stats.items() if k != "exit_reason_counts"})
        print("Exit-Gruende:", stats["exit_reason_counts"])
        if not sub.empty:
            print(sub[["entry_time", "direction", "return_pct", "r_multiple", "exit_reason", "hold_bars"]].to_string(index=False))

    return trades


def main():
    run_variant("Basis (Default-Parameter)", "BTCUSDT", "5m", PlaybookConfig())
    run_variant("ETHUSDT, gleiche Parameter", "ETHUSDT", "5m", PlaybookConfig())
    run_variant("Strengere Aggression (z=2.0)", "BTCUSDT", "5m", PlaybookConfig(aggression_z=2.0))
    run_variant("Lockerere Aggression (z=1.0)", "BTCUSDT", "5m", PlaybookConfig(aggression_z=1.0))
    run_variant("Kuerzeres Reclaim-Fenster (12 Bars = 1h)", "BTCUSDT", "5m", PlaybookConfig(reclaim_window=12))
    run_variant("Groeberer Zeitrahmen (15m)", "BTCUSDT", "15m", PlaybookConfig(
        reclaim_window=8, impulse_extension_grace=3, max_leg_bars=32, retest_window=8, delta_std_window=48, max_hold_bars=32,
    ))


if __name__ == "__main__":
    main()
