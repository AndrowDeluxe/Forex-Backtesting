"""Tageslauf Aktien bzw. Krypto: Daten -> Score -> Tiefen-Kandidaten (Szenarien + News + LLM) -> Bericht + Ledger."""

from __future__ import annotations

import glob
import json
import time
from datetime import datetime

import pandas as pd

from fusion_lab.screener import analyst, config as C, data_crypto, data_stocks, ledger, levels, news, scoring, universe

CHART_BARS = 180


def _tech(d: pd.DataFrame) -> dict:
    t = levels.technicals(d)
    s50 = levels.sma(d["Close"], 50)
    t["sma50_steigung"] = float(s50.iloc[-1] - s50.iloc[-21]) if len(s50.dropna()) > 21 else None
    return t


def _next(day: str | None, stand: str) -> str | None:
    """Nur kuenftige Quartalszahlen-Termine (Yahoo liefert nach dem Termin noch eine Weile den alten)."""
    return day if day and day >= stand else None


def _chart(d: pd.DataFrame) -> list[list]:
    x = d.iloc[-CHART_BARS:]
    return [[str(i.date()), *(round(float(v), 6) for v in r)] for i, r in
            zip(x.index, x[["Open", "High", "Low", "Close"]].to_numpy())]


def macro_context() -> dict | None:
    files = sorted(glob.glob(str(C.REPO / "fusion_lab" / "data" / "macro_agent" / "fact_sheet_*.json")))
    if not files:
        return None
    s = json.loads(open(files[-1], encoding="utf-8").read())
    z = s.get("zustand") or {}
    ind = {x["name"]: x["value"] for x in (z.get("tail") or [])}
    geo = [{"thema": t.get("thema"), "name": t.get("name"), "lage": t.get("lage"), "kernaussage": t.get("kernaussage")}
           for t in ((s.get("geopolitik") or {}).get("themen") or [])]
    md_path = files[-1][:-5] + ".md"
    md = open(md_path, encoding="utf-8").read() if glob.os.path.exists(md_path) else None
    return {"stand": s.get("stand"), "zustand": z.get("state"), "indikatoren": ind, "geopolitik": geo,
            "fact_sheet_md": md}


def _clean(x):
    """NaN -> None fuer JSON."""
    if isinstance(x, float) and pd.isna(x):
        return None
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_clean(v) for v in x]
    return x


def _finish(kind: str, stand: str, table: pd.DataFrame, deep: list[dict], context: dict, use_llm: bool,
            panel: dict, bench: str, write_ledger: bool) -> dict:
    table = table.sort_values("gesamt", ascending=False)
    report = {"screener": kind, "stand": stand, "erzeugt": datetime.now().isoformat(timespec="seconds"),
              "version": C.VERSION, "status": ledger.status(stand), "llm": use_llm,
              "schwellen": {"kaufen": C.BUY_THRESHOLD, "verkaufen": C.SELL_THRESHOLD,
                            "sentiment_gewicht": C.SENTIMENT_WEIGHT},
              "kontext": context, "anzahl": int(len(table)),
              "signale": table["signal"].value_counts().to_dict(),
              "tabelle": table.reset_index().to_dict(orient="records"), "tief": deep}
    if write_ledger:
        rows = []
        for c in deep:
            for sz in ("A", "B"):
                s = c["szenarien"].get(sz)
                if not s:
                    continue
                llm = c.get("llm") or {}
                rows.append({"erstellt": datetime.now().date().isoformat(), "stand": stand, "screener": kind,
                             "version": C.VERSION, "status": ledger.status(stand), "art": "szenario",
                             "objekt": c["objekt"], "szenario": sz, "gewaehlt": llm.get("szenario") == sz if llm and
                             "szenario" in llm else None, "score": c["gesamt"], "signal": c["signal"],
                             "sentiment": llm.get("sentiment"), "einstieg": s["einstieg"], "zone_lo": s.get("zone_lo"),
                             "zone_hi": s.get("zone_hi"), "stopp": s["stopp"], "ziel": s["ziel"], "rr": s["rr"]})
        groups = {"KAUFEN": table.index[table["signal"] == "KAUFEN"].tolist(),
                  "VERKAUFEN": table.index[table["signal"] == "VERKAUFEN"].tolist(),
                  "TOP10": table.index[:10].tolist()}
        for name, members in groups.items():
            for h in C.RANK_HORIZONS:
                rows.append({"erstellt": datetime.now().date().isoformat(), "stand": stand, "screener": kind,
                             "version": C.VERSION, "status": ledger.status(stand), "art": "gruppe", "objekt": name,
                             "horizont": h, "titel": ";".join(members)})
        report["ledger_neu"] = ledger.append(rows)
    report["ledger_ausgewertet"] = ledger.evaluate(panel, kind, bench)
    report["bilanz"] = ledger.summary()
    return _clean(report)


