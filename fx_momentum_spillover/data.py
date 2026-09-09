"""Data fetch for the FX-only momentum-spillover rebuild (simplified, own
substitute momentum signal - see signals.py module docstring) of the JPM
"Cross Asset Momentum Spillover" paper (Salopek/Tzotchev, 28.05.2025).
Universe: the 7 FX majors from the paper's asset list (see knowledge/
resources/cross-asset-momentum-spillover.md, Table 4). Reuses
combined_strategy.data (Dukascopy D1, already cached back to 2003-01-01
for 6/7 majors; NZDUSD added to combined_strategy.data.INSTRUMENTS
2026-09-09 for this package).

Data-quality finding (2026-09-09): Dukascopy's NZDUSD D1 series is sparse/
gappy through 2003-2009 (verified: a direct fetch for a window inside one
of the gaps returns 0 rows - not a caching/fetch-wrapper bug, the provider
itself has nothing there), and USDJPY separately has its own gap through
2010-02..2010-09. An inner join across all 7 pairs starting earlier than
that would silently splice data from well before a gap next to data from
well after it, as if they were adjacent trading days - fatal for any
rolling-window momentum signal (a 32-504 day window straddling a gap would
blend two points months/years apart). check_no_gaps() below guards against
ever re-introducing this silently; callers should start their backtest
window no earlier than 2010-11-01 (the first date after which no pair has
any gap >10 calendar days through 2026 - see scripts/research_fx_momentum_
spillover.py START)."""

import pandas as pd

from combined_strategy.data import fetch_timeframe

PAIRS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]


def fetch_fx_universe_closes(start: str, end: str) -> pd.DataFrame:
    """Returns a DataFrame (date x pair) of D1 close prices, INNER-joined
    across all 7 pairs (keeps only dates where every pair has a print -
    FX majors share almost the same OTC trading calendar, so this loses
    very few days while keeping every downstream array perfectly aligned,
    no per-pair NaN-handling needed in the modelling code). Raises if the
    resulting joined index has a calendar-month gap (see module docstring)."""
    closes = {}
    for pair in PAIRS:
        df = fetch_timeframe(pair, "D1", start, end)
        closes[pair] = df["Close"]
    combined = pd.concat(closes, axis=1, join="inner").sort_index()
    combined.columns = PAIRS
    check_no_gaps(combined.index)
    return combined


def check_no_gaps(index: pd.DatetimeIndex, max_gap_days: int = 10) -> None:
    """Raises ValueError if any two consecutive trading days in `index` are
    more than `max_gap_days` calendar days apart - catches a silently
    reintroduced per-pair data hole (see module docstring) before it can
    corrupt a rolling-window momentum signal."""
    if len(index) < 2:
        return
    gaps = index.to_series().diff().dt.days
    bad = gaps[gaps > max_gap_days]
    if not bad.empty:
        first = bad.index[0]
        raise ValueError(
            f"fx_momentum_spillover.data: {len(bad)} gap(s) > {max_gap_days}d in the joined FX "
            f"index, first at {first} ({bad.iloc[0]:.0f}d since the prior trading day) - a rolling "
            f"momentum window would silently straddle this. Narrow the [start, end] range to avoid it."
        )
