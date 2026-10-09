"""Legt das "Trading Fusion Cockpit" in Notion an (Strang 4, Grundgeruest).

Unter der freigegebenen Wurzelseite ([notion] root_page) entstehen eine
Straenge-Uebersicht und fuenf Datenbanken. Idempotent: vorhandene Datenbanken
(gleicher Titel) werden wiederverwendet, nicht doppelt angelegt. Die IDs landen
in fusion_lab/notion/cockpit_ids.json fuer spaetere Schreibzugriffe.

    python -m fusion_lab.notion.setup_cockpit           # anlegen / pruefen
    python -m fusion_lab.notion.setup_cockpit --test    # + Testzeile schreiben, lesen, archivieren
"""

import argparse
import json
import sys
from datetime import date as _date

from fusion_lab.notion.client import (IDS_FILE, Notion, load_ids, load_notion_config, page_id_from,
                                      para, rich, select, title)

QUELLE = ["Mentor", "Eigene", "Bot", "Gruppe"]
BIAS = [("Bullish", "green"), ("Bearish", "red"), ("Neutral", "gray")]
ASSETS = ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD", "Gold", "Silber",
          "Öl", "Indizes", "Anleihen", "Aktien"]
INSTRUMENTE = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "XAUUSD",
               "XAGUSD", "WTI", "US500", "NAS100", "US30", "DAX"]


def _sel(options) -> dict:
    """Optionen als "Name" oder ("Name", "farbe")."""
    out = []
    for o in options:
        name, color = o if isinstance(o, tuple) else (o, None)
        out.append({"name": name, "color": color} if color else {"name": name})
    return {"options": out}


def S(*options) -> dict:
    return {"select": _sel(options)}


def M(*options) -> dict:
    return {"multi_select": _sel(options)}


T, R, D, U, C = ({"title": {}}, {"rich_text": {}}, {"date": {}}, {"url": {}}, {"checkbox": {}})

DATABASES = {
    # ELITE 3 = Mentoring-Gruppe, ab 10/2026 Haupt-Input fuer neues Wissen,
    # Erkenntnisse und Aufgaben (vorher OneNote). Wissen hier ist NICHT
    # verbindlich, bis es nach knowledge/ uebernommen ist (Haekchen).
    "elite3": ("🎓 ELITE 3", {
        "Titel": T,
        "Art": S(("Wissen", "blue"), ("Erkenntnis", "purple"), ("Aufgabe", "orange"),
                 ("Material", "gray"), ("Session", "green")),
        "Datum": D, "Fällig": D,
        "Thema": M("Makro", "Zinsen", "Inflation", "Notenbanken", "COT/Positionierung",
                   "Struktur/Liquidität", "Bankreports", "Sentiment", "CTNL", "Strategie",
                   "Risiko", "Execution", "Psychologie", "Sonstiges"),
        "Assets": M(*ASSETS),
        "Status": S(("offen", "gray"), ("in Arbeit", "yellow"), ("abgegeben", "green"),
                    ("besprochen", "blue"), ("erledigt", "default")),
        "In knowledge/ übernommen": C,
        "Bot-Beitrag": R, "Ergebnis / Feedback": R, "Link": U,
    }),
    "makro": ("🌍 Makro-Übersicht", {
        "Thema": T, "Datum": D, "Assets": M(*ASSETS), "Bias": S(*BIAS),
        "Treiber": M("Zinsen", "Inflation", "Wachstum", "Arbeitsmarkt", "Notenbank",
                     "Geopolitik", "Risikostimmung", "Positionierung", "Ölpreis"),
        "Zusammenfassung": R, "Quelle": S(*QUELLE),
        "Gültig bis": D, "Link": U,
    }),
    "analysen": ("📈 Analysen", {
        "Titel": T, "Datum": D,
        "Instrument": S(*INSTRUMENTE),
        "Typ": S("Wochenanalyse", "Tagesanalyse", "Breakdown", "Bankreport", "Setup",
                 "Gruppenarbeit"),
        "Timeframe": M("MN", "W1", "D1", "H4", "H1", "M15", "M5"),
        "Bias": S(*BIAS), "Quelle": S(*QUELLE),
        "Ergebnis": S(("offen", "gray"), ("aufgegangen", "green"), ("nicht aufgegangen", "red"),
                      ("kein Trigger", "default")),
        "Kernaussage": R, "Link": U,
    }),
    "entscheidungslog": ("🤖 Entscheidungslog (Bot)", {
        "Entscheidung": T, "Zeitpunkt": D,
        "Strang": S("0 Inventur", "1 Edge Cards", "2 Tests", "3 Analyse", "4 Cockpit",
                    "5 Ausführung", "6 Agenten", "7 Selbstlernen"),
        "Gate": S(("1 autonom", "green"), ("2 autonom + Meldung", "yellow"),
                  ("3 Freigabe nötig", "red")),
        "Status": S(("ausgeführt", "green"), ("wartet auf Freigabe", "yellow"),
                    ("abgelehnt", "red"), ("zurückgenommen", "gray"),
                    ("unvollständig", "orange")),  # Pflichtangaben fehlen -> weder Freigabe noch Ablehnung
        # Abgelehnte/unvollstaendige Setups werden genauso geloggt wie ausgefuehrte,
        # sonst sind die Lerndaten fuer Strang 7 einseitig. Fakten (mit Quelle) und
        # Analyse getrennt halten; was fehlt, steht in "Fehlende Infos".
        "Instrument": S(*INSTRUMENTE),
        "Richtung": S(("long", "green"), ("short", "red"), ("flat", "gray")),
        "Fakten (Quelle)": R, "Fehlende Infos": R,
        "Kosten / Slippage": R,
        "Regeln befolgt": S(("ja", "green"), ("teilweise", "yellow"), ("nein", "red"),
                            ("n. a.", "gray")),
        "Warum": R, "Ergebnis": R, "Link": U,
    }),
    "zwischenablage": ("📥 Zwischenablage", {
        "Notiz": T, "Datum": D, "Typ": S("Idee", "Frage", "Notiz", "Material", "Aufgabe"),
        "Von": S("André", "Claude", "Bot"), "Inhalt": R,
        "In knowledge/ übernommen": C, "Link": U,
    }),
}

