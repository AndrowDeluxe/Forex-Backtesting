"""OneNote-Abschnitt "Makro Education" vollstaendig auslesen (Nutzerauftrag 24.11.2026).

Die Inventur vom 12.10. las nur den Seitentext; die Inhalte stecken aber in ~540 Bildern
(eingefuegte Folien, Charts, PDF-Ausdrucke) und drei PDF-Anhaengen. Dieses Skript schickt je
Seite den Text, den PDF-Text (pypdf) und die Bilder paketweise an den lokalen Claude Code
(Abo, `claude.exe -p`, nur Lese-Werkzeug) und sammelt strukturiert:
Kernaussagen, Wirkketten (Ausloeser -> Weg -> Asset, Bedingungen, Zeithorizont, Schwellen),
Regeln, eigene Auswertungen des Nutzers, unlesbare Stellen.

    python -m fusion_lab.inventory.makro_education_extract            # alle offenen Seiten
    python -m fusion_lab.inventory.makro_education_extract --limit 1  # Probe

Ausgabe: fusion_lab/data/onenote_macro/makro_education_v2/<Seite>.json (Wiederaufnahme: fertige
Seiten werden uebersprungen).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from fusion_lab.copy_trading.extract import claude_exe

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "fusion_lab/raw/onenote/Finanzielle Freiheit Neu/Smart Money Trading/Education 2025"
# Abschnitt -> (Quelle, Ausgabe); "Makro Angelo" (Elite 2, Regime-Lehre) seit 24.11. mit dabei
SECTIONS = {"education": (BASE / "Makro Education", ROOT / "fusion_lab/data/onenote_macro/makro_education_v2"),
            "angelo": (BASE / "Elite 2" / "Makro Angelo", ROOT / "fusion_lab/data/onenote_macro/makro_angelo_v2"),
            # eigene Aufarbeitung des Incentive-Prozesses (endogen/exogen) und Journal-Seite Gatekeeping
            "gs_exogen": (BASE / "Incentice 3 2025/Aufarbeitung GS Prozess/Aufarbeitung Exogener Makro Prozess",
                          ROOT / "fusion_lab/data/onenote_macro/gs_prozess_v2"),
            "gs_endogen": (BASE / "Incentice 3 2025/Aufarbeitung GS Prozess/Ausarbeitung Endogener Makro Prozess",
                           ROOT / "fusion_lab/data/onenote_macro/gs_prozess_v2"),
            # Sonderausbildung 2026 (Liquiditaet, Volatilitaet, Banken/FTL, Settlement, IPDA, Bonds/ZB1), Nutzerhinweis 25.11.
            "incentive_2026": (BASE.parent / "Education 2026" / "Incentive Nacharbeitung",
                               ROOT / "fusion_lab/data/onenote_macro/incentive_2026_v2"),
            "gatekeeping": (BASE.parent / "Journals und Progress/Wissensdatenbank/2025/Technische und mentale Defizite",
                            ROOT / "fusion_lab/data/onenote_macro/gs_prozess_v2")}
SRC, OUT = SECTIONS["education"]
MODEL = "sonnet"
IMGS_PER_CALL = 14
PDF_CHARS = 60_000

PROMPT = """Du liest eine Seite aus dem OneNote-Abschnitt "Makro Education" eines Traders (Coaching-Material,
Bank-Reports, eigene Notizen). Lies den Seitentext unten und JEDES aufgefuehrte Bild mit dem Read-Werkzeug
(Folien, Charts, Tabellen, Handschrift). Erfinde nichts: nur, was auf der Seite/den Bildern steht.

Gib NUR ein JSON-Objekt zurueck:
{{
 "seite": "{title}",
 "thema": "1 Satz",
 "kernaussagen": ["..."],
 "wirkketten": [{{
    "ausloeser": "z. B. CPI ueber Konsens",
    "weg": ["Schritt 1", "Schritt 2"],
    "assets": {{"USD": "steigt"}},
    "bedingungen": "nur wenn ... (oder leer)",
    "zeithorizont": "Termin-Reaktion (Minuten/Stunden) | Tage | Wochen | Monate | unklar",
    "schwellen": "Zahlen/Schwellen wie genannt (oder leer)",
    "beleg_auf_seite": "Beispiel/Chart/Statistik, falls gezeigt (oder leer)",
    "quelle": "Text oder Bilddatei"
 }}],
 "regeln": ["Handels-/Analyseregeln, Checklisten, Kein-Trade-Regeln"],
 "eigene_auswertungen": ["Trefferquoten, Pips, Stichproben, Backtests des Traders"],
 "daten_genannt": ["Indikatoren/Reihen, die genannt werden"],
 "herkunft": "eigene Notiz | Coaching-Folie | Bank-Report | Fremdtext | gemischt",
 "unlesbar": ["Bilder/Stellen, die nicht lesbar waren"]
}}

