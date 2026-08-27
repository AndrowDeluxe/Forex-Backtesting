"""NASDAQ calibration Stage 3: confirm range_bars with the ACTUAL best exit
found in Stage 2 (stop=0.6x ATR, target=4R, not the 1.0x/4R placeholder that
grid used), then filters/regime - direction, a PROPERLY IS/OOS-validated
weekday check (ranked on 2016-2021, confirmed on 2021-2026, not just an
OOS-only scan), and EMA-ribbon-bias tested across ALL THREE states (aligned/
neutral/counter-trend) rather than assuming "neutral" transfers from SP500 -
Stage 4e already showed it doesn't.
"""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from ny_open_orb import filters, regime
from ny_open_orb.data import fetch_m15, fetch_m5
from ny_open_orb.engine import build_frame, find_entries, simulate
from strategy.metrics import summarize

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)

START, END = "2016-07-28", "2026-07-28"
SPLIT_DATE = "2021-07-28"
INSTRUMENT = "NASDAQ"
EXIT_CFG = dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0)


def oos_report(label: str, frame: pd.DataFrame, trades: pd.DataFrame, split_ts):
    oos = trades[trades["entry_time"] >= split_ts] if not trades.empty else trades
    if oos.empty:
        print(f"{label:>36} keine Trades (OOS)")
        return None
    s = summarize(oos, frame.index[frame.index >= split_ts])
    print(f"{label:>36} n={s['n_trades']:>4} sharpe={s['sharpe']:>6.2f} pf={s['profit_factor']:>5.2f} win={s['win_rate']:>6.1%} cagr={s['cagr']:>7.1%} maxdd={s['max_drawdown']:>7.1%}")
    return s


def main():
    m15 = fetch_m15(INSTRUMENT, START, END)
    m5 = fetch_m5(INSTRUMENT, START, END)
    split_ts = pd.Timestamp(SPLIT_DATE, tz="America/New_York")

    print("--- range_bars mit korrektem Exit (stop=0.6x, target=4R) ---")
    for range_bars in (1, 2, 3, 4):
        frame_rb = build_frame(m15, m5, range_bars=range_bars)
        entries_rb = find_entries(frame_rb, "stop_breakout")
        trades = simulate(frame_rb, entries_rb, **EXIT_CFG)
        oos_report(f"range_bars={range_bars}", frame_rb, trades, split_ts)

    # Use range_bars=1 going forward unless the above clearly favours another -
    # printed for the user/log to confirm before locking in.
    frame = build_frame(m15, m5, range_bars=1)
    all_entries = find_entries(frame, "stop_breakout")

    print("\n--- Richtung ---")
    for label, direction in [("long+short (baseline)", None), ("long only", 1), ("short only", -1)]:
        entries = all_entries if direction is None else filters.filter_by_direction(all_entries, direction)
        trades = simulate(frame, entries, **EXIT_CFG)
        oos_report(label, frame, trades, split_ts)

    long_entries = filters.filter_by_direction(all_entries, 1)

    print("\n--- Wochentag: IS-Ranking (2016-2021) ---")
    is_pf = {}
    for day in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday"):
        day_entries = filters.filter_by_weekday(long_entries, include_only=[day])
        trades = simulate(frame, day_entries, **EXIT_CFG)
        is_trades = trades[trades["entry_time"] < split_ts] if not trades.empty else trades
        if is_trades.empty:
            print(f"  {day:>10}: keine Trades")
            continue
        s = summarize(is_trades, frame.index[frame.index < split_ts])
        is_pf[day] = s["profit_factor"]
        print(f"  {day:>10}: n={s['n_trades']:>3} sharpe={s['sharpe']:>6.2f} pf={s['profit_factor']:>5.2f}")
    weakest = min(is_pf, key=is_pf.get)
    print(f"  Schwaechster IS-Tag: {weakest} (PF={is_pf[weakest]:.2f}) -> OOS-Check:")
    for label, entries in [("baseline", long_entries), (f"ohne {weakest}", filters.filter_by_weekday(long_entries, exclude=[weakest]))]:
        trades = simulate(frame, entries, **EXIT_CFG)
        oos_report(f"  {label}", frame, trades, split_ts)

    print("\n--- EMA-Ribbon-Bias (alle 3 Zustaende, long-only) ---")
    bias = regime.ema_trend_bias(m15, frame["session"].unique())
    bias_vals = filters.values_at(long_entries, bias)
    aligned_score = long_entries["direction"].to_numpy() * bias_vals
    for label, entries in [
        ("baseline (long-only, kein Filter)", long_entries),
        ("mit Trend (Richtung==Bias)", filters.filter_by_series(long_entries, aligned_score, min_value=1)),
        ("gegen Trend (Richtung!=Bias)", filters.filter_by_series(long_entries, aligned_score, max_value=-1)),
        ("neutral Bias", filters.filter_by_category(long_entries, bias_vals, (0.0,))),
    ]:
        trades = simulate(frame, entries, **EXIT_CFG)
        oos_report(label, frame, trades, split_ts)

    print("\n--- ADR-Regime (long-only, eigener 60-Tage-Median) ---")
    import numpy as np
    adr = regime.average_daily_range(m15, n=20)
    adr_median = adr.rolling(60, min_periods=30).median()
    adr_regime = pd.Series(np.where(adr > adr_median, "high_adr", "low_adr"), index=adr.index, dtype=object)
    adr_regime[adr.isna() | adr_median.isna()] = None
    adr_vals = filters.values_at(long_entries, adr_regime)
    for label, allowed in [("baseline", None), ("high_adr", ("high_adr",)), ("low_adr", ("low_adr",))]:
        entries = long_entries if allowed is None else filters.filter_by_category(long_entries, adr_vals, allowed)
        trades = simulate(frame, entries, **EXIT_CFG)
        oos_report(label, frame, trades, split_ts)


if __name__ == "__main__":
    main()
