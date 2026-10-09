"""Inhaltsverzeichnis fuer den OneNote-Import "Smart Money Trading" (Strang 0).

Liest raw/onenote/_manifest.json und die importierten .md/.png-Dateien und
schreibt zwei Dateien nach raw/onenote/ (gitignored, enthaelt private Titel):

  _toc.md         Abschnitte gruppiert nach Kategorie, je Seitenzahl,
                  Zeitraum, Textmenge, Bilder und Seitentitel
  _pages.csv      eine Zeile je Seite (fuer die spaetere Bestandteile-Liste)

Die Kategorien sind eine grobe Vorsortierung nach Abschnittsnamen; sie
entscheiden nur, wo die Inventur zuerst liest, nicht was verworfen wird.

    python -m fusion_lab.inventory.onenote_toc
"""

import csv
import glob
import json
import os
from collections import defaultdict
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "raw" / "onenote"
ROOT = "Finanzielle Freiheit Neu/Smart Money Trading/"

# Reihenfolge = Prioritaet: die erste passende Regel gewinnt.
CATEGORIES = [
    ("Regeln & Edges", ["Meine Trading Edges", "Trading Checklisten", "Edges und Backtesting",
                        "Backtesting 2026", "Edges und ZSMfassungen", "Zusammenfassungen",
                        "Elite Backtesting", "Wiederholung und Backtesting", "Statistiken und Indikatoren",
                        "Score Templates", "Meine Statistiken"]),
    ("Makro", ["Makro", "Staatsanleihen", "Risk Indikator", "Exogene", "Endogene", "Gatekeeping",
               "Gate Keeping", "GS Prozess", "Bankreports", "News und Auswirkungen",
               "Institutional Mandate", "Fair value"]),
    ("Technik & Methodik", ["IPDA", "Ipda", "Time, Price", "Time and Price", "Multiple Timeframe",
                            "Ranges", "Technische Analyse", "Inst. Trading", "CTNL",
                            "Come to the next Level", "Prozessentwicklung", "Technischer Prozess"]),
    ("Mindset & Persoenlich", ["Reflektion und Goals", "World Wide", "Mindset", "True Identity",
                               "Heilung", "Greator", "Identitätsshift", "Defizite", "Reflektion"]),
    ("Journals", ["Vergangene Journals", "Journals und Progress/", "Lernjournal", "Education Checkups",
                  "Aufgaben und To Dos"]),
    ("Calls & Education (gemischt)", [""]),
]


def category(section: str) -> str:
    for name, keys in CATEGORIES:
        if any(k in section for k in keys):
            return name
    return CATEGORIES[-1][0]


def main() -> int:
    manifest = json.loads((RAW / "_manifest.json").read_text(encoding="utf-8"))
    pages = []
    for pid, v in manifest.items():
        base = RAW / v["path"] / v["file"]
        md = base.with_name(base.name + ".md")
        text = md.stat().st_size if md.exists() else 0
        n_img = len(glob.glob(glob.escape(str(base)) + "_img*"))
        section = v["path"].removeprefix(ROOT)
        pages.append({"section": section, "category": category(section), "title": v["title"],
                      "modified": v["modified"][:10], "order": v.get("order", 0),
                      "level": v.get("level", 0), "text_bytes": text, "images": n_img,
                      "image_only": text < 300 and n_img > 0,
                      "file": os.path.relpath(md, RAW).replace("\\", "/"), "page_id": pid})
    pages.sort(key=lambda p: (p["category"], p["section"], p["order"]))

    with open(RAW / "_pages.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(pages[0]))
        w.writeheader()
        w.writerows(pages)

    by_cat = defaultdict(lambda: defaultdict(list))
    for p in pages:
        by_cat[p["category"]][p["section"]].append(p)

    order = [c for c, _ in CATEGORIES]
    out = ["# Inhaltsverzeichnis „Smart Money Trading“ (OneNote-Import)", "",
           f"{len(pages)} Seiten. „nur Bild“ = weniger als 300 Byte Text, aber Bilder "
           "(Inhalt erst nach OCR lesbar).", "", "| Kategorie | Abschnitte | Seiten | Text kB | nur Bild |",
           "|---|---|---|---|---|"]
    for c in order:
        secs = by_cat.get(c, {})
        ps = [p for s in secs.values() for p in s]
        out.append(f"| {c} | {len(secs)} | {len(ps)} | {sum(p['text_bytes'] for p in ps) // 1000} "
                   f"| {sum(p['image_only'] for p in ps)} |")
    for c in order:
        out += ["", f"## {c}"]
        for s, ps in sorted(by_cat.get(c, {}).items()):
            d = sorted(p["modified"] for p in ps)
            out += ["", f"### {s}",
                    f"{len(ps)} Seiten, {d[0]} bis {d[-1]}, {sum(p['text_bytes'] for p in ps) // 1000} kB Text, "
                    f"{sum(p['images'] for p in ps)} Bilder, {sum(p['image_only'] for p in ps)} nur Bild", ""]
            for p in ps:
                flag = " *(nur Bild)*" if p["image_only"] else ""
                out.append(f"{'  ' * p['level']}- {p['title']} ({p['modified']}, "
                           f"{p['text_bytes'] // 1000} kB){flag}")
    (RAW / "_toc.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{len(pages)} Seiten -> {RAW / '_toc.md'}, {RAW / '_pages.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
