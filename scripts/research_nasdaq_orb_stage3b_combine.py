"""NASDAQ Stage 3b - Stage 3 tested weekday/EMA-bias on the long-only slice
(a design choice inherited from the SP500 script), but Stage 3 also found
long+short (Sharpe 1.18) beats long-only (0.91) outright on NASDAQ - the
opposite of SP500/US30. This checks whether "exclude Wednesday" and/or
"EMA-aligned" actually improve the TRUE NASDAQ baseline (long+short), not
just the long-only slice, before locking in a final config for Phase 6.
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


def oos_report(label, frame, trades, split_ts):
    oos = trades[trades["entry_time"] >= split_ts] if not trades.empty else trades
    if oos.empty:
        print(f"{label:>40} keine Trades (OOS)")
        return
    s = summarize(oos, frame.index[frame.index >= split_ts])
    print(f"{label:>40} n={s['n_trades']:>4} sharpe={s['sharpe']:>6.2f} pf={s['profit_factor']:>5.2f} win={s['win_rate']:>6.1%} cagr={s['cagr']:>7.1%} maxdd={s['max_drawdown']:>7.1%}")


def main():
    m15 = fetch_m15(INSTRUMENT, START, END)
    m5 = fetch_m5(INSTRUMENT, START, END)
    frame = build_frame(m15, m5, range_bars=1)
    split_ts = pd.Timestamp(SPLIT_DATE, tz=frame.index.tz)
    base_entries = find_entries(frame, "stop_breakout")

    bias = regime.ema_trend_bias(m15, frame["session"].unique())
    bias_vals = filters.values_at(base_entries, bias)
    aligned_score = base_entries["direction"].to_numpy() * bias_vals

    no_wed = filters.filter_by_weekday(base_entries, exclude=["Wednesday"])
    no_wed_aligned_score = no_wed["direction"].to_numpy() * filters.values_at(no_wed, bias)

    print("--- Auf long+short-Basis (der eigentliche NASDAQ-Sieger) ---")
    configs = {
        "baseline (long+short)": base_entries,
        "ohne Mittwoch": no_wed,
        "EMA mit Trend": filters.filter_by_series(base_entries, aligned_score, min_value=1),
        "ohne Mittwoch + EMA mit Trend": filters.filter_by_series(no_wed, no_wed_aligned_score, min_value=1),
    }
    for label, entries in configs.items():
        trades = simulate(frame, entries, **EXIT_CFG)
        oos_report(label, frame, trades, split_ts)


if __name__ == "__main__":
    main()
