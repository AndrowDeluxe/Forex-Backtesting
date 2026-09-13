"""cls_practical auf der EK-Portfolio-Bridge -- eigene Simulation, weil EK
den Stop ANDERS setzt als die beiden anderen Bridges (Nutzerfrage 2026-09-11:
"wie wuerden die Backtest-Ergebnisse auf EK aussehen?").

DER ARCHITEKTUR-UNTERSCHIED, um den es geht:

  Funded-Portfolio-Bridge / FKInstantFunding-MT5-Bridge
      nehmen den ABSOLUTEN SL-Preis aus dem Signal. Laeuft der Kurs zwischen
      Signal und Ausfuehrung auf den Stop zu, schrumpft der Risiko-Abstand und
      die Position blaeht sich auf (der Vorfall vom 2026-09-09).

  EK-Portfolio-Bridge (run_once.py::_check_cls_practical)
      verankert SL UND TP am Live-Kurs neu:
          stop_price   = entry_price_now - direction * sl_distance
          target_price = entry_price_now + direction * tp_distance
      Der Risiko-Abstand ist damit IMMER exakt sl_distance -- die Aufblaehung
      kann strukturell nicht entstehen, ein R-Detektor ist dort unnoetig.

Das ist aber kein Gratis-Vorteil, sondern ein Tausch: der Stop sitzt dann
NICHT mehr am strukturellen Invalidierungspunkt der Strategie, sondern nur
noch in dessen Abstand. Und die SL-Studie vom 2026-09-10 hat gezeigt, dass
genau das strukturelle Niveau den Edge traegt -- ein Stop, der nur die
Volatilitaets-DISTANZ uebernimmt, verlor dort massiv (Ø R -0,47).

Dieses Skript misst beide Varianten gegeneinander auf denselben Signalen.
Die Ausstiegsseite muss dafuer neu simuliert werden (SL und TP liegen auf
anderen Preisen als im Engine-Backtest), nicht nur umgerechnet.

EK-spezifische Annahmen, offen deklariert:
  - Risiko/Trade = CAPITAL_WEIGHT (1/8) x LEG_RISK_PCT 0.0440 = 0,55 %,
    aus EK-Portfolio-Bridge/config.py (Kalibrierung vom 2026-09-10).
    Auf 100k gerechnet, damit die Zahlen mit den Challenge-Zahlen vergleichbar
    sind -- das echte EK-Konto ist deutlich kleiner (~3,3k EUR).
  - Tickmill-Kosten sind NICHT belastbar gemessen (die Tickhistorie deckt das
    Handelsfenster mit 15 Ticks nicht ab; Kommission 0,00 ueber 331 Lots ist
    dagegen gesichert). Deshalb ein SWEEP ueber mehrere Kostenannahmen statt
    einer erfundenen Zahl.

Aufruf:
    python scripts/research_cls_practical_ek_reanchored.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

from cls_practical.data import (
    fetch_eurusd_entry_tf_berlin,
    fetch_major_m15_berlin,
    fetch_rate_instrument_m5_berlin,
)
from cls_practical.engine import simulate_cls_practical
from research_cls_practical_risk_sizing import equity_metrics
from research_cls_practical_sl_optimization import (
    DEFAULT_END,
    DEFAULT_START,
    OTHER_MAJORS,
    SPLIT,
    pips_to_bps,
)

pd.set_option("display.width", 240)
pd.set_option("display.max_columns", 40)

PIP = 0.0001
INITIAL_EQUITY = 100_000.0
EK_RISK_PCT = (1 / 8) * 0.0440          # = 0,55 %, siehe Modul-Docstring
EK_RISK_DOLLARS = INITIAL_EQUITY * EK_RISK_PCT
LAG = 1
MIN_SL_PIPS = 5
COST_SWEEP = [0.50, 1.00, 1.50, 2.05]   # Pips Round-Trip; 2,05 = gemessener TTP-Wert als Obergrenze


def simulate_reanchored(trades: pd.DataFrame, m5: pd.DataFrame, lag: int, cost_pips: float,
                        reanchor: bool) -> pd.DataFrame:
    """Laeuft die Ausstiegsseite NEU, weil SL/TP bei EK auf anderen Preisen
    liegen als im Engine-Backtest.

    reanchor=True  -> EK: SL/TP relativ zum Live-Einstieg (Abstand konstant)
    reanchor=False -> Funded/FK: SL/TP auf den absoluten Signal-Preisen

    Konservativ bei Mehrdeutigkeit: liegen in einer Bar sowohl SL als auch TP,
    zaehlt der STOP -- ohne Tickdaten ist die Reihenfolge innerhalb der Bar
    nicht bekannt, und die pessimistische Annahme ist die ehrliche."""
    high, low = m5["high"].to_numpy(), m5["low"].to_numpy()
    close = m5["close"].to_numpy()
    pos = {t: i for i, t in enumerate(m5.index)}
    half_cost = cost_pips * PIP / 2.0
    n = len(close)

    rows = []
    for _, t in trades.iterrows():
        i = pos.get(t["entry_time"])
        if i is None or i + lag >= n:
            continue
        d = 1 if t["direction"] == "long" else -1
        sl_dist, tp_dist = float(t["sl_distance"]), abs(float(t["tp"]) - float(t["entry_price"]))
        raw_entry = float(close[i + lag])
        entry = raw_entry + d * half_cost

        if reanchor:
            sl, tp = raw_entry - d * sl_dist, raw_entry + d * tp_dist
        else:
            sl, tp = float(t["sl"]), float(t["tp"])

        eff = (entry - sl) * d
        if eff <= 0:
            continue  # Kurs schon jenseits des Stops -- Entry findet nicht statt

        exit_price, exit_reason = None, None
        for k in range(i + lag + 1, n):
            hit_sl = low[k] <= sl if d == 1 else high[k] >= sl
            hit_tp = high[k] >= tp if d == 1 else low[k] <= tp
            if hit_sl:
                exit_price, exit_reason = sl - d * half_cost, "stop"
                break
            if hit_tp:
                exit_price, exit_reason = tp - d * half_cost, "take_profit"
                break
        if exit_price is None:
            exit_price, exit_reason = close[n - 1] - d * half_cost, "data_end"
            k = n - 1

        # Sizing: EK auf sl_dist (Abstand konstant), Funded/FK auf den echten
        # Restabstand -- genau der Unterschied, um den es geht.
        units = EK_RISK_DOLLARS / (sl_dist if reanchor else eff)
        pnl = units * d * (exit_price - entry)
        rows.append({
            "entry_time": t["entry_time"], "exit_time": m5.index[k],
            "sl_dist_pips": sl_dist / PIP, "entry": entry, "exit_price": exit_price,
            "exit_reason": exit_reason, "pnl_usd": pnl, "r": pnl / EK_RISK_DOLLARS,
            "leverage": units / 100_000.0,
        })
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame, label: str, cost: float) -> dict:
    if df.empty:
        return {"Variante": label, "Kosten": cost, "Trades": 0}
    ex = df["exit_time"].dt.tz_localize(None)
    gl = abs(df[df["pnl_usd"] <= 0]["pnl_usd"].sum())
    days = pd.date_range(ex.min().floor("D"), ex.max().floor("D"), freq="B")
    daily = df.groupby(ex.dt.floor("D"))["pnl_usd"].sum().reindex(days, fill_value=0.0)
    m = equity_metrics(daily)
    rng = np.random.default_rng(23)
    r = df["r"].to_numpy()
    boot = r[rng.integers(0, len(r), size=(20000, len(r)))].mean(axis=1)
    return {
        "Variante": label, "Kosten": cost, "Trades": len(df),
        "Treffer%": 100 * (df["pnl_usd"] > 0).mean(),
        "PF": df[df["pnl_usd"] > 0]["pnl_usd"].sum() / gl if gl else np.inf,
        "Ø R": r.mean(),
        "Ø R (IS)": r[(ex < SPLIT).to_numpy()].mean(),
        "Ø R (OOS)": r[(ex >= SPLIT).to_numpy()].mean(),
        "P(Ø R<0)%": 100 * (boot < 0).mean(),
        "PnL $": df["pnl_usd"].sum(),
        "CAGR %": m["CAGR %"], "Sharpe": m["Sharpe"], "MaxDD %": m["MaxDD %"],
        "Calmar": m["Calmar"], "Hebel max": df["leverage"].max(),
    }


def main() -> None:
    print(f"Lade Daten {DEFAULT_START}..{DEFAULT_END} ...")
    e = fetch_eurusd_entry_tf_berlin("M5", DEFAULT_START, DEFAULT_END)
    o = {p: fetch_major_m15_berlin(p, DEFAULT_START, DEFAULT_END) for p in OTHER_MAJORS}
    b = fetch_rate_instrument_m5_berlin("BUND", DEFAULT_START, DEFAULT_END)
    u = fetch_rate_instrument_m5_berlin("USTBOND", DEFAULT_START, DEFAULT_END)
    price = float(e["close"].mean())
    print(f"  EK-Risiko: 1/8 x 0.0440 = {EK_RISK_PCT:.2%} je Trade = ${EK_RISK_DOLLARS:,.0f} auf 100k")
    print(f"  Pip-Boden {MIN_SL_PIPS}, Ausfuehrung {LAG*5} Min. nach dem Signal-Schlusskurs\n")

    rows = []
    for cost in COST_SWEEP:
        raw = simulate_cls_practical(
            e, o, b, u, risk_pct=EK_RISK_PCT,
            spread_bps=pips_to_bps(cost, price), slippage_bps=0.0, min_sl_pips=MIN_SL_PIPS)
        rows.append(summarize(simulate_reanchored(raw, e, LAG, cost, True),
                              "EK (SL neu verankert)", cost))
        rows.append(summarize(simulate_reanchored(raw, e, LAG, cost, False),
                              "Funded/FK (absoluter SL)", cost))

    df = pd.DataFrame(rows).sort_values(["Kosten", "Variante"])
    print("=" * 190)
    print("cls_practical AUF EK -- neu verankerter Stop gegen absoluten Stop, ueber mehrere Kostenannahmen")
    print("=" * 190)
    print(df.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    print("\n  Tickmill-Kosten sind NICHT belastbar gemessen (15 Ticks im Handelsfenster; "
          "Kommission 0,00 ueber 331 Lots gesichert).")
    print("  Plausibelster Bereich fuer ein kommissionsfreies Konto: 0,50-1,00 Pips Round-Trip.")

    out = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "ek_reanchored_vs_absolute.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"\nGespeichert: {out}")


if __name__ == "__main__":
    main()
