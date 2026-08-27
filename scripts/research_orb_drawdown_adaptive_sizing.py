"""Drawdown-adaptive position sizing for ORB (Nasdaq/SP500, confirmed
baseline: long_only + ADX>=25 + per-asset weekday filter), instead of Kelly
(scripts/research_orb_kelly_sizing.py showed naive Kelly f* blows up the
account even at a quarter-fraction - the payoff ratio flips IS->OOS and the
close-only stop check lets losses run past the nominal 1R).

No existing module in this repo implements a genuinely REACTIVE (equity-
curve-dependent) sizing throttle - app_pages/risk_management.py's OU-Modell
findings are about a FIXED aggregate risk cap chosen via IS/OOS comparison
(and mainly address multi-position correlation risk, which does not apply
to ORB - only one position open at a time by construction, see
strategy/backtest.py's single-position-at-a-time rule). This script builds
and tests the more basic single-position throttle instead: cut risk_pct as
the strategy's OWN simulated equity curve sits deeper in drawdown, restore
it automatically once equity makes a new high (no separate reset state -
the multiplier is a pure function of the CURRENT trailing drawdown, which
by definition hits 0 exactly at a new high).

Same discipline as risk_management.py's 12.5%-cap lesson: an in-sample-
flattering sizing scheme is exactly as overfitting-prone as an entry rule.
Every scenario below is run on BOTH the In-Sample half (2016-2021, where a
scheme might get tuned) and the Out-of-Sample half (2021-2026) and reported
side by side, specifically so a scheme that only works in one half is
visible as such rather than quietly cherry-picked.

Throttle breakpoints (-5%/-10%/-15% trailing drawdown -> 1x/0.5x/0.25x/0.1x
base risk) are round, pre-committed numbers - not reverse-engineered from
either half's own drawdown path."""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from orb_strategy.pipeline import run_orb_pipeline
from strategy.backtest import BacktestConfig, simulate_trades

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-07-28", "2026-07-28"
SPLIT = "2021-07-28"
WEEKDAY_FILTER = {"NASDAQ": "Thursday", "SP500": "Monday"}
STOP_ATR_MULT = 2.0


def _lower_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})


def throttle_multiplier(trailing_dd: float) -> float:
    """trailing_dd <= 0 (0 = at equity high). Pre-committed step function,
    not fit to any specific asset's drawdown distribution."""
    if trailing_dd > -0.05:
        return 1.0
    elif trailing_dd > -0.10:
        return 0.5
    elif trailing_dd > -0.15:
        return 0.25
    else:
        return 0.10


def capital_demo(trades: pd.DataFrame, base_risk_pct: float, throttled: bool, start_capital: float = 10_000.0) -> dict:
    t = trades.sort_values("entry_time")
    if t.empty:
        return {"end_equity": start_capital, "cagr": float("nan"), "max_dd": float("nan"), "calmar": float("nan"), "avg_mult": float("nan")}

    equity = start_capital
    peak = start_capital
    rows = []
    mults = []
    for _, row in t.iterrows():
        trailing_dd = (equity - peak) / peak if peak > 0 else 0.0
        mult = throttle_multiplier(trailing_dd) if throttled else 1.0
        mults.append(mult)

        stop_frac = STOP_ATR_MULT * row["atr_at_entry"] / row["entry_price"]
        position_value = (equity * base_risk_pct * mult) / stop_frac
        pnl = position_value * row["return_pct"]
        equity = max(equity + pnl, 0.0)
        peak = max(peak, equity)
        rows.append({"entry_time": row["entry_time"], "equity": equity})

    curve = pd.DataFrame(rows).set_index("entry_time")["equity"]
    n_years = (t["entry_time"].max() - t["entry_time"].min()).days / 365.25
    cagr = (max(equity, 1e-9) / start_capital) ** (1 / n_years) - 1 if n_years > 0 else float("nan")
    running_max = curve.cummax()
    dd = (curve - running_max) / running_max
    max_dd = dd.min()
    calmar = cagr / abs(max_dd) if max_dd < 0 else float("nan")
    return {"end_equity": equity, "cagr": cagr, "max_dd": max_dd, "calmar": calmar, "avg_mult": sum(mults) / len(mults)}


def print_row(label: str, r: dict):
    print(
        f"  {label:<38} end={r['end_equity']:>12,.0f}  cagr={r['cagr']:>7.1%}  "
        f"max_dd={r['max_dd']:>7.1%}  calmar={r['calmar']:>5.2f}  avg_mult={r['avg_mult']:.2f}"
    )


def run_asset(name: str, df: pd.DataFrame):
    print(f"\n{'=' * 20} {name} {'=' * 20}")
    signaled = run_orb_pipeline(df, atr_n=14, atr_mult=1.0, long_only=True, adx_min=25.0, exclude_weekday=WEEKDAY_FILTER[name])
    cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=STOP_ATR_MULT, use_vwap_target=False)
    trades = simulate_trades(signaled, cfg)
    if trades.empty:
        print("Keine Trades.")
        return

    split_ts = pd.Timestamp(SPLIT, tz=signaled.index.tz)
    is_trades = trades[trades["entry_time"] < split_ts]
    oos_trades = trades[trades["entry_time"] >= split_ts]

    scenarios = [
        ("Flat 1% (Status quo)", 0.01, False),
        ("Throttled 1% Basis", 0.01, True),
        ("Flat 1.5% (ungeschuetzt, hoeheres Risiko)", 0.015, False),
        ("Throttled 1.5% Basis", 0.015, True),
        ("Flat 2% (ungeschuetzt, hoeheres Risiko)", 0.02, False),
        ("Throttled 2% Basis", 0.02, True),
    ]

    print("\nIn-Sample (2016-2021), Start 10.000:")
    for label, risk_pct, throttled in scenarios:
        print_row(label, capital_demo(is_trades, risk_pct, throttled))

    print("\nOut-of-Sample (2021-2026), Start 10.000 (eigene, unabhaengige Kapitalkurve je Halbjahr):")
    for label, risk_pct, throttled in scenarios:
        print_row(label, capital_demo(oos_trades, risk_pct, throttled))


def main():
    print("Loading NASDAQ + SP500 M15 ...")
    run_asset("NASDAQ", _lower_ohlcv(fetch_timeframe("NASDAQ", "M15", START, END)))
    run_asset("SP500", _lower_ohlcv(fetch_timeframe("SP500", "M15", START, END)))


if __name__ == "__main__":
    main()
