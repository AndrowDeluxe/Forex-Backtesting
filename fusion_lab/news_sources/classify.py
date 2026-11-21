"""Claude-Einordnung (Abo, `claude.exe -p`) aller Symbole in EINEM Aufruf, getrennt nach Quellgruppe.

Muster: fusion_lab/screener/analyst.py. Claude bekommt nummerierte Eintraege je Symbol und Gruppe
(news / social / offiziell) und liefert je Symbol und Gruppe: Stimmung -2..+2, Kernaussage, zitierte IDs.
Validator: nur vorhandene IDs, keine Gruppe ohne Eintraege, keine Zahlen in der Kernaussage, die nicht in den
zitierten Eintraegen stehen. Ungueltiges wird verworfen und als Warnung gemeldet. Ausfall -> None.
"""

from __future__ import annotations

import json
import re
import subprocess

from fusion_lab.news_sources import config as C

PROMPT = """Du bist Research-Analyst in einem Team (nur Analyse, kein Handel). Unten stehen fuer mehrere Maerkte
nummerierte Eintraege der letzten Stunden, je Quellgruppe:
- "news": Nachrichten-Schlagzeilen
- "social": Beitraege von Privatanlegern (StockTwits, Reddit)
- "offiziell": Zentralbank-Mitteilungen und Pflichtmeldungen (SEC)

Bewerte fuer JEDEN Markt und JEDE Gruppe, die Eintraege hat, getrennt:
- stimmung: was die Eintraege fuer den Kurs DIESES Marktes bedeuten, -2 (stark negativ) bis +2 (stark positiv),
  0 = neutral oder ohne Bezug. Bei Waehrungspaaren gilt die Richtung des Paares (z. B. EURUSD steigt = positiv).
- kernaussage: ein deutscher Satz, was die Eintraege sagen.
- ids: die IDs der Eintraege, auf die du dich stuetzt (nur IDs aus der Liste).

Regeln: Nur was in den Eintraegen steht, nichts dazuerfinden, keine eigenen Zahlen, Kurse oder Prognosen.
Gruppen ohne Eintraege weglassen. Keine Anlageberatung.

Antworte NUR mit einem JSON-Objekt, ohne Text davor oder danach:
{"<MARKT>": {"<gruppe>": {"stimmung": -2..2, "kernaussage": "...", "ids": ["..."]}}}

EINTRAEGE:
"""

_NUM = re.compile(r"\d+(?:[.,]\d+)?")


def claude_exe() -> str:
    from fusion_lab.copy_trading.extract import claude_exe as find
    return find()


def _f(s: str) -> float | None:
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def unbelegte_zahlen(text: str, belegt: str) -> list[str]:
    """Zahlen im Text, die in den Quellen nicht vorkommen. Dezimalkomma = Dezimalpunkt; '17.11' gilt als Datum,
    wenn '-11-17' (ISO) in den Quellen steht."""
    known = {v for n in _NUM.findall(belegt) if (v := _f(n)) is not None}
    out = []
    for n in _NUM.findall(text):
        if len(n) < 2:
            continue
        m = re.fullmatch(r"(\d{1,2})[.,](\d{1,2})", n)
        if m and f"-{int(m.group(2)):02d}-{int(m.group(1)):02d}" in belegt:
            continue
        v = _f(n)
        if v is None or v not in known:
            out.append(n)
    return out


def build_pack(items: list[dict]) -> tuple[dict, dict]:
    """-> (pack fuer den Prompt, index id -> eintrag). IDs: <SYMBOL>-<g>-<nr>, g = n/s/o."""
    pack, index = {}, {}
    count: dict[tuple, int] = {}
    for it in items:
        s, g = it["symbol"], it["gruppe"]
        k = (s, g)
        count[k] = count.get(k, 0) + 1
        iid = f"{s}-{g[0]}-{count[k]}"
        index[iid] = it
        pack.setdefault(s, {}).setdefault(g, []).append(
            {"id": iid, "quelle": it["quelle"], "zeit": it["zeit"], "text": it["titel"]})
    return pack, index


