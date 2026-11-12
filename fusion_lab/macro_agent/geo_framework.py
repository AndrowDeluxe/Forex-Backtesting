"""Geopolitisches Framework (Makro-Agent v3, 12.11.2026): Wie stark reagiert welches Asset auf welchen Treiber?

Treiber (Wochenaenderung): Brent, US-Realzins 10J, US-2J, Breakeven 10J, Dollar-Index, VIX,
Geopolitik-Index (GPR), Unsicherheitsindex (EPU). Assets: Gold, Silber, Kupfer, Indizes, FX.

Exposure-Matrix = Einfach-Regression der Wochenrendite eines Assets auf die Wochenaenderung eines
Treibers, angegeben als Wirkung eines festen Schocks ("Brent +10 % -> Gold x %"). Drei Fenster:
IS 2007-2016, OOS 2017-05/2026, heute (letzte 26 Wochen). Wochen statt Tage, weil Nikkei/DAX vor
dem US-Schluss schliessen (sonst misst man Zeitzonen statt Wirkung).

Status je Paar Asset x Treiber:
- "belegt":  gleiches Vorzeichen in IS, OOS und heute, |t| >= 2 in IS und OOS
- "gekippt": IS und OOS belegt, heute anderes Vorzeichen (Regime hat gedreht)
- "regime":  nur im aktuellen Fenster deutlich (|t| >= 2), historisch nicht stabil
- "schwach": sonst
Das ist Beschreibung, kein Signal: Es sagt, was passiert WENN der Treiber sich bewegt, nicht ob.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data_cache" / "geo" / "history.parquet"
IS = ("2007-01-01", "2016-12-31")
OOS = ("2017-01-01", "2026-05-10")
NOW_WEEKS = 26
T_MIN = 2.0

YF = {"gold": "GC=F", "silber": "SI=F", "kupfer": "HG=F", "brent": "BZ=F", "spx": "^GSPC", "ndx": "^NDX",
      "dax": "^GDAXI", "nikkei": "^N225", "dxy": "DX-Y.NYB"}
FRED = {"real_10y": "DFII10", "us_2y": "DGS2", "breakeven_10y": "T10YIE", "vix": "VIXCLS", "fed_funds": "DFF",
        "epu": "USEPUINDXD"}
CROSSES = {"EURJPY": ("EURUSD", "USDJPY", "*"), "GBPJPY": ("GBPUSD", "USDJPY", "*"),
           "AUDJPY": ("AUDUSD", "USDJPY", "*"), "CADJPY": ("USDJPY", "USDCAD", "/"),
           "EURGBP": ("EURUSD", "GBPUSD", "/"), "EURCHF": ("EURUSD", "USDCHF", "*"),
           "AUDNZD": ("AUDUSD", "NZDUSD", "/")}

# Treiber: Spalte, Art der Aenderung, Schockgroesse, Beschriftung
DRIVERS = {
    "brent": ("brent", "log", np.log(1.10), "Brent +10 %"),
    "realzins": ("real_10y", "bp", 25.0, "US-Realzins 10J +25 bp"),
    "us_2y": ("us_2y", "bp", 25.0, "US-2J +25 bp"),
    "breakeven": ("breakeven_10y", "bp", 25.0, "Inflationserwartung 10J +25 bp"),
    "dollar": ("dxy", "log", np.log(1.02), "Dollar-Index +2 %"),
    "vix": ("vix", "diff", 5.0, "VIX +5 Punkte"),
    "gpr": ("gpr", "logmean", np.log(1.5), "Geopolitik-Index +50 %"),
    "epu": ("epu", "logmean", np.log(1.5), "Unsicherheitsindex +50 %"),
}
ASSETS = ["gold", "silber", "kupfer", "brent", "spx", "ndx", "dax", "nikkei",
          "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY",
          "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "EURGBP", "EURCHF", "AUDNZD"]
ASSET_NAMES = {"gold": "Gold", "silber": "Silber", "kupfer": "Kupfer", "brent": "Brent", "spx": "S&P 500",
               "ndx": "Nasdaq 100", "dax": "DAX", "nikkei": "Nikkei"}


def _fred(series: str) -> pd.Series:
    from fusion_lab.macro_data.sources import FRED_API, _fred_key
    r = requests.get(FRED_API, params={"series_id": series, "api_key": _fred_key(), "file_type": "json",
                                       "observation_start": "2003-01-01"}, timeout=90)
    r.raise_for_status()
    obs = pd.DataFrame(r.json()["observations"])
    return pd.Series(pd.to_numeric(obs["value"], errors="coerce").values, index=pd.to_datetime(obs["date"])).dropna()


def _fx() -> pd.DataFrame:
    """D1-Schluesse 2003 bis heute: Cache-Dateien der Remy-Studien + Dukascopy-Tageswerte aus dem Speicher."""
    from fusion_lab.macro_data import store
    from scripts.remy_common import fx_closes
    fx = fx_closes()
    live = store.latest("markets")
    live = live[live["key"].str.startswith("FX.")]
    if len(live):
        w = live.assign(pair=live["key"].str[3:]).pivot_table(index="date", columns="pair", values="value")
        w = w[[c for c in fx.columns if c in w.columns]]
        fx = pd.concat([fx, w[w.index > fx.index.max()]]).sort_index()
    for name, (a, b, op) in CROSSES.items():
        fx[name] = fx[a] * fx[b] if op == "*" else fx[a] / fx[b]
    return fx


def build_history() -> pd.DataFrame:
    import yfinance as yf
    from fusion_lab.macro_data import store
    cols = {}
    for name, symbol in YF.items():
        d = yf.download(symbol, start="2003-01-01", progress=False, auto_adjust=True)["Close"]
        s = (d.iloc[:, 0] if isinstance(d, pd.DataFrame) else d).dropna()
        s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
        cols[name] = s
    for name, series in FRED.items():
        cols[name] = _fred(series)
    gpr = store.latest("markets")
    gpr = gpr[gpr["key"] == "MKT.gpr"]
    cols["gpr"] = pd.Series(gpr["value"].values, index=pd.to_datetime(gpr["date"].values))
    df = pd.DataFrame(cols)
    fx = _fx()
    return df.join(fx, how="outer").sort_index()


def history(refresh: bool = False) -> pd.DataFrame:
    """Tageswerte aller Treiber und Assets; Cache wird einmal je Kalendertag erneuert."""
    fresh = CACHE.exists() and pd.Timestamp(CACHE.stat().st_mtime, unit="s").date() == pd.Timestamp.now().date()
    if fresh and not refresh:
        return pd.read_parquet(CACHE)
    df = build_history()
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(CACHE)
    return df


def weekly_changes(daily: pd.DataFrame) -> pd.DataFrame:
    """Freitagswerte -> Wochenaenderung je Spalte; Assets als Log-Rendite, Treiber nach ihrer Art."""
    last = daily.resample("W-FRI").last()
    mean = daily.resample("W-FRI").mean()
    out = {}
    for asset in ASSETS:
        if asset in last:
            out[asset] = np.log(last[asset]).diff()
    for name, (col, kind, _, _) in DRIVERS.items():
        if col not in daily:
            continue
        if kind == "log":
            out["T." + name] = np.log(last[col]).diff()
        elif kind == "bp":
            out["T." + name] = last[col].diff() * 100
        elif kind == "diff":
            out["T." + name] = last[col].diff()
        else:  # logmean: taeglich verrauschte Zaehl-Indizes ueber den Wochenschnitt
            out["T." + name] = np.log(mean[col]).diff()
    w = pd.DataFrame(out)
    # Zinsregime zu Wochenbeginn: Markt preist Anhebungen (2J ueber Fed Funds) oder Senkungen
    gap = (last["us_2y"] - last["fed_funds"]).shift(1) if {"us_2y", "fed_funds"} <= set(daily) else None
    if gap is not None:
        w["regime"] = np.where(gap > 0.25, "anhebungen", np.where(gap < -0.25, "senkungen", "neutral"))
    return w


def ols(y: pd.Series, x: pd.Series) -> tuple[float, float, int]:
    d = pd.concat([y, x], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    n = len(d)
    if n < 12 or d.iloc[:, 1].std() == 0:
        return np.nan, np.nan, n
    xv = d.iloc[:, 1] - d.iloc[:, 1].mean()
    yv = d.iloc[:, 0] - d.iloc[:, 0].mean()
    beta = float((xv * yv).sum() / (xv ** 2).sum())
    resid = yv - beta * xv
    se = np.sqrt((resid ** 2).sum() / (n - 2) / (xv ** 2).sum())
    return beta, float(beta / se) if se > 0 else np.nan, n


def _window(w: pd.DataFrame, start, end) -> pd.DataFrame:
    return w.loc[pd.Timestamp(start):pd.Timestamp(end)]


def status(t_is, t_oos, t_now, s_is, s_oos, s_now) -> str:
    stable = (abs(t_is) >= T_MIN and abs(t_oos) >= T_MIN and s_is == s_oos) if np.isfinite([t_is, t_oos]).all() else False
    if stable and s_now == s_is:
        return "belegt"
    if stable and s_now == -s_is and np.isfinite(t_now) and abs(t_now) >= 1.0:
        return "gekippt"
    if np.isfinite(t_now) and abs(t_now) >= T_MIN:
        return "regime"
    return "schwach"


def exposure(w: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    """Lange Tabelle: asset, treiber, wirkung_is/oos/heute in % je Schock, t je Fenster, status."""
    w = w.loc[:as_of]
    now = w.tail(NOW_WEEKS)
    rows = []
    for name, (_, _, shock, label) in DRIVERS.items():
        x = "T." + name
        if x not in w:
            continue
        for asset in ASSETS:
            if asset not in w or asset == DRIVERS[name][0]:
                continue
            res = {}
            for tag, frame in (("is", _window(w, *IS)), ("oos", _window(w, *OOS)), ("heute", now)):
                beta, t, n = ols(frame[asset], frame[x])
                res[f"wirkung_{tag}"] = round(100 * (np.exp(beta * shock) - 1), 2) if np.isfinite(beta) else np.nan
                res[f"t_{tag}"] = round(t, 1) if np.isfinite(t) else np.nan
            sign = {k: np.sign(res[f"wirkung_{k}"]) for k in ("is", "oos", "heute")}
            rows.append({"asset": asset, "treiber": name, "schock": label, **res,
                         "status": status(res["t_is"], res["t_oos"], res["t_heute"], sign["is"], sign["oos"],
                                          sign["heute"])})
    return pd.DataFrame(rows)


def conditional(w: pd.DataFrame, asset: str, driver: str, end: str = OOS[1]) -> dict:
    """Wirkung getrennt nach Zinsregime (Markt preist Anhebungen / Senkungen), 2007 bis OOS-Ende."""
    shock = DRIVERS[driver][2]
    frame = w.loc[:pd.Timestamp(end)]
    out = {}
    for reg in ("anhebungen", "neutral", "senkungen"):
        f = frame[frame["regime"] == reg]
        beta, t, n = ols(f[asset], f["T." + driver])
        out[reg] = {"wirkung": round(100 * (np.exp(beta * shock) - 1), 2) if np.isfinite(beta) else None,
                    "t": round(t, 1) if np.isfinite(t) else None, "wochen": n}
    return out


def current_regime(daily: pd.DataFrame, as_of: pd.Timestamp) -> str:
    d = daily.loc[:as_of, ["us_2y", "fed_funds"]].dropna()
    if not len(d):
        return "n.v."
    gap = d["us_2y"].iloc[-1] - d["fed_funds"].iloc[-1]
    return "anhebungen" if gap > 0.25 else "senkungen" if gap < -0.25 else "neutral"


def label(asset: str) -> str:
    return ASSET_NAMES.get(asset, asset)


# --- Fact-Sheet-Block -------------------------------------------------------------------------------

# Thema -> Hauptkanal (Treiber) und Vorzeichen bei Eskalation. Belegt ist nur der Schritt Treiber -> Asset
# (Exposure-Matrix); der Schritt Thema -> Treiber ist Annahme und steht als solche im Fact Sheet.
THEME_CHANNELS = {
    "iran_hormuz": {"treiber": "brent", "eskalation": +1,
                    "weg": "Angriffe/Sperre Hormuz -> Ölangebot -> Brent; 2026 weiter über Fed-Erwartung -> Realzins"},
    "zoelle_trump": {"treiber": "breakeven", "eskalation": +1,
                     "weg": "Zölle -> US-Importpreise (90 % weitergegeben, NY Fed) -> Inflationserwartung; "
                            "Dollar-Richtung uneinheitlich (2025 fiel er)"},
    "ukraine_russland": {"treiber": "gpr", "eskalation": +1,
                         "weg": "Angriffe auf Energie -> Europa-Gas (TTF, ohne freie Historie) -> EUR, DAX"},
    "china_taiwan": {"treiber": "vix", "eskalation": +1,
                     "weg": "Sanktionen/Exportkontrollen -> Risikoappetit, Chips -> Nasdaq, Kupfer, AUD"},
    "fed_unabhaengigkeit": {"treiber": "breakeven", "eskalation": +1,
                            "weg": "Druck auf die Fed -> Glaubwürdigkeit -> Inflationserwartung hoch, Dollar schwach, Gold hoch"},
}
SHOW = ["gold", "silber", "kupfer", "spx", "ndx", "dax", "nikkei", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD",
        "USDCAD", "USDCHF"]
SHOW_DRIVERS = ["brent", "realzins", "us_2y", "breakeven", "dollar", "vix", "gpr"]
EVENTS_FILE = ROOT / "fusion_lab" / "data" / "macro_agent" / "geo_events.json"
SEASON_FILE = ROOT / "fusion_lab" / "data" / "macro_agent" / "earnings_season.json"


def _r(v, n=2):
    return None if v is None or not np.isfinite(v) else round(float(v), n)


def real_rates(macro_w: pd.DataFrame) -> dict:
    """US-Realzinsen aus TIPS (FRED) + Naeherung je Land 2J minus Kern-Inflation (ex post)."""
    def last(key, n=5):
        s = macro_w[key].dropna() if key in macro_w else pd.Series(dtype=float)
        if s.empty:
            return None
        chg = (s.iloc[-1] - s.iloc[-1 - n]) * 100 if len(s) > n else None
        return {"wert": _r(s.iloc[-1]), "datum": s.index[-1].date().isoformat(), "chg_5d_bp": _r(chg, 1)}
    us = {k: last(f"US.{k}") for k in ("real_10y", "real_5y", "breakeven_10y", "breakeven_5y", "fwd_5y5y")}
    proxy = {}
    from fusion_lab.macro_data.sources import G8
    for land in G8:
        y2, core = (macro_w.get(f"{land}.{q}") for q in ("2y", "core_yoy"))
        if y2 is None or core is None or y2.dropna().empty or core.dropna().empty:
            proxy[land] = None
            continue
        proxy[land] = _r(y2.dropna().iloc[-1] - core.dropna().iloc[-1])
    return {"us": us, "naeherung_2j_minus_kern": proxy}


def oil_passthrough(w: pd.DataFrame, as_of: pd.Timestamp) -> dict:
    """Wie stark hebt Brent +10 % die US-2J-Rendite und den Realzins (bp)? Entscheidet, ob Öl Gold
    drückt (Fed-Kanal) oder stützt (Inflationsschutz-Kanal)."""
    w = w.loc[:as_of]
    out = {}
    for target in ("us_2y", "realzins", "breakeven"):
        node = {}
        for tag, frame in (("is", _window(w, *IS)), ("oos", _window(w, *OOS)), ("heute", w.tail(NOW_WEEKS))):
            beta, t, _ = ols(frame["T." + target], frame["T.brent"])
            node[tag] = {"bp": _r(beta * np.log(1.10), 1), "t": _r(t, 1)}
        out[target] = node
    y2 = out["us_2y"]
    ref = max(y2["is"]["bp"] or 0, y2["oos"]["bp"] or 0)
    fed = (y2["heute"]["bp"] or 0) >= 1.5 * ref and (y2["heute"]["t"] or 0) >= T_MIN
    gold_now, _, _ = ols(w.tail(NOW_WEEKS)["gold"], w.tail(NOW_WEEKS)["T.brent"])
    out["gold_heute_pct"] = _r(100 * (np.exp(gold_now * np.log(1.10)) - 1))
    out["fed_kanal"] = bool(fed)
    out["kanal"] = ("Fed-Kanal: Öl hebt die Fed-Erwartung stärker als früher, das drückt Gold" if fed
                    else "Inflationsschutz-Kanal: Öl hebt vor allem die Inflationserwartung, Gold leidet nicht")
    return out


def _gpr_state(daily: pd.DataFrame, as_of: pd.Timestamp) -> dict | None:
    s = daily["gpr"].loc[:as_of].dropna()
    if len(s) < 260:
        return None
    year = s.iloc[-260:]
    return {"wert": _r(s.iloc[-1], 0), "datum": s.index[-1].date().isoformat(), "mittel_30t": _r(s.iloc[-30:].mean(), 0),
            "perzentil_1j": _r((year < s.iloc[-1]).mean() * 100, 0)}


def _events_summary() -> dict | None:
    if not EVENTS_FILE.exists():
        return None
    import json
    ev = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    out = {}
    for stage, node in ev.items():
        res = pd.DataFrame(node["ergebnis"])
        top = res.loc[res["t"].abs().idxmax()]
        out[stage] = {"ereignisse": node["ereignisse"], "max_abs_t": _r(abs(top["t"]), 2),
                      "bei": f"{label(top['asset'])} Tag {int(top['tag'])}",
                      "signifikant": int((res["t"].abs() >= T_MIN).sum())}
    return out


def theme_cards(expo: pd.DataFrame, news: dict) -> list[dict]:
    cards = []
    lage = news.get("einordnung", {})
    for theme, ch in THEME_CHANNELS.items():
        from fusion_lab.macro_data.geo import THEMES
        sub = expo[(expo["treiber"] == ch["treiber"]) & expo["asset"].isin(SHOW)]
        effects = []
        for _, r in sub.iterrows():  # alle Assets, Status sagt, wie belastbar
            effects.append({"asset": label(r["asset"]), "wirkung_heute": _r(r["wirkung_heute"]),
                            "wirkung_oos": _r(r["wirkung_oos"]), "status": r["status"]})
        node = lage.get(theme, {})
        cards.append({"thema": theme, "name": THEMES[theme]["name"], "lage": node.get("lage", "n.v."),
                      "kernaussage": node.get("kernaussage", ""), "quellen": node.get("quellen", []),
                      "treffer_24h": news.get("treffer", {}).get(theme), "weg": ch["weg"],
                      "treiber": DRIVERS[ch["treiber"]][3], "einfluss": effects})
    return cards


def sheet_block(macro_w: pd.DataFrame, as_of: pd.Timestamp) -> dict:
    import json
    from fusion_lab.macro_data import earnings
    from . import news_digest
    daily = history()
    daily = daily.loc[:as_of]
    w = weekly_changes(daily)
    expo = exposure(w, as_of)
    news = news_digest.load(as_of)
    matrix = {}
    for drv in SHOW_DRIVERS:
        sub = expo[(expo["treiber"] == drv) & expo["asset"].isin(SHOW)].set_index("asset")
        matrix[drv] = {"schock": DRIVERS[drv][3],
                       "assets": {label(a): {"heute": _r(sub.at[a, "wirkung_heute"]), "oos": _r(sub.at[a, "wirkung_oos"]),
                                             "status": sub.at[a, "status"]} for a in SHOW if a in sub.index}}
    season = json.loads(SEASON_FILE.read_text(encoding="utf-8")) if SEASON_FILE.exists() else None
    if season and pd.Timestamp(season.get("stand", "2100-01-01")) > as_of:
        season = None  # Handdatei kennt nur den neuesten Stand
    er = earnings.load()
    mega = er.get("werte", []) if er and pd.Timestamp(er["stand"][:10]) <= as_of else []  # nur Lauf bis Stichtag
    return {
        "realzins": real_rates(macro_w),
        "zinsregime": current_regime(daily, as_of),
        "oel_durchgriff": oil_passthrough(w, as_of),
        "gold_oel_regime": conditional(w, "gold", "brent"),
        "gpr": _gpr_state(daily, as_of),
        "ereignisstudie": _events_summary(),
        "news_stand": news.get("datum"),
        "themen": theme_cards(expo, news),
        "exposure": matrix,
        "earnings": {"megacaps": mega, "saison": season},
    }
