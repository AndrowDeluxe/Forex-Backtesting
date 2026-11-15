"""Tagesbericht (Markdown + JSON) und Telegram-Kurzfassung."""

from __future__ import annotations

import json
from pathlib import Path

from fusion_lab.screener import config as C

ICON = {"KAUFEN": "🟢", "HALTEN": "🟡", "VERKAUFEN": "🔴"}
SZ_NAME = {"A": "Rücksetzer", "B": "Ausbruch", "C": "Abwarten"}


def fmt(x, d: int = 2, pct: bool = False) -> str:
    if x is None:
        return "–"
    if isinstance(x, (int, float)):
        s = f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return s + (" %" if pct else "")
    return str(x)


def price(x) -> str:
    if x is None:
        return "–"
    d = 2 if abs(x) >= 1 else 4 if abs(x) >= 0.01 else 6
    return fmt(x, d)


def scenario_line(k: str, s: dict | None) -> str:
    if not s:
        return f"{k} {SZ_NAME[k]}: –"
    if k == "A":
        return (f"A Rücksetzer: Zone {price(s['zone_lo'])}–{price(s['zone_hi'])}, Stopp {price(s['stopp'])}, "
                f"Ziel {price(s['ziel'])} (CRV {fmt(s['rr'], 1)})")
    return f"B Ausbruch: über {price(s['trigger'])}, Stopp {price(s['stopp'])}, Ziel {price(s['ziel'])} (CRV {fmt(s['rr'], 1)})"


def markdown(r: dict) -> str:
    kind = "Aktien" if r["screener"] == "aktien" else "Krypto"
    L = [f"# {kind}-Screener {r['stand']}", "",
         f"Version {r['version']} · Status **{r['status']}** · erzeugt {r['erzeugt']} · "
         f"LLM {'an' if r['llm'] else 'aus'} · Signal: ≥ {fmt(r['schwellen']['kaufen'], 0)} KAUFEN, "
         f"≤ {fmt(r['schwellen']['verkaufen'], 0)} VERKAUFEN", ""]
    k = r["kontext"]
    if r["screener"] == "aktien":
        s = k["spy"]
        L.append(f"**Markt:** SPY {price(s['kurs'])} ({s['trend']}, 21 T {fmt(s['ret_21d'], 1, True)}, RSI {fmt(s['rsi14'], 0)})")
    else:
        b, f = k["btc"], k.get("fear_greed") or {}
        L.append(f"**Markt:** BTC {price(b['kurs'])} ({b['trend']}, 21 T {fmt(b['ret_21d'], 1, True)}, RSI {fmt(b['rsi14'], 0)}) · "
                 f"Fear & Greed {f.get('wert', '–')} ({f.get('einstufung', '–')})")
    if k.get("makro"):
        L.append(f"**Makro:** Zustand {k['makro']['zustand']} (Fact Sheet {k['makro']['stand']})")
    sig = r["signale"]
    L += ["", f"**Signale:** 🟢 {sig.get('KAUFEN', 0)} · 🟡 {sig.get('HALTEN', 0)} · 🔴 {sig.get('VERKAUFEN', 0)} "
              f"von {r['anzahl']}", "", "## Tiefen-Analyse", ""]
    for c in r["tief"]:
        llm = c.get("llm") or {}
        ok = llm and "fehler" not in llm
        L.append(f"### {ICON[c['signal']]} {c['objekt']} · {c['name']} · Score {fmt(c['gesamt'], 0)} → {c['signal']}")
        L.append("")
        pw = c["punktwerte"]
        L.append("Kurs " + price(c["kurs"]) + " · " + " · ".join(f"{k} {fmt(v, 0)}" for k, v in pw.items()))
        sc = c["szenarien"]
        for key in ("A", "B"):
            L.append(f"- {scenario_line(key, sc.get(key))}")
        if ok:
            L.append(f"- **Gewählt: {llm['szenario']} {SZ_NAME[llm['szenario']]}** ({llm['ueberzeugung']}): {llm['szenario_grund']}")
            L.append(f"- Stimmung {llm['sentiment']:+d}: {llm['sentiment_grund']}")
            for n in llm["news"]:
                L.append(f"  - {n['aussage']} ({n['quelle']})")
            L.append("- Pro: " + " | ".join(llm["pro"]))
            L.append("- Contra: " + " | ".join(llm["contra"]))
            L.append(f"- Hauptrisiko: {llm['hauptrisiko']}")
            if llm.get("warnungen"):
                L.append(f"- ⚠️ Prüfhinweise: {'; '.join(llm['warnungen'])}")
        else:
            L.append(f"- LLM-Einordnung: n.v. {('(' + llm['fehler'] + ')') if llm else ''}")
        L.append("")
    L += ["## Rangliste (Top 25)", "", "| # | Titel | Score | Signal | Kurs | 21 T |", "|---|---|---|---|---|---|"]
    for i, row in enumerate(r["tabelle"][:25], 1):
        L.append(f"| {i} | {row['index']} {row.get('name', '')} | {fmt(row['gesamt'], 0)} | {row['signal']} | "
                 f"{price(row['kurs'])} | {fmt(row.get('ret_21d'), 1, True)} |")
    b = r.get("bilanz", {})
    L += ["", "## Forward-Bilanz", "", "```", json.dumps(b, ensure_ascii=False, indent=1), "```"]
    return "\n".join(L)


