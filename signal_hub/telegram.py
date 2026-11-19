"""Telegram-Bot-API fuer den Signal-Hub: Foto mit Knoepfen senden, Nachricht aendern, Klicks abholen.

Gleicher Bot wie die uebrigen Meldungen (scripts/reports/telegram_config.py, lokal, gitignored). Ohne Konfiguration
tut jede Funktion nichts (Tests, Trockenlauf). Knopf-Daten: "sh|<id>|<aktion>[|<grund>]" (max. 64 Byte).
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)
_REPO = Path(__file__).resolve().parents[1]


def _cfg():
    sys.path.insert(0, str(_REPO / "scripts" / "reports"))
    try:
        from telegram_config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
        return TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    except ImportError:
        return None, None
    finally:
        sys.path.pop(0)


def _call(method: str, data: dict | None = None, files: dict | None = None, timeout: int = 30) -> dict | None:
    token, _ = _cfg()
    if not token:
        return None
    import requests
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/{method}", data=data, files=files, timeout=timeout)
        js = r.json()
        if not js.get("ok"):
            log.warning("Telegram %s: %s", method, js)
        return js
    except Exception as e:  # Telegram darf den Lauf nie abbrechen
        log.warning("Telegram %s fehlgeschlagen: %s", method, e)
        return None


def keyboard(rows: list[list[tuple[str, str]]] | None) -> str:
    if rows is None:
        return json.dumps({"inline_keyboard": []})
    return json.dumps({"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in row] for row in rows]})


def send_photo(path: str, caption: str, rows=None) -> int | None:
    _, chat = _cfg()
    data = {"chat_id": chat, "caption": caption[:1024]}
    if rows:
        data["reply_markup"] = keyboard(rows)
    with open(path, "rb") as f:
        js = _call("sendPhoto", data, files={"photo": f})
    return (js or {}).get("result", {}).get("message_id")


def send_text(text: str, rows=None, reply_to: int | None = None) -> int | None:
    _, chat = _cfg()
    data = {"chat_id": chat, "text": text[:4000]}
    if rows:
        data["reply_markup"] = keyboard(rows)
    if reply_to:
        data["reply_to_message_id"] = reply_to
    js = _call("sendMessage", data)
    return (js or {}).get("result", {}).get("message_id")


def edit_caption(message_id: int, caption: str, rows=None) -> None:
    _, chat = _cfg()
    _call("editMessageCaption", {"chat_id": chat, "message_id": message_id, "caption": caption[:1024],
                                 "reply_markup": keyboard(rows)})


def edit_markup(message_id: int, rows=None) -> None:
    _, chat = _cfg()
    _call("editMessageReplyMarkup", {"chat_id": chat, "message_id": message_id, "reply_markup": keyboard(rows)})


def answer(callback_id: str, text: str = "") -> None:
    _call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text[:190]})


def get_updates(offset: int | None) -> list[dict]:
    data = {"timeout": 0, "allowed_updates": json.dumps(["callback_query"])}
    if offset is not None:
        data["offset"] = offset
    js = _call("getUpdates", data)
    return (js or {}).get("result", []) or []
