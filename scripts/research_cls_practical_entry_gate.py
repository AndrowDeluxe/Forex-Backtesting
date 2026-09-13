"""R-Detektor ("Gegen das Signal"-Gate) -- backgetestet auf einer echten
Live-Entry-Simulation (Nutzerauftrag 2026-09-10).

DIE IDEE (Ideen-Inbox 2026-09-09, bis heute unentschieden): Entry abbrechen,
wenn der Kurs beim Ausfuehrungsversuch bereits mehr als X R der Stopdistanz
GEGEN das Signal gelaufen ist. Der Gate, der am 2026-09-09 tatsaechlich gebaut
wurde, fragt nur "wurde der SL schon beruehrt?" -- den CLS-Trade desselben
Tages haette er NICHT erfasst (der SL war zum Entry noch 0,1 Pip entfernt).

KORREKTUR 2026-09-10: die Ideen-Inbox nannte fuer diesen Trade 0,76R. Aus den
echten Orderdaten nachgerechnet (Signal-sl_distance 3,6 Pips, `price_current`
bei Auftragsannahme 1.16373, MT5-Sizing-Sicht 1,2 Pips Restabstand) waren es
0,61-0,67R -- die Inbox-Zahl beruhte auf einem anderen Referenzpreis und
3,8 statt 3,6 Pips. **Dieser Gate haette den Trade bei 0,75R also NICHT
geblockt.** Geblockt haette ihn der Pip-Boden (3,6 < 5 Pips). Die beiden
Massnahmen greifen in verschiedenen Faellen, nicht in demselben.

WARUM DAS MEHR IST ALS EIN FILTER: die Bridge rechnet die Lots als
`risk_dollars / |Live-Kurs - SL|` (Funded-Portfolio-Bridge/sizing.py). Sind
bereits X R aufgebraucht, ist der Restabstand (1-X) x sl_dist, die Position
also um 1/(1-X) groesser als geplant. Die Gate-Schwelle IST damit exakt ein
Hebel-Deckel:
      0,50R -> hoechstens 2,0x der geplanten Groesse
      0,60R -> hoechstens 2,5x
      0,75R -> hoechstens 4,0x
Am 2026-09-09 waren es 0,76R -> 4,2x, und real wurden aus ~6,9 geplanten Lots
20,8 tatsaechliche.

METHODE -- warum eine Live-Simulation und kein Filter auf Backtest-Trades:
der Backtest steigt zum Schlusskurs der Signalbar ein, der Live-Bot erst beim
naechsten 5-Minuten-Scan. Ein Gate auf den Backtest-Entries wuerde also die
falsche Groesse filtern. Stattdessen wird JEDER Trade auf den verzoegerten
Einstieg umgerechnet:

  Entry_live  = Schlusskurs `lag` Baren nach der Signalbar (+ halbe Kosten)
  units_live  = risk / |Entry_live - SL|        <- die echte Sizing-Formel
  Exit        = unveraendert (SL/TP haengen am trigger_level, nicht am Entry)
  R_live      = units_live x (Exit - Entry_live) / risk

Zwei Abbruchgruende werden dabei getrennt gezaehlt, weil sie verschiedenen
Schutzmechanismen entsprechen:
  - "SL schon beruehrt"  -> der am 2026-09-09 gebaute Restlaufzeit-Gate
  - "X R aufgebraucht"   -> DIESER Gate

VERGLEICHEN wird gegen den ungefilterten Live-Lauf UND gegen den Pip-Boden 5
aus der SL-Studie, jeweils unter den gemessenen TTP-Kosten (2,05 Pips).

Aufruf:
    python scripts/research_cls_practical_entry_gate.py [--lag 2]
"""

import argparse
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
from research_cls_practical_sl_optimization import (
    COSTS_PIPS,
    DEFAULT_END,
    DEFAULT_START,
    INITIAL_EQUITY,
    OTHER_MAJORS,
    RISK_PCT,
    SPLIT,
    pips_to_bps,
)

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)

PIP = 0.0001
RISK_DOLLARS = INITIAL_EQUITY * RISK_PCT
NOTIONAL_PER_LOT = 100_000.0
USD_PER_PIP_PER_LOT = 10.0


