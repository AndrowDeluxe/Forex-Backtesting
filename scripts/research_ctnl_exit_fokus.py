"""Fokusvergleich zu research_ctnl_exit_optimierung.py (2026-10-03): einzelne
Aenderungen gegen den heutigen Funded/FK-Stand, gepaart (Bootstrap), mit
Poll-Verzoegerung 1 (Broker-Bars, Fast-Lane 5 Min.) und 3 (Lake, 15-Min-Lane),
schlimmster Einzeltrade und Jahresbilanz.

Aufruf: python scripts/research_ctnl_exit_fokus.py --cache <pkl>
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_ctnl_exit_optimierung as X  # noqa: E402

VAR = {
    "heute (3 touch, TP5 gepollt, 4T)": dict(k=3.0, stop="touch", tp=5.0, hold=4, tp_mode="polled", hold_mode="polled"),
    "A: TP5 als Broker-TP": dict(k=3.0, stop="touch", tp=5.0, hold=4),
    "B: Schlusskurs-Stop 3, TP5": dict(k=3.0, stop="close", tp=5.0, hold=4),
    "C: Schlusskurs-Stop 3, TP7": dict(k=3.0, stop="close", tp=7.0, hold=4),
    "D: Broker-SL 4, TP5": dict(k=4.0, stop="touch", tp=5.0, hold=4),
    "E: Schlusskurs-Stop 4, TP5": dict(k=4.0, stop="close", tp=5.0, hold=4),
    "EK heute": dict(k=3.0, stop="touch", tp=5.0, hold=10, anchor="ek"),
}


def boot(a, b, n=5000):
    m = a.merge(b, on="et", suffixes=("_a", "_b"))
    d = (m["r_b"] - m["r_a"]).to_numpy()
    rng = np.random.default_rng(3)
    bs = [rng.choice(d, d.size).mean() for _ in range(n)]
    return len(d), float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, required=True)
    a = ap.parse_args()
    bars, rib, sig = X.lade(a.cache)
    p = X.Pfade(X.kandidaten(rib, sig), bars["m5"])
    out = {}
    for poll in (1, 3):
        X.POLL = poll
        res = {k: X.simuliere(p, **v) for k, v in VAR.items()}
        base = res[next(iter(VAR))]
        print(f"\n=== Poll-Verzoegerung {poll} M5-Bars ===")
        print(f"{'Variante':<36}{'n':>4}{'avgR':>7}{'SumR':>7}{'PF':>6}{'DD R':>7}{'Shrp':>6}{'worst':>7}  gepaart vs heute (n, dR, KI)   Jahre besser")
        jb = {}
        for k, df in res.items():
            z = X.kennzahlen(df)
            n, dm, lo, hi = boot(base, df)
            yb = (df.groupby("jahr")["r"].sum() - base.groupby("jahr")["r"].sum()).fillna(0)
            print(f"{k:<36}{z['n']:>4}{z['avg_r']:>7.3f}{z['sum_r']:>7.1f}{z['pf']:>6.2f}{z['maxdd_r']:>7.1f}"
                  f"{z['sharpe']:>6.2f}{df['r'].min():>7.2f}  ({n}, {dm:+.3f}, [{lo:+.3f};{hi:+.3f}])   {(yb > 0).sum()}/{len(yb)}")
            out[f"poll{poll}|{k}"] = {**z, "worst": float(df["r"].min()), "gepaart": [n, dm, lo, hi],
                                      "jahre_besser": int((yb > 0).sum()),
                                      "exit_gruende": df["grund"].value_counts().to_dict()}
        print("Exit-Gruende B:", res["B: Schlusskurs-Stop 3, TP5"]["grund"].value_counts().to_dict())
        print("Verlust < -1,5R in B:", int((res["B: Schlusskurs-Stop 3, TP5"]["r"] < -1.5).sum()))
    dest = X.REPO_DIR / "knowledge" / "_data" / "ctnl_exit_fokus.json"
    dest.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print("->", dest)


if __name__ == "__main__":
    main()
