"""Gemeinsame Helfer fuer die Import-Skripte."""

import json
import re
from pathlib import Path

_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_name(name: str, max_len: int = 80) -> str:
    """Windows-taugliche Datei-/Ordnernamen (kein : ? * usw., keine Endpunkte)."""
    name = _BAD.sub("_", (name or "").strip()).rstrip(". ")
    return (name or "unbenannt")[:max_len]


def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
