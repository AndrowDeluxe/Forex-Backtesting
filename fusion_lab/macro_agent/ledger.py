"""Forecast-Ledger (Meridian-Baustein, 12.11.2026): Wahrheitsbuch aller Aussagen des Fact Sheets.

Jeder Lauf haengt an (nie ueberschreiben): Scorecard-Ideen (Paar + Richtung) und Themen-Einordnungen
(Eskalation/Entspannung -> erwartete Richtung des Kanal-Treibers), je mit Horizont 5 und 20 Handelstagen.
`evaluate()` traegt faellige Ergebnisse nach; `summary()` liefert die Trefferquote je Art. Einziger ehrlicher
Test eines Makro-Agenten ist vorwaerts (Memory llm_agent_nur_vorwaerts_testbar).

Die Datei liegt im Repo (fusion_lab/data ist git-ignoriert), damit die Historie nicht verloren geht.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

LEDGER = Path(__file__).resolve().parent / "ledger" / "ledger.csv"
HORIZONS = (5, 20)
COLUMNS = ["erstellt", "art", "objekt", "richtung", "messgroesse", "einheit", "horizont", "faellig", "begruendung",
           "start", "ende", "ergebnis", "treffer"]
# Thema -> Messgroesse in der Geo-Historie, Einheit, Vorzeichen bei Eskalation
THEME_MEASURE = {"iran_hormuz": ("brent", "pct", +1), "zoelle_trump": ("breakeven_10y", "bp", +1),
                 "ukraine_russland": ("gpr", "pct", +1), "china_taiwan": ("vix", "diff", +1),
                 "fed_unabhaengigkeit": ("breakeven_10y", "bp", +1)}
MARKET_MEASURE = {"XAUUSD": "gold"}


def read(path: Path = LEDGER) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)
    return pd.read_csv(path, parse_dates=["erstellt", "faellig"])


def _due(day: pd.Timestamp, h: int) -> pd.Timestamp:
    return (day + pd.offsets.BDay(h)).normalize()


def records(sheet: dict) -> list[dict]:
    day = pd.Timestamp(sheet["stand"])
    out = []
    for i in sheet.get("risiko", {}).get("ideen", []):
        m = i["markt"]
        for h in HORIZONS:
            out.append({"erstellt": day, "art": "idee", "objekt": m, "richtung": 1 if i["seite"] == "long" else -1,
                        "messgroesse": MARKET_MEASURE.get(m, m), "einheit": "pct", "horizont": h,
                        "faellig": _due(day, h), "begruendung": f"Score-Differenz {i['diff']}"})
    geo = sheet.get("geopolitik") or {}
    for card in geo.get("themen", []):
        if card["lage"] not in ("eskalation", "entspannung") or card["thema"] not in THEME_MEASURE:
            continue
        col, unit, sign = THEME_MEASURE[card["thema"]]
        direction = sign if card["lage"] == "eskalation" else -sign
        for h in HORIZONS[:1]:
            out.append({"erstellt": day, "art": "thema", "objekt": card["thema"], "richtung": direction,
                        "messgroesse": col, "einheit": unit, "horizont": h, "faellig": _due(day, h),
                        "begruendung": f"{card['lage']}: {card['kernaussage'][:160]}"})
    return out


def append(sheet: dict, path: Path = LEDGER) -> int:
    """Haengt neue Aussagen an; ein zweiter Lauf am selben Tag aendert nichts (erste Fassung gilt)."""
    new = pd.DataFrame(records(sheet), columns=COLUMNS[:9])
    if new.empty:
        return 0
    old = read(path)
    if len(old):
        key = ["erstellt", "art", "objekt", "horizont"]
        known = set(map(tuple, old[key].astype(str).values))
        new = new[[tuple(r) not in known for r in new[key].astype(str).values]]
    if new.empty:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    out = pd.concat([old, new], ignore_index=True) if len(old) else new.reindex(columns=COLUMNS)
    out.to_csv(path, index=False, date_format="%Y-%m-%d")
    return len(new)


def _value(series: pd.Series, day: pd.Timestamp) -> float | None:
    s = series.loc[:day].dropna()
    return None if s.empty else float(s.iloc[-1])


def evaluate(history: pd.DataFrame, as_of: pd.Timestamp, path: Path = LEDGER) -> int:
    """Traegt Start- und Endwert fuer faellige, offene Eintraege nach; gibt die Anzahl zurueck."""
    df = read(path)
    if df.empty:
        return 0
    for col in ("start", "ende", "ergebnis", "treffer"):  # leere Spalten liest pandas als float
        df[col] = df[col].astype(object)
    done = 0
    for idx, r in df.iterrows():
        if pd.notna(r["ergebnis"]) or r["faellig"] > as_of or r["messgroesse"] not in history:
            continue
        s = history[r["messgroesse"]]
        if s.loc[:r["faellig"]].dropna().index.max() < r["faellig"] - pd.Timedelta(days=4):
            continue  # Daten fuer den Faelligkeitstag fehlen noch (z. B. GPR-Verzug)
        start, end = _value(s, r["erstellt"]), _value(s, r["faellig"])
        if start is None or end is None:
            continue
        change = {"pct": 100 * (end / start - 1), "bp": 100 * (end - start), "diff": end - start}[r["einheit"]]
        df.loc[idx, ["start", "ende", "ergebnis", "treffer"]] = [start, end, round(r["richtung"] * change, 3),
                                                                bool(r["richtung"] * change > 0)]
        done += 1
    if done:
        df.to_csv(path, index=False, date_format="%Y-%m-%d")
    return done


def summary(path: Path = LEDGER) -> dict:
    df = read(path)
    out = {"eintraege": int(len(df)), "ausgewertet": 0, "je_art": {}}
    if df.empty:
        return out
    ev = df[df["ergebnis"].notna()]
    out["ausgewertet"] = int(len(ev))
    for (art, h), g in ev.groupby(["art", "horizont"]):
        out["je_art"][f"{art}_{int(h)}t"] = {"n": int(len(g)), "trefferquote_pct": round(100 * g["treffer"].astype(bool).mean(), 0),
                                              "mittel": round(float(g["ergebnis"].mean()), 3)}
    return out
