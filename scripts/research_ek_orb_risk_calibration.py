"""EK: das ORB-Bein nachtraeglich in die Portfolio-Risikostudie aufnehmen und
sein Risiko/Trade sauber kalibrieren.

WARUM NOETIG (Nutzerauftrag 2026-09-22): EKs Bein-Gewichte wurden am
2026-09-10 Monte-Carlo-validiert neu kalibriert. ORB war dort NICHT dabei --
`portfolio_construction/results/ek_v2_realistic_final.json` listet es unter
`removed_strategies` mit der Begruendung "keine Evidenz, dass der Broker die
noetigen Instrumente anbietet". Das bezog sich auf das alte, verworfene
`orb_strategy`-Paket und ist widerlegt: Tickmill bietet US500/US30/USTEC, seit
2026-09-21 platziert EK dort real. Weil die Zahl fehlte, blieb FKs
konservativer Default stehen -- effektiv 0,042 % je Instrument, rund 1/70 von
gold_asb. Das ist kein bewerteter Wert, sondern eine Luecke.

METHODE (bewusst eigenstaendig statt Rueckrechnung der alten Studie):
- Jede Bein-Kurve in `results/legs/<leg>.csv` ist auf 1,00 % Risiko je Trade
  normiert (verifiziert: `<leg>_r200.csv` hat exakt die doppelte Tagesrendite).
  Portfolio-Tagesrendite = Summe(risiko_bein_% x 1-%-Rendite_bein).
- ORB kommt NICHT aus einer alten Datei, sondern wird mit der HEUTE live
  gefahrenen Variante C frisch simuliert (Stop-Order-Entry, gemessene Spreads,
  0,45 bps Einstiegs-Slippage) -- sonst wuerde eine ueberholte Exit-Logik
  kalibriert.
- Monte Carlo: Block-Bootstrap ueber KALENDERMONATE (erhaelt Verlust-Cluster;
  iid-Tage wuerden den Drawdown systematisch zu klein schaetzen).

ENTSCHEIDUNGSREGEL: das groesste ORB-Risiko, bei dem die Reissgefahr des
Portfolios NICHT ueber den heutigen Stand steigt. Nicht "so viel wie die
Studie 2026-09-10 toleriert hat" -- die Toleranz von damals ist eine Eigenschaft
des damaligen Portfolios, nicht ein Freibrief fuer ein zusaetzliches Bein.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import challenge_portfolio.paper_bot as pb  # noqa: E402
from ny_open_orb import filters, regime  # noqa: E402
from ny_open_orb.data import fetch_m5, fetch_m15  # noqa: E402
from ny_open_orb.engine import build_frame, find_entries, simulate  # noqa: E402

LEGS = Path(__file__).resolve().parents[1] / "portfolio_construction" / "results" / "legs"
RNG = np.random.default_rng(20260922)
N_PATHS = 3000
DD_LIMIT = 0.40          # EKs Drawdown-Grenze (Nutzervorgabe "40% ausreizen")

# EK-Ist-Zustand: effektives Risiko je Trade = CAPITAL_WEIGHT (1/8) x LEG_RISK_PCT
CAPITAL_WEIGHT = 1 / 8
LEG_RISK_PCT = {"gold_asb": 0.2347, "trend_pullback": 0.1467, "btc_ema_cross": 0.2347,
                "gold_silver": 0.2347, "cls_practical": 0.0440, "ou_modell": 0.0293}
LEG_FILE = {"gold_asb": "gold_asb", "trend_pullback": "trend_pullback",
            "btc_ema_cross": "btc_ema_cross", "gold_silver": "gold_silver_divergenz_r100",
            "cls_practical": "cls_practical", "ou_modell": "ou_modell"}
LEG_FILE_RISK = {"gold_silver": 1.00}   # _r100 = 1,00 % -- wie die Basis-Dateien

ORB_RISK_HEUTE_PCT = CAPITAL_WEIGHT * 0.01 / 3 * 100   # 0,0417 % je Instrument

# Variante C (live seit 2026-09-21)
ORB_CFG = {
    "SP500": dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=6.0,
                  partial_exit_r=None, partial_exit_fraction=0.0, move_stop_to_be_after_partial=False),
    "US30": dict(stop_atr_mult=0.6, target_mode="r_multiple", target_r_mult=6.0,
                 partial_exit_r=3.0, partial_exit_fraction=0.5, move_stop_to_be_after_partial=False),
    "NASDAQ": dict(stop_atr_mult=0.6, target_mode=None, partial_exit_r=3.0,
                   partial_exit_fraction=0.5, move_stop_to_be_after_partial=False),
}
SPREAD_BPS = {"SP500": 0.84, "US30": 0.48, "NASDAQ": 0.54}


def leg_returns_per_1pct(leg: str) -> pd.Series:
    """Tagesrendite des Beins bei 1,00 % Risiko je Trade."""
    f = LEG_FILE[leg]
    s = pd.read_csv(LEGS / f"{f}.csv", parse_dates=["date"]).set_index("date")["equity"]
    r = s.pct_change().dropna()
    return r / LEG_FILE_RISK.get(leg, 1.00)


def orb_returns_per_1pct() -> pd.Series:
    """ORB unter Variante C: Tages-R-Summe ueber die drei Instrumente.
    1 R = 1 % Risiko, also ist die Tages-R-Summe direkt die 1-%-Tagesrendite."""
    daily = []
    for inst, cfg in ORB_CFG.items():
        m15 = pb._retry(lambda i=inst: fetch_m15(i, "2016-01-01", "2026-09-18"),
                        attempts=3, delay_seconds=5, timeout_seconds=300)
        m5 = pb._retry(lambda i=inst: fetch_m5(i, "2016-01-01", "2026-09-18"),
                       attempts=3, delay_seconds=5, timeout_seconds=300)
        frame = build_frame(m15, m5, range_bars=1)
        all_entries = find_entries(frame, "stop_breakout")
        if inst == "NASDAQ":
            entries = filters.filter_by_weekday(all_entries, exclude=["Wednesday"])
        else:
            longs = filters.filter_by_direction(all_entries, 1)
            bias = regime.ema_trend_bias(m15, frame["session"].unique())
            entries = filters.filter_by_category(longs, filters.values_at(longs, bias), (0.0,))
        t = simulate(frame, entries, spread_bps=SPREAD_BPS[inst], entry_slippage_bps=0.45,
                     slippage_bps=0.30, entry_fill_mode="level", **cfg)
        d = t.set_index(pd.to_datetime(t["exit_time"]).dt.tz_convert("UTC").dt.date)["r_multiple"]
        daily.append(d.groupby(level=0).sum())
        print(f"  ORB {inst}: {len(t)} Trades, Ø R {t['r_multiple'].mean():+.3f}")
    s = pd.concat(daily, axis=1).fillna(0.0).sum(axis=1)
    s.index = pd.to_datetime(s.index)
    return s * 0.01          # 1 R bei 1 % Risiko = 1 % Rendite


def metrics(r: pd.Series) -> dict:
    eq = (1 + r).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    years = (r.index[-1] - r.index[0]).days / 365.25
    cagr = eq.iloc[-1] ** (1 / years) - 1
    return {"cagr": cagr, "maxdd": dd,
            "sharpe": r.mean() / r.std() * np.sqrt(252) if r.std() else np.nan,
            "n_days": len(r)}


def mc_dd(r: pd.Series) -> tuple[float, float]:
    """Block-Bootstrap ueber Kalendermonate -> (P(MaxDD > DD_LIMIT), Median-MaxDD)."""
    blocks = [g.to_numpy() for _, g in r.groupby([r.index.year, r.index.month])]
    idx = RNG.integers(0, len(blocks), size=(N_PATHS, len(blocks)))
    worst = np.empty(N_PATHS)
    for i in range(N_PATHS):
        path = np.concatenate([blocks[j] for j in idx[i]])
        eq = np.cumprod(1 + path)
        worst[i] = (eq / np.maximum.accumulate(eq) - 1).min()
    return float((worst < -DD_LIMIT).mean()), float(np.median(worst))


def main() -> int:
    print("Bein-Renditen laden (je 1 % Risiko/Trade) ...")
    base = {leg: leg_returns_per_1pct(leg) for leg in LEG_RISK_PCT}
    print("ORB unter Variante C frisch simulieren ...")
    base["orb"] = orb_returns_per_1pct()

    frame = pd.concat(base, axis=1).sort_index()
    # Gemeinsames Fenster: ab dem spaetesten Start aller Beine, damit kein Bein
    # abschnittsweise fehlt und den Drawdown kuenstlich glaettet.
    start = max(s.dropna().index.min() for s in base.values())
    end = min(s.dropna().index.max() for s in base.values())
    frame = frame.loc[start:end].fillna(0.0)
    print()
    print(f"Gemeinsames Fenster: {start.date()} .. {end.date()} ({len(frame)} Handelstage)")

    risk_ist = {leg: CAPITAL_WEIGHT * pct * 100 for leg, pct in LEG_RISK_PCT.items()}
    print()
    print("Effektives Risiko je Trade (Ist-Zustand):")
    for leg, r in risk_ist.items():
        print(f"  {leg:16s} {r:5.2f} %")
    print(f"  {'orb (je Instr.)':16s} {ORB_RISK_HEUTE_PCT:5.3f} %")

    def portfolio(orb_pct: float) -> pd.Series:
        r = sum(frame[leg] * risk_ist[leg] for leg in LEG_RISK_PCT)
        return r + frame["orb"] * orb_pct

    print()
    print("=" * 104)
    print(f"ORB-Risiko je Instrument -> Portfolio-Wirkung (Monte Carlo {N_PATHS} Pfade, "
          f"Grenze {DD_LIMIT:.0%})")
    print(f"{'ORB %':>8} {'Faktor':>7} {'CAGR':>9} {'MaxDD hist':>11} {'MC Median-DD':>13} "
          f"{'P(DD>40%)':>10} {'Sharpe':>7}")
    rows = []
    for orb_pct in [ORB_RISK_HEUTE_PCT, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.75, 1.00]:
        r = portfolio(orb_pct)
        m = metrics(r)
        p_break, med_dd = mc_dd(r)
        rows.append({"orb_pct": orb_pct, **m, "p_break": p_break, "med_dd": med_dd})
        mark = "  <- heute" if abs(orb_pct - ORB_RISK_HEUTE_PCT) < 1e-9 else ""
        print(f"{orb_pct:>8.3f} {orb_pct/ORB_RISK_HEUTE_PCT:>6.1f}x {m['cagr']:>8.1%} "
              f"{m['maxdd']:>10.1%} {med_dd:>12.1%} {p_break:>9.1%} {m['sharpe']:>7.2f}{mark}")

    heute = rows[0]
    print()
    print(f"Heutige Reissgefahr P(MaxDD>{DD_LIMIT:.0%}) = {heute['p_break']:.1%}")
    zulaessig = [r for r in rows if r["p_break"] <= heute["p_break"] + 0.005]
    best = max(zulaessig, key=lambda r: r["orb_pct"])
    print(f"Groesstes ORB-Risiko OHNE Anstieg der Reissgefahr: {best['orb_pct']:.3f} % je Instrument "
          f"({best['orb_pct']/ORB_RISK_HEUTE_PCT:.1f}x heute)")
    print(f"  CAGR {heute['cagr']:.1%} -> {best['cagr']:.1%} | hist. MaxDD {heute['maxdd']:.1%} -> "
          f"{best['maxdd']:.1%} | Sharpe {heute['sharpe']:.2f} -> {best['sharpe']:.2f}")
    print()
    print("Entsprechendes LEG_RISK_PCT fuer EK (= ORB%/100 / CAPITAL_WEIGHT): "
          f"{best['orb_pct'] / 100 / CAPITAL_WEIGHT:.4f} je Instrument")

    # Nur-ORB-Sicht: was traegt das Bein allein bei?
    solo = metrics(frame["orb"] * best["orb_pct"])
    print(f"ORB allein bei {best['orb_pct']:.3f} %: CAGR {solo['cagr']:.1%}, MaxDD {solo['maxdd']:.1%}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
