"""K4b -- Nachtest der eingefrorenen K4-Regel (Vor-EZB-Bein des Dollar-W) auf
frischen Paaren USDNOK/USDSEK. Vorregistrierung: smh_microstructure/k4b_vorregistrierung.json.

    python scripts/research_smh_k4b.py register   # Split, 6 Versuche, Einfrieren (vor jedem Datenblick)
    python scripts/research_smh_k4b.py costs      # Spread-Messung, nur IS-Jahre 2019/2021
    python scripts/research_smh_k4b.py is
    python scripts/research_smh_k4b.py oos
    python scripts/research_smh_k4b.py tresor
"""

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import research_smh_microstructure as base  # noqa: E402
from research_lock import Lock, config_hash, deflated_sharpe  # noqa: E402
from smh_microstructure import fix_windows as fw  # noqa: E402
from smh_microstructure import report as R  # noqa: E402
from smh_microstructure.data import CACHE, load  # noqa: E402

OUT = base.OUT
SYMS = ["USDNOK", "USDSEK"]
LOCK = "smh_k4b_fix_europa_neu"
C = {"lock": LOCK, "mod": fw, "syms": SYMS, "col": "pnl_bps"}
NEIGHBOURS = [("pre_start_shift_min", -75), ("pre_start_shift_min", 75), ("pre_end", "13:15"), ("pre_end", "15:15")]
CONTROLS = {f"alle Zeiten {h:+d} h": {"shift_h": h} for h in (-3, 3, 6)}
N_RANDOM = 2000


def frozen_cfg() -> fw.Config:
    k4 = Lock("smh_k4_fix_europa")._load()["frozen"]
    return fw.Config(**k4["config"])


def register():
    lock = Lock(LOCK)
    lock.register_split(*base.SPLIT)
    cfg = frozen_cfg()
    if lock._load()["frozen"] is None:
        if lock.trials == 0:
            lock.log_trials(1, "K4b: eingefrorene K4-Regel 1:1 auf USDNOK/USDSEK")
            lock.log_trials(len(NEIGHBOURS) + 1, "K4b: Nachbarwerte (4) + Kosten x2, vorregistriert")
        frozen = {**cfg.as_dict(), "syms": SYMS}
        h = lock.freeze(frozen)
        print("eingefroren", h[:12], "K4-Hash", config_hash(cfg.as_dict())[:12], "Versuche", lock.trials)


