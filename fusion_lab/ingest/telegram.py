"""Telegram-Import ueber Telethon (Strang 0 des Dachprojekts).

Liest ausgewaehlte Gruppen/Kanaele mit dem EIGENEN Konto (Bots koennen fremde
Gruppen nicht lesen) und schreibt je Chat eine JSONL-Datei plus Medien nach
fusion_lab/raw/telegram/<Chat>/. Inkrementell: pro Chat wird die hoechste
gelesene Nachrichten-ID gemerkt (raw/telegram/_state.json), ein zweiter Lauf
zieht nur Neues. Nur LESEN -- das Skript sendet nichts.

Erster Lauf fragt Telefonnummer + Login-Code (ggf. 2FA-Passwort) im Terminal ab,
die Session liegt danach in fusion_lab/.auth/ (gitignored, wie ein Passwort
behandeln).

    python -m fusion_lab.ingest.telegram --list           # Chats mit ID anzeigen
    python -m fusion_lab.ingest.telegram                  # Chats aus secrets.toml
    python -m fusion_lab.ingest.telegram --folder SMH     # ganzer Telegram-Ordner
    python -m fusion_lab.ingest.telegram --chat -100123   # einzelner Chat
    python -m fusion_lab.ingest.telegram --no-media       # nur Text
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from fusion_lab._secrets import AUTH_DIR, RAW_DIR, load_telegram_config
from fusion_lab.ingest.common import load_json, safe_name, save_json

OUT_DIR = RAW_DIR / "telegram"
STATE = OUT_DIR / "_state.json"
SESSION = AUTH_DIR / "telegram"


def _parse_chat(c):
    s = str(c).strip()
    return int(s) if s.lstrip("-").isdigit() else s


async def chats_by_name(client, name: str) -> list:
    """Alle Chats eines Telegram-Ordners (Chat-Filter) mit diesem Namen; gibt es
    keinen solchen Ordner, alle Chats, deren Name den Text enthaelt."""
    from telethon.tl.functions.messages import GetDialogFiltersRequest

    res = await client(GetDialogFiltersRequest())
    for f in getattr(res, "filters", res):
        title = getattr(f, "title", None)
        title = getattr(title, "text", title)
        if isinstance(title, str) and title.strip().lower() == name.lower():
            peers = list(getattr(f, "pinned_peers", [])) + list(getattr(f, "include_peers", []))
            if any(getattr(f, k, False) for k in ("contacts", "non_contacts", "groups", "broadcasts", "bots")):
                print(f"  Hinweis: Ordner '{title}' nutzt Regeln (z.B. 'alle Gruppen') -- "
                      "nur die explizit hinzugefuegten Chats werden gelesen.", flush=True)
            print(f"  Ordner '{title}': {len(peers)} Chats", flush=True)
            return peers
    hits = [d.entity async for d in client.iter_dialogs() if name.lower() in (d.name or "").lower()]
    print(f"  Kein Ordner '{name}' -- {len(hits)} Chats mit '{name}' im Namen", flush=True)
    return hits


def message_record(msg) -> dict:
    return {
        "id": msg.id,
        "date": msg.date.isoformat() if msg.date else None,
        "sender_id": msg.sender_id,
        "text": msg.message or "",
        "reply_to": msg.reply_to.reply_to_msg_id if msg.reply_to else None,
        "media": type(msg.media).__name__ if msg.media else None,
        "forwarded": bool(msg.fwd_from),
    }


async def dump_chat(client, chat, state: dict, media: bool) -> tuple[str, int]:
    entity = await client.get_entity(chat)
    title = getattr(entity, "title", None) or getattr(entity, "username", None) or str(chat)
    key = str(entity.id)
    folder = OUT_DIR / safe_name(f"{title}__{entity.id}")
    (folder / "media").mkdir(parents=True, exist_ok=True)
    last_id = state.get(key, {}).get("last_id", 0)

    n = 0
    newest = last_id
    with open(folder / "messages.jsonl", "a", encoding="utf-8") as fh:
        # reverse=True: aelteste zuerst, damit ein Abbruch nur den Rest verliert
        async for msg in client.iter_messages(entity, min_id=last_id, reverse=True):
            rec = message_record(msg)
            if media and msg.media and (msg.photo or msg.document):
                try:
                    path = await msg.download_media(file=str(folder / "media" / f"{msg.id}_"))
                    rec["media_file"] = Path(path).name if path else None
                except Exception as e:  # einzelnes Medium darf den Lauf nicht stoppen
                    rec["media_error"] = str(e)
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
            newest = max(newest, msg.id)
            if n % 200 == 0:
                state[key] = {"title": title, "last_id": newest}
                save_json(STATE, state)
                print(f"    {n} Nachrichten ...", flush=True)
    state[key] = {"title": title, "last_id": newest}
    save_json(STATE, state)
    return title, n


async def run(args) -> int:
    from telethon import TelegramClient  # erst hier, damit --help ohne Paket laeuft

    cfg = load_telegram_config()
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    async with TelegramClient(str(SESSION), int(cfg["api_id"]), cfg["api_hash"]) as client:
        if args.list:
            async for d in client.iter_dialogs():
                kind = "Kanal" if d.is_channel and not d.is_group else ("Gruppe" if d.is_group else "Chat")
                print(f"{d.id:>16}  {kind:6}  {d.name}")
            return 0
        chats = [_parse_chat(c) for c in (args.chat or cfg.get("chats", []))]
        folder = args.folder or cfg.get("folder")
        if folder and not args.chat:
            chats += await chats_by_name(client, folder)
        if not chats:
            print("Keine Chats gewaehlt -- [telegram] folder = \"SMH\" bzw. chats = [...] "
                  "in secrets.toml eintragen oder --folder/--chat angeben.", file=sys.stderr)
            return 1
        state = load_json(STATE, {})
        for chat in chats:
            title, n = await dump_chat(client, chat, state, media=not args.no_media)
            print(f"  {title}: {n} neue Nachrichten", flush=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--list", action="store_true", help="alle Chats mit ID auflisten")
    ap.add_argument("--chat", action="append", help="Chat-ID oder @username (mehrfach moeglich)")
    ap.add_argument("--folder", help="alle Chats eines Telegram-Ordners, z.B. SMH")
    ap.add_argument("--no-media", action="store_true", help="keine Bilder/Dateien laden")
    return asyncio.run(run(ap.parse_args(argv)))


if __name__ == "__main__":
    sys.exit(main())
