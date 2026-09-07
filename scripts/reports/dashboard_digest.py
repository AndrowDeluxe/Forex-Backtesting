"""Extrahiert die offenen Punkte aus knowledge/DASHBOARD.md und schickt sie
als kompakten Telegram-Digest. Nutzerwunsch 2026-09-06: jeden Morgen 8:00
den aktuellen Dashboard-Stand per Telegram statt es nur beim Reinschauen zu
sehen. Wiederverwendet telegram_notify.py/telegram_config.py aus diesem
Ordner (gleiche Quelle wie der Weekly-Report) -- ohne lokale
telegram_config.py tut send_telegram_message() einfach nichts.

Reine Text-Extraktion, kein Parsen der Markdown-Tabellen/Formatierung im
Detail -- erledigte Punkte (mit `~~durchgestrichen~~` markiert) werden
uebersprungen, offene Punkte unveraendert (nur Markdown-Zierde entfernt)
weitergereicht. Bricht bewusst NICHT hart ab, wenn eine Sektion fehlt oder
umbenannt wird (z.B. nach einem weiteren Dashboard-Redesign) -- zeigt dann
nur "(Sektion nicht gefunden)" statt den ganzen Lauf scheitern zu lassen."""

import html
import re
import sys
from pathlib import Path

from telegram_notify import send_telegram_message

REPO_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_PATH = REPO_ROOT / "knowledge" / "DASHBOARD.md"


def _section(text: str, heading_substring: str) -> str | None:
    """Text zwischen einer Heading-Zeile (##/### ... heading_substring ...)
    und der naechsten Heading-Zeile beliebiger Ebene, oder None, wenn die
    Heading-Zeile nicht gefunden wurde (Sektion umbenannt/entfernt)."""
    pattern = rf"^#{{2,3}}[^\n]*{re.escape(heading_substring)}[^\n]*\n"
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return None
    rest = text[match.end():]
    next_heading = re.search(r"^#{1,6}[ \t]", rest, re.MULTILINE)
    return rest[: next_heading.start()] if next_heading else rest


def _list_items(section_text: str) -> list[str]:
    """Zerlegt eine Markdown-Liste (`-`/`1.`-Items, ueber mehrere Zeilen
    fortgesetzt) in vollstaendige Bloecke (Fortsetzungszeilen an die erste
    Zeile angehaengt), Listenmarker entfernt. Keine Filterung."""
    items: list[str] = []
    current: list[str] = []

    def _flush() -> None:
        if current:
            items.append(" ".join(l.strip() for l in current))
            current.clear()

    for line in section_text.splitlines():
        if re.match(r"^-{3,}\s*$", line):
            _flush()
        elif re.match(r"^(\d+\.|-)\s+", line):
            _flush()
            current.append(line)
        elif not line.strip():
            _flush()
        else:
            if current:
                current.append(line)
    _flush()

    return [re.sub(r"^(\d+\.|-)\s+", "", item) for item in items]


def _open_items(section_text: str) -> list[str]:
    """Wie `_list_items()`, behaelt aber nur Eintraege, die NICHT mit `~~`
    (durchgestrichen = erledigt) beginnen."""
    return [_clean(item) for item in _list_items(section_text) if not item.startswith("~~")]


def _clean(text: str) -> str:
    """Entfernt Markdown-Zierde (**fett**, `code`) und escaped den Rest fuer
    Telegrams HTML-Parse-Mode (nur &/</> sind dort besonders)."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = text.replace("`", "")
    return html.escape(text, quote=False)


def _bold(text: str) -> str:
    """Ueberschriften kommen NICHT aus Dashboard-Inhalt, sondern sind hier
    im Code fest vorgegeben -- kein Escaping noetig, direkt als <b> nutzbar."""
    return f"<b>{text}</b>"


def build_digest() -> str:
    text = DASHBOARD_PATH.read_text(encoding="utf-8")

    stand_match = re.search(r"\*\*Stand:\s*([\d-]+)\*\*", text)
    stand = stand_match.group(1) if stand_match else "?"

    sections = {
        "naechstes": ("Als Nächstes", "▶️ Als Nächstes (offen)"),
        "bestaetigung": ("Braucht deine Bestätigung", "🔍 Braucht deine Bestätigung"),
        "aufgaben": ("Offene Aufgaben", "📌 Offene Aufgaben"),
    }

    parts = [_bold(f"📋 Forex-Backtesting Dashboard — Stand {stand}")]

    for key, (heading, label) in sections.items():
        raw = _section(text, heading)
        parts.append(f"\n{_bold(label + ':')}")
        if raw is None:
            parts.append("(Sektion nicht gefunden - Dashboard-Struktur geaendert?)")
            continue
        items = _open_items(raw)
        if items:
            parts.append("\n\n".join(items))
        else:
            parts.append("(keine offenen Punkte)")

    aktiv_section = _section(text, "was läuft gerade wirklich")
    if aktiv_section is not None:
        rows = [
            l for l in aktiv_section.splitlines()
            if l.strip().startswith("|") and "---" not in l and "Bot/Bridge" not in l
        ]
        live_geld = sum(
            1 for l in rows if "LIVE" in l and ("echtes Geld" in l or "DRY_RUN=False" in l)
        )
        parts.append(f"\n🟢 {len(rows)} aktive Bots/Bridges, davon {live_geld} LIVE mit echtem Geld")

    letzte_section = _section(text, "Letzte Aktivität")
    if letzte_section is not None:
        letzte_items = _list_items(letzte_section)
        if letzte_items:
            parts.append(f"\n🕐 Zuletzt: {_clean(letzte_items[0])}")

    parts.append("\nVolles Dashboard: knowledge/DASHBOARD.md")
    return "\n".join(parts)


def main() -> None:
    # Windows Task Scheduler laeuft oft mit cp1252-Konsole -- ohne das hier
    # crasht print() an den Emojis im Digest (UnicodeEncodeError), NACHDEM
    # die Telegram-Nachricht schon rausgegangen ist.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    digest = build_digest()
    send_telegram_message(digest, parse_mode="HTML")
    print(digest)


if __name__ == "__main__":
    main()
