"""Laedt die Zugangsdaten fuer den Material-Import aus .streamlit/secrets.toml
-- gleiches Muster wie news_calendar/_secrets.py (dieselbe Datei, eigene
Abschnitte [onenote] und [telegram])."""

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SECRETS_PATH = REPO_ROOT / ".streamlit" / "secrets.toml"

# Login-Caches (MSAL-Token, Telethon-Session) -- gitignored, nie committen.
AUTH_DIR = Path(__file__).resolve().parent / ".auth"
# Importiertes Rohmaterial (private Notizen/Chats) -- gitignored.
RAW_DIR = Path(__file__).resolve().parent / "raw"


def _section(name: str, required: tuple[str, ...]) -> dict:
    if not SECRETS_PATH.exists():
        raise FileNotFoundError(
            f"{SECRETS_PATH} nicht gefunden -- Abschnitt [{name}] anlegen, "
            f"siehe fusion_lab/README.md."
        )
    data = tomllib.loads(SECRETS_PATH.read_text(encoding="utf-8"))
    sec = data.get(name, {})
    missing = [k for k in required if not sec.get(k)]
    if missing:
        raise ValueError(
            f"{SECRETS_PATH}: Abschnitt [{name}] braucht {', '.join(missing)} "
            f"(siehe fusion_lab/README.md)."
        )
    return sec


def load_onenote_config() -> dict:
    return _section("onenote", ("client_id",))


def load_telegram_config() -> dict:
    return _section("telegram", ("api_id", "api_hash"))
