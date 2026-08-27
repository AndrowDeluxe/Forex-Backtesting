"""Laedt den FRED-API-Key aus .streamlit/secrets.toml -- gleiches Muster wie
tradingview/_secrets.py (dieselbe Datei, eigener [fred]-Abschnitt)."""

import tomllib
from pathlib import Path

SECRETS_PATH = Path(__file__).resolve().parents[1] / ".streamlit" / "secrets.toml"


def load_fred_api_key() -> str:
    if not SECRETS_PATH.exists():
        raise FileNotFoundError(
            f"{SECRETS_PATH} nicht gefunden -- .streamlit/secrets.toml.example "
            f"dorthin kopieren und [fred] api_key eintragen (kostenloser Key: "
            f"fred.stlouisfed.org/docs/api/api_key.html)."
        )
    data = tomllib.loads(SECRETS_PATH.read_text(encoding="utf-8"))
    key = data.get("fred", {}).get("api_key")
    if not key:
        raise ValueError(f"{SECRETS_PATH}: Abschnitt [fred] braucht api_key.")
    return key
