"""SMH-Elite-Teamaufgabe "Mikrostruktur & Liquiditaet": Auswertung K1-K3,
Runde 2 (18.10.2026, Paper-Screening smh_microstructure/screening_v2.json): K4-K7.

Ablauf (vorab festgelegt, 07.10.2026):
  is      -- deklarierte Varianten nur auf IS rechnen, Versuche zaehlen,
             Prueffragen (Haelften, Nachbarwerte, Gegenprobe, ohne Top 5).
  freeze  -- beste IS-Variante je Kandidat einfrieren (auch wenn negativ).
  oos     -- OOS je Kandidat genau einmal oeffnen. Team-Kandidat = bester
             nach OOS, festgelegt VOR dem Tresor.
  tresor  -- Tresor je Kandidat genau einmal oeffnen. Ergebnis zaehlt.

    python scripts/research_smh_microstructure.py is K1
    python scripts/research_smh_microstructure.py freeze K1
    python scripts/research_smh_microstructure.py oos K1
    python scripts/research_smh_microstructure.py tresor K1
"""

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research_lock import Lock, config_hash, deflated_sharpe  # noqa: E402
from smh_microstructure import fix_windows as fw  # noqa: E402
from smh_microstructure import liquidity_reversal as lr  # noqa: E402
from smh_microstructure import overnight_drift as od  # noqa: E402
from smh_microstructure import periodicity as pr  # noqa: E402
from smh_microstructure import report as R  # noqa: E402
from smh_microstructure import round_numbers as rn  # noqa: E402
from smh_microstructure import wmr_fix as wf  # noqa: E402
from smh_microstructure.data import load  # noqa: E402

OUT = ROOT / "smh_microstructure" / "results"
FX = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
IDX = ["SP500", "NASDAQ"]

CANDIDATES = {
    "K1": {"lock": "smh_k1_round_numbers", "mod": rn, "syms": FX, "col": "pnl_r",
           "variants": {"fade": rn.Config(mode="fade"), "cascade": rn.Config(mode="cascade")},
           # Nachbarwerte +-20 % je Parameter
           "neighbours": {"approach_pips": (16, 24), "stop_pips": (12, 18), "target_pips": (12, 18),
                          "hold_min": (48, 72)},
           # Gegenprobe: gleiche Mechanik an Schein-Leveln
           "controls": {f"level+{o}": {"offset_pips": o} for o in (13, 26, 37, 63, 74, 87)}},
    "K2": {"lock": "smh_k2_wmr_fix", "mod": wf, "syms": FX, "col": "pnl_bps",
           "variants": {"alle_tage": wf.Config(), "monatsende": wf.Config(month_end_only=True)},
           "neighbours": {"pre_start": ("15:36", "15:24"), "exit": ("16:51", "17:12")},
           # Gegenprobe: gleiche Regel zu Uhrzeiten ohne Fix
           "controls": {f"{h}:00 statt 16:00": {"pre_start": f"{h - 1}:30", "fix": f"{h}:00",
                                                 "entry": f"{h}:03", "exit": f"{h + 1}:00"}
                        for h in (11, 13, 19)}},
    "K3": {"lock": "smh_k3_liq_reversal", "mod": lr, "syms": IDX, "col": "pnl_bps",
           "variants": {"basis": lr.Config(), "hohe_vola": lr.Config(high_vol_only=True)},
           "neighbours": {"z": (1.6, 2.4), "lookback_days": (16, 24), "hold_min": (24, 36)},
           # Gegenprobe: jede halbe Stunde gegen die Bewegung, ohne grosse Bewegung als Ausloeser
           "controls": {"ohne z-Filter": {"z": 0.0}}},
    # ---- Runde 2 (18.10.2026): Top 4 aus dem Paper-Screening -------------------------
    # K4 Krohn/Mueller/Whelan (JF 2024) Europa-Fenster + Breedon/Ranaldo (2013) Sitzungs-Variante.
    "K4": {"lock": "smh_k4_fix_europa", "mod": fw, "syms": ["EURUSD", "GBPUSD", "USDCHF"], "col": "pnl_bps",
           "variants": {"beide": fw.Config(window="europa"),
                        "nur_vor_ezb": fw.Config(window="europa", leg_post=False),
                        "nur_nach_london": fw.Config(window="europa", leg_pre=False),
                        "breedon": fw.Config(window="europa", breedon=True)},
           "neighbours": {"pre_start_shift_min": (-75, 75), "post_end_shift_min": (-75, 75)},
           "controls": {f"alle Zeiten {h:+d} h": {"shift_h": h} for h in (-3, 3, 6)}},
    # K5 Krohn/Mueller/Whelan Tokio-Fenster; Gotobi-Variante nach Ito/Yamada (JIE 2017).
    "K5": {"lock": "smh_k5_fix_tokio", "mod": fw, "syms": ["USDJPY", "AUDUSD", "NZDUSD", "EURUSD"], "col": "pnl_bps",
           "variants": {"beide": fw.Config(window="tokio"),
                        "nur_vor_tokio": fw.Config(window="tokio", leg_post=False),
                        "nur_nach_tokio": fw.Config(window="tokio", leg_pre=False),
                        "gotobi": fw.Config(window="tokio", gotobi_only=True)},
           "neighbours": {"pre_start_shift_min": (-45, 45), "post_end_shift_min": (-70, 70)},
           "controls": {f"alle Zeiten {h:+d} h": {"shift_h": h} for h in (-4, 4, 8)}},
    # K6 Heston/Korajczyk/Sadka (JF 2010) Halbstunden-Periodizitaet auf den Index-CFDs.
    "K6": {"lock": "smh_k6_periodizitaet", "mod": pr, "syms": IDX, "col": "pnl_bps",
           "variants": {"L20": pr.Config(lookback_days=20), "L40": pr.Config(lookback_days=40),
                        "L20_thr1": pr.Config(lookback_days=20, thr=1.0),
                        "L40_thr1": pr.Config(lookback_days=40, thr=1.0)},
           "neighbours": {"lookback_days": "±20%", "thr": "±20%"},
           "controls": {f"Signal aus Slot +{k}": {"slot_shift": k} for k in (1, 3, 6)}},
    # K7 Boyarchenko/Larsen/Whelan (NY-Fed SR 917) Overnight Drift zur Europa-Eroeffnung.
    "K7": {"lock": "smh_k7_overnight_drift", "mod": od, "syms": IDX, "col": "pnl_bps",
           "variants": {"02-03": od.Config(), "0130-0330": od.Config(start="01:30", end="03:30"),
                        "abverkauf": od.Config(condition="abverkauf"),
                        "stark": od.Config(condition="stark")},
           "neighbours": {"start_shift_min": (-15, 15), "end_shift_min": (-15, 15)},
           "controls": {f"{a}-{b} statt 02-03": {"start": a, "end": b}
                        for a, b in (("22:00", "23:00"), ("05:00", "06:00"), ("12:00", "13:00"))}},
}

