"""Geopolitik und News abseits des Kalenders (Makro-Agent v3, 12.11.2026).

Drei Ebenen, von hart zu weich:
- Geopolitical Risk Index (Caldara/Iacoviello), taeglich ab 1985, Verzug ~10 Tage -> MKT.gpr*.
  Zaehlt Zeitungsartikel zu Kriegs-/Terror-/Konfliktbegriffen; ACT = Handlungen, THREAT = Drohungen.
- GDELT DOC 2.0 (seit 12.11.2026 fuer unsere IP gesperrt, nicht im Tageslauf): Nachrichtenvolumen (Anteil aller Artikel) und Ton je Thema ab 2017 -> GEO.<thema>.vol/.tone.
  Die API erlaubt eine Anfrage je 5 s, darum Pause und Wiederholung.
- Google-News-RSS: Schlagzeilen der letzten 24 h je Thema, nur fuer die LLM-Einordnung (news_digest),
  nicht im Datenspeicher.
"""

from __future__ import annotations

import io
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import pandas as pd
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (macro research script)"}
GPR_URL = "https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls"
GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"
GNEWS_RSS = "https://news.google.com/rss/search"
GDELT_START = "20170101000000"
GDELT_PAUSE_S = 8
TIMEOUT = 90

# Themen: GDELT-Abfrage (Englisch, wie die meisten Quellen) und Google-News-Suche.
THEMES = {
    "iran_hormuz": {"name": "Iran / Hormuz",
                    "gdelt": '(iran OR hormuz) (oil OR strike OR missile OR tanker OR ceasefire)',
                    "news": "Iran Hormuz oil"},
    "zoelle_trump": {"name": "Zölle / Trump-Handel",
                     "gdelt": '(tariff OR tariffs) (trump OR "white house")',
                     "news": "Trump tariffs"},
    "ukraine_russland": {"name": "Ukraine / Russland",
                         "gdelt": '(ukraine OR russia) (ceasefire OR offensive OR "peace talks" OR gas)',
                         "news": "Ukraine Russia ceasefire talks"},
    "china_taiwan": {"name": "China / Taiwan",
                     "gdelt": '(china OR taiwan OR beijing) (military OR sanctions OR "export controls")',
                     "news": "China Taiwan sanctions export controls"},
    "fed_unabhaengigkeit": {"name": "US-Haushalt / Druck auf die Fed",
                            "gdelt": '("federal reserve" OR powell OR treasury) (trump OR deficit OR "debt ceiling" OR shutdown)',
                            "news": "Trump Federal Reserve pressure deficit"},
}


def _long(key: str, s: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"key": key, "date": s.index, "value": s.values})


def parse_gpr(content: bytes) -> pd.DataFrame:
    df = pd.read_excel(io.BytesIO(content))
    df = df[pd.to_numeric(df["DAY"], errors="coerce").notna()]
    idx = pd.to_datetime(df["DAY"].astype(int).astype(str), format="%Y%m%d")
    out = []
    for key, col in {"MKT.gpr": "GPRD", "MKT.gpr_acts": "GPRD_ACT", "MKT.gpr_threats": "GPRD_THREAT"}.items():
        s = pd.Series(pd.to_numeric(df[col], errors="coerce").values, index=idx).dropna()
        out.append(_long(key, s))
    return pd.concat(out, ignore_index=True)


def fetch_gpr() -> pd.DataFrame:
    r = requests.get(GPR_URL, timeout=TIMEOUT, headers=HEADERS)
    r.raise_for_status()
    return parse_gpr(r.content)


def parse_gdelt(payload: dict) -> pd.Series:
    """Timeline-Antwort -> Tagesreihe (Datum ohne Uhrzeit)."""
    data = payload["timeline"][0]["data"]
    s = pd.Series({pd.Timestamp(d["date"][:8]): float(d["value"]) for d in data})
    return s.sort_index()


def _gdelt(query: str, mode: str, start: str, retries: int = 4) -> pd.Series:
    params = {"query": query, "mode": mode, "format": "json", "startdatetime": start,
              "enddatetime": pd.Timestamp.now("UTC").strftime("%Y%m%d%H%M%S")}
    wait = GDELT_PAUSE_S
    for attempt in range(retries):
        r = requests.get(GDELT_API, params=params, timeout=TIMEOUT, headers=HEADERS)
        if r.status_code == 429 or not r.text.lstrip().startswith("{"):
            time.sleep(wait)
            wait *= 2
            continue
        r.raise_for_status()
        return parse_gdelt(r.json())
    raise RuntimeError(f"GDELT antwortet nicht ({r.status_code}): {r.text[:120]}")


def fetch_gdelt(start: str | None = None) -> pd.DataFrame:
    """Volumen (timelinevol = Anteil an allen Artikeln in %) und Ton je Thema.
    Taeglich reichen 60 Tage; die volle Historie laedt man einmalig mit start=GDELT_START."""
    start = start or (pd.Timestamp.now("UTC") - pd.Timedelta(days=60)).strftime("%Y%m%d000000")
    out = []
    for theme, spec in THEMES.items():
        for mode, suffix in (("timelinevol", "vol"), ("timelinetone", "tone")):
            out.append(_long(f"GEO.{theme}.{suffix}", _gdelt(spec["gdelt"], mode, start)))
            time.sleep(GDELT_PAUSE_S)
    return pd.concat(out, ignore_index=True)


def count_rss(text: str) -> int:
    return sum(1 for _ in ET.fromstring(text).iter("item"))


def parse_rss(text: str, limit: int = 12) -> list[dict]:
    root = ET.fromstring(text)
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        source = (item.findtext("source") or "").strip()
        if source and title.endswith(" - " + source):
            title = title[: -len(source) - 3]
        pub = item.findtext("pubDate")
        items.append({"titel": title, "quelle": source,
                      "zeit": parsedate_to_datetime(pub).astimezone().strftime("%Y-%m-%d %H:%M") if pub else "",
                      "link": item.findtext("link") or ""})
    items.sort(key=lambda x: x["zeit"], reverse=True)
    return items[:limit]


def fetch_headlines(hours: int = 24, counts: dict | None = None) -> dict[str, list[dict]]:
    """Schlagzeilen je Thema; counts (falls uebergeben) bekommt die Trefferzahl je Thema (max. 100,
    Google begrenzt) als Intensitaetsmass, das ab 12.11.2026 taeglich mitgeschrieben wird."""
    out = {}
    for theme, spec in THEMES.items():
        q = f"{spec['news']} when:{max(1, hours // 24)}d"
        r = requests.get(GNEWS_RSS, params={"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"},
                         timeout=30, headers=HEADERS)
        r.raise_for_status()
        out[theme] = parse_rss(r.text)
        if counts is not None:
            counts[theme] = count_rss(r.text)
    return out
