"""Gegenwährungs-Filter für Dollar-Thesen -- Makro-Agent, Schicht „Zinsen × Angst“.

Frage: Der Agent erwartet Dollar-Stärke. Gegen wen verkauft er -- Häfen (CHF, JPY) oder
Rohstoffwährungen (AUD, NZD, CAD)?

Befund (Lock `gegenwaehrung_angst`, 6 Versuche, scripts/research_gegenwaehrung_angst.py,
Wochen 2004-05/2026, Doku knowledge/areas/filter-gegenwaehrung.md):
  Zinswoche (US-2J >= +10 bp) OHNE Angst (VIX fällt):  Dollar gewinnt gegen Häfen mehr
      IS +1,14 % (83 % der Wochen), OOS +0,31 % (63 %).
  Zinswoche MIT Angst (VIX steigt): kein Vorteil der Rohstoffwährung (IS +0,68 %, OOS 0,00 %).
  Angst der VORWOCHE sagt die Folgewoche nicht voraus (OOS p 0,20-0,90) -> kein Rückblick-Signal.

Darum zwei Teile:
  korb(angst_ausloeser)  -- Entscheidungsregel für den Sonntag. Ob in der Woche ein Angst-Auslöser
                            ansteht (Termin, Zahlen, Gipfel), schätzt der Agent selbst.
  wochen_regime(...)     -- Nachprüfung im Weekly: welches Regime hatte die Woche wirklich,
                            welcher Korb hat mehr verloren.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

HAEFEN = ("CHF", "JPY")
ROHSTOFF = ("AUD", "NZD", "CAD")
ZINS_SCHWELLE_BP = 10.0

# Paar je Währung und Vorzeichen: +1 = USD ist Basis (USD/XXX steigt = Dollar stärker)
PAAR = {"AUD": ("AUDUSD", -1), "NZD": ("NZDUSD", -1), "CAD": ("USDCAD", +1),
        "CHF": ("USDCHF", +1), "JPY": ("USDJPY", +1)}


def korb(angst_ausloeser: bool, jpy_eingriff_droht: bool = False) -> tuple[str, ...]:
    """Bevorzugte Gegenwährungen für einen Dollar-Long aus Zinsen.

    Standard ist der Hafen. Die Rohstoffwährung nur, wenn in der Woche ein konkreter
    Angst-Auslöser ansteht -- und auch dann ist der Vorteil im Backtest nicht belegt
    (OOS 0,00 %); also halbe Überzeugung, nicht Umkehr.
    JPY fällt raus, solange ein Eingriff droht (z. B. USD/JPY 160-164, Nov. 2026).
    """
    if angst_ausloeser:
        return ROHSTOFF
    return tuple(c for c in HAEFEN if not (c == "JPY" and jpy_eingriff_droht))


def wochen_regime(d2y_bp: float, vix_chg: float) -> str:
    """Regime einer abgeschlossenen Woche (nur zur Nachprüfung, nicht als Signal)."""
    if np.isnan(d2y_bp) or np.isnan(vix_chg):
        return "unbekannt"
    if d2y_bp < ZINS_SCHWELLE_BP:
        return "keine Zinswoche"
    return "Zinsen mit Angst" if vix_chg > 0 else "Zinsen ohne Angst"


def spread(wochen_rendite_pct: dict[str, float]) -> float:
    """S = Dollar-Gewinn gegen Häfen minus gegen Rohstoffwährungen (Prozent, Wochen-Log-Rendite).

    `wochen_rendite_pct` = Wochenrendite des PAARS wie notiert (z. B. AUDUSD -1,35).
    S > 0: Hafen war die bessere Gegenwährung.
    """
    usd = {c: s * wochen_rendite_pct[p] for c, (p, s) in PAAR.items() if p in wochen_rendite_pct}
    h = [usd[c] for c in HAEFEN if c in usd]
    r = [usd[c] for c in ROHSTOFF if c in usd]
    return float(np.mean(h) - np.mean(r)) if h and r else float("nan")


if __name__ == "__main__":
    # KW46/2026 als Beispiel (Lake/Yahoo, Fr 06.11. -> Fr 13.11.)
    print(wochen_regime(35.0, -6.34))
    print(round(spread({"AUDUSD": -1.35, "NZDUSD": -0.91, "USDCAD": 0.98,
                        "USDCHF": 2.27, "USDJPY": 0.79}), 2))
    print(korb(angst_ausloeser=True), korb(False, jpy_eingriff_droht=True))