def telegram(r: dict, url: str | None = None) -> str:
    kind = "📈 Aktien" if r["screener"] == "aktien" else "🪙 Krypto"
    k = r["kontext"]
    L = [f"{kind}-Screener {r['stand']} ({r['status']})"]
    if r["screener"] == "aktien":
        L.append(f"SPY {price(k['spy']['kurs'])} · {k['spy']['trend']}")
    else:
        f = k.get("fear_greed") or {}
        L.append(f"BTC {price(k['btc']['kurs'])} · {k['btc']['trend']} · F&G {f.get('wert', '–')}")
    sig = r["signale"]
    L.append(f"🟢 {sig.get('KAUFEN', 0)} · 🟡 {sig.get('HALTEN', 0)} · 🔴 {sig.get('VERKAUFEN', 0)}")
    L.append("")
    for c in r["tief"]:
        llm = c.get("llm") or {}
        ok = llm and "fehler" not in llm
        sz = llm.get("szenario") if ok else None
        L.append(f"{ICON[c['signal']]} {c['objekt']} {fmt(c['gesamt'], 0)} · {price(c['kurs'])}"
                 + (f" · Stimmung {llm['sentiment']:+d}" if ok else ""))
        if sz in ("A", "B"):
            L.append("   " + scenario_line(sz, c["szenarien"][sz]))
        elif ok:
            L.append("   C Abwarten")
    if url:
        L += ["", url]
    L.append("Analyse, keine Anlageberatung.")
    return "\n".join(L)


def write(r: dict) -> tuple[Path, Path]:
    C.DATA_DIR.mkdir(parents=True, exist_ok=True)
    stem = C.DATA_DIR / f"{r['stand']}_{r['screener']}"
    j, m = stem.with_suffix(".json"), stem.with_suffix(".md")
    j.write_text(json.dumps(r, ensure_ascii=False, default=str), encoding="utf-8")
    m.write_text(markdown(r), encoding="utf-8")
    archive(r)
    return j, m


def archive(r: dict) -> Path:
    """Dauerhaftes, git-getracktes Protokoll jedes Laufs (gzip, ohne Chart-Kerzen, die aus Kursdaten
    rekonstruierbar sind). Nie ueberschreiben: zweiter Lauf auf demselben Datenstand bekommt die Uhrzeit."""
    import gzip
    slim = {**r, "tief": [{k: v for k, v in c.items() if k != "chart"} for c in r["tief"]]}
    folder = C.ARCHIVE_DIR / r["stand"][:4]
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / f"{r['stand']}_{r['screener']}.json.gz"
    if p.exists():
        p = folder / f"{r['stand']}_{r['screener']}_{r['erzeugt'][11:19].replace(':', '')}.json.gz"
    with gzip.open(p, "wt", encoding="utf-8") as fh:
        json.dump(slim, fh, ensure_ascii=False, default=str)
    return p
