"""Numerische TradingView-Daten -- OHLCV-Kursverlauf (tvDatafeed) und ein
Snapshot von TradingViews eigener technischer Analyse (RSI/MACD/gleitende
Durchschnitte/Gesamtempfehlung, tradingview_ta). Analog zu den bestehenden
yfinance-basierten data.py-Modulen im Projekt, aber fuer Faelle, in denen
gezielt TradingViews eigene Berechnung/Symbolabdeckung gebraucht wird statt
Yahoo Finance.

fetch_ohlcv() laeuft IMMER anonym (tvDatafeed funktioniert eingeschraenkt in
Historie/Rate-Limit, aber ausreichend -- siehe cls_practical/rates.py
Docstring: TVC:DE02Y/US02Y bis 2014 zurueck bereits ohne Login abrufbar).
Der fruehere Pro-Account-Login (.streamlit/secrets.toml) wurde 2026-09-03
entfernt: TradingView verlangt seit einiger Zeit ein Captcha beim
Passwort-Login, das die Bibliothek nicht loesen kann (offenes, seit
2024-12-07 ungeloestes Upstream-Issue, github.com/rongardF/tvdatafeed/
issues/62, "recaptcha_required") -- jeder Versuch schlug zuverlaessig fehl
und erzeugte nur noch ERROR-Log-Spam ("error while signin") bei praktisch
jedem Bridge-Lauf (Funded-Portfolio-Bridge + FK Instant Funding, seit
2026-09-01), ohne echten Funktionsgewinn, da die anonyme Historie fuer
diesen Bedarf ohnehin ausreicht. fetch_indicators() braucht nie einen Login
(TradingViews Scanner-API ist oeffentlich)."""

from functools import lru_cache

import pandas as pd
from tradingview_ta import Interval as TAInterval
from tradingview_ta import TA_Handler
from tvDatafeed import Interval, TvDatafeed

_INTERVAL_MAP = {
    "1m": Interval.in_1_minute, "5m": Interval.in_5_minute, "15m": Interval.in_15_minute,
    "1h": Interval.in_1_hour, "4h": Interval.in_4_hour, "1d": Interval.in_daily,
    "1w": Interval.in_weekly,
}
_TA_INTERVAL_MAP = {
    "1m": TAInterval.INTERVAL_1_MINUTE, "5m": TAInterval.INTERVAL_5_MINUTES,
    "15m": TAInterval.INTERVAL_15_MINUTES, "1h": TAInterval.INTERVAL_1_HOUR,
    "4h": TAInterval.INTERVAL_4_HOURS, "1d": TAInterval.INTERVAL_1_DAY,
    "1w": TAInterval.INTERVAL_1_WEEK,
}


@lru_cache(maxsize=1)
def _client() -> TvDatafeed:
    return TvDatafeed()  # anonym, eingeschraenkt -- siehe Modul-Docstring


def fetch_ohlcv(symbol: str, exchange: str, interval: str = "1d", n_bars: int = 500) -> pd.DataFrame:
    """symbol z.B. "AAPL", exchange z.B. "NASDAQ" -- wie im TradingView-Chart-Link
    tradingview.com/chart/?symbol=NASDAQ:AAPL. Gibt ein DataFrame mit Spalten
    open/high/low/close/volume zurueck, Index = Zeitstempel."""
    tv_interval = _INTERVAL_MAP.get(interval)
    if tv_interval is None:
        raise ValueError(f"Unbekanntes interval={interval!r}, erlaubt: {list(_INTERVAL_MAP)}")
    df = _client().get_hist(symbol=symbol, exchange=exchange, interval=tv_interval, n_bars=n_bars)
    if df is None or df.empty:
        raise RuntimeError(f"Keine Daten fuer {exchange}:{symbol} ({interval}) erhalten.")
    return df


def fetch_indicators(symbol: str, exchange: str, screener: str = "america", interval: str = "1d") -> dict:
    """Kein Login noetig. screener passend zur Boerse waehlen (z.B. "america" fuer
    NASDAQ/NYSE, "germany" fuer XETRA/DAX-Werte, "forex" fuer FX-Paare -- siehe
    tradingview_ta-Doku fuer die vollstaendige Liste)."""
    handler = TA_Handler(
        symbol=symbol, exchange=exchange, screener=screener,
        interval=_TA_INTERVAL_MAP.get(interval, TAInterval.INTERVAL_1_DAY),
    )
    analysis = handler.get_analysis()
    return {
        "summary": analysis.summary,  # {"RECOMMENDATION": "BUY"/"SELL"/"NEUTRAL", "BUY": n, "SELL": n, "NEUTRAL": n}
        "oscillators": analysis.oscillators,
        "moving_averages": analysis.moving_averages,
        "indicators": analysis.indicators,  # Rohwerte: RSI, MACD.macd, ADX, ...
    }
