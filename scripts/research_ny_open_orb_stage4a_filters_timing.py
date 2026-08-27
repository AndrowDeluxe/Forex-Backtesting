"""Stage 4a - filters and timing, on the Stage 2/3 winner (stop_breakout,
15-min range, ATR-stop 1.0x, target 4R). Restricted to the OOS window
(2021-07-28 to 2026-07-28) since that's the period the edge actually lives
in (Phase 6's walk-forward) - no point re-litigating the flat 2016-2019
period on every single filter cut. Sweeps: trade direction, weekday
exclusion, entry-hour window, entry_cutoff_minutes (how late after the
range forms an entry may still fire), and range_bars (1-4, i.e. 15/30/45/60
min opening range).
"""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from ny_open_orb import filters
from ny_open_orb.data import fetch_m15, fetch_m5
from ny_open_orb.engine import build_frame, find_entries, simulate
from strategy.metrics import summarize

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

OOS_START, END = "2021-07-28", "2026-07-28"
EXIT_CFG = dict(stop_atr_mult=1.0, target_mode="r_multiple", target_r_mult=4.0)


def report(label: str, frame: pd.DataFrame, trades: pd.DataFrame):
    if trades.empty:
        print(f"{label:>45} keine Trades")
        return
    s = summarize(trades, frame.index)
    print(
        f"{label:>45} n={s['n_trades']:>4} sharpe={s['sharpe']:>6.2f} pf={s['profit_factor']:>5.2f} "
        f"win={s['win_rate']:>6.1%} cagr={s['cagr']:>7.1%} maxdd={s['max_drawdown']:>7.1%}"
    )


def main():
    m15 = fetch_m15("SP500", OOS_START, END)
    m5 = fetch_m5("SP500", OOS_START, END)

    print("\n--- range_bars (opening-range width) ---")
    for range_bars in (1, 2, 3, 4):
        frame = build_frame(m15, m5, range_bars=range_bars)
        entries = find_entries(frame, "stop_breakout")
        trades = simulate(frame, entries, **EXIT_CFG)
        report(f"range_bars={range_bars} ({15 * range_bars}min)", frame, trades)

    frame = build_frame(m15, m5, range_bars=1)
    base_entries = find_entries(frame, "stop_breakout")

    print("\n--- Richtung ---")
    for label, direction in [("long+short (baseline)", None), ("long only", 1), ("short only", -1)]:
        entries = base_entries if direction is None else filters.filter_by_direction(base_entries, direction)
        trades = simulate(frame, entries, **EXIT_CFG)
        report(label, frame, trades)

    print("\n--- Wochentag ausgeschlossen ---")
    for label, exclude in [("keiner (baseline)", None), ("Monday", ["Monday"]), ("Tuesday", ["Tuesday"]), ("Wednesday", ["Wednesday"]), ("Thursday", ["Thursday"]), ("Friday", ["Friday"])]:
        entries = base_entries if exclude is None else filters.filter_by_weekday(base_entries, exclude=exclude)
        trades = simulate(frame, entries, **EXIT_CFG)
        report(f"ohne {label}", frame, trades)

    print("\n--- Nur dieser Wochentag ---")
    for day in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday"):
        entries = filters.filter_by_weekday(base_entries, include_only=[day])
        trades = simulate(frame, entries, **EXIT_CFG)
        report(f"nur {day}", frame, trades)

    print("\n--- Entry-Stunden-Fenster (NY-lokal) ---")
    for label, start_h, end_h in [("baseline (ganze Session)", 0, 24), ("09:30-10:30 (1h)", 9.5, 10.5), ("09:30-11:30 (2h)", 9.5, 11.5), ("09:30-12:30 (3h)", 9.5, 12.5), ("11:30-16:00 (spaet)", 11.5, 16.0)]:
        entries = filters.filter_by_entry_hour(base_entries, start_h, end_h)
        trades = simulate(frame, entries, **EXIT_CFG)
        report(label, frame, trades)

    print("\n--- Entry-Cutoff (nur Entries innerhalb X Minuten nach Range-Ende) ---")
    for cutoff in (None, 30, 60, 120, 180):
        entries = find_entries(frame, "stop_breakout", entry_cutoff_minutes=cutoff)
        trades = simulate(frame, entries, **EXIT_CFG)
        report(f"cutoff={cutoff}min", frame, trades)


if __name__ == "__main__":
    main()
