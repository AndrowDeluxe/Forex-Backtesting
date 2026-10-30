"""Physische Ablage des Data Lake -- EIN Layer (validated/), siehe
data_lake/__init__.py-Docstring fuer die Begruendung, warum keine separate
raw/-Ablage existiert. Jede (source, key, timeframe)-Kombination lebt in
genau EINER Parquet-Datei, inkrementell per write_bars() fortgeschrieben
(letzter gespeicherter Balken -> jetzt, mit kleiner Ueberlappung), nie
komplett neu geschrieben -- reduziert die Fenstergroesse jeder einzelnen
Dukascopy-Anfrage gegenueber dem bisherigen "kompletter Lookback jeden
Zyklus"-Muster der Bots selbst (siehe ny_open_orb/data.py-Docstring: laengere
Anfragen treffen den dukascopy_python-Paginierungs-Bug haeufiger)."""

import logging
from pathlib import Path

import pandas as pd

LAKE_DIR = Path(__file__).resolve().parent.parent / "data_lake_store" / "validated"

log = logging.getLogger("data_lake.storage")

# Raster je Intraday-Timeframe (UTC, ab Epoche) -- alle Lake-Reihen liegen darauf
# (2026-10-30 gegen alle 24 Intraday-Reihen geprueft, H4 = 00/04/08/... UTC).
_INTRADAY_STEP = {"M1": "1min", "M5": "5min", "M15": "15min", "M30": "30min", "H1": "1h", "H4": "4h"}


def _guard_intraday(existing: pd.DataFrame | None, new_df: pd.DataFrame, timeframe: str,
                    backfill: pd.Timedelta | None, label: str) -> pd.DataFrame:
    """Schutz gegen zwei reale Vorfaelle (siehe knowledge/CHANGELOG.md 2026-10-28/-30):
    Windows-Zeitzonenspruenge 15.-17.09. haengten um +1 h versetzte Kerzen an, und der
    Twelve-Data-Failover schrieb pauschal 500 Kerzen (anderes H4-Raster, Volumen 0,
    Wochenend-Kerzen) rueckwirkend ueber die Dukascopy-Historie. Beides machte
    _bar_length() in gold_smc_htf_ltf/ falsch und die CTNL-Nachrechnung vorausschauend.

    1. Liegt ein neuer Zeitstempel nicht auf dem Raster -> ValueError, nichts wird geschrieben.
    2. Bereits gespeicherte, geschlossene Kerzen bleiben unangetastet: ueberschrieben werden
       darf nur ab der vorletzten gespeicherten Kerze (noch nicht abgeschlossene Kerze).
    3. Fehlende aeltere Kerzen werden nur innerhalb von `backfill` vor der letzten
       gespeicherten Kerze nachgetragen (= das Ueberlappungsfenster von ingest.py);
       backfill=None -> nur anhaengen (Twelve-Data-Failover)."""
    step = pd.Timedelta(_INTRADAY_STEP[timeframe])
    utc = new_df.index.tz_convert("UTC") if new_df.index.tz is not None else new_df.index
    off_grid = utc[utc.floor(step) != utc]
    if len(off_grid):
        raise ValueError(f"{len(off_grid)} Zeitstempel nicht auf dem {timeframe}-Raster "
                         f"(z.B. {off_grid[0]}) -- nichts geschrieben")
    if existing is None or existing.empty:
        return new_df

    last = existing.index.max()
    tail = new_df.index >= last - step
    gap_fill = ~new_df.index.isin(existing.index)
    if backfill is not None:
        gap_fill &= new_df.index >= last - backfill
    else:
        gap_fill &= False
    keep = tail | gap_fill

    ignored = new_df[~keep]
    if len(ignored):
        old = ignored.index.intersection(existing.index)
        close = next((c for c in ("Close", "close") if c in new_df.columns and c in existing.columns), None)
        n_conflict = int((ignored.loc[old, close] != existing.loc[old, close]).sum()) if close else 0
        n_new = len(ignored) - len(old)
        if n_conflict or n_new:
            log.warning("%s: %d abweichende Werte fuer bereits gespeicherte Kerzen und %d Kerzen "
                        "ausserhalb des Nachtragsfensters verworfen (Historie bleibt unveraendert).",
                        label, n_conflict, n_new)
    return new_df[keep]


