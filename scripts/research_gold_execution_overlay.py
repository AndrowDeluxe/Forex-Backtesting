"""Tests the Execution-Overlay concept (Zarattini & Pagani 2026, see
app_pages/execution_overlay_writeup.py) against the Gold ASB: does waiting
for a short counter-direction M15 bar after the breakout trigger, before
actually filling, improve on filling immediately at the wick touch -
holding the signal (which window breaks out, which direction) completely
fixed and changing ONLY entry timing/price?

Compared on two levels:
  1. Raw, unfiltered trades (clean signal-vs-execution-timing comparison,
     matching the paper's own isolated test design).
  2. The full production filter stack (ADX>=15, Trend-Bias, Entry-Delay<=3,
     Silver-5d-Alignment) - the actually-deployed configuration. Since the
     overlay itself already delays entry, the existing Entry-Delay filter
     is tested both included and dropped for the overlay variant.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from asian_range_breakout.data import fetch_gold_m15
from asian_range_breakout.engine import simulate_asian_breakout
from asian_range_breakout.execution_overlay import simulate_asian_breakout_overlay
from asian_range_breakout.filters import (
    apply_adx_filter,
    apply_entry_delay_filter,
    apply_silver_alignment_filter,
    apply_trend_bias_filter,
)
from combined_strategy.data import fetch_timeframe
from strategy.metrics import trade_stats

START, END = "2016-01-01", "2026-07-29"
SPLIT = pd.Timestamp("2021-01-01", tz="America/New_York")


def fmt(stats: dict) -> str:
    if stats["n_trades"] == 0:
        return "n=0"
    return f"n={stats['n_trades']:>4}  WR={stats['win_rate']:.1%}  PF={stats['profit_factor']:.3f}"


def production_stack(trades, daily_close_gold, daily_close_silver, include_delay=True):
    t = apply_adx_filter(trades, adx_min=15)
    t = apply_trend_bias_filter(t, daily_close_gold, sma_window=200)
    if include_delay:
        t = apply_entry_delay_filter(t, max_delay_bars=3)
    t = apply_silver_alignment_filter(t, daily_close_silver, window=5)
    return t.sort_values("entry_time").reset_index(drop=True)


def main():
    print(f"Fetching GOLD/SILVER M15 {START} -> {END} ...")
    df = fetch_gold_m15(START, END)
    daily_close_gold = df["close"].tz_localize(None).resample("D").last().dropna()
    silver_m15 = fetch_timeframe("SILVER", "M15", START, END)
    daily_close_silver = silver_m15["Close"].tz_localize(None).resample("D").last().dropna()

    print("Simulating wick-mode (baseline) and overlay-mode trades...")
    trades_wick = simulate_asian_breakout(df)  # entry_mode="wick", the current production default
    trades_overlay = simulate_asian_breakout_overlay(df)

    print("\n" + "=" * 78)
    print("1. RAW (UNFILTERED) -- signal held fixed, only entry timing changes")
    print("=" * 78)
    print(f"  Wick (immediate fill):     {fmt(trade_stats(trades_wick))}")
    print(f"  Overlay (wait for pullback): {fmt(trade_stats(trades_overlay))}")
    fill_rate_wick = len(trades_wick) / (len(trades_wick))  # trivially 1.0, kept for symmetry/clarity below
    print(f"  Overlay fill rate vs wick-mode trade count: {len(trades_overlay) / len(trades_wick):.1%} "
          f"({len(trades_overlay)}/{len(trades_wick)} windows still produced a trade)")
    if len(trades_overlay):
        print(f"  Median wait (bars) for pullback confirmation: {trades_overlay['wait_bars'].median():.0f} "
              f"(~{trades_overlay['wait_bars'].median() * 15:.0f} min)")

    print("\n" + "=" * 78)
    print("2. FULL PRODUCTION FILTER STACK (ADX>=15, Trend-Bias, Entry-Delay<=3, Silver-5d)")
    print("=" * 78)
    prod_wick = production_stack(trades_wick, daily_close_gold, daily_close_silver, include_delay=True)
    prod_overlay_with_delay = production_stack(trades_overlay, daily_close_gold, daily_close_silver, include_delay=True)
    prod_overlay_no_delay = production_stack(trades_overlay, daily_close_gold, daily_close_silver, include_delay=False)
    print(f"  Wick + full stack (current production):        {fmt(trade_stats(prod_wick))}")
    print(f"  Overlay + full stack (incl. Entry-Delay<=3):    {fmt(trade_stats(prod_overlay_with_delay))}")
    print(f"  Overlay + stack minus Entry-Delay (overlay already delays): {fmt(trade_stats(prod_overlay_no_delay))}")

    best_overlay_variant = prod_overlay_no_delay if trade_stats(prod_overlay_no_delay)["profit_factor"] > trade_stats(prod_overlay_with_delay)["profit_factor"] else prod_overlay_with_delay
    best_label = "Overlay (ohne Entry-Delay-Filter)" if best_overlay_variant is prod_overlay_no_delay else "Overlay (mit Entry-Delay-Filter)"

    print("\n" + "=" * 78)
    print(f"3. IS/OOS -- Wick-Produktion vs. bester Overlay-Variante ({best_label})")
    print("=" * 78)
    for label, trades in [("Wick (Produktion)", prod_wick), (best_label, best_overlay_variant)]:
        is_t = trades[trades["entry_time"] < SPLIT]
        oos_t = trades[trades["entry_time"] >= SPLIT]
        print(f"\n  {label}")
        print(f"    Full: {fmt(trade_stats(trades))}")
        print(f"    IS  : {fmt(trade_stats(is_t))}")
        print(f"    OOS : {fmt(trade_stats(oos_t))}")

    print("\n" + "=" * 78)
    print(f"4. OUTLIER-SENSITIVITY CHECK -- {best_label} (drop single best trade)")
    print("=" * 78)
    sorted_ret = best_overlay_variant["return_pct"].sort_values(ascending=False)
    without_best = best_overlay_variant.drop(index=sorted_ret.index[0])
    s_full = trade_stats(best_overlay_variant)
    s_wo = trade_stats(without_best)
    print(f"  Full PF:               {s_full['profit_factor']:.3f}")
    print(f"  Ohne besten Trade PF:  {s_wo['profit_factor']:.3f}")
    if s_wo["profit_factor"] <= 1.0:
        print("  -> PF kollabiert auf <=1.0 ohne den einzelnen besten Trade: Edge ist Ausreisser-getrieben.")
    else:
        print("  -> PF bleibt ueber 1.0 auch ohne den besten Trade.")

    print(
        "\nHinweis: Der Overlay ist bewusst konservativ umgesetzt (M15-Bar-Close als Pullback-Proxy, "
        "kein separates Fast-Alpha-Signal aus Tick-Daten) - eine Verschlechterung koennte an der groben "
        "Aufloesung liegen, nicht zwingend am Konzept selbst. Trade-Anzahl-Verlust durch verpasste Fuellungen "
        "(kein Pullback vor Sessionende) ist der zentrale Trade-off, den das Paper selbst benennt. Dieser "
        "Screening-Lauf ersetzt KEIN Walk-Forward (siehe asian_range_breakout/walkforward.py-Muster) - das "
        "waere der naechste Schritt vor jeder Produktions-Uebernahme."
    )


if __name__ == "__main__":
    main()
