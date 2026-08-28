"""Telegram-Versand fuer den Weekly/Monthly Checkup - gleiches Muster wie
fk_instant_funding/telegram_notify.py (Token/Chat-ID aus
scripts/reports/telegram_config.py, einer lokalen, in .gitignore
eingetragenen Datei; siehe telegram_config.example.py fuer die Vorlage).
Ohne diese Datei tut send_telegram_message()/send_telegram_document()
einfach nichts - Telegram ist optional, ein Telegram-Fehler darf den
Report-Lauf niemals zum Absturz bringen.

Erweitert den Standard-Nachrichten-Versand um send_telegram_document() (die
Bot-API-Methode sendDocument), damit das fertige PDF direkt als Datei-Anhang
verschickt werden kann, nicht nur eine Text-Zusammenfassung.

Absender-Signatur in Nachrichten: "Quant Trading Bot" (Nutzer-Wunsch,
2026-08-27) - der TATSAECHLICHE Telegram-Bot-Name selbst kann nur ueber
@BotFather (/setname, interaktiv in Telegram) geaendert werden, nicht per
Bot-API - das hier ist nur die Text-Signatur innerhalb der Nachricht."""

import logging
from pathlib import Path

log = logging.getLogger(__name__)

try:
    from telegram_config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
except ImportError:
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID = None, None

SIGNATURE = "Quant Trading Bot"
_MAX_MESSAGE_LEN = 4000


def send_telegram_message(text: str, parse_mode: str | None = None) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    import requests

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for start in range(0, len(text), _MAX_MESSAGE_LEN):
        chunk = text[start : start + _MAX_MESSAGE_LEN]
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": chunk}
        if parse_mode:
            data["parse_mode"] = parse_mode
        try:
            resp = requests.post(url, data=data, timeout=10)
            if resp.status_code != 200:
                log.error("Telegram-Nachricht fehlgeschlagen (Status %s): %s", resp.status_code, resp.text)
        except requests.RequestException as e:
            log.error("Telegram-Nachricht fehlgeschlagen: %s", e)


def send_telegram_document(file_path: str, caption: str | None = None) -> bool:
    """Verschickt eine Datei (z.B. das Checkup-PDF) via Bot-API sendDocument.
    Telegram-Limit fuer Bot-Uploads: 50 MB - ein Weekly-Checkup-PDF liegt
    weit darunter (siehe KW34-Beispiel, ~350 KB). Gibt True bei Erfolg
    zurueck, False sonst (nie eine Exception nach aussen werfen)."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    path = Path(file_path)
    if not path.exists():
        log.error("Telegram-Dokument fehlgeschlagen: Datei nicht gefunden: %s", file_path)
        return False

    import requests

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    data = {"chat_id": TELEGRAM_CHAT_ID}
    if caption:
        data["caption"] = caption[:1024]  # Telegram-Caption-Limit
    try:
        with open(path, "rb") as f:
            resp = requests.post(url, data=data, files={"document": (path.name, f, "application/pdf")}, timeout=60)
        if resp.status_code != 200:
            log.error("Telegram-Dokument fehlgeschlagen (Status %s): %s", resp.status_code, resp.text)
            return False
        return True
    except requests.RequestException as e:
        log.error("Telegram-Dokument fehlgeschlagen: %s", e)
        return False
