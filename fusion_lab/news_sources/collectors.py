"""Sammler je Quelle. Jeder liefert {"status", "grund", "items" | "werte"} und erfindet nie Ersatzwerte.

status: "ok" | "nicht konfiguriert" (Key fehlt) | "blockiert" (HTTP 401/403/429) | "fehler" (sonst)
items:  Texteintraege {"symbol", "gruppe", "quelle", "titel", "zeit", "link"} fuer die Claude-Einordnung
werte:  Zahlen {"symbol", "quelle", "roh", "wert" (-1..+1), "n"} direkt fuers Ledger
"""

from __future__ import annotations

import datetime as dt
import tomllib
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

from fusion_lab.macro_data.geo import GNEWS_RSS, parse_rss
from fusion_lab.news_sources import config as C

SECRETS = C.REPO / ".streamlit" / "secrets.toml"


def secrets() -> dict:
    """Abschnitt [news_sources] aus .streamlit/secrets.toml; fehlt er, leeres dict (Quellen: nicht konfiguriert)."""
    try:
        return tomllib.loads(SECRETS.read_text(encoding="utf-8")).get("news_sources", {}) or {}
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _result(status: str = "ok", grund: str = "", **kw) -> dict:
    return {"status": status, "grund": grund, **kw}


def _fail(exc: Exception) -> dict:
    code = getattr(getattr(exc, "response", None), "status_code", None)
    if code in (401, 403, 429):
        return _result("blockiert", f"HTTP {code}")
    return _result("fehler", f"{type(exc).__name__}: {str(exc)[:120]}")


def _get(url: str, **kw) -> requests.Response:
    r = requests.get(url, headers=kw.pop("headers", C.UA), timeout=C.TIMEOUT, **kw)
    r.raise_for_status()
    return r


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _clip(x: float) -> float:
    return max(-1.0, min(1.0, x))


# ------------------------------------------------------------------ Text: news
def google_news(symbols: list[str]) -> dict:
    items, errors = [], []
    for s in symbols:
        q = f"{C.UNIVERSE[s]['news']} when:{max(1, C.NEWS_HOURS // 24)}d"
        try:
            r = _get(GNEWS_RSS, params={"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"})
            for h in parse_rss(r.text, limit=C.NEWS_LIMIT):
                items.append({"symbol": s, "gruppe": "news", "quelle": f"Google News: {h['quelle']}",
                              "titel": h["titel"], "zeit": h["zeit"], "link": h["link"]})
        except Exception as e:  # noqa: BLE001 - je Symbol weiter
            errors.append(f"{s}: {_fail(e)['grund']}")
    if errors and not items:
        return _result("fehler", "; ".join(errors[:3]), items=[])
    return _result("ok", f"{len(errors)} Symbole ohne Antwort" if errors else "", items=items)


def finnhub_news(symbols: list[str]) -> dict:
    key = secrets().get("finnhub_key")
    if not key:
        return _result("nicht konfiguriert", "finnhub_key fehlt in .streamlit/secrets.toml [news_sources]", items=[])
    to = _now().date()
    items = []
    try:
        for s in [x for x in symbols if C.UNIVERSE[x]["klasse"] == "aktien" and "cik" in C.UNIVERSE[x]]:
            r = _get("https://finnhub.io/api/v1/company-news",
                     params={"symbol": s, "from": str(to - dt.timedelta(days=2)), "to": str(to), "token": key})
            for n in r.json()[: C.NEWS_LIMIT]:
                items.append({"symbol": s, "gruppe": "news", "quelle": f"Finnhub: {n.get('source', '')}",
                              "titel": n.get("headline", ""), "link": n.get("url", ""),
                              "zeit": dt.datetime.fromtimestamp(n.get("datetime", 0)).strftime("%Y-%m-%d %H:%M")})
    except Exception as e:  # noqa: BLE001
        return _fail(e) | {"items": items}
    return _result(items=items)


# ------------------------------------------------------------------ Text: offiziell
def _rss_items(xml: bytes | str) -> list[dict]:
    """Bytes bevorzugt: die Fed-RSS beginnt mit einem BOM, das ET nur in Bytes korrekt behandelt."""
    root = ET.fromstring(xml)
    out = []
    for it in root.iter("item"):
        pub = it.findtext("pubDate")
        try:
            t = parsedate_to_datetime(pub) if pub else None
        except (TypeError, ValueError):
            t = None
        out.append({"titel": (it.findtext("title") or "").strip(), "link": (it.findtext("link") or "").strip(), "t": t})
    return out