ROUND2 = ("K4", "K5", "K6", "K7")
SPLIT = ("2018-04-01", "2023-03-31", "2025-09-30", "2026-10-16")  # wie K1-K3; Tresor bis Datenstand


WARMUP_DAYS = 400  # K3: 20-Tage-Sigma + 250-Tage-Vola-Median brauchen Vorlauf


def stage_window(lock: Lock, stage: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    s = lock.split
    if stage == "is":
        a, b = s["is_start"], s["is_end"]
    elif stage == "oos":
        a, b = pd.Timestamp(s["is_end"]) + pd.Timedelta(days=1), s["oos_end"]
    else:
        a, b = pd.Timestamp(s["oos_end"]) + pd.Timedelta(days=1), s["tresor_end"]
    return pd.Timestamp(a, tz="UTC"), pd.Timestamp(b, tz="UTC") + pd.Timedelta(days=1)


def data_for(c, stage: str, lock: Lock) -> dict:
    """Daten der Stufe PLUS Vorlauf aus der Vergangenheit (nie aus der Zukunft).
    Trades werden danach auf das Stufenfenster gefiltert (trades_in)."""
    if stage != "is":
        lock.stage_slice(pd.DataFrame(index=pd.DatetimeIndex([], tz="UTC")), stage)  # wirft, wenn versiegelt
    a, b = stage_window(lock, stage)
    return {s: (lambda df: df[(df.index >= a - pd.Timedelta(days=WARMUP_DAYS)) & (df.index < b)])(load(s))
            for s in c["syms"]}


def trades_in(tr: pd.DataFrame, lock: Lock, stage: str) -> pd.DataFrame:
    a, b = stage_window(lock, stage)
    return tr[(tr["entry_time"] >= a) & (tr["entry_time"] < b)].reset_index(drop=True)


def sharpe(x: np.ndarray) -> float:
    return float(x.mean() / x.std(ddof=1)) if len(x) > 1 and x.std(ddof=1) > 0 else 0.0


def summary(tr: pd.DataFrame, col: str) -> dict:
    m = R.metrics(tr, col)
    if not m.get("n"):
        return m
    h1, h2 = R.halves(tr, col)
    m.update({"half1_sum": h1["sum"], "half2_sum": h2["sum"],
              "ohne_top5_sum": R.without_best(tr, 5, col)["sum"],
              "brutto_avg": float((tr[col] + (tr["cost_bps"] if "cost_bps" in tr else 0)).mean())
              if col == "pnl_bps" else None,
              "je_symbol": {s: round(float(g[col].sum()), 1) for s, g in tr.groupby("sym")},
              "je_jahr": {int(y): round(float(v), 1) for y, v in tr.groupby(tr.entry_time.dt.year)[col].sum().items()}})
    return m


def stage_is(key: str) -> dict:
    c = CANDIDATES[key]
    lock = Lock(c["lock"])
    if key in ROUND2:
        lock.register_split(*SPLIT)
    data = data_for(c, "is", lock)
    if lock.trials == 0:
        lock.log_trials(len(c["variants"]), f"{key}: deklarierte Basis-Varianten")
    res = {"variants": {}, "neighbours": {}}
    for name, cfg in c["variants"].items():
        tr = trades_in(c["mod"].run_all(data, cfg), lock, "is")
        res["variants"][name] = summary(tr, c["col"])
        tr.to_csv(OUT / f"{key}_is_{name}.csv", index=False)
        print(f"{key} {name:10s} {R.fmt(R.metrics(tr, c['col']))}")
    best = max(res["variants"], key=lambda k: res["variants"][k].get("avg", -1e9))
    # Nachbarwerte nur fuer die beste Variante (Robustheit, keine Auswahl)
    for p, vals in c["neighbours"].items():
        if vals == "±20%":
            base = getattr(c["variants"][best], p)
            vals = () if not base else tuple(type(base)(round(base * f, 2)) for f in (0.8, 1.2))
        for v in vals:
            cfg = replace(c["variants"][best], **{p: v})
            tr = trades_in(c["mod"].run_all(data, cfg), lock, "is")
            m = R.metrics(tr, c["col"])
            res["neighbours"][f"{p}={v}"] = {"n": m.get("n"), "avg": m.get("avg"), "pf": m.get("pf"), "t": m.get("t")}
            print(f"   Nachbar {p}={v}: {R.fmt(m)}")
    # Gegenprobe (brutto, damit der Mechanismus sichtbar ist, nicht die Kosten)
    res["controls"] = {}
    gross = replace(c["variants"][best], cost_mult=0.0)
    m0 = R.metrics(trades_in(c["mod"].run_all(data, gross), lock, "is"), c["col"])
    res["controls"]["ECHT (brutto)"] = {"n": m0.get("n"), "avg": m0.get("avg"), "t": m0.get("t")}
    print(f"   Gegenprobe ECHT brutto: {R.fmt(m0)}")
    for name, kw in c["controls"].items():
        m = R.metrics(trades_in(c["mod"].run_all(data, replace(gross, **kw)), lock, "is"), c["col"])
        res["controls"][name] = {"n": m.get("n"), "avg": m.get("avg"), "t": m.get("t")}
        print(f"   Gegenprobe {name} brutto: {R.fmt(m)}")
    # Kosten-Sensitivitaet
    tr2 = trades_in(c["mod"].run_all(data, replace(c["variants"][best], cost_mult=2.0)), lock, "is")
    res["kosten_x2"] = {k: R.metrics(tr2, c["col"]).get(k) for k in ("n", "pf", "avg", "t")}
    n_extra = len(res["neighbours"]) + 1  # Nachbarn + Kosten x2
    if not (OUT / f"{key}_is.json").exists():
        lock.log_trials(n_extra, f"{key}: Nachbarwerte + Kosten x2 (Robustheit)")
    res["best"] = best
    res["best_config"] = c["variants"][best].as_dict()
    res["trials_logged"] = lock.trials
    (OUT / f"{key}_is.json").write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    return res


def stage_freeze(key: str) -> str:
    c = CANDIDATES[key]
    res = json.loads((OUT / f"{key}_is.json").read_text(encoding="utf-8"))
    h = Lock(c["lock"]).freeze(res["best_config"])
    print(key, "eingefroren:", res["best"], h[:12])
    return h


def stage_open(key: str, stage: str, reeval: bool = False) -> dict:
    """reeval=True: bereits geoeffnete Stufe mit UNVERAENDERTER eingefrorener
    Regel neu auswerten (nur nach Datenfehler-Korrektur, im Log vermerkt)."""
    c = CANDIDATES[key]
    lock = Lock(c["lock"])
    res = json.loads((OUT / f"{key}_is.json").read_text(encoding="utf-8"))
    cfg_dict = res["best_config"]
    h = config_hash(cfg_dict)
    if reeval:
        if lock._load()["frozen"]["hash"] != h:
            raise RuntimeError("eingefrorene Regel weicht ab")
        lock._log("reeval", stage=stage, hash=h, note="Vorlauf-Daten (Warmup) ergaenzt, Regel unveraendert")
    else:
        lock.unseal(stage, h)
    cfg = type(c["variants"][res["best"]])(**cfg_dict)
    data = data_for(c, stage, lock)
    tr = trades_in(c["mod"].run_all(data, cfg), lock, stage)
    tr.to_csv(OUT / f"{key}_{stage}_{res['best']}.csv", index=False)
    out = summary(tr, c["col"])
    x = tr[c["col"]].to_numpy()
    out["dsr"] = deflated_sharpe(sharpe(x), len(x), max(total_trials(), 1)) if len(x) > 2 else None
    (OUT / f"{key}_{stage}.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"{key} {stage}: {R.fmt(R.metrics(tr, c['col']))}  DSR={out['dsr']}")
    return out


def total_trials() -> int:
    """Versuche ueber ALLE Kandidaten beider Runden -- das Team waehlt den besten aus allen."""
    return sum(Lock(c["lock"]).trials for c in CANDIDATES.values())


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    stage, key = sys.argv[1], sys.argv[2]
    if stage.startswith("reeval-"):
        stage_open(key, stage.split("-", 1)[1], reeval=True)
    else:
        {"is": stage_is, "freeze": stage_freeze}.get(stage, lambda k: stage_open(k, stage))(key)
