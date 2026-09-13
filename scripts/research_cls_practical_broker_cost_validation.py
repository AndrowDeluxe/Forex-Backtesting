"""Phase-6-Kostenvalidierung fuer cls_practical, je Broker getrennt
(Nutzerauftrag 2026-09-09 nach dem Live-Vorfall desselben Tages).

ANLASS: am 2026-09-09 lief EIN cls_practical-Signal ueber drei Konten. Alle
drei wurden binnen 16 Sekunden ausgestoppt, mit zusammen $1.634 Kosten gegen
ein Risikobudget von $741 -- Faktor 2,2. Der Verdacht "das Kostenmodell des
Backtests ist zu optimistisch" hat sich bestaetigt, aber ANDERS als zuerst
vermutet (siehe scripts/measure_broker_spreads.py fuer die Messung):

  - Der SPREAD ist NICHT das Problem. Gemessen im Handelsfenster:
    TTP 0,30 Pips, IQ Markets 0,10 Pips. Der Engine-Default spread_bps=0.3
    (~0,35 Pips Round-Trip) liegt damit ungefaehr richtig.
  - SLIPPAGE und KOMMISSION fehlen dagegen komplett. Gemessen am realen
    Trade: TTP 0,70 Pips Einstiegs- + 0,65 Pips Ausstiegs-Slippage + 0,40
    Pips Kommission; IQ 0,30 + 0,40 + 0,50 Pips. Der Engine-Default
    slippage_bps=0.0 unterschlaegt also den GROESSTEN Kostenblock.

Zusammen ergibt das echte Round-Trip-Kosten von ~2,05 Pips (TTP) bzw. ~1,30
Pips (IQ) -- bei einer Strategie, deren Stop-Abstand im Median bei wenigen
Pips liegt. Genau das ist die Frage, die dieses Skript beantwortet.

METHODE (Phase 6 aus app_pages/education_gold_intraday.py):
  p6_3 Kosten-Sensitivitaet -- Sweep der Gesamtkosten bis zum Breakeven,
       jeder Broker als Marker auf derselben Achse.
  p6_1 Out-of-Sample -- Split 2022-06-01, identisch zu
       scripts/research_cls_practical_final_verification.py.
  p6_4 Regime -- Aufschluesselung je Jahr.
  Zusatz: Verteilung der Stop-Abstaende und wieviel Ergebnis an Trades
       haengt, deren Stop kleiner ist als die realen Kosten.

KOSTENABBILDUNG in cls_practical/engine.py (dort verifiziert):
  entry_price = trigger_level +/- half_spread
  Stop-Exit   = current_sl -/+ half_spread -/+ slip
  TP-Exit     = tp -/+ half_spread
  d.h. spread_bps ist die ROUND-TRIP-Groesse (halb beim Ein-, halb beim
  Ausstieg), slippage_bps kommt NUR beim Stop-Exit dazu.

Alle Kosten werden hier deshalb in spread_bps gebuendelt: der Live-Bot setzt
KEINEN Broker-TP (target=None in Funded-Portfolio-Bridge/run_once.py), jeder
Ausstieg ist also eine Marktorder und slippt real -- die Kosten auf ALLE
Ausstiege zu legen ist naeher an der Realitaet als "nur auf Stops".

Aufruf:
    python scripts/research_cls_practical_broker_cost_validation.py [--start 2018-12-01]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from cls_practical.data import (
    fetch_eurusd_entry_tf_berlin,
    fetch_major_m15_berlin,
    fetch_rate_instrument_m5_berlin,
)
from cls_practical.engine import simulate_cls_practical
from strategy.cls_advanced import PAIRS

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)

DEFAULT_START, DEFAULT_END = "2018-12-01", "2026-09-09"
SPLIT = "2022-06-01"  # identisch zu research_cls_practical_final_verification.py
OTHER_MAJORS = [p for p in PAIRS if p != "EURUSD"]

# Live-aequivalentes Risiko: das Challenge-Portfolio riskiert je CLS-Trade
# CAPITAL_WEIGHT (1/6) x LEG_RISK_PCT["cls_practical"] (0.015) = 0,25% der
# Equity (challenge_portfolio/paper_bot.py). Der engine-Default 0,5% waere
# doppelt so hoch wie das, was real gehandelt wird.
RISK_PCT = 0.0025
INITIAL_EQUITY = 100_000.0

# Gemessene Round-Trip-Kosten je Broker in PIPS (scripts/measure_broker_spreads.py,
# Messung 2026-09-09, Fenster 08:00-12:30 Berlin, 30 Tage Rueckblick).
# Spread: Tick-Median ueber ~350k bzw. ~250k Ticks -- belastbar.
# Slippage/Kommission: aus dem EINEN realen CLS-Trade vom 2026-09-09 (n=1) --
# ausdruecklich duenn, deshalb ist der Sweep unten die eigentliche Aussage und
# diese Punkte nur Marker darauf.
BROKER_COSTS_PIPS = {
    "Funded / TTPMarkets":      {"spread": 0.30, "commission": 0.40, "slip_in": 0.70, "slip_out": 0.65, "measured": True},
    "Funded / BeyondIQCapital": {"spread": 0.10, "commission": 0.50, "slip_in": 0.30, "slip_out": 0.40, "measured": True},
    # EK/Tickmill: Kommission $0.00 ueber 331 Lots ist gesichert. Der Spread im
    # Handelsfenster ist es NICHT -- die Tickhistorie des Terminals deckt
    # 08:00-12:30 mit 15 Ticks praktisch nicht ab, der Median ueber alle
    # Tageszeiten liegt bei 0,20 Pips. Slippage ist mangels EURUSD-Trades gar
    # nicht messbar und hier von TTP/IQ uebernommen. ALLES UNTER VORBEHALT.
    "EK / TickmillEU (geschaetzt)": {"spread": 0.20, "commission": 0.00, "slip_in": 0.50, "slip_out": 0.50, "measured": False},
}


def total_cost_pips(c: dict) -> float:
    return c["spread"] + c["commission"] + c["slip_in"] + c["slip_out"]


def pips_to_bps(pips: float, price: float) -> float:
    """1 Pip = 0.0001 Preiseinheiten bei EURUSD; bps bezogen auf den Kurs."""
    return pips * 0.0001 / price * 10_000


def metrics(trades: pd.DataFrame, label: str) -> dict:
    """R-Vielfaches ist hier die Leitkennzahl: pnl_usd / risk_amount_usd ist
    exakt das, was der Live-Vorfall in "2,2x des Budgets" ausgedrueckt hat.
    Auf die $-Equity-Kurve (Muster research_cls_practical_final_verification.py)
    kommt es zusaetzlich fuer MaxDD an."""
    if trades.empty:
        return {"Szenario": label, "Trades": 0}
    r = trades["pnl_usd"] / trades["risk_amount_usd"]
    wins, losses = trades[trades["pnl_usd"] > 0], trades[trades["pnl_usd"] <= 0]
    gross_win, gross_loss = wins["pnl_usd"].sum(), abs(losses["pnl_usd"].sum())

    day = trades["exit_time"].dt.tz_localize(None).dt.floor("D")
    daily = trades.groupby(day)["pnl_usd"].sum().sort_index()
    equity = INITIAL_EQUITY + daily.cumsum()
    max_dd = (equity / equity.cummax() - 1.0).min()

    return {
        "Szenario": label,
        "Trades": len(trades),
        "Treffer%": 100.0 * len(wins) / len(trades),
        "PF": (gross_win / gross_loss) if gross_loss > 0 else float("inf"),
        "Ø R": r.mean(),
        "PnL $": trades["pnl_usd"].sum(),
        "MaxDD %": 100.0 * max_dd,
    }


def run(data: dict, cost_pips: float, price: float) -> pd.DataFrame:
    """Alle Kosten in spread_bps gebuendelt (Begruendung siehe Modul-Docstring),
    slippage_bps bleibt 0 -- sonst wuerde der Stop-Exit doppelt belastet."""
    return simulate_cls_practical(
        data["eurusd_m5"], data["other_majors_m15"], data["bund_m5"], data["ustbond_m5"],
        risk_pct=RISK_PCT, spread_bps=pips_to_bps(cost_pips, price), slippage_bps=0.0,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default=DEFAULT_START)
    ap.add_argument("--end", default=DEFAULT_END)
    args = ap.parse_args()

    print(f"Lade Daten {args.start}..{args.end} ...")
    data = {
        "eurusd_m5": fetch_eurusd_entry_tf_berlin("M5", args.start, args.end),
        "other_majors_m15": {p: fetch_major_m15_berlin(p, args.start, args.end) for p in OTHER_MAJORS},
        "bund_m5": fetch_rate_instrument_m5_berlin("BUND", args.start, args.end),
        "ustbond_m5": fetch_rate_instrument_m5_berlin("USTBOND", args.start, args.end),
    }
    price = float(data["eurusd_m5"]["close"].mean())
    print(f"  {len(data['eurusd_m5']):,} M5-Baren, mittlerer Kurs {price:.5f} "
          f"(1 Pip = {pips_to_bps(1.0, price):.3f} bps)\n")

    # ---------------------------------------------------------------- Szenarien
    # Engine-Default (spread_bps=0.3) in Pips ausgedrueckt, damit Status quo und
    # Broker-Szenarien auf EINER Achse vergleichbar sind.
    scenarios = [("Status quo (engine-default)", 0.3 / pips_to_bps(1.0, price))]
    for name, c in BROKER_COSTS_PIPS.items():
        scenarios.append((name, total_cost_pips(c)))

    rows, trades_by_scenario = [], {}
    for name, cp in scenarios:
        t = run(data, cp, price)
        trades_by_scenario[name] = t
        label = f"{name} [{cp:.2f} Pips]"
        rows.append(metrics(t, label))
        if not t.empty:
            ex = t["exit_time"].dt.tz_localize(None)
            rows.append(metrics(t[ex < SPLIT], f"    davon In-Sample (<{SPLIT})"))
            rows.append(metrics(t[ex >= SPLIT], f"    davon Out-of-Sample (>={SPLIT})"))

    print("=" * 120)
    print("SZENARIEN -- gleiche Signale, unterschiedliche Round-Trip-Kosten")
    print("=" * 120)
    df = pd.DataFrame(rows)
    print(df.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    # ------------------------------------------------------- p6_3 Kosten-Sweep
    print("\n" + "=" * 120)
    print("p6_3 KOSTEN-SENSITIVITAET -- Gesamtkosten Round-Trip vs. Erwartungswert")
    print("=" * 120)
    sweep_rows = []
    for cp in [0.0, 0.25, 0.5, 0.75, 1.0, 1.3, 1.6, 2.05, 2.5, 3.0, 4.0]:
        t = run(data, cp, price)
        if t.empty:
            continue
        r = t["pnl_usd"] / t["risk_amount_usd"]
        ex = t["exit_time"].dt.tz_localize(None)
        r_oos = (t[ex >= SPLIT]["pnl_usd"] / t[ex >= SPLIT]["risk_amount_usd"])
        sweep_rows.append({
            "Kosten (Pips)": cp, "Trades": len(t), "Ø R": r.mean(),
            "Ø R (OOS)": r_oos.mean() if len(r_oos) else float("nan"),
            "PnL $": t["pnl_usd"].sum(),
        })
    sweep = pd.DataFrame(sweep_rows)
    print(sweep.to_string(index=False, float_format=lambda v: f"{v:,.3f}"))

    be = _breakeven_cost_pips(data, price)
    print(f"\n  BREAKEVEN (Ø R = 0) bei rund {be:.2f} Pips Round-Trip-Kosten.")
    for name, c in BROKER_COSTS_PIPS.items():
        tc = total_cost_pips(c)
        verdict = "UNTER Breakeven (traegt)" if tc < be else "UEBER Breakeven (traegt NICHT)"
        flag = "" if c["measured"] else "  [geschaetzt, nicht gemessen]"
        print(f"    {name:32} {tc:.2f} Pips -> {verdict}{flag}")

    # ------------------------------------------------------------ p6_4 Regime
    print("\n" + "=" * 120)
    print("p6_4 JAHRESAUFSCHLUESSELUNG (Ø R je Jahr)")
    print("=" * 120)
    per_year = {}
    for name, t in trades_by_scenario.items():
        if t.empty:
            continue
        tt = t.copy()
        tt["Jahr"] = tt["exit_time"].dt.year
        per_year[name] = tt.groupby("Jahr").apply(
            lambda g: (g["pnl_usd"] / g["risk_amount_usd"]).mean(), include_groups=False
        )
    print(pd.DataFrame(per_year).to_string(float_format=lambda v: f"{v:+.3f}"))

    # -------------------------------------------- Zusatz: Stop-Abstandsanalyse
    print("\n" + "=" * 120)
    print("STOP-ABSTAENDE -- wie viel Ergebnis haengt an Trades, deren Stop kleiner ist als die Kosten?")
    print("=" * 120)
    base = trades_by_scenario["Status quo (engine-default)"]
    sl_pips = base["sl_distance"] / 0.0001
    print(f"  sl_distance in Pips: Median {sl_pips.median():.1f} | p10 {sl_pips.quantile(.10):.1f} "
          f"| p25 {sl_pips.quantile(.25):.1f} | p75 {sl_pips.quantile(.75):.1f} | max {sl_pips.max():.1f}")
    ttp = trades_by_scenario["Funded / TTPMarkets"]
    ttp_sl = ttp["sl_distance"] / 0.0001
    for k in (1, 2, 3, 5):
        thresh = k * total_cost_pips(BROKER_COSTS_PIPS["Funded / TTPMarkets"])
        sub = ttp[ttp_sl < thresh]
        share = 100.0 * len(sub) / len(ttp) if len(ttp) else 0.0
        r_sub = (sub["pnl_usd"] / sub["risk_amount_usd"]).mean() if len(sub) else float("nan")
        r_rest = ((ttp[ttp_sl >= thresh]["pnl_usd"] / ttp[ttp_sl >= thresh]["risk_amount_usd"]).mean()
                  if len(ttp) > len(sub) else float("nan"))
        print(f"  Stop < {k}x TTP-Kosten ({thresh:5.2f} Pips): {len(sub):4d} Trades ({share:4.1f}%) "
              f"| Ø R dieser Trades {r_sub:+.3f} | Ø R der uebrigen {r_rest:+.3f}")

    out = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "broker_cost_validation.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    sweep.to_csv(out.with_name("broker_cost_sweep.csv"), index=False)
    print(f"\nGespeichert: {out}\n           {out.with_name('broker_cost_sweep.csv')}")


def _breakeven_cost_pips(data: dict, price: float, lo: float = 0.0, hi: float = 6.0) -> float:
    """Bisektion auf die Gesamtkosten, bei denen das mittlere R auf 0 faellt.
    Muster von strategy/metrics.py::breakeven_spread_bps -- dort nicht direkt
    aufrufbar, weil es an strategy.backtest.simulate_trades haengt und
    cls_practical eine eigene Engine hat."""
    def mean_r(cp: float) -> float:
        t = run(data, cp, price)
        if t.empty:
            return -np.inf
        return float((t["pnl_usd"] / t["risk_amount_usd"]).mean())

    if mean_r(lo) < 0:
        return lo  # schon kostenfrei unprofitabel
    if mean_r(hi) > 0:
        return hi  # traegt selbst die breitesten getesteten Kosten
    for _ in range(12):
        mid = (lo + hi) / 2
        if mean_r(mid) > 0:
            lo = mid
        else:
            hi = mid
        if hi - lo < 0.05:
            break
    return (lo + hi) / 2


if __name__ == "__main__":
    main()
