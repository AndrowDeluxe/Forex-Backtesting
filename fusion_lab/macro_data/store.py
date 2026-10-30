"""Ablage mit Abrufzeit (point-in-time).

Eine Datei je Bereich, Langformat: key, date, value, fetched_at. Beim Speichern
kommen nur neue oder geaenderte Werte dazu, eine Revision ueberschreibt also nichts.
Wichtig: Point-in-time gilt erst ab dem ersten Abruf (30.10.2026). Davor steht bei
allen Werten dieselbe Abrufzeit, sie zeigen dort den heutigen Revisionsstand.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "fusion_lab" / "data" / "macro_data"
COLUMNS = ["key", "date", "value", "fetched_at"]


def _path(area: str, data_dir: Path | None = None) -> Path:
    return (data_dir or DATA_DIR) / f"{area}.parquet"


def read_all(area: str, data_dir: Path | None = None) -> pd.DataFrame:
    """Alle gespeicherten Staende, auch ueberholte."""
    path = _path(area, data_dir)
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)
    return pd.read_parquet(path)


def latest(area: str, as_of: pd.Timestamp | None = None, data_dir: Path | None = None) -> pd.DataFrame:
    """Je key und date der neueste Stand, optional wie er zum Zeitpunkt as_of bekannt war."""
    df = read_all(area, data_dir)
    if as_of is not None:
        df = df[df["fetched_at"] <= as_of]
    return df.sort_values("fetched_at").drop_duplicates(["key", "date"], keep="last").sort_values(["key", "date"])


def append(area: str, new: pd.DataFrame, fetched_at: pd.Timestamp | None = None,
           data_dir: Path | None = None) -> int:
    """Speichert neue und geaenderte Werte, gibt deren Anzahl zurueck.
    new braucht die Spalten key, date, value."""
    now = fetched_at if fetched_at is not None else pd.Timestamp.now("UTC").tz_localize(None)
    new = new[["key", "date", "value"]].dropna(subset=["value"]).copy()
    new["date"] = pd.to_datetime(new["date"])
    new["value"] = pd.to_numeric(new["value"])
    new = new.drop_duplicates(["key", "date"], keep="last")

    known = latest(area, data_dir=data_dir)
    merged = new.merge(known[["key", "date", "value"]], on=["key", "date"], how="left", suffixes=("", "_alt"))
    changed = merged[(merged["value"] - merged["value_alt"]).abs().fillna(float("inf")) > 1e-9]
    if changed.empty:
        return 0
    rows = changed[["key", "date", "value"]].assign(fetched_at=now)
    path = _path(area, data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_all(area, data_dir)
    out = pd.concat([existing, rows], ignore_index=True) if len(existing) else rows
    tmp = path.with_suffix(".tmp")
    out.to_parquet(tmp, index=False)
    tmp.replace(path)
    return len(rows)
