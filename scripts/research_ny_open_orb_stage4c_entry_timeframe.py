"""Stage 4c - execution/entry timeframe comparison: M1 vs M5 (Stage 2/3's
default) vs M15. Restricted to the OOS window (2021-07-28 to 2026-07-28) -
M1 over the full 10-year history is a lot of bars for limited added value
here (the question is "does finer/coarser execution granularity change the
picture", not "does the regime-dependence finding change").

fractal_k stays at 2 for every timeframe (a "5-bar fractal") even though
that means a very different real-world time window at M1 (5 min) vs M15
(75 min) - noted as a limitation, not tuned away, since fractal_reversal is
a secondary candidate at best (Stage 3) and isn't the focus of this stage.
"""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from ny_open_orb import filters, regime
from ny_open_orb.data import fetch_m1, fetch_m15, fetch_m5
from ny_open_orb.engine import build_frame, find_entries, simulate
from strategy.metrics import summarize

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2021-07-28", "2026-07-28"
EXIT_CFG = dict(stop_atr_mult=1.0, target_mode="r_multiple", target_r_mult=4.0)


def report(label: str, frame: pd.DataFrame, trades: pd.DataFrame):
    if trades.empty:
        print(f"{label:>20} keine Trades")
        return
    s = summarize(trades, frame.index)
    print(
        f"{label:>20} n={s['n_trades']:>4} sharpe={s['sharpe']:>6.2f} pf={s['profit_factor']:>5.2f} "
        f"win={s['win_rate']:>6.1%} cagr={s['cagr']:>7.1%} maxdd={s['max_drawdown']:>7.1%}"
    )


def main():
    m15 = fetch_m15("SP500", START, END)

    print("--- Ausfuehrungs-Timeframe (Range bleibt immer M15, Stage 2/3 Rohbaseline) ---")
    for label, fetcher, tf_name in [("M1", fetch_m1, "M1"), ("M5", fetch_m5, "M5"), ("M15", fetch_m15, "M15")]:
        m_exec = fetcher("SP500", START, END)
        frame = build_frame(m15, m_exec, range_bars=1)
        entries = find_entries(frame, "stop_breakout")
        trades = simulate(frame, entries, **EXIT_CFG)
        report(f"exec={tf_name} (roh)", frame, trades)

    print("\n--- Ausfuehrungs-Timeframe mit Stage 4b2's Filtern (long-only + EMA-neutral) ---")
    for label, fetcher, tf_name in [("M1", fetch_m1, "M1"), ("M5", fetch_m5, "M5"), ("M15", fetch_m15, "M15")]:
        m_exec = fetcher("SP500", START, END)
        frame = build_frame(m15, m_exec, range_bars=1)
        all_entries = find_entries(frame, "stop_breakout")
        long_entries = filters.filter_by_direction(all_entries, 1)
        bias = regime.ema_trend_bias(m15, frame["session"].unique())
        bias_vals = filters.values_at(long_entries, bias)
        entries = filters.filter_by_category(long_entries, bias_vals, (0.0,))
        trades = simulate(frame, entries, **EXIT_CFG)
        report(f"exec={tf_name} (gefiltert)", frame, trades)


if __name__ == "__main__":
    main()