def simulate_live_entries(trades: pd.DataFrame, m5: pd.DataFrame, lag: int,
                          cost_pips: float, risk_dollars: float | None = None) -> pd.DataFrame:
    """Rechnet jeden Backtest-Trade auf den verzoegerten Live-Einstieg um.

    Die Ausstiegsseite bleibt unveraendert: SL und TP haengen im Engine am
    `trigger_level` des Signals, nicht am Einstiegspreis -- eine spaetere
    Ausfuehrung verschiebt also NUR Einstiegspreis und Positionsgroesse."""
    close = m5["close"]
    pos = {t: i for i, t in enumerate(m5.index)}
    half_cost = cost_pips * PIP / 2.0
    # Default = das Risiko, mit dem diese Studien begonnen wurden (0,25 % auf
    # 100k). Explizit uebergeben, sobald eine andere Risikostufe geprueft wird
    # -- sonst rechnet die Funktion still weiter mit 250 $ und die
    # ausgewiesenen $-/Drawdown-Zahlen gehoeren zur falschen Stufe.
    risk = RISK_DOLLARS if risk_dollars is None else float(risk_dollars)

    rows = []
    for _, t in trades.iterrows():
        i = pos.get(t["entry_time"])
        if i is None or i + lag >= len(close):
            continue
        d = 1 if t["direction"] == "long" else -1
        sl_dist = float(t["sl_distance"])
        # Einstieg zum Kurs `lag` Baren spaeter, plus halbe Round-Trip-Kosten
        # auf der Einstiegsseite (gleiche Konvention wie in der Engine).
        entry_live = float(close.iloc[i + lag]) + d * half_cost
        eff = (entry_live - float(t["sl"])) * d      # Restabstand zum Stop
        consumed_r = (sl_dist - eff) / sl_dist       # >1 = Kurs jenseits des Stops

        # Wurde der SL zwischen Signalbar und Ausfuehrung schon beruehrt?
        seg = m5.iloc[i:i + lag + 1]
        sl_touched = bool((seg["low"] <= t["sl"]).any() if d == 1 else (seg["high"] >= t["sl"]).any())

        units = risk / eff if eff > 0 else np.nan
        pnl = units * d * (float(t["exit_price"]) - entry_live) if eff > 0 else np.nan
        lots = (units / NOTIONAL_PER_LOT) if eff > 0 else np.nan

        rows.append({
            "entry_time": t["entry_time"], "exit_time": t["exit_time"],
            "direction": t["direction"], "sl_dist_pips": sl_dist / PIP,
            "entry_live": entry_live, "eff_pips": eff / PIP,
            "consumed_r": consumed_r, "sl_touched": sl_touched,
            "lots": lots, "leverage": lots,  # 1 Lot = 100k auf 100k Equity
            "pnl_usd": pnl, "r": pnl / risk if eff > 0 else np.nan,
            "exit_reason": t["exit_reason"],
        })
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame, label: str, n_signals: int) -> dict:
    taken = df.dropna(subset=["r"])
    if taken.empty:
        return {"Gate": label, "Trades": 0, "genommen%": 0.0}
    ex = taken["exit_time"].dt.tz_localize(None)
    r = taken["r"]
    daily = taken.groupby(ex.dt.floor("D"))["pnl_usd"].sum().sort_index()
    eq = INITIAL_EQUITY + daily.cumsum()
    gl = abs(taken[taken["pnl_usd"] <= 0]["pnl_usd"].sum())
    return {
        "Gate": label,
        "Trades": len(taken),
        "genommen%": 100.0 * len(taken) / n_signals,
        "Treffer%": 100.0 * (taken["pnl_usd"] > 0).mean(),
        "PF": (taken[taken["pnl_usd"] > 0]["pnl_usd"].sum() / gl) if gl > 0 else float("inf"),
        "Ø R": float(r.mean()),
        "Ø R (IS)": float(r[ex < SPLIT].mean()) if (ex < SPLIT).any() else float("nan"),
        "Ø R (OOS)": float(r[ex >= SPLIT].mean()) if (ex >= SPLIT).any() else float("nan"),
        "PnL $": float(taken["pnl_usd"].sum()),
        "MaxDD %": 100.0 * float((eq / eq.cummax() - 1.0).min()),
        "Hebel med": float(taken["leverage"].median()),
        "Hebel p90": float(taken["leverage"].quantile(0.90)),
        "Hebel max": float(taken["leverage"].max()),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default=DEFAULT_START)
    ap.add_argument("--end", default=DEFAULT_END)
    ap.add_argument("--lag", type=int, default=2, help="M5-Baren zwischen Signal und Ausfuehrung")
    args = ap.parse_args()

    print(f"Lade Daten {args.start}..{args.end} ...")
    e = fetch_eurusd_entry_tf_berlin("M5", args.start, args.end)
    o = {p: fetch_major_m15_berlin(p, args.start, args.end) for p in OTHER_MAJORS}
    b = fetch_rate_instrument_m5_berlin("BUND", args.start, args.end)
    u = fetch_rate_instrument_m5_berlin("USTBOND", args.start, args.end)
    price = float(e["close"].mean())
    cost = COSTS_PIPS["TTP"]
    print(f"  {len(e):,} M5-Baren | Lag {args.lag} Baren = {args.lag*5} Min. | TTP-Kosten {cost} Pips\n")

    def base_trades(**kw):
        return simulate_cls_practical(
            e, o, b, u, risk_pct=RISK_PCT,
            spread_bps=pips_to_bps(cost, price), slippage_bps=0.0, **kw)

    for floor_label, floor_kw in (("OHNE Pip-Boden", {}), ("MIT Pip-Boden 5", {"min_sl_pips": 5})):
        raw = base_trades(**floor_kw)
        live = simulate_live_entries(raw, e, args.lag, cost)
        n = len(live)

        print("=" * 190)
        print(f"{floor_label} -- {n} Signale, Live-Einstieg {args.lag*5} Min. nach der Signalbar")
        print("=" * 190)

        rows = [summarize(live, "kein Gate (Ist-Zustand)", n)]
        # Der am 2026-09-09 gebaute Gate
        rows.append(summarize(live[~live["sl_touched"]], "nur 'SL schon beruehrt' (gebauter Gate)", n))
        # Der R-Detektor, allein und kombiniert
        for thr in (0.9, 0.75, 0.6, 0.5, 0.4, 0.3):
            sub = live[live["consumed_r"] <= thr]
            rows.append(summarize(sub, f"R-Detektor <= {thr:.2f}R  (Hebel-Deckel {1/(1-thr):.1f}x)", n))
        print(pd.DataFrame(rows).to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

        # Die Frage aus der Ideen-Inbox: mit wieviel Vorlauf starteten die Gewinner?
        ok = live.dropna(subset=["r"])
        if not ok.empty:
            print(f"\n  Verteilung von 'consumed_r' -- die Frage aus der Ideen-Inbox "
                  f"('welcher Anteil der Gewinner startete mit wieviel Vorlauf?'):")
            bins = [-np.inf, 0.0, 0.25, 0.5, 0.75, 1.0, np.inf]
            names = ["<0 (guenstiger)", "0-0.25R", "0.25-0.5R", "0.5-0.75R", "0.75-1R", ">1R (hinter SL)"]
            grp = pd.cut(live["consumed_r"], bins=bins, labels=names)
            tab = live.groupby(grp, observed=False).agg(
                Signale=("consumed_r", "size"),
                Gewinner=("pnl_usd", lambda s: int((s > 0).sum())),
                **{"Ø R": ("r", "mean"), "Hebel med": ("leverage", "median")})
            tab["Anteil%"] = 100.0 * tab["Signale"] / n
            tab["Treffer%"] = 100.0 * tab["Gewinner"] / tab["Signale"].replace(0, np.nan)
            print(tab.to_string(float_format=lambda v: f"{v:,.2f}"))
        print()

    out = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "entry_gate_r_detector.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = base_trades(min_sl_pips=5)
    simulate_live_entries(raw, e, args.lag, cost).to_csv(out, index=False)
    print(f"Gespeichert: {out}")


if __name__ == "__main__":
    main()
