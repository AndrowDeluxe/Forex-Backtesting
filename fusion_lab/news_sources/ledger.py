"""Quellen-Ledger: je Tag x Symbol x Quelle ein Wert (-1..+1), dazu der Status je Quelle und Lauf.

Muster fusion_lab/macro_agent/ledger.py: nur anhaengen, nie ueberschreiben; ein zweiter Lauf am selben Tag
aendert nichts (erste Fassung gilt). Ausgewertet wird in report.py gegen die Folgerendite ab dem ersten
Schlusskurs NACH dem Aufzeichnungstag (kein Vorgriff). Einziger ehrlicher Test ist vorwaerts.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from fusion_lab.news_sources import config as C

COLUMNS = ["datum", "zeit", "symbol", "klasse", "quelle", "roh", "wert", "n", "status"]
RUNS = C.LEDGER_DIR / "laeufe.csv"
RUN_COLUMNS = ["datum", "zeit", "quelle", "status", "grund", "eintraege"]


def read(path: Path = C.LEDGER) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)
    return pd.read_csv(path, dtype={"roh": str})


def rows(snap: dict) -> list[dict]:
    """Ledger-Zeilen aus einem Snapshot (pipeline.snapshot)."""
    day, ts = snap["datum"], snap["zeit"]
    out = []
    for w in snap["werte"]:
        out.append({"datum": day, "zeit": ts, "symbol": w["symbol"], "klasse": C.UNIVERSE[w["symbol"]]["klasse"],
                    "quelle": w["quelle"], "roh": w["roh"], "wert": w["wert"], "n": w["n"],
                    "status": "ok" if w["wert"] is not None else "zu wenig Daten"})
    for sym, groups in (snap["claude"].get("ergebnis") or {}).items():
        for g, v in groups.items():
            out.append({"datum": day, "zeit": ts, "symbol": sym, "klasse": C.UNIVERSE[sym]["klasse"],
                        "quelle": f"claude_{g}", "roh": v["stimmung"], "wert": v["wert"], "n": len(v["ids"]),
                        "status": "ok"})
    return out


def run_rows(snap: dict) -> list[dict]:
    out = [{"datum": snap["datum"], "zeit": snap["zeit"], "quelle": q, "status": s["status"], "grund": s["grund"],
            "eintraege": s.get("eintraege", 0)} for q, s in snap["quellen"].items()]
    cl = snap["claude"]
    out.append({"datum": snap["datum"], "zeit": snap["zeit"], "quelle": "claude", "status": cl["status"],
                "grund": cl["grund"] or "; ".join(cl.get("warnungen", [])[:3]), "eintraege": sum(
                    len(g) for g in (cl.get("ergebnis") or {}).values())})
    return out


def append(snap: dict, path: Path = C.LEDGER, runs: Path = RUNS) -> int:
    new = pd.DataFrame(rows(snap), columns=COLUMNS)
    old = read(path)
    if len(old) and len(new):
        key = ["datum", "symbol", "quelle"]
        known = set(map(tuple, old[key].astype(str).values))
        new = new[[tuple(r) not in known for r in new[key].astype(str).values]]
    path.parent.mkdir(parents=True, exist_ok=True)
    if len(new):
        new.to_csv(path, mode="a", header=not path.exists(), index=False)
    r = pd.DataFrame(run_rows(snap), columns=RUN_COLUMNS)
    r.to_csv(runs, mode="a", header=not runs.exists(), index=False)
    return len(new)
