"""Better ORB exit logic - the SL itself stays as-is (still needed to size
real broker positions, stop_atr_mult x ATR from the breakout trigger level,
see orb_strategy/pipeline.py), but research_orb_intrabar_stop.py showed it
essentially never fires as a price-level exit (117-118/118 OOS Nasdaq
trades exit via session_end, regardless of stop distance 1.0x-3.0x ATR or
close-vs-intrabar checking) - the SL is the sizing anchor, not the thing
that actually ends a trade. This script asks what SHOULD end a trade
earlier than "ride it to session rollover", per the user's own suggestions:
tighter/different exit TIMES, a trailing stop, or a manual close once a
trade is a fixed R underwater.

Context worth knowing before reading the numbers: the M15 data here trades
close to 24h/day (~89 bars/session, not a ~26-bar NYSE cash session) - the
current "session_end" exit can therefore hold a trade up to ~22h, far
longer than a typical intraday breakout hold. That is the most likely
reason the SL never binds: by the time price would have needed ~22h to
prove the breakout wrong, a session-end exit, not the SL, is almost always
what closes the position first.

Four exit levers, each swept independently on top of the confirmed
baseline (long_only + ADX>=25 + per-asset weekday filter, atr_mult=1.0,
stop_atr_mult=2.0 kept fixed as the sizing SL):

A. max_hold_bars - hard time cap (BacktestConfig field, already built into
   strategy/backtest.py, used elsewhere in this repo - e.g. cls_squeeze).
B. trailing_atr_mult - stop trails N x ATR behind the best confirmed-close
   seen so far (also an existing BacktestConfig field).
C. breakeven_trigger_r - stop jumps to entry once +R is reached (existing
   BacktestConfig field) - re-tested here in combination with A/B, not just
   alone (the original single-filter test already found it weak alone, see
   app_pages/orb_strategy.py step 8).
D. Soft adverse-R close ("manuell bei -0.5R schliessen") - NOT an existing
   BacktestConfig feature (there is no max-adverse-R field), so this is a
   standalone reimplementation of the trade loop: once a trade's confirmed-
   close unrealized R drops to -threshold, close it there instead of
   waiting for the SL or session_end - directly what the user proposed.

Every variant is reported on Out-of-Sample (2021-2026) only (the honest
half) with the same R-multiple/Kelly lens as research_orb_kelly_sizing.py,
so "does this fix the blow-up problem" has a concrete answer, not just a
Sharpe/PF number."""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from combined_strategy.data import fetch_timeframe
from orb_strategy.pipeline import run_orb_pipeline
from research_orb_kelly_sizing import capital_demo, kelly_stats
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

warnings.filterwarnings("ignore")
pd.set_option("display.width", 170)
pd.set_option("display.max_columns", 20)

START, END = "2016-07-28", "2026-07-28"
SPLIT = "2021-07-28"
WEEKDAY_FILTER = {"NASDAQ": "Thursday", "SP500": "Monday"}
STOP_ATR_MULT = 2.0


def _lower_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})


def _r_multiples(trades: pd.DataFrame) -> np.ndarray:
    stop_frac = STOP_ATR_MULT * trades["atr_at_entry"] / trades["entry_price"]
    return (trades["return_pct"] / stop_frac).to_numpy()


def report_row(label: str, oos_trades: pd.DataFrame, oos_index: pd.DatetimeIndex):
    if oos_trades.empty:
        print(f"  {label:<28} keine Trades")
        return
    s = summarize(oos_trades, oos_index)
    k = kelly_stats(_r_multiples(oos_trades))
    half_kelly_end = "-"
    if k["half_kelly_f"] == k["half_kelly_f"] and k["half_kelly_f"] > 0:
        half_kelly_end = f"{capital_demo(oos_trades, k['half_kelly_f'])['end_equity']:,.0f}"
    print(
        f"  {label:<28} n={s['n_trades']:>4}  sharpe={s['sharpe']:>6.2f}  pf={s['profit_factor']:>5.2f}  "
        f"win={s['win_rate']:>6.1%}  avg_win_R={k['avg_win_r']:>6.2f}  avg_loss_R={k['avg_loss_r']:>6.2f}  "
        f"payoff_b={k['payoff_ratio_b']:>5.2f}  kelly_f={k['kelly_f']:>7.1%}  half_kelly_end={half_kelly_end:>10}"
    )


