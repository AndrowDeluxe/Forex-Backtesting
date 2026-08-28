"""Optionale Telegram-Benachrichtigungen fuer den Challenge-Portfolio-Paper-Bot
(2026-08-27) - identisches Muster wie fk_instant_funding/telegram_notify.py:
Token/Chat-ID werden aus challenge_portfolio/telegram_config.py gelesen, einer
lokalen, in .gitignore eingetragenen Datei (siehe telegram_config.example.py
fuer die Vorlage). Ohne diese Datei tut send_telegram_message() nichts -
Telegram ist rein optional, kein Fehler, kein Absturz.

Ein Telegram-Fehler darf niemals einen Scan-Lauf zum Absturz bringen, deshalb
faengt diese Funktion alle eigenen Fehler ab und wirft nichts nach aussen."""

import logging

log = logging.getLogger(__name__)

try:
    from challenge_portfolio.telegram_config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
except ImportError:
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID = None, None

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
