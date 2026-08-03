"""Final "auf Herz und Nieren" stress test on the COMPLETE confirmed ORB
setup: long-only + ADX>=25 + per-asset weekday filter (Nasdaq: no Thursday,
SP500: no Monday). The earlier stress test (research_orb_stress_test.py)
predates the weekday filter - this repeats the same battery (parameter
sensitivity on OOS, Monte Carlo bootstrap, capital-growth demo with real
position sizing) on the actual final configuration, so the numbers we act
on reflect what's really being proposed, not an earlier intermediate step.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from combined_strategy.data import fetch_timeframe
from orb_strategy.pipeline import run_orb_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-07-28", "2026-07-28"
SPLIT = "2021-07-28"
STOP_MULT = 2.0
RNG = np.random.default_rng(42)
ASSET_WEEKDAY = {"NASDAQ": "Thursday", "SP500": "Monday"}


def _lower_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})


def _oos_trades(df, atr_mult, stop_mult, adx_min, exclude_weekday):
    signaled = run_orb_pipeline(df, atr_n=14, atr_mult=atr_mult, long_only=True, adx_min=adx_min, exclude_weekday=exclude_weekday)
    cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=stop_mult, use_vwap_target=False)
    trades = simulate_trades(signaled, cfg)
    split_ts = pd.Timestamp(SPLIT, tz=signaled.index.tz)
    oos_signaled = signaled[signaled.index >= split_ts]
    oos_trades = trades[trades["entry_time"] >= split_ts] if not trades.empty else trades
    return oos_signaled, oos_trades


def sensitivity(name: str, df: pd.DataFrame):
    weekday = ASSET_WEEKDAY[name]
    print(f"\n{'=' * 15} {name}: Parameter-Sensitivitaet MIT Wochentag-Filter (OOS) {'=' * 15}")

    print("\n-- atr_mult, stop=2.0, adx=25 fest --")
    for atr_mult in [0.5, 0.75, 1.0, 1.25, 1.5]:
        oos_df, oos_trades = _oos_trades(df, atr_mult, 2.0, 25.0, weekday)
        s = summarize(oos_trades, oos_df.index)
        print(f"  atr_mult={atr_mult}: n={s['n_trades']}, sharpe={s['sharpe']:.2f}, pf={s['profit_factor']:.2f}")

    print("\n-- adx_min, atr_mult=1.0, stop=2.0 fest --")
    for adx_min in [None, 20.0, 25.0, 30.0]:
        oos_df, oos_trades = _oos_trades(df, 1.0, 2.0, adx_min, weekday)
        s = summarize(oos_trades, oos_df.index)
        label = "aus" if adx_min is None else str(adx_min)
        print(f"  adx_min={label}: n={s['n_trades']}, sharpe={s['sharpe']:.2f}, pf={s['profit_factor']:.2f}")


def monte_carlo(oos_trades: pd.DataFrame, name: str, n_sims=5000, risk_pct=0.01, start_capital=10_000.0):
    print(f"\n{'=' * 15} {name}: Monte-Carlo (OOS, MIT Wochentag-Filter, {n_sims} Resamples) {'=' * 15}")
    if oos_trades.empty:
        print("  Keine Trades.")
        return
    returns = oos_trades["return_pct"].to_numpy()
    stop_frac = (STOP_MULT * oos_trades["atr_at_entry"] / oos_trades["entry_price"]).to_numpy()
    n = len(returns)
    finals, dds = [], []
    for _ in range(n_sims):
        idx = RNG.integers(0, n, size=n)
        equity, curve = start_capital, [start_capital]
        for r, sf in zip(returns[idx], stop_frac[idx]):
            equity += (equity * risk_pct / sf) * r
            curve.append(equity)
        finals.append(equity)
        arr = np.array(curve)
        dds.append(((arr - np.maximum.accumulate(arr)) / np.maximum.accumulate(arr)).min())
    finals, dds = np.array(finals), np.array(dds)
    print(f"  Startkapital {start_capital:,.0f}, {n} Trades/Sim, Risiko {risk_pct:.1%}/Trade")
    for p in [5, 25, 50, 75, 95]:
        print(f"    p{p}: Endkapital={np.percentile(finals, p):,.0f}, MaxDD={np.percentile(dds, p):.1%}")
    print(f"  Anteil Simulationen mit Verlust: {(finals < start_capital).mean():.1%}")


def capital_demo(oos_trades: pd.DataFrame, name: str, risk_pct=0.01, start_capital=10_000.0):
    print(f"\n{'=' * 15} {name}: Kapital-Demo (OOS, tatsaechliche Reihenfolge, MIT Wochentag-Filter) {'=' * 15}")
    if oos_trades.empty:
        print("  Keine Trades.")
        return
    t = oos_trades.sort_values("entry_time")
    equity = start_capital
    rows = []
    for _, row in t.iterrows():
        stop_frac = STOP_MULT * row["atr_at_entry"] / row["entry_price"]
        equity += (equity * risk_pct / stop_frac) * row["return_pct"]
        rows.append({"entry_time": row["entry_time"], "equity": equity})
    curve = pd.DataFrame(rows).set_index("entry_time")
    n_years = (t["entry_time"].max() - t["entry_time"].min()).days / 365.25
    cagr = (equity / start_capital) ** (1 / n_years) - 1 if n_years > 0 else float("nan")
    running_max = curve["equity"].cummax()
    dd = (curve["equity"] - running_max) / running_max
    print(f"  Start: {start_capital:,.0f} -> Ende: {equity:,.0f} ueber {n_years:.1f} Jahre, {len(t)} Trades")
    print(f"  CAGR: {cagr:.1%}, Max Drawdown: {dd.min():.1%}")
    print("  Equity zum Jahresende:")
    print(curve["equity"].resample("YE").last().apply(lambda v: f"{v:,.0f}"))


def main():
    for name, key in [("NASDAQ", "NASDAQ"), ("SP500", "SP500")]:
        print(f"\nLoading {key} M15...")
        df = _lower_ohlcv(fetch_timeframe(key, "M15", START, END))
        sensitivity(name, df)
        _, oos_trades = _oos_trades(df, 1.0, STOP_MULT, 25.0, ASSET_WEEKDAY[name])
        monte_carlo(oos_trades, name)
        capital_demo(oos_trades, name)


if __name__ == "__main__":
    main()