def simulate_soft_adverse_r(df: pd.DataFrame, spread_bps: float, stop_atr_mult: float, max_adverse_r: float) -> pd.DataFrame:
    """Same entry lag / SL(sizing) / session-rollover skeleton as
    strategy/backtest.py::simulate_trades, plus one new exit condition: once
    the confirmed-close R (favor / initial_risk, initial_risk from the SAME
    SL used for sizing) drops to -max_adverse_r or below, close at that
    bar's close (exit_reason='soft_stop') - a proxy for "manually flatten
    once a trade is meaningfully underwater" without waiting for the SL
    (which per research_orb_intrabar_stop.py essentially never fires) or
    session_end."""
    required = {"open", "close", "atr", "prev_high", "prev_low", "signal", "session"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"missing columns {missing}")

    n = len(df)
    open_, close = df["open"].to_numpy(), df["close"].to_numpy()
    atr = df["atr"].to_numpy()
    prev_high, prev_low = df["prev_high"].to_numpy(), df["prev_low"].to_numpy()
    signal = df["signal"].to_numpy()
    session_codes = pd.factorize(df["session"].to_numpy())[0]
    times = df.index

    half_cost_frac = spread_bps / 10_000 / 2
    trades = []
    i = 0
    while i < n - 1:
        sig = signal[i]
        if sig == 0 or np.isnan(atr[i]):
            i += 1
            continue
        direction = int(sig)
        entry_i = i + 1
        entry_session = session_codes[entry_i]

        raw_entry = open_[entry_i]
        cost = raw_entry * half_cost_frac
        entry_price = raw_entry - cost if direction == -1 else raw_entry + cost

        trigger_level = prev_high[entry_i] if direction == -1 else prev_low[entry_i]
        stop_level = trigger_level + stop_atr_mult * atr[entry_i] if direction == -1 else trigger_level - stop_atr_mult * atr[entry_i]
        initial_risk = abs(entry_price - stop_level)

        exit_i, exit_reason = None, None
        j = entry_i
        while j < n:
            if session_codes[j] != entry_session:
                exit_i, exit_reason = max(j - 1, entry_i), "session_end"
                break
            favor = (entry_price - close[j]) if direction == -1 else (close[j] - entry_price)
            r = favor / initial_risk if initial_risk > 0 else 0.0
            if direction == -1 and close[j] > stop_level:
                exit_i, exit_reason = j, "stop"
                break
            if direction == 1 and close[j] < stop_level:
                exit_i, exit_reason = j, "stop"
                break
            if r <= -max_adverse_r:
                exit_i, exit_reason = j, "soft_stop"
                break
            j += 1
        if exit_i is None:
            exit_i, exit_reason = n - 1, "data_end"

        raw_exit = close[exit_i]
        cost = raw_exit * half_cost_frac
        exit_price = raw_exit + cost if direction == -1 else raw_exit - cost
        ret = (entry_price - exit_price) / entry_price if direction == -1 else (exit_price - entry_price) / entry_price

        trades.append({
            "entry_time": times[entry_i], "exit_time": times[exit_i], "direction": direction,
            "entry_price": entry_price, "exit_price": exit_price, "return_pct": ret,
            "exit_reason": exit_reason, "hold_bars": exit_i - entry_i, "atr_at_entry": atr[entry_i],
        })
        i = exit_i + 1
    return pd.DataFrame(trades)


