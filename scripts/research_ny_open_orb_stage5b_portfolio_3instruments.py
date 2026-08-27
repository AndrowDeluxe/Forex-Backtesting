"""Stage 5b - does combining all three calibrated ny_open_orb configs
(SP500: long-only+EMA-neutral+0.6x/4R; NASDAQ: long+short+exclude-Wednesday
+0.6x/4R; US30: long-only+EMA-neutral+0.6x/4R, confirmed in Stage 4e/the
quick 0.6x check) beat running NASDAQ alone - NASDAQ was the single
strongest, most regime-consistent result of the whole project (Phase 6:
Sharpe 1.30, no regime dependence, zero negative OOS years). Equal-weight
AND inverse-vol (risk-parity, IS-fitted) blends, both full-period and OOS.
"""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from ny_open_orb import filters, regime
from ny_open_orb.data import fetch_m15, fetch_m5
from ny_open_orb.engine import build_frame, find_entries, simulate
from strategy.backtest import trades_to_daily_returns
from strategy.metrics import annualized_sharpe, calmar_ratio, cagr as cagr_fn, max_drawdown

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)

START, END = "2016-07-28", "2026-07-28"
SPLIT_DATE = "2021-07-28"
EXIT_CFG = dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0)


def report(label: str, daily: pd.Series):
    print(f"{label:>28} sharpe={annualized_sharpe(daily):>6.2f} calmar={calmar_ratio(daily):>6.2f} cagr={cagr_fn(daily):>7.1%} maxdd={max_drawdown(daily):>7.1%} vol={daily.std() * np.sqrt(252):>6.1%}")


def sp500_daily() -> pd.Series:
    m15 = fetch_m15("SP500", START, END)
    m5 = fetch_m5("SP500", START, END)
    frame = build_frame(m15, m5, range_bars=1)
    all_e = find_entries(frame, "stop_breakout")
    long_e = filters.filter_by_direction(all_e, 1)
    bias = regime.ema_trend_bias(m15, frame["session"].unique())
    bv = filters.values_at(long_e, bias)
    entries = filters.filter_by_category(long_e, bv, (0.0,))
    trades = simulate(frame, entries, **EXIT_CFG)
    return trades_to_daily_returns(trades, frame.index)


def us30_daily() -> pd.Series:
    m15 = fetch_m15("US30", START, END)
    m5 = fetch_m5("US30", START, END)
    frame = build_frame(m15, m5, range_bars=1)
    all_e = find_entries(frame, "stop_breakout")
    long_e = filters.filter_by_direction(all_e, 1)
    bias = regime.ema_trend_bias(m15, frame["session"].unique())
    bv = filters.values_at(long_e, bias)
    entries = filters.filter_by_category(long_e, bv, (0.0,))
    trades = simulate(frame, entries, **EXIT_CFG)
    return trades_to_daily_returns(trades, frame.index)


def nasdaq_daily() -> pd.Series:
    m15 = fetch_m15("NASDAQ", START, END)
    m5 = fetch_m5("NASDAQ", START, END)
    frame = build_frame(m15, m5, range_bars=1)
    all_e = find_entries(frame, "stop_breakout")
    entries = filters.filter_by_weekday(all_e, exclude=["Wednesday"])
    trades = simulate(frame, entries, **EXIT_CFG)
    return trades_to_daily_returns(trades, frame.index)


def main():
    sp = sp500_daily().pipe(lambda s: s.set_axis(s.index.tz_localize(None)))
    us = us30_daily().pipe(lambda s: s.set_axis(s.index.tz_localize(None)))
    nq = nasdaq_daily().pipe(lambda s: s.set_axis(s.index.tz_localize(None)))

    common = sp.index.union(us.index).union(nq.index)
    sp, us, nq = (s.reindex(common, fill_value=0.0) for s in (sp, us, nq))
    split_ts = pd.Timestamp(SPLIT_DATE)
    is_mask, oos_mask = common < split_ts, common >= split_ts

    print(f"Korrelationsmatrix (volle Historie):\n{pd.DataFrame({'SP500': sp, 'US30': us, 'NASDAQ': nq}).corr().round(3)}\n")

    equal3 = (sp + us + nq) / 3.0
    vols_is = np.array([sp[is_mask].std(), us[is_mask].std(), nq[is_mask].std()])
    inv_vol = 1 / vols_is
    w = inv_vol / inv_vol.sum()
    print(f"Inverse-Vol-Gewichte (aus IS, fix): SP500={w[0]:.1%}, US30={w[1]:.1%}, NASDAQ={w[2]:.1%}\n")
    riskpar3 = w[0] * sp + w[1] * us + w[2] * nq

    print("--- Voller Zeitraum ---")
    report("NASDAQ allein", nq)
    report("SP500 allein", sp)
    report("US30 allein", us)
    report("3er gleichgewichtet", equal3)
    report("3er Risk-Parity", riskpar3)

    print("\n--- OOS (>=2021-07-28) ---")
    report("NASDAQ allein", nq[oos_mask])
    report("SP500 allein", sp[oos_mask])
    report("US30 allein", us[oos_mask])
    report("3er gleichgewichtet", equal3[oos_mask])
    report("3er Risk-Parity", riskpar3[oos_mask])


if __name__ == "__main__":
    main()
