"""Stage 4e - does the stop_breakout NY-open ORB edge replicate on NASDAQ
and US30 futures/CFDs (same Dukascopy feed, INSTRUMENT_IDX_AMERICA_E_NQ_100
/ INSTRUMENT_IDX_AMERICA_E_D_J_IND, newly registered in
combined_strategy/data.py for this)? Same walk-forward structure as Phase
6's p6_1 (3 independent ~3-year periods) plus the OOS summary, using the
SP500-derived config as-is (stop=1.0x ATR, target=4R) - NOT re-optimized
per instrument, since the question here is generalization, not a fresh
per-asset fit (a fresh fit-per-asset would need its own Stage 2/3/Phase 6,
out of scope for this pass).
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
pd.set_option("display.max_columns", 20)

START, END = "2016-07-28", "2026-07-28"
SPLIT_DATE = "2021-07-28"
PERIODS = [("2016-2019", "2016-07-28", "2019-07-28"), ("2019-2022", "2019-07-28", "2022-07-28"), ("2022-2026", "2022-07-28", "2026-07-28")]
EXIT_CFG = dict(stop_atr_mult=1.0, target_mode="r_multiple", target_r_mult=4.0)


def report(label: str, index: pd.DatetimeIndex, trades: pd.DataFrame):
    if trades.empty:
        print(f"{label:>16} keine Trades")
        return
    s = summarize(trades, index)
    print(f"{label:>16} n={s['n_trades']:>4} sharpe={s['sharpe']:>6.2f} pf={s['profit_factor']:>5.2f} win={s['win_rate']:>6.1%} cagr={s['cagr']:>7.1%} maxdd={s['max_drawdown']:>7.1%}")


def walkforward_block(frame, trades, tz):
    split_ts = pd.Timestamp(SPLIT_DATE, tz=tz)
    report("full", frame.index, trades)
    report("OOS (>=2021-07-28)", frame.index[frame.index >= split_ts], trades[trades["entry_time"] >= split_ts])
    for label, p_start, p_end in PERIODS:
        p_start_ts, p_end_ts = pd.Timestamp(p_start, tz=tz), pd.Timestamp(p_end, tz=tz)
        sub_trades = trades[(trades["entry_time"] >= p_start_ts) & (trades["entry_time"] < p_end_ts)]
        sub_index = frame.index[(frame.index >= p_start_ts) & (frame.index < p_end_ts)]
        report(label, sub_index, sub_trades)


def run(instrument: str):
    print(f"\n{'=' * 30} {instrument} {'=' * 30}")
    m15 = fetch_m15(instrument, START, END)
    m5 = fetch_m5(instrument, START, END)
    frame = build_frame(m15, m5, range_bars=1)
    all_entries = find_entries(frame, "stop_breakout")

    print(f"-- {instrument}: roh (Stage 2/3 Baseline) --")
    trades = simulate(frame, all_entries, **EXIT_CFG)
    walkforward_block(frame, trades, frame.index.tz)

    print(f"\n-- {instrument}: long-only + EMA-neutral (SP500-abgeleiteter Filter) --")
    long_entries = filters.filter_by_direction(all_entries, 1)
    bias = regime.ema_trend_bias(m15, frame["session"].unique())
    bias_vals = filters.values_at(long_entries, bias)
    filtered_entries = filters.filter_by_category(long_entries, bias_vals, (0.0,))
    trades_filtered = simulate(frame, filtered_entries, **EXIT_CFG)
    walkforward_block(frame, trades_filtered, frame.index.tz)


def main():
    for instrument in ("NASDAQ", "US30"):
        run(instrument)


if __name__ == "__main__":
    main()
