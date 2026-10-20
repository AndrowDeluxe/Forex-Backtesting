"""Schreibt die Regime-Roadmap (Wachstum x Inflation) als Eintrag in die
Notion-DB "🌍 Makro-Übersicht". Idempotent ueber den Titel: ein vorhandener
Eintrag wird aktualisiert und sein Inhalt neu aufgebaut.

    python -m fusion_lab.macro_regime            # erst rechnen
    python -m fusion_lab.notion.sync_regime      # dann nach Notion
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from fusion_lab.macro_regime.data import ASSETS
from fusion_lab.notion.client import Notion, date, load_ids, multi, rich, select, title

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "macro_regime"
PAGE_TITLE = "Regime-Roadmap — Wachstum × Inflation"
BIG_STATES = 4  # nur die vier grossen Zustaende der gemeinsamen Sicht sind belastbar


def _rt(text: str, bold: bool = False, color: str = "default") -> dict:
    return {"type": "text", "text": {"content": text[:2000]},
            "annotations": {"bold": bold, "color": color}}


def _block(kind: str, text: str, **extra) -> dict:
    return {"object": "block", "type": kind, kind: {"rich_text": [_rt(text)], **extra}}


def _bullets(items: list[str]) -> list[dict]:
    return [_block("bulleted_list_item", t) for t in items]


def _table(header: list[str], rows: list[list[dict]]) -> dict:
    def row(cells):
        return {"object": "block", "type": "table_row", "table_row": {"cells": cells}}
    return {"object": "block", "type": "table", "table": {
        "table_width": len(header), "has_column_header": True, "has_row_header": True,
        "children": [row([[_rt(h, bold=True)] for h in header])] + [row(r) for r in rows]}}


def _stats_table(stats: pd.DataFrame, field: str, current: str, digits: int, limit: int | None) -> dict:
    rows = []
    for reg in stats.index[:limit]:
        cur = reg == current
        cells = [[_rt(("▶ " if cur else "") + reg, bold=cur)],
                 [_rt(str(int(stats.loc[reg, ("days", "n")])), bold=cur)]]
        for a in ASSETS:
            v = stats.loc[reg, (field, a)]
            color = "default" if pd.isna(v) or field == "vol" else ("green" if v > 0 else "red")
            cells.append([_rt("–" if pd.isna(v) else f"{v:.{digits}f}", bold=cur, color=color)])
        rows.append(cells)
    return _table(["Regime", "Tage", *ASSETS], rows)


def _load_stats(lens: str) -> pd.DataFrame:
    df = pd.read_csv(OUT_DIR / f"stats_{lens}.csv", header=[0, 1], index_col=0)
    return df


def build_blocks(state: dict) -> list[dict]:
    g, i, lab = state["growth"], state["inflation"], state["labels"]
    tempo = lambda x: "beschleunigt" if x["accel"] else "verlangsamt"
    sign = lambda x: "positiv" if x["up"] else "negativ"
    nxt = "; ".join(f"{k} {', '.join(pd.Timestamp(d).strftime('%d.%m.') for d in v)}"
                    for k, v in state["next_releases"].items())
    since = pd.Timestamp(state["regime_since"]).strftime("%d.%m.%Y")
    blocks = [
        {"object": "block", "type": "callout", "callout": {
            "rich_text": [_rt("Aktuelles Regime: ", bold=True), _rt(lab["joint"], bold=True),
                          _rt(f" (seit {since}). Nächste Prints: {nxt}.")],
            "icon": {"type": "emoji", "emoji": "🧭"}, "color": "blue_background"}},
        _block("heading_2", "Wo wir stehen"),
        _table(["", "YoY vorher", "YoY aktuell", "Vorzeichen", "Tempo", "Print"], [
            [[_rt(f"Wachstum (reales BIP, {g['period'][:7]})")], [_rt(f"{g['yoy_prev_period']:.2f} %")],
             [_rt(f"{g['yoy']:.2f} %", bold=True)], [_rt(sign(g))], [_rt(tempo(g))], [_rt(g["release"])]],
            [[_rt(f"Inflation (CPI, {i['period'][:7]})")], [_rt(f"{i['yoy_prev_period']:.2f} %")],
             [_rt(f"{i['yoy']:.2f} %", bold=True)], [_rt(sign(i))], [_rt(tempo(i))], [_rt(i["release"])]],
        ]),
        _block("paragraph", f"Linsen: gemeinsam {lab['joint']} · Tempo {lab['change']} · Vorzeichen {lab['signs']}. "
                            f"Ein Print gilt ab der folgenden Sitzung."),
        _block("heading_2", "Wie das Regime bestimmt wird"),
        *_bullets([
            "Wachstum = reales US-BIP YoY, Inflation = Headline-CPI YoY, jeweils so, wie am "
            "Release-Morgen veröffentlicht (ALFRED-Erstveröffentlichung, keine späteren Revisionen).",
            "Frage 1: Ist die Rate positiv oder negativ? Frage 2: Ist sie höher (accel) oder niedriger "
            "(slow) als die der Vorperiode?",
            "„Nur Vorzeichen“ ist zu einseitig (rund 93 % der Tage „beide positiv“). Aussagekräftig sind "
            "„Tempo“ und vor allem die gemeinsame Sicht.",
            "Je Regime: Rendite, Vola und Sharpe gegen Cash (3M T-Bill), annualisiert, Stichprobe ab März 1994.",
        ]),
        _block("heading_2", "Zwei Ebenen: Bestätigung und Frühwarnung"),
        *_bullets([
            "Karte (diese Seite) = Bestätigung. Sie wechselt per Definition nur an GDP- und CPI-Terminen.",
            "Marktsicht = Frühwarnung (geplant, beim Bau des Makro-Agenten). Staatsanleihen-Renditen "
            "(2y/10y), Breakevens und GDPNow bewegen sich laufend und können einen Wechsel anzeigen, "
            "bevor der nächste Print ihn bestätigt.",
        ]),
    ]
    joint = _load_stats("joint")
    change = _load_stats("change")
    blocks += [
        _block("heading_2", "Gemeinsame Sicht: die vier großen Zustände"),
        _block("paragraph", "Werte gegen Cash, annualisiert. ▶ = aktuelles Regime. Grün positiv, rot negativ."),
        _block("heading_3", "Sharpe"),
        _stats_table(joint, "sharpe", lab["joint"], 2, BIG_STATES),
        _block("heading_3", "Rendite % p.a."),
        _stats_table(joint, "ret", lab["joint"], 1, BIG_STATES),
        _block("heading_3", "Vola % p.a."),
        _stats_table(joint, "vol", lab["joint"], 1, BIG_STATES),
        _block("heading_2", "Tempo-Sicht (beschleunigt vs. verlangsamt)"),
        _block("heading_3", "Sharpe"),
        _stats_table(change, "sharpe", lab["change"], 2, None),
        _block("heading_3", "Rendite % p.a."),
        _stats_table(change, "ret", lab["change"], 1, None),
        _block("heading_2", "Dünne Zustände (Rauschen, nur zur Info)"),
        _block("paragraph", "Unter ~150 Tagen sind die Mittelwerte nicht belastbar."),
        _stats_table(joint.iloc[BIG_STATES:], "sharpe", lab["joint"], 2, None),
        _block("heading_2", "Datenbasis und Abgleich mit dem Original"),
        *_bullets([
            "Vorlage: A. Landi, „Reading the growth–inflation map“ (Stand 20.09.2026, Bloomberg-Daten).",
            "Nachbau mit freien Daten: SPX Total Return und DXY (yfinance), UST als synthetische "
            "5y-Anleihe (FRED DGS5), Gold/Kupfer/Öl/Weizen als Front-Monats-Futures (ab 2000, ohne Rollrendite).",
            "Abgleich 18.09.2026: Regime identisch, Tagesanteile der vier großen Zustände ±1,5 Prozentpunkte, "
            "Vorzeichen und Rangfolge der Assets gleich. Rohstoffe wirken besser als im Original, weil die "
            "Rollrendite fehlt.",
            "Karte der Vergangenheit, keine Prognose. Regeln wie „Bein X nur in Regime Y“ laufen unter der "
            "Overfitting-Sperre.",
        ]),
        _block("heading_2", "Später (beim Bau des Makro-Agenten)"),
        *_bullets([
            "Täglicher Lauf nach den US-Releases, Wechsel-Log, Telegram nur bei Wechsel.",
            "Soll/Ist-Abgleich: Assets seit dem Wechsel gegen das Regime-Mittel.",
            "Regime-Block im Wochenbericht; Marktsicht als Frühwarnung.",
        ]),
        _block("paragraph", f"Stand Daten: {state['sample']['end']}. Quelle der Wahrheit: Repo "
                            "fusion_lab/macro_regime/, knowledge/resources/regimekarte-wachstum-inflation.md."),
    ]
    return blocks


def props(state: dict) -> dict:
    g, i, lab = state["growth"], state["inflation"], state["labels"]
    summary = (f"{lab['joint']} seit {state['regime_since']}: Wachstum {g['yoy']:.2f} % "
               f"({'beschleunigt' if g['accel'] else 'verlangsamt'}), Inflation {i['yoy']:.2f} % "
               f"({'beschleunigt' if i['accel'] else 'verlangsamt'}). Historisch in diesem Regime: "
               + ", ".join(f"{a} Sharpe {state['current_regime_stats'][a]['sharpe']:+.2f}" for a in ASSETS))
    upcoming = sorted(d for v in state["next_releases"].values() for d in v)
    p = {"Thema": title(PAGE_TITLE), "Datum": date(state["sample"]["end"]),
         "Assets": multi("USD", "Gold", "Öl", "Indizes", "Anleihen"),
         "Treiber": multi("Wachstum", "Inflation", "Zinsen"),
         "Zusammenfassung": rich(summary), "Quelle": select("Bot")}
    if upcoming:
        p["Gültig bis"] = date(upcoming[0])
    return p


def find_row(n: Notion, db: str) -> str | None:
    data = n.req("POST", f"/databases/{db}/query", {
        "filter": {"property": "Thema", "title": {"equals": PAGE_TITLE}}, "page_size": 5})
    return data["results"][0]["id"] if data["results"] else None


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    state = json.loads((OUT_DIR / "current.json").read_text(encoding="utf-8"))
    ids = load_ids()
    n = Notion()
    blocks = build_blocks(state)
    page = find_row(n, ids["makro"])
    if page:
        n.req("PATCH", f"/pages/{page}", {"properties": props(state)})
        for b in n.children(page):
            n.req("DELETE", f"/blocks/{b['id']}")
    else:
        page = n.add_row(ids["makro"], props(state))["id"]
    for k in range(0, len(blocks), 50):
        n.req("PATCH", f"/blocks/{page}/children", {"children": blocks[k:k + 50]})
    print(f"Regime-Roadmap: https://www.notion.so/{page.replace('-', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
