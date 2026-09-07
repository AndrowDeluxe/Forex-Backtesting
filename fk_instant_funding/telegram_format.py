"""Telegram-Layout fuer FK Instant Funding -- war urspruenglich das Vorbild
fuer EK-Portfolio-Bridge/core/telegram_format.py::ek_message() (siehe dessen
Docstring) und Funded-Portfolio-Bridge/telegram_format.py::challenge_message(),
lebte bisher aber nur als privates `_fk_message()` direkt in paper_bot.py statt
in einem eigenen Modul wie bei den beiden Geschwistern (Fund 2026-09-02:
Telegram-Logik-Abgleich, war seitdem nicht mehr synchron). Fester 2-Zeilen-
Banner ueber jeder Nachricht -- identisches Format wie ek_message()."""

_BANNER = "\U0001F3E6 FK INSTANT FUNDING"
_RULE = "─" * 24


def fk_message(subtitle: str, body_lines: list[str] | None = None) -> str:
    header = f"{_BANNER}\n{_RULE}\n{subtitle}"
    if body_lines:
        return header + "\n\n" + "\n".join(body_lines)
    return header
