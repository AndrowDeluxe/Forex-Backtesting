"""Wirkketten-Katalog (Meridian "Mechanismus-Register", Phase-2-Schritt 3, 12.11.2026).

Eine Kette = Ausloeser -> Schritte -> betroffene Assets, jeder Schritt mit messbarer Bedingung, dazu eine
Stopp-Bedingung und der Beleg-Status. Quelle der ersten vier Ketten: SMT-Report 21.10.
(knowledge/resources/makro-wirkketten-und-regeln.md §2); die anderen aus dem Geo-Framework und der Literatur.

Status je Lauf:
- "aktiv":     alle Schritte erfuellt, Stopp nicht erfuellt
- "anlaufend": erster Schritt erfuellt, spaetere noch nicht
- "gestoppt":  Stopp-Bedingung erfuellt
- "ruhend":    sonst
Beleg: "belegt" heisst, der letzte Schritt (Treiber -> Asset) ist in der Exposure-Matrix stabil
(gleiches Vorzeichen 2007-16, 2017-26, heute); die frueheren Schritte sind Annahmen, solange nicht anders
vermerkt. Aktive Ketten gehen als Aussage ins Forecast-Ledger (Asset-Richtung, 20 Handelstage).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

M = dict  # Messwerte: Name -> Zahl (None = fehlt)


@dataclass
class Step:
    text: str
    check: Callable[[M], bool | None]
    zeigt: str  # Messwert(e) fuer die Anzeige


@dataclass
class Chain:
    id: str
    name: str
    quelle: str
    schritte: list[Step]
    stopp: Step
    assets: dict[str, int]                      # Asset -> erwartete Richtung, wenn die Kette laeuft
    beleg: list[tuple[str, str]] = field(default_factory=list)  # (Asset, Treiber) in der Exposure-Matrix
    hinweis: str = ""


def _gt(name, x):
    return lambda m: None if m.get(name) is None else m[name] > x


def _lt(name, x):
    return lambda m: None if m.get(name) is None else m[name] < x


def _all(*fs):
    def f(m):
        vals = [g(m) for g in fs]
        return None if any(v is None for v in vals) else all(vals)
    return f


def _any(*fs):
    def f(m):
        vals = [g(m) for g in fs]
        return True if any(v is True for v in vals) else (None if any(v is None for v in vals) else False)
    return f


def _eq(name, x):
    return lambda m: None if m.get(name) is None else m[name] == x


CHAINS = [
    Chain("oel_fed_gold", "Ölschock → Fed-Erwartung → Realzins/Dollar → Gold schwach", "Geo-Framework 12.11.",
          [Step("Brent steigt (20 T > +5 %)", _gt("brent_20d", 5), "brent_20d"),
           Step("Öl greift auf die Fed-Erwartung durch (2J je Brent +10 % über früherem Niveau)",
                _eq("fed_kanal", True), "fed_kanal"),
           Step("US-2J steigt (20 T > +10 bp)", _gt("us_2y_20d_bp", 10), "us_2y_20d_bp")],
          Step("Brent fällt (20 T < −5 %) oder Fed-Kanal aus", _any(_lt("brent_20d", -5), _eq("fed_kanal", False)),
               "brent_20d"),
          {"gold": -1, "USDJPY": +1, "EURUSD": -1}, [("gold", "us_2y"), ("USDJPY", "us_2y"), ("EURUSD", "us_2y")],
          "Historisch hob Öl Gold (Inflationsschutz); nur bei Fed-Durchgriff negativ."),
    Chain("oel_cad", "Öl + Inflation → BoC-Erwartung → CAD stärker", "SMT 21.10.",
          [Step("Brent steigt (20 T > +3 %)", _gt("brent_20d", 3), "brent_20d"),
           Step("CA-Pricing steigt (1J − Leitzins, Woche > 0)", _gt("ca_pricing_1w_bp", 0), "ca_pricing_1w_bp")],
          Step("Brent fällt (20 T < −5 %)", _lt("brent_20d", -5), "brent_20d"),
          {"USDCAD": -1, "CADJPY": +1}, [("USDCAD", "brent")]),
    Chain("oel_importeure", "Öl hoch → Importeure (JPY, EUR) schwächer", "Lehrbuch (Terms of Trade)",
          [Step("Brent steigt (20 T > +5 %)", _gt("brent_20d", 5), "brent_20d")],
          Step("Brent fällt (20 T < −5 %)", _lt("brent_20d", -5), "brent_20d"),
          {"EURUSD": -1, "USDJPY": +1}, [("EURUSD", "brent"), ("USDJPY", "brent")],
          "Eigener Test: EURUSD/USDJPY reagieren auf Brent nicht stabil – eher Hypothese."),
    Chain("defizit_oat", "Defizit Frankreich → OAT-Bund-Spread → EUR nur gegen CHF/GBP schwach", "SMT 21.10.",
          [Step("OAT-Bund über 80 bp", _gt("oat_bund_bp", 80), "oat_bund_bp"),
           Step("Spread steigt (20 T > +10 bp)", _gt("oat_bund_20d_bp", 10), "oat_bund_20d_bp")],
          Step("Spread fällt (20 T < −10 bp)", _lt("oat_bund_20d_bp", -10), "oat_bund_20d_bp"),
          {"EURCHF": -1, "EURGBP": -1}, [], "Kein Treiber in der Exposure-Matrix: Hypothese."),
    Chain("ki_schulden_hy", "KI-Schulden → Kreditaufschlag → Aktien (verzögert)", "SMT 21.10.",
          [Step("HY-Spread steigt (20 T > +25 bp)", _gt("hy_20d_bp", 25), "hy_20d_bp"),
           Step("VIX noch ruhig (< 20)", _lt("vix", 20), "vix")],
          Step("HY-Spread unter 3,15 %", _lt("hy", 3.15), "hy"),
          {"ndx": -1, "spx": -1}, [("ndx", "vix"), ("spx", "vix")],
          "Erst Kredit, dann Aktien: Wirkung kommt verzögert, wenn der VIX nachzieht."),
    Chain("oel_praemie", "Öl-Prämie: Angriff statt Menge", "SMT 21.10.",
          [Step("Iran/Hormuz laut Schlagzeilen eskalierend", _eq("lage_iran_hormuz", "eskalation"), "lage_iran_hormuz"),
           Step("Brent über dem 20-Tage-Mittel", _gt("brent_vs_20d", 0), "brent_vs_20d")],
          Step("Entspannung gemeldet", _eq("lage_iran_hormuz", "entspannung"), "lage_iran_hormuz"),
          {"brent": +1}, [],
          "Eine Angriffsprämie verschwindet bei Waffenruhe schneller als eine echte Mengenkrise (Tanker ~70 %)."),
    Chain("zoelle_inflation", "Zölle → Importpreise → Inflationserwartung → Rohstoffwährungen", "Geo-Framework 12.11.",
          [Step("Zölle laut Schlagzeilen eskalierend", _eq("lage_zoelle_trump", "eskalation"), "lage_zoelle_trump"),
           Step("Inflationserwartung 10J steigt (20 T > +10 bp)", _gt("breakeven_20d_bp", 10), "breakeven_20d_bp")],
          Step("Zölle laut Schlagzeilen entspannt", _eq("lage_zoelle_trump", "entspannung"), "lage_zoelle_trump"),
          {"AUDUSD": +1, "USDCAD": -1}, [("AUDUSD", "breakeven"), ("USDCAD", "breakeven")]),
    Chain("ukraine_gas", "Ukraine/Energie → Europa-Gas → EUR, DAX schwächer", "SMT/Lehrbuch",
          [Step("Ukraine/Russland laut Schlagzeilen eskalierend", _eq("lage_ukraine_russland", "eskalation"),
                "lage_ukraine_russland")],
          Step("Entspannung gemeldet", _eq("lage_ukraine_russland", "entspannung"), "lage_ukraine_russland"),
          {"EURUSD": -1, "dax": -1}, [], "Ohne TTF-Historie nicht messbar: Hypothese."),
    Chain("risiko_aus_hafen", "Stress → Flucht in Häfen (USD, JPY, CHF) gegen Rohstoffwährungen", "Leitlinie 08.11.",
          [Step("VIX über 24", _gt("vix", 24), "vix"),
           Step("S&P 500 fällt (5 T < −3 %)", _lt("spx_5d", -3), "spx_5d")],
          Step("VIX unter 18", _lt("vix", 18), "vix"),
          {"AUDUSD": -1, "USDCAD": +1, "spx": -1}, [("AUDUSD", "vix"), ("USDCAD", "vix"), ("spx", "vix")]),
    Chain("risiko_an_ki", "KI-Gewinne → Nasdaq → Risikoappetit → AUD stärker", "Geo-Framework 12.11.",
          [Step("Nasdaq steigt (20 T > +5 %)", _gt("ndx_20d", 5), "ndx_20d"),
           Step("VIX fällt (20 T < 0)", _lt("vix_20d", 0), "vix_20d")],
          Step("Nasdaq fällt (20 T < −5 %)", _lt("ndx_20d", -5), "ndx_20d"),
          {"AUDUSD": +1, "kupfer": +1}, [("AUDUSD", "vix"), ("kupfer", "vix")]),
    Chain("us_zins_dollar", "US-Zinsen steigen relativ → Dollar stärker (vor allem gegen JPY)", "Fed-Note 2017",
          [Step("US-2J steigt (20 T > +15 bp)", _gt("us_2y_20d_bp", 15), "us_2y_20d_bp")],
          Step("US-2J fällt (20 T < −15 bp)", _lt("us_2y_20d_bp", -15), "us_2y_20d_bp"),
          {"USDJPY": +1, "EURUSD": -1, "gold": -1}, [("USDJPY", "us_2y"), ("EURUSD", "us_2y"), ("gold", "us_2y")]),
    Chain("china_kupfer", "China-Nachfrage → Kupfer → AUD stärker", "Lehrbuch",
          [Step("Kupfer steigt (20 T > +5 %)", _gt("kupfer_20d", 5), "kupfer_20d")],
          Step("Kupfer fällt (20 T < −5 %)", _lt("kupfer_20d", -5), "kupfer_20d"),
          {"AUDUSD": +1}, [], "Kupfer ist in der Exposure-Matrix kein Treiber: Hypothese."),
    Chain("fed_druck", "Druck auf die Fed → Glaubwürdigkeit → Dollar schwach, Gold stark", "Literatur",
          [Step("Fed-Druck laut Schlagzeilen eskalierend", _eq("lage_fed_unabhaengigkeit", "eskalation"),
                "lage_fed_unabhaengigkeit"),
           Step("5J-in-5J-Inflationserwartung steigt (Woche > +5 bp)", _gt("fwd_5y5y_1w_bp", 5), "fwd_5y5y_1w_bp")],
          Step("Entspannung gemeldet", _eq("lage_fed_unabhaengigkeit", "entspannung"), "lage_fed_unabhaengigkeit"),
          {"gold": +1, "EURUSD": +1}, [("gold", "dollar")]),
]


def _ret(s: pd.Series, n: int) -> float | None:
    s = s.dropna()
    return None if len(s) <= n else float(100 * (s.iloc[-1] / s.iloc[-1 - n] - 1))


def _chg(s: pd.Series, n: int, scale: float = 100) -> float | None:
    s = s.dropna()
    return None if len(s) <= n else float(scale * (s.iloc[-1] - s.iloc[-1 - n]))


def measures(daily: pd.DataFrame, macro_w: pd.DataFrame, sheet: dict) -> M:
    d = daily
    col = lambda c: d[c] if c in d else pd.Series(dtype=float)
    mw = lambda k: macro_w[k] if k in macro_w else pd.Series(dtype=float)
    b = col("brent").dropna()
    m: M = {
        "brent_20d": _ret(b, 20), "brent_vs_20d": None if len(b) < 20 else float(100 * (b.iloc[-1] / b.iloc[-20:].mean() - 1)),
        "us_2y_20d_bp": _chg(col("us_2y"), 20), "breakeven_20d_bp": _chg(col("breakeven_10y"), 20),
        "vix": None if col("vix").dropna().empty else float(col("vix").dropna().iloc[-1]),
        "vix_20d": _chg(col("vix"), 20, 1), "spx_5d": _ret(col("spx"), 5), "ndx_20d": _ret(col("ndx"), 20),
        "kupfer_20d": _ret(col("kupfer"), 20),
        "hy": None if mw("MKT.hy_spread").dropna().empty else float(mw("MKT.hy_spread").dropna().iloc[-1]),
        "hy_20d_bp": _chg(mw("MKT.hy_spread"), 20), "fwd_5y5y_1w_bp": _chg(mw("US.fwd_5y5y"), 5),
    }
    fr, de = mw("FR.10y").dropna(), mw("DE.10y").dropna()
    spread = (fr - de).dropna() * 100
    m["oat_bund_bp"] = None if spread.empty else float(spread.iloc[-1])
    m["oat_bund_20d_bp"] = _chg(spread, 20, 1)
    geo = sheet.get("geopolitik") or {}
    m["fed_kanal"] = (geo.get("oel_durchgriff") or {}).get("fed_kanal")
    for card in geo.get("themen", []):
        m[f"lage_{card['thema']}"] = card["lage"] if card["lage"] != "n.v." else None
    ca = ((sheet.get("taktisch") or {}).get("notenbanken") or {}).get("CA") or {}
    m["ca_pricing_1w_bp"] = ca.get("chg_1w_bp")
    return {k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in m.items()}


def _fmt_measure(v):
    if v is None:
        return "n.v."
    if isinstance(v, bool):
        return "ja" if v else "nein"
    return f"{v:.1f}".replace(".", ",") if isinstance(v, float) else str(v)


def evaluate(m: M, exposure: dict | None) -> list[dict]:
    from .geo_framework import label
    out = []
    for c in CHAINS:
        steps = [s.check(m) for s in c.schritte]
        stop = c.stopp.check(m)
        if stop:
            status = "gestoppt"
        elif steps and all(v is True for v in steps):
            status = "aktiv"
        elif steps and steps[0] is True:
            status = "anlaufend"
        else:
            status = "ruhend"
        beleg = []
        for asset, drv in c.beleg:
            x = ((exposure or {}).get(drv) or {}).get("assets", {}).get(label(asset))
            if x:
                beleg.append({"asset": label(asset), "treiber": drv, "status": x["status"], "heute": x["heute"], "oos": x["oos"]})
        stable = [b for b in beleg if b["status"] == "belegt"]
        out.append({
            "id": c.id, "name": c.name, "quelle": c.quelle, "status": status,
            "schritte": [{"text": s.text, "erfuellt": v, "wert": _fmt_measure(m.get(s.zeigt))} for s, v in zip(c.schritte, steps)],
            "stopp": {"text": c.stopp.text, "erfuellt": stop},
            "assets": {label(a): ("steigt" if s > 0 else "fällt") for a, s in c.assets.items()},
            "beleg": "belegt" if stable and len(stable) == len(c.beleg) else ("teilweise" if stable else "Hypothese"),
            "beleg_details": beleg, "hinweis": c.hinweis,
            "ledger_assets": c.assets,
        })
    return out
