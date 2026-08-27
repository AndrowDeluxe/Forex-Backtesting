"""Stage 4b - regime/trend filters, directly motivated by Phase 6's finding
that the stop_breakout edge is regime-dependent (flat 2016-2019, strong
2022-2026). Tests whether a volatility or trend regime filter can (a)
explain that split and (b) improve the OOS numbers further.

- ADR (ny_open_orb.regime.average_daily_range): full 2016-2026 history
  available (computed from SP500's own price data, unlike VIX).
- VIX regime: Dukascopy's VIX CFD only has history from 2022-10-04 onward
  (verified directly - NOT the full real-VIX history) - tested on that
  subset only, clearly separate from the full-history ADR results.
- EMA trend bias (strategy/mtf_ema_ribbon.py, reused as-is): trades WITH
  vs. AGAINST vs. ignoring the daily HTF-EMA-ribbon direction.
- Combined ATR x ADR x RVOL grid: joint high/low buckets on all three
  regime dimensions at once, to see whether requiring several to agree
  finds a cleaner regime signal than any one alone.
"""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from ny_open_orb import filters, regime
from ny_open_orb.data import fetch_m15, fetch_m5, fetch_vix_daily
from ny_open_orb.engine import build_frame, find_entries, simulate
from strategy.metrics import summarize

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-07-28", "2026-07-28"
VIX_START = "2022-10-04"
EXIT_CFG = dict(stop_atr_mult=1.0, target_mode="r_multiple", target_r_mult=4.0)


def report(label: str, index: pd.DatetimeIndex, trades: pd.DataFrame):
    if trades.empty:
        print(f"{label:>45} keine Trades")
        return
    s = summarize(trades, index)
    print(
        f"{label:>45} n={s['n_trades']:>4} sharpe={s['sharpe']:>6.2f} pf={s['profit_factor']:>5.2f} "
        f"win={s['win_rate']:>6.1%} cagr={s['cagr']:>7.1%} maxdd={s['max_drawdown']:>7.1%}"
    )


def main():
    m15 = fetch_m15("SP500", START, END)
    m5 = fetch_m5("SP500", START, END)
    frame = build_frame(m15, m5, range_bars=1)
    entries = find_entries(frame, "stop_breakout")

    print("\n--- ADR-Regime (volle Historie, ADR(20) ueber/unter eigenem 60-Tage-Median) ---")
    adr = regime.average_daily_range(m15, n=20)
    adr_median = adr.rolling(60, min_periods=30).median()
    adr_regime = pd.Series(np.where(adr > adr_median, "high_adr", "low_adr"), index=adr.index, dtype=object)
    adr_regime[adr.isna() | adr_median.isna()] = None
    adr_vals = filters.values_at(entries, adr_regime)
    for label, allowed in [("baseline (kein Filter)", None), ("high_adr", ("high_adr",)), ("low_adr", ("low_adr",))]:
        sub_entries = entries if allowed is None else filters.filter_by_category(entries, adr_vals, allowed)
        trades = simulate(frame, sub_entries, **EXIT_CFG)
        report(label, frame.index, trades)

    print("\n--- VIX-Regime (nur ab 2022-10-04 - Dukascopy-Datenstart) ---")
    vix = fetch_vix_daily(VIX_START, END)
    vr = regime.vix_regime(frame["session"].unique(), vix)
    vix_start_ts = pd.Timestamp(VIX_START, tz=frame.index.tz)
    sub_frame_idx = frame.index[frame.index >= vix_start_ts]
    sub_entries_all = entries[entries["entry_time"] >= vix_start_ts]
    vix_vals = filters.values_at(sub_entries_all, vr["vix_regime"])
    for label, allowed in [("baseline (kein Filter, ab 2022-10)", None), ("high_vix", ("high_vix",)), ("low_vix", ("low_vix",))]:
        sub_entries = sub_entries_all if allowed is None else filters.filter_by_category(sub_entries_all, vix_vals, allowed)
        trades = simulate(frame, sub_entries, **EXIT_CFG)
        report(label, sub_frame_idx, trades)

    print("\n--- EMA-Trend-Bias (strategy/mtf_ema_ribbon.py, volle Historie) ---")
    bias = regime.ema_trend_bias(m15, frame["session"].unique())
    bias_vals = filters.values_at(entries, bias)
    aligned_score = entries["direction"].to_numpy() * bias_vals
    for label, mask_fn in [
        ("baseline (kein Filter)", lambda: entries),
        ("mit Trend (Richtung == Bias)", lambda: filters.filter_by_series(entries, aligned_score, min_value=1)),
        ("gegen Trend (Richtung != Bias)", lambda: filters.filter_by_series(entries, aligned_score, max_value=-1)),
        ("neutral Bias (kein Trend)", lambda: filters.filter_by_category(entries, bias_vals, (0.0,))),
    ]:
        trades = simulate(frame, mask_fn(), **EXIT_CFG)
        report(label, frame.index, trades)

    print("\n--- Kombiniert: ATR-Regime x ADR-Regime x RVOL@Time ---")
    # Session-level (not bar-level) ATR regime, from the SAME per-session,
    # no-lookahead ATR build_frame already captured at range-close (frame['atr']) -
    # avoids re-deriving a bar-level M15 series that wouldn't align cleanly
    # with entries['entry_time'] (M5 timestamps, mostly off the M15 grid).
    session_atr = frame.groupby("session")["atr"].first()
    session_atr_median = session_atr.rolling(60, min_periods=30).median()
    atr_regime_series = pd.Series(np.where(session_atr > session_atr_median, "high_atr", "low_atr"), index=session_atr.index, dtype=object)
    atr_regime_series[session_atr.isna() | session_atr_median.isna()] = None
    atr_vals = filters.values_at(entries, atr_regime_series)
    rvol_vals = filters.values_at(entries, frame["rvol_at_time"])

    rvol_bucket_vals = np.where(rvol_vals >= 1.0, "high_rvol", "low_rvol")
    for atr_bucket in ("high_atr", "low_atr"):
        for adr_bucket in ("high_adr", "low_adr"):
            for rvol_bucket in ("high_rvol", "low_rvol"):
                mask = (atr_vals == atr_bucket) & (adr_vals == adr_bucket) & (rvol_bucket_vals == rvol_bucket)
                sub_entries = entries[mask]
                trades = simulate(frame, sub_entries, **EXIT_CFG)
                report(f"ATR={atr_bucket} x ADR={adr_bucket} x RVOL={rvol_bucket}", frame.index, trades)


if __name__ == "__main__":
    main()
