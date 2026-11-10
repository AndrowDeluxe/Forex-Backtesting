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
Futures only, ab 2005). Fehlende Maerkte nachladen: `python -m fusion_lab.filters.cot_flow`
(CAD/CHF/NZD seit 10.11.2026 fuer die Daily-Filter-Matrix).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

COT_FILE = "data_cache/smh/cot_legacy_nr.parquet"
CFTC_LEGACY = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
# Markt -> (CFTC-Code, +1 wenn der Future die Basis gegen USD ist, −1 wenn USD die Basis ist)
CODES = {"EURUSD": ("099741", 1), "GBPUSD": ("096742", 1), "AUDUSD": ("232741", 1),
         "USDJPY": ("097741", -1), "XAUUSD": ("088691", 1), "XAGUSD": ("084691", 1),
         "NZDUSD": ("112741", 1), "USDCAD": ("090741", -1), "USDCHF": ("092741", -1)}


def fetch_legacy(path: str = COT_FILE) -> int:
    """Legacy-Berichte fuer alle CODES ab 2005 laden und mit der Datei zusammenfuehren."""
    import requests
    old = pd.read_parquet(path)
    codes = ",".join(f"'{c}'" for c, _ in CODES.values())
    r = requests.get(CFTC_LEGACY, timeout=120, params={
        "$where": f"cftc_contract_market_code in ({codes}) AND report_date_as_yyyy_mm_dd >= '2005-01-01T00:00:00.000'",
        "$select": ",".join(old.columns), "$limit": 100000})
    r.raise_for_status()
    new = pd.DataFrame(r.json())[list(old.columns)].astype(str)
    out = pd.concat([old.astype(str), new]).drop_duplicates(
        ["cftc_contract_market_code", "report_date_as_yyyy_mm_dd"], keep="first")  # Bestand unveraendert
    out.to_parquet(path, index=False)
    return len(out) - len(old)


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

    def direction(self, market: str, day) -> int:
        """+1 nur long, −1 nur short, 0 keine Aussage (Markt-Richtung, ohne Retail-Bedingung)."""
        dd = self.deltas(market, day) if market in CODES else None
        return 0 if dd is None or dd[0] == 0 else int(np.sign(dd[0]) * CODES[market][1])

    def allows(self, market: str, side: str, day) -> bool:
        dd = self.deltas(market, day)
        if dd is None:
            return False
        want = (1 if side == "long" else -1) * CODES[market][1]
        ok = np.sign(dd[0]) == want
        if self.retail:
            ok = ok and np.sign(dd[1]) != want
        return bool(ok)


if __name__ == "__main__":
    print(f"{fetch_legacy()} neue Berichte in {COT_FILE}")
