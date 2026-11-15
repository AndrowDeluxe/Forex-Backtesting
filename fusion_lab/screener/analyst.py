"""LLM-Einordnung je Tiefen-Kandidat ueber den lokalen Claude Code (Abo, `claude.exe -p`).

Das LLM bekommt ein Faktenpaket (Kennzahlen, Punktwerte, BERECHNETE Szenarien, Schlagzeilen, Makro-Lage) und
liefert nur JSON: Sentiment, News-Kernaussagen, Pro/Contra, Wahl eines der vorgegebenen Szenarien A/B/C.
Es nennt keine eigenen Preise. Der Validator verwirft ungueltige Szenario-Wahlen und markiert Dollar-
Betraege im Text, die nicht im Paket stehen. Faellt der Aufruf aus -> None (Bericht zeigt "n.v.").
"""

from __future__ import annotations

import json
import re
import subprocess

from fusion_lab.screener import config as C

PROMPT = """Du bist Analyst in einem Research-Team (nur Analyse, kein Handel). Unten steht ein Faktenpaket zu
EINEM Titel als JSON. Alle Zahlen und Preisbereiche sind von Python berechnet und gelten als richtig.

Aufgabe:
1. Bewerte die Nachrichtenlage/Stimmung der Schlagzeilen fuer den Kurs: -2 (stark negativ) bis +2 (stark positiv).
   Ohne relevante Schlagzeilen: 0.
2. Fasse die 2-4 wichtigsten Schlagzeilen sachlich zusammen, je mit Quelle.
3. Nenne je 3 Pro- und Contra-Punkte, gestuetzt auf das Paket.
4. Waehle GENAU EIN Szenario aus dem Paket: "A" (Ruecksetzer-Zone), "B" (Ausbruch) oder "C" (Abwarten).
   A oder B nur, wenn es im Paket existiert (nicht null). Begruende die Wahl in 1-2 Saetzen
   (z. B. Trend, Ereignisrisiko wie Quartalszahlen in den naechsten Tagen, Nachrichtenlage).
5. Ueberzeugung: "niedrig", "mittel" oder "hoch". Hauptrisiko in einem Satz.

Regeln: Deutsch, einfache Sprache. KEINE eigenen Preise, Kursziele oder Prozentzahlen erfinden -- nur Zahlen aus
dem Paket verwenden. Nichts dazuerfinden, was nicht in Paket oder Schlagzeilen steht. Keine Anlageberatung.

Antworte NUR mit einem JSON-Objekt, ohne Text davor oder danach:
{"sentiment": -2..2, "sentiment_grund": "...", "news": [{"aussage": "...", "quelle": "..."}],
 "pro": ["...", "...", "..."], "contra": ["...", "...", "..."], "szenario": "A"|"B"|"C",
 "szenario_grund": "...", "ueberzeugung": "niedrig"|"mittel"|"hoch", "hauptrisiko": "..."}

FAKTENPAKET:
"""

_MONEY = re.compile(r"(?:\$\s?(\d[\d.,]*)|(\d[\d.,]*)\s?(?:\$|USD|Dollar))")


def claude_exe() -> str:
    from fusion_lab.copy_trading.extract import claude_exe as find
    return find()


def _num(s: str) -> float | None:
    s = s.strip().rstrip(".,")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".") if len(s.split(",")[-1]) <= 2 else s.replace(",", "")
    elif "." in s and all(len(g) == 3 for g in s.split(".")[1:]):
        s = s.replace(".", "")                     # deutscher Tausenderpunkt: 65.000 -> 65000
    try:
        return float(s)
    except ValueError:
        return None


def money_mentions(text: str) -> list[float]:
    return [v for m in _MONEY.finditer(text or "") if (v := _num(m.group(1) or m.group(2))) is not None]


def validate(raw: dict, pack: dict, allowed_prices: set[float]) -> dict:
    """Bereinigt die LLM-Antwort. Wirft ValueError bei unbrauchbarer Antwort."""
    if not isinstance(raw, dict):
        raise ValueError("keine JSON-Objekt-Antwort")
    out = {}
    try:
        out["sentiment"] = max(-2, min(2, int(raw.get("sentiment", 0))))
    except (TypeError, ValueError):
        raise ValueError("sentiment fehlt/ungueltig") from None
    out["sentiment_grund"] = str(raw.get("sentiment_grund", ""))[:400]
    out["news"] = [{"aussage": str(n.get("aussage", ""))[:300], "quelle": str(n.get("quelle", ""))[:80]}
                   for n in (raw.get("news") or [])[:4] if isinstance(n, dict)]
    out["pro"] = [str(x)[:250] for x in (raw.get("pro") or [])[:3]]
    out["contra"] = [str(x)[:250] for x in (raw.get("contra") or [])[:3]]
    sz = str(raw.get("szenario", "C")).strip().upper()[:1]
    warn = []
    if sz not in ("A", "B", "C"):
        warn.append(f"Szenario '{sz}' ungueltig -> C")
        sz = "C"
    elif sz in ("A", "B") and not pack["szenarien"].get(sz):
        warn.append(f"Szenario {sz} existiert nicht -> C")
        sz = "C"
    out["szenario"] = sz
    out["szenario_grund"] = str(raw.get("szenario_grund", ""))[:400]
    u = str(raw.get("ueberzeugung", "niedrig")).lower()
    out["ueberzeugung"] = u if u in ("niedrig", "mittel", "hoch") else "niedrig"
    out["hauptrisiko"] = str(raw.get("hauptrisiko", ""))[:300]
    # Dollar-Betraege im Text muessen (auf 1 %) zu Paketpreisen passen
    text = " ".join([out["sentiment_grund"], out["szenario_grund"], out["hauptrisiko"], *out["pro"], *out["contra"],
                     *[n["aussage"] for n in out["news"]]])
    allowed = [p for p in allowed_prices if p]
    for v in money_mentions(text):
        if not any(abs(v - p) <= 0.01 * abs(p) for p in allowed) and v >= 1:
            warn.append(f"ungepruefter Betrag {v:g} $")
    out["warnungen"] = warn
    return out


def parse(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", flags=re.S)
    if not m:
        raise ValueError("kein JSON in der Antwort")
    return json.loads(m.group(0))


def allowed_prices_of(pack: dict) -> set[float]:
    vals = set()

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, (int, float)) and not isinstance(x, bool):
            vals.add(float(x))
    walk(pack)
    # Zahlen, die woertlich in den Schlagzeilen stehen (Analystenziele, Oelpreis, BTC-Kurs ...), gelten als belegt
    for h in pack.get("schlagzeilen") or []:
        for m in re.finditer(r"\d[\d.,]*", str(h.get("titel", ""))):
            if (v := _num(m.group(0))) is not None:
                vals.add(v)
    return vals


def analyse(pack: dict, model: str = C.LLM_MODEL) -> dict | None:
    """Ein Aufruf je Kandidat. None bei Ausfall (Lauf geht weiter)."""
    prompt = PROMPT + json.dumps(pack, ensure_ascii=False, default=str)
    try:
        res = subprocess.run([claude_exe(), "-p", "--model", model, "--output-format", "json"], input=prompt,
                             capture_output=True, text=True, encoding="utf-8", timeout=C.LLM_TIMEOUT)
        if res.returncode != 0:
            return {"fehler": f"claude rc={res.returncode}: {(res.stderr or res.stdout)[-200:]}"}
        raw = parse(json.loads(res.stdout).get("result", ""))
        return validate(raw, pack, allowed_prices_of(pack))
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        return {"fehler": f"{type(e).__name__}: {str(e)[:200]}"}
