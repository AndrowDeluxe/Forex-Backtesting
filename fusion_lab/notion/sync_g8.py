"""Schreibt die G8-Waehrungsstaerke ins Notion-Cockpit (DB "💱 G8-Stärke") und
pflegt die Erklaerseite "G8-Modell".

Zeilen: veroeffentlichte SMH-Tabellen (fusion_lab/data/g8/snapshots.csv) und
unser Nachbau (fusion_lab/g8) fuer die letzten --days Handelstage -- FRED, wo
vorhanden, sonst Dukascopy (FRED hinkt ~1 Woche nach). Idempotent ueber den
Titel "<Datum> · <Quelle>": vorhandene Zeilen werden aktualisiert, nicht doppelt
angelegt.

    python -m fusion_lab.notion.setup_cockpit       # einmalig: DB anlegen
    python -m fusion_lab.notion.sync_g8 --days 60
    python -m fusion_lab.notion.sync_g8 --days 10 --refresh   # Tageslauf (Task "G8-Notion-Sync")
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from fusion_lab.g8.data import CURRENCIES, log_values, usd_value_panel
from fusion_lab.g8.model import DEFAULT_NORM, score
from fusion_lab.notion.client import Notion, date, load_ids, rich, select, title

SNAPSHOTS = Path(__file__).resolve().parents[1] / "data" / "g8" / "snapshots.csv"
PAGE_TITLE = "G8-Modell — Währungsstärke (Nachbau)"

EXPLAIN = [
    ("heading_2", "Was das Modell zeigt"),
    ("paragraph", "Rangliste der acht Hauptwährungen (USD, EUR, GBP, JPY, CHF, AUD, CAD, NZD) nach "
                  "relativer Stärke. Vorbild: das tägliche Bild „Währungsstärke G8“ aus SMHxSMT "
                  "(dort ausdrücklich „Zustandsmodell, kein Handelssignal“)."),
    ("heading_2", "Wie gerechnet wird"),
    ("bulleted_list_item", "Wert jeder Währung in USD aus FRED-Tageskursen (H.10) ab 1999; jüngste Tage aus "
                           "Dukascopy, weil FRED ~1 Woche nachhinkt."),
    ("bulleted_list_item", "Je Horizont (1 Woche = 5, 1 Monat = 21, 3 Monate = 63 Handelstage): Logrendite der "
                           "Währung minus Mittel der acht, geteilt durch die Streuung der acht am selben Tag (z-Wert)."),
    ("bulleted_list_item", "Score = Mittel der drei z-Werte. Über +1 auffällig stark, unter −1 auffällig schwach."),
    ("heading_2", "Wie gut der Nachbau trifft"),
    ("paragraph", "Gegen 23 veröffentlichte Tabellen (24.08.–06.10.2026): Score-Korrelation 0,98, "
                  "Rang-Korrelation je Tag 0,95, mittlere Abweichung 0,12 Score-Punkte. Restabweichung "
                  "vor allem im 1-Wochen-Wert (andere Datenquelle/Uhrzeit)."),
    ("heading_2", "Was der Backtest sagt"),
    ("paragraph", "Als eigenständiges Signal (stärkste kaufen, schwächste verkaufen; 1–3 je Seite, "
                  "wöchentlich/täglich) 2000–2017 durchweg negativ (Sharpe −0,13 bis −0,42). "
                  "Verwendung daher als Kontext-Baustein (welche Währung als Gegenseite), nicht als "
                  "Einstieg. Prüfzeiträume 2018–2026 bleiben ungeöffnet."),
    ("paragraph", "Quelle der Wahrheit: Repo fusion_lab/g8/, knowledge/projects/quant-diskretionaer-fusion.md."),
]


def _block(kind: str, text: str) -> dict:
    return {"object": "block", "type": kind, kind: rich(text)}


def ensure_page(n: Notion, root: str) -> str:
    for b in n.children(root):
        if b["type"] == "child_page" and b["child_page"]["title"] == PAGE_TITLE:
            return b["id"]
    page = n.req("POST", "/pages", {
        "parent": {"page_id": root},
        "properties": {"title": {"title": [{"text": {"content": PAGE_TITLE}}]}},
        "children": [_block(k, t) for k, t in EXPLAIN],
    })
    return page["id"]


def existing_rows(n: Notion, db: str) -> dict[str, str]:
    out, cursor = {}, None
    while True:
        body = {"page_size": 100, **({"start_cursor": cursor} if cursor else {})}
        data = n.req("POST", f"/databases/{db}/query", body)
        for p in data["results"]:
            t = "".join(x["plain_text"] for x in p["properties"]["Stand"]["title"])
            out[t] = p["id"]
        if not data.get("has_more"):
            return out
        cursor = data["next_cursor"]


def _props(day: str, quelle: str, scores: pd.Series, common: float | None = None, note: str = "") -> dict:
    s = scores.sort_values(ascending=False)
    p = {
        "Stand": title(f"{day} · {quelle}"), "Datum": date(day), "Quelle": select(quelle),
        "Stärkste": select(s.index[0]), "Schwächste": select(s.index[-1]),
        "Rangfolge": rich(" > ".join(f"{c} {v:+.2f}" for c, v in s.items())),
        **{c: {"number": round(float(scores[c]), 2)} for c in CURRENCIES},
    }
    if common is not None and pd.notna(common):
        p["Gemeinsamer Treiber %"] = {"number": float(common)}
    if note:
        p["Hinweis"] = rich(note)
    return p


def rows_rebuild(days: int, refresh: bool = False) -> list[tuple[str, str, pd.Series]]:
    fred, _ = score(log_values(usd_value_panel("fred", force_refresh=refresh)), DEFAULT_NORM)
    duka, _ = score(log_values(usd_value_panel("duka", start="2025-01-01")), DEFAULT_NORM)
    fred, duka = fred.dropna(), duka.dropna()
    out = [(d.strftime("%Y-%m-%d"), "Nachbau FRED", fred.loc[d]) for d in fred.index[-days:]]
    last_fred = fred.index[-1]
    out += [(d.strftime("%Y-%m-%d"), "Nachbau Dukascopy", duka.loc[d]) for d in duka.index if d > last_fred]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--days", type=int, default=60, help="Nachbau: letzte N FRED-Handelstage")
    ap.add_argument("--refresh", action="store_true", help="FRED neu laden (Tageslauf)")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")

    ids = load_ids()
    if "g8" not in ids:
        raise SystemExit("DB fehlt -- erst: python -m fusion_lab.notion.setup_cockpit")
    n = Notion()
    page = ensure_page(n, ids["root_page"])
    have = existing_rows(n, ids["g8"])

    rows = []
    if SNAPSHOTS.exists():
        snap = pd.read_csv(SNAPSHOTS)
        for st, g in snap.groupby("stand_date"):
            rows.append(_props(st, "SMH", g.set_index("currency").score, g.common_driver_pct.iloc[0],
                               "veröffentlichte Tabelle (abgeschrieben)"))
    rows += [_props(d, q, s) for d, q, s in rows_rebuild(args.days, args.refresh)]

    new = upd = 0
    for p in rows:
        key = p["Stand"]["title"][0]["text"]["content"]
        if key in have:
            n.req("PATCH", f"/pages/{have[key]}", {"properties": p})
            upd += 1
        else:
            n.add_row(ids["g8"], p)
            new += 1
    print(f"Erklärseite: {page}\nG8-Zeilen: {new} neu, {upd} aktualisiert")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
