"""Makro-Agent v2: Multi-Faktor-Scorecard der G8-Waehrungen im Backtest.

    python -m scripts.research_macro_scorecard --stage is|oos|tresor

Monatsende: Waehrungen nach Score (gleich gewichtet aus Carry, Zins-Momentum, Preis-Momentum,
Value, Ueberraschungen; fusion_lab/macro_agent/factors.py) sortieren, long die 2 staerksten,
short die 2 schwaechsten, gilt ab dem naechsten Handelstag. Ertrag = Kurs + Zinsdifferenz -
Swap-Aufschlag - Spread (scripts.research_remy_a2_carry.pnl).

Overfitting-Sperre `macro_scorecard_v1` (Regel seit 10.11.2026: OOS frei, Tresor einmal).
Kandidat VOR dem ersten Lauf festgelegt: V3 = Score + COT-Veto + Regime (Nutzerentscheid 11.11.,
feste Gewichte). V1/V2 und die fuenf Einzelfaktoren sind gezaehlte Vergleichsrechnungen.
"""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import pandas as pd
import requests

from fusion_lab.macro_agent import factors, panels
from fusion_lab.macro_agent.fact_sheet import TEST_FILE
from fusion_lab.macro_agent.analytics import state_machine
from fusion_lab.macro_data.sources import FRED_API, _fred_key
from research_lock import Lock, deflated_sharpe
from scripts.remy_common import stats
from scripts.research_remy_a2_carry import pnl

LOCK = Lock("macro_scorecard_v1")
SPLIT = ("2007-01-01", "2016-12-31", "2026-05-10", "2026-11-10")
K = 2
CANDIDATE = {"modell": "scorecard_v1", "faktoren": factors.FACTORS, "gewichte": "gleich", "k": K,
             "veto": [factors.COT_HI, factors.COT_LO], "regime": "TAIL oder STLFSI > 1 -> halb",
             "stlfsi_cut": 1.0}


def fred(series: str) -> pd.Series:
    r = requests.get(FRED_API, params={"series_id": series, "api_key": _fred_key(), "file_type": "json",
                                       "observation_start": "2000-01-01"}, timeout=90)
    r.raise_for_status()
    obs = pd.DataFrame(r.json()["observations"])
    return pd.Series(pd.to_numeric(obs["value"], errors="coerce").values, index=pd.to_datetime(obs["date"])).dropna()


def regime_halves(days: pd.DatetimeIndex) -> pd.Series:
    """Faktor 0,5 an Tagen nach einem TAIL-Tag oder STLFSI > 1 (Werte des Vortags)."""
    import yfinance as yf
    from tradingview.data import fetch_ohlcv
    on = lambda s: s.reindex(s.index.union(days)).ffill().reindex(days)
    vix, hy, fsi = on(fred("VIXCLS")), on(fred("BAMLH0A0HYM2")), on(fred("STLFSI4"))
    brent = yf.download("BZ=F", start="2007-01-01", progress=False, auto_adjust=True)["Close"].squeeze()
    brent.index = pd.to_datetime(brent.index).tz_localize(None)
    oat = None
    try:
        fr, de = (fetch_ohlcv(s, "TVC", interval="1d", n_bars=6000)["close"] for s in ("FR10Y", "DE10Y"))
        spread = ((fr - de) * 100).dropna()
        spread.index = spread.index.normalize()
        oat = on(spread[~spread.index.duplicated(keep="last")])
    except Exception as e:
        print("OAT-Bund nicht verfuegbar:", e)
    brent = on(brent)
    hits = (vix > 28).astype(int) + (hy > 3.5).astype(int) + (brent > 120).astype(int)
    if oat is not None:
        hits += (oat > 180).astype(int)
    tail = hits >= state_machine.TAIL_MIN
    stress = tail | (fsi > CANDIDATE["stlfsi_cut"])
    return pd.Series(np.where(stress.shift(1, fill_value=False), 0.5, 1.0), index=days)


