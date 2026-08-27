"""Stage 5a - Stage 4f found that a naive 50/50 blend of ny_open_orb (SP500)
and the existing orb_strategy/ (SP500) makes things WORSE despite near-zero
correlation (0.045), because orb_strategy's much lower Sharpe (0.44 vs 0.97)
dilutes the stronger strategy's return more than the low correlation
compensates for.

This tests the standard fix: INVERSE-VOLATILITY (risk-parity) weighting
instead of equal weighting - each strategy contributes equal RISK, not
equal capital/equal weight. weight_i = (1/vol_i) / sum(1/vol_j), computed
on the IS half only (2016-07-28 to 2021-07-28) and held fixed for the OOS
half, so the weights themselves aren't fit on the data they're evaluated on
- the same IS/OOS discipline as every other filter in this project.
"""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from combined_strategy.data import fetch_timeframe
from ny_open_orb import filters, regime
from ny_open_orb.data import fetch_sp500_m15, fetch_sp500_m5
from ny_open_orb.engine import build_frame, find_entries, simulate as ny_simulate
from orb_strategy.pipeline import run_orb_pipeline
from strategy.backtest import BacktestConfig, simulate_trades, trades_to_daily_returns
from strategy.metrics import annualized_sharpe, calmar_ratio, cagr as cagr_fn, max_drawdown

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)

START, END = "2016-07-28", "2026-07-28"
SPLIT_DATE = "2021-07-28"


def _to_naive_daily(series: pd.Series) -> pd.Series:
    out = series.copy()
    out.index = out.index.tz_localize(None)
    return out


def report(label: str, daily: pd.Series):
    print(f"{label:>32} sharpe={annualized_sharpe(daily):>6.2f} calmar={calmar_ratio(daily):>6.2f} cagr={cagr_fn(daily):>7.1%} maxdd={max_drawdown(daily):>7.1%} vol={daily.std() * np.sqrt(252):>6.1%}")


def main():
    m15 = fetch_sp500_m15(START, END)
    m5 = fetch_sp500_m5(START, END)
    frame = build_frame(m15, m5, range_bars=1)
    all_entries = find_entries(frame, "stop_breakout")
    long_entries = filters.filter_by_direction(all_entries, 1)
    bias = regime.ema_trend_bias(m15, frame["session"].unique())
    bias_vals = filters.values_at(long_entries, bias)
    ny_entries = filters.filter_by_category(long_entries, bias_vals, (0.0,))
    ny_trades = ny_simulate(frame, ny_entries, stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0)
    ny_daily = _to_naive_daily(trades_to_daily_returns(ny_trades, frame.index))

    df_m15_utc = fetch_timeframe("SP500", "M15", START, END).rename(
        columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    )
    signaled = run_orb_pipeline(df_m15_utc, atr_n=14, atr_mult=1.0, long_only=True, adx_min=25.0, exclude_weekday="Monday")
    cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=2.0, use_vwap_target=False)
    orb_trades = simulate_trades(signaled, cfg)
    orb_daily = _to_naive_daily(trades_to_daily_returns(orb_trades, df_m15_utc.index))

    common_index = ny_daily.index.union(orb_daily.index)
    ny_daily = ny_daily.reindex(common_index, fill_value=0.0)
    orb_daily = orb_daily.reindex(common_index, fill_value=0.0)
    split_ts = pd.Timestamp(SPLIT_DATE)

    is_mask = common_index < split_ts
    oos_mask = common_index >= split_ts

    ny_vol_is = ny_daily[is_mask].std()
    orb_vol_is = orb_daily[is_mask].std()
    inv_vol = np.array([1 / ny_vol_is, 1 / orb_vol_is])
    weights = inv_vol / inv_vol.sum()
    w_ny, w_orb = weights
    print(f"IS-Volatilitaeten: ny_open_orb={ny_vol_is:.4%}/Tag, orb_strategy={orb_vol_is:.4%}/Tag")
    print(f"Inverse-Vol-Gewichte (aus IS, fix gehalten): ny_open_orb={w_ny:.1%}, orb_strategy={w_orb:.1%}\n")

    equal_blend = (ny_daily + orb_daily) / 2.0
    risk_blend = w_ny * ny_daily + w_orb * orb_daily

    print("--- Voller Zeitraum ---")
    report("ny_open_orb allein", ny_daily)
    report("orb_strategy allein", orb_daily)
    report("50/50 Blend (Stage 4f)", equal_blend)
    report(f"Risk-Parity Blend ({w_ny:.0%}/{w_orb:.0%})", risk_blend)

    print("\n--- OOS (>=2021-07-28) ---")
    report("ny_open_orb allein", ny_daily[oos_mask])
    report("orb_strategy allein", orb_daily[oos_mask])
    report("50/50 Blend", equal_blend[oos_mask])
    report(f"Risk-Parity Blend ({w_ny:.0%}/{w_orb:.0%})", risk_blend[oos_mask])


if __name__ == "__main__":
    main()
