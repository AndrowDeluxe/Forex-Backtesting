"""Stage 9 - risk-scaling exploration, direct follow-up to Stage 8's width
finding. Every binary include/exclude filter tested in Stage 8 (width
threshold, direction-lock) HURT every instrument - shrinking the sample
lost more than any per-trade quality improvement gained. But the raw
diagnostic showed wide-vs-narrow opening ranges DO carry different average
outcomes (not just noise). Question: instead of excluding the "weaker"
trades, can a graded confirmation signal size them DOWN and the "stronger"
trades UP - keeping the full sample (no lost diversification/trade count)
while still capturing the differential edge? User's framing: "mehr
Bestaetigung -> mehr Risiko", i.e. a conviction-weighted position size
instead of a keep/reject gate.

Caveat stated up front: this project's daily-return-based Sharpe/CAGR
metrics (strategy.metrics.summarize, used everywhere except Stage 7's real
dollar account sim) implicitly assume one fixed-notional unit per trade,
not risk-based position sizing. A "risk multiplier" here is approximated
by scaling each trade's return_pct directly before compounding into daily
returns - the same level of simplification Stage 1-6 already operate at,
NOT Stage 7's real position-sized simulation. Results are directional
(does grading beat flat-risk on this proxy) - a Stage-7-style real-account
re-test would be the way to confirm any adopted scaling scheme before
sizing real money by it.

Part A - signal-quality quintile scan: for each instrument, on BOTH raw
stop_breakout entries (full sample, isolates the signal from any filter
interaction) and the currently adopted standard-config entries, buckets
trades into quintiles by three candidate confirmation signals and reports
avg R-multiple/win-rate per bucket:
  - orb_width_percentile (Stage 8's signal, rolling 60-session rank)
  - adx_at_entry (M15 ADX at range-close - already computed per trade,
    Stage 3 found an ADX>=25 EXCLUSION filter hurt; untested as a scale)
  - rvol_at_time at entry (opening relative volume - Stage 3 found an
    exclusion/exit filter hurt; untested as a scale)
A clean MONOTONIC gradient across quintiles is what would make a signal
usable for scaling; flat or non-monotonic is not - reported honestly
either way, not just for the signals that happen to look clean.

Part B - for the signal(s) with the clearest gradient, simulates a
tercile-based risk multiplier (bottom=0.5x, middle=1.0x, top=1.5x) against
flat-risk (1.0x always) on the IDENTICAL trade set (same n, only sizing
differs) - the direct answer to "can we scale into more risk on
higher-confirmation trades".
"""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from ny_open_orb import filters, regime
from ny_open_orb.data import fetch_m15, fetch_m5
from ny_open_orb.engine import build_frame, find_entries, simulate
from strategy.backtest import trades_to_daily_returns
from strategy.metrics import summarize

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)

START, END = "2016-07-28", "2026-07-28"
SPLIT_DATE = "2021-07-28"

EXIT_CFG_BY_INSTRUMENT = {
    "SP500": dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0, partial_exit_r=2.0, partial_exit_fraction=0.5, move_stop_to_be_after_partial=True),
    "US30": dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0, partial_exit_r=2.0, partial_exit_fraction=0.5, move_stop_to_be_after_partial=True),
    "NASDAQ": dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0, partial_exit_r=1.5, partial_exit_fraction=0.5, move_stop_to_be_after_partial=True),
}
RAW_EXIT_CFG = dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0)


def standard_entries(instrument: str, frame: pd.DataFrame, m15: pd.DataFrame) -> pd.DataFrame:
    all_entries = find_entries(frame, "stop_breakout")
    if instrument == "NASDAQ":
        return filters.filter_by_weekday(all_entries, exclude=["Wednesday"])
    long_entries = filters.filter_by_direction(all_entries, 1)
    bias = regime.ema_trend_bias(m15, frame["session"].unique())
    bias_vals = filters.values_at(long_entries, bias)
    return filters.filter_by_category(long_entries, bias_vals, (0.0,))


def attach_signals(trades: pd.DataFrame, frame: pd.DataFrame, width_rank: pd.Series) -> pd.DataFrame:
    t = trades.copy()
    session = t["entry_time"].dt.normalize()
    t["width_rank"] = session.map(width_rank)
    t["rvol_at_entry"] = frame["rvol_at_time"].reindex(t["entry_time"]).to_numpy()
    return t


