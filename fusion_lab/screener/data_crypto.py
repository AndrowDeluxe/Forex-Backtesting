"""Krypto-Daten: Binance-Tageskerzen + Funding (Futures), Fear & Greed (alternative.me). Alles frei, ohne Key."""

from __future__ import annotations

import time

import pandas as pd
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (screener; research)"}
KLINES = "https://api.binance.com/api/v3/klines"
PREMIUM = "https://fapi.binance.com/fapi/v1/premiumIndex"
FNG = "https://api.alternative.me/fng/"


def klines(pair: str, limit: int = 500) -> pd.DataFrame:
    """Tageskerzen (UTC), ohne die laufende, noch offene Tageskerze."""
    for attempt in range(3):
        try:
            r = requests.get(KLINES, params={"symbol": pair, "interval": "1d", "limit": limit}, timeout=30,
                             headers=HEADERS)
            r.raise_for_status()
            break
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    rows = r.json()
    d = pd.DataFrame(rows, columns=["t", "Open", "High", "Low", "Close", "Volume", "ct", "qv", "n", "tb", "tq", "x"])
    d.index = pd.to_datetime(d["t"], unit="ms")
    d = d[["Open", "High", "Low", "Close", "qv"]].astype(float).rename(columns={"qv": "Volume"})  # Volumen in USDT
    now_ms = pd.Timestamp.now(tz="UTC").tz_localize(None)
    return d[d.index + pd.Timedelta(days=1) <= now_ms]


def prices(pairs: list[str]) -> dict[str, pd.DataFrame]:
    out = {}
    for p in pairs:
        try:
            d = klines(p)
        except requests.RequestException:
            continue
        if len(d) >= 30:
            out[p] = d
    return out


def funding() -> dict[str, float]:
    """Letzte Funding-Rate je Perpetual (z. B. BTCUSDT -> 0.0001 = 0,01 % je 8 h)."""
    try:
        r = requests.get(PREMIUM, timeout=30, headers=HEADERS)
        r.raise_for_status()
        return {x["symbol"]: float(x["lastFundingRate"]) for x in r.json() if x.get("lastFundingRate") not in (None, "")}
    except requests.RequestException:
        return {}


def fear_greed() -> dict | None:
    try:
        r = requests.get(FNG, params={"limit": 8}, timeout=30, headers=HEADERS)
        r.raise_for_status()
        data = r.json()["data"]
        return {"wert": int(data[0]["value"]), "einstufung": data[0]["value_classification"],
                "vor_7_tagen": int(data[-1]["value"])}
    except (requests.RequestException, KeyError, ValueError, IndexError):
        return None
