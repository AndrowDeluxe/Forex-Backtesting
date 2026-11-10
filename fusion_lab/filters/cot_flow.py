"""COT-Fluss je Markt -- wiederverwendbarer Filter-Baustein (Positionierungs-Schicht).

Quelle: Dennis (Elite Coaching), „beim COT zaehlt nur die Veraenderungsrate“
([[smh-dennis-cot-volumen-calls]], Abschnitt 5 und 9). Getestet am 10.11.2026 als Filter fuer die
Daily-Edge C2 (Sperre `dennis_cot_trend`): IS +0,38 R statt +0,21, OOS nur +0,18 statt +0,13,
deshalb allein verworfen. Als Baustein fuer spaetere Kombinationen festgehalten (Nutzerentscheid
10.11.); neue Einsaetze zaehlen als Varianten.

Non-Commercials (Hedgefonds): Netto-Position heute gegen vor `n` Berichten. Aufbau = Richtung.
Optional `retail=True`: Non-Reportables duerfen in derselben Zeit NICHT in dieselbe Richtung
laufen (Dennis 5.6, im Test schaedlich).

Richtung: +1 nur long, −1 nur short, 0 keine Aussage. Nur Berichte, die VOR dem Tag veroeffentlicht
waren (Stichtag Dienstag + 3 Tage). Daten: data_cache/smh/cot_legacy_nr.parquet (CFTC Legacy,
Futures only, ab 2005; Abruf siehe scripts/research_dennis_cot_trend.py).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

COT_FILE = "data_cache/smh/cot_legacy_nr.parquet"
# Markt -> (CFTC-Code, +1 wenn der Future die Basis gegen USD ist, −1 wenn USD die Basis ist)
CODES = {"EURUSD": ("099741", 1), "GBPUSD": ("096742", 1), "AUDUSD": ("232741", 1),
         "USDJPY": ("097741", -1), "XAUUSD": ("088691", 1), "XAGUSD": ("084691", 1)}


def load_cot(path: str = COT_FILE) -> pd.DataFrame:
    d = pd.read_parquet(path)
    d["avail"] = pd.to_datetime(d["report_date_as_yyyy_mm_dd"]) + pd.Timedelta(days=3)
    num = lambda c: pd.to_numeric(d[c])
    d["nc"] = num("noncomm_positions_long_all") - num("noncomm_positions_short_all")
    d["nr"] = num("nonrept_positions_long_all") - num("nonrept_positions_short_all")
    return d.drop_duplicates(["cftc_contract_market_code", "avail"]).sort_values("avail")


class CotFlowFilter:
    def __init__(self, n: int = 4, retail: bool = False, data: pd.DataFrame | None = None):
        self.n, self.retail = n, retail
        self.cot = load_cot() if data is None else data

    def deltas(self, market: str, day) -> tuple[float, float] | None:
        code, _ = CODES[market]
        s = self.cot[(self.cot["cftc_contract_market_code"] == code) & (self.cot["avail"] < pd.Timestamp(day))]
        if len(s) <= self.n:
            return None
        return s["nc"].iloc[-1] - s["nc"].iloc[-1 - self.n], s["nr"].iloc[-1] - s["nr"].iloc[-1 - self.n]

    def allows(self, market: str, side: str, day) -> bool:
        dd = self.deltas(market, day)
        if dd is None:
            return False
        want = (1 if side == "long" else -1) * CODES[market][1]
        ok = np.sign(dd[0]) == want
        if self.retail:
            ok = ok and np.sign(dd[1]) != want
        return bool(ok)
