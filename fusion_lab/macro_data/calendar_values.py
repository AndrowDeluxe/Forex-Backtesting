"""Ersatzwerte aus dem Wirtschaftskalender und Zusammenfuehrung mit den Hauptreihen.

Ersatzreihen tragen einen eigenen Schluessel `<LAND>.<GROESSE>@<QUELLE>`, damit sie die Hauptreihe
im Speicher nie ueberschreiben (sonst zaehlte jeder Lauf als Revision). Erst `extend()` haengt sie
an: Werte einer Ersatzreihe zaehlen nur NACH dem letzten Datum der Hauptreihe. So gewinnt die
Hauptquelle, sobald sie nachzieht, und die Luecke dazwischen fuellt der schnellere Ersatz.

Anlass (10.11.2026): BIS-Leitzinsen hinkten nach Notenbank-Entscheiden nach (BoE 3,75 statt 4,00).
Definitionen geprueft: GB/AU/CA/NZ/CH/JP melden im Kalender denselben Satz wie BIS. US meldet die
Obergrenze (BIS: Mitte) und EA den Hauptrefi-Satz (BIS: Einlagensatz) -> beide nicht aus dem
Kalender; EA verlaengert stattdessen der taegliche Einlagensatz von FRED.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import calendar, store

ROOT = Path(__file__).resolve().parents[2]
FF_HISTORY = ROOT / "data_cache" / "remy" / "ff_calendar.parquet"
CCY_LAND = {"USD": "US", "EUR": "EA", "GBP": "GB", "JPY": "JP", "CHF": "CH", "AUD": "AU", "CAD": "CA", "NZD": "NZ"}
# (Waehrung, Titel) -> Groesse. ForexFactory-Titel gelten fuer Live-Feed und Historie, myfxbook nur live.
TITLES = {
    ("GBP", "Official Bank Rate"): "policy_rate", ("GBP", "BoE Interest Rate Decision"): "policy_rate",
    ("AUD", "Cash Rate"): "policy_rate", ("AUD", "RBA Interest Rate Decision"): "policy_rate",
    ("CAD", "Overnight Rate"): "policy_rate", ("CAD", "BoC Interest Rate Decision"): "policy_rate",
    ("NZD", "Official Cash Rate"): "policy_rate", ("NZD", "RBNZ Interest Rate Decision"): "policy_rate",
    ("CHF", "SNB Policy Rate"): "policy_rate", ("CHF", "SNB Interest Rate Decision"): "policy_rate",
    ("JPY", "BOJ Policy Rate"): "policy_rate", ("JPY", "BoJ Interest Rate Decision"): "policy_rate",
    # Kern-Inflation: Japan ohne Frischware (BoJ-Standard), Kanada Trimmed Mean (BoC-Vorzugsmass)
    ("JPY", "National Core CPI y/y"): "core_yoy", ("CAD", "Trimmed CPI y/y"): "core_yoy",
}
# Hauptreihe -> Ersatzreihen, die sie nach ihrem letzten Datum verlaengern
ALIASES = {"EA.policy_rate": ["EA.ecb_deposit"], "US.services_yoy": ["US.services_yoy@fred"],
           "AU.2y": ["AU.2y_tvc"]}  # RBA ueber DBnomics ~1 Woche Verzug


def _value(text) -> float | None:
    value, unit = calendar.parse_number(str(text).strip().lstrip("<>"))
    return value if unit in ("%", "") else None


def from_events(events: pd.DataFrame) -> pd.DataFrame:
    """events: currency, title, event_time (UTC, ohne Zeitzone), actual. Datum = Tag der Bekanntgabe."""
    rows = []
    for e in events.itertuples():
        quantity = TITLES.get((e.currency, e.title))
        value = _value(e.actual) if quantity else None
        if value is not None:
            rows.append({"key": f"{CCY_LAND[e.currency]}.{quantity}@cal",
                         "date": pd.Timestamp(e.event_time).normalize(), "value": value})
    df = pd.DataFrame(rows, columns=["key", "date", "value"])
    return df.drop_duplicates(["key", "date"], keep="last")


def fetch_calendar_values() -> pd.DataFrame:
    """Kein Netzabruf: liest den archivierten Live-Kalender und die FF-Historie ab 2007."""
    parts = []
    if FF_HISTORY.exists():
        h = pd.read_parquet(FF_HISTORY)
        parts.append(pd.DataFrame({"currency": h["currency"], "title": h["name"], "actual": h["actual"],
                                   "event_time": pd.to_datetime(h["time"], utc=True).dt.tz_localize(None)}))
    live_path = store.DATA_DIR / "calendar.parquet"
    if live_path.exists():
        live = pd.read_parquet(live_path).sort_values("fetched_at")
        live = live[live["actual"].astype(str).str.strip() != ""]
        parts.append(live.drop_duplicates(["source", "currency", "title", "event_time"], keep="last")
                     [["currency", "title", "actual", "event_time"]])
    if not parts:
        raise ValueError("weder FF-Historie noch Live-Kalender vorhanden")
    return from_events(pd.concat(parts, ignore_index=True).sort_values("event_time"))


def services_yoy_from_index(long: pd.DataFrame) -> pd.DataFrame:
    """US-Dienste-Inflation j/j aus dem FRED-Index (CUSR0000SASLE)."""
    idx = long[long["key"] == "US.services_index"].set_index("date")["value"].sort_index()
    yoy = (idx / idx.shift(12) - 1) * 100
    return pd.DataFrame({"key": "US.services_yoy@fred", "date": yoy.index, "value": yoy.values}).dropna()


def extend(long: pd.DataFrame) -> pd.DataFrame:
    """Haengt Ersatzwerte an die Hauptreihen an (nur Daten nach deren letztem Datum).
    Rueckgabe ohne die @-Schluessel; Eingabe/Ausgabe im Langformat key, date, value."""
    long = pd.concat([long[["key", "date", "value"]], services_yoy_from_index(long)], ignore_index=True)
    alt_map: dict[str, list[str]] = {}
    for k in long["key"].unique():
        if "@" in k:
            alt_map.setdefault(k.split("@")[0], []).append(k)
    for main, alts in ALIASES.items():
        alt_map.setdefault(main, []).extend(alts)
    main_rows = long[~long["key"].str.contains("@")]
    out = [main_rows]
    for main, alts in alt_map.items():
        last = main_rows.loc[main_rows["key"] == main, "date"].max()
        for alt in alts:
            part = long[long["key"] == alt]
            if pd.notna(last):
                part = part[part["date"] > last]
            out.append(part.assign(key=main))  # ein Alias (z. B. EA.ecb_deposit) bleibt auch unter eigenem Namen
            if len(part):
                last = max(last, part["date"].max()) if pd.notna(last) else part["date"].max()
    merged = pd.concat(out, ignore_index=True)
    return merged.drop_duplicates(["key", "date"], keep="last").sort_values(["key", "date"]).reset_index(drop=True)
