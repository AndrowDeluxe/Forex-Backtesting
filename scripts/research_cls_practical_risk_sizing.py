"""Kennzahlen und Risiko-Allokation fuer die finale cls_practical-Konfiguration
(Nutzerfragen 2026-09-10: "haben wir immer noch ein profitables Edge?",
"wie wirkt sich das auf die wichtigsten Backtest-Ratios aus bei 0,5 % Risiko
auf 100k?" und "muss sich unsere Risikologik fuer das Bein aendern, um die
optimale Mischung aus Rendite und Regeleinhaltung zu haben?").

FINALE KONFIGURATION (Ergebnis der Studien vom 2026-09-09/10):
  - min_sl_pips = 5, Modus "drop"     (Pip-Boden, siehe SL-Studie)
  - Entry-Gate "SL schon beruehrt"    (am 2026-09-09 gebaut)
  - Entry-Gate R-Detektor <= 0,75R    (Ideen-Inbox 2026-09-09, hier bestaetigt)
  - TP unveraendert (adr_mult 0.35, adr_period 14)
Alles unter den GEMESSENEN TTP-Kosten (2,05 Pips Round-Trip) und auf einer
LIVE-SIMULATION (Entry 10 Min. nach der Signalbar, Sizing auf |Live-Kurs - SL|),
nicht auf dem idealisierten Backtest.

WARUM DIE RISIKOFRAGE NICHT TRIVIAL IST: das P&L skaliert exakt linear mit
risk_pct (units = risk / sl_dist), PF/Trefferquote/Ø R sind davon unberuehrt.
Was NICHT linear-egal ist, sind die Regelgrenzen der Challenges:
  TTP:  Tagesverlust-Deckel 3 %, Gesamt-Drawdown 7 %, Ziel +10 %
  IQ:   Gesamt-Drawdown 6 %, Ziel +8 %
Und: das Bein laeuft NICHT allein -- CAPITAL_WEIGHT ist 1/6, es teilt sich das
Konto mit fuenf weiteren Beinen. Ein Bein, das allein 4 % Drawdown zieht,
verbraucht mehr als die Haelfte des TTP-Budgets.

Aufruf:
    python scripts/research_cls_practical_risk_sizing.py
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
from research_cls_practical_entry_gate import simulate_live_entries
from research_cls_practical_sl_optimization import (
    COSTS_PIPS,
    DEFAULT_END,
    DEFAULT_START,
    OTHER_MAJORS,
    SPLIT,
    pips_to_bps,
)

pd.set_option("display.width", 230)
pd.set_option("display.max_columns", 40)

INITIAL_EQUITY = 100_000.0
BASE_RISK_PCT = 0.0025          # Basis der Live-Simulation (= heutiges Live-Risiko)
BASE_RISK_DOLLARS = INITIAL_EQUITY * BASE_RISK_PCT
TRADING_DAYS = 252
RULES = {"TTP": {"daily": 0.03, "total_dd": 0.07, "target": 0.10},
         "IQ": {"daily": None, "total_dd": 0.06, "target": 0.08}}


def equity_metrics(daily_pnl: pd.Series) -> dict:
    """$-PnL-Equity-Kurve statt strategy/metrics.py::summarize() -- dieselbe
    Begruendung wie in scripts/research_cls_practical_final_verification.py:
    summarize() unterstellt ein Sizing-Modell, das diese Strategie nicht hat."""
    equity = INITIAL_EQUITY + daily_pnl.cumsum()
    ret = equity.pct_change().fillna(0.0)
    dd = equity / equity.cummax() - 1.0
    years = len(daily_pnl) / TRADING_DAYS
    total = equity.iloc[-1] / INITIAL_EQUITY - 1.0
    cagr = (equity.iloc[-1] / INITIAL_EQUITY) ** (1 / years) - 1 if years > 0 and equity.iloc[-1] > 0 else np.nan
    sharpe = ret.mean() / ret.std(ddof=1) * np.sqrt(TRADING_DAYS) if ret.std(ddof=1) > 0 else 0.0
    downside = ret[ret < 0].std(ddof=1)
    sortino = ret.mean() / downside * np.sqrt(TRADING_DAYS) if downside and downside > 0 else np.nan
    max_dd = float(dd.min())
    # laengste Zeit unter Wasser, in Handelstagen
    under = (dd < -1e-12).astype(int)
    longest, cur = 0, 0
    for v in under:
        cur = cur + 1 if v else 0
        longest = max(longest, cur)
    return {
        "Gesamt-Return %": 100 * total, "CAGR %": 100 * cagr, "Sharpe": sharpe,
        "Sortino": sortino, "MaxDD %": 100 * max_dd,
        "Calmar": (cagr / abs(max_dd)) if max_dd else np.nan,
        "schlechtester Tag %": 100 * float(daily_pnl.min() / INITIAL_EQUITY),
        "bester Tag %": 100 * float(daily_pnl.max() / INITIAL_EQUITY),
        "längste DD-Phase (Tage)": longest,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default=DEFAULT_START)
    ap.add_argument("--end", default=DEFAULT_END)
    args = ap.parse_args()

    print(f"Lade Daten {args.start}..{args.end} ...")
    e = fetch_eurusd_entry_tf_berlin("M5", args.start, args.end)
    o = {p: fetch_major_m15_berlin(p, args.start, args.end) for p in OTHER_MAJORS}
    b = fetch_rate_instrument_m5_berlin("BUND", args.start, args.end)
    u = fetch_rate_instrument_m5_berlin("USTBOND", args.start, args.end)
    price = float(e["close"].mean())
    cost = COSTS_PIPS["TTP"]

    def final_live(**kw):
        raw = simulate_cls_practical(
            e, o, b, u, risk_pct=BASE_RISK_PCT,
            spread_bps=pips_to_bps(cost, price), slippage_bps=0.0, min_sl_pips=5, **kw)
        lv = simulate_live_entries(raw, e, 2, cost)
        return lv[(~lv["sl_touched"]) & (lv["consumed_r"] <= 0.75)].dropna(subset=["r"])

    taken = final_live()
    ex = taken["exit_time"].dt.tz_localize(None)
    print(f"  Finale Konfiguration: {len(taken)} Trades, "
          f"{ex.min():%Y-%m-%d} .. {ex.max():%Y-%m-%d}\n")

    # ---------------------------------------------- Ist der Edge belastbar?
    rng = np.random.default_rng(7)
    r = taken["r"].to_numpy()
    idx = rng.integers(0, len(r), size=(20000, len(r)))
    means = r[idx].mean(axis=1)
    print("=" * 110)
    print("1) IST DER EDGE BELASTBAR? (Bootstrap, 20.000 Resamples)")
    print("=" * 110)
    print(f"  Ø R = {r.mean():+.3f}   90 %-Intervall [{np.percentile(means,5):+.3f} .. "
          f"{np.percentile(means,95):+.3f}]   P(Ø R < 0) = {(means<0).mean():.2%}")
    r_is, r_oos = r[(ex < SPLIT).to_numpy()], r[(ex >= SPLIT).to_numpy()]
    print(f"  In-Sample  {len(r_is):>3} Trades: Ø R {r_is.mean():+.3f}")
    print(f"  Out-of-S.  {len(r_oos):>3} Trades: Ø R {r_oos.mean():+.3f}")
    print(f"  Trades/Jahr: {len(r) / ((ex.max()-ex.min()).days/365.25):.1f}")

    # -------------------------------- Kennzahlen bei verschiedenen Risikostufen
    full_days = pd.date_range(taken["exit_time"].min().tz_localize(None).floor("D"),
                              taken["exit_time"].max().tz_localize(None).floor("D"), freq="B")
    base_daily = taken.groupby(ex.dt.floor("D"))["pnl_usd"].sum().reindex(full_days, fill_value=0.0)

    print("\n" + "=" * 150)
    print("2) KENNZAHLEN JE RISIKOSTUFE (Bein allein, 100k, fixes $-Risiko -- PnL skaliert exakt linear)")
    print("=" * 150)
    rows = []
    for rp in (0.0025, 0.00375, 0.005, 0.0075, 0.01):
        scale = rp / BASE_RISK_PCT
        m = equity_metrics(base_daily * scale)
        m = {"risk_pct": f"{rp:.3%}", "$ je Trade": INITIAL_EQUITY * rp, **m}
        m["Hebel max (x Equity)"] = float(taken["leverage"].max() * scale)
        m["Verletzt TTP 7 % DD"] = "JA" if -m["MaxDD %"] / 100 < -RULES["TTP"]["total_dd"] else "nein"
        m["Verletzt TTP 3 % Tag"] = "JA" if m["schlechtester Tag %"] < -100 * RULES["TTP"]["daily"] else "nein"
        m["Verletzt IQ 6 % DD"] = "JA" if -m["MaxDD %"] / 100 < -RULES["IQ"]["total_dd"] else "nein"
        rows.append(m)
    df = pd.DataFrame(rows)
    print(df.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    print("\n  Zur Einordnung: das Bein laeuft NICHT allein -- CAPITAL_WEIGHT = 1/6.")
    print("  Der ausgewiesene Drawdown ist der des BEINS; die Challenge-Grenze gilt fuer das GESAMTKONTO.")

    # ------------------------------------------------ TP-Frage im Live-Setup
    print("\n" + "=" * 110)
    print("3) TP adr 0.35 vs 0.75 -- IM LIVE-SETUP, mit Bootstrap")
    print("=" * 110)
    for am in (0.35, 0.50, 0.75):
        t = final_live(adr_mult=am)
        rr = t["r"].to_numpy()
        ii = rng.integers(0, len(rr), size=(20000, len(rr)))
        mm = rr[ii].mean(axis=1)
        exx = t["exit_time"].dt.tz_localize(None)
        wr = 100 * (t["pnl_usd"] > 0).mean()
        print(f"  adr_mult={am:<5g} n={len(t):>3}  Treffer {wr:5.1f}%  Ø R {rr.mean():+.3f}  "
              f"[{np.percentile(mm,5):+.3f} .. {np.percentile(mm,95):+.3f}]  "
              f"P(<0) {(mm<0).mean():5.2%}  IS {rr[(exx<SPLIT).to_numpy()].mean():+.3f} / "
              f"OOS {rr[(exx>=SPLIT).to_numpy()].mean():+.3f}")

    out = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "risk_sizing_final.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"\nGespeichert: {out}")


if __name__ == "__main__":
    main()
