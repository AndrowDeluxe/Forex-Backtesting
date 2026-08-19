"""Visualization for the reversal cascade's FINAL best config (chat
2026-08-19 request, second round: "zeig mir die Entrys nochmal visuell").

Winning config (research_gold_smc_reversal_cascade_v8.py + v9.py):
m15_entry_mode="repeat_sweep" (the "2x ueber denselben Punkt" LTF entry -
enter only on the SECOND M15 sweep-and-reject of the same h1_ref_level),
h4_confirm_bars=30, h1_valid_bars=24, require_ema_reject=True,
min_target_distance_atr=1.0, stop_atr_mult=3.0, breakeven_trigger_r=None,
tp_mode=atr (take_profit_r=5.0), max_hold_bars=96 (24h on M15).
OOS: n=41, WR=58.5%, PF=2.267, Sharpe=1.61, CAGR=+11.0%, MaxDD=-1.4% -
beats buy&hold on Sharpe, outlier-robust (PF 1.946 without best trade).

Produces:
  1. Per-exit-reason stats (count, win rate, avg return, contribution to
     total P&L) - quantifies whether max_hold trades are actually hurting
     or just capping upside/downside.
  2. Overview candlestick chart (mplfinance) over a representative OOS
     stretch with entry/exit markers colored by exit_reason.
  3. Individual zoomed charts for a few max_hold trades specifically,
     showing entry, stop level, target level (frozen at entry value for
     the visual, even though simulate_trades re-reads it live), and the
     full 96-bar window, to see what the price actually did.
All images saved as PNG to the scratchpad for embedding in an HTML report.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplfinance as mpf
import numpy as np
import pandas as pd

from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m15
from gold_smc_htf_ltf.reversal_cascade import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

OUT_DIR = Path(r"C:\Users\andre\AppData\Local\Temp\claude\c--Users-andre-Forex-Backtesting-knowledge\d6a799be-ce53-45be-9fe0-7c8911ea651e\scratchpad")
OUT_DIR.mkdir(parents=True, exist_ok=True)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0

MC = mpf.make_marketcolors(up="#26a69a", down="#ef5350", edge="inherit", wick="inherit", volume="in")
STYLE = mpf.make_mpf_style(marketcolors=MC, gridstyle=":", gridcolor="#2a2e39", facecolor="#131722", figcolor="#131722", edgecolor="#131722", rc={"axes.labelcolor": "#d1d4dc", "xtick.color": "#d1d4dc", "ytick.color": "#d1d4dc", "text.color": "#d1d4dc"})


def main():
    print("Fetching GOLD H4/H1/M15 ...")
    h4 = fetch_gold_h4(START, END)
    h1 = fetch_gold_h1(START, END)
    m15 = fetch_gold_m15(START, END)

    signaled = run_pipeline(h4, h1, m15, require_ema_reject=True, h4_confirm_bars=30, h1_valid_bars=24, min_target_distance_atr=1.0, m15_entry_mode="repeat_sweep")
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=3.0, use_vwap_target=False, take_profit_r=5.0, breakeven_trigger_r=None, max_hold_bars=96)
    oos_sig = signaled[signaled.index >= SPLIT]
    trades = simulate_trades(oos_sig, cfg)
    stats = summarize(trades, oos_sig.index)
    print(f"OOS: n={stats['n_trades']} WR={stats['win_rate']:.1%} PF={stats['profit_factor']:.3f} Sharpe={stats['sharpe']:.2f}")

    print("\n=== Per-exit-reason breakdown ===")
    for reason, grp in trades.groupby("exit_reason"):
        wins = (grp["return_pct"] > 0).mean()
        avg_ret = grp["return_pct"].mean()
        total_ret = grp["return_pct"].sum()
        avg_hold_h = (grp["hold_bars"] * 15 / 60).mean()
        print(f"  {reason:<10} n={len(grp):>3}  WR={wins:.1%}  avg_ret={avg_ret * 100:+.3f}%  sum_ret={total_ret * 100:+.2f}%  avg_hold={avg_hold_h:.1f}h")
    total_all = trades["return_pct"].sum()
    print(f"\n  Total return (sum of all trade returns): {total_all * 100:+.2f}%")
    maxhold = trades[trades["exit_reason"] == "max_hold"]
    print(f"  max_hold share of trade count: {len(maxhold) / len(trades):.1%}")
    print(f"  max_hold share of TOTAL P&L:   {maxhold['return_pct'].sum() / total_all:.1%}" if total_all != 0 else "")

    trades.to_csv(OUT_DIR / "reversal_v2_oos_trades.csv", index=False)
    print(f"\nSaved trades CSV -> {OUT_DIR / 'reversal_v2_oos_trades.csv'}")

    # --- 1. Overview chart: pick a 6-week stretch with several trades of different exit_reasons ---
    counts_by_month = trades.groupby(trades["entry_time"].dt.to_period("M")).size()
    print(f"\nTrades per month:\n{counts_by_month}")
    best_month = counts_by_month.idxmax()
    window_start = best_month.start_time.tz_localize("America/New_York") - pd.Timedelta(days=3)
    window_end = best_month.end_time.tz_localize("America/New_York") + pd.Timedelta(days=3)
    chart_df = m15.loc[window_start:window_end, ["open", "high", "low", "close", "volume"]]
    window_trades = trades[(trades["entry_time"] >= window_start) & (trades["entry_time"] <= window_end)]
    print(f"\nOverview window {window_start.date()} -> {window_end.date()}: {len(window_trades)} trades, {len(chart_df)} bars")

    reason_colors = {"target": "#26a69a", "stop": "#ef5350", "max_hold": "#ffa726", "breakeven": "#42a5f5"}
    apds = []
    entry_up = pd.Series(np.nan, index=chart_df.index)
    entry_down = pd.Series(np.nan, index=chart_df.index)
    for _, tr in window_trades.iterrows():
        if tr["entry_time"] in chart_df.index:
            if tr["direction"] == 1:
                entry_up.loc[tr["entry_time"]] = tr["entry_price"] * 0.997
            else:
                entry_down.loc[tr["entry_time"]] = tr["entry_price"] * 1.003
    if entry_up.notna().any():
        apds.append(mpf.make_addplot(entry_up, type="scatter", marker="^", markersize=90, color="#26a69a", panel=0))
    if entry_down.notna().any():
        apds.append(mpf.make_addplot(entry_down, type="scatter", marker="v", markersize=90, color="#ef5350", panel=0))
    for reason, color in reason_colors.items():
        exit_series = pd.Series(np.nan, index=chart_df.index)
        sub = window_trades[window_trades["exit_reason"] == reason]
        for _, tr in sub.iterrows():
            if tr["exit_time"] in chart_df.index:
                exit_series.loc[tr["exit_time"]] = tr["exit_price"]
        if exit_series.notna().any():
            apds.append(mpf.make_addplot(exit_series, type="scatter", marker="x", markersize=70, color=color, panel=0))

    fig, axlist = mpf.plot(
        chart_df, type="candle", style=STYLE, addplot=apds, volume=False, returnfig=True,
        figsize=(16, 8), title=f"\nGOLD M15 - Reversal Cascade OOS Trades ({window_start.date()} to {window_end.date()})",
    )
    legend_lines = [plt.Line2D([0], [0], marker="^", color="w", markerfacecolor="#26a69a", markersize=10, label="Entry Long", linestyle="None"),
                    plt.Line2D([0], [0], marker="v", color="w", markerfacecolor="#ef5350", markersize=10, label="Entry Short", linestyle="None")]
    for reason, color in reason_colors.items():
        legend_lines.append(plt.Line2D([0], [0], marker="x", color=color, markersize=10, label=f"Exit: {reason}", linestyle="None"))
    axlist[0].legend(handles=legend_lines, loc="upper left", facecolor="#131722", labelcolor="#d1d4dc", framealpha=0.9)
    fig.savefig(OUT_DIR / "overview_chart.png", dpi=130, facecolor="#131722")
    plt.close(fig)
    print(f"Saved overview chart -> {OUT_DIR / 'overview_chart.png'}")

    # --- 2. Zoomed max_hold examples ---
    def plot_examples(reason: str, n: int, prefix: str):
        sub = trades[trades["exit_reason"] == reason].copy()
        if sub.empty:
            print(f"No '{reason}' trades to plot.")
            return
        examples = sub.sort_values("entry_time").iloc[:n]
        for idx, (_, tr) in enumerate(examples.iterrows()):
            pad = pd.Timedelta(hours=8)
            w_start, w_end = tr["entry_time"] - pad, tr["exit_time"] + pad
            zoom_df = m15.loc[w_start:w_end, ["open", "high", "low", "close", "volume"]]
            if zoom_df.empty:
                continue
            stop_level = tr["entry_price"] - tr["direction"] * tr["initial_risk"]
            # tp_mode=atr (take_profit_r=5.0): target is a fixed R-multiple from entry, not h1_target
            target_level = tr["entry_price"] + tr["direction"] * 5.0 * tr["initial_risk"]

            hline_vals = [tr["entry_price"]] + ([stop_level] if not np.isnan(stop_level) else []) + ([target_level] if not np.isnan(target_level) else [])
            hline_colors = ["#d1d4dc"] + (["#ef5350"] if not np.isnan(stop_level) else []) + (["#26a69a"] if not np.isnan(target_level) else [])
            hlines = dict(hlines=hline_vals, colors=hline_colors, linestyle=["--"] * len(hline_vals), linewidths=[1.2] * len(hline_vals))

            entry_marker = pd.Series(np.nan, index=zoom_df.index)
            exit_marker = pd.Series(np.nan, index=zoom_df.index)
            if tr["entry_time"] in zoom_df.index:
                entry_marker.loc[tr["entry_time"]] = tr["entry_price"]
            if tr["exit_time"] in zoom_df.index:
                exit_marker.loc[tr["exit_time"]] = tr["exit_price"]
            apds_zoom = [
                mpf.make_addplot(entry_marker, type="scatter", marker="^" if tr["direction"] == 1 else "v", markersize=140, color="#ffffff", panel=0),
                mpf.make_addplot(exit_marker, type="scatter", marker="o", markersize=100, color="#ffa726", panel=0),
            ]
            direction_label = "LONG" if tr["direction"] == 1 else "SHORT"
            fig, axlist = mpf.plot(
                zoom_df, type="candle", style=STYLE, addplot=apds_zoom, hlines=hlines, volume=False, returnfig=True,
                figsize=(14, 7),
                title=f"\n{reason} Beispiel {idx + 1}: {direction_label}, entry={tr['entry_time'].strftime('%Y-%m-%d %H:%M')}, hold={tr['hold_bars']} bars ({tr['hold_bars']*15/60:.0f}h), return={tr['return_pct']*100:+.2f}%",
            )
            legend_lines = [plt.Line2D([0], [0], color="#d1d4dc", linestyle="--", label=f"Entry {tr['entry_price']:.1f}")]
            if not np.isnan(stop_level):
                legend_lines.append(plt.Line2D([0], [0], color="#ef5350", linestyle="--", label=f"Stop {stop_level:.1f}"))
            if not np.isnan(target_level):
                legend_lines.append(plt.Line2D([0], [0], color="#26a69a", linestyle="--", label=f"Target (5R) {target_level:.1f}"))
            axlist[0].legend(handles=legend_lines, loc="upper left", facecolor="#131722", labelcolor="#d1d4dc", framealpha=0.9)
            fname = OUT_DIR / f"{prefix}_example_{idx + 1}.png"
            fig.savefig(fname, dpi=130, facecolor="#131722")
            plt.close(fig)
            print(f"Saved {reason} example {idx + 1} -> {fname}")

    plot_examples("max_hold", 3, "maxhold")
    plot_examples("stop", 2, "stop")
    plot_examples("target", 2, "target")

    print("\nDone.")


if __name__ == "__main__":
    main()
