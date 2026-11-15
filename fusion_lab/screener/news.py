"""Schlagzeilen je Firma/Coin ueber Google-News-RSS (frei). Parser aus fusion_lab/macro_data/geo.py."""

from __future__ import annotations

import re

import requests

from fusion_lab.macro_data.geo import GNEWS_RSS, parse_rss
from fusion_lab.screener import config as C

HEADERS = {"User-Agent": "Mozilla/5.0 (screener; research)"}
_SUFFIX = re.compile(r"\b(Inc\.?|Incorporated|Corporation|Corp\.?|Company|Co\.?|plc|Ltd\.?|Holdings?|Group|"
                     r"\(Class [A-Z]\)|Class [A-Z]|N\.V\.|S\.A\.|SE|AG)\b", re.I)


def clean_name(name: str) -> str:
    n = _SUFFIX.sub("", name or "").replace(",", " ")
    return re.sub(r"\s+", " ", n).strip()


def query_stock(ticker: str, name: str) -> str:
    return f'("{clean_name(name)}" OR {ticker}) stock'


def query_crypto(symbol: str, name: str) -> str:
    return f'("{clean_name(name)}" OR {symbol}) crypto'


def headlines(query: str, hours: int = C.NEWS_HOURS, limit: int = C.NEWS_LIMIT) -> list[dict]:
    q = f"{query} when:{max(1, hours // 24)}d"
    try:
        r = requests.get(GNEWS_RSS, params={"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"},
                         timeout=30, headers=HEADERS)
        r.raise_for_status()
        return parse_rss(r.text, limit=limit)
    except (requests.RequestException, Exception):  # RSS kaputt/leer -> keine Schlagzeilen, Lauf geht weiter
        return []
