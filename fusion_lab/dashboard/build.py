"""Baut das statische Dashboard nach fusion_lab/data/dashboard_dist (git-ignoriert)."""

from __future__ import annotations

import glob
import json
import shutil
from datetime import datetime
from pathlib import Path

from fusion_lab.screener import config as C
from fusion_lab.screener.pipeline import macro_context

STATIC = Path(__file__).resolve().parent / "static"
DIST = C.REPO / "fusion_lab" / "data" / "dashboard_dist"

HEADERS = """/data/*
  Cache-Control: no-store
/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: no-referrer
  X-Frame-Options: DENY
  X-Robots-Tag: noindex, nofollow
"""


def latest(kind: str) -> Path | None:
    files = sorted(glob.glob(str(C.DATA_DIR / f"????-??-??_{kind}.json")))
    return Path(files[-1]) if files else None


def commodities() -> dict | None:
    """Tageslauf Rohstoffe + neueste Wochen-Tiefenanalyse je Rohstoff (archive/rohstoffe_tief). Auch ohne
    Tageslauf gibt es eine Datei, sobald eine Wochenanalyse existiert (z. B. Kupfer 18.11.2026)."""
    import sys
    sys.path.insert(0, str(C.REPO / "scripts" / "reports"))
    from commodity_deep import latest as latest_deep
    src = latest("rohstoffe")
    r = json.loads(src.read_text(encoding="utf-8")) if src else None
    woche = latest_deep()
    if r is None and not woche:
        return None
    r = r or {"screener": "rohstoffe", "stand": None, "tief": [], "tabelle": [], "anzahl": 0, "signale": {}}
    r["tief_woche"] = woche
    return r


def build(dist: Path = DIST) -> Path:
    if dist.exists():
        shutil.rmtree(dist)
    shutil.copytree(STATIC, dist)
    data = dist / "data"
    data.mkdir()
    for kind in ("aktien", "krypto"):
        src = latest(kind)
        if src:
            shutil.copy(src, data / f"{kind}.json")
    roh = commodities()
    if roh:
        (data / "rohstoffe.json").write_text(json.dumps(roh, ensure_ascii=False, default=str), encoding="utf-8")
    agenten = C.REPO / "fusion_lab" / "agent_forward" / "ledger" / "summary.json"   # TradingAgents-Forward
    if agenten.exists():
        shutil.copy(agenten, data / "agenten.json")
    mc = macro_context()
    if mc:
        (data / "makro.json").write_text(json.dumps(mc, ensure_ascii=False, default=str), encoding="utf-8")
    (data / "meta.json").write_text(json.dumps({"gebaut": datetime.now().strftime("%d.%m.%Y %H:%M")}), encoding="utf-8")
    (dist / "_headers").write_text(HEADERS, encoding="utf-8")
    (dist / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    return dist
