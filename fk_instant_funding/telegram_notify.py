"""Optionale Telegram-Benachrichtigungen fuer den FK-Instant-Funding-Paper-Bot
(2026-08-25) - identisches Muster wie gold_smc_htf_ltf/telegram_notify.py:
Token/Chat-ID werden aus fk_instant_funding/telegram_config.py gelesen, einer
lokalen, in .gitignore eingetragenen Datei (siehe telegram_config.example.py
fuer die Vorlage). Ohne diese Datei tut send_telegram_message() nichts -
Telegram ist rein optional, kein Fehler, kein Absturz.

Ein Telegram-Fehler darf niemals einen Scan-Lauf zum Absturz bringen, deshalb
faengt diese Funktion alle eigenen Fehler ab und wirft nichts nach aussen.

queue_message()/flush_queued_messages() (ergaenzt 2026-09-02, Telegram-Logik-
Abgleich): identisches Buendelungs-Muster wie EK-Portfolio-Bridge/core/
telegram_notify.py und Funded-Portfolio-Bridge/telegram_notify.py -- vorher
hatte dieses Modul nur das nackte send_telegram_message(), paper_bot.py baute
die gebuendelte Nachricht ueber eine lokale Liste selbst zusammen (aelteres
Vor-Refactor-Muster, funktional gleichwertig, aber nicht dieselbe
gemeinsame Infrastruktur wie die beiden Schwester-Bridges)."""

import logging

from fk_instant_funding.telegram_format import fk_message

log = logging.getLogger(__name__)

try:
    from fk_instant_funding.telegram_config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
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


_queued: list[str] = []


def queue_message(text: str) -> None:
    """Sammelt eine Nachricht fuer die naechste flush_queued_messages()-
    Buendelung, statt sie sofort zu senden."""
    _queued.append(text)


def flush_queued_messages(subtitle: str = "Scan-Update") -> None:
    """Sendet alle seit dem letzten Flush gesammelten Nachrichten als EINE
    Telegram-Nachricht (Banner + Aufzaehlung) -- kein Versand, wenn der
    Puffer leer ist (kein "es ist nichts passiert"-Spam)."""
    global _queued
    if _queued:
        send_telegram_message(fk_message(subtitle, _queued))
    _queued = []
