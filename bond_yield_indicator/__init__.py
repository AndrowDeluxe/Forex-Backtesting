"""Bond-Yield-Spread-Indikator: continuous cross-country rate-spread signal
for FX, built from the monetary-policy-spillover framework in Yildirim
(2024/2025, SSRN 6353258). See knowledge/projects/bond-yield-spread-
indikator.md for the design and knowledge/resources/monetary-policy-
spillover.md for the source-paper distillation.

Layers:
    fred.py      - Layer 1 data: 10y government bond yields (US daily via
                   FRED DGS10, 6 other countries monthly via FRED OECD
                   series - see fred.py docstring for the resolution caveat).
    calendar.py  - Layer 2 data: FOMC + 6 foreign central-bank meeting dates,
                   3-day event-window dummy construction.
    friction.py  - Layer 3: Corwin-Schultz FX bid-ask-spread estimator from
                   existing daily FX OHLC (no new data source needed).
    spread.py    - Layer 1 signal: rolling z-scored yield-change spread.
    beta.py      - Layer 2 signal: rolling country-specific spillover beta.
    indicator.py - composite indicator + FX sign mapping.
"""
