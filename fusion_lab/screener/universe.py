"""Universen: Aktien (S&P 500 + Nasdaq-100, entdupliziert) und Krypto (Top N CoinGecko mit Binance-USDT-Paar)."""

from __future__ import annotations

import pandas as pd
import requests

from fusion_lab.screener import config as C

HEADERS = {"User-Agent": "Mozilla/5.0 (screener; research)"}
COINGECKO = "https://api.coingecko.com/api/v3/coins/markets"
BINANCE_INFO = "https://api.binance.com/api/v3/exchangeInfo"


def yahoo_symbol(sym: str) -> str:
    """Wikipedia-Schreibweise -> Yahoo (BRK.B -> BRK-B)."""
    return sym.strip().upper().replace(".", "-")


def stocks() -> pd.DataFrame:
    """Spalten: ticker, name, sektor, index (sp500/nasdaq100/beide/watchlist). Jeder Ticker genau einmal
    (Memory "OU: Doppel-Universum": Titel in beiden Indizes sonst doppelt gezaehlt)."""
    sp = pd.read_csv(C.SP500_CSV)
    nq = pd.read_csv(C.NASDAQ100_CSV)
    rows = {}
    for _, r in sp.iterrows():
        t = yahoo_symbol(r["Symbol"])
        rows[t] = {"ticker": t, "name": r["Security"], "sektor": r.get("GICS Sector", ""), "index": "sp500"}
    tcol = "Ticker" if "Ticker" in nq.columns else "Symbol"
    ncol = "Company" if "Company" in nq.columns else ("Security" if "Security" in nq.columns else tcol)
    scol = next((c for c in nq.columns if c == "GICS Sector" or c.startswith("ICB Industry") or c == "Sector"), None)
    for _, r in nq.iterrows():
        t = yahoo_symbol(r[tcol])
        if t in rows:
            rows[t]["index"] = "beide"
        else:
            rows[t] = {"ticker": t, "name": r[ncol], "sektor": r[scol] if scol else "", "index": "nasdaq100"}
    for t in C.WATCHLIST_STOCKS:
        t = yahoo_symbol(t)
        rows.setdefault(t, {"ticker": t, "name": t, "sektor": "", "index": "watchlist"})
    return pd.DataFrame(list(rows.values())).sort_values("ticker").reset_index(drop=True)


def binance_usdt_bases() -> set[str]:
    r = requests.get(BINANCE_INFO, params={"permissions": "SPOT"}, timeout=60, headers=HEADERS)
    r.raise_for_status()
    return {s["baseAsset"] for s in r.json()["symbols"]
            if s["quoteAsset"] == "USDT" and s["status"] == "TRADING"}


def _looks_stable(x: dict) -> bool:
    """Neue Stablecoins fehlen in jeder festen Liste: Kurs ~1 $ und 30 Tage fast unbewegt."""
    p = x.get("current_price") or 0
    ch = x.get("price_change_percentage_30d_in_currency")
    return 0.97 <= p <= 1.03 and ch is not None and abs(ch) < 2.0


def crypto(n: int = C.N_CRYPTO) -> pd.DataFrame:
    """Top n nach Marktkapitalisierung ohne Stablecoins/Wrapped/Gold-Token, nur mit Binance-USDT-Paar.
    Spalten = CoinGecko-Felder + symbol (gross) + pair."""
    r = requests.get(COINGECKO, params={"vs_currency": "usd", "order": "market_cap_desc", "per_page": 120,
                                        "page": 1, "price_change_percentage": "7d,30d"},
                     timeout=60, headers=HEADERS)
    r.raise_for_status()
    bases = binance_usdt_bases()
    out = []
    for x in r.json():
        s = x["symbol"].upper()
        if s in C.CRYPTO_EXCLUDE or s not in bases or any(o["symbol"] == s for o in out):
            continue
        if _looks_stable(x):
            continue
        out.append({**x, "symbol": s, "pair": f"{s}USDT"})
        if len(out) >= n:
            break
    return pd.DataFrame(out)
