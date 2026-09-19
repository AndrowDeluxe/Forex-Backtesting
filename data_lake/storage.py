"""Physische Ablage des Data Lake -- EIN Layer (validated/), siehe
data_lake/__init__.py-Docstring fuer die Begruendung, warum keine separate
raw/-Ablage existiert. Jede (source, key, timeframe)-Kombination lebt in
genau EINER Parquet-Datei, inkrementell per write_bars() fortgeschrieben
(letzter gespeicherter Balken -> jetzt, mit kleiner Ueberlappung), nie
komplett neu geschrieben -- reduziert die Fenstergroesse jeder einzelnen
Dukascopy-Anfrage gegenueber dem bisherigen "kompletter Lookback jeden
Zyklus"-Muster der Bots selbst (siehe ny_open_orb/data.py-Docstring: laengere
Anfragen treffen den dukascopy_python-Paginierungs-Bug haeufiger)."""

from pathlib import Path

import pandas as pd

LAKE_DIR = Path(__file__).resolve().parent.parent / "data_lake_store" / "validated"


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


def write_bars(source: str, key: str, timeframe: str, new_df: pd.DataFrame) -> pd.DataFrame:
    """Merged `new_df` in die bestehende Datei (falls vorhanden), dedupliziert
    per Index (letzter Wert gewinnt -- ein erneut angefragter, ueberlappender
    Zeitraum darf den vorhandenen Balken ueberschreiben, z.B. eine zuvor noch
    nicht abgeschlossene Kerze), sortiert und schreibt EINMAL zurueck. Gibt
    das gemergte Ergebnis zurueck (ingest.py nutzt das fuers Manifest:
    n_rows/last_bar_ts)."""
    path = path_for(source, key, timeframe)
    existing = read_bars(source, key, timeframe)
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