{part}
Seitentext:
{text}

{pdf}
Bilder (mit Read oeffnen):
{images}
"""


def pages() -> list[Path]:
    return sorted(SRC.glob("*.md"))


def assets(md: Path) -> tuple[list[Path], list[Path]]:
    stem = md.stem
    imgs = sorted((p for p in SRC.glob(f"{glob_escape(stem)}_img*") if p.suffix.lower() in (".png", ".jpeg", ".jpg")),
                  key=lambda p: int(re.search(r"_img(\d+)", p.name).group(1)))
    pdfs = sorted(SRC.glob(f"{glob_escape(stem)}_att_*.pdf"))
    return imgs, pdfs


def glob_escape(s: str) -> str:
    return re.sub(r"([\[\]*?])", r"[\1]", s)


def pdf_text(pdfs: list[Path]) -> str:
    if not pdfs:
        return ""
    from pypdf import PdfReader
    out = []
    for p in pdfs:
        try:
            r = PdfReader(str(p))
            out.append(f"PDF-Anhang {p.name} ({len(r.pages)} Seiten):\n" +
                       "\n".join((pg.extract_text() or "") for pg in r.pages))
        except Exception as e:  # defekte PDFs: Bilder reichen
            out.append(f"PDF-Anhang {p.name}: nicht lesbar ({e})")
    return "\n\n".join(out)[:PDF_CHARS]


def parse_obj(text: str) -> dict:
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        raise ValueError("kein JSON-Objekt in der Antwort")
    return json.loads(m.group(0))


def call(exe: str, prompt: str) -> dict:
    res = subprocess.run([exe, "-p", "--model", MODEL, "--allowedTools", "Read", "--output-format", "json"],
                         input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=1800, cwd=str(SRC))
    if res.returncode != 0:
        msg = res.stderr or res.stdout
        if "usage_limit_reached" in msg:  # Abo-Grenze: abbrechen statt alle Seiten durchzuprobieren
            raise SystemExit(f"Abo-Nutzungsgrenze erreicht, spaeter fortsetzen: {msg[-600:]}")
        raise RuntimeError(f"claude.exe rc={res.returncode}: {msg[-400:]}")
    return parse_obj(json.loads(res.stdout).get("result", ""))


def merge(parts: list[dict]) -> dict:
    out = dict(parts[0])
    for p in parts[1:]:
        for k in ("kernaussagen", "wirkketten", "regeln", "eigene_auswertungen", "daten_genannt", "unlesbar"):
            out[k] = (out.get(k) or []) + (p.get(k) or [])
    return out


def run_page(exe: str, md: Path) -> dict:
    text = md.read_text(encoding="utf-8")[:20_000]
    title = text.splitlines()[0].lstrip("# ").strip() if text else md.stem
    imgs, pdfs = assets(md)
    pdf = pdf_text(pdfs)
    chunks = [imgs[i:i + IMGS_PER_CALL] for i in range(0, len(imgs), IMGS_PER_CALL)] or [[]]
    parts = []
    for n, chunk in enumerate(chunks):
        part = "" if len(chunks) == 1 else f"(Teil {n + 1} von {len(chunks)} der Bilder; Text/PDF stehen in jedem Teil)\n"
        prompt = PROMPT.format(title=title.replace('"', "'"), part=part, text=text,
                               pdf=pdf if n == 0 else ("(PDF-Text siehe Teil 1)" if pdf else ""),
                               images="\n".join(str(p) for p in chunk) or "(keine)")
        parts.append(call(exe, prompt))
    rec = merge(parts)
    rec.update({"datei": md.name, "bilder": len(imgs), "pdfs": [p.name for p in pdfs], "aufrufe": len(chunks),
                "modell": MODEL})
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only", help="Teil des Seitennamens")
    ap.add_argument("--section", choices=list(SECTIONS), default="education")
    args = ap.parse_args(argv)
    global SRC, OUT
    SRC, OUT = SECTIONS[args.section]
    OUT.mkdir(parents=True, exist_ok=True)
    exe = claude_exe()
    todo = [p for p in pages() if not (OUT / f"{p.stem}.json").exists()]
    if args.only:
        todo = [p for p in todo if args.only.lower() in p.stem.lower()]
    todo = todo[: args.limit] if args.limit else todo
    print(f"{len(todo)} Seiten offen", flush=True)
    fails = 0
    for md in todo:
        try:
            rec = run_page(exe, md)
            (OUT / f"{md.stem}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"  ok {md.stem[:50]}: {len(rec.get('wirkketten', []))} Ketten, {rec['bilder']} Bilder", flush=True)
        except Exception as e:
            fails += 1
            print(f"  FEHLER {md.stem[:50]}: {type(e).__name__}: {str(e)[:200]}", flush=True)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
