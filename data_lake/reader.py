"""Lake-gestuetzte Ersatzfunktionen fuer jede Fetch-Funktion, die die 6
Funded-Portfolio-Bridge-Beine aufrufen -- gleicher Name/gleiche Signatur/
gleiche Rueckgabe-Form wie das Original, nur dass die Daten aus dem lokal
gepflegten Lake kommen statt live von Dukascopy/TradingView/yfinance.
_scan_*(..., source="lake") in challenge_portfolio/paper_bot.py importiert
NUR diese Funktionen an Stelle der Originale -- kein anderer Code-Pfad
aendert sich (siehe Plan-Dokument, Abschnitt "Integration").

Wirft LakeMissingDataError/LakeStaleDataError statt stillschweigend leere
oder veraltete Daten zurueckzugeben -- der bestehende _retry()/
_record_scan_error()-Pfad in paper_bot.py/run_once.py behandelt das dann
GENAU WIE einen heutigen Dukascopy-Fehler (Bein wird diesen Zyklus
uebersprungen, kein Crash, kein stiller Fallback auf veraltete Kurse)."""

import pandas as pd

from data_lake import manifest, storage


class LakeMissingDataError(Exception):
    pass


class LakeStaleDataError(Exception):
    pass


def _require_fresh(source: str, key: str, timeframe: str) -> pd.DataFrame:
    df = storage.read_bars(source, key, timeframe)
    if df is None or df.empty:
        raise LakeMissingDataError(f"Keine Lake-Daten fuer {source}:{key}_{timeframe} -- Ingestion noch nicht gelaufen?")
    if not manifest.is_fresh(source, key, timeframe):
        entry = manifest.get_entry(source, key, timeframe)
        raise LakeStaleDataError(
            f"Lake-Daten fuer {source}:{key}_{timeframe} zu alt (last_success_at={entry and entry.get('last_success_at')})"
        )
    return df


def _slice(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    idx = df.index
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if idx.tz is not None:
        start_ts = start_ts.tz_localize(idx.tz) if start_ts.tzinfo is None else start_ts.tz_convert(idx.tz)
        end_ts = end_ts.tz_localize(idx.tz) if end_ts.tzinfo is None else end_ts.tz_convert(idx.tz)
    return df[(idx >= start_ts) & (idx <= end_ts)]


_RENAME_CAP_TO_LOWER = {"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}


def _to_lower_tz(df: pd.DataFrame, tz: str) -> pd.DataFrame:
    df = df.rename(columns=_RENAME_CAP_TO_LOWER)
    df.index = df.index.tz_convert(tz)
    return df


# ---------------------------------------------------------------- combined_strategy.data.fetch_timeframe (raw shape)
def fetch_timeframe(key: str, timeframe: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    df = _require_fresh("dukascopy", key, timeframe)
    return _slice(df, start, end)


# ---------------------------------------------------------------- asian_range_breakout.data.fetch_gold_m15 (gold_asb)
def fetch_gold_m15(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    df = _to_lower_tz(_require_fresh("dukascopy", "GOLD", "M15"), "America/New_York")
    return _slice(df, start, end)


# ---------------------------------------------------------------- bond_yield_indicator.friction.fetch_fx_friction (gold_asb)
def fetch_fx_friction(pair: str, start: str, end: str, force_refresh: bool = False) -> pd.Series:
    from bond_yield_indicator.friction import corwin_schultz_spread

    df = _require_fresh("dukascopy", pair, "D1")
    s = corwin_schultz_spread(df["High"], df["Low"])
    if s.index.tz is not None:
        s.index = s.index.tz_localize(None)
    return _slice(s.to_frame("cs_spread"), start, end)["cs_spread"].rename("cs_spread")


# ---------------------------------------------------------------- cls_practical.data.* (cls_practical)
def fetch_eurusd_entry_tf_berlin(timeframe: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    if timeframe != "M5":
        raise LakeMissingDataError(f"Lake fuehrt EURUSD nur als M5 (Pilot-Umfang) -- angefragt: {timeframe!r}")
    df = _to_lower_tz(_require_fresh("dukascopy", "EURUSD", "M5"), "Europe/Berlin")
    return _slice(df, start, end)


def fetch_major_m15_berlin(key: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    df = _to_lower_tz(_require_fresh("dukascopy", key, "M15"), "Europe/Berlin")
    return _slice(df, start, end)


def fetch_rate_instrument_m5_berlin(key: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    # bereits in der Original-Form gespeichert (sources.py::_rate_instrument ruft die echte
    # Funktion direkt auf) -- kein weiteres Reshaping noetig.
    df = _require_fresh("dukascopy", key, "M5")
    return _slice(df, start, end)


def fetch_2y_yield_daily(key: str, n_bars: int = 3650, force_refresh: bool = False) -> pd.DataFrame:
    # ignoriert n_bars bewusst -- der Lake haelt die volle bislang eingesammelte Historie,
    # identisch zur Original-Funktion, die ohnehin nur "die letzten n_bars" kennt statt einer
    # echten Spanne (siehe cls_practical/data.py-Docstring).
    return _require_fresh("tradingview", key, "D1")


# ---------------------------------------------------------------- gold_smc_htf_ltf.data.* (ctnl_edge)
def fetch_gold_h4(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return _slice(_to_lower_tz(_require_fresh("dukascopy", "GOLD", "H4"), "America/New_York"), start, end)


def fetch_gold_h1(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return _slice(_to_lower_tz(_require_fresh("dukascopy", "GOLD", "H1"), "America/New_York"), start, end)


def fetch_gold_m15_ny(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    """Gleiche zugrunde liegenden Balken wie fetch_gold_m15() oben (gold_asb),
    nur fuer ctnl_edge's eigene lowercase/NY-tz-Erwartung -- eigener Name,
    damit _scan_ctnl nicht versehentlich die gold_asb-Variante importiert
    (beide lesen aus demselben gespeicherten (dukascopy,GOLD,M15))."""
    return fetch_gold_m15(start, end, force_refresh)


def fetch_gold_m5(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return _slice(_to_lower_tz(_require_fresh("dukascopy", "GOLD", "M5"), "America/New_York"), start, end)


# ---------------------------------------------------------------- ny_open_orb.data.* (orb)
def fetch_m5(instrument: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    # bereits in Original-Form gespeichert (sources.py::_orb ruft die echte Funktion direkt auf).
    return _slice(_require_fresh("dukascopy", instrument, "M5"), start, end)


def fetch_m15(instrument: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return _slice(_require_fresh("dukascopy", instrument, "M15"), start, end)


# ---------------------------------------------------------------- yfinance (ou_modell)
def fetch_ticker_daily(ticker: str, start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    return _slice(_require_fresh("yfinance", ticker, "D1"), start, end)
