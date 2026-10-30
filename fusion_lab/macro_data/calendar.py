"""Kalender + Konsens + Ist, jeder Abruf wird archiviert (eigene Historie waechst ab 30.10.2026).

  Forex Factory, Wochenfeed: Termine der laufenden Woche mit Konsens, aber ohne Ist.
  Myfxbook, RSS:             Termine des laufenden Tages mit Konsens und Ist.

Der Myfxbook-Feed zeigt nur den laufenden Tag (GMT). Ein Tag ohne Abruf ist also
verloren, darum laeuft der Abruf zweimal taeglich. Die Ueberraschung kommt allein aus
Myfxbook, weil Ereignistitel zwischen beiden Quellen nicht uebereinstimmen.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

import pandas as pd
import requests

from .store import DATA_DIR

FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
MYFXBOOK_URL = "https://www.myfxbook.com/rss/forex-economic-calendar-events"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
COLUMNS = ["source", "currency", "title", "event_time", "impact", "forecast", "previous", "actual", "fetched_at"]
KEY = ["source", "currency", "title", "event_time"]

COUNTRY_CCY = {"United States": "USD", "Euro Area": "EUR", "Eurozone": "EUR", "European Union": "EUR",
               "Germany": "EUR", "France": "EUR", "Italy": "EUR", "Spain": "EUR", "Netherlands": "EUR",
               "United Kingdom": "GBP", "Japan": "JPY", "Switzerland": "CHF", "Australia": "AUD",
               "Canada": "CAD", "New Zealand": "NZD"}
EURO_MEMBERS = {"Germany", "France", "Italy", "Spain", "Netherlands"}
UNIT_FACTOR = {"": 1.0, "%": 1.0, "K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}


def parse_number(text) -> tuple[float | None, str]:
    """'0.6%' -> (0.6, '%'), '-52.5K' -> (-52500.0, 'K'), '' -> (None, '')."""
    match = re.fullmatch(r"\s*([+-]?[\d,]*\.?\d+)\s*(%|[KMBT])?\s*", str(text or ""))
    if not match:
        return None, ""
    unit = match.group(2) or ""
    return float(match.group(1).replace(",", "")) * UNIT_FACTOR[unit], unit


def parse_ff(payload: list[dict]) -> pd.DataFrame:
    rows = [{"source": "forexfactory", "currency": e.get("country", ""), "title": e.get("title", ""),
             "event_time": pd.Timestamp(e["date"]).tz_convert("UTC").tz_localize(None),
             "impact": e.get("impact", ""), "forecast": e.get("forecast", ""),
             "previous": e.get("previous", ""), "actual": ""} for e in payload]
    return pd.DataFrame(rows)


def parse_myfxbook(xml: str) -> pd.DataFrame:
    """Nur G8-Laender. Titel kommt als 'Land Ereignis', die Werte als HTML-Tabelle in
    der Reihenfolge Restzeit, Impact, Previous, Consensus, Actual."""
    rows = []
    for item in re.findall(r"<item>(.*?)</item>", xml, flags=re.S):
        full_title = re.search(r"<title>(.*?)</title>", item, flags=re.S).group(1).strip()
        title_text = html.unescape(full_title)
        country = next((c for c in COUNTRY_CCY if title_text.startswith(c + " ")), None)
        if country is None:
            continue
        body = html.unescape(re.search(r"<description>(.*?)</description>", item, flags=re.S).group(1))
        cells = re.findall(r"<td[^>]*>(.*?)</td>", body, flags=re.S)
        if len(cells) < 5:
            continue
        impact = re.search(r"sprite-(\w+)-impact", cells[1])
        when = re.search(r"<pubDate>(.*?)</pubDate>", item).group(1)
        event = title_text[len(country) + 1:]
        if country in EURO_MEMBERS:  # gleiche Titel zur gleichen Zeit wie die Eurozone, sonst Kollision
            event = f"{country}: {event}"
        rows.append({"source": "myfxbook", "currency": COUNTRY_CCY[country],
                     "title": event,
                     "event_time": pd.to_datetime(when, format="%a, %d %b %Y %H:%M GMT"),
                     "impact": impact.group(1).capitalize() if impact else "",
                     "previous": cells[2].strip(), "forecast": cells[3].strip(), "actual": cells[4].strip()})
    return pd.DataFrame(rows, columns=COLUMNS[:-1])


def fetch_events() -> pd.DataFrame:
    ff = requests.get(FF_URL, headers=HEADERS, timeout=30)
    ff.raise_for_status()
    mf = requests.get(MYFXBOOK_URL, headers=HEADERS, timeout=30)
    mf.raise_for_status()
    parsed = parse_myfxbook(mf.text)
    if parsed.empty:
        raise ValueError("Myfxbook-Feed ohne G8-Termine: Format geaendert?")
    return pd.concat([parse_ff(ff.json()), parsed], ignore_index=True)


def append_events(new: pd.DataFrame, fetched_at: pd.Timestamp | None = None, data_dir: Path | None = None) -> int:
    """Archiviert nur Termine, die neu sind oder deren Werte sich geaendert haben.
    So bleibt der Konsens sichtbar, der vor dem Termin galt."""
    now = fetched_at if fetched_at is not None else pd.Timestamp.now("UTC").tz_localize(None)
    path = (data_dir or DATA_DIR) / "calendar.parquet"
    existing = pd.read_parquet(path) if path.exists() else pd.DataFrame(columns=COLUMNS)
    values = ["impact", "forecast", "previous", "actual"]
    last = existing.sort_values("fetched_at").drop_duplicates(KEY, keep="last") if len(existing) else existing
    merged = new.merge(last[KEY + values], on=KEY, how="left", suffixes=("", "_alt"), indicator=True)
    changed = (merged["_merge"] == "left_only") | (merged[values].astype(str).values != merged[[v + "_alt" for v in values]].astype(str).values).any(axis=1)
    rows = merged.loc[changed, KEY + values].assign(fetched_at=now)
    if rows.empty:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    out = pd.concat([existing, rows], ignore_index=True) if len(existing) else rows
    tmp = path.with_suffix(".tmp")
    out[COLUMNS].to_parquet(tmp, index=False)
    tmp.replace(path)
    return len(rows)


def surprises(events: pd.DataFrame) -> pd.DataFrame:
    """Ueberraschung = Ist - Konsens, je Termin aus dem letzten Stand. Der Konsens stammt
    aus dem letzten Abruf VOR dem ersten Ist, sonst koennte ein nachgezogener Wert zaehlen.
    Nur bei gleicher Einheit; Termine ohne Ist oder Konsens fallen weg."""
    rows = []
    mf = events[events["source"] == "myfxbook"].sort_values("fetched_at")
    for key, group in mf.groupby(KEY, sort=False):
        with_actual = group[group["actual"].astype(str).str.strip() != ""]
        if with_actual.empty:
            continue
        actual, actual_unit = parse_number(with_actual["actual"].iloc[-1])
        first_seen = with_actual["fetched_at"].iloc[0]
        before = group[group["fetched_at"] < first_seen]
        forecast_text = before["forecast"].iloc[-1] if len(before) else with_actual["forecast"].iloc[0]
        forecast, forecast_unit = parse_number(forecast_text)
        if actual is None or forecast is None or actual_unit != forecast_unit:
            continue
        rows.append({"currency": key[1], "title": key[2], "event_time": key[3], "impact": group["impact"].iloc[-1],
                     "forecast": forecast, "actual": actual, "surprise": actual - forecast,
                     "forecast_before_print": len(before) > 0})
    return pd.DataFrame(rows, columns=["currency", "title", "event_time", "impact", "forecast", "actual",
                                       "surprise", "forecast_before_print"])
