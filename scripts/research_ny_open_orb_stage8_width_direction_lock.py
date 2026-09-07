"""Stage 8 - three exit/filter candidates sourced from external literature
(knowledge/resources/opening-range-breakout.md), tested on top of the
CURRENTLY ADOPTED per-instrument standard config (app_pages/ny_open_orb_portfolio.py's
EXIT_CFG_BY_INSTRUMENT/INSTRUMENT_CONFIG: SP500/US30 long-only+EMA-neutral,
NASDAQ long+short+ex-Wednesday, all with the Stage-6 partial-exit standard) -
the practically relevant question is whether stacking a new filter/exit on
the strategy as it is ACTUALLY RUN improves it further, not whether it
works in isolation.

1. ORB-Width-Percentile filter (regime.orb_width_percentile): NQ-futures
   paper found narrow opening ranges (<= IS-33rd-percentile) carry a much
   stronger breakout edge than wide ones. Implemented here as a walk-forward
   ROLLING percentile (n=60 sessions) rather than that paper's single static
   IS threshold - the paper's own OOS section is an explicit warning that a
   static threshold breaks when the width distribution structurally shifts
   (IS mean 53.5pt -> OOS mean 74.7pt).
2. Opening-candle direction lock (range.range_candle_bias): the "Stocks in
   Play" 5-minute-ORB paper only trades breakouts that agree with the
   opening range candle's own body color (bullish candle -> long only, even
   if the low breaks first). Orthogonal to the existing long-only/EMA/
   weekday filters, never tested here before.
3. EOD-close exit instead of a fixed R-multiple target: the "Stocks in Play"
   paper never takes profit early - it holds until the session close (or the
   ATR stop, whichever comes first). engine.simulate() already supports this
   with no code change (target_mode anything other than "r_multiple"/
   "range_multiple" skips the target check entirely, so the position runs
   until stop or session_end) - tested here as target_mode=None, no partial
   exit (a pure stop-or-EOD exit, not a hybrid with the existing 4R/partial
   machinery), same 0.6x ATR stop as the adopted standard so only the target
   philosophy changes.

Also runs DIAGNOSTIC blocks: each candidate alone on RAW stop_breakout
entries (no long-only/EMA/weekday filters at all) - isolates each one's own
effect from the already-adopted filters, and is the closer analogue to how
the source papers tested them.

Reports BOTH full-history and OOS (split 2021-07-28, matching every prior
stage) - small-sample fragility after stacking multiple filters is exactly
the failure mode the source paper's own live-execution section warns about
(N=50 OOS trades before its edge evaporated), so trade counts are printed
prominently, not just Sharpe/PF.
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
from ny_open_orb.range import range_candle_bias
from strategy.metrics import summarize

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)

START, END = "2016-07-28", "2026-07-28"
SPLIT_DATE = "2021-07-28"

# Matches app_pages/ny_open_orb_portfolio.py exactly (the live-adopted standard).
EXIT_CFG_BY_INSTRUMENT = {
    "SP500": dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0, partial_exit_r=2.0, partial_exit_fraction=0.5, move_stop_to_be_after_partial=True),
    "US30": dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0, partial_exit_r=2.0, partial_exit_fraction=0.5, move_stop_to_be_after_partial=True),
    "NASDAQ": dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0, partial_exit_r=1.5, partial_exit_fraction=0.5, move_stop_to_be_after_partial=True),
}
RAW_EXIT_CFG = dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0)  # no partial exit, for the diagnostic block
EOD_EXIT_CFG = dict(stop_atr_mult=0.6, target_mode=None)  # stop-or-session-close, no target/partial - Paper 2's exit philosophy


def report(label: str, frame_index: pd.DatetimeIndex, trades: pd.DataFrame) -> None:
    if trades.empty:
        print(f"{label:>50} keine Trades")
        return
    s = summarize(trades, frame_index)
    print(
        f"{label:>50} n={s['n_trades']:>4} sharpe={s['sharpe']:>6.2f} pf={s['profit_factor']:>5.2f} "
        f"win={s['win_rate']:>6.1%} cagr={s['cagr']:>7.1%} maxdd={s['max_drawdown']:>7.1%}"
    )


def both_windows(label: str, frame: pd.DataFrame, entries: pd.DataFrame, exit_cfg: dict, split_ts: pd.Timestamp) -> None:
    trades = simulate(frame, entries, **exit_cfg)
    report(f"{label} (voll)", frame.index, trades)
    oos_trades = trades[trades["entry_time"] >= split_ts] if not trades.empty else trades
    oos_index = frame.index[frame.index >= split_ts]
    report(f"{label} (OOS)", oos_index, oos_trades)


def standard_entries(instrument: str, frame: pd.DataFrame, m15: pd.DataFrame) -> pd.DataFrame:
    """Exactly app_pages/ny_open_orb_portfolio.py::run_backtest's entry logic."""
    all_entries = find_entries(frame, "stop_breakout")
    if instrument == "NASDAQ":
        return filters.filter_by_weekday(all_entries, exclude=["Wednesday"])
    long_entries = filters.filter_by_direction(all_entries, 1)
    bias = regime.ema_trend_bias(m15, frame["session"].unique())
    bias_vals = filters.values_at(long_entries, bias)
    return filters.filter_by_category(long_entries, bias_vals, (0.0,))