def daily(w_month: pd.DataFrame, days: pd.DatetimeIndex) -> pd.DataFrame:
    return w_month.reindex(days).ffill().fillna(0.0).shift(1).fillna(0.0)


def single_factor(sc: dict, name: str, days) -> pd.DataFrame:
    return daily(factors.month_end_weights({**sc, "score": sc[name]}, K, veto=False), days)


def report(label: str, r: pd.Series, n_trials: int) -> dict:
    s = stats(r)
    yearly = r.groupby(r.index.year).sum()
    dsr = deflated_sharpe(s["sr_d"], s["n"], max(n_trials, 1), s["skew"], s["kurt"])
    print(f"{label:34s} Rend. {s['ret_pa']*100:5.1f} % p.a. | Vol {s['vol_pa']*100:4.1f} % | Sharpe {s['sharpe']:5.2f} "
          f"| t {s['t']:5.2f} | MaxDD {s['maxdd']*100:6.1f} % | DSR {dsr:.2f} | Jahre +{(yearly > 0).sum()}/{len(yearly)}")
    return {**s, "dsr": dsr}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["is", "oos", "tresor"], default="is")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    LOCK.register_split(*SPLIT)

    p = panels.build(pd.Timestamp(SPLIT[3]), point_in_time=False)
    days = pd.bdate_range("2006-01-02", SPLIT[3])
    sc = factors.scorecard(p, days)
    ret = p.value.reindex(days).ffill().diff().fillna(0.0)
    pr = panels._on_days(p.policy, days).ffill()
    half = regime_halves(days)

    variants = {
        "V1 Score": daily(factors.month_end_weights(sc, K, veto=False), days),
        "V2 Score + Veto": daily(factors.month_end_weights(sc, K, veto=True), days),
    }
    variants["V3 Score + Veto + Regime (Kandidat)"] = variants["V2 Score + Veto"].mul(half, axis=0)
    for f in factors.FACTORS:
        variants[f"nur {f}"] = single_factor(sc, f, days)
    results = {k: pnl(w, ret, pr) for k, w in variants.items()}

    state = LOCK._load()
    if state["trials"] == 0:
        LOCK.log_trials(len(variants), "V1-V3 + 5 Einzelfaktoren, Kandidat V3 vorab festgelegt")
    n = LOCK.trials
    print(f"Lock {LOCK.strategy}, Versuche {n}, Split {SPLIT}")

    if args.stage in ("is", "oos"):
        print("\n== IS 2007-2016 ==")
        summary = {"is": {k: report(k, LOCK.is_only(r), n) for k, r in results.items()}}
        if args.stage == "oos":
            h = LOCK.freeze(CANDIDATE)
            print(f"\n== OOS 2017 - 10.05.2026 (Kandidat eingefroren, Hash {h}) ==")
            summary["oos"] = {k: report(k, LOCK.oos_only(r), n) for k, r in results.items()}
        # Kurzfassung fuers Fact Sheet (fusion_lab/macro_agent/fact_sheet.TEST_FILE)
        keep = ("ret_pa", "sharpe", "t", "maxdd", "dsr")
        out = {"lock": LOCK.strategy, "versuche": n, "kandidat": "V3 Score + Veto + Regime (Kandidat)",
               **{stage: {k: {m: round(float(v[m]), 3) for m in keep} for k, v in res.items()}
                  for stage, res in summary.items()}}
        TEST_FILE.parent.mkdir(parents=True, exist_ok=True)
        TEST_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    else:
        h = LOCK.freeze(CANDIDATE)
        start, end = LOCK.unseal("tresor", h)
        print(f"\n== Tresor {start} - {end} (einmalig) ==")
        r = LOCK.stage_slice(results["V3 Score + Veto + Regime (Kandidat)"], "tresor")
        report("V3 Kandidat", r, n)
        print("Monate:", (r.groupby(r.index.to_period("M")).sum() * 100).round(2).to_dict())


if __name__ == "__main__":
    main()
