"""Wahrscheinlichkeit je FOMC-Sitzung aus Fed-Funds-Futures (Methode wie CME FedWatch).

Ein Monatskontrakt preist den Durchschnitt des effektiven Satzes im Monat. Liegt im Monat eine
Sitzung, gilt bis zum Tag nach der Entscheidung der Anfangssatz, danach der Endsatz:
    avg = f * start + (1 - f) * end,  f = Tage bis einschliesslich Entscheidungstag / Monatstage
-> end = (avg - f * start) / (1 - f). Monate ohne Sitzung setzen start = avg fuer den Folgemonat.
Wahrscheinlichkeit einer Bewegung = (end - start) / 0,25 (> 1 heisst: mehr als ein Schritt gepreist).

Termine: federalreserve.gov/monetarypolicy/fomccalendars.htm (2027 vorlaeufig), Stand 11.11.2026.
"""

from __future__ import annotations

import calendar as cal

import pandas as pd

# Entscheidungstag (zweiter Sitzungstag)
FOMC = ["2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16", "2026-10-28",
        "2026-12-09", "2027-01-27", "2027-03-17", "2027-04-28", "2027-06-09", "2027-07-28", "2027-09-15",
        "2027-10-27", "2027-12-08"]
STEP = 0.25
PAID = 0.75  # Regel 3.1: ab 75 % gepreist ist die Sitzung bezahlt


def meeting_path(implied: dict[str, float], effective: float, today: pd.Timestamp) -> list[dict]:
    """implied: Liefermonat 'YYYY-MM' -> implizierter Satz. Gibt je kommender Sitzung Start-/Endsatz,
    Veraenderung in bp und Wahrscheinlichkeit eines 25-bp-Schritts zurueck."""
    meetings = {pd.Timestamp(d).strftime("%Y-%m"): pd.Timestamp(d) for d in FOMC if pd.Timestamp(d) >= today}
    start = effective
    out = []
    for month in sorted(implied):
        if month < today.strftime("%Y-%m"):
            continue
        avg = implied[month]
        if month in meetings:
            d = meetings[month]
            n = cal.monthrange(d.year, d.month)[1]
            f = d.day / n
            end = (avg - f * start) / (1 - f)
            move = end - start
            out.append({"sitzung": d.date().isoformat(), "start": round(start, 4), "ende": round(end, 4),
                        "bp": round(move * 100, 1), "wahrscheinlichkeit": round(move / STEP, 3),
                        "pct": round(move / STEP * 100, 1),
                        "bezahlt": abs(move / STEP) >= PAID})
            start = end
        else:
            start = avg
    return out
