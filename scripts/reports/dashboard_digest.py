"""Extrahiert die offenen Punkte aus knowledge/DASHBOARD.md und schickt sie
als kompakten Telegram-Digest. Nutzerwunsch 2026-09-06: jeden Morgen 8:00
den aktuellen Dashboard-Stand per Telegram statt es nur beim Reinschauen zu
sehen. Wiederverwendet telegram_notify.py/telegram_config.py aus diesem
Ordner (gleiche Quelle wie der Weekly-Report) -- ohne lokale
telegram_config.py tut send_telegram_message() einfach nichts.

UMBAU 2026-09-11 (Nutzerfeedback: "ich habe heute morgen 4 Seiten Dashboard
bekommen, das ist viel zu viel"): der Digest schuettete bis dahin JEDEN
offenen Punkt im VOLLTEXT aus. Mit den ausfuehrlichen Eintraegen vom
2026-09-09/10 (inkl. Markdown-Tabellen) waren das gemessene 16.066 Zeichen
= 4 Telegram-Nachrichten. Zwei Aenderungen:

1. EIN EINZEILER JE PUNKT statt Volltext (_item_title()). Der Digest haengt
   damit strukturell nicht mehr an der LAENGE eines Dashboard-Eintrags --
   das war die eigentliche Ursache, nicht die Anzahl der Punkte. Es werden
   weiterhin ALLE offenen Punkte gezeigt (Nutzerentscheid: lieber die volle
   Lage auf einen Blick als eine Top-3-Auswahl).
2. HEALTH-ZEILEN aus den echten Logs/dem State der EK-Bridge (_health_lines()),
   nicht nur aus dem, was im Dashboard STEHT. Genau das haette den 4h
   haengenden CTNL-Exit vom 2026-09-09 am naechsten Morgen sichtbar gemacht,
   statt ihn erst auf Nachfrage zu finden.

Reine Text-Extraktion, kein Parsen der Markdown-Tabellen/Formatierung im
Detail -- erledigte Punkte (mit `~~durchgestrichen~~` markiert) werden
uebersprungen. Bricht bewusst NICHT hart ab, wenn eine Sektion fehlt oder
umbenannt wird (z.B. nach einem weiteren Dashboard-Redesign) -- zeigt dann
nur "(Sektion nicht gefunden)" statt den ganzen Lauf scheitern zu lassen.
Dasselbe gilt fuer die Health-Zeilen: fehlt die Bridge, die DB oder das Log,
entfaellt die Zeile einfach."""

import datetime
import html
import re
import sqlite3
import sys
from pathlib import Path

from telegram_notify import send_telegram_message

REPO_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_PATH = REPO_ROOT / "knowledge" / "DASHBOARD.md"
EK_BRIDGE_PATH = Path(r"C:\Users\andre\EK-Portfolio-Bridge")


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


def _open_raw_items(section_text: str) -> list[str]:
    """Wie `_list_items()`, aber ohne erledigte (`~~durchgestrichen~~`) und
    bewusst OHNE `_clean()`: die `**fett**`-Marker muessen erhalten bleiben,
    weil `_item_title()` den ersten Fettdruck als Titel liest."""
    return [item for item in _list_items(section_text) if not item.startswith("~~")]


