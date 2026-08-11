"""Composite Bond-Yield-Spread indicator, combining Layers 1-3 from
knowledge/projects/bond-yield-spread-indikator.md:

    indicator_t = z_spread_t * w_event_t * beta_rolling_t * friction_gate_t

z_spread    Layer 1 (spread.py): rolling z-score of (ΔUS_yield - Δforeign_yield).
w_event     Layer 2 timing: 1.0 baseline, boosted inside the 3-day CB event
            window (paper finding: within-window changes carry the signal,
            out-of-window changes are "transitory" - Section 2). A soft
            boost rather than a hard gate, so the indicator stays continuous
            for the 6 monthly-resolution countries (see beta.py docstring
            for why a hard FOMC-window-only gate would starve them of data).
beta_rolling Layer 2 sensitivity (beta.py): country-specific spillover
            strength, dispatched daily/monthly per fred.FREQUENCY.
friction_gate Layer 3 (friction.py): 1 - rolling-normalized Corwin-Schultz
            spread, so the indicator is damped when the FX pair's own
            liquidity is unusually poor (paper Section 6.2: higher FX
            friction dampens transmission).

FX sign mapping is NOT from the paper (it only regresses yield-on-yield,
never FX returns) - it is this project's own working hypothesis via the
textbook rate-differential/UIP channel: US yields rising relative to a
country's yields -> relatively more attractive USD carry -> bullish USD.
`usd_base` from fred.COUNTRIES flips the sign for USDxxx-quoted pairs
(JPY/CAD/CHF) vs xxxUSD-quoted pairs (EUR/GBP/AUD) so that
fx_signal > 0 always means "go long the pair" in every case. This sign
hypothesis is exactly the part flagged in the project note as needing its
own backtest validation, not something inherited from the source paper."""

import pandas as pd

from bond_yield_indicator.beta import rolling_beta
from bond_yield_indicator.calendar import BANK_BY_COUNTRY, event_window_dummy
from bond_yield_indicator.fred import COUNTRIES
from bond_yield_indicator.friction import fetch_fx_friction
from bond_yield_indicator.spread import zscore_spread


def build_indicator(country: str, start: str, end: str, *,
                     z_window: int = 60, event_window_days: int = 1,
                     event_boost: float = 1.0, friction_window: int = 250) -> pd.DataFrame:
    meta = COUNTRIES[country]
    pair = meta["pair"]
    if pair is None:
        raise ValueError(f"{country} is the anchor (US) country, has no FX pair")

    z = zscore_spread(country, start, end, window=z_window)

    bank = BANK_BY_COUNTRY[country]
    is_event = event_window_dummy(bank, z.index, window_days=event_window_days)
    w_event = 1.0 + event_boost * is_event

    beta = rolling_beta(country, start, end).reindex(z.index)

    friction = fetch_fx_friction(pair, start, end).reindex(z.index).ffill()
    roll_min = friction.rolling(friction_window, min_periods=friction_window // 4).min()
    roll_max = friction.rolling(friction_window, min_periods=friction_window // 4).max()
    friction_norm = ((friction - roll_min) / (roll_max - roll_min)).clip(0, 1)
    friction_gate = (1 - friction_norm).fillna(1.0)

    raw = z * w_event * beta * friction_gate
    sign = 1.0 if meta["usd_base"] else -1.0
    fx_signal = sign * raw

    return pd.DataFrame({
        "z_spread": z, "is_event": is_event, "w_event": w_event,
        "beta_rolling": beta, "friction": friction, "friction_gate": friction_gate,
        "indicator": raw, "fx_signal": fx_signal,
    })
