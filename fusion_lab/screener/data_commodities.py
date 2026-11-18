"""Rohstoff-Daten: Yahoo-Futures (Front-Monat, ueber data_stocks.prices) + CFTC-COT (Disaggregated, Managed Money).

Alles frei, ohne Key. Front-Monat-Reihen haben Roll-Spruenge; fuer Trend/Zonen auf Tagesbasis reicht das
(gleicher Weg wie scripts/reports/stock_technicals.py), fuer Renditen ueber Monate ist es eine Naeherung.
"""

from __future__ import annotations

import pandas as pd
import requests

from fusion_lab.macro_data.sources import CFTC_API, CFTC_LAG_DAYS
from fusion_lab.screener import config as C, data_stocks

HEADERS = {"User-Agent": "Mozilla/5.0 (screener; research)"}
DISAGG = "72hh-3qpy"


def prices() -> dict[str, pd.DataFrame]:
    """Schluessel (GOLD, KUPFER, ...) + Benchmark -> Tageskerzen."""
    tickers = {v[0]: k for k, v in C.COMMODITIES.items()}
    raw = data_stocks.prices(list(tickers) + [C.COMMODITY_BENCHMARK])
    out = {tickers[t]: d for t, d in raw.items() if t in tickers}
    if C.COMMODITY_BENCHMARK in raw:
        out[C.COMMODITY_BENCHMARK] = raw[C.COMMODITY_BENCHMARK]
    return out


def cot_rows(codes: list[str], weeks: int = C.COT_INDEX_WEEKS + 10) -> pd.DataFrame:
    """Managed-Money-Netto je Code und Berichtsdatum (leer bei Netzfehler)."""
    start = (pd.Timestamp.now() - pd.Timedelta(weeks=weeks)).strftime("%Y-%m-%d")
    quoted = ",".join(f"'{c}'" for c in codes)
    try:
        r = requests.get(f"{CFTC_API}/{DISAGG}.json", timeout=60, headers=HEADERS, params={
            "$where": f"cftc_contract_market_code in ({quoted}) AND report_date_as_yyyy_mm_dd >= '{start}T00:00:00.000'",
            "$select": "cftc_contract_market_code,report_date_as_yyyy_mm_dd,open_interest_all,"
                       "m_money_positions_long_all,m_money_positions_short_all",
            "$limit": 50000})
        r.raise_for_status()
        d = pd.DataFrame(r.json())
    except (requests.RequestException, ValueError):
        return pd.DataFrame()
    if d.empty:
        return d
    d["datum"] = pd.to_datetime(d["report_date_as_yyyy_mm_dd"]).dt.tz_localize(None)
    num = lambda c: pd.to_numeric(d[c], errors="coerce")  # noqa: E731
    d["netto"] = num("m_money_positions_long_all") - num("m_money_positions_short_all")
    d["oi"] = num("open_interest_all")
    return d.sort_values("datum")


def cot_summary(rows: pd.DataFrame, code: str, weeks: int = C.COT_INDEX_WEEKS) -> dict | None:
    """COT-Index (0 = tiefste, 100 = hoechste Netto-Position der letzten `weeks` Berichte), Veraenderung zur
    Vorwoche, Netto in % des Open Interest. None, wenn zu wenig Daten."""
    if rows is None or rows.empty:
        return None
    s = rows[rows["cftc_contract_market_code"] == code].drop_duplicates("datum").tail(weeks)
    if len(s) < 26:
        return None
    net = s["netto"]
    lo, hi = float(net.min()), float(net.max())
    idx = 50.0 if hi == lo else (float(net.iloc[-1]) - lo) / (hi - lo) * 100
    return {"bericht": str(s["datum"].iloc[-1].date()),
            "veroeffentlicht": str((s["datum"].iloc[-1] + pd.Timedelta(days=CFTC_LAG_DAYS)).date()),
            "netto": int(net.iloc[-1]), "veraenderung_1w": int(net.iloc[-1] - net.iloc[-2]),
            "netto_pct_oi": round(float(net.iloc[-1] / s["oi"].iloc[-1] * 100), 1) if s["oi"].iloc[-1] else None,
            "cot_index": round(idx, 1)}


def cot() -> dict[str, dict | None]:
    rows = cot_rows([v[3] for v in C.COMMODITIES.values()])
    return {k: cot_summary(rows, v[3]) for k, v in C.COMMODITIES.items()}