# Umbenennungen bestehender Datenbanken/Felder (alt -> neu), damit ein erneuter
# Lauf nichts doppelt anlegt.
KEY_RENAMES = {"gruppenarbeit": "elite3"}
PROP_RENAMES = {"elite3": {"Aufgabe": "Titel", "Abgabe": "Fällig"}}

OVERVIEW = [
    ("heading_2", "Trading Fusion — Stränge"),
    ("paragraph", "Spiegel von knowledge/projects/quant-diskretionaer-fusion.md (die Quelle "
                  "der Wahrheit). Notion zeigt an, entschieden wird im Repo."),
    ("to_do", "0 Inventur — Material importieren, Bestandteile listen"),
    ("to_do", "1 Edge Cards je Bestandteil"),
    ("to_do", "2 Reproduzieren + Testen (Phasen 4–6)"),
    ("to_do", "3 Analyse automatisieren — zuerst Makro"),
    ("to_do", "4 Sichtbarkeit — dieses Cockpit"),
    ("to_do", "5 Ausführung auf Paper (FX/Rohstoffe)"),
    ("to_do", "6 Agentenschicht"),
    ("to_do", "7 Selbstlernen"),
    ("heading_3", "Freigabe-Gates"),
    ("bulleted_list_item", "1 — autonom mit Log: Retries, Datenlücken, kleine Fixes in Paper-/Analyse-Code"),
    ("bulleted_list_item", "2 — autonom mit Telegram-Meldung: Parameter in freigegebenen Bandbreiten"),
    ("bulleted_list_item", "3 — nur André (Plan-Modus): neue Regeln, Risiko, alles mit echtem Geld"),
]


def ensure_overview(n: Notion, root: str, existing: list[dict]) -> None:
    if any(b["type"] == "heading_2" and "Stränge" in "".join(
            t["plain_text"] for t in b["heading_2"]["rich_text"]) for b in existing):
        return
    blocks = []
    for kind, text in OVERVIEW:
        body = rich(text)
        if kind == "to_do":
            body["checked"] = False
        blocks.append({"object": "block", "type": kind, kind: body})
    n.req("PATCH", f"/blocks/{root}/children", {"children": blocks})
    print("  Übersicht angelegt")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--test", action="store_true", help="Testzeile schreiben, lesen, archivieren")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")  # Emojis in DB-Titeln, Windows-Konsole ist cp1252

    cfg = load_notion_config()
    n = Notion(cfg["token"])
    root = page_id_from(cfg["root_page"])
    page = n.req("GET", f"/pages/{root}")
    root_title = "".join(t["plain_text"] for p in page["properties"].values()
                         if p["type"] == "title" for t in p["title"])
    print(f"Wurzelseite: {root_title or root}")

    existing = n.children(root)
    have = {b["child_database"]["title"]: b["id"] for b in existing if b["type"] == "child_database"}
    ensure_overview(n, root, existing)

    old_ids = load_ids()
    for old, new in KEY_RENAMES.items():
        if old in old_ids and new not in old_ids:
            old_ids[new] = old_ids.pop(old)
    ids = {"root_page": root}
    for key, (db_title, props) in DATABASES.items():
        db_id = old_ids.get(key) or have.get(db_title)
        if db_id:
            # Abgleich: Titel + Felder auf den Stand dieser Datei bringen. Notion
            # ergaenzt fehlende Felder/Optionen, loescht aber nichts.
            current = n.req("GET", f"/databases/{db_id}")["properties"]
            renames = {o: {"name": nw} for o, nw in PROP_RENAMES.get(key, {}).items()
                       if o in current and nw not in current}
            if renames:
                n.req("PATCH", f"/databases/{db_id}", {"properties": renames})
            n.req("PATCH", f"/databases/{db_id}", {
                "title": [{"type": "text", "text": {"content": db_title}}],
                "properties": props,
            })
            ids[key] = db_id
            print(f"  abgeglichen: {db_title}" + (f" (umbenannt: {', '.join(renames)})" if renames else ""))
            continue
        db = n.req("POST", "/databases", {
            "parent": {"type": "page_id", "page_id": root},
            "title": [{"type": "text", "text": {"content": db_title}}],
            "properties": props,
        })
        ids[key] = db["id"]
        print(f"  angelegt:  {db_title}")
    IDS_FILE.write_text(json.dumps(ids, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.test:
        row = n.add_row(ids["zwischenablage"], {
            "Notiz": title("Verbindungstest Claude"), "Datum": {"date": {"start": _date.today().isoformat()}},
            "Typ": select("Notiz"), "Von": select("Claude"), "Inhalt": rich("Schreiben + Lesen klappt."),
        }, [para("Automatisch angelegt und wieder archiviert.")])
        back = n.req("GET", f"/pages/{row['id']}")
        ok = back["properties"]["Inhalt"]["rich_text"][0]["plain_text"] == "Schreiben + Lesen klappt."
        n.req("PATCH", f"/pages/{row['id']}", {"archived": True})
        print(f"  Test: schreiben/lesen {'OK' if ok else 'FEHLGESCHLAGEN'}, Testzeile archiviert")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