def costs():
    """Median-Spread Ask-Bid an den Handelsminuten (08:00 / 14:15 Frankfurt), nur 2019+2021."""
    out = {}
    for sym in ["EURUSD"] + SYMS:
        bid = load(sym)
        rows = []
        for y in (2019, 2021):
            ask = pd.read_parquet(CACHE / "ask" / f"{sym}_M1_ASK_{y}.parquet")
            b = bid[(bid.index >= f"{y}-01-01") & (bid.index < f"{y + 1}-01-01")]
            j = b[["open"]].join(ask[["open"]].rename(columns={"open": "ask"}), how="inner")
            loc = j.index.tz_convert("Europe/Berlin")
            hm = loc.strftime("%H:%M")
            j = j[(np.isin(hm, ["08:00", "14:15"])) & (loc.dayofweek < 5)]
            rows.append((j["ask"] - j["open"]) / j["open"] * 1e4)
        s = pd.concat(rows)
        out[sym] = {"spread_bps_median": round(float(s.median()), 3), "n": int(len(s)),
                    "spread_bps_p75": round(float(s.quantile(0.75)), 3)}
    eur_px = float(load("EURUSD", "2019-01-01", "2021-12-31")["open"].median())
    eur_rt = 1.2e-4 / eur_px * 1e4
    add_on = eur_rt - out["EURUSD"]["spread_bps_median"]
    for sym in SYMS:
        out[sym]["rt_bps"] = round(out[sym]["spread_bps_median"] + add_on, 2)
    out["_aufschlag_bps"] = round(add_on, 3)
    out["_eurusd_rt_bps"] = round(eur_rt, 3)
    (OUT / "K4b_kosten.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


def random_test(data: dict, lock: Lock, stage: str, real_gross: float, seed: int = 7) -> dict:
    """2.000 gleich lange Long-USD-Fenster mit zufaelligem Start (Frankfurt 00:00-17:45) je Tag, brutto."""
    rng = np.random.default_rng(seed)
    length = pd.Timedelta(hours=6, minutes=15)
    per = []
    for sym, df in data.items():
        opens = df["open"].copy()
        opens.index = opens.index.as_unit("ns")
        closes = df["close"].copy()
        closes.index = opens.index
        a, b = base.stage_window(lock, stage)
        days = pd.date_range(a.tz_convert("Europe/Berlin").normalize().tz_localize(None),
                             b.tz_convert("Europe/Berlin").normalize().tz_localize(None), freq="D")
        days = days[days.dayofweek < 5]
        per.append((sym, opens, closes, days))
    means = np.empty(N_RANDOM)
    for k in range(N_RANDOM):
        g = []
        for sym, opens, closes, days in per:
            off = rng.integers(0, 17 * 60 + 46, len(days))
            ts0 = (days + pd.to_timedelta(off, unit="min")).tz_localize(
                "Europe/Berlin", nonexistent="shift_forward", ambiguous=False).tz_convert("UTC")
            ts1 = ts0 + length
            pe, px = fw._price_at(opens, ts0), fw._price_at(opens, ts1, closes)
            ok = np.isfinite(pe) & np.isfinite(px)
            side = 1 if sym in fw.USD_BASE else -1
            g.append(side * (px[ok] - pe[ok]) / pe[ok] * 1e4)
        means[k] = np.concatenate(g).mean()
    return {"zufall_mittel_bps": round(float(means.mean()), 3), "zufall_p95_bps": round(float(np.quantile(means, 0.95)), 3),
            "anteil_zufall_besser": round(float((means >= real_gross).mean()), 4)}


def evaluate(stage: str) -> dict:
    lock = Lock(LOCK)
    st = lock._load()
    cfg = frozen_cfg()
    frozen = {**cfg.as_dict(), "syms": SYMS}
    if st["frozen"]["hash"] != config_hash(frozen):
        raise RuntimeError("eingefrorene Regel weicht ab")
    if not (OUT / "K4b_kosten.json").exists():
        raise RuntimeError("erst costs")
    if stage != "is":
        lock.unseal(stage, st["frozen"]["hash"])
    data = base.data_for(C, stage, lock)
    tr = base.trades_in(fw.run_all(data, cfg), lock, stage)
    tr.to_csv(OUT / f"K4b_{stage}.csv", index=False)
    res = base.summary(tr, "pnl_bps")
    x = tr["pnl_bps"].to_numpy()
    n_all = base.total_trials() + lock.trials
    res["dsr"] = deflated_sharpe(base.sharpe(x), len(x), n_all) if len(x) > 2 else None
    res["versuche_gesamt"] = n_all
    res["gross_avg"] = float(tr["gross_bps"].mean())
    print(f"K4b {stage}: {R.fmt(R.metrics(tr, 'pnl_bps'))}  brutto Ø {res['gross_avg']:+.2f}  DSR={res['dsr']}")
    print("   je Paar", res["je_symbol"], " je Jahr", res["je_jahr"], " Haelften", round(res["half1_sum"]), round(res["half2_sum"]))
    res["nachbarn"], res["gegenprobe_brutto"] = {}, {}
    for p, v in NEIGHBOURS:
        m = R.metrics(base.trades_in(fw.run_all(data, replace(cfg, **{p: v})), lock, stage), "pnl_bps")
        res["nachbarn"][f"{p}={v}"] = {k: m.get(k) for k in ("n", "avg", "pf", "t")}
        print(f"   Nachbar {p}={v}: {R.fmt(m)}")
    m = R.metrics(base.trades_in(fw.run_all(data, replace(cfg, cost_mult=2.0)), lock, stage), "pnl_bps")
    res["kosten_x2"] = {k: m.get(k) for k in ("n", "avg", "pf", "t")}
    print(f"   Kosten x2: {R.fmt(m)}")
    gross = replace(cfg, cost_mult=0.0)
    for name, kw in CONTROLS.items():
        m = R.metrics(base.trades_in(fw.run_all(data, replace(gross, **kw)), lock, stage), "pnl_bps")
        res["gegenprobe_brutto"][name] = {k: m.get(k) for k in ("n", "avg", "t")}
        print(f"   Gegenprobe {name} brutto: {R.fmt(m)}")
    res["zufallstest"] = random_test(data, lock, stage, res["gross_avg"])
    print("   Zufallstest", res["zufallstest"])
    (OUT / f"K4b_{stage}.json").write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    return res


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    step = sys.argv[1]
    {"register": register, "costs": costs}.get(step, lambda: evaluate(step))()
