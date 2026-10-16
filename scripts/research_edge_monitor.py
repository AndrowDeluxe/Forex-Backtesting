"""Fruehwarnung + Kill-Switch fuer kippende Edges (Plan 2026-10-14).

Frage des Nutzers: "Wie koennen wir im Vorhinein feststellen, ab wann der
Edge kippt? Anzeichen, die vorwarnen, und wie ein Kill-Switch funktioniert."
Entscheide: ORB + weitere bekannte Brueche, erst Research + Report, Aktion
Pausieren + Schattenkonto mit Hysterese-Wiedereinstieg.

Vorgehen (Lock edge_monitor_20261014):
  calibrate  Schwellen je Fall NUR aus dem Kalibrierfenster (siehe
             edge_monitor/cases.py), Bootstrap unter "Edge intakt",
             Fehlalarm-Budget streng (1 je 5 J.) / locker (1 je 2 J.).
             Regelwerk (Signale, Budgets, Kombination) wird eingefroren.
  evaluate   einmal: Schalter auf der Zeit NACH dem Kalibrierfenster.
             Kennzahlen je Fall/Regel: Σ R ohne/mit Schalter, Fehlalarm-
             Kosten vor dem letzten Equity-Hoch, vermiedene R danach,
             Verzug bis zum ersten Alarm nach dem Hoch, Anteil Zeit in Pause.
  status     aktuelle Ampel je Live-Bein (gruen / gelb = locker rot /
             rot = streng rot) aus der jeweils vorhandenen Broker-Trade-Liste.

Regeln (vorab fest):
  5 Einzelsignale (edge_monitor/signals.py) x 2 Budgets = 10
  "2 von 5" (locker) = 1;  ORB IS-only zusaetzlich Ribbon-Schatten-Spread x 2 = 2

  python scripts/research_edge_monitor.py --stage calibrate
  python scripts/research_edge_monitor.py --stage evaluate
  python scripts/research_edge_monitor.py --stage status
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))

from edge_monitor import calibrate, cases, signals, switch  # noqa: E402
from research_lock import Lock  # noqa: E402

LOCK = "edge_monitor_20261014"
RES = ROOT / "edge_monitor" / "results"
RES.mkdir(parents=True, exist_ok=True)
SPREAD_W = 40
RULEBOOK = {"signale": list(signals.SIGNALS), "budgets": calibrate.BUDGETS, "kombi": "2 von 5 (locker)",
            "regime_orb": f"Ribbon-Schatten-Spread {SPREAD_W} Trades je Modus", "roll_n": signals.ROLL_N,
            "bayes_w": signals.BAYES_W, "bootstrap": {"paths": calibrate.N_PATHS, "jahre": calibrate.YEARS},
            "hysterese": "Freigabe auf halbem Weg Normalwert -> Schwelle", "aktion": "Pause + Schattenkonto"}


def lock() -> Lock:
    lk = Lock(LOCK)
    lk.register_split("2016-07-28", "2022-12-31", "2026-09-30")   # formal; Kalibrierfenster je Fall in cases.py
    return lk


def _close_sorted(t: pd.DataFrame):
    order = switch.close_order(t.exit_time)
    return order, t.r.to_numpy()[order]


def ribbon_spread(t: pd.DataFrame, shadow: pd.DataFrame) -> np.ndarray:
    """Nach jedem geschlossenen eigenen Trade: Ø R der letzten W Trend-Trades
    minus Ø R der letzten W eigenen (neutralen) Trades, je nur geschlossene."""
    order, r_close = _close_sorted(t)
    ex = pd.DatetimeIndex(t.exit_time).values[order]
    sh = shadow.sort_values("exit_time")
    sh_ex, sh_r = pd.DatetimeIndex(sh.exit_time).values, sh.r.to_numpy()
    sh_c = np.cumsum(np.r_[0.0, sh_r]); own_c = np.cumsum(np.r_[0.0, r_close])
    out = np.full(len(r_close), np.nan)
    for i in range(len(r_close)):
        k = np.searchsorted(sh_ex, ex[i], side="right")
        if i + 1 >= SPREAD_W and k >= SPREAD_W:
            out[i] = (sh_c[k] - sh_c[k - SPREAD_W]) / SPREAD_W - (own_c[i + 1] - own_c[i + 1 - SPREAD_W]) / SPREAD_W
    return out


def _empirical_thr(b_cal: np.ndarray, years: float) -> dict:
    v = b_cal[~np.isnan(b_cal)]
    b0 = float(np.median(v))
    cand = np.unique(np.quantile(v, np.linspace(0.5, 1.0, 300)))
    res = {}
    for name, budget in calibrate.BUDGETS.items():
        pick = float(cand[-1]) + 1e-9
        for thr in cand:
            if switch.episodes_seq(b_cal, thr, b0 + (thr - b0) / 2) <= budget * years:
                pick = float(thr)
                break
        res[name] = (pick, b0 + (pick - b0) / 2)
    return res


def stage_calibrate() -> int:
    lk = lock()
    allc = cases.all_cases()
    n_rules = len(signals.SIGNALS) * len(calibrate.BUDGETS) + 1 + 2
    if lk.trials == 0:
        lk.log_trials(n_rules, note=f"{n_rules} vorab feste Regeln, je Fall angewendet ({len(allc)} Faelle); keine Auswahl am Bruch")
    out = {}
    for name, c in allc.items():
        t = c["trades"]
        cal = t[t.exit_time <= pd.Timestamp(c["cal_end"]) + pd.Timedelta(days=1)]
        years = max(0.5, (cal.entry_time.max() - cal.entry_time.min()).days / 365.25)
        cfg = calibrate.thresholds(cal.r.to_numpy(), len(cal) / years)
        if "shadow_trend" in c:
            b = ribbon_spread(t, c["shadow_trend"])
            ncal = len(cal)
            cfg["signale"]["ribbon_spread"] = _empirical_thr(b[:ncal], years)
        cfg["cal_end"], cfg["gruppe"], cfg["n_cal"] = c["cal_end"], c["gruppe"], len(cal)
        out[name] = cfg  # gleiche Methode wie _calibrate_case
        print(name, "kalibriert:", len(cal), "Trades", flush=True)
    (RES / "schwellen.json").write_text(json.dumps(out, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    h = lk.freeze({"regelwerk": RULEBOOK, "schwellen_datei_faelle": sorted(out)})
    print("eingefroren", h)
    return 0


def _rules(cfg: dict) -> list[tuple[str, str]]:
    return [(s, b) for s in cfg["signale"] for b in calibrate.BUDGETS] + [("2 von 5", "locker")]


def _states(name: str, c: dict, cfg: dict) -> dict:
    t = c["trades"]
    order, r_close = _close_sorted(t)
    mu0, sd0, n0 = cfg["mu0"], cfg["sd0"], cfg["n0"]
    bvals = {s: signals.compute(s, r_close, mu0, sd0, n0) for s in signals.SIGNALS}
    if "ribbon_spread" in cfg["signale"]:
        bvals["ribbon_spread"] = ribbon_spread(t, c["shadow_trend"])
    st = {}
    for s, b in bvals.items():
        for bud in calibrate.BUDGETS:
            thr, rel = cfg["signale"][s][bud]
            st[(s, bud)] = switch.state_seq(b, thr, rel)
    st[("2 von 5", "locker")] = np.sum([st[(s, "locker")] for s in signals.SIGNALS], axis=0) >= 2
    return st, bvals


def stage_evaluate() -> int:
    lk = lock()
    state = lk._load()
    if "oos" not in state["unsealed"]:
        lk.unseal("oos", state["frozen"]["hash"])
    thr = json.loads((RES / "schwellen.json").read_text(encoding="utf-8"))
    allc = cases.all_cases()
    rows = []
    for name, c in allc.items():
        cfg = thr[name]
        t = c["trades"]
        st, _ = _states(name, c, cfg)
        ev = t.entry_time > pd.Timestamp(cfg["cal_end"]) + pd.Timedelta(days=1)
        te = t[ev]
        cum = te.r.cumsum()
        peak_t = te.entry_time.iloc[int(np.argmax(cum.to_numpy()))] if len(te) else None
        after = te.entry_time > peak_t
        base = {"fall": name, "gruppe": cfg["gruppe"], "n_eval": len(te), "sum_ohne": te.r.sum(),
                "hoch_datum": peak_t, "sum_nach_hoch": te.r[after].sum(), "n_nach_hoch": int(after.sum()),
                "sd0": cfg["sd0"]}
        for (s, bud), sts in st.items():
            live = switch.mask_from_states(t.entry_time, t.exit_time, sts)[ev.to_numpy()]
            paused = ~live
            first_after = te.entry_time[paused & after.to_numpy()]
            rows.append({**base, "signal": s, "budget": bud,
                         "sum_mit": te.r[live].sum(),
                         "fehlalarm_kosten": te.r[paused & ~after.to_numpy()].sum(),   # > 0 = verpasste Gewinne vor dem Hoch
                         "vermieden_nach_hoch": -te.r[paused & after.to_numpy()].sum(),
                         "verzug_tage": (first_after.iloc[0] - peak_t).days if len(first_after) else np.nan,
                         "anteil_pause": paused.mean(),
                         "episoden": int(np.sum(np.diff(np.r_[0, paused.astype(int)]) == 1))})
    df = pd.DataFrame(rows)
    df["delta"] = df.sum_mit - df.sum_ohne
    df["delta_sd"] = df.delta / df.sd0          # in Einheiten der Trade-Streuung (vergleichbar ueber Faelle)
    df.to_csv(RES / "auswertung.csv", index=False)
    summ = df.groupby(["signal", "budget"]).agg(
        faelle=("fall", "size"), besser=("delta", lambda x: int((x > 0).sum())),
        delta_sd_median=("delta_sd", "median"), delta_sd_bruch=("delta_sd", lambda x: x[df.loc[x.index, "gruppe"] == "Bruch"].median()),
        delta_sd_live=("delta_sd", lambda x: x[df.loc[x.index, "gruppe"] == "Live-Bein"].median()),
        verzug_median=("verzug_tage", "median"), pause_median=("anteil_pause", "median")).reset_index()
    summ.to_csv(RES / "auswertung_regeln.csv", index=False)
    pd.set_option("display.width", 220); pd.set_option("display.max_rows", 400)
    print(summ.round(2).to_string(index=False))
    cols = ["fall", "signal", "budget", "sum_ohne", "sum_mit", "delta", "fehlalarm_kosten", "vermieden_nach_hoch", "verzug_tage", "anteil_pause", "episoden"]
    print(df[cols].round(2).to_string(index=False))
    return 0


def warnstufe(row: dict) -> str:
    """Seit 2026-10-16 (Nutzerentscheid): rot = Leitsignal drawdown streng rot (der Schalter
    waere aus); gelb = drawdown locker rot ODER ein anderes Signal streng rot; sonst gruen.
    Nur Anzeige im Weekly Report, kein Eingriff in Bots."""
    if row["drawdown"] == "rot":
        return "ROT"
    if row["drawdown"] == "gelb" or any(row[s] == "rot" for s in signals.SIGNALS if s != "drawdown"):
        return "GELB"
    return "gruen"


def _calibrate_case(c: dict) -> dict:
    t = c["trades"]
    cal = t[t.exit_time <= pd.Timestamp(c["cal_end"]) + pd.Timedelta(days=1)]
    years = max(0.5, (cal.entry_time.max() - cal.entry_time.min()).days / 365.25)
    return calibrate.thresholds(cal.r.to_numpy(), len(cal) / years)


def stage_status() -> int:
    """Schwellen werden je Lauf aus DERSELBEN Liste neu kalibriert (eingefrorene Methode,
    Fenster 2019-2022): der Schalter muss den gehandelten Satz messen (Memory
    ctnl-serienstopp) -- z. B. NASDAQ mit Storno seit 04.10. statt der alten Version."""
    rows = []
    legs = cases.live_legs(ampel=True)
    for name, c in legs.items():
        cfg = _calibrate_case(c)
        st, bvals = _states(name, c, cfg)
        row = {"bein": name.split(":", 1)[1], "letzter_trade": c["trades"].exit_time.max().date()}
        for s in signals.SIGNALS:
            row[s] = "rot" if st[(s, "streng")][-1] else ("gelb" if st[(s, "locker")][-1] else "gruen")
        row["warnstufe"] = warnstufe(row)
        b = bvals["drawdown"]
        row["drawdown_R"] = round(float(b[-1]), 1)
        row["drawdown_schwelle_R"] = round(float(cfg["signale"]["drawdown"]["streng"][0]), 1)
        rows.append(row)
    df = pd.DataFrame(rows).sort_values("warnstufe", key=lambda x: x.map({"ROT": 0, "GELB": 1, "gruen": 2}))
    src = "ampel" if (cases.PC / "live_trades_tickmill_ampel.csv").exists() else "2019_2026 (veraltet?)"
    df.to_csv(RES / "status.csv", index=False)
    print(f"Quelle: live_trades_tickmill_{src}, letzter Trade gesamt {df.letzter_trade.max()}")
    print(df.to_string(index=False))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["calibrate", "evaluate", "status"])
    raise SystemExit({"calibrate": stage_calibrate, "evaluate": stage_evaluate, "status": stage_status}[ap.parse_args().stage]())
