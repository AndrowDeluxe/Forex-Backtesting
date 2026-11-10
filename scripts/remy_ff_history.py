"""ForexFactory-Kalenderhistorie (Ist, Konsens, Vorwert) fuer den Remy-King-Test A3.

    python -m scripts.remy_ff_history [--start 2007-01-01]

Eine Wochenseite je Abruf, 3 s Pause, jede Woche als eigene Datei gecacht (wiederaufnehmbar).
Die Seite liefert die Termine als eingebettetes JSON (`calendarComponentStates[1].days`);
`dateline` ist ein Unix-Zeitstempel (UTC). Ergebnis: `data_cache/remy/ff_calendar.parquet`.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import pandas as pd
import requests

URL = "https://www.forexfactory.com/calendar"
HEADERS = {"User-Agent": "Mozilla/5.0 research-script"}
CACHE = Path("data_cache/remy/ff_weeks")
OUT = Path("data_cache/remy/ff_calendar.parquet")
G8 = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD"}
PAUSE_S = 3


def week_param(monday: pd.Timestamp) -> str:
    """FF erwartet den Sonntag der Woche, z. B. jan6.2019."""
    sunday = monday - pd.Timedelta(days=1)
    return f"{sunday.strftime('%b').lower()}{sunday.day}.{sunday.year}"


def parse_week(html: str) -> pd.DataFrame:
    m = re.search(r"calendarComponentStates\[1\]\s*=\s*\{\s*days:\s*(\[.*?\])\s*,\s*\n", html, re.S)
    if not m:
        raise ValueError("kein Kalender-JSON gefunden")
    rows = []
    for day in json.loads(m.group(1)):
        for e in day["events"]:
            rows.append({"ts": e.get("dateline"), "currency": e.get("currency"), "name": e.get("name"),
                         "impact": e.get("impactName"), "actual": e.get("actual"),
                         "forecast": e.get("forecast"), "previous": e.get("previous"),
                         "revision": e.get("revision"), "ebase_id": e.get("ebaseId")})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["time"] = pd.to_datetime(df["ts"], unit="s", utc=True)
    return df[df["currency"].isin(G8)].drop(columns="ts")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2007-01-01")
    args = ap.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    mondays = pd.date_range(args.start, pd.Timestamp.today().normalize() - pd.Timedelta(days=7), freq="W-MON")
    for i, monday in enumerate(mondays):
        f = CACHE / f"{monday.date()}.parquet"
        if f.exists():
            continue
        for attempt in range(3):
            r = requests.get(URL, params={"week": week_param(monday)}, headers=HEADERS, timeout=60)
            if r.status_code == 200 and "calendarComponentStates" in r.text:
                break
            time.sleep(30 * (attempt + 1))
        else:
            raise RuntimeError(f"{monday.date()}: HTTP {r.status_code} -- Abbruch (keine Umgehung)")
        parse_week(r.text).to_parquet(f, index=False)
        if i % 50 == 0:
            print(monday.date(), flush=True)
        time.sleep(PAUSE_S)
    df = pd.concat([pd.read_parquet(p) for p in sorted(CACHE.glob("*.parquet"))], ignore_index=True)
    df = df.drop_duplicates(["time", "currency", "name"]).sort_values("time")
    df.to_parquet(OUT, index=False)
    print(len(df), df["time"].min(), df["time"].max())


if __name__ == "__main__":
    main()