def run_asset(name: str, df: pd.DataFrame):
    print(f"\n{'=' * 25} {name} {'=' * 25}")
    signaled = run_orb_pipeline(df, atr_n=14, atr_mult=1.0, long_only=True, adx_min=25.0, exclude_weekday=WEEKDAY_FILTER[name])
    split_ts = pd.Timestamp(SPLIT, tz=signaled.index.tz)
    oos_signaled = signaled[signaled.index >= split_ts]
    oos_index = oos_signaled.index
    is_signaled = signaled[signaled.index < split_ts]
    is_index = is_signaled.index

    def oos(cfg: BacktestConfig) -> pd.DataFrame:
        trades = simulate_trades(signaled, cfg)
        return trades[trades["entry_time"] >= split_ts] if not trades.empty else trades

    def is_(cfg: BacktestConfig) -> pd.DataFrame:
        trades = simulate_trades(signaled, cfg)
        return trades[trades["entry_time"] < split_ts] if not trades.empty else trades

    print("\n-- A. Baseline vs. Zeit-Cap (max_hold_bars, ~89 M15-Bars = 1 volle Session) --")
    report_row("Baseline (kein Cap)", oos(BacktestConfig(spread_bps=0.3, stop_atr_mult=STOP_ATR_MULT, use_vwap_target=False)), oos_index)
    for bars, label in [(8, "8 Bars (~2h)"), (16, "16 Bars (~4h)"), (26, "26 Bars (~6.5h, NYSE-Session)"), (40, "40 Bars (~10h)"), (60, "60 Bars (~15h)")]:
        report_row(label, oos(BacktestConfig(spread_bps=0.3, stop_atr_mult=STOP_ATR_MULT, use_vwap_target=False, max_hold_bars=bars)), oos_index)

    print("\n-- B. Trailing Stop (trailing_atr_mult x M15-ATR hinter dem besten Kurs) -- OOS --")
    for mult, label in [(None, "Baseline (kein Trailing)"), (0.5, "0.5x ATR"), (1.0, "1.0x ATR"), (1.5, "1.5x ATR"), (2.0, "2.0x ATR (=SL selbst)")]:
        report_row(label, oos(BacktestConfig(spread_bps=0.3, stop_atr_mult=STOP_ATR_MULT, use_vwap_target=False, trailing_atr_mult=mult)), oos_index)
    print("  -- dieselbe Sweep-Reihe, In-Sample (2016-2021) zur Gegenprobe --")
    for mult, label in [(None, "Baseline (kein Trailing)"), (0.5, "0.5x ATR"), (1.0, "1.0x ATR"), (1.5, "1.5x ATR"), (2.0, "2.0x ATR (=SL selbst)")]:
        report_row(label, is_(BacktestConfig(spread_bps=0.3, stop_atr_mult=STOP_ATR_MULT, use_vwap_target=False, trailing_atr_mult=mult)), is_index)

    print("\n-- C. Breakeven-Trigger (Stop auf Einstieg sobald +R erreicht) --")
    for r, label in [(None, "Baseline (kein Breakeven)"), (0.25, "0.25R"), (0.5, "0.5R"), (0.75, "0.75R"), (1.0, "1.0R")]:
        report_row(label, oos(BacktestConfig(spread_bps=0.3, stop_atr_mult=STOP_ATR_MULT, use_vwap_target=False, breakeven_trigger_r=r)), oos_index)

    print("\n-- D. Soft-Close bei -X R (kein Preis-Level, sondern konfirmierte Close-Distanz zum Einstieg) -- OOS --")
    for thr, label in [(2.0, "Baseline-aehnlich (-2.0R, quasi nie)"), (1.0, "-1.0R"), (0.75, "-0.75R"), (0.5, "-0.5R"), (0.3, "-0.3R")]:
        trades = simulate_soft_adverse_r(signaled, spread_bps=0.3, stop_atr_mult=STOP_ATR_MULT, max_adverse_r=thr)
        oos_trades = trades[trades["entry_time"] >= split_ts] if not trades.empty else trades
        report_row(label, oos_trades, oos_index)
    print("  -- dieselbe Sweep-Reihe, In-Sample (2016-2021) zur Gegenprobe --")
    for thr, label in [(2.0, "Baseline-aehnlich (-2.0R, quasi nie)"), (1.0, "-1.0R"), (0.75, "-0.75R"), (0.5, "-0.5R"), (0.3, "-0.3R")]:
        trades = simulate_soft_adverse_r(signaled, spread_bps=0.3, stop_atr_mult=STOP_ATR_MULT, max_adverse_r=thr)
        is_trades = trades[trades["entry_time"] < split_ts] if not trades.empty else trades
        report_row(label, is_trades, is_index)


def main():
    print("Loading NASDAQ + SP500 M15 ...")
    run_asset("NASDAQ", _lower_ohlcv(fetch_timeframe("NASDAQ", "M15", START, END)))
    run_asset("SP500", _lower_ohlcv(fetch_timeframe("SP500", "M15", START, END)))


if __name__ == "__main__":
    main()
