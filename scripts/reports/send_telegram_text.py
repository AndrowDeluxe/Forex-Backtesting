"""Schickt den Inhalt einer Textdatei per Telegram (telegram_notify.py, Token aus telegram_config.py).

    python scripts/reports/send_telegram_text.py <datei>

Exit 0 = versendet, 1 = Datei fehlt/leer, 2 = kein Telegram-Konfig.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from telegram_notify import TELEGRAM_BOT_TOKEN, send_telegram_message  # noqa: E402

if __name__ == "__main__":
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not p or not p.exists() or not p.read_text(encoding="utf-8").strip():
        print("Datei fehlt oder ist leer")
        sys.exit(1)
    if not TELEGRAM_BOT_TOKEN:
        print("telegram_config.py fehlt")
        sys.exit(2)
    send_telegram_message(p.read_text(encoding="utf-8"))
    print(f"versendet: {p}")
