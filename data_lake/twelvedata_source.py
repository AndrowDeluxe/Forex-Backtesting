"""Backup-Datenquelle fuer den Data-Lake-Pilot (2026-09-06, Nutzerauftrag nach
wiederholten Dukascopy-Haengern): springt in `ingest.py` erst ein, wenn
Dukascopy fuer einen Key 2x in Folge scheitert (siehe manifest.py::
consecutive_failures) -- NICHT jeden Zyklus parallel abgefragt, das kostenlose
Twelve-Data-Kontingent (800 Anfragen/Tag, siehe https://twelvedata.com/pricing)
reicht bei 24 Keys x alle 5 Min. (288 Zyklen/Tag) fuer ein "immer beide Quellen
abfragen"-Schema NICHT (24x288 >> 800) -- reaktiv fuer alle 24 Keys nutzbar,
ein Dauer-Parallelabgleich waere nur fuer ~2-3 Keys ueberhaupt budgetierbar.

`timezone=UTC` wird IMMER explizit mitgegeben -- ohne den Parameter ist das
Antwortformat mehrdeutig (empirisch verifiziert 2026-09-06: derselbe Call
ohne/mit `timezone=UTC` lieferte zwei verschiedene "aktuellste Kerze"-
Zeitstempel mit ~10h Abstand, kein sauberer fester Offset). Nur FX-Majors +
Gold/Silber abgedeckt (SYMBOL_MAP) -- Platin/CHFJPY/Indizes/Anleihen/2Y-
Renditen sind auf dem kostenlosen Twelve-Data-Plan nicht zuverlaessig/gar
nicht verfuegbar, bewusst NICHT geraten, sondern hier offen als Luecke
dokumentiert statt eine falsche Zuordnung zu riskieren."""

import tomllib
from pathlib import Path

import pandas as pd
import requests

SECRETS_PATH = Path(__file__).resolve().parent.parent / ".streamlit" / "secrets.toml"

SYMBOL_MAP = {
    "EURUSD": "EUR/USD", "GBPUSD": "GBP/USD", "USDJPY": "USD/JPY",
    "USDCHF": "USD/CHF", "AUDUSD": "AUD/USD", "USDCAD": "USD/CAD",
    "GOLD": "XAU/USD", "SILVER": "XAG/USD",
}

_TIMEFRAME_MAP = {"M5": "5min", "M15": "15min", "H1": "1h", "H4": "4h", "D1": "1day", "W1": "1week"}


def _load_api_key() -> str:
    data = tomllib.loads(SECRETS_PATH.read_text(encoding="utf-8"))
    key = data.get("twelvedata", {}).get("api_key")
    if not key:
        raise FileNotFoundError(f"{SECRETS_PATH}: Abschnitt [twelvedata] braucht api_key.")
    return key


def is_covered(key: str) -> bool:
    return key in SYMBOL_MAP


def fetch(key: str, timeframe: str, outputsize: int = 500) -> pd.DataFrame:
    """Liefert dieselbe Form wie combined_strategy.data.fetch_timeframe()
    (Capitalized-Spalten, UTC-tz-aware Index, aufsteigend sortiert) -- damit
    ingest.py das Ergebnis unveraendert in denselben Lake-Speicherplatz
    schreiben kann wie eine Dukascopy-Antwort, reader.py braucht dafuer KEINE
    Aenderung. outputsize=500 statt Datumsbereich, da Twelve Data (anders als
    dukascopy_python) "letzte N Balken" nativ unterstuetzt -- reicht fuer die
    Ueberbrueckungsluecke waehrend eines Dukascopy-Ausfalls locker."""
    if key not in SYMBOL_MAP:
        raise ValueError(f"Twelve Data deckt {key!r} nicht ab (siehe SYMBOL_MAP) -- kein Backup fuer diesen Key.")
    if timeframe not in _TIMEFRAME_MAP:
        raise ValueError(f"unbekannter Timeframe {timeframe!r} fuer Twelve Data, erwartet {list(_TIMEFRAME_MAP)}")

    resp = requests.get(
        "https://api.twelvedata.com/time_series",
        params={
            "symbol": SYMBOL_MAP[key], "interval": _TIMEFRAME_MAP[timeframe],
            "outputsize": outputsize, "timezone": "UTC", "apikey": _load_api_key(),
        },
        timeout=15,
    )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("status") != "ok" or "values" not in payload:
        raise RuntimeError(f"Twelve Data lieferte kein OK fuer {key}/{timeframe}: {payload}")

    df = pd.DataFrame(payload["values"])
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df = df.set_index("datetime").sort_index()
    df.index.name = "timestamp"
    for col in ("open", "high", "low", "close"):
        df[col] = df[col].astype(float)
    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close"})
    if "volume" in df.columns:
        df["Volume"] = df["volume"].astype(float)
        df = df.drop(columns=["volume"])
    else:
        df["Volume"] = 0.0  # FX/Metalle liefern kein Volume -- 0.0 statt fehlender Spalte,
        # damit validate_ohlc_numeric() (erwartet nur Open/High/Low/Close) unveraendert greift
        # und nachgelagerter Code, der optional eine Volume-Spalte anfasst, nicht crasht.
    return df[["Open", "High", "Low", "Close", "Volume"]]
