"""EUR High-Impact-Release-Termine via Eurostats oeffentlichen iCalendar-Feed
(keylos, offiziell dokumentiert unter ec.europa.eu/eurostat/subscribe/
ics.format -- URL selbst per Playwright aus dem Theme/Kategorie-Dropdown auf
jener Seite ermittelt, 2026-08-12: theme=2 "Economy and finance",
category=2 "Euro indicator release"). Enthaelt u.a. HICP-Inflation
(Flash + final), GDP (Flash + final), Handelsbilanz, Immobilienpreisindex --
nicht nur die "grossen 2", aber alles unter derselben kuratierten
Eurostat-Kategorie.

Bekannte Luecke: kein EUR-PMI-Aequivalent (S&P-Global-eigene Daten, nicht bei
Eurostat). Cached als CSV unter data_cache/news_calendar/ (gitignored)."""

from pathlib import Path

import pandas as pd
import requests
from icalendar import Calendar

CACHE_DIR = Path(__file__).resolve().parents[1] / "data_cache" / "news_calendar"
EUROSTAT_ICAL_URL = "https://ec.europa.eu/eurostat/o/calendars/eventsIcal?theme=2&category=2"


def fetch_eur_release_dates(force_refresh: bool = False) -> pd.DataFrame:
    """DataFrame mit Spalten date/summary -- ALLE Termine, die der Feed liefert
    (typischerweise ca. 1 Jahr rueckwirkend + ca. 1 Jahr voraus, von Eurostat
    selbst so vorgehalten, nicht von uns waehlbar)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / "eurostat_release_calendar.csv"
    if cache_path.exists() and not force_refresh:
        return pd.read_csv(cache_path, parse_dates=["date"])

    r = requests.get(EUROSTAT_ICAL_URL, timeout=30)
    r.raise_for_status()
    cal = Calendar.from_ical(r.text)
    rows = [
        {"date": pd.Timestamp(c["dtstart"].dt), "summary": str(c.get("summary"))}
        for c in cal.walk() if c.name == "VEVENT"
    ]
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    df.to_csv(cache_path, index=False)
    return df


def fetch_eur_release_dates_filtered(keywords: tuple[str, ...] = ("inflation", "hicp", "gdp")) -> pd.DatetimeIndex:
    """Nur Termine, deren summary eines der keywords enthaelt (case-insensitive)
    -- Default: HICP/Inflation + GDP, die zwei Kernindikatoren analog zu den
    US-Releases. Andere Eurostat-Termine (Handelsbilanz, Immobilienpreise...)
    bewusst ausgeschlossen, um beim 'ganz simplen' Filter nicht zu viele Tage
    zu blockieren."""
    df = fetch_eur_release_dates()
    mask = df["summary"].str.lower().apply(lambda s: any(k in s for k in keywords))
    return pd.DatetimeIndex(sorted(df.loc[mask, "date"].dt.normalize().unique()))
