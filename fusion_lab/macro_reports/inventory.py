"""Inventur der SMH-Makro-Reports aus dem Telegram-Kanal "SMH Daily Update"
(Phase 1, Schritt 1 -- Plan: knowledge/projects/smh-makro-reports-backtest.md).

Liest alle PDFs des Kanals, klassifiziert sie (Makroreport / Preview /
Arbeitsblatt / Sonstiges), ordnet die Format-Generation zu und schreibt
fusion_lab/data/macro_reports/inventory.csv. PDFs ohne Textlayer (Bild-PDFs)
werden nach fusion_lab/data/macro_reports/render/<msg_id>/ als PNG gerendert,
damit sie visuell gelesen werden koennen; der Text der uebrigen landet in
.../text/<msg_id>.txt.

Zeitstempel ist die Telegram-Postzeit (point-in-time), nicht das Datum im PDF.

    python -m fusion_lab.macro_reports.inventory            # bis heute
    python -m fusion_lab.macro_reports.inventory --until 2026-10-07
"""

import argparse
import csv
import json
import logging
import re
from pathlib import Path

import pandas as pd

from fusion_lab._secrets import RAW_DIR

CHANNEL_DIR = RAW_DIR / "telegram" / "SMH Daily Update__2552394198"
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "macro_reports"

# Format-Generationen (Grenzen = Postdatum, gesichtet 2026-10-09):
#   1 Fliesstext "Makroreport dd.mm" (bis 16.11.2025)
#   2 wechselnde Layouts, z. T. Bild-PDFs ("SMH Global Macro Research", Disclaimer vorn)
#   3 "SMT Macro Desk": Regime, G8-Ranking, Szenarien, Trades mit 5 Gates
GEN2_START = pd.Timestamp("2025-11-19", tz="UTC")
GEN3_START = pd.Timestamp("2026-06-28", tz="UTC")

_REPORT = re.compile(r"makro\s*-?\s*repo?r?t|macro\s*-?\s*report|macro\s+research|macro\s+desk|macro\s+update",
                     re.I)
_PREVIEW = re.compile(r"preview|fomc|nfp|cpi\b|briefing", re.I)
_WORKSHEET = re.compile(r"arbeitsblatt|hausaufgabe|incentive|mindset|identit", re.I)
MIN_TEXT_CHARS = 500  # darunter gilt das PDF als Bild-PDF


def generation(ts: pd.Timestamp) -> int:
    return 3 if ts >= GEN3_START else (2 if ts >= GEN2_START else 1)


def classify(head: str) -> str:
    """Reihenfolge zaehlt: Previews heissen oft auch "Macro ...", Gen-1-Reports
    nennen im Kopf "Incentive" (Mitgliederbereich) -- daher Titel zuerst."""
    if _REPORT.search(head[:120]):
        return "makroreport"
    if _WORKSHEET.search(head[:300]):
        return "arbeitsblatt"
    if _PREVIEW.search(head[:200]) and not _REPORT.search(head[:60]):
        return "preview"
    if _REPORT.search(head) or re.match(r"[\d.]{8,10}\s+Big Picture", head):
        return "makroreport"
    return "sonstiges"


def _messages() -> list[dict]:
    rows = []
    with open(CHANNEL_DIR / "messages.jsonl", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def render_pages(pdf: Path, out_dir: Path, zoom: float = 1.6) -> int:
    import pymupdf

    out_dir.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(pdf) as doc:
        for i, page in enumerate(doc):
            target = out_dir / f"p{i + 1:02d}.png"
            if not target.exists():
                page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).save(target)
        return doc.page_count


def build(until: str | None = None) -> pd.DataFrame:
    import pymupdf

    logging.disable(logging.WARNING)
    cutoff = pd.Timestamp(until, tz="UTC") + pd.Timedelta(days=1) if until else None
    (DATA_DIR / "text").mkdir(parents=True, exist_ok=True)
    seen, out = set(), []
    for m in _messages():
        f = m.get("media_file") or ""
        if not f.lower().endswith(".pdf") or m["id"] in seen:
            continue
        seen.add(m["id"])
        ts = pd.Timestamp(m["date"])
        if cutoff is not None and ts >= cutoff:
            continue
        pdf = CHANNEL_DIR / "media" / f
        with pymupdf.open(pdf) as doc:
            text = "\n".join(p.get_text() for p in doc)
            pages = doc.page_count
        is_image = len(text.strip()) < MIN_TEXT_CHARS
        head = " ".join(text.split())[:3000]
        kind = "unklar_bild" if is_image else classify(head)
        if is_image:
            render_pages(pdf, DATA_DIR / "render" / str(m["id"]))
        else:
            (DATA_DIR / "text" / f"{m['id']}.txt").write_text(text, encoding="utf-8")
        out.append({
            "msg_id": m["id"], "posted_utc": ts.isoformat(), "weekday": ts.day_name(),
            "generation": generation(ts), "kind": kind, "pages": pages,
            "image_pdf": is_image, "caption": (m.get("text") or "")[:80].replace("\n", " "),
            "head": head[:160], "file": f,
        })
    df = pd.DataFrame(out).sort_values("posted_utc")
    df.to_csv(DATA_DIR / "inventory.csv", index=False, quoting=csv.QUOTE_NONNUMERIC, encoding="utf-8")
    return df


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--until", help="letztes Postdatum (YYYY-MM-DD), Stichtag der Historie")
    df = build(ap.parse_args(argv).until)
    print(df.groupby(["generation", "kind"]).size().to_string())
    print(f"-> {DATA_DIR / 'inventory.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
