"""Lauf-Protokoll und As-of-Pruefung (Meridian "Run Manifest" + "As-of-Pruefung", 12.11.2026).

Je Fact-Sheet-Lauf eine Zeile in ledger/manifest.jsonl: Stichtag, Erzeugung, Git-Stand, Stand je
Datenbereich (letztes Datum, letzter Abruf), Status des letzten Datenlaufs, Zahl der Werte und Luecken,
Ergebnis der As-of-Pruefung.

As-of-Pruefung: Kein Datum im Fact Sheet unter Schluesseln, die einen Messwert datieren
(datum/date/tag/stand), darf nach dem Stichtag liegen. Termine in der Zukunft (naechster_termin,
Kalender) sind erlaubt und stehen unter anderen Schluesseln.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pandas as pd

from fusion_lab.macro_data import store

MANIFEST = Path(__file__).resolve().parent / "ledger" / "manifest.jsonl"
DATED_KEYS = {"datum", "date", "tag", "stand", "news_stand", "letzter_termin"}
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}")


def asof_violations(node, as_of: pd.Timestamp, path: str = "") -> list[str]:
    out = []
    if isinstance(node, dict):
        for k, v in node.items():
            p = f"{path}.{k}" if path else str(k)
            if k in DATED_KEYS and isinstance(v, str) and ISO.match(v) and pd.Timestamp(v[:10]) > as_of:
                out.append(f"{p} = {v[:10]}")
            else:
                out += asof_violations(v, as_of, p)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out += asof_violations(v, as_of, f"{path}[{i}]")
    return out


def _git() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              cwd=Path(__file__).resolve().parents[2], timeout=10).stdout.strip() or None
    except Exception:
        return None


def sources_state() -> dict:
    out = {}
    for area in ("macro", "markets", "positioning"):
        df = store.read_all(area)
        if len(df):
            out[area] = {"letztes_datum": str(pd.Timestamp(df["date"].max()).date()),
                         "letzter_abruf": str(pd.Timestamp(df["fetched_at"].max()))[:19], "reihen": int(df["key"].nunique())}
    run = store.DATA_DIR / "last_run.json"
    if run.exists():
        status = json.loads(run.read_text(encoding="utf-8"))
        out["datenlauf"] = {"zeit": status.get("lauf"),
                            "fehler": [k for k, v in status.get("quellen", {}).items() if "fehler" in v]}
    return out


def record(sheet: dict) -> dict:
    as_of = pd.Timestamp(sheet["stand"])
    viol = asof_violations({k: v for k, v in sheet.items() if k != "register"}, as_of)
    return {"stand": sheet["stand"], "erzeugt": sheet["erzeugt"], "git": _git(), "quellen": sources_state(),
            "zahlen": len(sheet.get("register", {})), "luecken": len(sheet.get("datenluecken", [])),
            "asof_ok": not viol, "asof_verstoesse": viol[:20]}


def write(rec: dict, path: Path = MANIFEST) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