def _clean(text: str) -> str:
    """Entfernt Markdown-Zierde (**fett**, `code`) und escaped den Rest fuer
    Telegrams HTML-Parse-Mode (nur &/</> sind dort besonders)."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = text.replace("`", "")
    return html.escape(text, quote=False)


def _item_title(raw_item: str, max_len: int = 72) -> str:
    """Ein Dashboard-Punkt auf EINE Zeile. Konvention im Dashboard: jeder
    Eintrag beginnt mit `**Titel**` -- der erste Fettdruck ist also der Titel.
    Fallback fuer Eintraege ohne Fettdruck: der erste Satz."""
    bold = re.search(r"\*\*(.+?)\*\*", raw_item, re.S)
    title = bold.group(1) if bold else raw_item.split(". ")[0]
    title = re.sub(r"\s+", " ", title).strip(" .:\u2014-")
    # Klammer-Zusaetze wie "(2026-09-09 gefunden)" tragen im Einzeiler nichts bei
    title = re.sub(r"\s*\([^)]*\)\s*$", "", title).strip(" .:\u2014-")
    if len(title) > max_len:
        title = title[:max_len].rsplit(" ", 1)[0] + "\u2026"
    return _clean(title)


def _health_lines() -> list[str]:
    """Echter Betriebszustand der EK-Bridge aus State-DB + Logs
    (Nutzerwunsch 2026-09-11). Defensiv: jeder Teil einzeln gekapselt, der
    Digest darf nie am Health-Abschnitt scheitern."""
    lines: list[str] = []
    today = datetime.date.today().isoformat()

    try:
        db = EK_BRIDGE_PATH / "state" / "ek_portfolio_55918977.sqlite3"
        if db.exists():
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            try:
                scans = con.execute(
                    "SELECT leg, COUNT(*) FROM scan_errors WHERE day=? GROUP BY leg", (today,)
                ).fetchall()
                orders = con.execute(
                    "SELECT COUNT(*) FROM order_failures WHERE day=?", (today,)
                ).fetchone()[0]
            finally:
                con.close()
            if scans:
                worst = max(scans, key=lambda r: r[1])
                total = sum(n for _, n in scans)
                lines.append(
                    f"\u26a0\ufe0f EK: {total} Scan-Fehler ({_clean(worst[0])}), {orders} Order-Fehler"
                )
            elif orders:
                lines.append(f"\u26a0\ufe0f EK: {orders} gescheiterte Orders heute")
            else:
                lines.append("\u2705 EK: keine Scan-/Order-Fehler heute")
    except Exception:  # noqa: BLE001 -- Health ist Beiwerk, nie ein Grund zu scheitern
        pass

    try:
        logs = sorted((EK_BRIDGE_PATH / "logs").glob("run_*.log"))
        for log in reversed(logs[-40:]):
            hit = None
            for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
                if "Aggregiertes offenes Risiko" in line:
                    hit = line
            if hit:
                m = re.search(
                    r"Risiko \(ganzes Konto\): ([\d.]+) \(Deckel dieser Bridge: ([\d.]+), (\d+)%", hit
                )
                if m:
                    offen, deckel = float(m.group(1)), float(m.group(2))
                    pct = offen / deckel * 100 if deckel else 0.0
                    # deutsches Tausendertrennzeichen -- f"{x:,.0f}" liefert "1,001"
                    fmt = lambda v: f"{v:,.0f}".replace(",", ".")
                    lines.append(
                        f"\U0001F4CA EK-Risiko {fmt(offen)} / {fmt(deckel)} EUR ({pct:.0f}% vom Deckel)"
                    )
                break
    except Exception:  # noqa: BLE001
        pass

    lines.extend(_missing_weekly_reports())
    return lines


def _missing_weekly_reports() -> list[str]:
    """Meldet fehlende Weekly-Reports (Fund 2026-09-24).

    Anlass: fuer KW38/2026 wurde nie ein Report erzeugt. Ursache war NICHT
    das Skript, sondern der Scheduler -- der Rechner lag Sonntag 20.09. um
    10:41 im Standby, der Trigger um 18:00 lief ins Leere, und `WakeToRun`
    am Task ist wirkungslos, weil die Windows-Wake-Timer auf "nur wichtige"
    stehen (powercfg SUB_SLEEP RTCWAKE = 0x2 im Netz-, 0x0 im Akkubetrieb).
    `StartWhenAvailable` hat den Lauf auch nach dem Boot um 22:25 nicht
    nachgeholt.

    Warum die Meldung HIER haengt und nicht im Weekly-Task: ein Task, der
    nicht laeuft, kann sich nicht selbst beschweren. Dieser Digest laeuft
    taeglich um 08:00, also zu einer Zeit, zu der der Rechner erfahrungs-
    gemaess laeuft. Und das Task-Scheduler-Operational-Log ist deaktiviert
    (ohne Adminrechte nicht einschaltbar), es gibt also keine andere Spur.

    Geprueft wird die ISO-Woche von vor 7 Tagen: die ist sicher abgelaufen
    und ihr Report damit faellig, egal an welchem Wochentag der Digest
    laeuft."""
    out: list[str] = []
    try:
        weekly = REPO_ROOT / "knowledge" / "reports" / "weekly"
        if not weekly.is_dir():
            return out
        faellig = (datetime.date.today() - datetime.timedelta(days=7)).isocalendar()
        fehlen = [
            art for art, muster in (("Education", "education"), ("Performance", "performance"))
            if not (weekly / f"KW{faellig[1]}_{faellig[0]}_{muster}.md").exists()
        ]
        if fehlen:
            out.append(
                f"⚠️ Weekly-Report KW{faellig[1]}/{faellig[0]} fehlt "
                f"({', '.join(fehlen)}) – Task lief nicht"
            )
    except Exception:  # noqa: BLE001 -- Health ist Beiwerk, nie ein Grund zu scheitern
        pass
    return out


def _bold(text: str) -> str:
    """Ueberschriften kommen NICHT aus Dashboard-Inhalt, sondern sind hier
    im Code fest vorgegeben -- kein Escaping noetig, direkt als <b> nutzbar."""
    return f"<b>{text}</b>"


def build_digest() -> str:
    text = DASHBOARD_PATH.read_text(encoding="utf-8")

    stand_match = re.search(r"\*\*Stand:\s*([\d-]+)\*\*", text)
    stand = stand_match.group(1) if stand_match else "?"

    parts = [_bold(f"\U0001F4CB Dashboard \u2014 Stand {stand}")]

    # --- Betriebszustand zuerst: das ist die Zeile, die morgens zaehlt ---
    aktiv_section = _section(text, "was läuft gerade wirklich")
    if aktiv_section is not None:
        rows = [
            l for l in aktiv_section.splitlines()
            if l.strip().startswith("|") and "---" not in l and "Bot/Bridge" not in l
        ]
        live_geld = sum(
            1 for l in rows if "LIVE" in l and ("echtes Geld" in l or "DRY_RUN=False" in l)
        )
        parts.append(f"\U0001F7E2 {len(rows)} aktive Bots/Bridges \u00b7 {live_geld} mit echtem Geld")
    parts.extend(_health_lines())

    # --- Offene Punkte: ALLE, aber je genau eine Zeile ---
    sections = [
        ("Als Nächstes", "\u25B6\uFE0F ALS N\u00c4CHSTES"),
        ("Braucht deine Bestätigung", "\U0001F50D BRAUCHT DEINE BEST\u00c4TIGUNG"),
        ("Offene Aufgaben", "\U0001F4CC OFFENE AUFGABEN"),
    ]
    for heading, label in sections:
        raw = _section(text, heading)
        if raw is None:
            parts.append(f"\n{_bold(label)}\n (Sektion nicht gefunden \u2014 Struktur geaendert?)")
            continue
        items = _open_raw_items(raw)
        parts.append(f"\n{_bold(f'{label} ({len(items)})')}")
        if items:
            parts.append("\n".join(f" \u2022 {_item_title(i)}" for i in items))
        else:
            parts.append(" (keine offenen Punkte)")

    letzte_section = _section(text, "Letzte Aktivität")
    if letzte_section is not None:
        letzte_items = _list_items(letzte_section)
        if letzte_items:
            parts.append(f"\n\U0001F550 Zuletzt: {_item_title(letzte_items[0], max_len=90)}")

    parts.append("\nVoll: knowledge/DASHBOARD.md")
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
