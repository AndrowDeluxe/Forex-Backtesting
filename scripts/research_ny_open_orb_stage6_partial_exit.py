"""Stage 6 - partial-exit (scale-out) optimization, on the user's question
"can win rate still be improved". engine.py's simulate() now supports
partial_exit_r/partial_exit_fraction/move_stop_to_be_after_partial (banks a
fraction of the position at an early R-level, the rest keeps running against
the original stop/target unless explicitly moved to breakeven).

Sweeps partial_exit_r x partial_exit_fraction x move_stop_to_be_after_partial
on both confirmed configs (SP500 long-only+EMA-neutral, NASDAQ long+short+
ex-Wednesday), OOS only. Goal: find whether any combination improves win
rate WITHOUT degrading Sharpe/PF below the no-partial baseline - a higher
win rate alone isn't the actual goal (already learned from the target_r_mult
grid in Stage 3/4d: chasing win rate directly made things worse).
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
BASE_EXIT = dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0)


def oos_report(label: str, frame: pd.DataFrame, trades: pd.DataFrame, split_ts) -> None:
    oos = trades[trades["entry_time"] >= split_ts] if not trades.empty else trades
    if oos.empty:
        print(f"{label:>48} keine Trades (OOS)")
        return
    s = summarize(oos, frame.index[frame.index >= split_ts])
    print(
        f"{label:>48} n={s['n_trades']:>4} sharpe={s['sharpe']:>6.2f} pf={s['profit_factor']:>5.2f} "
        f"win={s['win_rate']:>6.1%} avg_r={oos['r_multiple'].mean():>6.2f} cagr={s['cagr']:>7.1%} maxdd={s['max_drawdown']:>7.1%}"
    )


def sp500_entries(frame, m15):
    all_e = find_entries(frame, "stop_breakout")
    long_e = filters.filter_by_direction(all_e, 1)
    bias = regime.ema_trend_bias(m15, frame["session"].unique())
    bv = filters.values_at(long_e, bias)
    return filters.filter_by_category(long_e, bv, (0.0,))


def nasdaq_entries(frame, m15):
    all_e = find_entries(frame, "stop_breakout")
    return filters.filter_by_weekday(all_e, exclude=["Wednesday"])


def run_instrument(instrument: str, entries_fn):
    print(f"\n{'=' * 30} {instrument} {'=' * 30}")
    m15 = fetch_m15(instrument, START, END)
    m5 = fetch_m5(instrument, START, END)
    frame = build_frame(m15, m5, range_bars=1)
    split_ts = pd.Timestamp(SPLIT_DATE, tz=frame.index.tz)
    entries = entries_fn(frame, m15)

    trades_base = simulate(frame, entries, **BASE_EXIT)
    oos_report("baseline (kein Teil-Ausstieg)", frame, trades_base, split_ts)

    print("\n  -- partial_exit_r x partial_exit_fraction (stop bleibt am Original) --")
    for partial_r in (1.0, 1.5, 2.0):
        for frac in (0.25, 0.5, 0.75):
            trades = simulate(frame, entries, partial_exit_r=partial_r, partial_exit_fraction=frac, **BASE_EXIT)
            oos_report(f"partial_r={partial_r} frac={frac}", frame, trades, split_ts)

    print("\n  -- beste partial_exit_r/frac-Kandidaten x move_stop_to_be_after_partial --")
    for partial_r, frac in ((1.0, 0.5), (1.5, 0.5), (1.5, 0.75), (2.0, 0.5)):
        trades = simulate(frame, entries, partial_exit_r=partial_r, partial_exit_fraction=frac, move_stop_to_be_after_partial=True, **BASE_EXIT)
        oos_report(f"partial_r={partial_r} frac={frac} +BE-Rest", frame, trades, split_ts)


def main():
    run_instrument("SP500", sp500_entries)
    run_instrument("NASDAQ", nasdaq_entries)


if __name__ == "__main__":
    main()
