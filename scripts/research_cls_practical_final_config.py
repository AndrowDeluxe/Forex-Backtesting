"""Abschluss-Backtest der TATSAECHLICH IMPLEMENTIERTEN cls_practical-
Konfiguration (2026-09-10). Bildet exakt ab, was im Live-Pfad steht:

  challenge_portfolio/paper_bot.py
      min_sl_pips = 5                       (Pip-Boden, Modus "drop")
      LEG_RISK_PCT["cls_practical"] = 0.010 (war 0.015)
      -> Risiko je Trade = CAPITAL_WEIGHT (1/6) x 0.010 = 0,1667 % der Equity
  Funded-Portfolio-Bridge/run_once.py
      Restlaufzeit-Gate  ("SL schon beruehrt", gebaut 2026-09-09)
      MAX_CONSUMED_R_FOR_ENTRY = 0.50       (R-Detektor, neu -- 2x-Hebel-Deckel)
  Funded-Portfolio-Bridge/sizing.py
      MAX_MARGIN_PCT_OF_EQUITY = 0.20       (hartes Netz, hier nicht simulierbar --
                                             greift erst bei Ausreissern, die die
                                             beiden Gates schon abfangen)

Alles unter den GEMESSENEN Broker-Kosten und auf der LIVE-SIMULATION
(Ausfuehrung eine M5-Bar nach dem Signal-Schlusskurs = der real beobachtete
Versatz vom 2026-09-09; Sizing auf |Live-Kurs - SL|).

WICHTIG zur Lag-Wahl: Bar-Label 10:20 heisst Bar-SCHLUSS 10:25, ausgefuehrt
wurde 10:30 -> lag=1. Frueher in dieser Untersuchung wurde faelschlich mit
lag=2 gerechnet; ueber die Lag-Achse ist das Ergebnis mit Schutzmechanismen
nicht monoton (0,20 / 0,23 / 0,33 / 0,22 bei 0/5/10/15 Min), lag=2 war schlicht
die guenstigste Zelle. lag=1 ist der belegte Wert.

Aufruf:
    python scripts/research_cls_practical_final_config.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

import challenge_portfolio.paper_bot as pb
from cls_practical.data import (
    fetch_eurusd_entry_tf_berlin,
    fetch_major_m15_berlin,
    fetch_rate_instrument_m5_berlin,
)
from cls_practical.engine import simulate_cls_practical
from research_cls_practical_entry_gate import simulate_live_entries
from research_cls_practical_risk_sizing import equity_metrics
from research_cls_practical_sl_optimization import (
    COSTS_PIPS,
    DEFAULT_END,
    DEFAULT_START,
    OTHER_MAJORS,
    SPLIT,
    pips_to_bps,
)

pd.set_option("display.width", 240)
pd.set_option("display.max_columns", 40)

INITIAL_EQUITY = 100_000.0
LAG = 1
MIN_SL_PIPS = 5
GATE_R = 0.50
# Direkt aus dem Live-Code gelesen, nicht dupliziert -- faellt auf, wenn dort
# jemand etwas aendert, ohne diesen Backtest zu wiederholen.
LIVE_RISK_PCT = pb.CAPITAL_WEIGHT * pb.LEG_RISK_PCT["cls_practical"]


def main() -> None:
    print(f"Lade Daten {DEFAULT_START}..{DEFAULT_END} ...")
    e = fetch_eurusd_entry_tf_berlin("M5", DEFAULT_START, DEFAULT_END)
    o = {p: fetch_major_m15_berlin(p, DEFAULT_START, DEFAULT_END) for p in OTHER_MAJORS}
    b = fetch_rate_instrument_m5_berlin("BUND", DEFAULT_START, DEFAULT_END)
    u = fetch_rate_instrument_m5_berlin("USTBOND", DEFAULT_START, DEFAULT_END)
    price = float(e["close"].mean())
    print(f"  Live-Risiko laut Code: CAPITAL_WEIGHT {pb.CAPITAL_WEIGHT:.4f} x "
          f"LEG_RISK_PCT {pb.LEG_RISK_PCT['cls_practical']} = {LIVE_RISK_PCT:.4%} je Trade\n")

    def live(cost_pips, gate_r=GATE_R, floor=MIN_SL_PIPS, lag=LAG):
        kw = {"min_sl_pips": floor} if floor else {}
        raw = simulate_cls_practical(
            e, o, b, u, risk_pct=LIVE_RISK_PCT,
            spread_bps=pips_to_bps(cost_pips, price), slippage_bps=0.0, **kw)
        # risk_dollars explizit: simulate_live_entries() rechnet sonst mit
        # seinem 250-$-Default weiter, und die $-/Drawdown-Zahlen gehoerten
        # zur falschen Risikostufe (Fehler in der ersten Fassung dieses Skripts).
        lv = simulate_live_entries(raw, e, lag, cost_pips,
                                   risk_dollars=INITIAL_EQUITY * LIVE_RISK_PCT)
        sub = lv if gate_r is None else lv[(~lv["sl_touched"]) & (lv["consumed_r"] <= gate_r)]
        return lv, sub.dropna(subset=["r"])

    # ---- 1. Schwellenwahl beim RICHTIGEN Lag nachpruefen
    print("=" * 118)
    print(f"1) R-DETEKTOR-SCHWELLE bei lag={LAG} ({LAG*5} Min), TTP-Kosten, Pip-Boden {MIN_SL_PIPS}")
    print("=" * 118)
    lv, _ = live(COSTS_PIPS["TTP"])
    rows = []
    for thr in (None, 1.00, 0.90, 0.75, 0.60, 0.50, 0.40):
        sub = lv.dropna(subset=["r"]) if thr is None else \
            lv[(~lv["sl_touched"]) & (lv["consumed_r"] <= thr)].dropna(subset=["r"])
        if sub.empty:
            continue
        ex = sub["exit_time"].dt.tz_localize(None)
        gl = abs(sub[sub["pnl_usd"] <= 0]["pnl_usd"].sum())
        rows.append({
            "Schwelle": "ohne Gates" if thr is None else f"<= {thr:.2f}R",
            "Deckel": "-" if thr is None or thr >= 1 else f"{1/(1-thr):.1f}x",
            "Trades": len(sub), "Treffer%": 100 * (sub["pnl_usd"] > 0).mean(),
            "PF": sub[sub["pnl_usd"] > 0]["pnl_usd"].sum() / gl if gl else np.inf,
            "Ø R": sub["r"].mean(),
            "Ø R (IS)": sub["r"][(ex < SPLIT).to_numpy()].mean(),
            "Ø R (OOS)": sub["r"][(ex >= SPLIT).to_numpy()].mean(),
            "Hebel p90": sub["leverage"].quantile(0.90), "Hebel max": sub["leverage"].max(),
        })
    print(pd.DataFrame(rows).to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    # ---- 2. Finale Konfiguration, beide Broker
    print("\n" + "=" * 150)
    print("2) FINALE KONFIGURATION -- Kennzahlen auf 100k beim implementierten Risiko")
    print("=" * 150)
    out_rows = []
    for broker, cost in COSTS_PIPS.items():
        _, t = live(cost)
        ex = t["exit_time"].dt.tz_localize(None)
        days = pd.date_range(t["exit_time"].min().tz_localize(None).floor("D"),
                             t["exit_time"].max().tz_localize(None).floor("D"), freq="B")
        daily = t.groupby(ex.dt.floor("D"))["pnl_usd"].sum().reindex(days, fill_value=0.0)
        m = equity_metrics(daily)
        gl = abs(t[t["pnl_usd"] <= 0]["pnl_usd"].sum())
        rng = np.random.default_rng(11)
        r = t["r"].to_numpy()
        boot = r[rng.integers(0, len(r), size=(20000, len(r)))].mean(axis=1)
        out_rows.append({
            "Broker": broker, "Kosten (Pips)": cost, "Trades": len(t),
            "Trades/Jahr": len(t) / ((ex.max() - ex.min()).days / 365.25),
            "Treffer%": 100 * (t["pnl_usd"] > 0).mean(),
            "PF": t[t["pnl_usd"] > 0]["pnl_usd"].sum() / gl if gl else np.inf,
            "Ø R": r.mean(), "Ø R (IS)": r[(ex < SPLIT).to_numpy()].mean(),
            "Ø R (OOS)": r[(ex >= SPLIT).to_numpy()].mean(),
            "P(Ø R<0)": 100 * (boot < 0).mean(),
            "PnL $": t["pnl_usd"].sum(), **m,
            "Hebel max": t["leverage"].max(),
        })
    df = pd.DataFrame(out_rows)
    print(df.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    # ---- 3. Regeleinhaltung + Jahre
    print("\n" + "=" * 118)
    print("3) REGELEINHALTUNG (TTP: 3 % Tag / 7 % Gesamt-DD | IQ: 6 % Gesamt-DD) und Jahresverlauf")
    print("=" * 118)
    _, t = live(COSTS_PIPS["TTP"])
    ex = t["exit_time"].dt.tz_localize(None)
    days = pd.date_range(ex.min().floor("D"), ex.max().floor("D"), freq="B")
    daily = t.groupby(ex.dt.floor("D"))["pnl_usd"].sum().reindex(days, fill_value=0.0)
    m = equity_metrics(daily)
    print(f"  MaxDD des Beins {m['MaxDD %']:.2f} %  -> {abs(m['MaxDD %'])/7*100:.0f} % des TTP-Budgets, "
          f"{abs(m['MaxDD %'])/6*100:.0f} % des IQ-Budgets (Bein ist EINES von sechs)")
    print(f"  schlechtester Tag {m['schlechtester Tag %']:.2f} % (TTP-Grenze -3,00 %)")
    print(f"  laengste Unterwasserphase {m['längste DD-Phase (Tage)']} Handelstage "
          f"(~{m['längste DD-Phase (Tage)']/252:.1f} Jahre)")
    yr = t.copy(); yr["Jahr"] = ex.dt.year
    print("\n  Ø R je Jahr:")
    print(yr.groupby("Jahr").agg(Trades=("r", "size"), **{"Ø R": ("r", "mean"),
                                                          "PnL $": ("pnl_usd", "sum")})
          .to_string(float_format=lambda v: f"{v:,.2f}"))

    out = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "final_config_verification.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"\nGespeichert: {out}")


if __name__ == "__main__":
    main()
