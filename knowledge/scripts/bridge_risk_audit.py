"""Probe zum Standardprozess "Paper-Bot -> Live-Bridge"
(knowledge/areas/paper-bot-zu-live-bridge.md).

Prueft alle Live-Bridges in C:\\Users\\andre\\*-Bridge\\ rein statisch (AST, kein
Import, keine MT5-Verbindung) auf die Auslassungen, die am 2026-09-09 bei der
EK-Portfolio-Bridge gefunden wurden:

  1. TOTE RISIKOKONSTANTE -- eine Konstante wie CAPITAL_WEIGHT ist in config.py
     definiert, wird aber nirgends im Code GELESEN. Das war der EK-Bug: die
     Verduennungsformel stand im Docstring, im Code fehlte sie, jedes Bein
     handelte ~8x zu gross. Diese Pruefung ist der eigentliche Kern.
  2. KILL-SWITCH -- gibt es ueberhaupt eine Trailing-/Gesamt-Drawdown-Grenze?
     Die EK-Bridge hatte keine, obwohl ihr Paper-Bot eine hat.
  3. AGGREGIERTER RISIKODECKEL -- vorhanden?
  4. PAPER-BOT-DRIFT -- dupliziert die Bridge ihre Risikowerte (statt den
     Paper-Bot zu importieren) und weichen sie inzwischen ab? Real passiert am
     2026-09-11 bei der EK-Neukalibrierung, 6 von 8 Beinen.
  5. SIZING-METHODE -- order_calc_profit() statt manueller tick_value-Rechnung
     (Vorfall 2026-08-06: manuelle Formel lag um Faktor 8,6 daneben).

Aufruf:  python knowledge/scripts/bridge_risk_audit.py
Exit 0 = keine Befunde, 1 = mindestens ein Befund (fuer spaetere Automatisierung).
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

BRIDGE_ROOT = Path(r"C:\Users\andre")

# Konstanten, die das Risiko/die Positionsgroesse bestimmen. Ist eine davon
# definiert, MUSS sie auch irgendwo gelesen werden.
RISK_CONSTANTS = {
    "CAPITAL_WEIGHT", "LEG_RISK_PCT", "RISK_PCT", "RISK_PER_TRADE_PCT",
    "MAX_TOTAL_RISK_PCT", "MAX_SINGLE_TRADE_RISK_PCT", "ORB_COMBINED_RISK_PCT",
}
# Case-insensitiv geprueft, und bewusst auch die deutschen Schreibweisen: die
# Funded-Bridge nennt ihren Kill-Switch "Trailing-Gesamt-Drawdown-Kill-Switch"
# (Bindestrich), was eine reine "KILL_SWITCH"-Suche uebersieht -- erster
# Fehlalarm dieser Probe am 2026-09-10.
KILL_SWITCH_HINTS = ("trailing_dd", "max_daily_drawdown", "max_total_drawdown",
                     "kill_switch", "kill-switch", "check_trailing_dd",
                     "drawdown_pct", "peak_equity", "trailing-dd")
# Bridge -> Paper-Bot im Repo. Nur noetig fuer Bridges, die ihre Risikowerte
# DUPLIZIEREN. Bridges, die ihren Paper-Bot zur Laufzeit importieren
# (Funded-/FKInstantFunding-Bridge: "import X.paper_bot as pb"), koennen
# strukturell nicht abdriften und werden uebersprungen.
# Stillgelegte Bridges (Nutzerentscheid 2026-09-11): werden NICHT reaktiviert.
# Jede Alt-Strategie bekommt stattdessen ein eigenes optimiertes Bein in den
# neuen Portfolio-Bridges. Ihre Befunde (tick_value-Sizing, fehlende
# Kill-Switches) sind damit gegenstandslos -- sie hier zu uebergehen haelt die
# Probe leise und aussagekraeftig, statt bei jedem Lauf dieselben 7 Befunde zu
# melden, die niemand mehr abarbeiten wird. Wird eine davon doch je
# reaktiviert: Zeile entfernen, dann greift die volle Pruefung wieder.
RETIRED_BRIDGES = {
    "BTC-EMA-Cross-Bridge",
    "CLS-Practical-Bridge",
    "CTNL-Edge-MT5-Bridge",
    "GoldASB-MT5-Bridge",
    "OU-Modell-MT5-Bridge",
}

PAPER_BOT_BY_BRIDGE = {
    "EK-Portfolio-Bridge": "ek_portfolio/paper_bot.py",
    "Funded-Portfolio-Bridge": "challenge_portfolio/paper_bot.py",
    "FKInstantFunding-MT5-Bridge": "fk_instant_funding/paper_bot.py",
}
REPO_ROOT = Path(__file__).resolve().parents[2]

CAP_HINTS = ("max_total_risk", "check_cap", "risiko-deckel", "risk_cap", "max_risk_dollars")


def py_files(bridge: Path) -> list[Path]:
    return [p for p in bridge.rglob("*.py") if "__pycache__" not in p.parts]


def assigned_names(tree: ast.AST) -> set[str]:
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    out.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            out.add(node.target.id)
    return out


def loaded_names(tree: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)} | {
        n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)
    }


def _numeric_dict(path: Path, name: str) -> dict[str, str]:
    """Numerische Eintraege eines Dict-Literals `name = { "k": 0.12, ... }`.
    Nicht-numerische Werte (z.B. `ORB_RISK_PCT_PER_INSTRUMENT`) werden bewusst
    uebersprungen -- sie sind per Konstruktion auf beiden Seiten gleich
    benannt und kaemen sonst als Schein-Abweichung durch."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        start = text.index(f"{name} = {{")
    except (OSError, ValueError):
        return {}
    block = text[start:]
    block = block[: block.index("}") + 1]
    return dict(re.findall(r'"(\w+)":\s*([\d.]+)', block))


def _paper_bot_drift(bridge: Path) -> list[str]:
    """Vergleicht duplizierte Risikowerte einer Bridge mit ihrem Paper-Bot.

    Anlass (2026-09-11): bei der Neukalibrierung der EK-Bridge wurden deren
    LEG_RISK_PCT auf die 2,20x-Werte gesetzt, ek_portfolio/paper_bot.py aber
    nicht -- 6 von 8 Beinen wichen danach ab, ohne dass es irgendwo aufgefallen
    waere. Genau dieselbe Duplikations-Drift, die den urspruenglichen
    CAPITAL_WEIGHT-Bug ermoeglicht hat."""
    cfg = bridge / "config.py"
    if not cfg.exists():
        return []
    bridge_vals = _numeric_dict(cfg, "LEG_RISK_PCT")
    if not bridge_vals:
        return []  # dupliziert nichts -- liest vermutlich den Paper-Bot direkt

    rel = PAPER_BOT_BY_BRIDGE.get(bridge.name)
    if rel is None:
        return [f"  [DRIFT?] dupliziert LEG_RISK_PCT, aber kein Paper-Bot zugeordnet "
                f"(PAPER_BOT_BY_BRIDGE in dieser Datei ergaenzen)."]
    paper = REPO_ROOT / rel
    paper_vals = _numeric_dict(paper, "LEG_RISK_PCT")
    if not paper_vals:
        return [f"  [DRIFT?] Paper-Bot {rel} hat kein lesbares LEG_RISK_PCT."]

    diffs = []
    for leg in sorted(set(bridge_vals) | set(paper_vals)):
        b, pv = bridge_vals.get(leg), paper_vals.get(leg)
        if b != pv:
            diffs.append(f"     {leg}: Bridge {b or '-'} vs. Paper-Bot {pv or '-'}")
    if diffs:
        return [f"  [DRIFT] LEG_RISK_PCT weicht von {rel} ab:"] + diffs
    return []


def audit(bridge: Path) -> list[str]:
    findings: list[str] = []
    files = py_files(bridge)
    if not files:
        return findings

    defined: dict[str, Path] = {}
    used: set[str] = set()
    text_all = ""

    for f in files:
        try:
            src = f.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(src)
        except SyntaxError as e:
            findings.append(f"  [!] {f.relative_to(bridge)}: nicht parsebar ({e.msg})")
            continue
        text_all += src
        if f.name == "config.py":
            for name in assigned_names(tree) & RISK_CONSTANTS:
                defined[name] = f
        used |= loaded_names(tree)

    # 1) Tote Risikokonstanten -- der EK-Fehlermodus.
    # Ableitungsketten INNERHALB config.py zaehlen als Verwendung, sofern das
    # abgeleitete Symbol seinerseits ausserhalb benutzt wird (z.B.
    # ORB_COMBINED_RISK_PCT -> ORB_RISK_PCT_PER_INSTRUMENT -> LEG_RISK_PCT).
    # Ohne diese Aufloesung meldet die Probe Fehlalarme -- zweiter Fehlalarm
    # am 2026-09-10.
    used_anywhere_outside_config = set()
    for f in files:
        if f.name == "config.py":
            continue
        try:
            used_anywhere_outside_config |= loaded_names(ast.parse(f.read_text(encoding="utf-8", errors="replace")))
        except SyntaxError:
            continue

    cfg = next((f for f in files if f.name == "config.py"), None)
    derived_ok: set[str] = set()
    if cfg is not None:
        try:
            cfg_tree = ast.parse(cfg.read_text(encoding="utf-8", errors="replace"))
            # Zwei Runden reichen fuer die real vorkommenden Ketten
            for _ in range(3):
                for node in ast.walk(cfg_tree):
                    if not isinstance(node, ast.Assign):
                        continue
                    targets = {t.id for t in node.targets if isinstance(t, ast.Name)}
                    reachable = targets & (used_anywhere_outside_config | derived_ok)
                    if targets and not reachable:
                        continue
                    derived_ok |= loaded_names(node.value)
                # Dict-Werte (LEG_RISK_PCT.update({...})) mit einsammeln
                for node in ast.walk(cfg_tree):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "update":
                        derived_ok |= loaded_names(node)
        except SyntaxError:
            pass

    for name, where in sorted(defined.items()):
        if name in derived_ok:
            continue
        used_outside = False
        for f in files:
            if f == where:
                continue
            try:
                if name in loaded_names(ast.parse(f.read_text(encoding="utf-8", errors="replace"))):
                    used_outside = True
                    break
            except SyntaxError:
                continue
        if not used_outside:
            findings.append(
                f"  [RISIKO] '{name}' ist in config.py definiert, wird aber NIRGENDS im Code gelesen "
                f"-- exakt die Signatur des EK-Bugs vom 2026-09-09."
            )

    low = text_all.lower()  # Hinweise sind bewusst klein geschrieben

    # 1b) Drift gegen den Paper-Bot
    findings += _paper_bot_drift(bridge)

    # 2) Kill-Switch
    if not any(h in low for h in KILL_SWITCH_HINTS):
        findings.append("  [KILL-SWITCH] Keine Trailing-/Gesamt-Drawdown-Grenze gefunden.")

    # 3) Aggregierter Deckel ueber das offene Gesamtrisiko. Bei Ein-Strategie-
    # Bridges kann das eine bewusste Entscheidung sein (dort deckelt die
    # Risikostufe je Trade allein) -- Triage-Befund, nicht automatisch Bug.
    if not any(h in low for h in CAP_HINTS):
        findings.append("  [DECKEL] Kein Deckel fuer das aggregierte OFFENE Risiko gefunden "
                        "(bei Ein-Strategie-Bridges ggf. bewusst -- pruefen, nicht blind fixen).")

    # 4) Sizing-Methode
    if "order_send" in text_all or "sizing" in text_all.lower():
        if "order_calc_profit" not in text_all and "trade_tick_value" in text_all:
            findings.append(
                "  [SIZING] Nutzt trade_tick_value statt order_calc_profit() "
                "-- die manuelle Formel lag am 2026-08-06 um Faktor 8,6 daneben."
            )
    return findings


def main() -> int:
    bridges = sorted(p for p in BRIDGE_ROOT.glob("*-Bridge") if p.is_dir())
    if not bridges:
        print(f"Keine *-Bridge-Ordner unter {BRIDGE_ROOT} gefunden.")
        return 0

    total = 0
    aktive = [b for b in bridges if b.name not in RETIRED_BRIDGES]
    print(f"Bridge-Risiko-Audit -- {len(aktive)} aktive Bridges "
          f"({len(bridges) - len(aktive)} stillgelegt, uebersprungen)")
    print()
    for b in bridges:
        if b.name in RETIRED_BRIDGES:
            print(f'--   {b.name} (stillgelegt, siehe RETIRED_BRIDGES)')
            continue
        found = audit(b)
        total += len(found)
        print(f"{'OK  ' if not found else 'PRUEFEN'} {b.name}")
        for line in found:
            print(line)
    print()
    if total:
        print(f"{total} Befund(e). Siehe knowledge/areas/paper-bot-zu-live-bridge.md.")
        print("Nicht jeder Befund ist ein Bug -- ein bewusst weggelassener Wert gehoert")
        print("als Kommentar + DASHBOARD-Eintrag dokumentiert, nicht stillschweigend.")
    else:
        print("Keine Befunde.")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
