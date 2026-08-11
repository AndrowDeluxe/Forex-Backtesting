"""Research script: Bond-Yield-Spread-Indikator backtest (see knowledge/
projects/bond-yield-spread-indikator.md for the design and knowledge/
resources/monetary-policy-spillover.md for the source paper, Yildirim SSRN
6353258).

Composite indicator per country/pair (bond_yield_indicator/indicator.py):
    z-scored US-vs-country 10y yield-change spread (Layer 1, fred.py)
    x event-window weight around that country's CB meetings (Layer 2, paper
      appendix calendars)
    x rolling country-specific spillover beta (Layer 2)
    x FX-liquidity gate from the Corwin-Schultz bid-ask-spread estimator
      (Layer 3, computed on this repo's own cached FX D1 data)

Position each day = sign of YESTERDAY's indicator (no lookahead), held for
one day, applied to close-to-close FX returns. Benchmarked per pair against
buy&hold and a 20-day price-momentum baseline built through the identical
position/no-lookahead machinery, so any edge is attributable to the yield-
spread signal itself and not to the backtest plumbing.

Known scope limits (see bond_yield_indicator/fred.py + beta.py docstrings):
FRED gives daily yields only for the US; the other 6 countries are monthly
OECD mirrors, forward-filled with a disclosed publication lag. The FX-return
sign hypothesis (rate-differential/UIP channel) is this project's own,
not the source paper's - the paper only regresses yield-on-yield."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from bond_yield_indicator.fred import COUNTRIES
from bond_yield_indicator.indicator import build_indicator
from combined_strategy.data import fetch_timeframe
from strategy.metrics import annualized_sharpe, cagr, calmar_ratio, max_drawdown

START, END = "2016-01-01", "2026-08-07"
SPLIT = "2021-01-01"
COUNTRY_PAIRS = [c for c in COUNTRIES if COUNTRIES[c]["pair"] is not None]


def _pair_returns(pair: str) -> pd.Series:
    df = fetch_timeframe(pair, "D1", START, END)
    close = df["Close"]
    close.index = close.index.tz_localize(None) if close.index.tz is not None else close.index
    return close.pct_change().rename("ret")


def _strategy_returns(signal: pd.Series, pair_ret: pd.Series) -> pd.Series:
    """position_t = sign(signal_{t-1}); return_t = position_t * pair_ret_t."""
    position = np.sign(signal).shift(1).reindex(pair_ret.index).fillna(0)
    return (position * pair_ret).rename("strategy_ret")


def _fmt(daily_ret: pd.Series) -> str:
    daily_ret = daily_ret.dropna()
    if daily_ret.empty or daily_ret.std(ddof=1) == 0:
        return "n=0 (flat)"
    win_rate = (daily_ret > 0).mean()
    return (f"Sharpe={annualized_sharpe(daily_ret):+.2f}  CAGR={cagr(daily_ret):+.2%}  "
            f"MaxDD={max_drawdown(daily_ret):.2%}  Calmar={calmar_ratio(daily_ret):+.2f}  "
            f"WinRate={win_rate:.1%}  n_days={len(daily_ret)}")


def main():
    print(f"Bond-Yield-Spread-Indikator backtest, {START} -> {END}, IS/OOS split at {SPLIT}\n")

    indicator_rets, momentum_rets, buyhold_rets = {}, {}, {}

    for country in COUNTRY_PAIRS:
        pair = COUNTRIES[country]["pair"]
        print("=" * 88)
        print(f"{country} / {pair}")
        print("=" * 88)

        ind = build_indicator(country, START, END)
        pair_ret = _pair_returns(pair)

        strat_ret = _strategy_returns(ind["fx_signal"], pair_ret)
        mom_signal = pair_ret.rolling(20).sum()
        mom_ret = _strategy_returns(mom_signal, pair_ret)
        bh_ret = pair_ret.copy()

        indicator_rets[pair] = strat_ret
        momentum_rets[pair] = mom_ret
        buyhold_rets[pair] = bh_ret

        for label, series in [("Indicator ", strat_ret), ("Momentum20", mom_ret), ("Buy&Hold  ", bh_ret)]:
            full = _fmt(series)
            is_part = _fmt(series[series.index < SPLIT])
            oos_part = _fmt(series[series.index >= SPLIT])
            print(f"  {label}  FULL: {full}")
            print(f"  {label}  IS:   {is_part}")
            print(f"  {label}  OOS:  {oos_part}")
        print()

    print("=" * 88)
    print("EQUAL-WEIGHT PORTFOLIO (6 pairs)")
    print("=" * 88)
    for label, rets_by_pair in [("Indicator ", indicator_rets), ("Momentum20", momentum_rets), ("Buy&Hold  ", buyhold_rets)]:
        panel = pd.DataFrame(rets_by_pair)
        port = panel.mean(axis=1, skipna=True)
        full = _fmt(port)
        is_part = _fmt(port[port.index < SPLIT])
        oos_part = _fmt(port[port.index >= SPLIT])
        print(f"  {label}  FULL: {full}")
        print(f"  {label}  IS:   {is_part}")
        print(f"  {label}  OOS:  {oos_part}")


if __name__ == "__main__":
    main()
