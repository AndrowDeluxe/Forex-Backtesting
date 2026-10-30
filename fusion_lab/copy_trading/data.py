"""Kurse (Dukascopy M1, Bid, UTC) und Kosten fuer die Copy-Trading-Calls.

Gleiches Muster wie smh_microstructure/data.py (jahresweise gecacht), aber mit allen
Instrumenten, zu denen in der Gruppe Calls gepostet werden. Bid-Bars: der Spread steckt
nicht in den Kursen, er wird je Rundturn voll abgezogen.
"""

from pathlib import Path

import dukascopy_python
import dukascopy_python.instruments as duka
import pandas as pd

CACHE = Path(__file__).resolve().parents[2] / "data_cache" / "copy_trading"
FIRST_YEAR = 2025
LAST_DAY = "2026-10-16"

INSTRUMENTS = {
    "EURUSD": duka.INSTRUMENT_FX_MAJORS_EUR_USD,
    "GBPUSD": duka.INSTRUMENT_FX_MAJORS_GBP_USD,
    "USDJPY": duka.INSTRUMENT_FX_MAJORS_USD_JPY,
    "AUDUSD": duka.INSTRUMENT_FX_MAJORS_AUD_USD,
    "USDCAD": duka.INSTRUMENT_FX_MAJORS_USD_CAD,
    "USDCHF": duka.INSTRUMENT_FX_MAJORS_USD_CHF,
    "NZDUSD": duka.INSTRUMENT_FX_MAJORS_NZD_USD,
    "EURJPY": duka.INSTRUMENT_FX_CROSSES_EUR_JPY,
    "GBPJPY": duka.INSTRUMENT_FX_CROSSES_GBP_JPY,
    "EURGBP": duka.INSTRUMENT_FX_CROSSES_EUR_GBP,
    "AUDJPY": duka.INSTRUMENT_FX_CROSSES_AUD_JPY,
    "CHFJPY": duka.INSTRUMENT_FX_CROSSES_CHF_JPY,
    "AUDNZD": duka.INSTRUMENT_FX_CROSSES_AUD_NZD,
    "XAUUSD": duka.INSTRUMENT_FX_METALS_XAU_USD,
    "XAGUSD": duka.INSTRUMENT_FX_METALS_XAG_USD,
    "US500": duka.INSTRUMENT_IDX_AMERICA_E_SANDP_500,
    "NAS100": duka.INSTRUMENT_IDX_AMERICA_E_NQ_100,
    "US30": duka.INSTRUMENT_IDX_AMERICA_E_D_J_IND,
    "USOIL": duka.INSTRUMENT_CMD_ENERGY_E_LIGHT,
}
ALIASES = {"SPX500": "US500", "SPX": "US500", "SP500": "US500", "SPY": "US500", "NASDAQ": "NAS100",
           "US100": "NAS100", "NAS": "NAS100", "DOW": "US30", "DJI": "US30", "GOLD": "XAUUSD",
           "SILVER": "XAGUSD", "WTI": "USOIL", "OIL": "USOIL"}

# Kosten je Rundturn in bps vom Kurs bzw. in Pips.
PIP = {s: (1e-2 if s.endswith("JPY") else 1e-4) for s in INSTRUMENTS if len(s) == 6 and s[:3] != "XAU"
       and s[:3] != "XAG"}
RT_PIPS = {"EURUSD": 1.2, "USDJPY": 1.4, "AUDUSD": 1.5, "GBPUSD": 1.6,   # smh_microstructure/costs.py
           "USDCAD": 1.6, "USDCHF": 1.6, "NZDUSD": 1.8, "EURGBP": 1.6, "EURJPY": 1.8, "GBPJPY": 2.5,
           # ANNAHME (20.10.2026, nicht gemessen): Crosses wie GBPJPY bzw. EURJPY
           "AUDJPY": 1.8, "CHFJPY": 2.5, "AUDNZD": 2.5}
RT_BPS = {"US500": 2.6, "NAS100": 2.3,                                   # smh_microstructure/costs.py
          # XAUUSD: 0,79 bps gemessen (BeyondIQCapital) + 0,45 bps Live-Slippage, aufgerundet
          # (scripts/research_fk_gesamtportfolio_2026.py)
          "XAUUSD": 1.3,
          # ANNAHME (20.10.2026): US30 wie US500; Silber und Oel breiter, nicht gemessen
          "US30": 2.6, "XAGUSD": 3.0, "USOIL": 3.0}


