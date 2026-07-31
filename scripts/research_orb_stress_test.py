""""Auf Herz und Nieren" pass on the ORB long-only + ADX>=25 strategy
(Nasdaq primary, SP500 secondary) before trusting it further:

1. Parameter sensitivity - vary atr_mult, stop_atr_mult, adx_min one at a
   time around the chosen defaults (1.0 / 2.0 / 25.0), on the honest
   Out-of-Sample slice (2021-2026, the same split used in
   research_orb_robustness.py) - a real edge shouldn't only exist at one
   exact parameter combination.
2. Monte Carlo bootstrap - resample the OOS trade sequence with
   replacement (order and clustering effects removed) to see the RANGE of
   plausible outcomes, not just the one historical path.
3. Capital growth demo - fixed-fractional position sizing (risk_pct of
   current equity per trade, sized off stop_atr_mult x ATR-at-entry, the
   same convention the live OU-Modell bot uses), compounded over the
   actual historical OOS trade sequence, so "how capital could grow" is
   grounded in the same honest OOS sample as everything else here, not
   the friendlier in-sample half.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from combined_strategy.data import fetch_timeframe
from orb_strategy.pipeline import run_orb_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import max_drawdown, summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-07-28", "2026-07-28"
SPLIT = "2021-07-28"
RNG = np.random.default_rng(42)


def _lower_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})


def _oos_trades(df: pd.DataFrame, atr_mult: float, stop_atr_mult: float, adx_min: float | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    signaled = run_orb_pipeline(df, atr_n=14, atr_mult=atr_mult, long_only=True, adx_min=adx_min)
    cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=stop_atr_mult, use_vwap_target=False)
    trades = simulate_trades(signaled, cfg)
    split_ts = pd.Timestamp(SPLIT, tz=signaled.index.tz)
    oos_signaled = signaled[signaled.index >= split_ts]
    oos_trades = trades[trades["entry_time"] >= split_ts] if not trades.empty else trades
    return oos_signaled, oos_trades


def sensitivity_sweep(df: pd.DataFrame, name: str):
    print(f"\n{'=' * 15} {name}: Parameter-Sensitivitaet (Out-of-Sample 2021-2026) {'=' * 15}")

    print("\n-- atr_mult (Schwellen-Distanz), stop_atr_mult=2.0, adx_min=25 fest --")
    for atr_mult in [0.5, 0.75, 1.0, 1.25, 1.5]:
        oos_df, oos_trades = _oos_trades(df, atr_mult, 2.0, 25.0)
        s = summarize(oos_trades, oos_df.index)
        print(f"  atr_mult={atr_mult}: n={s['n_trades']}, sharpe={s['sharpe']:.2f}, pf={s['profit_factor']:.2f}, win_rate={s['win_rate']:.1%}")

    print("\n-- stop_atr_mult, atr_mult=1.0, adx_min=25 fest --")
    for stop_mult in [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]:
        oos_df, oos_trades = _oos_trades(df, 1.0, stop_mult, 25.0)
        s = summarize(oos_trades, oos_df.index)
        print(f"  stop_atr_mult={stop_mult}: n={s['n_trades']}, sharpe={s['sharpe']:.2f}, pf={s['profit_factor']:.2f}, win_rate={s['win_rate']:.1%}")

    print("\n-- adx_min, atr_mult=1.0, stop_atr_mult=2.0 fest --")
    for adx_min in [None, 15.0, 20.0, 25.0, 30.0, 35.0]:
        oos_df, oos_trades = _oos_trades(df, 1.0, 2.0, adx_min)
        s = summarize(oos_trades, oos_df.index)
        label = "aus" if adx_min is None else str(adx_min)
        print(f"  adx_min={label}: n={s['n_trades']}, sharpe={s['sharpe']:.2f}, pf={s['profit_factor']:.2f}, win_rate={s['win_rate']:.1%}")


def monte_carlo_bootstrap(oos_trades: pd.DataFrame, name: str, n_sims: int = 5000, risk_pct: float = 0.01, start_capital: float = 10_000.0):
    print(f"\n{'=' * 15} {name}: Monte-Carlo-Bootstrap (Out-of-Sample, {n_sims} Resamples) {'=' * 15}")
    if oos_trades.empty:
        print("  Keine Trades.")
        return

    returns = oos_trades["return_pct"].to_numpy()
    stop_frac = (2.0 * oos_trades["atr_at_entry"] / oos_trades["entry_price"]).to_numpy()  # stop_atr_mult=2.0 baked in
    n = len(returns)

    final_equities, max_dds = [], []
    for _ in range(n_sims):
        idx = RNG.integers(0, n, size=n)
        equity = start_capital
        curve = [equity]
        for r, sf in zip(returns[idx], stop_frac[idx]):
            position_value = (equity * risk_pct) / sf
            equity += position_value * r
            curve.append(equity)
        final_equities.append(equity)
        curve_arr = np.array(curve)
        running_max = np.maximum.accumulate(curve_arr)
        max_dds.append(((curve_arr - running_max) / running_max).min())

    final_equities = np.array(final_equities)
    max_dds = np.array(max_dds)
    pcts = [5, 25, 50, 75, 95]
    print(f"  Startkapital: {start_capital:,.0f}, Risiko/Trade: {risk_pct:.1%}, {n} Trades/Simulation")
    print("  Endkapital-Perzentile:")
    for p in pcts:
        print(f"    p{p}: {np.percentile(final_equities, p):,.0f}")
    print(f"  Anteil Simulationen mit Endkapital < Startkapital: {(final_equities < start_capital).mean():.1%}")
    print("  Max-Drawdown-Perzentile:")
    for p in pcts:
        print(f"    p{p}: {np.percentile(max_dds, p):.1%}")


def capital_growth_demo(oos_trades: pd.DataFrame, name: str, risk_pct: float = 0.01, start_capital: float = 10_000.0):
    print(f"\n{'=' * 15} {name}: Kapital-Demo (tatsaechliche Out-of-Sample-Reihenfolge) {'=' * 15}")
    if oos_trades.empty:
        print("  Keine Trades.")
        return

    t = oos_trades.sort_values("entry_time")
    equity = start_capital
    rows = []
    for _, row in t.iterrows():
        stop_frac = 2.0 * row["atr_at_entry"] / row["entry_price"]
        position_value = (equity * risk_pct) / stop_frac
        pnl = position_value * row["return_pct"]
        equity += pnl
        rows.append({"entry_time": row["entry_time"], "pnl": pnl, "equity": equity})

    curve = pd.DataFrame(rows).set_index("entry_time")
    daily_equity = curve["equity"].resample("YE").last()
    print(f"  Start: {start_capital:,.0f} ({t['entry_time'].min().date()})")
    print(f"  Ende:  {equity:,.0f} ({t['entry_time'].max().date()}), {len(t)} Trades")
    n_years = (t["entry_time"].max() - t["entry_time"].min()).days / 365.25
    cagr = (equity / start_capital) ** (1 / n_years) - 1 if n_years > 0 else float("nan")
    print(f"  CAGR: {cagr:.1%} ueber {n_years:.1f} Jahre")
    running_max = curve["equity"].cummax()
    dd = (curve["equity"] - running_max) / running_max
    print(f"  Max Drawdown (in Euro-Equity-Kurve): {dd.min():.1%}")
    print("\n  Equity zum Jahresende:")
    print(daily_equity.apply(lambda v: f"{v:,.0f}"))


def main():
    print("Loading NASDAQ M15...")
    nasdaq = _lower_ohlcv(fetch_timeframe("NASDAQ", "M15", START, END))
    sensitivity_sweep(nasdaq, "NASDAQ")
    _, nasdaq_oos_trades = _oos_trades(nasdaq, 1.0, 2.0, 25.0)
    monte_carlo_bootstrap(nasdaq_oos_trades, "NASDAQ")
    capital_growth_demo(nasdaq_oos_trades, "NASDAQ")

    print("\n\nLoading SP500 M15...")
    sp500 = _lower_ohlcv(fetch_timeframe("SP500", "M15", START, END))
    sensitivity_sweep(sp500, "SP500")
    _, sp500_oos_trades = _oos_trades(sp500, 1.0, 2.0, 25.0)
    monte_carlo_bootstrap(sp500_oos_trades, "SP500")
    capital_growth_demo(sp500_oos_trades, "SP500")


if __name__ == "__main__":
    main()
