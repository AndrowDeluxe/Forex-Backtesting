"""Einordnung der Schlagzeilen je Geopolitik-Thema durch den lokalen Claude Code (Abo, `claude.exe -p`).

Nutzerentscheid 12.11.2026: messbare Indizes (GPR, GDELT, EPU) + taegliche LLM-Kurzfassung.
Das LLM ordnet nur ein (Eskalation / Entspannung / unveraendert, ein Satz Kernaussage) und darf keine
Zahlen erfinden; Preise und Messgroessen kommen aus der Datenschicht. Faellt der Aufruf aus, steht im
Fact Sheet "n.v." und alles andere laeuft weiter.

    python -m fusion_lab.macro_agent.news_digest            # Schlagzeilen holen + einordnen
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

from fusion_lab.macro_data import geo

OUT_DIR = Path(__file__).resolve().parents[2] / "fusion_lab" / "data" / "macro_agent" / "news"
MODEL = "sonnet"
LAGEN = ("eskalation", "entspannung", "unverändert")
PROMPT = """Du bist Makro-Analyst. Unten stehen Schlagzeilen der letzten 24 Stunden je Thema.
Ordne JEDES Thema ein und antworte NUR mit einem JSON-Array, ein Objekt je Thema:
{"thema": "<schluessel>", "lage": "eskalation" | "entspannung" | "unverändert",
 "kernaussage": "<ein deutscher Satz, was sich geaendert hat>", "quellen": ["<Quelle>", ...]}
Regeln: Nur was in den Schlagzeilen steht, nichts dazuerfinden, keine Kurs- oder Preisangaben,
keine Prognose. Widersprechen sich Schlagzeilen, "unverändert" und den Widerspruch nennen.
Keine Schlagzeilen -> "unverändert", Kernaussage "keine Meldungen".

"""


def claude_exe() -> str:
    from fusion_lab.copy_trading.extract import claude_exe as find
    return find()


def build_prompt(headlines: dict[str, list[dict]]) -> str:
    parts = [PROMPT]
    for theme, items in headlines.items():
        parts.append(f"## {theme} ({geo.THEMES[theme]['name']})")
        parts += [f"- [{x['zeit']}] {x['quelle']}: {x['titel']}" for x in items] or ["- (keine)"]
    return "\n".join(parts)


def parse(text: str, themes: list[str]) -> dict[str, dict]:
    m = re.search(r"\[.*\]", text, flags=re.S)
    if not m:
        raise ValueError("kein JSON-Array in der Antwort")
    out = {}
    for x in json.loads(m.group(0)):
        if x.get("thema") in themes and x.get("lage") in LAGEN:
            out[x["thema"]] = {"lage": x["lage"], "kernaussage": str(x.get("kernaussage", ""))[:300],
                               "quellen": [str(q) for q in x.get("quellen", [])][:6]}
    return out


def classify(headlines: dict[str, list[dict]]) -> dict[str, dict]:
    res = subprocess.run([claude_exe(), "-p", "--model", MODEL, "--output-format", "json"],
                         input=build_prompt(headlines), capture_output=True, text=True, encoding="utf-8",
                         timeout=600)
    if res.returncode != 0:
        raise RuntimeError(f"claude.exe rc={res.returncode}: {(res.stderr or res.stdout)[-300:]}")
    return parse(json.loads(res.stdout).get("result", ""), list(headlines))


def run(day: pd.Timestamp | None = None) -> dict:
    day = (day or pd.Timestamp.today()).normalize()
    counts: dict[str, int] = {}
    headlines = geo.fetch_headlines(counts=counts)
    record = {"datum": day.strftime("%Y-%m-%d"), "treffer": counts, "schlagzeilen": headlines}
    try:
        record["einordnung"] = classify(headlines)
    except Exception as e:
        record["einordnung"] = {}
        record["fehler"] = f"{type(e).__name__}: {e}"[:300]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"news_{record['datum']}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1),
                                                         encoding="utf-8")
    return record


def intensity(as_of: pd.Timestamp, days: int = 30) -> pd.DataFrame:
    """Trefferzahl je Thema und Tag aus den gespeicherten Laeufen (Historie waechst ab 12.11.2026)."""
    rows = {}
    for p in sorted(OUT_DIR.glob("news_*.json")):
        if p.stem[5:] <= as_of.strftime("%Y-%m-%d"):
            rows[pd.Timestamp(p.stem[5:])] = json.loads(p.read_text(encoding="utf-8")).get("treffer", {})
    return pd.DataFrame(rows).T.sort_index().tail(days)


def load(as_of: pd.Timestamp) -> dict:
    """Neueste Einordnung bis einschliesslich as_of."""
    files = sorted(p for p in OUT_DIR.glob("news_*.json") if p.stem[5:] <= as_of.strftime("%Y-%m-%d"))
    return json.loads(files[-1].read_text(encoding="utf-8")) if files else {}


if __name__ == "__main__":
    r = run()
    print(json.dumps({k: v for k, v in r.items() if k != "schlagzeilen"}, ensure_ascii=False, indent=1))
    sys.exit(1 if r.get("fehler") else 0)