def norm_symbol(sym: str | None) -> str | None:
    if not sym:
        return None
    s = sym.upper().replace("/", "").replace(" ", "")
    s = ALIASES.get(s, s)
    return s if s in INSTRUMENTS else None


def roundtrip_cost(sym: str, price: float) -> float:
    """Kosten eines Rundturns in Kurseinheiten."""
    if sym in RT_PIPS:
        return RT_PIPS[sym] * PIP[sym]
    return RT_BPS[sym] * 1e-4 * price


def _year_path(sym: str, year: int) -> Path:
    suffix = "" if year < pd.Timestamp(LAST_DAY).year else f"_bis_{LAST_DAY}"
    return CACHE / f"{sym}_M1_{year}{suffix}.parquet"


def fetch_year(sym: str, year: int) -> pd.DataFrame:
    path = _year_path(sym, year)
    if path.exists():
        return pd.read_parquet(path)
    start = pd.Timestamp(f"{year}-01-01")
    end = min(pd.Timestamp(f"{year + 1}-01-01"), pd.Timestamp(LAST_DAY) + pd.Timedelta(days=1))
    df = dukascopy_python.fetch(INSTRUMENTS[sym], dukascopy_python.INTERVAL_MIN_1,
                                dukascopy_python.OFFER_SIDE_BID,
                                start.to_pydatetime(), end.to_pydatetime())
    df = df.sort_index()
    df = df[~df.index.duplicated()]
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index.name = "timestamp"
    out = df[["open", "high", "low", "close"]].astype("float64")
    CACHE.mkdir(parents=True, exist_ok=True)
    out.to_parquet(path)
    return out


_MEM: dict[str, pd.DataFrame] = {}
# Forward-Test Stufe 2 (28.10.2026): Kurse nach LAST_DAY kommen aus einem eigenen, taeglich
# fortgeschriebenen Cache. Nur wenn EXTEND gesetzt ist; IS/OOS-Laeufe bleiben unveraendert.
EXTEND = False


def fetch_tail(sym: str) -> pd.DataFrame:
    """M1 ab LAST_DAY+1 bis jetzt; holt nur die Tage ab dem letzten gespeicherten Tag nach."""
    path = CACHE / f"{sym}_M1_forward.parquet"
    old = pd.read_parquet(path) if path.exists() else None
    start = (pd.Timestamp(LAST_DAY) + pd.Timedelta(days=1) if old is None or old.empty
             else old.index[-1].tz_convert(None).normalize())
    end = pd.Timestamp.now("UTC").tz_convert(None)
    df = dukascopy_python.fetch(INSTRUMENTS[sym], dukascopy_python.INTERVAL_MIN_1,
                                dukascopy_python.OFFER_SIDE_BID,
                                start.to_pydatetime(), end.to_pydatetime())
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index.name = "timestamp"
    new = df[["open", "high", "low", "close"]].astype("float64")
    out = new if old is None else pd.concat([old[old.index < new.index.min()] if len(new) else old, new])
    out = out.sort_index()
    out = out[~out.index.duplicated(keep="last")]
    CACHE.mkdir(parents=True, exist_ok=True)
    out.to_parquet(path)
    return out


def load(sym: str) -> pd.DataFrame:
    if sym not in _MEM:
        parts = [fetch_year(sym, y) for y in range(FIRST_YEAR, pd.Timestamp(LAST_DAY).year + 1)]
        if EXTEND:
            parts.append(fetch_tail(sym))
        df = pd.concat(parts).sort_index()
        _MEM[sym] = df[~df.index.duplicated()]
    return _MEM[sym]


TF_RULE = {"M1": "1min", "M3": "3min", "M5": "5min", "M15": "15min", "M30": "30min", "M45": "45min",
           "H1": "1h", "H2": "2h", "H3": "3h", "H4": "4h", "H6": "6h", "H8": "8h", "H12": "12h",
           "H16": "16h", "D1": "1D", "W1": "W"}


def resample(m1: pd.DataFrame, tf: str) -> pd.DataFrame:
    rule = TF_RULE[tf]
    return m1.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