def _deep_entry(objekt: str, name: str, d: pd.DataFrame, tech: dict, comp: pd.Series, extra: dict,
                heads: list[dict], context_small: dict, use_llm: bool) -> dict:
    sc = levels.scenarios(d)
    pack = {"titel": objekt, "name": name, "stand": tech["datum"],
            "technik": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in tech.items()},
            "punktwerte": {k: comp[k] for k in comp.index
                           if k in C.WEIGHTS_STOCKS or k in C.WEIGHTS_CRYPTO or k == "kennzahlen_score"},
            "kennzahlen": extra,
            "szenarien": {k: sc[k] for k in ("A", "B", "C")}, "schlagzeilen": heads, "markt": context_small}
    llm = analyst.analyse(pack) if use_llm else None
    ok = llm and "fehler" not in llm
    gesamt = scoring.total(comp["kennzahlen_score"], llm["sentiment"] if ok else None)
    return {"objekt": objekt, "name": name, "kurs": tech["close"], "technik": pack["technik"],
            "punktwerte": pack["punktwerte"], "kennzahlen": extra, "szenarien": sc, "schlagzeilen": heads,
            "llm": llm, "gesamt": gesamt, "signal": scoring.signal(gesamt), "chart": _chart(d)}


# ------------------------------------------------------------------ Aktien

def run_stocks(use_llm: bool = True, write_ledger: bool = True, log=print) -> dict:
    t0 = time.time()
    u = universe.stocks().set_index("ticker")
    tickers = list(u.index)
    panel = data_stocks.prices(tickers + [C.STOCK_BENCHMARK])
    bench = panel.get(C.STOCK_BENCHMARK)
    stand = str(bench.index[-1].date())
    log(f"Kurse: {len(panel)} Reihen, Stand {stand} ({time.time() - t0:.0f} s)")
    tech = {t: _tech(d) for t, d in panel.items() if t != C.STOCK_BENCHMARK and len(d) >= 210}
    fund = data_stocks.fundamentals(list(tech))
    bt = levels.technicals(bench)
    comp = scoring.stocks(tech, fund, u["sektor"].to_dict(), bt.get("ret_63d"))
    comp["name"] = [fund.get(t, {}).get("shortName") or u.at[t, "name"] for t in comp.index]
    comp["sektor"] = [fund.get(t, {}).get("sector") or u.at[t, "sektor"] for t in comp.index]
    comp["kurs"] = [round(tech[t]["close"], 2) for t in comp.index]
    comp["ret_21d"] = [tech[t].get("ret_21d") for t in comp.index]
    comp["zahlen_am"] = [_next(data_stocks.earnings_date(fund.get(t, {})), stand) for t in comp.index]
    comp["gesamt"] = comp["kennzahlen_score"]
    comp["signal"] = comp["gesamt"].map(scoring.signal)

    ranked = comp.sort_values("kennzahlen_score", ascending=False)
    deep_names = list(dict.fromkeys(list(ranked.index[: C.N_DEEP_STOCKS]) +
                                    [t for t in C.WATCHLIST_STOCKS if t in comp.index]))
    fresh = data_stocks.fundamentals(deep_names, max_age_days=0.5)
    spy_trend = "über SMA200" if bt["close"] > (bt["sma200"] or 0) else "unter SMA200"
    mc = macro_context()
    ctx_small = {"spy_trend": spy_trend, "spy_ret_21d": bt.get("ret_21d"),
                 "makro_zustand": mc["zustand"] if mc else None}
    deep = []
    for t in deep_names:
        f = fresh.get(t, {})
        extra = {k: f.get(k) for k in ("marketCap", "forwardPE", "trailingPE", "trailingPegRatio", "grossMargins",
                                       "operatingMargins", "returnOnEquity", "revenueGrowth", "earningsGrowth",
                                       "debtToEquity", "freeCashflow", "totalRevenue", "targetMeanPrice",
                                       "recommendationKey", "numberOfAnalystOpinions", "shortPercentOfFloat", "beta")}
        extra["zahlen_am"] = _next(data_stocks.earnings_date(f), stand)
        extra["eps_revisionen_30t"] = data_stocks.eps_revisions(t)
        heads = news.headlines(news.query_stock(t, comp.at[t, "name"]))
        e = _deep_entry(t, comp.at[t, "name"], panel[t], tech[t], comp.loc[t], extra, heads, ctx_small, use_llm)
        comp.at[t, "gesamt"], comp.at[t, "signal"] = e["gesamt"], e["signal"]
        deep.append(e)
        log(f"  {t}: Score {e['gesamt']} {e['signal']}, LLM {'ok' if e['llm'] and 'fehler' not in e['llm'] else 'n.v.'}")
    context = {"benchmark": C.STOCK_BENCHMARK, "spy": {"kurs": bt["close"], "trend": spy_trend,
                                                       "ret_21d": bt.get("ret_21d"), "rsi14": bt.get("rsi14")},
               "makro": mc}
    if write_ledger:
        _seed_reference()
    return _finish("aktien", stand, comp, deep, context, use_llm, panel, C.STOCK_BENCHMARK, write_ledger)