def path_for(source: str, key: str, timeframe: str) -> Path:
    """z.B. path_for("dukascopy", "GOLD", "M15") ->
    data_lake_store/validated/dukascopy/GOLD_M15.parquet -- EIN Verzeichnis
    pro Quelle, damit z.B. spaetere MT5-Rohdaten sich nie mit Dukascopy-
    Dateien gleichen Namens mischen koennen."""
    return LAKE_DIR / source / f"{key}_{timeframe}.parquet"


def read_bars(source: str, key: str, timeframe: str) -> pd.DataFrame | None:
    """None, falls es diese Datei noch nie gab (erster Ingest-Lauf steht
    noch aus) -- Aufrufer (reader.py) behandelt das wie "kein Lake-Treffer"."""
    path = path_for(source, key, timeframe)
    if not path.exists():
        return None
    return pd.read_parquet(path)


def write_bars(source: str, key: str, timeframe: str, new_df: pd.DataFrame,
               backfill: pd.Timedelta | None = None) -> pd.DataFrame:
    """Merged `new_df` in die bestehende Datei (falls vorhanden), dedupliziert
    per Index (letzter Wert gewinnt -- ein erneut angefragter, ueberlappender
    Zeitraum darf den vorhandenen Balken ueberschreiben, z.B. eine zuvor noch
    nicht abgeschlossene Kerze), sortiert und schreibt EINMAL zurueck. Gibt
    das gemergte Ergebnis zurueck (ingest.py nutzt das fuers Manifest:
    n_rows/last_bar_ts). Intraday-Reihen laufen vorher durch _guard_intraday
    (Raster-Pruefung, Historie nur am Ende veraenderbar, `backfill` siehe dort)."""
    path = path_for(source, key, timeframe)
    existing = read_bars(source, key, timeframe)
    if timeframe in _INTRADAY_STEP and isinstance(new_df.index, pd.DatetimeIndex):
        new_df = _guard_intraday(existing, new_df, timeframe, backfill, f"{source}:{key}_{timeframe}")
    if existing is not None and not existing.empty:
        combined = pd.concat([existing, new_df])
        combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    else:
        combined = new_df.sort_index()

    # D1 zusaetzlich auf KALENDERTAG deduplizieren, nicht nur auf den exakten
    # Zeitstempel. Grund (realer Vorfall 2026-09-15): TradingView lieferte die
    # 2y-Zinsreihen ploetzlich eine Stunde spaeter gestempelt (DE 08:00 -> 09:00,
    # US 01:00 -> 02:00). Die Zeitstempel-Deduplizierung oben sieht darin lauter
    # NEUE Balken -- die komplette Historie wurde ein zweites Mal angehaengt
    # (3.657 -> 7.307 Zeilen). cls_practical/rates.py::compute_daily_rate_score_2y
    # legt den Index auf .date um und scheiterte danach bei JEDEM Scan mit
    # "cannot reindex on an axis with duplicate labels" -- das Bein war auf
    # Funded und FK ab 2026-09-15 22:38 tot (792 fehlgeschlagene Scans).
    # Eine Tagesreihe hat per Definition einen Balken pro Tag; der spaeteste
    # Stempel des Tages gewinnt. Fuer korrekt gestempelte Reihen ist das ein
    # No-Op (2026-09-16 gegen alle 62 D1-Reihen geprueft: nur die beiden
    # TradingView-Zinsreihen waren betroffen).
    if timeframe == "D1" and isinstance(combined.index, pd.DatetimeIndex) and not combined.empty:
        by_date = pd.Index(combined.index.date)
        combined = combined[~by_date.duplicated(keep="last")]

    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomar schreiben (temp + rename) -- ein Absturz mitten im Schreiben darf
    # nie eine halb geschriebene, kaputte Parquet-Datei hinterlassen, die der
    # naechste Bot-Lauf dann faelschlich fuer gueltig haelt.
    tmp_path = path.with_suffix(".parquet.tmp")
    combined.to_parquet(tmp_path)
    tmp_path.replace(path)
    return combined
