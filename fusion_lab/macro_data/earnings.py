"""S&P-Earnings der Megacaps (Makro-Agent v3, 12.11.2026, Nutzerentscheid: Yahoo statt FMP).

Die zehn groessten Werte tragen den Index (Q3 2026: ohne Nvidia/Micron faellt das Gewinnwachstum
laut FactSet von 29 auf 20 %). Je Wert: naechster Termin, Erwartung, letzte Ueberraschung.
Saisonzahlen (Wachstum, Beat-Quote) traegt man woechentlich aus FactSet Earnings Insight in
`fusion_lab/data/macro_agent/earnings_season.json` nach.
"""

from __future__ import annotations

import json

import pandas as pd

from . import store

MEGACAPS = ["NVDA", "MSFT", "AAPL", "AMZN", "GOOGL", "META", "AVGO", "TSLA", "BRK-B", "JPM"]
OUT = store.DATA_DIR / "earnings.json"


def summarize(symbol: str, dates: pd.DataFrame, today: pd.Timestamp) -> dict:
    """dates: Index Termin (tz-aware), Spalten EPS Estimate, Reported EPS, Surprise(%)."""
    d = dates.copy()
    d.index = pd.to_datetime(d.index).tz_localize(None) if d.index.tz is None else d.index.tz_convert(None)
    past = d[d["Reported EPS"].notna()].sort_index()
    future = d[(d.index >= today) & d["Reported EPS"].isna()].sort_index()
    last = past.iloc[-1] if len(past) else None
    return {
        "symbol": symbol,
        "naechster_termin": future.index[0].strftime("%Y-%m-%d") if len(future) else None,
        "erwartung_eps": float(future["EPS Estimate"].iloc[0]) if len(future) and pd.notna(future["EPS Estimate"].iloc[0]) else None,
        "letzter_termin": past.index[-1].strftime("%Y-%m-%d") if last is not None else None,
        "letzte_ueberraschung_pct": round(float(last["Surprise(%)"]), 1) if last is not None and pd.notna(last["Surprise(%)"]) else None,
        "beats_letzte_4": int((past["Surprise(%)"].tail(4) > 0).sum()) if len(past) else None,
    }


def fetch_megacaps(today: pd.Timestamp | None = None) -> list[dict]:
    import yfinance as yf
    today = today if today is not None else pd.Timestamp.today().normalize()
    out = []
    for symbol in MEGACAPS:
        try:
            dates = yf.Ticker(symbol).get_earnings_dates(limit=8)
            if dates is not None and len(dates):
                out.append(summarize(symbol, dates, today))
        except Exception as e:  # ein Wert darf die anderen nicht mitreissen
            out.append({"symbol": symbol, "fehler": f"{type(e).__name__}: {e}"[:120]})
    return out


def run() -> dict:
    rows = fetch_megacaps()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"stand": pd.Timestamp.now().isoformat(timespec="seconds"), "werte": rows},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    return {"werte": len([r for r in rows if "fehler" not in r])}


def load() -> dict:
    return json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
