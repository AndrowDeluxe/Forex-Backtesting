"""CTNL Edge: Kosten- und Ausfuehrungsvalidierung, Proben p6_5-p6_8 (2026-09-21)

Anlass: am 2026-09-17/18 loeste `ctnl_reversal` eine Order-Flut aus, die das
Echtgeld-Konto TTP Konto 1 gebreacht hat. Die URSACHE der Flut (ein fehlender
Live-Deckel) ist behoben -- offen blieb die davon unabhaengige Frage, ob das
CTNL-Bein seine Kosten ueberhaupt verdient.

Der konkrete Verdacht steht in knowledge/areas/realkosten-und-ausfuehrungs-
probe.md, die CTNL namentlich nennt:

    Im Repo standen nebeneinander `spread_bps=0.3` (cls_practical) und
    `spread_bps=8.0` (CTNL) -- beides gegriffene Zahlen.

Verifiziert: strategy/backtest.py::BacktestConfig kennt NUR `spread_bps`. Es
gibt kein Slippage- und kein Kommissionsfeld, beide stehen fuer CTNL auf null.
Genau diese Konstellation kostete bei cls_practical am 09-09 das 2,2-fache des
Budgets im ersten Live-Trade.

VORGEHEN (Muster: scripts/research_ou_execution_costs.py)
Die Signal-/Trade-LISTE bleibt fix -- sie kommt aus genau der Pipeline, die
auch live laeuft (challenge_portfolio/paper_bot.py::_scan_ctnl mit den
CONT_KWARGS/REV_KWARGS aus gold_smc_htf_ltf/live_signal.py). Variiert wird
ausschliesslich die AUSFUEHRUNG. Jede Differenz ist damit reine Ausfuehrung,
keine andere Signalauswahl.

Die Einstiegsseite wird nach dem etablierten Muster aus
scripts/research_cls_practical_entry_gate.py::simulate_live_entries
neu gerechnet. Das ist zulaessig, WEIL die Engine Stop und Ziel am
`trigger_level` des SIGNALS verankert und nicht am Einstiegspreis
(strategy/backtest.py: `stop_level = trigger_level +/- stop_atr_mult*atr`).
Eine spaetere Ausfuehrung verschiebt deshalb nur Einstiegspreis und
Positionsgroesse -- die Ausstiegsseite bleibt, was sie war. Genau das wird
unten in Probe 2 auch explizit nachgeprueft statt angenommen.

LAG-EINHEITEN (die Falle, vor der die Probe-Notiz warnt: Bar-Label != Bar-Schluss)
  Reversal     laeuft auf M15  -> 1 Lag-Bar = 15 Min.
  Continuation laeuft auf M5   -> 1 Lag-Bar =  5 Min.

Real gemessen am Reversal-Bein (134 echte Fills aus bridge_state_*.json,
09-17/09-18): Signal-Label 09:30 -> Live-Entry 09:58. Also 28 Min. nach dem
LABEL, und das bemerkenswert konstant (Median 28, min 28, max 29).

Die Bar mit Label 09:30 schliesst aber erst 09:45, und genau dort fuellt der
Backtest (`open_[entry_i]`, entry_i = Signalbar + 1). Der fuer Probe 2
relevante Versatz betraegt damit ~13 Min., nicht 28.

WICHTIG, zwei verschiedene Anker -- hier wird man sonst sicher irre:
  * Gegen die SIGNALBAR gemessen passt der real gezahlte Fill am besten auf
    das Open der Bar T+30 (Median-Abweichung 1,28 Preispunkte, gegen 3,44 bei
    T+15 und 4,97 bei T+0).
  * Die Lag-Zahlen UNTEN sind gegen die ENTRY-Bar gemessen, also gegen
    `entry_time` aus dem Trade-Output = Signalbar+1 = T+15.
  => Der reale Betriebspunkt ist deshalb LAG 1 in der Tabelle unten,
     nicht Lag 2. Dieselben 13 Minuten, nur anderer Nullpunkt.

Es werden mehrere Lags gerechnet, nicht einer: ist die Kurve nicht monoton,
ist der Effekt in diesem Bereich Rauschen -- dann wird das so gesagt, statt
einen einzelnen Wert als Befund zu verkaufen.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR))

from gold_smc_htf_ltf.concurrent_backtest import simulate_trades_concurrent  # noqa: E402
from gold_smc_htf_ltf.continuation import run_pipeline as run_continuation  # noqa: E402
from gold_smc_htf_ltf.data import (  # noqa: E402
    fetch_gold_h1,
    fetch_gold_h4,
    fetch_gold_m5,
    fetch_gold_m15,
)
from gold_smc_htf_ltf.live_signal import (  # noqa: E402
    CONT_KWARGS,
    CONT_STOP_ATR_MULT,
    REV_KWARGS,
    REV_MAX_CONCURRENT,
    REV_STOP_ATR_MULT,
    REV_TP_R,
)
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal  # noqa: E402
from strategy.backtest import BacktestConfig, simulate_trades  # noqa: E402

# Die live gefahrenen Engine-Konfigurationen, 1:1 aus challenge_portfolio/
# paper_bot.py::_scan_ctnl uebernommen. Bewusst hier dupliziert statt importiert:
# _scan_ctnl() holt seine Daten selbst und laesst sich keine eigene Historie
# uebergeben. Eine stille Divergenz wuerde diesen ganzen Vergleich wertlos
# machen -- deshalb prueft _assert_live_config_match() die Werte unten gegen
# die importierbare Quelle der Wahrheit.
CONT_CFG = dict(spread_bps=8.0, stop_atr_mult=0.5, use_vwap_target=True,
                breakeven_trigger_r=None, max_hold_bars=24 * 12)
REV_CFG = dict(spread_bps=8.0, stop_atr_mult=3.0, use_vwap_target=False,
               take_profit_r=5.0, breakeven_trigger_r=None, max_hold_bars=96 * 4)


def _assert_live_config_match() -> None:
    """Haelt die oben duplizierten Werte gegen gold_smc_htf_ltf/live_signal.py.

    Deckt die Stop-/Ziel-Parameter ab, also genau die Groessen, an denen die
    Proben 2 und 4 haengen. Laeuft bei jedem Start; lieber ein harter Abbruch
    als eine Auswertung, die eine andere Strategie beschreibt als die
    gehandelte."""
    expected = {
        ("ctnl_continuation", "stop_atr_mult"): (CONT_CFG["stop_atr_mult"], CONT_STOP_ATR_MULT),
        ("ctnl_reversal", "stop_atr_mult"): (REV_CFG["stop_atr_mult"], REV_STOP_ATR_MULT),
        ("ctnl_reversal", "take_profit_r"): (REV_CFG["take_profit_r"], REV_TP_R),
    }
    bad = [f"{leg}.{key}: hier {mine} vs. live_signal.py {theirs}"
           for (leg, key), (mine, theirs) in expected.items() if mine != theirs]
    if bad:
        raise SystemExit("Config-Divergenz zu live_signal.py:\n  " + "\n  ".join(bad))

ASSUMED_SPREAD_BPS = 8.0  # die gegriffene Zahl, die hier auf den Pruefstand kommt
LAGS = (0, 1, 2, 3, 4)


# --------------------------------------------------------------------------- Daten


def _utc_naive(s):
    s = pd.to_datetime(s)
    if isinstance(s, pd.DatetimeIndex):
        return s.tz_convert(None) if s.tz is not None else s
    if getattr(s, "dt", None) is not None:
        return s.dt.tz_convert(None) if s.dt.tz is not None else s
    return s.tz_convert(None) if s.tzinfo is not None else s


def load_bars(start: str, end: str, force_refresh: bool = False) -> dict:
    """Vollhistorie, NICHT das 90-Tage-Live-Fenster (LOOKBACK_DAYS). Fuer eine
    Kostenaussage braucht es die Trade-Zahl; das Live-Fenster ist eine
    offengelegte Naeherung fuer den Scan-Takt, keine Backtest-Grundlage."""
    return {
        "h4": fetch_gold_h4(start, end, force_refresh=force_refresh),
        "h1": fetch_gold_h1(start, end, force_refresh=force_refresh),
        "m15": fetch_gold_m15(start, end, force_refresh=force_refresh),
        "m5": fetch_gold_m5(start, end, force_refresh=force_refresh),
    }


def _cap_concurrent(rev_trades: pd.DataFrame, max_concurrent: int) -> pd.DataFrame:
    """Identisch zu challenge_portfolio/paper_bot.py::_cap_concurrent_reversals.

    ACHTUNG, hier liegt der Fund vom 2026-09-19: diese Kappung ist ein
    SIMULATIONS-Filter. Live wirkt sie nicht, weil sie bei jedem Scan neu
    ueber eine neu simulierte Liste laeuft. Fuer die Kostenfrage ist sie
    trotzdem die richtige Referenz -- sie beschreibt, was die Strategie
    LAUT DESIGN handeln sollte."""
    if rev_trades.empty:
        return rev_trades
    entry = _utc_naive(rev_trades["entry_time"])
    exit_ = _utc_naive(rev_trades["exit_time"])
    open_exits: list = []
    keep = []
    for idx in entry.sort_values().index:
        e, x = entry.loc[idx], exit_.loc[idx]
        open_exits = [t for t in open_exits if t > e]
        if len(open_exits) >= max_concurrent:
            continue
        open_exits.append(x)
        keep.append(idx)
    return rev_trades.loc[keep].sort_index()


def build_trades(bars: dict, spread_bps: float) -> dict[str, pd.DataFrame]:
    """Trade-Listen beider Beine bei gegebenem Kostenansatz."""
    cont_sig = run_continuation(bars["h4"], bars["h1"], bars["m5"],
                                trend_df=bars["m15"], **CONT_KWARGS)
    cont = simulate_trades(cont_sig, BacktestConfig(**{**CONT_CFG, "spread_bps": spread_bps}))

    rev_sig = run_reversal(bars["h4"], bars["h1"], bars["m15"], **REV_KWARGS)
    rev = simulate_trades_concurrent(rev_sig, BacktestConfig(**{**REV_CFG, "spread_bps": spread_bps}))
    rev = _cap_concurrent(rev, REV_MAX_CONCURRENT)
    return {"ctnl_continuation": cont, "ctnl_reversal": rev}


# ------------------------------------------------------- Probe 2: Ausfuehrungs-Lag


def stop_level(t: pd.Series) -> float:
    """Absolutes Stop-Niveau aus dem Trade-Output rekonstruiert.

    Die Engine gibt `initial_risk` (= |entry_price - stop_level|) aus, aber
    nicht das Niveau selbst. Der Stop liegt immer auf der Verlustseite:
    long -> darunter, short -> darueber. Also stop = entry - direction*risk.
    """
    return float(t["entry_price"]) - int(t["direction"]) * float(t["initial_risk"])


def replay_with_lag(trades: pd.DataFrame, bars: pd.DataFrame, lag: int,
                    roundtrip_price_frac: float) -> pd.DataFrame:
    """Rechnet jeden Trade auf den verzoegerten Live-Einstieg um.

    Muster: research_cls_practical_entry_gate.py::simulate_live_entries.
    Die Ausstiegsseite (`exit_price`) bleibt unveraendert -- siehe
    Modul-Docstring, der Stop haengt am Signal-Level.

    `roundtrip_price_frac` ist der Round-Trip-Kostenanteil am PREIS
    (bps/10_000); davon wird die Haelfte auf der Einstiegsseite belastet,
    exakt wie in strategy/backtest.py (`half_cost_frac`).
    """
    idx = _utc_naive(bars.index)
    pos = {t: i for i, t in enumerate(idx)}
    op = bars["open"].to_numpy()
    hi = bars["high"].to_numpy()
    lo = bars["low"].to_numpy()
    half = roundtrip_price_frac / 2.0

    rows = []
    for _, t in trades.iterrows():
        i = pos.get(_utc_naive(t["entry_time"]))
        if i is None or i + lag >= len(op):
            continue
        d = int(t["direction"])
        sl = stop_level(t)
        planned = float(t["initial_risk"])
        if planned <= 0:
            continue

        raw = float(op[i + lag])
        entry_live = raw * (1 + d * half)
        # Restabstand zum Stop = der Nenner, auf den die Bridge real sizet
        eff = (entry_live - sl) * d
        consumed_r = (planned - eff) / planned

        # Wurde der Stop zwischen Signal-Fill und verzoegertem Fill schon beruehrt?
        seg = slice(i, i + lag + 1)
        sl_touched = bool((lo[seg] <= sl).any() if d == 1 else (hi[seg] >= sl).any())

        exit_price = float(t["exit_price"])
        r = (d * (exit_price - entry_live) / eff) if eff > 0 else np.nan
        rows.append({
            "entry_time": t["entry_time"], "exit_time": t["exit_time"], "direction": d,
            "entry_backtest": float(t["entry_price"]), "entry_live": entry_live,
            "sl": sl, "planned_risk": planned, "effective_risk": eff,
            "consumed_r": consumed_r, "sl_touched": sl_touched,
            "inflation": (planned / eff) if eff > 0 else np.inf,
            "exit_price": exit_price, "exit_reason": t["exit_reason"], "r": r,
        })
    return pd.DataFrame(rows)


# Der R-Detektor der Bridges (Funded-Portfolio-Bridge/run_once.py:247,
# FKInstantFunding-MT5-Bridge/run_once.py:395). Ueber die Identitaet
# Aufblaehung = 1/(1-X) ist das zugleich ein Hebel-Deckel bei 2,0x.
MAX_CONSUMED_R_FOR_ENTRY = 0.50


def summarize(df: pd.DataFrame, n_signals: int, apply_gate: bool) -> dict:
    """apply_gate=True bildet nach, was die Bridges WIRKLICH tun.

    Ohne das Gate ist `avg_r` hier nicht interpretierbar: laeuft der Kurs bis
    dicht an den Stop, geht der Nenner (`effective_risk`) gegen null und ein
    einzelner Trade reisst den Mittelwert ins Absurde (gemessen: Ø R -11,8 beim
    Continuation-Bein, Lag 1, 0,73 bps). Live kaeme dieser Trade nie zustande --
    der R-Detektor lehnt ihn ab. Die ungegateten Zahlen werden trotzdem
    mitgefuehrt, weil sie zeigen, WIE VIEL das Gate hier eigentlich abfaengt.

    Zusaetzlich wird der Median-R ausgewiesen. Bei einer derart schiefen
    Verteilung ist der Mittelwert allein irrefuehrend -- genau die Warnung aus
    Probe 3 ("Verteilung ausweisen, nicht nur den Median")."""
    ok = df[df["effective_risk"] > 0]
    gated_out = 0
    if apply_gate:
        keep = ok["consumed_r"] <= MAX_CONSUMED_R_FOR_ENTRY
        gated_out = int((~keep).sum())
        ok = ok[keep]
    r = ok["r"].dropna()
    wins = r[r > 0]
    losses = r[r <= 0]
    return {
        "signale": int(n_signals),
        "handelbar": int(len(ok)),
        "vom_r_detektor_abgelehnt": gated_out,
        "unhandelbar_kurs_jenseits_stop": int(len(df) - len(df[df["effective_risk"] > 0])),
        "sl_bereits_beruehrt": int(df["sl_touched"].sum()),
        "avg_r": float(r.mean()) if len(r) else float("nan"),
        "median_r": float(r.median()) if len(r) else float("nan"),
        "summe_r": float(r.sum()) if len(r) else 0.0,
        "trefferquote": float((r > 0).mean()) if len(r) else float("nan"),
        "profit_factor": (float(wins.sum() / abs(losses.sum()))
                          if len(losses) and losses.sum() != 0 else float("nan")),
        "hebel_median": float(ok["inflation"].median()) if len(ok) else float("nan"),
        "hebel_p90": float(ok["inflation"].quantile(0.90)) if len(ok) else float("nan"),
        "hebel_max": float(ok["inflation"].max()) if len(ok) else float("nan"),
    }


# ------------------------------------------- Probe 4: Stopdistanz gegen die Kosten


def stop_vs_cost(trades: pd.DataFrame, roundtrip_price_frac: float) -> dict:
    """Anteil der Trades mit Stopdistanz < 3x Round-Trip-Kosten und deren Ø R,
    SEPARAT ausgewiesen (so verlangt es die Probe-Notiz p6_8)."""
    if trades.empty:
        return {"trades": 0}
    cost = trades["entry_price"].astype(float) * roundtrip_price_frac
    dist = trades["initial_risk"].astype(float)
    tight = dist < 3 * cost
    r = trades["r_multiple"].astype(float)
    return {
        "trades": int(len(trades)),
        "kosten_median_preis": float(cost.median()),
        "stopdistanz_median_preis": float(dist.median()),
        "stopdistanz_in_kosten_median": float((dist / cost).median()),
        "anteil_eng": float(tight.mean()),
        "n_eng": int(tight.sum()),
        "avg_r_eng": float(r[tight].mean()) if tight.any() else float("nan"),
        "avg_r_weit": float(r[~tight].mean()) if (~tight).any() else float("nan"),
    }


# ----------------------------------------------------------------------- Ausgabe


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2020-01-01")
    ap.add_argument("--end", default=pd.Timestamp.utcnow().strftime("%Y-%m-%d"))
    ap.add_argument("--force-refresh", action="store_true")
    ap.add_argument("--measured-bps", type=float, default=None,
                    help="Gemessene XAUUSD-Round-Trip-Kosten in bps (aus "
                         "scripts/measure_broker_spreads.py). Ohne Angabe wird nur "
                         "die angenommene Zahl gerechnet.")
    ap.add_argument("--out", type=Path,
                    default=REPO_DIR / "knowledge" / "_data" / "ctnl_execution_costs.json")
    args = ap.parse_args()

    _assert_live_config_match()

    print(f"Lade Gold-Bars {args.start} .. {args.end} ...")
    bars = load_bars(args.start, args.end, args.force_refresh)
    for k, v in bars.items():
        print(f"  {k}: {len(v):,} Bars  {v.index.min()} .. {v.index.max()}")

    bar_source = {"ctnl_continuation": bars["m5"], "ctnl_reversal": bars["m15"]}
    bar_minutes = {"ctnl_continuation": 5, "ctnl_reversal": 15}

    cost_scenarios = {"angenommen_8bps": ASSUMED_SPREAD_BPS}
    if args.measured_bps is not None:
        cost_scenarios["gemessen"] = args.measured_bps

    result: dict = {"start": args.start, "end": args.end, "szenarien": {}}

    for label, bps in cost_scenarios.items():
        frac = bps / 10_000.0
        print(f"\n{'='*78}\nKOSTENSZENARIO: {label}  ({bps:.2f} bps Round-Trip)\n{'='*78}")
        trades = build_trades(bars, bps)
        szen: dict = {"spread_bps": bps, "beine": {}}

        for leg, tr in trades.items():
            print(f"\n--- {leg}: {len(tr)} Trades")
            if tr.empty:
                szen["beine"][leg] = {"trades": 0}
                continue

            # Probe 4
            p4 = stop_vs_cost(tr, frac)
            print(f"  Probe 4 (Stopdistanz gegen Kosten):")
            print(f"    Stopdistanz Median = {p4['stopdistanz_in_kosten_median']:.1f}x Round-Trip-Kosten")
            print(f"    Anteil < 3x Kosten: {p4['anteil_eng']:.1%} ({p4['n_eng']} Trades)"
                  f" | Ø R eng {p4['avg_r_eng']:+.3f} vs. weit {p4['avg_r_weit']:+.3f}")

            # Probe 2 + 3
            rows: dict = {"mit_gate": {}, "ohne_gate": {}}
            print(f"  Probe 2/3 (Lag, 1 Bar = {bar_minutes[leg]} Min.)")
            print(f"    MIT 0,50R-Detektor -- so verhaelt sich die Bridge wirklich:")
            print(f"    {'Lag':>4} {'Min.':>5} {'handelb.':>9} {'abgel.':>7} {'ØR':>8} "
                  f"{'MedR':>7} {'PF':>6} {'Treffer':>8} {'Hebel p90':>10} {'Hebel max':>10}")
            replays = {lag: replay_with_lag(tr, bar_source[leg], lag, frac) for lag in LAGS}
            for lag in LAGS:
                s = summarize(replays[lag], len(tr), apply_gate=True)
                rows["mit_gate"][lag] = s
                print(f"    {lag:>4} {lag*bar_minutes[leg]:>5} {s['handelbar']:>9} "
                      f"{s['vom_r_detektor_abgelehnt']:>7} {s['avg_r']:>+8.3f} "
                      f"{s['median_r']:>+7.3f} {s['profit_factor']:>6.2f} "
                      f"{s['trefferquote']:>7.1%} {s['hebel_p90']:>10.2f} {s['hebel_max']:>10.2f}")

            print(f"    OHNE Gate (nur zum Vergleich -- zeigt, was das Gate abfaengt):")
            for lag in LAGS:
                s = summarize(replays[lag], len(tr), apply_gate=False)
                rows["ohne_gate"][lag] = s
                print(f"    {lag:>4} {lag*bar_minutes[leg]:>5} {s['handelbar']:>9} "
                      f"{'-':>7} {s['avg_r']:>+8.3f} {s['median_r']:>+7.3f} "
                      f"{s['profit_factor']:>6.2f} {s['trefferquote']:>7.1%} "
                      f"{s['hebel_p90']:>10.2f} {s['hebel_max']:>10.2f}")

            # Monotonie-Pruefung: ist die Lag-Kurve nicht monoton, ist der
            # Effekt in diesem Bereich Rauschen (so verlangt es die Probe-Notiz).
            # Gegen den MEDIAN gerechnet, nicht gegen den Mittelwert -- dieser
            # ist bei der schiefen R-Verteilung hier nicht robust.
            meds = [rows["mit_gate"][l]["median_r"] for l in LAGS]
            monoton = all(a >= b for a, b in zip(meds, meds[1:]))
            print(f"    Lag-Kurve (Median-R, mit Gate) monoton fallend: "
                  f"{'ja' if monoton else 'NEIN -> in diesem Bereich Rauschen'}")

            szen["beine"][leg] = {"probe4": p4, "probe2_3": rows,
                                  "lag_kurve_monoton": bool(monoton),
                                  "bar_minuten": bar_minutes[leg]}
        result["szenarien"][label] = szen

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {args.out}")


if __name__ == "__main__":
    main()
