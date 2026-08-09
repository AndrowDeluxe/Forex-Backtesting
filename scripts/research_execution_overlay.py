"""Research script: Execution-Overlay (fast-alpha 5-min streak-reversal as
an entry/exit timing filter for an ATR-breakout session-trend strategy).
Zarattini & Pagani (2026), "Improving Performance with Fast Alphas" --
see app_pages/execution_overlay_writeup.py for the paper writeup.

Two parts:
1. SPY, yfinance 5-minute RTH bars (~60 days only -- yfinance's free-tier
   cap, vs. the paper's SPY 2007-2026 sample). Quick look, not a
   statistically powered replication -- reported as such.
2. EUR/USD, Dukascopy 5-minute bars, 2016-2026 (real multi-year depth, no
   data-length caveat). FX has no session open in the SPY-cash sense, so
   each Dukascopy calendar day is treated as one "session" -- the Sunday
   partial-reopen day is dropped first (same artifact, same fix, as
   gap_fade/engine.py's docstring explains for the daily case).

Run: python scripts/research_execution_overlay.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from execution_overlay.data import (
    fetch_eurusd_5m,
    fetch_eurusd_daily,
    fetch_spy_5m_rth,
    fetch_spy_daily,
    fetch_spy_h1_rth,
)
from execution_overlay.engine import apply_cost, simulate, summarize

SPREAD_SWEEP_BPS = [0.0, 0.5, 1.0, 1.5, 2.0]


def _header(title: str) -> None:
    print("\n" + "=" * 88)
    print(title)
    print("=" * 88)


def _compare(intraday: pd.DataFrame, daily: pd.DataFrame, label: str, spread_bps_headline: float = 1.0):
    # Simulate ONCE per variant (expensive: bar-by-bar over the whole
    # history) -- entries/exits never depend on spread_bps, only pnl_pct
    # does, so every cost scenario below is a cheap re-price via apply_cost,
    # not a re-simulation.
    baseline_raw = simulate(intraday, daily, use_overlay=False, spread_bps=0.0)
    overlay_raw = simulate(intraday, daily, use_overlay=True, spread_bps=0.0)

    baseline = apply_cost(baseline_raw, spread_bps_headline)
    overlay = apply_cost(overlay_raw, spread_bps_headline)

    _header(f"{label} -- Baseline vs. Overlay (spread_bps={spread_bps_headline})")
    print("Baseline:", summarize(baseline))
    print("Overlay: ", summarize(overlay))
    if not baseline.empty:
        print("\nBaseline exit reasons:", baseline["exit_reason"].value_counts().to_dict())
    if not overlay.empty:
        print("Overlay exit reasons: ", overlay["exit_reason"].value_counts().to_dict())

    _header(f"{label} -- Cost sensitivity (re-priced, not re-simulated)")
    for bps in SPREAD_SWEEP_BPS:
        b = summarize(apply_cost(baseline_raw, bps))
        o = summarize(apply_cost(overlay_raw, bps))
        print(f"  spread_bps={bps:>4.1f}  baseline: n={b['n_trades']:>4} total_pnl%={b['total_pnl_pct']:>7}  "
              f"|  overlay: n={o['n_trades']:>4} total_pnl%={o['total_pnl_pct']:>7}")

    return baseline, overlay


def run_spy():
    _header("PART 1: SPY (yfinance, ~60 days) -- quick look, NOT a powered replication")
    intraday = fetch_spy_5m_rth()
    daily = fetch_spy_daily()
    print(f"5m bars: {len(intraday)} ({intraday.index[0]} .. {intraday.index[-1]})")
    print(f"daily bars for ATR: {len(daily)}")
    return _compare(intraday, daily, "SPY")


def run_spy_h1():
    _header("PART 1b: SPY on H1 instead of M5 (yfinance, 730 days -- the only free way to get "
            "more than 60 days) -- a DIFFERENT construction, not a deeper replication of Part 1")
    intraday = fetch_spy_h1_rth()
    daily = fetch_spy_daily(period="3y")
    print(f"H1 bars: {len(intraday)} ({intraday.index[0]} .. {intraday.index[-1]})")
    print(f"daily bars for ATR: {len(daily)}")
    return _compare(intraday, daily, "SPY (H1)")


def run_eurusd():
    _header("PART 2: EUR/USD (Dukascopy, 2016-2026) -- 'session' = 1 calendar day, Sunday sliver dropped")
    intraday = fetch_eurusd_5m("2016-01-01", "2026-08-09")
    daily = fetch_eurusd_daily("2016-01-01", "2026-08-09")
    intraday = intraday[intraday.index.dayofweek != 6]
    daily = daily[daily.index.dayofweek != 6]
    print(f"5m bars: {len(intraday)} ({intraday.index[0]} .. {intraday.index[-1]})")
    print(f"daily bars for ATR: {len(daily)}")
    return _compare(intraday, daily, "EUR/USD")


if __name__ == "__main__":
    pd.set_option("display.width", 120)
    spy_baseline, spy_overlay = run_spy()
    spy_h1_baseline, spy_h1_overlay = run_spy_h1()
    eur_baseline, eur_overlay = run_eurusd()
