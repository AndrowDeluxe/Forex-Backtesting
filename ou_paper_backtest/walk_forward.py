"""Walk-forward validation: instead of a single static in-sample (2010-2017) OU
universe selection held fixed for the whole 2018-2024 out-of-sample period, re-
estimate OU parameters and re-select the universe every year, on a rolling trailing
window, then trade only the following year with that freshly-selected universe.
Stitches the resulting yearly out-of-sample segments into one continuous equity
curve (compounding across year boundaries) and is meant to be compared against the
static-selection curve on identical strategy parameters (SL/TP/breakeven/regime
filter never change here -- only which tickers are in the tradeable universe).

Directly addresses a standing concern flagged since the earliest version of this
project: OU parameters estimated once on 2010-2017 data are up to 14 years stale by
the end of a 2018-2024 backtest, and mean-reversion characteristics of individual
stocks can plausibly drift over that horizon.
"""

import pandas as pd

import config
import ou_model
import portfolio


def _select_universe(ou_table: pd.DataFrame) -> list[str]:
    sel = ou_table[
        (ou_table["theta"] > config.THETA_MIN) & (ou_table["p_value"] < config.PVALUE_MAX)
        & (ou_table["half_life"].between(config.HALFLIFE_MIN, config.HALFLIFE_MAX))
    ]
    return sel.index.tolist()


def run_walk_forward(
    panel: pd.DataFrame,
    benchmark: pd.Series,
    window_years: int = 8,
    trade_start_year: int = 2018,
    trade_end_year: int = 2024,
    initial_equity: float = config.INITIAL_EQUITY,
) -> dict:
    """Rolling `window_years`-long in-sample OU re-selection, one calendar year of
    out-of-sample trading per step, stitched into one continuous curve. Strategy
    parameters fixed at the final locked config (long-only, 3.0-sigma SL, no TP,
    0.25R breakeven, market-wide EMA200 regime filter) -- only the universe changes
    per step, not the entry/exit/sizing rules."""
    regime = (benchmark > benchmark.ewm(span=200).mean()).reindex(panel.index).fillna(False)

    equity_segments: list[pd.Series] = []
    all_trades: list[dict] = []
    step_log: list[dict] = []
    running_equity = initial_equity

    for trade_year in range(trade_start_year, trade_end_year + 1):
        in_sample_end = pd.Timestamp(f"{trade_year - 1}-12-31")
        in_sample_start = pd.Timestamp(f"{trade_year - window_years}-01-01")
        trade_start = f"{trade_year}-01-01"
        trade_end = f"{trade_year}-12-31"

        truncated_panel = panel.loc[:in_sample_end]
        ou_table = ou_model.build_ou_summary_table(
            truncated_panel, str(in_sample_start.date()), str(in_sample_end.date())
        )
        universe = _select_universe(ou_table)

        eq, trades = portfolio.simulate_bracket_portfolio(
            panel, universe, trade_start, trade_end,
            initial_equity=running_equity, risk_pct=0.01, max_hold=10,
            stop_sigma=3.0, rr_ratio=None, be_trigger_r=0.25,
            allowed_directions=(1,), regime_filter=regime,
        )
        if len(eq) == 0:
            continue

        equity_segments.append(eq)
        all_trades.extend(trades)
        step_log.append({
            "trade_year": trade_year,
            "in_sample_start": in_sample_start.date().isoformat(),
            "in_sample_end": in_sample_end.date().isoformat(),
            "n_selected": len(universe),
            "start_equity": running_equity,
            "end_equity": eq.iloc[-1],
            "tickers": ",".join(universe),
        })
        running_equity = eq.iloc[-1]

    combined_equity = pd.concat(equity_segments)
    return {
        "equity": combined_equity,
        "trades": all_trades,
        "step_log": pd.DataFrame(step_log),
    }
