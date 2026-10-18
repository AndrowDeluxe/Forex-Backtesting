"""Edge Cards aus knowledge/ als Unterseiten des Ordners "📁 Edge Cards" in der
ELITE-3-Datenbank veroeffentlichen. Quelle der Wahrheit bleibt die Datei im
Repo; ein erneuter Lauf ersetzt die Notion-Seite gleichen Titels.

    python -m fusion_lab.notion.edge_cards knowledge/projects/keylevel-edge-card-final.md
"""

import json
import re
import sys
from datetime import date as _date
from pathlib import Path

from fusion_lab.notion.client import IDS_FILE, Notion, date, load_ids, rich, select, title

FOLDER_TITLE = "📁 Edge Cards"
FIELD_RE = re.compile(r"^0[1-5] [A-ZÄÖÜ]+$")


def _rt(text: str) -> list:
    # Notion begrenzt Textstuecke auf 2000 Zeichen
    return [{"type": "text", "text": {"content": text[i:i + 2000]}} for i in range(0, len(text), 2000)] or \
        [{"type": "text", "text": {"content": ""}}]


def _block(kind: str, text: str) -> dict:
    return {"object": "block", "type": kind, kind: {"rich_text": _rt(text)}}


def md_to_blocks(text: str) -> tuple[str, list[dict]]:
    """Schlichtes Edge-Card-Textformat -> (Kartentitel, Notion-Bloecke)."""
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    lines = [l.rstrip() for l in text.splitlines()]
    card_title, blocks = None, []
    for raw in lines:
        line = raw.strip()
        if not line or line == "EDGE CARD":
            continue
        if card_title is None:
            card_title = line
            continue
        if FIELD_RE.match(line):
            blocks.append(_block("heading_2", line))
        elif line in ("Vollständige Ausgangsthese", "Level", "Frischer Anlauf", "Ereignis", "Messung",
                      "Ausschlüsse") or line.startswith("Kontext (Stufe 2"):
            blocks.append(_block("heading_3", line))
        elif re.match(r"^\d+\. ", line):
            # Originalnummer behalten: Notion zaehlt Listen nach jeder Ueberschrift neu ab 1
            blocks.append(_block("paragraph", line))
        elif line.startswith(("• ", "- ")):
            blocks.append(_block("bulleted_list_item", line[2:]))
        elif line.startswith(("Wichtig:", "Kern:", "Merksatz:", "Ergebnis:")):
            blocks.append({"object": "block", "type": "callout", "callout": {
                "rich_text": _rt(line), "icon": {"type": "emoji", "emoji": "💡"}}})
        else:
            blocks.append(_block("paragraph", line))
    return card_title or "Edge Card", blocks


def ensure_folder(n: Notion) -> str:
    ids = load_ids()
    if ids.get("edge_cards_folder"):
        return ids["edge_cards_folder"]
    page = n.add_row(ids["elite3"], {
        "Titel": title(FOLDER_TITLE), "Art": select("Edge Card"),
        "Datum": date(_date.today().isoformat()), "Status": select("in Arbeit"),
        "Bot-Beitrag": rich("Ordner: je Edge Card eine Unterseite. Quelle der Wahrheit: knowledge/projects/*-edge-card*.md"),
    })
    ids["edge_cards_folder"] = page["id"]
    IDS_FILE.write_text(json.dumps(ids, indent=2, ensure_ascii=False), encoding="utf-8")
    return page["id"]


def publish(md_path: str) -> str:
    n = Notion()
    folder = ensure_folder(n)
    card_title, blocks = md_to_blocks(Path(md_path).read_text(encoding="utf-8"))
    page_title = f"Edge Card: {card_title}"
    for b in n.children(folder):  # gleiche Karte ersetzen statt doppeln
        if b["type"] == "child_page" and b["child_page"]["title"] == page_title:
            n.req("PATCH", f"/pages/{b['id']}", {"archived": True})
    page = n.req("POST", "/pages", {
        "parent": {"page_id": folder},
        "icon": {"type": "emoji", "emoji": "🃏"},
        "properties": {"title": [{"text": {"content": page_title}}]},
        "children": blocks[:100]})
    for i in range(100, len(blocks), 100):
        n.req("PATCH", f"/blocks/{page['id']}/children", {"children": blocks[i:i + 100]})
    return page.get("url", page["id"])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    for p in sys.argv[1:]:
        print(publish(p))
