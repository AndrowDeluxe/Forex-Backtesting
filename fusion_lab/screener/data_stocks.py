"""Aktiendaten ueber yfinance: Tageskurse (Batch) + Fundamentaldaten (Wochen-Cache, Tiefen-Kandidaten taeglich)."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

from fusion_lab.screener import config as C

FUND_CACHE = C.DATA_DIR / "fundamentals.json"
INFO_FIELDS = [
    "shortName", "longName", "sector", "industry", "marketCap", "currentPrice", "forwardPE", "trailingPE",
    "trailingPegRatio", "priceToSalesTrailing12Months", "enterpriseToEbitda", "grossMargins",
    "operatingMargins", "profitMargins", "returnOnEquity", "freeCashflow", "totalRevenue", "revenueGrowth",
    "earningsGrowth", "debtToEquity", "currentRatio", "totalCash", "totalDebt", "targetMeanPrice",
    "targetLowPrice", "targetHighPrice", "recommendationMean", "recommendationKey", "numberOfAnalystOpinions",
    "earningsTimestamp", "shortPercentOfFloat", "dividendYield", "beta",
]


def prices(tickers: list[str], period: str = "2y") -> dict[str, pd.DataFrame]:
    """OHLCV je Ticker (ohne leere/zu kurze Reihen)."""
    raw = yf.download(tickers, period=period, group_by="ticker", auto_adjust=True, threads=True,
                      progress=False)
    out = {}
    for t in tickers:
        try:
            d = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
        except KeyError:
            continue
        d = d[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
        if len(d) >= 60:
            d.index = pd.DatetimeIndex(d.index).tz_localize(None)
            out[t] = d.astype(float)
    return out


def _info(t: str) -> dict:
    for attempt in range(3):
        try:
            i = yf.Ticker(t).info or {}
            return {k: i.get(k) for k in INFO_FIELDS}
        except Exception:  # Yahoo drosselt gelegentlich
            time.sleep(2 * (attempt + 1))
    return {}


def _load_cache() -> dict:
    if FUND_CACHE.exists():
        return json.loads(FUND_CACHE.read_text(encoding="utf-8"))
    return {}


def _save_cache(cache: dict) -> None:
    C.DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = FUND_CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    tmp.replace(FUND_CACHE)


def _archive_fundamentals(snapshot: dict) -> None:
    import gzip
    folder = C.ARCHIVE_DIR / "fundamentals"
    folder.mkdir(parents=True, exist_ok=True)
    day = datetime.now().strftime("%Y-%m-%d")
    with gzip.open(folder / f"{day}.json.gz", "wt", encoding="utf-8") as fh:
        json.dump(snapshot, fh, ensure_ascii=False)


def _stale(entry: dict | None, max_age_days: float) -> bool:
    if not entry or "_ts" not in entry:
        return True
    age = datetime.now(timezone.utc) - datetime.fromisoformat(entry["_ts"])
    return age.total_seconds() > max_age_days * 86400


def fundamentals(tickers: list[str], max_age_days: float = C.FUNDAMENTALS_MAX_AGE_DAYS,
                 workers: int = 8) -> dict[str, dict]:
    """Kennzahlen je Ticker; nur veraltete Eintraege werden neu geladen."""
    cache = _load_cache()
    todo = [t for t in tickers if _stale(cache.get(t), max_age_days)]
    if todo:
        with ThreadPoolExecutor(workers) as ex:
            for t, info in zip(todo, ex.map(_info, todo)):
                if info:
                    cache[t] = {**info, "_ts": datetime.now(timezone.utc).isoformat()}
        _save_cache(cache)
        if len(todo) >= 50:          # Wochen-Aktualisierung: Stand dauerhaft archivieren (Yahoo hat keine Historie)
            _archive_fundamentals({t: cache[t] for t in todo if t in cache})
    return {t: cache.get(t, {}) for t in tickers}


def earnings_date(info: dict) -> str | None:
    ts = info.get("earningsTimestamp")
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


def eps_revisions(t: str) -> dict | None:
    """Analysten-Revisionen der EPS-Schaetzung (laufendes Quartal), nur fuer Tiefen-Kandidaten."""
    try:
        r = yf.Ticker(t).eps_revisions
        if r is None or r.empty or "0q" not in r.index:
            return None
        row = r.loc["0q"]
        return {"hoch_30t": int(row.get("upLast30days", 0) or 0), "runter_30t": int(row.get("downLast30days", 0) or 0)}
    except Exception:
        return None
