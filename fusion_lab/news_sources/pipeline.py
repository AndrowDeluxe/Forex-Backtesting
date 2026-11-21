"""Ein Lauf: Quellen holen -> Claude ordnet Texte ein -> Snapshot (+ optional ins Ledger)."""

from __future__ import annotations

import datetime as dt
import json

from fusion_lab.news_sources import classify, collectors, ledger
from fusion_lab.news_sources import config as C


def snapshot(symbols: list[str] | None = None, daily: bool = False, use_llm: bool = True) -> dict:
    """Alle Quellen + Claude-Einordnung. Schreibt nichts ins Ledger (das macht record()).
    Speichert den Snapshot als latest.json (git-ignoriert) fuer Dashboards."""
    symbols = [s for s in (symbols or list(C.UNIVERSE)) if s in C.UNIVERSE]
    now = dt.datetime.now().astimezone()
    raw = collectors.collect(symbols, daily=daily)
    items = [it for q in raw.values() for it in q["items"]]
    werte = [w for q in raw.values() for w in q["werte"]]
    if use_llm:
        cl = classify.classify(items)
    else:
        cl = {"status": "aus", "grund": "Claude-Einordnung abgeschaltet", "ergebnis": {}, "warnungen": []}
    snap = {
        "datum": now.date().isoformat(), "zeit": now.isoformat(timespec="seconds"), "symbole": symbols,
        "quellen": {q: {"status": r["status"], "grund": r["grund"], "eintraege": len(r["items"]) + len(r["werte"])}
                    for q, r in raw.items()},
        "items": items, "werte": werte, "claude": cl,
    }
    C.DATA_DIR.mkdir(parents=True, exist_ok=True)
    C.LATEST.write_text(json.dumps(snap, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    with open(C.DATA_DIR / f"snapshots_{snap['datum'][:7]}.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(snap, ensure_ascii=False, default=str) + "\n")
    return snap


def by_symbol(snap: dict) -> dict:
    """Fuer Dashboards: je Symbol Gesamtstimmung (Mittel der Claude-Gruppen), Gruppen, Zahlen, Schlagzeilen."""
    out = {}
    cl = snap["claude"].get("ergebnis") or {}
    for s in snap["symbole"]:
        groups = cl.get(s, {})
        vals = [v["wert"] for v in groups.values()]
        out[s] = {"stimmung": round(sum(vals) / len(vals), 3) if vals else None, "gruppen": groups,
                  "zahlen": [w for w in snap["werte"] if w["symbol"] == s],
                  "schlagzeilen": [it for it in snap["items"] if it["symbol"] == s][:12]}
    return out


def record(daily: bool = True) -> tuple[dict, int]:
    snap = snapshot(daily=daily)
    return snap, ledger.append(snap)