def _seed_reference() -> None:
    """NVDA-Handanalyse 15.11.2026 (Stand 13.11.) einmalig als Referenz ins Ledger."""
    df = ledger.read()
    if ((df["art"] == "referenz") & (df["objekt"] == "NVDA")).any():
        return
    base = {"erstellt": "2026-11-15", "stand": "2026-11-13", "screener": "aktien", "version": "hand",
            "status": "referenz", "art": "referenz", "objekt": "NVDA", "score": None, "signal": None}
    ledger.append([base | {"szenario": "A", "einstieg": 153.5, "zone_lo": 149.0, "zone_hi": 158.0, "stopp": 145.0,
                           "ziel": 180.0, "rr": round((180 - 153.5) / (153.5 - 145), 2), "gewaehlt": None},
                   base | {"szenario": "B", "einstieg": 172.0, "stopp": 158.0, "ziel": 180.0,
                           "rr": round((180 - 172) / (172 - 158), 2), "gewaehlt": None}])


# ------------------------------------------------------------------ Krypto

def run_crypto(use_llm: bool = True, write_ledger: bool = True, log=print) -> dict:
    t0 = time.time()
    cg = universe.crypto().set_index("symbol")
    raw = data_crypto.prices(list(cg["pair"]))
    panel = {s: raw[p] for s, p in cg["pair"].items() if p in raw}
    stand = str(panel[C.CRYPTO_BENCHMARK].index[-1].date())
    log(f"Krypto: {len(panel)} Reihen, Stand {stand} ({time.time() - t0:.0f} s)")
    tech = {s: _tech(d) for s, d in panel.items()}
    fr = data_crypto.funding()
    comp = scoring.crypto(tech, cg, fr, C.CRYPTO_BENCHMARK)
    comp["name"] = [cg.at[s, "name"] for s in comp.index]
    comp["kurs"] = [tech[s]["close"] for s in comp.index]
    comp["ret_21d"] = [tech[s].get("ret_21d") for s in comp.index]
    comp["mcap_rang"] = [cg.at[s, "market_cap_rank"] for s in comp.index]
    comp["funding_pct"] = [round(fr[f"{s}USDT"] * 100, 4) if f"{s}USDT" in fr else None for s in comp.index]
    comp["gesamt"] = comp["kennzahlen_score"]
    comp["signal"] = comp["gesamt"].map(scoring.signal)

    fng = data_crypto.fear_greed()
    bt = tech[C.CRYPTO_BENCHMARK]
    btc_trend = "über SMA200" if bt["sma200"] and bt["close"] > bt["sma200"] else "unter SMA200"
    mc = macro_context()
    ctx_small = {"btc_trend": btc_trend, "fear_greed": fng, "makro_zustand": mc["zustand"] if mc else None}
    ranked = comp.sort_values("kennzahlen_score", ascending=False)
    deep_names = list(dict.fromkeys(list(ranked.index[: C.N_DEEP_CRYPTO]) +
                                    [s for s in C.CRYPTO_ALWAYS if s in comp.index]))
    deep = []
    for s in deep_names:
        g = cg.loc[s]
        extra = {"market_cap": g["market_cap"], "market_cap_rank": g["market_cap_rank"],
                 "volumen_24h": g["total_volume"], "umlauf": g["circulating_supply"],
                 "max_menge": g["max_supply"], "gesamtmenge": g["total_supply"], "ath": g["ath"],
                 "ath_abstand_pct": g["ath_change_percentage"], "ath_datum": str(g["ath_date"])[:10],
                 "funding_8h_pct": comp.at[s, "funding_pct"]}
        heads = news.headlines(news.query_crypto(s, g["name"]))
        e = _deep_entry(s, g["name"], panel[s], tech[s], comp.loc[s], extra, heads, ctx_small, use_llm)
        comp.at[s, "gesamt"], comp.at[s, "signal"] = e["gesamt"], e["signal"]
        deep.append(e)
        log(f"  {s}: Score {e['gesamt']} {e['signal']}, LLM {'ok' if e['llm'] and 'fehler' not in e['llm'] else 'n.v.'}")
    context = {"benchmark": C.CRYPTO_BENCHMARK, "btc": {"kurs": bt["close"], "trend": btc_trend,
                                                        "ret_21d": bt.get("ret_21d"), "rsi14": bt.get("rsi14")},
               "fear_greed": fng, "makro": mc}
    return _finish("krypto", stand, comp, deep, context, use_llm, panel, C.CRYPTO_BENCHMARK, write_ledger)
