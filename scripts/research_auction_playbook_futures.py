"""Backtest the same unified Auction Market Playbook state machine
(auction_playbook/signals.py) on the paper's actual named instruments -
Futures: NASDAQ, ES - via Dukascopy's E-mini S&P 500 / Nasdaq-100 CFD
proxies (auction_playbook/dukascopy_data.py), run alongside the crypto
version (scripts/research_auction_playbook.py) for direct comparison.

Key difference from the crypto run: aggression here is an OHLC-shape proxy
(no real taker buy/sell split available from Dukascopy), so this run tests
whether matching the paper's actual asset class changes the picture versus
the crypto run's genuine order-flow signal on the wrong asset class - see
auction_playbook/dukascopy_data.py's docstring for the full disclosure.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from auction_playbook.dukascopy_data import fetch_index_bars
from auction_playbook.metrics import trade_stats
from auction_playbook.signals import PlaybookConfig, generate_playbook_trades

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2025-08-01", "2026-07-29"


def run_variant(label: str, symbol: str, interval: str, cfg: PlaybookConfig):
    print(f"\n{'=' * 90}\n=== {label} ({symbol}, {interval}) ===\n{'=' * 90}")
    df = fetch_index_bars(symbol, interval, START, END)
    print(f"Bars: {len(df)}  ({df.index.min()} .. {df.index.max()})")

    trades = generate_playbook_trades(df, cfg)
    for setup in ["trend_continuation", "mean_reversion"]:
        sub = trades[trades["setup"] == setup] if not trades.empty else trades
        stats = trade_stats(sub)
        print(f"\n--- {setup} ---")
        print({k: v for k, v in stats.items() if k != "exit_reason_counts"})
        print("Exit-Gruende:", stats["exit_reason_counts"])
        if not sub.empty:
            r = sub["r_multiple"].dropna()
            sub_sorted = sub.sort_values("return_pct", ascending=False)
            without_top1 = sub_sorted.iloc[1:]
            wins = without_top1["return_pct"] > 0
            gw, gl = without_top1.loc[wins, "return_pct"].sum(), -without_top1.loc[~wins, "return_pct"].sum()
            pf_ex1 = gw / gl if gl > 0 else float("inf")
            print(f"median_R={r.median():.2f}  PF_excl_best_trade={pf_ex1:.2f}  best_trade_bps={sub_sorted.iloc[0]['return_pct']*1e4:.1f}")
            print(sub[["entry_time", "direction", "return_pct", "r_multiple", "exit_reason", "hold_bars"]].to_string(index=False))

    return trades


def main():
    run_variant("Basis (Default-Parameter)", "SP500", "M5", PlaybookConfig())
    run_variant("NASDAQ, gleiche Parameter", "NASDAQ", "M5", PlaybookConfig())
    run_variant("Strengere Aggression (z=2.0)", "SP500", "M5", PlaybookConfig(aggression_z=2.0))
    run_variant("Lockerere Aggression (z=1.0)", "SP500", "M5", PlaybookConfig(aggression_z=1.0))
    run_variant("Kuerzeres Reclaim-Fenster (12 Bars = 1h)", "SP500", "M5", PlaybookConfig(reclaim_window=12))
    run_variant("Groeberer Zeitrahmen (M15)", "SP500", "M15", PlaybookConfig(
        reclaim_window=8, impulse_extension_grace=3, max_leg_bars=32, retest_window=8, delta_std_window=48, max_hold_bars=32,
    ))


if __name__ == "__main__":
    main()