def width_filtered(entries: pd.DataFrame, width_rank: pd.Series, max_rank: float | None = None, min_rank: float | None = None) -> pd.DataFrame:
    vals = filters.values_at(entries, width_rank)
    return filters.filter_by_series(entries, vals, min_value=min_rank, max_value=max_rank)


def direction_locked(entries: pd.DataFrame, bias: pd.Series) -> pd.DataFrame:
    bias_vals = filters.values_at(entries, bias)
    return entries[entries["direction"].to_numpy() == bias_vals]


def run_instrument(instrument: str) -> None:
    print(f"\n{'=' * 25} {instrument} {'=' * 25}")
    m15 = fetch_m15(instrument, START, END)
    m5 = fetch_m5(instrument, START, END)
    frame = build_frame(m15, m5, range_bars=1)
    split_ts = pd.Timestamp(SPLIT_DATE, tz=frame.index.tz)
    exit_cfg = EXIT_CFG_BY_INSTRUMENT[instrument]

    session_width = frame.groupby("session")["orb_width"].first()
    width_rank = regime.orb_width_percentile(session_width, n=60)
    candle_bias = range_candle_bias(m15, range_bars=1)

    entries = standard_entries(instrument, frame, m15)
    print(f"\n--- Baseline: aktuell adoptierte Standard-Config (n_entries vor Exit-Sim={len(entries)}) ---")
    both_windows("baseline (Standard-Config)", frame, entries, exit_cfg, split_ts)

    print("\n--- + ORB-Width-Perzentil-Filter (n=60, gestapelt auf Standard-Config) ---")
    for label, kwargs in [
        ("narrow <= P20", dict(max_rank=0.20)),
        ("narrow <= P33", dict(max_rank=0.33)),
        ("wide >= P67", dict(min_rank=0.67)),
        ("wide >= P80", dict(min_rank=0.80)),
    ]:
        sub = width_filtered(entries, width_rank, **kwargs)
        both_windows(f"width {label}", frame, sub, exit_cfg, split_ts)

    print("\n--- + Erste-Kerze-Richtungssperre (gestapelt auf Standard-Config) ---")
    locked = direction_locked(entries, candle_bias)
    both_windows("direction-lock (agree only)", frame, locked, exit_cfg, split_ts)

    print("\n--- Kombiniert: Width <= P33 UND Richtungssperre ---")
    combined = direction_locked(width_filtered(entries, width_rank, max_rank=0.33), candle_bias)
    both_windows("width<=P33 + direction-lock", frame, combined, exit_cfg, split_ts)

    print("\n--- + EOD-Close-Exit statt festem 4R-Ziel (gestapelt auf Standard-Config-Entries, 0.6x-ATR-Stop unveraendert, kein Teilausstieg) ---")
    both_windows("EOD-exit (Standard-Config-Entries)", frame, entries, EOD_EXIT_CFG, split_ts)
    both_windows("EOD-exit + width<=P33", frame, width_filtered(entries, width_rank, max_rank=0.33), EOD_EXIT_CFG, split_ts)
    both_windows("EOD-exit + direction-lock", frame, locked, EOD_EXIT_CFG, split_ts)

    print("\n--- Diagnose: Width-Filter/Richtungssperre/EOD-Exit auf ROHEN stop_breakout-Entries (keine EMA/Weekday/Long-only-Filter, kein Teilausstieg) ---")
    raw_entries = find_entries(frame, "stop_breakout")
    both_windows("raw baseline", frame, raw_entries, RAW_EXIT_CFG, split_ts)
    for label, kwargs in [("narrow <= P20", dict(max_rank=0.20)), ("narrow <= P33", dict(max_rank=0.33)), ("wide >= P67", dict(min_rank=0.67))]:
        sub = width_filtered(raw_entries, width_rank, **kwargs)
        both_windows(f"raw width {label}", frame, sub, RAW_EXIT_CFG, split_ts)
    raw_locked = direction_locked(raw_entries, candle_bias)
    both_windows("raw direction-lock (agree only)", frame, raw_locked, RAW_EXIT_CFG, split_ts)
    both_windows("raw EOD-exit", frame, raw_entries, EOD_EXIT_CFG, split_ts)


def main():
    for instrument in ("SP500", "US30", "NASDAQ"):
        run_instrument(instrument)


if __name__ == "__main__":
    main()