def validate(raw: dict, pack: dict, index: dict) -> tuple[dict, list[str]]:
    out, warn = {}, []
    if not isinstance(raw, dict):
        raise ValueError("keine JSON-Objekt-Antwort")
    for sym, groups in raw.items():
        if sym not in pack:
            warn.append(f"unbekannter Markt {sym} verworfen")
            continue
        if not isinstance(groups, dict):
            continue
        for g, v in groups.items():
            if g not in C.GROUPS or g not in pack[sym]:
                warn.append(f"{sym}/{g}: Gruppe ohne Eintraege verworfen")
                continue
            try:
                st = max(-2, min(2, int(round(float(v.get("stimmung"))))))
            except (TypeError, ValueError, AttributeError):
                warn.append(f"{sym}/{g}: Stimmung ungueltig")
                continue
            ids = [i for i in (v.get("ids") or []) if isinstance(i, str)]
            good = [i for i in ids if i in index and index[i]["symbol"] == sym and index[i]["gruppe"] == g]
            if len(good) < len(ids):
                warn.append(f"{sym}/{g}: {len(ids) - len(good)} erfundene/fremde ID(s) entfernt")
            if not good:
                warn.append(f"{sym}/{g}: keine gueltige Quelle zitiert -> verworfen")
                continue
            text = str(v.get("kernaussage", ""))[:300]
            belegt = " ".join(f"{index[i]['titel']} {index[i]['zeit']}" for i in good)
            fremd = unbelegte_zahlen(text, belegt)
            if fremd:
                warn.append(f"{sym}/{g}: Zahl(en) {', '.join(fremd[:3])} nicht in den Quellen")
            out.setdefault(sym, {})[g] = {"stimmung": st, "wert": st / 2, "kernaussage": text, "ids": good,
                                          "quellen": [{"quelle": index[i]["quelle"], "titel": index[i]["titel"],
                                                       "link": index[i]["link"], "zeit": index[i]["zeit"]} for i in good],
                                          "zahlen_ungeprueft": fremd}
    return out, warn


def parse(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", flags=re.S)
    if not m:
        raise ValueError("kein JSON in der Antwort")
    return json.loads(m.group(0))


def classify(items: list[dict], model: str = C.LLM_MODEL) -> dict:
    """-> {"status", "grund", "ergebnis", "warnungen"}. Ein Aufruf fuer alle Symbole."""
    pack, index = build_pack(items)
    if not pack:
        return {"status": "ok", "grund": "keine Eintraege", "ergebnis": {}, "warnungen": []}
    prompt = PROMPT + json.dumps(pack, ensure_ascii=False)
    try:
        res = subprocess.run([claude_exe(), "-p", "--model", model, "--output-format", "json"], input=prompt,
                             capture_output=True, text=True, encoding="utf-8", timeout=C.LLM_TIMEOUT)
    except FileNotFoundError as e:
        return {"status": "offline", "grund": str(e), "ergebnis": {}, "warnungen": []}
    except subprocess.TimeoutExpired:
        return {"status": "fehler", "grund": f"Zeitlimit {C.LLM_TIMEOUT}s", "ergebnis": {}, "warnungen": []}
    if res.returncode != 0:
        return {"status": "fehler", "grund": f"claude rc={res.returncode}: {(res.stderr or res.stdout)[-200:]}",
                "ergebnis": {}, "warnungen": []}
    try:
        envelope = json.loads(res.stdout)
        if envelope.get("is_error"):
            return {"status": "fehler", "grund": str(envelope.get("result", ""))[:200], "ergebnis": {}, "warnungen": []}
        result, warn = validate(parse(envelope.get("result", "")), pack, index)
    except (ValueError, json.JSONDecodeError) as e:
        return {"status": "fehler", "grund": f"Antwort unbrauchbar: {e}", "ergebnis": {}, "warnungen": []}
    return {"status": "ok", "grund": "", "ergebnis": result, "warnungen": warn}