def central_banks(symbols: list[str]) -> dict:
    cut = _now() - dt.timedelta(days=C.CB_DAYS)
    by_ccy, errors = {}, []
    for ccy, (name, url) in C.CENTRAL_BANKS.items():
        try:
            by_ccy[ccy] = [(name, x) for x in _rss_items(_get(url).content) if x["t"] and x["t"] >= cut]
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}: {_fail(e)['grund']}")
    items = []
    for s in symbols:
        for ccy in C.UNIVERSE[s].get("ccy", []):
            for name, x in by_ccy.get(ccy, []):
                items.append({"symbol": s, "gruppe": "offiziell", "quelle": name, "titel": x["titel"],
                              "zeit": x["t"].astimezone().strftime("%Y-%m-%d %H:%M"), "link": x["link"]})
    status = "fehler" if len(errors) == len(C.CENTRAL_BANKS) else "ok"
    return _result(status, "; ".join(errors), items=items)


def sec_edgar(symbols: list[str]) -> dict:
    cut = (_now() - dt.timedelta(days=C.EDGAR_DAYS)).date().isoformat()
    items = []
    try:
        for s in symbols:
            cik = C.UNIVERSE[s].get("cik")
            if not cik:
                continue
            rec = _get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json").json()["filings"]["recent"]
            for form, date, items_, doc, acc in zip(rec["form"], rec["filingDate"], rec.get("items", [""] * len(rec["form"])),
                                                    rec["primaryDocument"], rec["accessionNumber"]):
                if date < cut:
                    break
                if form not in C.EDGAR_FORMS:
                    continue
                link = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{doc}"
                items.append({"symbol": s, "gruppe": "offiziell", "quelle": "SEC EDGAR",
                              "titel": f"{form} filed {date}" + (f" (items {items_})" if items_ else ""),
                              "zeit": date, "link": link})
    except Exception as e:  # noqa: BLE001
        return _fail(e) | {"items": items}
    return _result(items=items)


# ------------------------------------------------------------------ Social
def stocktwits(symbols: list[str]) -> dict:
    """Bull/Bear-Anteil der letzten 30 Nachrichten (nur getaggte zaehlen) + Texte fuer Claude."""
    items, werte, errors = [], [], []
    for s in symbols:
        try:
            msgs = _get(f"https://api.stocktwits.com/api/2/streams/symbol/{C.UNIVERSE[s]['st']}.json").json().get("messages", [])
        except Exception as e:  # noqa: BLE001
            errors.append(f"{s}: {_fail(e)['grund']}")
            continue
        tags = [((m.get("entities") or {}).get("sentiment") or {}).get("basic") for m in msgs]
        bull, bear = tags.count("Bullish"), tags.count("Bearish")
        n = bull + bear
        werte.append({"symbol": s, "quelle": "stocktwits", "roh": f"{bull}/{bear}",
                      "wert": round((bull - bear) / n, 3) if n >= 3 else None, "n": n})
        for m in msgs[: C.SOCIAL_LIMIT]:
            items.append({"symbol": s, "gruppe": "social", "quelle": "StockTwits", "titel": (m.get("body") or "")[:240],
                          "zeit": (m.get("created_at") or "")[:16].replace("T", " "),
                          "link": f"https://stocktwits.com/message/{m.get('id')}"})
    if errors and not werte:
        return _result("blockiert" if any("HTTP 4" in e for e in errors) else "fehler", "; ".join(errors[:3]),
                       items=[], werte=[])
    return _result("ok", "; ".join(errors[:3]), items=items, werte=werte)


def reddit(symbols: list[str]) -> dict:
    sec = secrets()
    cid, csec = sec.get("reddit_client_id"), sec.get("reddit_client_secret")
    if not (cid and csec):
        return _result("nicht konfiguriert", "reddit_client_id/secret fehlen (ohne Login blockt Reddit mit 403)", items=[])
    ua = {"User-Agent": "news-sources research script (read-only)"}
    try:
        tok = requests.post("https://www.reddit.com/api/v1/access_token", auth=(cid, csec),
                            data={"grant_type": "client_credentials"}, headers=ua, timeout=C.TIMEOUT)
        tok.raise_for_status()
        hdr = ua | {"Authorization": f"bearer {tok.json()['access_token']}"}
        items = []
        for s in symbols:
            u = C.UNIVERSE[s]
            q = u["news"].split()[0] if u["klasse"] != "fx" else s
            for sub in u["subs"][:2]:
                r = _get(f"https://oauth.reddit.com/r/{sub}/search", headers=hdr,
                         params={"q": q, "restrict_sr": 1, "sort": "new", "t": "day", "limit": 5})
                for p in r.json().get("data", {}).get("children", []):
                    d = p["data"]
                    items.append({"symbol": s, "gruppe": "social", "quelle": f"Reddit r/{sub}", "titel": d.get("title", "")[:240],
                                  "zeit": dt.datetime.fromtimestamp(d.get("created_utc", 0)).strftime("%Y-%m-%d %H:%M"),
                                  "link": "https://www.reddit.com" + d.get("permalink", "")})
    except Exception as e:  # noqa: BLE001
        return _fail(e) | {"items": []}
    return _result(items=items)


