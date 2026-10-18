"""Kosten je Rundturn, in Kurseinheiten (FX) bzw. Anteil (Indizes).

FX: gemessener Spread + Kommission (TTP/IQ, knowledge/resources/
broker-kostenmodell-eurusd.md) plus Slippage, aufgerundet. Bid-Bars
enthalten den Spread nicht, darum wird er hier voll abgezogen.
Indizes: Werte aus dem Baltussen-Test (1,59/1,29 bps) + 1 Tick je Seite.
"""

PIP = {"EURUSD": 1e-4, "GBPUSD": 1e-4, "AUDUSD": 1e-4, "USDJPY": 1e-2,
       "USDCAD": 1e-4, "USDCHF": 1e-4, "NZDUSD": 1e-4, "EURGBP": 1e-4, "EURJPY": 1e-2, "GBPJPY": 1e-2}
RT_PIPS = {"EURUSD": 1.2, "USDJPY": 1.4, "AUDUSD": 1.5, "GBPUSD": 1.6,
           # ANNAHME (16.10.2026, nicht gemessen): typische Raw-Spreads + gleiche
           # Kommission/Slippage wie oben, aufgerundet; Crosses breiter.
           "USDCAD": 1.6, "USDCHF": 1.6, "NZDUSD": 1.8, "EURGBP": 1.6, "EURJPY": 1.8, "GBPJPY": 2.5}
RT_BPS = {"SP500": 2.6, "NASDAQ": 2.3}


def roundtrip_cost(sym: str, price: float, mult: float = 1.0) -> float:
    """Kosten eines Rundturns in Kurseinheiten."""
    if sym in RT_PIPS:
        return RT_PIPS[sym] * PIP[sym] * mult
    return RT_BPS[sym] * 1e-4 * price * mult
