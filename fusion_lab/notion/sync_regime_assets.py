"""Ergaenzt die Regime-Roadmap (sync_regime.py) um eine Notion-Seite
"Regime-Karte — Assets je Regime": Sharpe je Asset und Regime (gemeinsame Sicht)
fuer das erweiterte Universum (G8-FX-Paare, Kreuze, Metalle, Indizes;
fusion_lab/macro_regime/universe.py) ueber 2000–heute, mit dem Ergebnis des
Richtungsbacktests als Warnhinweis. Inhalt wird bei jedem Lauf ersetzt.

    python -m fusion_lab.macro_regime                 # Regime rechnen
    python -m fusion_lab.notion.sync_regime           # Roadmap (bestehend)
    python -m fusion_lab.notion.sync_regime_assets    # diese Seite
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

import pandas as pd

from fusion_lab.macro_regime import model as m
from fusion_lab.macro_regime.__main__ import current_state
from fusion_lab.macro_regime.universe import GROUPS, universe_returns
from fusion_lab.notion.client import Notion, load_ids

PAGE_TITLE = "Regime-Karte — Assets je Regime"
WARN = ("Kontext, kein Signal: Der Richtungsbacktest (Lock regime_direction, 28.10.2026) fiel durch — "
        "IS 2000–2014 Sharpe 1,60 (Richtungen dort gewählt), OOS 2015–2025 0,14, Tresor (12 Monate) −0,30. "
        "Ursache: 10 Regime × 25 Assets = 250 gewählte Richtungen. Nur Gold hielt im OOS (Sharpe 0,92). "
        "Die Tabellen zeigen historisches Verhalten je Regime, keine Prognose.")


def _rt(text: str, bold: bool = False) -> list:
    return [{"type": "text", "text": {"content": text[:2000]}, "annotations": {"bold": bold}}]


def _block(kind: str, text: str) -> dict:
    return {"object": "block", "type": kind, kind: {"rich_text": _rt(text)}}


def _table(header: list[str], rows: list[list[str]], bold_row: int | None) -> dict:
    def row(cells, bold=False):
        return {"type": "table_row", "table_row": {"cells": [_rt(c, bold) for c in cells]}}
    return {"object": "block", "type": "table",
            "table": {"table_width": len(header), "has_column_header": True, "has_row_header": True,
                      "children": [row(header)] + [row(r, i == bold_row) for i, r in enumerate(rows)]}}


def build_blocks(refresh: bool) -> tuple[list[dict], str]:
    rets = universe_returns(refresh)
    labels = m.daily_labels(rets.index, refresh=refresh)
    rets = rets.loc[labels.index]
    rets = rets[rets.index >= "2000-09-01"]
    st = m.regime_stats(rets, labels.loc[rets.index], "joint")
    sharpe, days = st["sharpe"], st[("days", "n")]
    cur = current_state(refresh)["labels"]["joint"]
    blocks = [_block("callout", WARN),
              _block("paragraph", f"Aktuelles Regime: {cur} (fett markiert). Stand {date.today().isoformat()}. "
                                  "Sharpe = Rendite/Vola p. a.; Original-Assets vs. Cash, FX-Paare ohne Carry, "
                                  "Indizes NDX/DJI/DAX als Preisindex.")]
    regs = list(sharpe.index)
    cur_i = regs.index(cur) if cur in regs else None
    for group, assets in GROUPS.items():
        assets = [a for a in assets if a in sharpe.columns]
        rows = [[reg, str(int(days.loc[reg]))]
                + [f"{sharpe.loc[reg, a]:+.2f}" if pd.notna(sharpe.loc[reg, a]) else "–" for a in assets]
                for reg in regs]
        blocks += [_block("heading_3", group), _table(["Regime", "Tage"] + assets, rows, cur_i)]
    return blocks, cur


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    ids = load_ids()
    n = Notion()
    blocks, cur = build_blocks(args.refresh)
    page = next((b["id"] for b in n.children(ids["root_page"])
                 if b["type"] == "child_page" and b["child_page"]["title"] == PAGE_TITLE), None)
    if page is None:
        page = n.req("POST", "/pages", {"parent": {"page_id": ids["root_page"]},
                                        "properties": {"title": {"title": _rt(PAGE_TITLE)}}})["id"]
    for b in n.children(page):
        n.req("DELETE", f"/blocks/{b['id']}")
    n.req("PATCH", f"/blocks/{page}/children", {"children": blocks})
    print(f"Seite {page}: Regime {cur}, {len(blocks)} Blöcke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
