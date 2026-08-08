"""Realistic round-trip transaction costs, taken directly from Seeck (2026)
Sec. 3.1's own stated retail-platform figures -- reused as-is (not
re-derived) so our results are cost-comparable to the paper's own claims,
not just a different, arbitrary cost assumption.
"""

import pandas as pd

PIP_SIZE = {
    "EURUSD": 0.0001,
    "GBPUSD": 0.0001,
    "AUDJPY": 0.01,
    "GBPJPY": 0.01,
    "USDJPY": 0.01,
}

# All-in round-trip cost in pips (Seeck 2026, Sec. 3.1).
ROUND_TRIP_PIPS = {
    "EURUSD": 0.70,
    "GBPUSD": 1.00,
    "AUDJPY": 2.30,
    "GBPJPY": 3.10,
    "USDJPY": 1.47,
}


def apply_costs(trades: pd.DataFrame, pair: str) -> pd.DataFrame:
    """Deduct the round-trip cost (in log-return units, approximated as
    cost_price / entry_price) from `raw_return` -> `net_return`."""
    if pair not in ROUND_TRIP_PIPS:
        raise ValueError(f"no cost figure for {pair!r}, expected one of {list(ROUND_TRIP_PIPS)}")
    trades = trades.copy()
    cost_price = ROUND_TRIP_PIPS[pair] * PIP_SIZE[pair]
    cost_frac = cost_price / trades["entry_price"]
    trades["net_return"] = trades["raw_return"] - cost_frac
    return trades
