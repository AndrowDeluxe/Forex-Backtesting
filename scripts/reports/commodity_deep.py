"""Wochen-Tiefenanalyse je Rohstoff (Kupfer-Stil): baut den Prompt je Rohstoff und liest die Ergebnisse.

    python scripts/reports/commodity_deep.py prompt KUPFER     -> Prompt auf stdout (fuer claude.exe -p)
    python scripts/reports/commodity_deep.py liste             -> Schluessel aus config.DEEP_WEEKLY_COMMODITIES, eine Zeile je Rohstoff
    python scripts/reports/commodity_deep.py telegram          -> Sammel-Kurzfassung der neuesten Analysen

Der Task scripts/commodity_deep_task.ps1 ruft das nacheinander je Rohstoff auf (So 18:00).
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from fusion_lab.screener import config as C  # noqa: E402

PROMPT = REPO / "scripts" / "reports" / "commodity_deep_prompt.md"
OUT_DIR = C.ARCHIVE_DIR / "rohstoffe_tief"

# Branchen-Checkliste je Rohstoff (Schritt 4 im Prompt)
CHECK = {
    "GOLD": ["Notenbank-Käufe (WGC, PBoC)", "ETF-Bestände (GLD, physische ETFs)", "Schmuck-/Barren-Nachfrage China/Indien",
             "Minenangebot und Recycling", "Realzinsen und Dollar als Haupttreiber"],
    "SILBER": ["Industrienachfrage (Solar/PV, Elektronik)", "Marktdefizit (Silver Institute)", "ETF-Bestände, LBMA/COMEX-Lager",
               "Minenangebot (Nebenprodukt von Blei/Zink/Kupfer)", "Gold/Silber-Verhältnis"],
    "PLATIN": ["Autokatalysatoren (Diesel, Hybride)", "Angebot Südafrika (Strom, Minen) und Russland",
               "Marktdefizit (WPIC)", "Wasserstoff/Brennstoffzellen", "Lager und Leasingraten"],
    "KUPFER": ["Minenstörungen und Guidance (Chile, Peru, Kongo, Grasberg)", "TC/RC und Hütten-Kürzungen",
               "Lager LME/COMEX/SHFE, COMEX-LME-Prämie, Zölle (Section 232)", "Nachfrage: Stromnetze, KI/Rechenzentren, E-Autos, "
               "Solar, Bau China", "Marktbilanz (ICSG, Banken)"],
    "WTI": ["OPEC+-Förderpolitik und Disziplin", "US-Förderung, Bohranlagen (Baker Hughes), EIA-Lager inkl. Cushing",
            "Raffinerie-Margen, Nachfrage (IEA/EIA/OPEC-Prognosen)", "Geopolitik (Sanktionen, Nahost, Russland)",
            "Terminkurve (Backwardation/Contango)"],
    "BRENT": ["OPEC+-Förderpolitik", "Nordsee/Atlantik-Angebot, Russland-Sanktionen, Tankerverkehr",
              "Nachfrage Asien (China-Importe, Indien)", "Brent-WTI-Spread", "Terminkurve"],
    "ERDGAS": ["US-Speicher (EIA wöchentlich) gegen 5-Jahres-Schnitt", "Wetterprognosen (Heizgradtage)",
               "LNG-Exporte/neue Terminals", "Förderung (Haynesville, Permian)", "Europa TTF als Vergleich"],
    "WEIZEN": ["WASDE (Bestände/Verbrauch-Verhältnis)", "Ernten und Wetter (USA, EU, Russland, Australien, Argentinien)",
               "Schwarzmeer-Exporte und Exportquoten", "Dollar und Konkurrenzpreise", "Saatenstand-Berichte"],
    "MAIS": ["WASDE (Bestände/Verbrauch-Verhältnis)", "Ernte USA/Brasilien, Wetter", "Ethanol-Nachfrage",
             "Exporte (China, Mexiko)", "Futtermittelnachfrage"],
    "SOJA": ["WASDE", "Ernte Brasilien/Argentinien/USA, Wetter", "China-Käufe und Handelspolitik",
             "Crush-Margen, Sojaöl (Biodiesel)", "Exporte"],
}


def prompt(key: str, today: str | None = None) -> str:
    ticker, name = C.COMMODITIES[key][0], C.COMMODITIES[key][1]
    check = "\n".join(f"   - {x}" for x in CHECK[key])
    return (PROMPT.read_text(encoding="utf-8").replace("{CHECKLISTE}", check).replace("{SCHLUESSEL}", key)
            .replace("{NAME}", name).replace("{TICKER}", ticker).replace("{DATUM}", today or date.today().isoformat()))


_HEAD = re.compile(r"<!--\s*(\{.*?\})\s*-->", re.S)


def parse(path: Path) -> dict:
    """Datei -> {'kopf': JSON-Kopf oder {}, 'markdown': Rest, 'datei': Name}."""
    text = path.read_text(encoding="utf-8")
    m = _HEAD.search(text[:4000])
    head = {}
    if m:
        try:
            head = json.loads(m.group(1))
        except json.JSONDecodeError:
            head = {}
    body = (text[:m.start()] + text[m.end():]).strip() if m else text
    return {"kopf": head, "markdown": body, "datei": path.name}


def latest() -> dict[str, dict]:
    """Neueste Wochenanalyse je Schluessel."""
    out = {}
    if not OUT_DIR.exists():
        return out
    for p in sorted(OUT_DIR.glob("????-??-??_*.md")):
        key = p.stem.split("_", 1)[1]
        if key in C.COMMODITIES:
            out[key] = parse(p) | {"datum": p.stem[:10]}
    return out


def telegram() -> str:
    L = ["🛢️ Rohstoffe: Wochen-Tiefenanalyse"]
    icon = {"bullisch": "🟢", "neutral": "🟡", "bärisch": "🔴"}
    for key, x in latest().items():
        h = x["kopf"]
        L.append(f"{icon.get(h.get('urteil_kurz'), '⚪')} {C.COMMODITIES[key][1]} ({x['datum']}): kurz {h.get('urteil_kurz', '–')}, "
                 f"strukturell {h.get('urteil_struktur', '–')}, Szenario {h.get('szenario', '–')}")
        if h.get("fazit"):
            L.append(f"   {h['fazit']}")
    L.append("Details im Cockpit (Tab Rohstoffe). Analyse, keine Anlageberatung.")
    return "\n".join(L)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "liste"
    if cmd == "prompt":
        print(prompt(sys.argv[2]))
    elif cmd == "liste":
        print("\n".join(C.DEEP_WEEKLY_COMMODITIES))
    elif cmd == "telegram":
        print(telegram())
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
