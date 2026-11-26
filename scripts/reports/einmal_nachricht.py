"""Schickt eine vorbereitete Textdatei einmalig per Telegram (Erinnerungen/Zusammenfassungen zu festen Zeiten).

    python scripts/reports/einmal_nachricht.py <datei.txt>

Wird von einem einmaligen Task-Scheduler-Eintrag aufgerufen. Kein Handel, kein Commit.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from telegram_notify import send_telegram_message  # noqa: E402

if __name__ == "__main__":
    text = Path(sys.argv[1]).read_text(encoding="utf-8")
    send_telegram_message(text)
    print("gesendet:", sys.argv[1])
