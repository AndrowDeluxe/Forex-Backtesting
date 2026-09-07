"""Second-Brain-Lint fuer knowledge/ (siehe CLAUDE.md Regel 6).

Prueft automatisierbare Teile des Lint-Checks:
  (a) tote [[wikilinks]] ohne Ziel-Datei
  (b) veraltete "Zuletzt geprueft"-Daten in der DASHBOARD.md-Statustabelle
  (d) verwaiste Seiten ohne eingehende Links (nur PARA-Ordner)
  (e) unverarbeitete Dateien in Clippings/ (Raw-Inbox: Web-Clips, PDFs,
      Bilder, eigene Notizen -- noch von keiner PARA-Notiz referenziert)

(c) Widersprueche zwischen Notizen ist inhaltlich und bleibt Handarbeit.

Aufruf: python knowledge/scripts/lint.py [--stale-days 21]
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

KNOWLEDGE_ROOT = Path(__file__).resolve().parent.parent
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")

# Ordner, die auf eingehende Links geprueft werden (echte PARA-Notizen).
# Clippings/ (Web-Clips) und reports/ (generierte Wochenberichte) sind
# bewusst ausgenommen -- die verlinken oft *raus* auf Memory-Slugs statt
# untereinander, das ist kein Lint-Befund.
ORPHAN_CHECK_DIRS = {"projects", "areas", "resources", "archive"}


def iter_markdown_files() -> list[Path]:
    return sorted(
        p
        for p in KNOWLEDGE_ROOT.rglob("*.md")
        if "_templates" not in p.parts
    )


def build_target_map(files: list[Path]) -> dict[str, list[Path]]:
    targets: dict[str, list[Path]] = {}
    for f in files:
        targets.setdefault(f.stem.lower(), []).append(f)
    return targets


def find_dead_links(files: list[Path], targets: dict[str, list[Path]]):
    dead = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        for m in WIKILINK_RE.finditer(text):
            raw = m.group(1).strip()
            name = raw.rsplit("/", 1)[-1]  # z.B. [[folder/Name]]
            if name.lower() not in targets:
                line_no = text.count("\n", 0, m.start()) + 1
                dead.append((f.relative_to(KNOWLEDGE_ROOT), line_no, raw))
    return dead


def find_orphans(files: list[Path], targets: dict[str, list[Path]]):
    linked_to: set[str] = set()
    for f in files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        for m in WIKILINK_RE.finditer(text):
            raw = m.group(1).strip().rsplit("/", 1)[-1]
            if raw.lower() in targets:
                linked_to.add(raw.lower())

    orphans = []
    for f in files:
        rel = f.relative_to(KNOWLEDGE_ROOT)
        if rel.parts[0] not in ORPHAN_CHECK_DIRS:
            continue
        if f.stem.lower() not in linked_to:
            orphans.append(rel)
    return orphans


def find_stale_dashboard_dates(stale_days: int):
    dashboard = KNOWLEDGE_ROOT / "DASHBOARD.md"
    text = dashboard.read_text(encoding="utf-8", errors="ignore")
    today = dt.date.today()
    stale = []
    in_table = False
    for line in text.splitlines():
        if line.startswith("| Bot/Bridge"):
            in_table = True
            continue
        if in_table and not line.startswith("|"):
            break
        if not in_table or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2 or cells[0].startswith("---"):
            continue
        last_cell = cells[-1]
        date_match = DATE_RE.search(last_cell)
        if date_match:
            checked = dt.date.fromisoformat(date_match.group(1))
            age = (today - checked).days
            if age > stale_days:
                stale.append((cells[0], checked.isoformat(), age))
    return stale


def find_unprocessed_clippings() -> list[Path]:
    clippings_dir = KNOWLEDGE_ROOT / "Clippings"
    if not clippings_dir.is_dir():
        return []
    clips = sorted(p for p in clippings_dir.rglob("*") if p.is_file())
    if not clips:
        return []

    # Ein Clip gilt als "verarbeitet", sobald sein Dateiname irgendwo
    # ausserhalb von Clippings/ selbst erwaehnt wird (Wikilink, Klartext-Pfad
    # wie in resources/second-brain-methodik.md, o.ae.) -- reicht als
    # Heuristik, muss keine exakte Verlinkung sein.
    haystack_parts = []
    for f in KNOWLEDGE_ROOT.rglob("*.md"):
        if "_templates" in f.parts or "Clippings" in f.parts:
            continue
        haystack_parts.append(f.read_text(encoding="utf-8", errors="ignore"))
    haystack = "\n".join(haystack_parts)

    return [
        clip.relative_to(KNOWLEDGE_ROOT)
        for clip in clips
        if clip.name not in haystack and clip.stem not in haystack
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stale-days", type=int, default=21)
    args = parser.parse_args()

    files = iter_markdown_files()
    targets = build_target_map(files)

    dead_links = find_dead_links(files, targets)
    orphans = find_orphans(files, targets)
    stale = find_stale_dashboard_dates(args.stale_days)
    unprocessed_clippings = find_unprocessed_clippings()

    print(f"# Second-Brain-Lint ({dt.date.today().isoformat()})\n")

    print(f"## Tote Wikilinks ({len(dead_links)})")
    for rel, line_no, raw in dead_links:
        print(f"- {rel}:{line_no} -> [[{raw}]]")
    if not dead_links:
        print("- keine")

    print(f"\n## Verwaiste Seiten ohne eingehende Links ({len(orphans)})")
    for rel in orphans:
        print(f"- {rel}")
    if not orphans:
        print("- keine")

    print(f"\n## Veraltete 'Zuletzt geprueft'-Daten (> {args.stale_days} Tage) ({len(stale)})")
    for name, date, age in stale:
        print(f"- {name}: {date} ({age} Tage alt)")
    if not stale:
        print("- keine")

    print(f"\n## Unverarbeitete Clippings ({len(unprocessed_clippings)})")
    for rel in unprocessed_clippings:
        print(f"- {rel}")
    if not unprocessed_clippings:
        print("- keine")

    return 0


if __name__ == "__main__":
    sys.exit(main())
