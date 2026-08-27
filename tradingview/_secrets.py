"""Laedt TradingView-Pro-Zugangsdaten aus .streamlit/secrets.toml -- dieselbe
Datei/derselbe Gitignore-Eintrag, den dieses Repo bereits fuer Streamlit-Secrets
reserviert (siehe .gitignore), hier per stdlib tomllib gelesen (nicht ueber
Streamlit selbst, da data.py/screenshot.py auch ausserhalb einer laufenden
Streamlit-App genutzt werden sollen, z.B. aus eigenstaendigen Skripten)."""

import tomllib
from pathlib import Path

SECRETS_PATH = Path(__file__).resolve().parents[1] / ".streamlit" / "secrets.toml"


def load_credentials() -> tuple[str, str]:
    """Wirft FileNotFoundError/ValueError mit einer erklaerenden Meldung, wenn die
    Datei fehlt oder unvollstaendig ist -- Aufrufer, die auch ohne Login
    funktionieren (z.B. fetch_ohlcv), fangen FileNotFoundError ab und fallen auf
    anonymen Zugriff zurueck."""
    if not SECRETS_PATH.exists():
        raise FileNotFoundError(
            f"{SECRETS_PATH} nicht gefunden -- .streamlit/secrets.toml.example "
            f"dorthin kopieren und die echten TradingView-Zugangsdaten eintragen."
        )
    data = tomllib.loads(SECRETS_PATH.read_text(encoding="utf-8"))
    tv = data.get("tradingview", {})
    username, password = tv.get("username"), tv.get("password")
    if not username or not password:
        raise ValueError(f"{SECRETS_PATH}: Abschnitt [tradingview] braucht username UND password.")
    return username, password
