"""Stage 4b's two strongest independent findings - long-only (Stage 4a) and
"EMA-ribbon-bias neutral" (Stage 4b, full history: Sharpe 0.56 -> 1.05,
PF 1.45) - combined, then re-run through Phase 6's exact 3-period
walk-forward to check the thing that actually matters: does this combo fix
the 2016-2019 flatness, or does it just look good pooled while still hiding
the same regime-dependence?
"""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from ny_open_orb import filters, regime
from ny_open_orb.data import fetch_sp500_m15, fetch_sp500_m5
from ny_open_orb.engine import build_frame, find_entries, simulate
from strategy.metrics import summarize

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)

START, END = "2016-07-28", "2026-07-28"
PERIODS = [("2016-2019", "2016-07-28", "2019-07-28"), ("2019-2022", "2019-07-28", "2022-07-28"), ("2022-2026", "2022-07-28", "2026-07-28")]
EXIT_CFG = dict(stop_atr_mult=1.0, target_mode="r_multiple", target_r_mult=4.0)


def report(label: str, index: pd.DatetimeIndex, trades: pd.DataFrame):
    if trades.empty:
        print(f"{label:>14} keine Trades")
        return
    s = summarize(trades, index)
    print(f"{label:>14} n={s['n_trades']:>4} sharpe={s['sharpe']:>6.2f} pf={s['profit_factor']:>5.2f} win={s['win_rate']:>6.1%} cagr={s['cagr']:>7.1%} maxdd={s['max_drawdown']:>7.1%}")


def walkforward(frame, entries, tz):
    for label, p_start, p_end in PERIODS:
        p_start_ts, p_end_ts = pd.Timestamp(p_start, tz=tz), pd.Timestamp(p_end, tz=tz)
        trades = simulate(frame, entries, **EXIT_CFG)
        sub_trades = trades[(trades["entry_time"] >= p_start_ts) & (trades["entry_time"] < p_end_ts)]
        sub_index = frame.index[(frame.index >= p_start_ts) & (frame.index < p_end_ts)]
        report(label, sub_index, sub_trades)
    trades = simulate(frame, entries, **EXIT_CFG)
    report("full", frame.index, trades)


def main():
    m15 = fetch_sp500_m15(START, END)
    m5 = fetch_sp500_m5(START, END)
    frame = build_frame(m15, m5, range_bars=1)
    all_entries = find_entries(frame, "stop_breakout")
    bias = regime.ema_trend_bias(m15, frame["session"].unique())
    bias_vals = filters.values_at(all_entries, bias)

    print("--- Baseline (long+short, kein Regimefilter) ---")
    walkforward(frame, all_entries, frame.index.tz)

    print("\n--- Long-only ---")
    long_entries = filters.filter_by_direction(all_entries, 1)
    walkforward(frame, long_entries, frame.index.tz)

    print("\n--- EMA-neutral only (long+short) ---")
    bias_vals_all = filters.values_at(all_entries, bias)
    neutral_entries = filters.filter_by_category(all_entries, bias_vals_all, (0.0,))
    walkforward(frame, neutral_entries, frame.index.tz)

    print("\n--- Long-only + EMA-neutral (kombiniert) ---")
    long_bias_vals = filters.values_at(long_entries, bias)
    combined_entries = filters.filter_by_category(long_entries, long_bias_vals, (0.0,))
    walkforward(frame, combined_entries, frame.index.tz)


if __name__ == "__main__":
    main()