def bucket_report(trades: pd.DataFrame, signal_col: str, label: str, n_buckets: int = 5) -> None:
    df = trades.dropna(subset=[signal_col])
    if len(df) < n_buckets * 8:
        print(f"  {label}: zu wenig Daten (n={len(df)}), uebersprungen")
        return
    df = df.copy()
    df["_bucket"] = pd.qcut(df[signal_col], n_buckets, labels=False, duplicates="drop")
    g = df.groupby("_bucket").agg(n=("r_multiple", "size"), avg_r=("r_multiple", "mean"), win_rate=("r_multiple", lambda s: (s > 0).mean()))
    line = "  ".join(f"Q{b}(n={int(r['n'])},r={r['avg_r']:+.3f},win={r['win_rate']:.0%})" for b, r in g.iterrows())
    print(f"  {label:<28} {line}")


def scaled_vs_flat(trades: pd.DataFrame, frame: pd.DataFrame, signal_col: str, split_ts: pd.Timestamp, tercile_mults=(0.5, 1.0, 1.5)) -> None:
    df = trades.dropna(subset=[signal_col]).copy()
    if len(df) < 30:
        print(f"  {signal_col}: zu wenig Daten fuer Scaling-Test (n={len(df)})")
        return
    df["_tercile"] = pd.qcut(df[signal_col], 3, labels=False, duplicates="drop")
    mult_map = {t: m for t, m in zip(sorted(df["_tercile"].unique()), tercile_mults)}
    df["risk_mult"] = df["_tercile"].map(mult_map)
    df["return_pct_scaled"] = df["return_pct"] * df["risk_mult"]

    flat_daily = trades_to_daily_returns(df.assign(return_pct=df["return_pct"]), frame.index)
    scaled_daily = trades_to_daily_returns(df.assign(return_pct=df["return_pct_scaled"]), frame.index)

    for name, daily in [("flat (1.0x immer)", flat_daily), (f"skaliert ({tercile_mults[0]}x/{tercile_mults[1]}x/{tercile_mults[2]}x)", scaled_daily)]:
        oos_daily = daily[daily.index >= split_ts]
        from strategy.metrics import annualized_sharpe, cagr as cagr_fn, max_drawdown
        print(
            f"    {name:<26} n={len(df):>4} full: sharpe={annualized_sharpe(daily):>6.2f} cagr={cagr_fn(daily):>7.1%} maxdd={max_drawdown(daily):>7.1%}  |  "
            f"OOS: sharpe={annualized_sharpe(oos_daily):>6.2f} cagr={cagr_fn(oos_daily):>7.1%} maxdd={max_drawdown(oos_daily):>7.1%}"
        )


def run_instrument(instrument: str) -> None:
    print(f"\n{'=' * 25} {instrument} {'=' * 25}")
    m15 = fetch_m15(instrument, START, END)
    m5 = fetch_m5(instrument, START, END)
    frame = build_frame(m15, m5, range_bars=1)
    split_ts = pd.Timestamp(SPLIT_DATE, tz=frame.index.tz)

    session_width = frame.groupby("session")["orb_width"].first()
    width_rank = regime.orb_width_percentile(session_width, n=60)

    raw_entries = find_entries(frame, "stop_breakout")
    std_entries = standard_entries(instrument, frame, m15)

    raw_trades = attach_signals(simulate(frame, raw_entries, **RAW_EXIT_CFG), frame, width_rank)
    std_trades = attach_signals(simulate(frame, std_entries, **EXIT_CFG_BY_INSTRUMENT[instrument]), frame, width_rank)

    print("\n--- Part A: Quintil-Scan (avg R-Multiple je Bucket, 0=niedrig, 4=hoch) ---")
    print(" ROH (stop_breakout, keine Filter):")
    for col, label in [("width_rank", "orb_width_percentile"), ("adx_at_entry", "adx_at_entry"), ("rvol_at_entry", "rvol_at_time")]:
        bucket_report(raw_trades, col, label)
    print(" STANDARD-CONFIG (aktuell adoptierte Filter):")
    for col, label in [("width_rank", "orb_width_percentile"), ("adx_at_entry", "adx_at_entry"), ("rvol_at_entry", "rvol_at_time")]:
        bucket_report(std_trades, col, label)

    print("\n--- Part B: Terzil-Risk-Scaling (0.5x/1.0x/1.5x) vs. Flat-Risk, gleicher Trade-Satz ---")
    print(" ROH (stop_breakout, keine Filter):")
    for col in ("width_rank", "adx_at_entry", "rvol_at_entry"):
        print(f"  Signal: {col}")
        scaled_vs_flat(raw_trades, frame, col, split_ts)
    print(" STANDARD-CONFIG (aktuell adoptierte Filter):")
    for col in ("width_rank", "adx_at_entry", "rvol_at_entry"):
        print(f"  Signal: {col}")
        scaled_vs_flat(std_trades, frame, col, split_ts)


def main():
    for instrument in ("SP500", "US30", "NASDAQ"):
        run_instrument(instrument)


if __name__ == "__main__":
    main()