# ------------------------------------------------------------------ Zahlen
def cnn_fear_greed(symbols: list[str]) -> dict:
    try:
        d = _get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata").json()
    except Exception as e:  # noqa: BLE001
        return _fail(e) | {"werte": []}
    fg, pc = d["fear_and_greed"], d.get("put_call_options") or {}
    werte = [{"symbol": C.MARKET_WIDE["cnn_fear_greed"], "quelle": "cnn_fear_greed", "roh": round(fg["score"], 1),
              "wert": round(_clip((fg["score"] - 50) / 50), 3), "n": 1}]
    if pc.get("score") is not None:
        werte.append({"symbol": C.MARKET_WIDE["cnn_put_call"], "quelle": "cnn_put_call", "roh": round(pc["score"], 1),
                      "wert": round(_clip((pc["score"] - 50) / 50), 3), "n": 1})
    return _result(grund=f"{fg['rating']} ({fg['score']:.0f})", werte=werte)


def krypto_fear_greed(symbols: list[str]) -> dict:
    try:
        v = int(_get("https://api.alternative.me/fng/?limit=1").json()["data"][0]["value"])
    except Exception as e:  # noqa: BLE001
        return _fail(e) | {"werte": []}
    return _result(werte=[{"symbol": C.MARKET_WIDE["krypto_fear_greed"], "quelle": "krypto_fear_greed", "roh": v,
                           "wert": round(_clip((v - 50) / 50), 3), "n": 1}])


def alphavantage(symbols: list[str]) -> dict:
    """News-Sentiment je Ticker (relevanzgewichtet). Ein Aufruf je Symbol, Limit 25/Tag -> nur Tageslauf."""
    key = secrets().get("alphavantage_key")
    if not key:
        return _result("nicht konfiguriert", "alphavantage_key fehlt in .streamlit/secrets.toml [news_sources]", werte=[])
    werte, notes = [], []
    since = (_now() - dt.timedelta(hours=C.NEWS_HOURS)).strftime("%Y%m%dT%H%M")
    for s in symbols:
        tick = C.UNIVERSE[s]["av"]
        try:
            d = _get("https://www.alphavantage.co/query",
                     params={"function": "NEWS_SENTIMENT", "tickers": tick, "time_from": since, "limit": 50, "apikey": key}).json()
        except Exception as e:  # noqa: BLE001
            notes.append(f"{s}: {_fail(e)['grund']}")
            continue
        if "feed" not in d:  # Limit erreicht oder Fehlermeldung im JSON
            notes.append(f"{s}: {str(d.get('Information') or d.get('Note') or d)[:80]}")
            if "rate limit" in str(d).lower() or "25 requests" in str(d).lower():
                break
            continue
        num = den = 0.0
        for art in d["feed"]:
            for ts in art.get("ticker_sentiment", []):
                if ts.get("ticker") == tick:
                    w = float(ts.get("relevance_score", 0))
                    num += w * float(ts.get("ticker_sentiment_score", 0))
                    den += w
        n = len(d["feed"])
        werte.append({"symbol": s, "quelle": "alphavantage", "roh": round(num / den, 4) if den else None,
                      "wert": round(_clip(num / den / C.AV_SCALE), 3) if den else None, "n": n})
    status = "ok" if werte else ("blockiert" if notes else "fehler")
    return _result(status, "; ".join(notes[:3]), werte=werte)


TEXT_SOURCES = {"google_news": google_news, "finnhub": finnhub_news, "zentralbanken": central_banks,
                "sec_edgar": sec_edgar, "stocktwits": stocktwits, "reddit": reddit}
NUMBER_SOURCES = {"cnn_fear_greed": cnn_fear_greed, "krypto_fear_greed": krypto_fear_greed,
                  "alphavantage": alphavantage}


def collect(symbols: list[str], daily: bool = False) -> dict:
    """Alle Quellen fuer die Symbole. daily=False laesst Quellen mit Tageslimit aus (Status 'nur Tageslauf')."""
    out = {}
    for name, fn in {**TEXT_SOURCES, **NUMBER_SOURCES}.items():
        if name in C.DAILY_ONLY and not daily:
            out[name] = _result("nur Tageslauf", "Abfragelimit: nur im taeglichen Task", items=[], werte=[])
            continue
        try:
            out[name] = fn(symbols)
        except Exception as e:  # noqa: BLE001 - eine kaputte Quelle stoppt nie den Lauf
            out[name] = _fail(e)
        out[name].setdefault("items", [])
        out[name].setdefault("werte", [])
    return out
