"""Stage 7 - real $100k account simulation of the full 3-instrument
portfolio (SP500+US30+NASDAQ, now using Stage 6's standard partial-exit
configs), 2025-01-01 to today, sharing ONE compounding equity pool.

Reuses gold_smc_htf_ltf/concurrent_backtest.py::simulate_combined_account
(heap-based time-ordered settlement, risk-based position sizing off the
CURRENT shared equity) rather than writing a bespoke account simulator -
it already does exactly this for multiple independently-signalled
strategies on one real account (built for the CTNL Edge FK-Challenge
portfolio), just used here with three instruments as the "strategies"
instead of two SMC sub-strategies.

1% risk per trade per instrument (matches this repo's house convention -
the old ORB-MT5-ForwardTest bot's RISK_PCT and mt5_gold_silver_divergenz's
account sim both use 1%). max_concurrent=1 per instrument is a formality,
not a real constraint - each instrument's own signal logic already allows
at most one open position at a time (one entry per session, exits by
session close).
"""

import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from gold_smc_htf_ltf.concurrent_backtest import equity_curve_to_daily_returns, simulate_combined_account

from ny_open_orb import filters, regime
from ny_open_orb.data import fetch_m15, fetch_m5
from ny_open_orb.engine import build_frame, find_entries, simulate
from strategy.metrics import annualized_sharpe, calmar_ratio, cagr as cagr_fn, max_drawdown

warnings.filterwarnings("ignore")
pd.set_option("display.width", 160)

DATA_START, DATA_END = "2016-07-28", pd.Timestamp.today().strftime("%Y-%m-%d")
SIM_START = "2025-01-01"
STARTING_EQUITY = 100_000.0
RISK_PCT = 0.01

EXIT_CFG_BY_INSTRUMENT = {
    "SP500": dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0, partial_exit_r=2.0, partial_exit_fraction=0.5, move_stop_to_be_after_partial=True),
    "US30": dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0, partial_exit_r=2.0, partial_exit_fraction=0.5, move_stop_to_be_after_partial=True),
    "NASDAQ": dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=4.0, partial_exit_r=1.5, partial_exit_fraction=0.5, move_stop_to_be_after_partial=True),
}


def instrument_trades(instrument: str) -> pd.DataFrame:
    m15 = fetch_m15(instrument, DATA_START, DATA_END)
    m5 = fetch_m5(instrument, DATA_START, DATA_END)
    frame = build_frame(m15, m5, range_bars=1)
    all_entries = find_entries(frame, "stop_breakout")

    if instrument == "NASDAQ":
        entries = filters.filter_by_weekday(all_entries, exclude=["Wednesday"])
    else:
        long_entries = filters.filter_by_direction(all_entries, 1)
        bias = regime.ema_trend_bias(m15, frame["session"].unique())
        bias_vals = filters.values_at(long_entries, bias)
        entries = filters.filter_by_category(long_entries, bias_vals, (0.0,))

    trades = simulate(frame, entries, **EXIT_CFG_BY_INSTRUMENT[instrument])
    sim_start_ts = pd.Timestamp(SIM_START, tz=trades["entry_time"].dt.tz) if not trades.empty else None
    return trades[trades["entry_time"] >= sim_start_ts] if sim_start_ts is not None else trades


def main():
    trades_by_instrument = {}
    for instrument in EXIT_CFG_BY_INSTRUMENT:
        t = instrument_trades(instrument)
        trades_by_instrument[instrument] = t
        print(f"{instrument}: {len(t)} Trades seit {SIM_START}")

    risk_pct = {k: RISK_PCT for k in trades_by_instrument}
    max_concurrent = {k: 1 for k in trades_by_instrument}

    sim = simulate_combined_account(
        trades_by_instrument, risk_pct, max_concurrent, starting_equity=STARTING_EQUITY,
    )

    print(f"\n{'=' * 90}")
    print(f"$100k-Konto-Simulation, {SIM_START} bis {DATA_END} (1% Risiko/Trade je Instrument, EINE geteilte Equity)")
    print(f"{'=' * 90}")
    print(f"Start-Kapital:     ${STARTING_EQUITY:>12,.0f}")
    print(f"End-Kapital:       ${sim['final_equity']:>12,.0f}")
    print(f"Total Return:      {sim['final_equity'] / STARTING_EQUITY - 1:>13.1%}")
    print(f"Trades genommen:   {sim['n_taken']:>13d}")
    print(f"Trades uebersprungen: {sim['n_skipped']:>10d}")

    if not sim["trades"].empty:
        idx = pd.date_range(pd.Timestamp(SIM_START), pd.Timestamp(DATA_END), freq="D")
        daily = equity_curve_to_daily_returns(sim["equity_curve"], idx)
        print(f"Sharpe (ann.):     {annualized_sharpe(daily):>13.2f}")
        print(f"Calmar:            {calmar_ratio(daily):>13.2f}")
        print(f"CAGR:              {cagr_fn(daily):>13.1%}")
        print(f"Max Drawdown:      {max_drawdown(daily):>13.1%}")

        print("\nPro Instrument (genommene Trades):")
        for instrument, grp in sim["trades"].groupby("strategy"):
            win_rate = (grp["r_multiple"] > 0).mean()
            total_pnl = grp["pnl"].sum()
            print(f"  {instrument:>8}: n={len(grp):>4} win_rate={win_rate:>6.1%} total_pnl=${total_pnl:>12,.0f} avg_r={grp['r_multiple'].mean():>6.2f}")

        print("\nJaehrliche Aufschluesselung (Equity am Jahresende):")
        eq = sim["equity_curve"].set_index("time")["equity"]
        eq_yearly = eq.resample("YE").last()
        prev = STARTING_EQUITY
        for ts, val in eq_yearly.items():
            print(f"  {ts.year}: ${val:>12,.0f}  ({(val / prev - 1):+7.1%} ggue. Vorjahresende)")
            prev = val


if __name__ == "__main__":
    main()
