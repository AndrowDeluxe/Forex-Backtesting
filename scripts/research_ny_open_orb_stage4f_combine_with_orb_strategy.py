"""Stage 4f - can the new NY-open ORB (stop_breakout, long-only, EMA-neutral)
and the EXISTING orb_strategy/ (daily-ATR-threshold, long-only + ADX>=25 +
exclude Monday) be usefully combined on SP500? Both are long-only breakout-
continuation systems on the same instrument, so the first question is
correlation - if they mostly trade the same days in the same direction,
"combining" them barely diversifies anything; if they're substantially
uncorrelated (different trigger mechanics: daily-open-ATR-threshold vs.
first-15-min-range), a blend could genuinely smooth the equity curve.

Uses strategy/backtest.py::trades_to_daily_returns (unmodified, both
strategies' trade tables already have the right entry_time/exit_time/
return_pct columns) to get comparable daily-return series, then reports
correlation and a simple equal-risk-weighted blend (average of the two
daily-return series, not a capital-weighted sum - matches how
research_gold_smc_phase6_robustness.py's simulate_combined_account treats
independent sub-strategies as parallel books, not one shared position).
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
from strategy.metrics import annualized_sharpe, calmar_ratio, max_drawdown, cagr as cagr_fn


def _to_naive_daily(series: pd.Series) -> pd.Series:
    """Both strategies define their trading day in different timezones
    (ny_open_orb: America/New_York, orb_strategy production: raw UTC from
    combined_strategy.data - unmodified here on purpose, to stay faithful to
    how it's actually run in app_pages/orb_strategy.py). Stripping tz after
    normalizing lets the two daily-return series be combined by calendar
    date without a spurious tz mismatch."""
    out = series.copy()
    out.index = out.index.tz_localize(None)
    return out

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)

START, END = "2016-07-28", "2026-07-28"
SPLIT_DATE = "2021-07-28"


def report_series(label: str, daily: pd.Series):
    print(f"{label:>28} sharpe={annualized_sharpe(daily):>6.2f} calmar={calmar_ratio(daily):>6.2f} cagr={cagr_fn(daily):>7.1%} maxdd={max_drawdown(daily):>7.1%}")


def main():
    m15 = fetch_sp500_m15(START, END)
    m5 = fetch_sp500_m5(START, END)

    # New strategy: stop_breakout, long-only, EMA-neutral (Stage 4b2's config)
    frame = build_frame(m15, m5, range_bars=1)
    all_entries = find_entries(frame, "stop_breakout")
    long_entries = filters.filter_by_direction(all_entries, 1)
    bias = regime.ema_trend_bias(m15, frame["session"].unique())
    bias_vals = filters.values_at(long_entries, bias)
    ny_entries = filters.filter_by_category(long_entries, bias_vals, (0.0,))
    ny_trades = ny_simulate(frame, ny_entries, stop_atr_mult=1.0, target_mode="r_multiple", target_r_mult=4.0)
    ny_daily = trades_to_daily_returns(ny_trades, frame.index)

    # Existing strategy: orb_strategy/pipeline.py, confirmed SP500 config -
    # fetched via the SAME (UTC, un-tz-converted) path app_pages/orb_strategy.py
    # actually uses in production, not ny_open_orb's NY-local convention.
    df_m15_utc = fetch_timeframe("SP500", "M15", START, END).rename(
        columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    )
    signaled = run_orb_pipeline(df_m15_utc, atr_n=14, atr_mult=1.0, long_only=True, adx_min=25.0, exclude_weekday="Monday")
    cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=2.0, use_vwap_target=False)
    orb_trades = simulate_trades(signaled, cfg)
    orb_daily = trades_to_daily_returns(orb_trades, df_m15_utc.index)

    ny_daily = _to_naive_daily(ny_daily)
    orb_daily = _to_naive_daily(orb_daily)
    common_index = ny_daily.index.union(orb_daily.index)
    ny_daily = ny_daily.reindex(common_index, fill_value=0.0)
    orb_daily = orb_daily.reindex(common_index, fill_value=0.0)

    print("--- Einzeln (voller Zeitraum) ---")
    report_series("ny_open_orb (neu)", ny_daily)
    report_series("orb_strategy (bestehend)", orb_daily)

    trading_days_ny = ny_daily[ny_daily != 0].index
    trading_days_orb = orb_daily[orb_daily != 0].index
    overlap = trading_days_ny.intersection(trading_days_orb)
    print(f"\nHandelstage neu: {len(trading_days_ny)}, bestehend: {len(trading_days_orb)}, "
          f"UEBERLAPPUNG (beide aktiv am selben Tag): {len(overlap)} "
          f"({len(overlap) / max(len(trading_days_ny), 1):.1%} der neuen Tage)")
    corr = ny_daily.corr(orb_daily)
    print(f"Korrelation der taeglichen Renditen (voller Zeitraum): {corr:.3f}")

    print("\n--- Kombiniert (gleichgewichtetes Mittel der beiden Tagesrenditen) ---")
    combined = (ny_daily + orb_daily) / 2.0
    report_series("50/50 Blend", combined)

    print("\n--- OOS (>=2021-07-28) ---")
    split_ts = pd.Timestamp(SPLIT_DATE, tz=common_index.tz)
    oos_mask = common_index >= split_ts
    report_series("ny_open_orb OOS", ny_daily[oos_mask])
    report_series("orb_strategy OOS", orb_daily[oos_mask])
    report_series("50/50 Blend OOS", combined[oos_mask])
    print(f"Korrelation OOS: {ny_daily[oos_mask].corr(orb_daily[oos_mask]):.3f}")


if __name__ == "__main__":
    main()
