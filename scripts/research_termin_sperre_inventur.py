"""Kandidat A aus dem SMH-Call "Session Pips" (knowledge/resources/
smh-session-pips-call.md), Schritt 1: Bestandsaufnahme, rein beschreibend.

Frage: Welche Live-Beine steigen kurz vor den bestaetigten Ruck-Terminen 08:00
und 14:30 (Berlin) ein oder halten eine Position ueber diese Termine? Und
werden solche Positionen auffaellig oft direkt nach dem Termin ausgestoppt?
Kontrolltermin ohne Ruck: 11:00.

Quelle: portfolio_construction/results/live_trades_ttp_2019_2026.csv (Challenge-
Beine, live simuliert mit TTP-Kosten, Zeiten UTC) plus gold_silver aus der
FK-Liste. Keine Variante, kein Parameter -> verbraucht keine Versuche unter
der Overfitting-Sperre. Ausgewertet wird nur IS (bis 2022-05-31), damit ein
spaeterer Test noch ein unberuehrtes OOS hat.

Aufruf:
    python scripts/research_termin_sperre_inventur.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "portfolio_construction" / "results"
IS_END = pd.Timestamp("2022-05-31 23:59")
TERMINE = {"08:00": (8, 0), "14:30": (14, 30), "11:00 (Kontrolle)": (11, 0)}
PRE_MIN = 15      # "kurz vor": Einstieg in den 15 Minuten vor dem Termin
POST_MIN = 30     # Stopp "direkt danach": Ausstieg binnen 30 Minuten nach dem Termin
LEGS = ["gold_asb", "cls_practical", "ctnl_reversal", "orb_sp500", "orb_nasdaq", "orb_us30",
        "trend_pullback", "gold_silver"]


def load() -> pd.DataFrame:
    a = pd.read_csv(RES / "live_trades_ttp_2019_2026.csv")
    b = pd.read_csv(RES / "live_trades_fk_offene_beine_2019_2026.csv")
    d = pd.concat([a, b[b["leg"] == "gold_silver"]], ignore_index=True)
    d = d[d["leg"].isin(LEGS)].copy()
    for c in ("entry_time", "exit_time"):
        d[c] = (pd.to_datetime(d[c]).dt.tz_localize("UTC").dt.tz_convert("Europe/Berlin"))
    return d[d["entry_time"].dt.tz_localize(None) <= IS_END]


def main() -> None:
    d = load()
    print(f"IS-Trades bis {IS_END.date()}: {len(d)}  (Zeiten Berlin)\n")
    rows = []
    for leg, g in d.groupby("leg"):
        row = {"Bein": leg, "n": len(g), "Ø R": g["r"].mean()}
        for name, (hh, mm) in TERMINE.items():
            day = g["entry_time"].dt.normalize()
            t = day + pd.Timedelta(hours=hh, minutes=mm)
            pre = (g["entry_time"] >= t - pd.Timedelta(minutes=PRE_MIN)) & (g["entry_time"] < t)
            across = (g["entry_time"] < t) & (g["exit_time"] > t)
            hit = across & (g["exit_reason"] == "stop") & (g["exit_time"] <= t + pd.Timedelta(minutes=POST_MIN))
            k = name.split(" ")[0]
            row[f"{k} Einstieg davor"] = int(pre.sum())
            row[f"{k} offen drüber"] = int(across.sum())
            row[f"{k} Stopp ≤30 Min. %"] = 100 * hit.sum() / across.sum() if across.sum() else np.nan
            row[f"{k} Ø R offen"] = g.loc[across, "r"].mean() if across.sum() else np.nan
        rows.append(row)
    out = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    for k in ("08:00", "14:30", "11:00"):
        cols = ["Bein", "n", "Ø R"] + [c for c in out.columns if c.startswith(k)]
        print(f"--- Termin {k} ---")
        print(out[cols].to_string(index=False, float_format=lambda v: f"{v:,.2f}"))
        print()

    # Wo genau liegen die Einstiege? Stunde (Berlin) je Bein
    print("--- Einstiegsstunde (Berlin), Anzahl IS-Trades ---")
    print(pd.crosstab(d["leg"], d["entry_time"].dt.hour).to_string())


if __name__ == "__main__":
    main()
